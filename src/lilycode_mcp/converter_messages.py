"""Centralized message and warning strings for conversion tools and server."""

# ---- Binary / tool availability ----
MSG_LILYPOND_NOT_FOUND = "lilypond binary not found"
MSG_LILYPOND_NOT_INSTALLED = "lilypond is not installed; produced fallback only."
MSG_LILYPOND_COMPILE_FAILED = "lilypond compile failed"
MSG_LILYPOND_COMPILE_SUCCESS = "lilypond compile success"
MSG_COMPILED_VIA_LILYPOND = "compiled via lilypond"

MSG_FFMPEG_MISSING = "ffmpeg missing"
MSG_FFMPEG_REQUIRED = "ffmpeg is required for audio container conversion."
MSG_FFMPEG_CONVERSION_FAILED = "ffmpeg conversion failed"
MSG_AUDIO_CONVERSION_SUCCESS = "audio conversion success"

MSG_MUSIC21_IMPORT_FAILED = "music21 import failed"
MSG_MUSIC21_CONVERSION_SUCCESS = "music21 conversion success"
MSG_MUSIC21_CONVERSION_FAILED = "music21 conversion failed"
MSG_MUSIC21_NOT_AVAILABLE_ABC = "music21 not available for ABC conversion"

MSG_BASIC_PITCH_UNAVAILABLE = "basic-pitch unavailable"
MSG_INSTALL_AUDIO_DEPS = "Install optional 'audio' deps to transcribe audio: {exc}"
MSG_TRANSCRIPTION_NO_MIDI = "transcription produced no midi"
MSG_BASIC_PITCH_NO_MIDI = "basic-pitch ran but returned no MIDI output."
MSG_AUDIO_TO_MIDI_SUCCESS = "audio to midi success"
MSG_AUDIO_TRANSCRIPTION_FAILED = "audio transcription failed"

# ---- Normalize / fallback ----
MSG_TEXT_NORMALIZED_FALLBACK = "text normalized into robust fallback representation"
MSG_FALLBACK_JSON_GENERATED = "fallback json generated"
MSG_BINARY_SOURCE = "Binary source: {name}"

# ---- ABC ----
MSG_ABC_PARSE_FAILED = "ABC parse failed: {exc}"
MSG_ABC_WRITE_FAILED = "Write to {output_format} failed: {exc}"
MSG_WRITE_FAILED = "Write failed: {exc}"
MSG_ABC_CONVERTED_TO = "ABC notation converted to {output_format}"
MSG_ABC_OUTPUT_NOT_SUPPORTED = "ABC text conversion does not support output format: {output_format}"

# ---- Unsupported format / route ----
MSG_UNSUPPORTED_MUSIC21_OUTPUT = "unsupported music21 output format: {output_format}"
MSG_UNSUPPORTED_OUTPUT_FORMAT = "unsupported output_format {output_format}"
MSG_UNSUPPORTED_TRANSPOSE_OUTPUT = "unsupported transpose output format: {output_format}"
MSG_UNSUPPORTED_TRANSPOSE_FORMAT = "unsupported transpose format {output_format}"

MSG_NO_SINGLE_STEP_ROUTE = "No single-step route from {source_format} to {output_format}."
MSG_REQUESTED_UNSUPPORTED_DIRECT = "Requested unsupported direct route: {source_format} -> {output_format}"
MSG_NO_CONVERSION_ROUTE = "No conversion route from {source_format} to {output_format}."
MSG_REQUESTED_UNSUPPORTED_ROUTE = "Requested unsupported route: {source_format} -> {output_format}"

MSG_CONVERSION_STOPPED_AT = "Conversion stopped at step {from_fmt} -> {to_fmt} (attempted route: {route})"
MSG_CONVERSION_SUCCESS_VIA_ROUTE = "conversion success via route: {route}"
MSG_ALL_ROUTES_FAILED = "All attempted routes failed for {source_format} -> {target_format}."
MSG_TRANSPOSE_SUCCESS = "transpose success"
MSG_TRANSPOSE_FAILED = "transpose failed"

MSG_NO_ROUTE_SUCCEEDED = (
    "No route execution succeeded despite route planning. "
    "Check external binary availability."
)

# ---- Server / fetch ----
MSG_DOWNLOAD_SUCCESS = "download success"
MSG_FETCH_FAILED = "fetch failed: {exc}"
MSG_FETCH_CHECK_URL = "{exc} Check URL is public and returns a music file (MIDI, audio, MusicXML, ABC, PDF, etc.)."
MSG_NO_KNOWN_ROUTE = "No known route {input_format} -> {output_format}"
MSG_ROUTE_FOUND = "Route found: {route}"
MSG_MUSESCORE_TOKEN_SET = "musescore session token set"
MSG_INVALID_PAYLOAD_JSON = "Invalid payload_json: {exc}"

# ---- Helpers for parameterized messages ----
def no_single_step_route(source_format: str, output_format: str) -> str:
    return MSG_NO_SINGLE_STEP_ROUTE.format(source_format=source_format, output_format=output_format)


def requested_unsupported_direct(source_format: str, output_format: str) -> str:
    return MSG_REQUESTED_UNSUPPORTED_DIRECT.replace("{source_format}", source_format).replace(
        "{output_format}", output_format
    )


def no_conversion_route(source_format: str, output_format: str) -> str:
    return MSG_NO_CONVERSION_ROUTE.format(source_format=source_format, output_format=output_format)


def requested_unsupported_route(source_format: str, output_format: str) -> str:
    return MSG_REQUESTED_UNSUPPORTED_ROUTE.replace("{source_format}", source_format).replace(
        "{output_format}", output_format
    )


def conversion_stopped_at(from_fmt: str, to_fmt: str, route: list[str]) -> str:
    return MSG_CONVERSION_STOPPED_AT.format(
        from_fmt=from_fmt, to_fmt=to_fmt, route=" -> ".join(route)
    )


def conversion_success_via_route(route: list[str]) -> str:
    return MSG_CONVERSION_SUCCESS_VIA_ROUTE.format(route=" -> ".join(route))


def all_routes_failed(source_format: str, target_format: str) -> str:
    return MSG_ALL_ROUTES_FAILED.format(source_format=source_format, target_format=target_format)
