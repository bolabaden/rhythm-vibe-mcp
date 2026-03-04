"""Comprehensive mapping of file extensions to music/audio format identifiers."""

from __future__ import annotations

# Format identifiers used by converters: lilypond, abc, chordpro, musicxml, pdf,
# midi, wav, mp3, m4a, json_fallback (for unknown / unconvertible)
EXT_TO_FORMAT: dict[str, str] = {
    # LilyPond
    "ly": "lilypond",
    "ily": "lilypond",
    "lilypond": "lilypond",
    # PDF
    "pdf": "pdf",
    # MusicXML / XML
    "musicxml": "musicxml",
    "xml": "musicxml",
    "mxl": "musicxml",
    "mxlc": "musicxml",
    # MIDI
    "midi": "midi",
    "mid": "midi",
    "kar": "midi",
    "rmi": "midi",
    "smf": "midi",
    # Audio - WAV
    "wav": "wav",
    "wave": "wav",
    "bwf": "wav",
    "rf64": "wav",
    # Audio - MP3
    "mp3": "mp3",
    "mp2": "mp3",
    "mpa": "mp3",
    # Audio - M4A / AAC
    "m4a": "m4a",
    "aac": "m4a",
    "mp4": "m4a",
    "3gp": "m4a",
    "3g2": "m4a",
    # ABC
    "abc": "abc",
    "abcm2ps": "abc",
    # ChordPro
    "cho": "chordpro",
    "chopro": "chordpro",
    "chordpro": "chordpro",
    "pro": "chordpro",
    "crd": "chordpro",
    # JSON / fallback
    "json": "json_fallback",
    "js": "json_fallback",
    # Additional notation formats -> musicxml where convertible
    "mscx": "musicxml",
    "mscz": "musicxml",
    "sib": "json_fallback",
    "musx": "json_fallback",
    "mus": "json_fallback",
    "dorico": "json_fallback",
    "cap": "json_fallback",
    "capx": "json_fallback",
    "gp": "json_fallback",
    "gp3": "json_fallback",
    "gp4": "json_fallback",
    "gp5": "json_fallback",
    "gpx": "json_fallback",
    "ptb": "json_fallback",
    "tab": "json_fallback",
    # Additional audio aliases normalized to the existing audio graph.
    "flac": "wav",
    "ogg": "wav",
    "oga": "wav",
    "opus": "wav",
    "spx": "wav",
    "weba": "wav",
    "aiff": "wav",
    "aif": "wav",
    "aifc": "wav",
    "au": "wav",
    "snd": "wav",
    "wma": "wav",
    "ra": "wav",
    "ram": "wav",
    "rm": "wav",
    "dsd": "wav",
    "dsf": "wav",
    "dff": "wav",
    "ape": "wav",
    "wv": "wav",
    "tta": "wav",
    "alac": "m4a",
    "ac3": "wav",
    "dts": "wav",
    "cda": "wav",
    "voc": "wav",
    "8svx": "wav",
    "iff": "wav",
    "svx": "wav",
    "sam": "wav",
    "caf": "wav",
    "adts": "m4a",
    "amr": "wav",
    # More notation / DAW
    "lily": "lilypond",
    "scor": "json_fallback",
    "nwc": "json_fallback",
    "nwctxt": "json_fallback",
    "noteworthy": "json_fallback",
    "ptx": "json_fallback",
    "vextab": "json_fallback",
    "vxt": "json_fallback",
    "mei": "json_fallback",
    "mused": "json_fallback",
    "ms": "json_fallback",
    # Plain text / unknown
    "txt": "json_fallback",
    "text": "json_fallback",
    "asc": "json_fallback",
    "md": "json_fallback",
}

# Build extended map: add uppercase and dot-prefixed variants
_FORMAT_EXT_MAP: dict[str, str] = dict(EXT_TO_FORMAT)


def _extend_format_map() -> None:
    """Executes logic for _extend_format_map.

    Args:
    ----
        None

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _extend_format_map logic.

    """
    for ext, fmt in list(EXT_TO_FORMAT.items()):
        _FORMAT_EXT_MAP[ext.upper()] = fmt
        if not ext.startswith("."):
            _FORMAT_EXT_MAP[f".{ext}"] = fmt


_extend_format_map()


def format_from_extension(ext: str) -> str:
    """Return format identifier for the given extension (with or without leading dot).

    Args:
    ----
        ext (Any): Description for ext.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of format_from_extension logic.

    """
    e = ext.lower().strip().lstrip(".")
    return _FORMAT_EXT_MAP.get(e, "json_fallback")
