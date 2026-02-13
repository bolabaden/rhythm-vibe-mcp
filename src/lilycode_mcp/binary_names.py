"""External binary names used for conversion and rendering."""

# Binaries checked by healthcheck and used in conversion pipeline
LILYPOND_BINARY = "lilypond"
FFMPEG_BINARY = "ffmpeg"

# All external binaries (for batch checks)
EXTERNAL_BINARIES: frozenset[str] = frozenset({
    LILYPOND_BINARY,
    FFMPEG_BINARY,
})
