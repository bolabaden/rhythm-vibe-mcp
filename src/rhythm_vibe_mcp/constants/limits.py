"""Numeric limits and truncation lengths for text, errors, and API responses."""

from __future__ import annotations

# Tempo (BPM) bounds for narrative composition
TEMPO_BPM_MIN = 44
TEMPO_BPM_MAX = 72

# Prompt/comment length in generated LilyPond (traceability comment)
PROMPT_COMMENT_MAX_LEN = 220

# Fallback shorthand text / preview length (e.g. in ToolResult.fallback)
SHORTHAND_PREVIEW_MAX_LEN = 2000

# Error message truncation (e.g. lilypond/ffmpeg stderr)
ERROR_MESSAGE_MAX_LEN = 800

# Max characters to read from a text-based source file
SOURCE_TEXT_MAX_CHARS = 50_000

# API response text truncation (e.g. MuseScore error body)
API_RESPONSE_TEXT_MAX_LEN = 500

# CLI help description first line max length
CLI_DESCRIPTION_FIRST_LINE_MAX_LEN = 80

# Conversion route planning: max candidate routes and max steps per route
CANDIDATE_ROUTES_MAX = 4
ROUTE_MAX_DEPTH = 8


def clamp_tempo(bpm: int) -> int:
    return min(max(int(bpm), TEMPO_BPM_MIN), TEMPO_BPM_MAX)


def truncate_for_preview(text: str, max_len: int | None = None) -> str:
    limit = max_len if max_len is not None else SHORTHAND_PREVIEW_MAX_LEN
    return text[:limit] if len(text) > limit else text


def truncate_error(err: str, max_len: int | None = None) -> str:
    limit = max_len if max_len is not None else ERROR_MESSAGE_MAX_LEN
    return err[:limit] if len(err) > limit else err
