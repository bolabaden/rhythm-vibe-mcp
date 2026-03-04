from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports]

from rhythm_vibe_mcp.audio_analysis import safe_analyze_audio_to_lily
from rhythm_vibe_mcp.composer import build_narrative_lily, write_lily_file
from rhythm_vibe_mcp.constants.binaries import FFMPEG_BINARY, LILYPOND_BINARY
from rhythm_vibe_mcp.constants.defaults import (
    ARTIFACT_SOURCE_GENERATED,
    ARTIFACT_SOURCE_WEB,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PREFER_SHEET_OUTPUT,
    DEFAULT_TRANSPOSE_OUTPUT,
)
from rhythm_vibe_mcp.constants.env import ENV_MUSESCORE_TOKEN
from rhythm_vibe_mcp.constants.formats import format_from_extension
from rhythm_vibe_mcp.constants.http import HTTP_GET
from rhythm_vibe_mcp.constants.json import JSON_EMPTY_OBJECT, JSON_INDENT
from rhythm_vibe_mcp.constants.limits import truncate_for_preview
from rhythm_vibe_mcp.constants.response_keys import (
    KEY_HINT,
    KEY_MESSAGE,
    KEY_OK,
    KEY_ROUTE,
)
from rhythm_vibe_mcp.constants.server import (
    COMPOSE_NOTE_DURATION,
    COMPOSE_NOTE_INSTRUMENT,
    DEFAULT_TITLE_AUDIO_OR_FILE,
    DEFAULT_TITLE_CONVERT,
    DEFAULT_TITLE_REDDIT_VIBE,
    DEFAULT_TITLE_TEXT_NOTATION,
    DEFAULT_TITLE_TRANSPOSE,
    LILYPOND_INSTALL_HINT,
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
    MSG_MUSESCORE_REQUEST_FAILED,
    MSG_PLAN_HINT_PREFIX,
    MSG_USE_LOCAL_OR_URL,
    MUSESCORE_HINT_AUTH,
    SESSION_KEY_MUSESCORE_TOKEN,
)
from rhythm_vibe_mcp.conversion_graph import (
    AUDIO_FORMATS,
    FORMAT_JSON_FALLBACK,
    FORMAT_LILYPOND,
    FORMAT_MIDI,
    FORMAT_MUSICXML,
    FORMAT_PDF,
    SUPPORTED_CONVERSION_FORMATS,
    TEXT_TO_NOTATION_FORMATS,
    plan_conversion_route,
)
from rhythm_vibe_mcp.converter_messages import (
    MSG_DOWNLOAD_SUCCESS,
    MSG_FETCH_CHECK_URL,
    MSG_FETCH_FAILED,
    MSG_INVALID_PAYLOAD_JSON,
    MSG_MUSESCORE_TOKEN_SET,
    MSG_NO_KNOWN_ROUTE,
    MSG_ROUTE_FOUND,
)
from rhythm_vibe_mcp.converters import (
    convert_abc_text_to_format,
    convert_any,
    normalize_text_to_fallback,
    transpose_with_music21,
)
from rhythm_vibe_mcp.fallbacks import fallback_from_error
from rhythm_vibe_mcp.integrations.musescore import musescore_api_request
from rhythm_vibe_mcp.integrations.web import download_music_asset
from rhythm_vibe_mcp.models import MusicArtifact, SupportedFormat, ToolResult
from rhythm_vibe_mcp.runtime_enums import ServerTransport
from rhythm_vibe_mcp.services.app_services import MusicToolApplicationService
from rhythm_vibe_mcp.utils import (
    artifacts_dir,
    binary_available,
    guess_format,
    looks_like_abc,
    normalize_text_input,
    workspace_root,
)

if TYPE_CHECKING:
    from typing import TypedDict

    class HealthcheckPayload(TypedDict):
        workdir: str
        artifacts_dir: str
        musescore_auth_env_present: bool
        musescore_session_token_set: bool
        lilypond_available: bool
        ffmpeg_available: bool
        supported_formats: list[str]

load_dotenv()

mcp = FastMCP(MCP_NAME, instructions=MCP_INSTRUCTIONS)


class SessionContext:
    """Small mutable session-state manager used by server tool workflows."""

    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        self._state: dict[str, Any] = initial_state or {}

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._state[key] = value

    def clear(self) -> None:
        self._state.clear()


_SESSION_CONTEXT = SessionContext()
# Compatibility alias retained for tests/import surfaces.
_SESSION_STATE: dict[str, Any] = _SESSION_CONTEXT.state


class MusicToolService:
    """Object-oriented façade for MCP tool orchestration and shared workflow logic."""

    def __init__(
        self,
        session_context: SessionContext,
    ) -> None:
        self.session_context: SessionContext = session_context

    @staticmethod
    def result_json(result: ToolResult) -> str:
        return json.dumps(result.model_dump(), indent=JSON_INDENT)

    @staticmethod
    def binary_available_safe(name: str) -> bool:
        try:
            return binary_available(name)
        except Exception:
            return False

    def coerce_input_to_path(self, input_ref: str) -> Path:
        from rhythm_vibe_mcp.constants.paths import is_remote_ref

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

    def input_error(self, *, title: str, exc: Exception) -> str:
        return self.result_json(
            ToolResult(
                ok=False,
                message=MSG_INPUT_ERROR.format(exc=exc),
                fallback=fallback_from_error(
                    title=title,
                    warning=MSG_USE_LOCAL_OR_URL.format(exc=exc),
                ),
            ),
        )

    def healthcheck(self) -> str:
        checks: HealthcheckPayload = {
            "workdir": str(workspace_root()),
            "artifacts_dir": str(artifacts_dir()),
            "musescore_auth_env_present": bool(os.getenv(ENV_MUSESCORE_TOKEN, "")),
            "musescore_session_token_set": bool(
                self.session_context.get(SESSION_KEY_MUSESCORE_TOKEN),
            ),
            "lilypond_available": self.binary_available_safe(LILYPOND_BINARY),
            "ffmpeg_available": self.binary_available_safe(FFMPEG_BINARY),
            "supported_formats": sorted(SUPPORTED_CONVERSION_FORMATS),
        }
        return json.dumps(checks, indent=JSON_INDENT)

    def fetch_music_from_web(self, url: str) -> str:
        try:
            path = download_music_asset(url)
            fmt = guess_format(path)
            result = ToolResult(
                ok=True,
                message=MSG_DOWNLOAD_SUCCESS,
                artifacts=[
                    MusicArtifact(
                        path=str(path),
                        format=cast("SupportedFormat", fmt),
                        source=ARTIFACT_SOURCE_WEB,
                        notes=[],
                    ),
                ],
            )
            return self.result_json(result)
        except Exception as exc:
            return self.result_json(
                ToolResult(
                    ok=False,
                    message=MSG_FETCH_FAILED.format(exc=exc),
                    fallback=fallback_from_error(
                        title="fetch",
                        warning=MSG_FETCH_CHECK_URL.format(exc=exc),
                    ),
                ),
            )

    def convert_music(self, input_ref: str, output_format: str) -> str:
        try:
            input_path = self.coerce_input_to_path(input_ref)
        except Exception as exc:
            return self.input_error(title=DEFAULT_TITLE_CONVERT, exc=exc)

        return self.result_json(convert_any(input_path, output_format))

    def plan_music_conversion(self, input_format: str, output_format: str) -> str:
        normalized_input = format_from_extension(input_format)
        normalized_output = format_from_extension(output_format)
        route = plan_conversion_route(normalized_input, normalized_output)
        if not route:
            return json.dumps(
                {
                    KEY_OK: False,
                    KEY_MESSAGE: MSG_NO_KNOWN_ROUTE.format(
                        input_format=normalized_input,
                        output_format=normalized_output,
                    ),
                    KEY_HINT: MSG_PLAN_HINT_PREFIX
                    + ", ".join(sorted(SUPPORTED_CONVERSION_FORMATS)),
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

    def audio_or_file_to_sheet(
        self,
        input_ref: str,
        prefer_output: str = DEFAULT_PREFER_SHEET_OUTPUT,
    ) -> str:
        try:
            input_path = self.coerce_input_to_path(input_ref)
        except Exception as exc:
            return self.input_error(title=DEFAULT_TITLE_AUDIO_OR_FILE, exc=exc)

        src_fmt = guess_format(input_path)
        if src_fmt in AUDIO_FORMATS:
            first = convert_any(input_path, FORMAT_MIDI)
            if not first.ok or not first.artifacts:
                return self.result_json(first)
            second = convert_any(Path(first.artifacts[0].path), FORMAT_MUSICXML)
            if not second.ok or not second.artifacts:
                return self.result_json(second)
            third = convert_any(Path(second.artifacts[0].path), prefer_output)
            return self.result_json(third)
        return self.result_json(convert_any(input_path, prefer_output))

    def transpose_song(
        self,
        input_ref: str,
        semitones: int,
        output_format: str = DEFAULT_TRANSPOSE_OUTPUT,
    ) -> str:
        try:
            input_path = self.coerce_input_to_path(input_ref)
        except Exception as exc:
            return self.input_error(title=DEFAULT_TITLE_TRANSPOSE, exc=exc)
        return self.result_json(
            transpose_with_music21(input_path, semitones, output_format=output_format),
        )

    def normalize_reddit_music_text(
        self,
        text: str,
        title: str = DEFAULT_TITLE_REDDIT_VIBE,
    ) -> str:
        text = normalize_text_input(text)
        return self.result_json(normalize_text_to_fallback(text, title=title))

    def convert_text_notation_to_lily_or_fallback(
        self,
        text: str,
        target_format: str = DEFAULT_OUTPUT_FORMAT,
        title: str = DEFAULT_TITLE_TEXT_NOTATION,
    ) -> str:
        text = normalize_text_input(text)
        target_format = (target_format or DEFAULT_OUTPUT_FORMAT).lower()
        if target_format == FORMAT_JSON_FALLBACK:
            return self.result_json(normalize_text_to_fallback(text, title=title))

        if looks_like_abc(text) and target_format in TEXT_TO_NOTATION_FORMATS:
            result = convert_abc_text_to_format(
                text,
                output_format=target_format,
                title=title,
            )
            return self.result_json(result)

        if looks_like_abc(text) and target_format == FORMAT_PDF:
            result = convert_abc_text_to_format(
                text,
                output_format=FORMAT_MUSICXML,
                title=title,
            )
            if not result.ok or not result.artifacts:
                return self.result_json(result)
            pdf_result = convert_any(Path(result.artifacts[0].path), FORMAT_PDF)
            return self.result_json(pdf_result)

        result = normalize_text_to_fallback(text, title=title)
        if result.fallback:
            extra = MSG_FOR_TARGET_PASTE_ABC.format(target_format=target_format)
            fallback = result.fallback
            result = result.model_copy(
                update={
                    "fallback": fallback.model_copy(
                        update={"warnings": [*fallback.warnings, extra]},
                    ),
                },
            )
        return self.result_json(result)

    def compose_story_lily(
        self,
        prompt: str,
        title: str = "Theme",
        tempo_bpm: int = 56,
        instrument: str = "Solo",
        clef: str | None = None,
        midi_instrument: str | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> str:
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
                    format=cast("SupportedFormat", FORMAT_LILYPOND),
                    source=ARTIFACT_SOURCE_GENERATED,
                    notes=[
                        COMPOSE_NOTE_INSTRUMENT.format(instrument=instrument),
                        COMPOSE_NOTE_DURATION,
                    ],
                ),
            ]
            msg = MSG_LILYPOND_COMPOSITION_GENERATED

            if output_format and output_format.lower() != DEFAULT_OUTPUT_FORMAT:
                conv = convert_any(path, output_format.lower())
                if conv.ok and conv.artifacts:
                    artifacts.extend(conv.artifacts)
                    msg = MSG_COMPOSITION_CONVERTED.format(output_format=output_format)
                else:
                    hint = LILYPOND_INSTALL_HINT.format(
                        stem=path.with_suffix(""),
                        path=path,
                    )
                    fb = conv.fallback
                    if fb:
                        fb = fb.model_copy(update={"warnings": [*fb.warnings, hint]})
                    return self.result_json(
                        ToolResult(
                            ok=True,
                            message=MSG_COMPOSITION_PDF_SKIPPED,
                            artifacts=artifacts,
                            fallback=fb,
                        ),
                    )

            return self.result_json(
                ToolResult(ok=True, message=msg, artifacts=artifacts),
            )
        except Exception as exc:
            return self.result_json(
                ToolResult(
                    ok=False,
                    message=MSG_COMPOSITION_FAILED.format(exc=exc),
                    fallback=fallback_from_error(
                        title=title,
                        warning=MSG_COMPOSITION_GENERATION_FAILED.format(exc=exc),
                        shorthand_text=truncate_for_preview(prompt),
                    ),
                ),
            )

    def set_musescore_auth_token(self, token: str) -> str:
        self.session_context.set(SESSION_KEY_MUSESCORE_TOKEN, token.strip())
        return json.dumps(
            {KEY_OK: True, KEY_MESSAGE: MSG_MUSESCORE_TOKEN_SET},
            indent=JSON_INDENT,
        )

    def musescore_api(
        self,
        endpoint: str,
        method: str = HTTP_GET,
        payload_json: str = JSON_EMPTY_OBJECT,
        base_url: str = "",
    ) -> str:
        payload: dict[str, Any] = {}
        try:
            payload = json.loads(payload_json) if payload_json.strip() else {}
        except json.JSONDecodeError as exc:
            return json.dumps(
                {KEY_OK: False, KEY_MESSAGE: MSG_INVALID_PAYLOAD_JSON.format(exc=exc)},
                indent=JSON_INDENT,
            )

        token = self.session_context.get(SESSION_KEY_MUSESCORE_TOKEN)
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

    def batch_convert_audio_formats(self, input_ref: str) -> str:
        from rhythm_vibe_mcp.batch_audio_converter import batch_convert_audio_formats
        try:
            input_path = self.coerce_input_to_path(input_ref)
        except Exception as exc:
            return self.input_error(title="Batch Convert Audio", exc=exc)
        
        result = batch_convert_audio_formats(input_path)
        return json.dumps(result, indent=JSON_INDENT)

    def analyze_audio_performance(self, input_ref: str) -> str:
        try:
            input_path = self.coerce_input_to_path(input_ref)
        except Exception as exc:
            return self.input_error(title="Analyze Audio Performance", exc=exc)

        result = safe_analyze_audio_to_lily(input_path)
        return json.dumps(result, indent=JSON_INDENT)


_SERVICE = MusicToolService(session_context=_SESSION_CONTEXT)
_APP_SERVICE = MusicToolApplicationService(_SERVICE)


def _coerce_input_to_path(input_ref: str) -> Path:
    """Compatibility wrapper that delegates to MusicToolService."""
    return _SERVICE.coerce_input_to_path(input_ref)


def _result_json(result: ToolResult) -> str:
    """Compatibility wrapper that delegates to MusicToolService."""
    return _SERVICE.result_json(result)


def _binary_available_safe(name: str) -> bool:
    """Compatibility wrapper that delegates to MusicToolService."""
    return _SERVICE.binary_available_safe(name)


@mcp.tool()
def healthcheck() -> str:
    """Quick diagnostics and available binary checks.

    Args:
    ----
        None

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of healthcheck logic.

    """
    return _APP_SERVICE.healthcheck()


@mcp.tool()
def fetch_music_from_web(url: str) -> str:
    """Download publicly available music assets from the web.
    Supports direct links to MIDI/audio/sheet-like files.
    """
    return _APP_SERVICE.fetch_music_from_web(url)


@mcp.tool()
def convert_music(input_ref: str, output_format: str) -> str:
    """Convert music between formats.
    input_ref can be a local path or URL.
    """
    return _APP_SERVICE.convert_music(input_ref, output_format)


@mcp.tool()
def plan_music_conversion(input_format: str, output_format: str) -> str:
    """Return best-effort route for requested format conversion.

    Args:
    ----
        input_format (Any): Description for input_format.
        output_format (Any): Description for output_format.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of plan_music_conversion logic.

    """
    return _APP_SERVICE.plan_music_conversion(input_format, output_format)


@mcp.tool()
def audio_or_file_to_sheet(
    input_ref: str,
    prefer_output: str = DEFAULT_PREFER_SHEET_OUTPUT,
) -> str:
    """Best-effort route to sheet output from audio or notation.
    Returns partial/fallback output when strict conversion fails.
    """
    return _APP_SERVICE.audio_or_file_to_sheet(input_ref, prefer_output)


@mcp.tool()
def transpose_song(
    input_ref: str,
    semitones: int,
    output_format: str = DEFAULT_TRANSPOSE_OUTPUT,
) -> str:
    """Transpose a song/sheet source by semitones."""
    return _APP_SERVICE.transpose_song(input_ref, semitones, output_format)


@mcp.tool()
def normalize_reddit_music_text(
    text: str,
    title: str = DEFAULT_TITLE_REDDIT_VIBE,
) -> str:
    """Normalize informal text notation into a robust fallback model.
    Uses ABC/ChordPro detection before freeform fallback.
    """
    return _APP_SERVICE.normalize_reddit_music_text(text, title)


@mcp.tool()
def convert_text_notation_to_lily_or_fallback(
    text: str,
    target_format: str = DEFAULT_OUTPUT_FORMAT,
    title: str = DEFAULT_TITLE_TEXT_NOTATION,
) -> str:
    """Attempt text notation conversion.
    ABC notation is converted to LilyPond, MusicXML, or MIDI via music21 when possible.
    ChordPro and freeform text return a robust fallback model for downstream use.
    """
    return _APP_SERVICE.convert_text_notation_to_lily_or_fallback(
        text,
        target_format,
        title,
    )


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
    """Compose a gentle solo LilyPond piece from narrative text.
    Returns a LilyPond artifact (and optionally PDF/MIDI if output_format requested).
    instrument: e.g. Cello, Violin, Viola, Flute (affects clef and MIDI voice).
    Set output_format to 'pdf' to compose and render in one step (requires lilypond).
    """
    return _APP_SERVICE.compose_story_lily(
        prompt,
        title,
        tempo_bpm,
        instrument,
        clef,
        midi_instrument,
        output_format,
    )


@mcp.tool()
def set_musescore_auth_token(token: str) -> str:
    """Set auth token for current MCP session (SSE/session-friendly).
    You can also set MUSESCORE_API_TOKEN in env.
    """
    return _APP_SERVICE.set_musescore_auth_token(token)


@mcp.tool()
def musescore_api(
    endpoint: str,
    method: str = HTTP_GET,
    payload_json: str = JSON_EMPTY_OBJECT,
    base_url: str = "",
) -> str:
    """Generic Musescore API proxy for public endpoints and authenticated use.

    Args:
    ----
        endpoint (Any): Description for endpoint.
        method (Any): Description for method.
        payload_json (Any): Description for payload_json.
        base_url (Any): Description for base_url.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of musescore_api logic.

    """
    return _APP_SERVICE.musescore_api(endpoint, method, payload_json, base_url)

@mcp.tool()
def batch_convert_audio(input_ref: str) -> str:
    """Convert an audio file to top 25 formats simultaneously.

    Returns per-format conversion results and output artifact paths.
    """
    return _SERVICE.batch_convert_audio_formats(input_ref)


@mcp.tool()
def analyze_audio_performance(input_ref: str) -> str:
    """Analyze musical performance characteristics from audio and generate LilyPond.

    Produces a text summary with articulation/intonation proxies and MIDI/LilyPond artifacts.
    """
    return _SERVICE.analyze_audio_performance(input_ref)

def main(argv: list[str] | None = None) -> None:
    """Run MCP server with transport arguments.

    Supports stdio, streamable-http, and sse transports.
    For compatibility, `http` is accepted as an alias for `streamable-http`.
    """
    parser = argparse.ArgumentParser(prog="rhythm-vibe-mcp")
    parser.add_argument(
        "--transport",
        choices=[transport.value for transport in ServerTransport],
        default=ServerTransport.STDIO.value,
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    raw_transport = str(args.transport)
    if raw_transport == ServerTransport.HTTP_ALIAS.value:
        transport: Literal["stdio", "sse", "streamable-http"] = "streamable-http"
    else:
        transport = cast(
            Literal["stdio", "sse", "streamable-http"],
            raw_transport,
        )
    if transport in {"streamable-http", "sse"}:
        mcp.settings.host = args.host
        mcp.settings.port = args.port

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
