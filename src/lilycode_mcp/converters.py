from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from lilycode_mcp.binary_names import FFMPEG_BINARY, LILYPOND_BINARY
from lilycode_mcp.encoding_constants import DEFAULT_TEXT_ENCODING, TEXT_DECODE_ERRORS
from lilycode_mcp.conversion_graph import (
    AUDIO_FORMATS,
    FORMAT_ABC,
    FORMAT_JSON_FALLBACK,
    FORMAT_LILYPOND,
    FORMAT_MIDI,
    FORMAT_MUSICXML,
    FORMAT_PDF,
    MUSIC21_OUTPUT_FORMATS,
    MUSIC21_WRITE_PDF,
    SUPPORTED_CONVERSION_FORMATS,
    TEXT_READABLE_FORMATS,
    candidate_conversion_routes,
    plan_conversion_route,
)
from lilycode_mcp.converter_messages import (
    MSG_ABC_CONVERTED_TO,
    MSG_ABC_OUTPUT_NOT_SUPPORTED,
    MSG_ABC_PARSE_FAILED,
    MSG_ABC_WRITE_FAILED,
    MSG_ALL_ROUTES_FAILED,
    MSG_AUDIO_CONVERSION_SUCCESS,
    MSG_AUDIO_TO_MIDI_SUCCESS,
    MSG_AUDIO_TRANSCRIPTION_FAILED,
    MSG_BASIC_PITCH_NO_MIDI,
    MSG_BASIC_PITCH_UNAVAILABLE,
    MSG_BINARY_SOURCE,
    MSG_COMPILED_VIA_LILYPOND,
    MSG_CONVERSION_STOPPED_AT,
    MSG_CONVERSION_SUCCESS_VIA_ROUTE,
    MSG_FALLBACK_JSON_GENERATED,
    MSG_FFMPEG_CONVERSION_FAILED,
    MSG_FFMPEG_MISSING,
    MSG_FFMPEG_REQUIRED,
    MSG_LILYPOND_COMPILE_FAILED,
    MSG_LILYPOND_COMPILE_SUCCESS,
    MSG_LILYPOND_NOT_FOUND,
    MSG_LILYPOND_NOT_INSTALLED,
    MSG_MUSIC21_CONVERSION_FAILED,
    MSG_MUSIC21_CONVERSION_SUCCESS,
    MSG_MUSIC21_IMPORT_FAILED,
    MSG_MUSIC21_NOT_AVAILABLE_ABC,
    MSG_NO_CONVERSION_ROUTE,
    MSG_NO_ROUTE_SUCCEEDED,
    MSG_NO_SINGLE_STEP_ROUTE,
    MSG_REQUESTED_UNSUPPORTED_DIRECT,
    MSG_REQUESTED_UNSUPPORTED_ROUTE,
    MSG_TEXT_NORMALIZED_FALLBACK,
    MSG_TRANSCRIPTION_NO_MIDI,
    MSG_UNSUPPORTED_MUSIC21_OUTPUT,
    MSG_UNSUPPORTED_OUTPUT_FORMAT,
    MSG_UNSUPPORTED_TRANSPOSE_FORMAT,
    MSG_UNSUPPORTED_TRANSPOSE_OUTPUT,
    MSG_INSTALL_AUDIO_DEPS,
    MSG_NO_ROUTE_SUCCEEDED,
    MSG_TRANSPOSE_FAILED,
    MSG_WRITE_FAILED,
    MSG_TRANSPOSE_SUCCESS,
    all_routes_failed,
    conversion_stopped_at,
    conversion_success_via_route,
    no_conversion_route,
    no_single_step_route,
    requested_unsupported_direct,
    requested_unsupported_route,
)
from lilycode_mcp.fallbacks import fallback_from_error, fallback_from_text
from lilycode_mcp.json_constants import JSON_INDENT
from lilycode_mcp.limits_constants import (
    SOURCE_TEXT_MAX_CHARS,
    truncate_error,
    truncate_for_preview,
)
from lilycode_mcp.models import MusicArtifact, ToolResult
from lilycode_mcp.path_constants import (
    ARTIFACT_FALLBACK_SUFFIX,
    ARTIFACT_TRANSCRIBED_MID_SUFFIX,
)
from lilycode_mcp.utils import (
    artifacts_dir,
    binary_available,
    ensure_abc_has_default_length,
    guess_format,
    run_cmd,
)


def _read_source_text(input_path: Path, max_chars: int | None = None) -> str:
    """Read file as text when format is text-based; return empty string on binary or error."""
    limit = max_chars if max_chars is not None else SOURCE_TEXT_MAX_CHARS
    fmt = guess_format(input_path)
    if fmt not in TEXT_READABLE_FORMATS:
        return ""
    try:
        return input_path.read_text(encoding=DEFAULT_TEXT_ENCODING, errors=TEXT_DECODE_ERRORS)[:limit]
    except Exception:
        return ""


if TYPE_CHECKING:
    from music21 import Score


def _artifact(path: Path, fmt: str, notes: list[str] | None = None) -> MusicArtifact:
    return MusicArtifact(path=str(path), format=fmt, notes=notes or [])


def compile_lilypond_to_pdf(input_path: Path) -> ToolResult:
    if not binary_available(LILYPOND_BINARY):
        return ToolResult(
            ok=False,
            message=MSG_LILYPOND_NOT_FOUND,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=MSG_LILYPOND_NOT_INSTALLED,
                shorthand_text=input_path.read_text(encoding=DEFAULT_TEXT_ENCODING, errors=TEXT_DECODE_ERRORS),
            ),
        )

    out_dir = artifacts_dir()
    code, _, err = run_cmd(
        [LILYPOND_BINARY, "-o", str(out_dir / input_path.stem), str(input_path)]
    )
    if code != 0:
        return ToolResult(
            ok=False,
            message=MSG_LILYPOND_COMPILE_FAILED,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=f"{MSG_LILYPOND_COMPILE_FAILED}: {truncate_error(err)}",
                shorthand_text=input_path.read_text(encoding=DEFAULT_TEXT_ENCODING, errors=TEXT_DECODE_ERRORS),
            ),
        )

    pdf_path = out_dir / f"{input_path.stem}.pdf"
    midi_path = out_dir / f"{input_path.stem}.midi"
    artifacts = [_artifact(pdf_path, FORMAT_PDF, [MSG_COMPILED_VIA_LILYPOND])]
    if midi_path.exists():
        artifacts.append(_artifact(midi_path, FORMAT_MIDI))
    return ToolResult(ok=True, message=MSG_LILYPOND_COMPILE_SUCCESS, artifacts=artifacts)


def convert_audio_container(input_path: Path, output_format: str) -> ToolResult:
    if not binary_available(FFMPEG_BINARY):
        return ToolResult(
            ok=False,
            message=MSG_FFMPEG_MISSING,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=MSG_FFMPEG_REQUIRED,
            ),
        )
    out = artifacts_dir() / f"{input_path.stem}.{output_format}"
    code, _, err = run_cmd([FFMPEG_BINARY, "-y", "-i", str(input_path), str(out)])
    if code != 0:
        return ToolResult(
            ok=False,
            message=MSG_FFMPEG_CONVERSION_FAILED,
            fallback=fallback_from_error(title=input_path.stem, warning=truncate_error(err)),
        )
    return ToolResult(
        ok=True,
        message=MSG_AUDIO_CONVERSION_SUCCESS,
        artifacts=[_artifact(out, output_format)],
    )


def convert_with_music21(input_path: Path, output_format: str) -> ToolResult:
    try:
        from music21 import converter
    except Exception as exc:
        return ToolResult(
            ok=False,
            message=MSG_MUSIC21_IMPORT_FAILED,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=str(exc),
                shorthand_text=_read_source_text(input_path),
            ),
        )

    try:
        score: Score = converter.parse(str(input_path))
        out = artifacts_dir() / f"{input_path.stem}.{output_format}"

        if output_format == FORMAT_MUSICXML:
            score.write(FORMAT_MUSICXML, fp=str(out))
        elif output_format == FORMAT_MIDI:
            score.write(FORMAT_MIDI, fp=str(out))
        elif output_format == FORMAT_LILYPOND:
            # music21 lily output is not always strict LilyPond-compatible,
            # but this is useful as a best-effort intermediary.
            score.write(FORMAT_LILYPOND, fp=str(out))
        elif output_format == FORMAT_ABC:
            text = score.write(FORMAT_ABC)
            out.write_text(str(text), encoding=DEFAULT_TEXT_ENCODING)
        elif output_format == FORMAT_PDF:
            # music21 usually shells out to external engravers for PDF.
            score.write(MUSIC21_WRITE_PDF, fp=str(out))
        else:
            return ToolResult(
                ok=False,
                message=MSG_UNSUPPORTED_MUSIC21_OUTPUT.format(output_format=output_format),
                fallback=fallback_from_error(
                    title=input_path.stem,
                    warning=MSG_UNSUPPORTED_OUTPUT_FORMAT.format(output_format=output_format),
                    shorthand_text=_read_source_text(input_path),
                ),
            )
        return ToolResult(
            ok=True,
            message=MSG_MUSIC21_CONVERSION_SUCCESS,
            artifacts=[_artifact(out, output_format)],
        )
    except Exception as exc:
        return ToolResult(
            ok=False,
            message=MSG_MUSIC21_CONVERSION_FAILED,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=str(exc),
                shorthand_text=_read_source_text(input_path),
            ),
        )


def transpose_with_music21(
    input_path: Path, semitones: int, output_format: str = FORMAT_MUSICXML
) -> ToolResult:
    try:
        from music21 import converter, interval
    except Exception as exc:
        return ToolResult(
            ok=False,
            message=MSG_MUSIC21_IMPORT_FAILED,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=str(exc),
                shorthand_text=_read_source_text(input_path),
            ),
        )

    try:
        score = converter.parse(str(input_path))
        score = score.transpose(interval.Interval(semitones))
        out = artifacts_dir() / f"{input_path.stem}.transposed.{output_format}"
        if output_format == FORMAT_MUSICXML:
            score.write(FORMAT_MUSICXML, fp=str(out))
        elif output_format == FORMAT_MIDI:
            score.write(FORMAT_MIDI, fp=str(out))
        elif output_format == FORMAT_LILYPOND:
            score.write(FORMAT_LILYPOND, fp=str(out))
        else:
            return ToolResult(
                ok=False,
                message=MSG_UNSUPPORTED_TRANSPOSE_OUTPUT.format(output_format=output_format),
                fallback=fallback_from_error(
                    title=input_path.stem,
                    warning=MSG_UNSUPPORTED_TRANSPOSE_FORMAT.format(output_format=output_format),
                    shorthand_text=_read_source_text(input_path),
                ),
            )
        return ToolResult(
            ok=True,
            message=MSG_TRANSPOSE_SUCCESS,
            artifacts=[_artifact(out, output_format)],
        )
    except Exception as exc:
        return ToolResult(
            ok=False,
            message=MSG_TRANSPOSE_FAILED,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=str(exc),
                shorthand_text=_read_source_text(input_path),
            ),
        )


def audio_to_midi(input_path: Path) -> ToolResult:
    try:
        from basic_pitch.inference import predict_and_save
    except Exception as exc:
        return ToolResult(
            ok=False,
            message=MSG_BASIC_PITCH_UNAVAILABLE,
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=MSG_INSTALL_AUDIO_DEPS.format(exc=exc),
            ),
        )

    out_dir = artifacts_dir()
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        try:
            predict_and_save(
                [str(input_path)],
                output_directory=str(temp),
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
            )
            midi_files = list(temp.glob("*.mid")) + list(temp.glob("*.midi"))
            if not midi_files:
                return ToolResult(
                    ok=False,
                    message=MSG_TRANSCRIPTION_NO_MIDI,
                    fallback=fallback_from_error(
                        title=input_path.stem,
                        warning=MSG_BASIC_PITCH_NO_MIDI,
                    ),
                )
            final_path = out_dir / f"{input_path.stem}{ARTIFACT_TRANSCRIBED_MID_SUFFIX}"
            final_path.write_bytes(midi_files[0].read_bytes())
            return ToolResult(
                ok=True,
                message=MSG_AUDIO_TO_MIDI_SUCCESS,
                artifacts=[_artifact(final_path, FORMAT_MIDI)],
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                message=MSG_AUDIO_TRANSCRIPTION_FAILED,
                fallback=fallback_from_error(title=input_path.stem, warning=str(exc)),
            )


def normalize_text_to_fallback(text: str, title: str | None = None) -> ToolResult:
    from lilycode_mcp.app_defaults import DEFAULT_UNTITLED

    fallback = fallback_from_text(text, title=title or DEFAULT_UNTITLED)
    return ToolResult(
        ok=True,
        message=MSG_TEXT_NORMALIZED_FALLBACK,
        fallback=fallback,
    )


def convert_abc_text_to_format(
    abc_text: str,
    output_format: str,
    title: str | None = None,
) -> ToolResult:
    """
    Parse ABC notation from text (music21), write to LilyPond, MusicXML, or MIDI.
    Returns ToolResult with artifacts on success; fallback on parse/write failure.
    """
    from lilycode_mcp.app_defaults import DEFAULT_TEXT_PIECE_TITLE
    from lilycode_mcp.slugify_constants import slugify

    title = title or DEFAULT_TEXT_PIECE_TITLE
    try:
        from music21 import converter
    except Exception as exc:
        return ToolResult(
            ok=False,
            message=MSG_MUSIC21_NOT_AVAILABLE_ABC,
            fallback=fallback_from_error(
                title=title,
                warning=str(exc),
                shorthand_text=truncate_for_preview(abc_text),
            ),
        )
    abc_normalized = ensure_abc_has_default_length(abc_text)
    try:
        score = converter.parse(abc_normalized, format=FORMAT_ABC)
    except Exception as exc:
        fallback = fallback_from_text(abc_text, title=title)
        fallback.warnings.append(MSG_ABC_PARSE_FAILED.format(exc=exc))
        return ToolResult(
            ok=False,
            message=MSG_ABC_PARSE_FAILED.format(exc=exc),
            fallback=fallback,
        )
    safe_title = slugify(title)
    out_path = artifacts_dir() / f"{safe_title}.{output_format}"
    try:
        if output_format == FORMAT_MUSICXML:
            score.write(FORMAT_MUSICXML, fp=str(out_path))
        elif output_format == FORMAT_LILYPOND:
            score.write(FORMAT_LILYPOND, fp=str(out_path))
        elif output_format == FORMAT_MIDI:
            score.write(FORMAT_MIDI, fp=str(out_path))
        elif output_format == FORMAT_ABC:
            text_out = score.write(FORMAT_ABC)
            out_path.write_text(str(text_out), encoding=DEFAULT_TEXT_ENCODING)
        else:
            return ToolResult(
                ok=False,
                message=MSG_ABC_OUTPUT_NOT_SUPPORTED.format(output_format=output_format),
                fallback=fallback_from_text(abc_text, title=title),
            )
    except Exception as exc:
        fallback = fallback_from_text(abc_text, title=title)
        fallback.warnings.append(MSG_ABC_WRITE_FAILED.format(output_format=output_format, exc=exc))
        return ToolResult(
            ok=False,
            message=MSG_WRITE_FAILED.format(exc=exc),
            fallback=fallback,
        )
    return ToolResult(
        ok=True,
        message=MSG_ABC_CONVERTED_TO.format(output_format=output_format),
        artifacts=[_artifact(out_path, output_format)],
    )


def _convert_single_step(input_path: Path, output_format: str) -> ToolResult:
    """One-hop conversion primitive used by route executor."""
    source_format = guess_format(input_path)

    if source_format in AUDIO_FORMATS and output_format in AUDIO_FORMATS:
        return convert_audio_container(input_path, output_format)
    if source_format == FORMAT_LILYPOND and output_format == FORMAT_PDF:
        return compile_lilypond_to_pdf(input_path)
    if source_format in AUDIO_FORMATS and output_format == FORMAT_MIDI:
        return audio_to_midi(input_path)
    if source_format == FORMAT_MIDI and output_format in AUDIO_FORMATS:
        # Uses ffmpeg's synth only if system has a default MIDI decoder.
        return convert_audio_container(input_path, output_format)
    if output_format in MUSIC21_OUTPUT_FORMATS:
        return convert_with_music21(input_path, output_format)

    if output_format == FORMAT_JSON_FALLBACK:
        text = ""
        try:
            text = input_path.read_text(encoding=DEFAULT_TEXT_ENCODING, errors=TEXT_DECODE_ERRORS)
        except Exception:
            pass
        fallback = fallback_from_text(text or MSG_BINARY_SOURCE.format(name=input_path.name), title=input_path.stem)
        out = artifacts_dir() / f"{input_path.stem}{ARTIFACT_FALLBACK_SUFFIX}"
        out.write_text(json.dumps(fallback.model_dump(), indent=JSON_INDENT), encoding=DEFAULT_TEXT_ENCODING)
        return ToolResult(ok=True, message=MSG_FALLBACK_JSON_GENERATED, artifacts=[_artifact(out, FORMAT_JSON_FALLBACK)], fallback=fallback)

    return ToolResult(
        ok=False,
        message=no_single_step_route(source_format, output_format),
        fallback=fallback_from_error(
            title=input_path.stem,
            warning=requested_unsupported_direct(source_format, output_format),
            shorthand_text=_read_source_text(input_path),
        ),
    )


def convert_any(input_path: Path, output_format: str) -> ToolResult:
    source_format = guess_format(input_path)
    target_format = output_format.lower()
    routes = candidate_conversion_routes(source_format, target_format)
    if not routes:
        return ToolResult(
            ok=False,
            message=no_conversion_route(source_format, output_format),
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=requested_unsupported_route(source_format, output_format),
                shorthand_text=_read_source_text(input_path),
            ),
        )

    best_failure: ToolResult | None = None
    best_failure_artifact_count = -1

    for route in routes:
        current_path = input_path
        collected: list[MusicArtifact] = []
        failed = False
        for next_fmt in route[1:]:
            result = _convert_single_step(current_path, next_fmt)
            if not result.ok or not result.artifacts:
                note = conversion_stopped_at(
                    guess_format(current_path), next_fmt, route
                )
                if result.fallback and note not in result.fallback.warnings:
                    result.fallback.warnings.append(note)
                if collected:
                    result = result.model_copy(update={"artifacts": collected})
                artifact_count = len(result.artifacts)
                if artifact_count >= best_failure_artifact_count:
                    best_failure = result
                    best_failure_artifact_count = artifact_count
                failed = True
                break
            collected.extend(result.artifacts)
            current_path = Path(result.artifacts[-1].path)

        if not failed:
            return ToolResult(
                ok=True,
                message=conversion_success_via_route(route),
                artifacts=collected,
            )

    return best_failure or ToolResult(
        ok=False,
        message=all_routes_failed(source_format, target_format),
        fallback=fallback_from_error(
            title=input_path.stem,
            warning=MSG_NO_ROUTE_SUCCEEDED,
            shorthand_text=_read_source_text(input_path),
        ),
    )
