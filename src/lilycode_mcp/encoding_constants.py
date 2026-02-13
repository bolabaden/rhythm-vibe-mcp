"""Text encoding constants for file I/O."""

# Default encoding for reading/writing text files (notation, JSON, etc.)
DEFAULT_TEXT_ENCODING = "utf-8"

# Error handling for decode: "ignore" skips invalid bytes; "replace" uses replacement char
TEXT_DECODE_ERRORS = "ignore"

# Subprocess stdout/stderr decode: "replace" avoids UnicodeDecodeError on binary output
SUBPROCESS_DECODE_ERRORS = "replace"
