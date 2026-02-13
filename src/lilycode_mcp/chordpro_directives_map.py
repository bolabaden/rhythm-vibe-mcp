"""ChordPro directive patterns and metadata extraction."""

import re
from typing import NamedTuple

# Directives that extract a single value (name -> regex group name)
# Format: {directive: value} or {directive: value}
CHORDPRO_META_DIRECTIVES: frozenset[str] = frozenset({
    "title", "t", "sorttitle", "subtitle", "st", "artist", "sortartist",
    "composer", "lyricist", "copyright", "album", "year", "key", "time",
    "tempo", "duration", "capo", "tag", "meta", "transpose",
    "new_song", "ns", "comment", "c", "comment_italic", "ci", "comment_box", "cb",
    "highlight", "chordfont", "cf", "chordsize", "cs", "chordcolour",
    "textfont", "tf", "textsize", "ts", "textcolour",
    "new_page", "np", "new_physical_page", "npp", "column_break", "colb",
    "columns", "col", "pagetype", "diagrams", "grid", "g", "no_grid", "ng", "titles",
})

# Directives that indicate ChordPro format (for looks_like_chordpro)
CHORDPRO_LOOKUP_DIRECTIVES: frozenset[str] = frozenset({
    "title", "t", "artist", "key", "capo", "subtitle", "st",
    "start_of_chorus", "soc", "end_of_chorus", "eoc",
    "start_of_verse", "sov", "end_of_verse", "eov",
    "start_of_bridge", "sob", "end_of_bridge", "eob",
    "start_of_tab", "sot", "end_of_tab", "eot",
    "comment", "c", "chorus",
})

# Regex for chord brackets: [C], [Am7], [F#m], [Bb/C], etc.
CHORDPRO_CHORD_RE = re.compile(
    r"\[([A-G](?:#|b)?(?:m|maj|min|dim|aug|sus|add)?\d*(?:/[A-G](?:#|b)?)?)\]",
    re.IGNORECASE,
)

# Regex for {directive: value} - capture directive and value
CHORDPRO_DIRECTIVE_RE = re.compile(
    r"\{([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*([^}]*)\}",
)

# Specific directive patterns for common extractions (faster than generic)
CHORDPRO_TITLE_RE = re.compile(r"\{title:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_ARTIST_RE = re.compile(r"\{artist:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_KEY_RE = re.compile(r"\{key:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_CAPO_RE = re.compile(r"\{capo:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_TEMPO_RE = re.compile(r"\{tempo:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_SUBTITLE_RE = re.compile(r"\{subtitle:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_COPYRIGHT_RE = re.compile(r"\{copyright:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_ALBUM_RE = re.compile(r"\{album:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_YEAR_RE = re.compile(r"\{year:\s*([^}]+)\}", re.IGNORECASE)
CHORDPRO_DURATION_RE = re.compile(r"\{duration:\s*([^}]+)\}", re.IGNORECASE)

# Map directive name (lowercase) -> (regex, group)
_DIRECTIVE_EXTRACTORS: dict[str, tuple[re.Pattern[str], int]] = {
    "title": (CHORDPRO_TITLE_RE, 1),
    "t": (CHORDPRO_TITLE_RE, 1),
    "artist": (CHORDPRO_ARTIST_RE, 1),
    "key": (CHORDPRO_KEY_RE, 1),
    "capo": (CHORDPRO_CAPO_RE, 1),
    "tempo": (CHORDPRO_TEMPO_RE, 1),
    "subtitle": (CHORDPRO_SUBTITLE_RE, 1),
    "st": (CHORDPRO_SUBTITLE_RE, 1),
    "copyright": (CHORDPRO_COPYRIGHT_RE, 1),
    "album": (CHORDPRO_ALBUM_RE, 1),
    "year": (CHORDPRO_YEAR_RE, 1),
    "duration": (CHORDPRO_DURATION_RE, 1),
}


class ChordProMeta(NamedTuple):
    """Extracted ChordPro metadata."""

    title: str | None
    artist: str | None
    key: str | None
    capo: str | None
    tempo: str | None
    subtitle: str | None
    copyright: str | None
    album: str | None
    year: str | None
    duration: str | None


def parse_chordpro_meta(text: str) -> ChordProMeta:
    """Extract all known metadata directives from ChordPro text."""
    result: dict[str, str | None] = {
        "title": None, "artist": None, "key": None, "capo": None,
        "tempo": None, "subtitle": None, "copyright": None,
        "album": None, "year": None, "duration": None,
    }
    for name, (pattern, group) in _DIRECTIVE_EXTRACTORS.items():
        m = pattern.search(text)
        if m and result.get(_directive_to_field(name)) is None:
            val = m.group(group).strip()
            if val:
                result[_directive_to_field(name)] = val
    return ChordProMeta(**{k: result.get(k) for k in ChordProMeta._fields})


def _directive_to_field(d: str) -> str:
    if d in ("t",):
        return "title"
    if d in ("st",):
        return "subtitle"
    return d


def extract_chordpro_title(text: str) -> str | None:
    """Extract title from ChordPro text. Prefers {title:}, falls back to {t:}."""
    m = CHORDPRO_TITLE_RE.search(text)
    return m.group(1).strip() if m else None


def extract_chordpro_chords(text: str) -> list[str]:
    """Extract chord symbols from [brackets] in ChordPro text."""
    return CHORDPRO_CHORD_RE.findall(text)
