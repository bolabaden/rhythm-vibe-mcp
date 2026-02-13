"""ABC notation regex patterns for parsing."""

import re
from lilycode_mcp.abc_constants import ABC_HEADER_KEYS, ABC_SKIP_IN_BODY

# ABC pitch: optional accidental (=_^), letter, optional octave (,' )
ABC_PITCH_RE = re.compile(r"[=_^]?[A-Ga-g][,']*")

# ABC header: key: value at line start
# Build from ABC_HEADER_KEYS for maintainability
_HEADER_KEYS_PATTERN = "|".join(sorted(ABC_HEADER_KEYS))
ABC_HEADER_RE = re.compile(rf"^({_HEADER_KEYS_PATTERN}):\s*(.+)$", re.MULTILINE)

# Minimal header check for looks_like_abc (X, T, M, K are most common)
ABC_LOOKS_LIKE_RE = re.compile(r"^(X:|T:|M:|K:)", re.MULTILINE)

# L: (default length) presence check
ABC_HAS_LENGTH_RE = re.compile(r"^\s*L:\s*\S", re.MULTILINE)

# Any single-letter header at line start
ABC_ANY_HEADER_RE = re.compile(r"^[A-Za-z]:", re.MULTILINE)

# Note token: accidental + letter + octave, optional length
ABC_NOTE_TOKEN_RE = re.compile(r"([=_^]?[A-Ga-g][,']*)(/\d+|\d+/\d+|\d+)?")

# Header keys to skip when parsing note body (as tuple for iteration)
ABC_SKIP_KEYS: tuple[str, ...] = tuple(sorted(ABC_SKIP_IN_BODY))

# Default note length when none specified
ABC_DEFAULT_LENGTH = "1/8"
