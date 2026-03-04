"""ABC notation constants: header keys, field names, and metadata."""

from __future__ import annotations

# ABC standard header keys (single letter) - see https://abcnotation.com/wiki/abc:standard
ABC_HEADER_KEYS: frozenset[str] = frozenset(
    {
        "A",  # Area (origin)
        "B",  # Book
        "C",  # Composer
        "D",  # Discography
        "E",  # Elems (decorations)
        "F",  # File url
        "G",  # Group
        "H",  # History
        "I",  # Instruction (inline)
        "K",  # Key
        "L",  # Unit note length
        "M",  # Meter
        "N",  # Notes (annotation)
        "O",  # Origin
        "P",  # Parts
        "Q",  # Tempo
        "R",  # Rhythm
        "S",  # Source
        "T",  # Title
        "U",  # User defined
        "V",  # Voice
        "W",  # Words (lyrics)
        "X",  # Reference number
        "Z",  # Transcription
    },
)

# Header keys that indicate start of tune body (not in header section)
ABC_HEADER_ONLY: frozenset[str] = frozenset(
    {
        "X",
        "T",
        "M",
        "L",
        "K",
        "Q",
        "P",
        "V",
        "W",
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "N",
        "O",
        "R",
        "S",
        "U",
        "Z",
    },
)

# Header keys to skip when parsing note events (header lines)
ABC_SKIP_IN_BODY: frozenset[str] = frozenset(
    {
        "X",
        "T",
        "M",
        "K",
        "Q",
        "V",
        "W",
        "L",
        "P",
        "A",
        "B",
        "C",
    },
)

# Default note length values used in ABC
ABC_DEFAULT_LENGTHS: frozenset[str] = frozenset(
    {
        "1",
        "1/2",
        "1/4",
        "1/8",
        "1/16",
        "1/32",
        "1/64",
        "2",
        "4",
        "8",
        "16",
        "32",
        "64",
    },
)

# Common ABC meter values
ABC_METER_VALUES: frozenset[str] = frozenset(
    {
        "C",
        "C|",
        "2/2",
        "2/4",
        "3/4",
        "4/4",
        "6/8",
        "9/8",
        "12/8",
        "3/2",
        "4/2",
        "3/8",
        "5/4",
        "7/8",
        "5/8",
        "7/4",
    },
)

# Minimal ABC header when none present (reference number + default length)
ABC_DEFAULT_REF = "X:1"
ABC_MINIMAL_HEADER_TEMPLATE = "{ref}\nL:{length}\n"

# Map header key to parse hint for parse_abc_headers
ABC_HEADER_PARSE_HINTS: dict[str, str] = {
    "T": "title",
    "K": "tonic",
    "M": "meter",
    "Q": "tempo_bpm",
    "L": "default_length",
}
