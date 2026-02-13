"""Chord quality/suffix recognition for chord token parsing."""

from lilycode_mcp.pitch_constants import PITCH_LETTERS

# Chord quality suffixes (case-insensitive) that indicate a chord token
# Ordered by specificity (longer matches first when using startswith)
CHORD_QUALITY_SUFFIXES: frozenset[str] = frozenset({
    "m", "M", "maj", "min", "dim", "aug", "sus", "add",
    "M7", "m7", "maj7", "min7", "dim7", "aug7", "7", "dom7",
    "M9", "m9", "maj9", "min9", "9",
    "M11", "m11", "11",
    "M13", "m13", "13",
    "sus2", "sus4", "sus9",
    "add2", "add9", "add11", "add13",
    "dim", "°", "o",
    "aug", "+",
    "maj", "min", "ma", "mi",
    "b5", "#5", "b9", "#9", "b11", "#11", "b13", "#13",
    "5", "6", "6/9", "69",
    "7b5", "7#5", "7b9", "7#9",
    "m7b5", "m7-5", "halfdim", "ø",
    "mM7", "mmaj7", "minmaj7",
    "aug7", "+7",
    "dim7", "°7", "o7",
    "phryg", "lyd", "mix", "loc",
    "no3", "no5",
})

# Single-char suffixes (accidentals, etc.)
CHORD_ACCIDENTALS: frozenset[str] = frozenset({"#", "b", "♯", "♭", "♮"})

# Base note letters (re-export from pitch_constants)
CHORD_ROOT_LETTERS: frozenset[str] = PITCH_LETTERS


def looks_like_chord_token(s: str) -> bool:
    """Return True if the string appears to be a chord symbol (e.g. Am, C#m7, Bb, Fmaj7)."""
    if len(s) < 2:
        return False
    c = s[0].upper()
    if c not in PITCH_LETTERS:
        return False
    rest = s[1:].upper().replace(" ", "")
    # Bare accidental + optional letter: C#, Bb
    if len(rest) == 1 and rest in {"#", "B"}:
        return True
    if rest in CHORD_QUALITY_SUFFIXES:
        return True
    # Check prefix match for compound suffixes (e.g. MAJ7, SUS4)
    for suffix in sorted(CHORD_QUALITY_SUFFIXES, key=len, reverse=True):
        if rest == suffix or rest.startswith(suffix):
            # Validate remainder: digits, /, or more quality
            remainder = rest[len(suffix):]
            if not remainder:
                return True
            if remainder.isdigit() or remainder.startswith("/"):
                return True
            if any(remainder.startswith(q) for q in CHORD_QUALITY_SUFFIXES):
                return True
    if rest.startswith(("M", "B", "#")) or "/" in rest:
        return True
    return False
