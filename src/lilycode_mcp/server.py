from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports]

from lilycode_mcp.composer import build_narrative_lily, write_lily_file
from lilycode_mcp.conversion_graph import (
    AUDIO_FORMATS,
    FORMAT_JSON_FALLBACK,
    FORMAT_LILYPOND,
    FORMAT_MIDI,
    FORMAT_MUSICXML,
    FORMAT_PDF,
    TEXT_TO_NOTATION_FORMATS,
)
from lilycode_mcp.converters import (
    convert_any,
    convert_abc_text_to_format,
    normalize_text_to_fallback,
    plan_conversion_route,
    transpose_with_music21,
    SUPPORTED_CONVERSION_FORMATS,
)
from lilycode_mcp.fallbacks import fallback_from_error
from lilycode_mcp.utils import looks_like_abc
from lilycode_mcp.models import MusicArtifact, ToolResult, SupportedFormat
from lilycode_mcp.musescore import musescore_api_request
from lilycode_mcp.utils import (
    artifacts_dir,
    binary_available,
    guess_format,
    normalize_text_input,
    workspace_root,
)
from lilycode_mcp.app_defaults import (
    ARTIFACT_SOURCE_GENERATED,
    ARTIFACT_SOURCE_WEB,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PREFER_SHEET_OUTPUT,
    DEFAULT_TRANSPOSE_OUTPUT,
)
from lilycode_mcp.binary_names import FFMPEG_BINARY, LILYPOND_BINARY
from lilycode_mcp.server_constants import (
    COMPOSE_NOTE_DURATION,
    COMPOSE_NOTE_INSTRUMENT,
    DEFAULT_TITLE_AUDIO_OR_FILE,
    DEFAULT_TITLE_CONVERT,
    DEFAULT_TITLE_REDDIT_VIBE,
    DEFAULT_TITLE_TEXT_NOTATION,
    DEFAULT_TITLE_TRANSPOSE,
    MCP_INSTRUCTIONS,
    MCP_NAME,
    MSG_COMPOSITION_CONVERTED,
    MSG_COMPOSITION_FAILED,
    MSG_COMPOSITION_GENERATION_FAILED,
    MSG_COMPOSITION_PDF_SKIPPED,
    MSG_FOR_TARGET_PASTE_ABC,
    MSG_INPUT_DOES_NOT_EXIST,
    MSG_INPUT_ERROR,
    MSG_LILYPOND_COMPOSITION_GENERATED,
    MSG_USE_LOCAL_OR_URL,
    MSG_MUSESCORE_REQUEST_FAILED,
    MUSESCORE_HINT_AUTH,
    LILYPOND_INSTALL_HINT,
    HEALTHCHECK_ARTIFACTS_DIR,
    HEALTHCHECK_FFMPEG,
    HEALTHCHECK_LILYPOND,
    HEALTHCHECK_MUSESCORE_AUTH_ENV,
    HEALTHCHECK_MUSESCORE_SESSION,
    HEALTHCHECK_SUPPORTED_FORMATS,
    HEALTHCHECK_WORKDIR,
    MSG_PLAN_HINT_PREFIX,
    SESSION_KEY_MUSESCORE_TOKEN,
)
from lilycode_mcp.api_response_keys import (
    KEY_HINT,
    KEY_MESSAGE,
    KEY_OK,
    KEY_ROUTE,
)
from lilycode_mcp.converter_messages import (
    MSG_DOWNLOAD_SUCCESS,
    MSG_FETCH_CHECK_URL,
    MSG_FETCH_FAILED,
    MSG_INVALID_PAYLOAD_JSON,
    MSG_MUSESCORE_TOKEN_SET,
    MSG_NO_KNOWN_ROUTE,
    MSG_ROUTE_FOUND,
)
from lilycode_mcp.env_constants import ENV_MUSESCORE_TOKEN
from lilycode_mcp.http_constants import HTTP_GET
from lilycode_mcp.json_constants import JSON_EMPTY_OBJECT, JSON_INDENT
from lilycode_mcp.limits_constants import truncate_for_preview
from lilycode_mcp.web_fetch import download_music_asset

load_dotenv()

mcp = FastMCP(MCP_NAME, instructions=(MCP_INSTRUCTIONS,))

_SESSION_STATE: dict[str, Any] = {}


def _coerce_input_to_path(input_ref: str) -> Path:
    from lilycode_mcp.path_constants import is_remote_ref

    if is_remote_ref(input_ref):
        return download_music_asset(input_ref)
    p = Path(input_ref).expanduser()
    if not p.is_absolute():
        p = (workspace_root() / p).resolve()
    else:
        p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(MSG_INPUT_DOES_NOT_EXIST.format(path=p))
    return p


def _result_json(result: ToolResult) -> str:
    return json.dumps(result.model_dump(), indent=JSON_INDENT)


def _binary_available_safe(name: str) -> bool:
    """Return True if binary is on PATH; False on any error (so healthcheck always returns all keys)."""
    try:
        return binary_available(name)
    except Exception:
        return False


@mcp.tool()
def healthcheck() -> str:
    """Quick diagnostics and available binary checks."""
    checks = {
        HEALTHCHECK_WORKDIR: str(workspace_root()),
        HEALTHCHECK_ARTIFACTS_DIR: str(artifacts_dir()),
        HEALTHCHECK_MUSESCORE_AUTH_ENV: bool(os.getenv(ENV_MUSESCORE_TOKEN, "")),
        HEALTHCHECK_MUSESCORE_SESSION: bool(_SESSION_STATE.get(SESSION_KEY_MUSESCORE_TOKEN)),
        HEALTHCHECK_LILYPOND: _binary_available_safe(LILYPOND_BINARY),
        HEALTHCHECK_FFMPEG: _binary_available_safe(FFMPEG_BINARY),
        HEALTHCHECK_SUPPORTED_FORMATS: sorted(SUPPORTED_CONVERSION_FORMATS),
    }
    return json.dumps(checks, indent=JSON_INDENT)


@mcp.tool()
def fetch_music_from_web(url: str) -> str:
    """
    Download publicly available music assets from the web.
    Supports direct links to MIDI/audio/sheet-like files.
    """
    try:
        path = download_music_asset(url)
        fmt = guess_format(path)
        result = ToolResult(
            ok=True,
            message=MSG_DOWNLOAD_SUCCESS,
            artifacts=[
                MusicArtifact(
                    path=str(path),
                    format=cast(SupportedFormat, fmt),
                    source=ARTIFACT_SOURCE_WEB,
                    notes=[],
                )
            ],
        )
        return _result_json(result)
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=MSG_FETCH_FAILED.format(exc=exc),
                fallback=fallback_from_error(
                    title="fetch",
                    warning=MSG_FETCH_CHECK_URL.format(exc=exc),
                ),
            ),
        )


@mcp.tool()
def convert_music(input_ref: str, output_format: str) -> str:
    """
    Convert music between formats.
    input_ref can be a local path or URL.
    """
    try:
        input_path = _coerce_input_to_path(input_ref)
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=MSG_INPUT_ERROR.format(exc=exc),
                fallback=fallback_from_error(
                    title=DEFAULT_TITLE_CONVERT,
                    warning=MSG_USE_LOCAL_OR_URL.format(exc=exc),
                ),
            ),
        )

    result = convert_any(input_path, output_format)
    return _result_json(result)


@mcp.tool()
def plan_music_conversion(input_format: str, output_format: str) -> str:
    """Return best-effort route for requested format conversion."""
    route = plan_conversion_route(input_format, output_format)
    if not route:
        return json.dumps(
            {
                KEY_OK: False,
                KEY_MESSAGE: MSG_NO_KNOWN_ROUTE.format(input_format=input_format, output_format=output_format),
                KEY_HINT: MSG_PLAN_HINT_PREFIX + ", ".join(sorted(SUPPORTED_CONVERSION_FORMATS)),
            },
            indent=JSON_INDENT,
        )
    return json.dumps(
        {
            KEY_OK: True,
            KEY_MESSAGE: MSG_ROUTE_FOUND.format(route=" -> ".join(route)),
            KEY_ROUTE: route,
        },
        indent=JSON_INDENT,
    )


@mcp.tool()
def audio_or_file_to_sheet(
    input_ref: str,
    prefer_output: str = DEFAULT_PREFER_SHEET_OUTPUT,
) -> str:
    """
    Best-effort route to sheet output from audio or notation.
    Returns partial/fallback output when strict conversion fails.
    """
    try:
        input_path = _coerce_input_to_path(input_ref)
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=MSG_INPUT_ERROR.format(exc=exc),
                fallback=fallback_from_error(
                    title=DEFAULT_TITLE_AUDIO_OR_FILE,
                    warning=MSG_USE_LOCAL_OR_URL.format(exc=exc),
                ),
            ),
        )

    src_fmt = guess_format(input_path)
    if src_fmt in AUDIO_FORMATS:
        first = convert_any(input_path, FORMAT_MIDI)
        if not first.ok or not first.artifacts:
            return _result_json(first)
        second = convert_any(Path(first.artifacts[0].path), FORMAT_MUSICXML)
        if not second.ok or not second.artifacts:
            return _result_json(second)
        third = convert_any(Path(second.artifacts[0].path), prefer_output)
        return _result_json(third)
    return _result_json(convert_any(input_path, prefer_output))


@mcp.tool()
def transpose_song(
    input_ref: str,
    semitones: int,
    output_format: str = DEFAULT_TRANSPOSE_OUTPUT,
) -> str:
    """Transpose a song/sheet source by semitones."""
    try:
        input_path = _coerce_input_to_path(input_ref)
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=MSG_INPUT_ERROR.format(exc=exc),
                fallback=fallback_from_error(
                    title=DEFAULT_TITLE_TRANSPOSE,
                    warning=MSG_USE_LOCAL_OR_URL.format(exc=exc),
                ),
            ),
        )
    result = transpose_with_music21(input_path, semitones, output_format=output_format)
    return _result_json(result)


@mcp.tool()
def normalize_reddit_music_text(text: str, title: str = DEFAULT_TITLE_REDDIT_VIBE) -> str:
    """
    Normalize informal text notation into a robust fallback model.
    Uses ABC/ChordPro detection before freeform fallback.
    """
    text = normalize_text_input(text)
    result = normalize_text_to_fallback(text, title=title)
    return _result_json(result)


@mcp.tool()
def convert_text_notation_to_lily_or_fallback(
    text: str,
    target_format: str = DEFAULT_OUTPUT_FORMAT,
    title: str = DEFAULT_TITLE_TEXT_NOTATION,
) -> str:
    """
    Attempt text notation conversion.
    ABC notation is converted to LilyPond, MusicXML, or MIDI via music21 when possible.
    ChordPro and freeform text return a robust fallback model for downstream use.
    """
    text = normalize_text_input(text)
    target_format = (target_format or DEFAULT_OUTPUT_FORMAT).lower()
    if target_format == FORMAT_JSON_FALLBACK:
        result = normalize_text_to_fallback(text, title=title)
        return _result_json(result)

    if looks_like_abc(text) and target_format in TEXT_TO_NOTATION_FORMATS:
        result = convert_abc_text_to_format(
            text, output_format=target_format, title=title
        )
        if result.ok:
            return _result_json(result)
        return _result_json(result)

    if looks_like_abc(text) and target_format == FORMAT_PDF:
        result = convert_abc_text_to_format(
            text, output_format=FORMAT_MUSICXML, title=title
        )
        if not result.ok or not result.artifacts:
            return _result_json(result)
        pdf_result = convert_any(Path(result.artifacts[0].path), FORMAT_PDF)
        return _result_json(pdf_result)

    result = normalize_text_to_fallback(text, title=title)
    if result.fallback:
        extra = MSG_FOR_TARGET_PASTE_ABC.format(target_format=target_format)
        fallback = result.fallback
        result = result.model_copy(
            update={
                "fallback": fallback.model_copy(
                    update={"warnings": [*fallback.warnings, extra]}
                )
            }
        )
    return _result_json(result)


@mcp.tool()
def compose_story_lily(
    prompt: str,
    title: str = "Theme",
    tempo_bpm: int = 56,
    instrument: str = "Solo",
    clef: str | None = None,
    midi_instrument: str | None = None,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
) -> str:
    """
    Compose a gentle solo LilyPond piece from narrative text.
    Returns a LilyPond artifact (and optionally PDF/MIDI if output_format requested).
    instrument: e.g. Cello, Violin, Viola, Flute (affects clef and MIDI voice).
    Set output_format to 'pdf' to compose and render in one step (requires lilypond).
    """
    try:
        lily = build_narrative_lily(
            prompt=normalize_text_input(prompt),
            title=title,
            tempo_bpm=tempo_bpm,
            instrument=instrument,
            clef=clef,
            midi_instrument=midi_instrument,
        )
        path = write_lily_file(title, lily)
        artifacts: list[MusicArtifact] = [
            MusicArtifact(
                path=str(path),
                format=FORMAT_LILYPOND,
                source=ARTIFACT_SOURCE_GENERATED,
                notes=[
                    COMPOSE_NOTE_INSTRUMENT.format(instrument=instrument),
                    COMPOSE_NOTE_DURATION,
                ],
            )
        ]
        msg = MSG_LILYPOND_COMPOSITION_GENERATED

        if output_format and output_format.lower() != DEFAULT_OUTPUT_FORMAT:
            conv = convert_any(path, output_format.lower())
            if conv.ok and conv.artifacts:
                artifacts.extend(conv.artifacts)
                msg = MSG_COMPOSITION_CONVERTED.format(output_format=output_format)
            else:
                hint = LILYPOND_INSTALL_HINT.format(
                    stem=path.with_suffix(""), path=path
                )
                fb = conv.fallback
                if fb:
                    fb = fb.model_copy(
                        update={"warnings": [*fb.warnings, hint]}
                    )
                return _result_json(
                    ToolResult(
                        ok=True,
                        message=MSG_COMPOSITION_PDF_SKIPPED,
                        artifacts=artifacts,
                        fallback=fb,
                    )
                )

        return _result_json(
            ToolResult(ok=True, message=msg, artifacts=artifacts)
        )
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=MSG_COMPOSITION_FAILED.format(exc=exc),
                fallback=fallback_from_error(
                    title=title,
                    warning=MSG_COMPOSITION_GENERATION_FAILED.format(exc=exc),
                    shorthand_text=truncate_for_preview(prompt),
                ),
            )
        )


@mcp.tool()
def set_musescore_auth_token(token: str) -> str:
    """
    Set auth token for current MCP session (SSE/session-friendly).
    You can also set MUSESCORE_API_TOKEN in env.
    """
    _SESSION_STATE[SESSION_KEY_MUSESCORE_TOKEN] = token.strip()
    return json.dumps({KEY_OK: True, KEY_MESSAGE: MSG_MUSESCORE_TOKEN_SET}, indent=JSON_INDENT)


@mcp.tool()
def musescore_api(
    endpoint: str,
    method: str = HTTP_GET,
    payload_json: str = JSON_EMPTY_OBJECT,
    base_url: str = "",
) -> str:
    """
    Generic Musescore API proxy for public endpoints and authenticated use.
    """
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(payload_json) if payload_json.strip() else {}
    except json.JSONDecodeError as exc:
        return json.dumps(
            {KEY_OK: False, KEY_MESSAGE: MSG_INVALID_PAYLOAD_JSON.format(exc=exc)}, indent=JSON_INDENT
        )

    token = _SESSION_STATE.get(SESSION_KEY_MUSESCORE_TOKEN)
    try:
        data = musescore_api_request(
            endpoint=endpoint,
            method=method,
            payload=payload,
            base_url=base_url or None,
            auth_token=token,
        )
        if not data.get(KEY_OK, True):
            data.setdefault(KEY_HINT, MUSESCORE_HINT_AUTH)
        return json.dumps(data, indent=JSON_INDENT)
    except Exception as exc:
        return json.dumps(
            {
                KEY_OK: False,
                KEY_MESSAGE: MSG_MUSESCORE_REQUEST_FAILED.format(exc=exc),
                KEY_HINT: MUSESCORE_HINT_AUTH,
            },
            indent=JSON_INDENT,
        )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
