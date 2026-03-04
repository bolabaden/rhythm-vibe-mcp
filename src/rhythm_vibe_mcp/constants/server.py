"""Server identity, tool defaults, and user-facing message strings for MCP tools."""

from __future__ import annotations

# ---- Session state keys ----
SESSION_KEY_MUSESCORE_TOKEN = "musescore_token"

# ---- MCP identity ----
MCP_NAME = "rhythm-vibe-mcp"
MCP_INSTRUCTIONS = (
    "Music vibe-coding server with robust conversion/transposition/fetch tools. "
    "Prefer LilyPond when feasible. On failures, return structured fallback data."
)

# ---- Input / coercion errors ----
MSG_INPUT_ERROR = "input error: {exc}"
MSG_USE_LOCAL_OR_URL = (
    "{exc} Use a local file path (relative to workdir) or a valid HTTP(S) URL."
)
MSG_INPUT_DOES_NOT_EXIST = "Input does not exist: {path}"

# ---- Healthcheck keys (for consistent JSON shape) ----
HEALTHCHECK_WORKDIR = "workdir"
HEALTHCHECK_ARTIFACTS_DIR = "artifacts_dir"
HEALTHCHECK_MUSESCORE_AUTH_ENV = "musescore_auth_env_present"
HEALTHCHECK_MUSESCORE_SESSION = "musescore_session_token_set"
HEALTHCHECK_LILYPOND = "lilypond_available"
HEALTHCHECK_FFMPEG = "ffmpeg_available"
HEALTHCHECK_SUPPORTED_FORMATS = "supported_formats"

# ---- Plan conversion response ----
MSG_PLAN_HINT_PREFIX = "Supported formats: "

# ---- Default tool titles / names ----
DEFAULT_TITLE_REDDIT_VIBE = "reddit_vibe_idea"
DEFAULT_TITLE_TEXT_NOTATION = "text_notation_piece"
DEFAULT_TITLE_AUDIO_OR_FILE = "audio_or_file_to_sheet"
DEFAULT_TITLE_CONVERT = "convert_music"
DEFAULT_TITLE_TRANSPOSE = "transpose_song"

# ---- convert_text_notation fallback hint ----
MSG_FOR_TARGET_PASTE_ABC = "For {target_format} output, paste ABC notation (X:/K:/body) or use normalize_reddit_music_text first."

# ---- compose_story_lily ----
COMPOSE_NOTE_INSTRUMENT = "Instrument: {instrument}, slow lyrical E minor"
COMPOSE_NOTE_DURATION = "Approx. 3-minute duration at configured tempo"
MSG_LILYPOND_COMPOSITION_GENERATED = "lilypond composition generated"
MSG_COMPOSITION_CONVERTED = "composition generated and converted to {output_format}"
MSG_COMPOSITION_PDF_SKIPPED = (
    "composition generated; PDF render skipped (lilypond not found)"
)
LILYPOND_INSTALL_HINT = (
    "Install LilyPond from https://lilypond.org/ then run: lilypond -o {stem} {path}"
)
MSG_COMPOSITION_FAILED = "composition failed: {exc}"
MSG_COMPOSITION_GENERATION_FAILED = "composition generation failed: {exc}"

# ---- musescore_api ----
MSG_MUSESCORE_REQUEST_FAILED = "Musescore request failed: {exc}"
MUSESCORE_HINT_AUTH = "Use public endpoints or provide auth via env/session token."
