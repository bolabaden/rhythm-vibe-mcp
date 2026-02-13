"""Path and URL scheme constants for input resolution and artifacts."""

# URL schemes treated as remote (fetch instead of local path)
REMOTE_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})

# Prefixes for quick check (scheme + "://")
REMOTE_URL_PREFIXES: tuple[str, ...] = ("http://", "https://")

# Artifact subdirectory name under workspace
ARTIFACTS_SUBDIR = "artifacts"

# Fallback filename when URL has no extension
DOWNLOAD_FALLBACK_FILENAME = "downloaded_music_asset.bin"

# Artifact filename suffixes (used when building artifact paths)
ARTIFACT_FALLBACK_SUFFIX = ".fallback.json"
ARTIFACT_TRANSCRIBED_MID_SUFFIX = ".transcribed.mid"


def is_remote_ref(ref: str) -> bool:
    """Return True if ref looks like a remote URL (http/https)."""
    s = ref.strip().lower()
    return any(s.startswith(prefix) for prefix in REMOTE_URL_PREFIXES)
