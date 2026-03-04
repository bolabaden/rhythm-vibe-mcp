"""Escape sequence mappings for text normalization (CLI, JSON input)."""

from __future__ import annotations

# Literal string sequences (as appear in CLI/JSON) -> actual character
ESCAPE_TO_CHAR: dict[str, str] = {
    "\\n": "\n",
    "\\t": "\t",
    "\\r": "\r",
    "\\\\": "\\",
    "\\'": "'",
    '\\"': '"',
    "\\0": "\0",
    "\\a": "\a",
    "\\b": "\b",
    "\\f": "\f",
    "\\v": "\v",
}

# Sequences that indicate escaped input (for quick detection)
ESCAPE_INDICATORS: frozenset[str] = frozenset(
    {"\\n", "\\t", "\\r", "\\\\", "\\'", '\\"'},
)


def normalize_escapes(text: str) -> str:
    """Replace literal escape sequences (e.g. ``\\n``) with real characters."""
    result: str = text
    for seq, char in ESCAPE_TO_CHAR.items():
        result = result.replace(seq, char)
    return result


def has_escapes(text: str) -> bool:
    """Return ``True`` when text contains common literal escape sequences."""
    return any(seq in text for seq in ESCAPE_INDICATORS)
