"""Shared pitch and note-name constants for music notation parsing."""

from __future__ import annotations

# Western diatonic pitch letters (no accidentals)
PITCH_LETTERS: frozenset[str] = frozenset({"A", "B", "C", "D", "E", "F", "G"})

# Lowercase equivalents (for case-insensitive matching)
PITCH_LETTERS_LOWER: frozenset[str] = frozenset({"a", "b", "c", "d", "e", "f", "g"})

# All valid pitch letters (upper + lower)
PITCH_LETTERS_ANY: frozenset[str] = PITCH_LETTERS | PITCH_LETTERS_LOWER

# Accidentals in various notations
ACCIDENTALS_SHARP: frozenset[str] = frozenset({"#", "♯", "s", "is"})
ACCIDENTALS_FLAT: frozenset[str] = frozenset({"b", "♭", "f", "es"})
ACCIDENTALS_NATURAL: frozenset[str] = frozenset({"n", "♮", "natural"})
ACCIDENTALS_ALL: frozenset[str] = (
    ACCIDENTALS_SHARP | ACCIDENTALS_FLAT | ACCIDENTALS_NATURAL
)

# Octave markers (ABC, LilyPond, etc.)
OCTAVE_UP: frozenset[str] = frozenset({"'", "8va", "8"})
OCTAVE_DOWN: frozenset[str] = frozenset({",", "8vb"})

# Chromatic note names (for lookup)
CHROMATIC_SHARP: tuple[str, ...] = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)
CHROMATIC_FLAT: tuple[str, ...] = (
    "C",
    "Db",
    "D",
    "Eb",
    "E",
    "F",
    "Gb",
    "G",
    "Ab",
    "A",
    "Bb",
    "B",
)

# Key root letters (for key signature parsing)
KEY_ROOT_LETTERS: frozenset[str] = PITCH_LETTERS


def is_pitch_letter(c: str) -> bool:
    """Return True if c is A-G (case insensitive).

    Args:
    ----
        c (Any): Description for c.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of is_pitch_letter logic.

    """
    return len(c) == 1 and c.upper() in PITCH_LETTERS


def normalize_pitch_letter(c: str) -> str:
    """Return uppercase pitch letter, or empty string if invalid.

    Args:
    ----
        c (Any): Description for c.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of normalize_pitch_letter logic.

    """
    return c.upper() if is_pitch_letter(c) else ""
