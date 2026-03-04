from __future__ import annotations

import importlib
import inspect
import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from rhythm_vibe_mcp.constants.binaries import FFMPEG_BINARY, LILYPOND_BINARY
from rhythm_vibe_mcp.conversion_graph import (
    AUDIO_FORMATS,
    FORMAT_ABC,
    FORMAT_JSON_FALLBACK,
    FORMAT_LILYPOND,
    FORMAT_MIDI,
    FORMAT_MUSICXML,
    FORMAT_PDF,
    MUSIC21_OUTPUT_FORMATS,
    MUSIC21_WRITE_PDF,
    TEXT_READABLE_FORMATS,
    candidate_conversion_routes,
    plan_conversion_route as _plan_conversion_route,
)
from rhythm_vibe_mcp.services.pipeline import ConversionContext, ConversionStep

from rhythm_vibe_mcp.converter_messages import (
    MSG_ABC_CONVERTED_TO,
    MSG_ABC_OUTPUT_NOT_SUPPORTED,
    MSG_ABC_PARSE_FAILED,
    MSG_ABC_WRITE_FAILED,
    MSG_AUDIO_CONVERSION_SUCCESS,
    MSG_AUDIO_TO_MIDI_SUCCESS,
    MSG_AUDIO_TRANSCRIPTION_FAILED,
    MSG_BASIC_PITCH_NO_MIDI,
    MSG_BASIC_PITCH_UNAVAILABLE,
    MSG_BINARY_SOURCE,
    MSG_COMPILED_VIA_LILYPOND,
    MSG_FALLBACK_JSON_GENERATED,
    MSG_FFMPEG_CONVERSION_FAILED,
    MSG_FFMPEG_MISSING,
    MSG_FFMPEG_REQUIRED,
    MSG_INSTALL_AUDIO_DEPS,
    MSG_LILYPOND_COMPILE_FAILED,
    MSG_LILYPOND_COMPILE_SUCCESS,
    MSG_LILYPOND_NOT_FOUND,
    MSG_LILYPOND_NOT_INSTALLED,
    MSG_MUSIC21_CONVERSION_FAILED,
    MSG_MUSIC21_CONVERSION_SUCCESS,
    MSG_MUSIC21_IMPORT_FAILED,
    MSG_MUSIC21_NOT_AVAILABLE_ABC,
    MSG_NO_ROUTE_SUCCEEDED,
    MSG_TEXT_NORMALIZED_FALLBACK,
    MSG_TRANSCRIPTION_NO_MIDI,
    MSG_TRANSPOSE_FAILED,
    MSG_TRANSPOSE_SUCCESS,
    MSG_UNSUPPORTED_MUSIC21_OUTPUT,
    MSG_UNSUPPORTED_OUTPUT_FORMAT,
    MSG_UNSUPPORTED_TRANSPOSE_FORMAT,
    MSG_UNSUPPORTED_TRANSPOSE_OUTPUT,
    MSG_WRITE_FAILED,
    all_routes_failed,
    conversion_stopped_at,
    conversion_success_via_route,
    no_conversion_route,
    no_single_step_route,
    requested_unsupported_direct,
    requested_unsupported_route,
)
from rhythm_vibe_mcp.constants.encodings import DEFAULT_TEXT_ENCODING, TEXT_DECODE_ERRORS
from rhythm_vibe_mcp.fallbacks import fallback_from_error, fallback_from_text
from rhythm_vibe_mcp.constants.json import JSON_INDENT
from rhythm_vibe_mcp.constants.limits import (
    SOURCE_TEXT_MAX_CHARS,
    truncate_error,
    truncate_for_preview,
)
from rhythm_vibe_mcp.models import MusicArtifact, ToolResult
from rhythm_vibe_mcp.constants.paths import (
    ARTIFACT_FALLBACK_SUFFIX,
    ARTIFACT_TRANSCRIBED_MID_SUFFIX,
)
from rhythm_vibe_mcp.runtime_enums import ConversionStepId
from rhythm_vibe_mcp.utils import (
    artifacts_dir,
    binary_available,
    ensure_abc_has_default_length,
    guess_format,
    run_cmd,
)

if TYPE_CHECKING:
    from typing import TypedDict

    from music21 import Score

    class JsonFallbackPayload(TypedDict):
        title: str
        shorthand_text: str
        notation_hint: str
        warnings: list[str]
        events: list[dict[str, Any]]


plan_conversion_route = _plan_conversion_route


def _read_source_text(input_path: Path, max_chars: int | None = None) -> str:
    """Read file as text when format is text-based; return empty string on binary or error."""
    limit = max_chars if max_chars is not None else SOURCE_TEXT_MAX_CHARS
    fmt = guess_format(input_path)
    if fmt not in TEXT_READABLE_FORMATS:
        return ""
    try:
        return input_path.read_text(
            encoding=DEFAULT_TEXT_ENCODING,
            errors=TEXT_DECODE_ERRORS,
        )[:limit]
    except Exception:
        return ""


def _artifact(path: Path, fmt: str, notes: list[str] | None = None) -> MusicArtifact:
    """Create a MusicArtifact from path, format, and optional notes."""
    return MusicArtifact(path=str(path), format=cast("Any", fmt), notes=notes or [])


class _LilypondCompileStep(ConversionStep):
    identifier = ConversionStepId.LILYPOND_COMPILE.value

    def run(self, input_path: Path, output_format: str = FORMAT_PDF) -> ToolResult:
        if not binary_available(LILYPOND_BINARY):
            return ToolResult(
                ok=False,
                message=MSG_LILYPOND_NOT_FOUND,
                fallback=fallback_from_error(
                    title=input_path.stem,
                    warning=MSG_LILYPOND_NOT_INSTALLED,
                    shorthand_text=input_path.read_text(
                        encoding=DEFAULT_TEXT_ENCODING,
                        errors=TEXT_DECODE_ERRORS,
                    ),
                ),
            )

        out_dir = artifacts_dir()
        code, _, err = run_cmd(
            [LILYPOND_BINARY, "-o", str(out_dir / input_path.stem), str(input_path)],
        )
        if code != 0:
            return ToolResult(
                ok=False,
                message=MSG_LILYPOND_COMPILE_FAILED,
                fallback=fallback_from_error(
                    title=input_path.stem,
                    warning=f"{MSG_LILYPOND_COMPILE_FAILED}: {truncate_error(err)}",
                    shorthand_text=input_path.read_text(
                        encoding=DEFAULT_TEXT_ENCODING,
                        errors=TEXT_DECODE_ERRORS,
                    ),
                ),
            )

        pdf_path = out_dir / f"{input_path.stem}.pdf"
        midi_path = out_dir / f"{input_path.stem}.midi"
        artifacts = [_artifact(pdf_path, FORMAT_PDF, [MSG_COMPILED_VIA_LILYPOND])]
        if midi_path.exists():
            artifacts.append(_artifact(midi_path, FORMAT_MIDI))
        return ToolResult(
            ok=True,
            message=MSG_LILYPOND_COMPILE_SUCCESS,
            artifacts=artifacts,
        )


class _AudioContainerStep(ConversionStep):
    identifier = ConversionStepId.AUDIO_CONTAINER.value

    def run(self, input_path: Path, output_format: str) -> ToolResult:
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
                fallback=fallback_from_error(
                    title=input_path.stem,
                    warning=truncate_error(err),
                ),
            )
        return ToolResult(
            ok=True,
            message=MSG_AUDIO_CONVERSION_SUCCESS,
            artifacts=[_artifact(out, output_format)],
        )


class _AudioToMidiStep(ConversionStep):
    identifier = ConversionStepId.AUDIO_TO_MIDI.value

    # -- basic_pitch (ML, requires TF — won't work on Py 3.13+) -----------
    def _try_basic_pitch(
        self, input_path: Path
    ) -> ToolResult | None:
        """Attempt ML transcription via basic-pitch.  Returns None if unavailable."""
        try:
            basic_pitch_module = importlib.import_module("basic_pitch")
            inference_module = importlib.import_module("basic_pitch.inference")
            predict_and_save = getattr(inference_module, "predict_and_save")
        except Exception:
            return None  # not installed / not compatible — fall through

        out_dir = artifacts_dir()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            try:
                call_kwargs: dict[str, Any] = {
                    "output_directory": str(temp),
                    "save_midi": True,
                    "sonify_midi": False,
                    "save_model_outputs": False,
                    "save_notes": False,
                }
                params = inspect.signature(predict_and_save).parameters
                if "model_or_model_path" in params:
                    model_path = getattr(
                        basic_pitch_module,
                        "ICASSP_2022_MODEL_PATH",
                        None,
                    ) or getattr(inference_module, "ICASSP_2022_MODEL_PATH", None)
                    if not model_path:
                        raise RuntimeError("basic-pitch model path unavailable")
                    call_kwargs["model_or_model_path"] = str(model_path)

                predict_and_save([str(input_path)], **call_kwargs)
                midi_files = list(temp.glob("*.mid")) + list(temp.glob("*.midi"))
                if not midi_files:
                    return None  # no output — let fallback handle
                final_path = (
                    out_dir
                    / f"{input_path.stem}{ARTIFACT_TRANSCRIBED_MID_SUFFIX}"
                )
                final_path.write_bytes(midi_files[0].read_bytes())
                return ToolResult(
                    ok=True,
                    message=MSG_AUDIO_TO_MIDI_SUCCESS,
                    artifacts=[_artifact(final_path, FORMAT_MIDI)],
                )
            except Exception:
                return None  # ML failed — fall through to ffmpeg path

    # -- ffmpeg + autocorrelation fallback (works on any Python) -----------
    def _try_ffmpeg_fallback(self, input_path: Path) -> ToolResult:
        """Best-effort pitch-detection transcription via ffmpeg + music21."""
        from rhythm_vibe_mcp.audio_to_midi import audio_to_midi_ffmpeg

        out_dir = artifacts_dir()
        final_path = out_dir / f"{input_path.stem}{ARTIFACT_TRANSCRIBED_MID_SUFFIX}"
        try:
            audio_to_midi_ffmpeg(input_path, output_path=final_path)
            return ToolResult(
                ok=True,
                message="audio to midi success (ffmpeg fallback)",
                artifacts=[_artifact(final_path, FORMAT_MIDI)],
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                message=MSG_AUDIO_TRANSCRIPTION_FAILED,
                fallback=fallback_from_error(
                    title=input_path.stem, warning=str(exc)
                ),
            )

    def run(self, input_path: Path, output_format: str = FORMAT_MIDI) -> ToolResult:
        # 1. Try ML transcription (basic_pitch) — best quality
        bp_result = self._try_basic_pitch(input_path)
        if bp_result is not None:
            return bp_result

        # 2. Fall back to ffmpeg-based autocorrelation (Py 3.13 safe)
        return self._try_ffmpeg_fallback(input_path)


_LILYPOND_COMPILE_STEP = _LilypondCompileStep()
_AUDIO_CONTAINER_STEP = _AudioContainerStep()
_AUDIO_TO_MIDI_STEP = _AudioToMidiStep()


class _Music21ConvertStep(ConversionStep):
    identifier = ConversionStepId.MUSIC21_CONVERT.value

    def run(self, input_path: Path, output_format: str) -> ToolResult:
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
                score.write(FORMAT_LILYPOND, fp=str(out))
            elif output_format == FORMAT_ABC:
                text = score.write(FORMAT_ABC)
                out.write_text(str(text), encoding=DEFAULT_TEXT_ENCODING)
            elif output_format == FORMAT_PDF:
                score.write(MUSIC21_WRITE_PDF, fp=str(out))
            else:
                return ToolResult(
                    ok=False,
                    message=MSG_UNSUPPORTED_MUSIC21_OUTPUT.format(
                        output_format=output_format,
                    ),
                    fallback=fallback_from_error(
                        title=input_path.stem,
                        warning=MSG_UNSUPPORTED_OUTPUT_FORMAT.format(
                            output_format=output_format,
                        ),
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


class _Music21TransposeStep:
    identifier = ConversionStepId.MUSIC21_TRANSPOSE.value

    def run(
        self,
        input_path: Path,
        semitones: int,
        output_format: str = FORMAT_MUSICXML,
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
                    message=MSG_UNSUPPORTED_TRANSPOSE_OUTPUT.format(
                        output_format=output_format,
                    ),
                    fallback=fallback_from_error(
                        title=input_path.stem,
                        warning=MSG_UNSUPPORTED_TRANSPOSE_FORMAT.format(
                            output_format=output_format,
                        ),
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


class _AbcTextConvertStep:
    identifier = ConversionStepId.ABC_TEXT_CONVERT.value

    def run(
        self,
        abc_text: str,
        output_format: str,
        title: str | None = None,
    ) -> ToolResult:
        from rhythm_vibe_mcp.constants.defaults import DEFAULT_TEXT_PIECE_TITLE
        from rhythm_vibe_mcp.constants.slugify import slugify

        normalized_title = title or DEFAULT_TEXT_PIECE_TITLE
        try:
            from music21 import converter
        except Exception as exc:
            return ToolResult(
                ok=False,
                message=MSG_MUSIC21_NOT_AVAILABLE_ABC,
                fallback=fallback_from_error(
                    title=normalized_title,
                    warning=str(exc),
                    shorthand_text=truncate_for_preview(abc_text),
                ),
            )
        abc_normalized = ensure_abc_has_default_length(abc_text)
        try:
            score = converter.parse(abc_normalized, format=FORMAT_ABC)
        except Exception as exc:
            fallback = fallback_from_text(abc_text, title=normalized_title)
            fallback.warnings.append(MSG_ABC_PARSE_FAILED.format(exc=exc))
            return ToolResult(
                ok=False,
                message=MSG_ABC_PARSE_FAILED.format(exc=exc),
                fallback=fallback,
            )
        safe_title = slugify(normalized_title)
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
                    message=MSG_ABC_OUTPUT_NOT_SUPPORTED.format(
                        output_format=output_format,
                    ),
                    fallback=fallback_from_text(abc_text, title=normalized_title),
                )
        except Exception as exc:
            fallback = fallback_from_text(abc_text, title=normalized_title)
            fallback.warnings.append(
                MSG_ABC_WRITE_FAILED.format(output_format=output_format, exc=exc),
            )
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


_MUSIC21_CONVERT_STEP = _Music21ConvertStep()
_MUSIC21_TRANSPOSE_STEP = _Music21TransposeStep()
_ABC_TEXT_CONVERT_STEP = _AbcTextConvertStep()


def compile_lilypond_to_pdf(input_path: Path) -> ToolResult:
    """Compile LilyPond source to PDF."""
    return _LILYPOND_COMPILE_STEP.run(input_path, FORMAT_PDF)


def convert_audio_container(input_path: Path, output_format: str) -> ToolResult:
    """Convert audio container format using FFmpeg."""
    return _AUDIO_CONTAINER_STEP.run(input_path, output_format)


def convert_with_music21(input_path: Path, output_format: str) -> ToolResult:
    """Convert music files using music21 library."""
    return _MUSIC21_CONVERT_STEP.run(input_path, output_format)


def transpose_with_music21(
    input_path: Path,
    semitones: int,
    output_format: str = FORMAT_MUSICXML,
) -> ToolResult:
    """Transpose music file by semitones using music21."""
    return _MUSIC21_TRANSPOSE_STEP.run(input_path, semitones, output_format)


def audio_to_midi(input_path: Path) -> ToolResult:
    """Transcribe audio to MIDI using basic-pitch."""
    return _AUDIO_TO_MIDI_STEP.run(input_path, FORMAT_MIDI)


def normalize_text_to_fallback(text: str, title: str | None = None) -> ToolResult:
    """Convert informal text notation to a robust fallback JSON model."""
    from rhythm_vibe_mcp.constants.defaults import DEFAULT_UNTITLED

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
    """Parse ABC notation from text (music21), write to LilyPond, MusicXML, or MIDI.
    Returns ToolResult with artifacts on success; fallback on parse/write failure.
    """
    return _ABC_TEXT_CONVERT_STEP.run(abc_text, output_format, title)


def _convert_single_step(input_path: Path, output_format: str) -> ToolResult:
    """One-hop conversion primitive used by route executor."""
    return _ROUTE_EXECUTOR.convert_single_step(input_path, output_format)


def convert_any(input_path: Path, output_format: str) -> ToolResult:
    """Executes logic for convert_any.

    Args:
    ----
        input_path (Any): Description for input_path.
        output_format (Any): Description for output_format.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of convert_any logic.

    """
    return _ROUTE_EXECUTOR.convert_any(input_path, output_format)


class RouteExecutor:
    """Facade for route planning and execution with compatibility-preserving behavior."""

    def convert_single_step(self, input_path: Path, output_format: str) -> ToolResult:
        source_format = guess_format(input_path)

        if source_format in AUDIO_FORMATS and output_format in AUDIO_FORMATS:
            return convert_audio_container(input_path, output_format)
        if source_format == FORMAT_LILYPOND and output_format == FORMAT_PDF:
            return compile_lilypond_to_pdf(input_path)
        if source_format in AUDIO_FORMATS and output_format == FORMAT_MIDI:
            return audio_to_midi(input_path)
        if source_format == FORMAT_MIDI and output_format in AUDIO_FORMATS:
            return convert_audio_container(input_path, output_format)
        if output_format in MUSIC21_OUTPUT_FORMATS:
            return convert_with_music21(input_path, output_format)

        if output_format == FORMAT_JSON_FALLBACK:
            text = ""
            try:
                text = input_path.read_text(
                    encoding=DEFAULT_TEXT_ENCODING,
                    errors=TEXT_DECODE_ERRORS,
                )
            except Exception:
                pass
            fallback = fallback_from_text(
                text or MSG_BINARY_SOURCE.format(name=input_path.name),
                title=input_path.stem,
            )
            payload: JsonFallbackPayload = cast("JsonFallbackPayload", fallback.model_dump())
            out = artifacts_dir() / f"{input_path.stem}{ARTIFACT_FALLBACK_SUFFIX}"
            out.write_text(
                json.dumps(payload, indent=JSON_INDENT),
                encoding=DEFAULT_TEXT_ENCODING,
            )
            return ToolResult(
                ok=True,
                message=MSG_FALLBACK_JSON_GENERATED,
                artifacts=[_artifact(out, FORMAT_JSON_FALLBACK)],
                fallback=fallback,
            )

        return ToolResult(
            ok=False,
            message=no_single_step_route(source_format, output_format),
            fallback=fallback_from_error(
                title=input_path.stem,
                warning=requested_unsupported_direct(source_format, output_format),
                shorthand_text=_read_source_text(input_path),
            ),
        )

    def convert_any(self, input_path: Path, output_format: str) -> ToolResult:
        source_format = guess_format(input_path)
        target_format = output_format.lower()
        base_context = ConversionContext(
            original_input_path=input_path,
            current_path=input_path,
            source_format=source_format,
            target_format=target_format,
        )
        routes = candidate_conversion_routes(source_format, target_format)
        if not routes:
            return ToolResult(
                ok=False,
                message=no_conversion_route(source_format, output_format),
                fallback=fallback_from_error(
                    title=base_context.original_input_path.stem,
                    warning=requested_unsupported_route(
                        base_context.source_format,
                        output_format,
                    ),
                    shorthand_text=_read_source_text(base_context.original_input_path),
                ),
            )

        best_failure: ToolResult | None = None
        best_failure_artifact_count = -1

        for route in routes:
            context = ConversionContext(
                original_input_path=base_context.original_input_path,
                current_path=base_context.original_input_path,
                source_format=base_context.source_format,
                target_format=base_context.target_format,
                route=tuple(route),
            )
            failed = False
            for next_fmt in route[1:]:
                result = self.convert_single_step(context.current_path, next_fmt)
                if not result.ok or not result.artifacts:
                    note = conversion_stopped_at(
                        guess_format(context.current_path),
                        next_fmt,
                        route,
                    )
                    if result.fallback and note not in result.fallback.warnings:
                        result.fallback.warnings.append(note)
                    if context.collected_artifacts:
                        result = result.model_copy(
                            update={"artifacts": context.collected_artifacts},
                        )
                    artifact_count = len(result.artifacts)
                    if artifact_count >= best_failure_artifact_count:
                        best_failure = result
                        best_failure_artifact_count = artifact_count
                    failed = True
                    break
                context.collected_artifacts.extend(result.artifacts)
                context.current_path = Path(result.artifacts[-1].path)

            if not failed:
                return ToolResult(
                    ok=True,
                    message=conversion_success_via_route(route),
                    artifacts=context.collected_artifacts,
                )

        return best_failure or ToolResult(
            ok=False,
            message=all_routes_failed(
                base_context.source_format,
                base_context.target_format,
            ),
            fallback=fallback_from_error(
                title=base_context.original_input_path.stem,
                warning=MSG_NO_ROUTE_SUCCEEDED,
                shorthand_text=_read_source_text(base_context.original_input_path),
            ),
        )


_ROUTE_EXECUTOR = RouteExecutor()


class ConverterEngine:
    """Object-oriented conversion facade for orchestrators and future dependency injection."""

    def compile_lilypond_to_pdf(self, input_path: Path) -> ToolResult:
        return compile_lilypond_to_pdf(input_path)

    def convert_audio_container(self, input_path: Path, output_format: str) -> ToolResult:
        return convert_audio_container(input_path, output_format)

    def convert_with_music21(self, input_path: Path, output_format: str) -> ToolResult:
        return convert_with_music21(input_path, output_format)

    def transpose_with_music21(
        self,
        input_path: Path,
        semitones: int,
        output_format: str = FORMAT_MUSICXML,
    ) -> ToolResult:
        return transpose_with_music21(input_path, semitones, output_format)

    def audio_to_midi(self, input_path: Path) -> ToolResult:
        return audio_to_midi(input_path)

    def normalize_text_to_fallback(
        self,
        text: str,
        title: str | None = None,
    ) -> ToolResult:
        return normalize_text_to_fallback(text, title)

    def convert_abc_text_to_format(
        self,
        abc_text: str,
        output_format: str,
        title: str | None = None,
    ) -> ToolResult:
        return convert_abc_text_to_format(abc_text, output_format, title)

    def convert_any(self, input_path: Path, output_format: str) -> ToolResult:
        return convert_any(input_path, output_format)


default_converter_engine = ConverterEngine()
