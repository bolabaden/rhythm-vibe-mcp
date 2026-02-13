"""Conversion graph and format classification for music format conversions."""

from collections import deque

from lilycode_mcp.limits_constants import CANDIDATE_ROUTES_MAX, ROUTE_MAX_DEPTH

# Canonical format identifiers (use these in conditionals and convert_any targets)
FORMAT_ABC = "abc"
FORMAT_CHORDPRO = "chordpro"
FORMAT_JSON_FALLBACK = "json_fallback"
FORMAT_LILYPOND = "lilypond"
FORMAT_MIDI = "midi"
FORMAT_MUSICXML = "musicxml"
FORMAT_PDF = "pdf"

# music21-specific write format for PDF (shells out to external engravers)
MUSIC21_WRITE_PDF = "musicxml.pdf"

# Formats that participate in the conversion pipeline
SUPPORTED_CONVERSION_FORMATS = frozenset({
    "wav", "mp3", "m4a", "midi", "musicxml", "lilypond", "abc", "pdf",
    "chordpro", "json_fallback",
})

# Formats that can be read as text (for source parsing)
TEXT_READABLE_FORMATS = frozenset({
    "lilypond", "abc", "chordpro", "musicxml", "json_fallback",
})

# Audio formats (inter-convertible via ffmpeg, can go to/from midi)
AUDIO_FORMATS = frozenset({"wav", "mp3", "m4a"})

# Notation formats that music21 can produce
MUSIC21_OUTPUT_FORMATS = frozenset({
    "musicxml", "midi", "lilypond", "abc", "pdf",
})

# Formats that convert_text_notation_to_lily_or_fallback accepts for direct ABC conversion
# (pdf is handled via musicxml -> convert_any -> pdf in server)
TEXT_TO_NOTATION_FORMATS = frozenset({"lilypond", "musicxml", "midi", "abc"})

# Conversion graph: format -> set of formats reachable in one step
CONVERSION_GRAPH: dict[str, set[str]] = {
    "wav": {"mp3", "m4a", "midi"},
    "mp3": {"wav", "m4a", "midi"},
    "m4a": {"wav", "mp3", "midi"},
    "midi": {"musicxml", "lilypond", "pdf", "wav", "mp3", "m4a"},
    "musicxml": {"midi", "lilypond", "pdf", "abc"},
    "lilypond": {"pdf", "midi", "musicxml"},
    "abc": {"musicxml", "midi", "lilypond"},
    "pdf": {"json_fallback"},
    "json_fallback": set(),
    "chordpro": {"json_fallback"},
}


def neighbors(format_name: str) -> set[str]:
    """Return set of formats reachable in one conversion step."""
    return CONVERSION_GRAPH.get(format_name.lower(), set())


def plan_conversion_route(source_format: str, target_format: str) -> list[str]:
    """Shortest best-effort route across the conversion graph."""
    source_format = source_format.lower()
    target_format = target_format.lower()
    if source_format == target_format:
        return [source_format]

    q: deque[list[str]] = deque([[source_format]])
    seen = {source_format}
    while q:
        path = q.popleft()
        cur = path[-1]
        for nxt in neighbors(cur):
            if nxt in seen:
                continue
            next_path = path + [nxt]
            if nxt == target_format:
                return next_path
            seen.add(nxt)
            q.append(next_path)
    return []


def candidate_conversion_routes(
    source_format: str,
    target_format: str,
    *,
    max_routes: int = CANDIDATE_ROUTES_MAX,
    max_depth: int = ROUTE_MAX_DEPTH,
) -> list[list[str]]:
    """
    Return a small set of shortest candidate routes.

    Route execution can fail at runtime due to missing binaries/plugins.
    Trying a handful of alternatives improves best-effort behavior.
    """
    source_format = source_format.lower()
    target_format = target_format.lower()
    if source_format == target_format:
        return [[source_format]]

    routes: list[list[str]] = []
    q: deque[list[str]] = deque([[source_format]])

    while q and len(routes) < max_routes:
        path = q.popleft()
        cur = path[-1]
        if len(path) > max_depth:
            continue
        for nxt in sorted(neighbors(cur)):
            if nxt in path:
                continue
            next_path = path + [nxt]
            if nxt == target_format:
                routes.append(next_path)
                if len(routes) >= max_routes:
                    break
                continue
            q.append(next_path)
    return routes
