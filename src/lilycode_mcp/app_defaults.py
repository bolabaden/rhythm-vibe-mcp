"""Default display strings and values for tools and UI."""

# Composition / narrative
DEFAULT_TITLE = "Theme"
DEFAULT_INSTRUMENT = "Solo"
DEFAULT_TEMPO_BPM = 56

# Text notation conversion
DEFAULT_TEXT_PIECE_TITLE = "text_notation_piece"
DEFAULT_REDDIT_TITLE = "reddit_vibe_idea"
DEFAULT_UNTITLED = "untitled"

# Fallback filenames / slugs
DEFAULT_SLUG = "piece"

# Model default values (for MusicArtifact.source, etc.)
ARTIFACT_SOURCE_LOCAL = "local"
ARTIFACT_SOURCE_WEB = "web"
ARTIFACT_SOURCE_GENERATED = "generated"

# Fallback / notation hint and duration labels (RobustMusicFallback, FallbackNoteEvent)
NOTATION_HINT_UNKNOWN = "unknown"
NOTATION_HINT_ABC = "abc"
NOTATION_HINT_CHORDPRO = "chordpro"
NOTATION_HINT_FREEFORM = "freeform"
FALLBACK_PITCH_UNKNOWN = "unknown"
FALLBACK_DURATION_UNKNOWN = "unknown"
FALLBACK_DURATION_CHORD = "chord"

# LilyPond narrative defaults (keys passed to lilypond_constants)
DEFAULT_KEY = "e minor"
DEFAULT_TIME_SIG = "3/4"
DEFAULT_TEMPO_MARK = "Lento e cantabile"

# Default output format for tools (when not specified)
DEFAULT_OUTPUT_FORMAT = "lilypond"
DEFAULT_PREFER_SHEET_OUTPUT = "pdf"
DEFAULT_TRANSPOSE_OUTPUT = "musicxml"

# MCP server identity
COMPOSER_TAGLINE = "lilycode-mcp"
COMPOSER_TAGLINE_DISPLAY = "Vibe-coded narrative scoring"
