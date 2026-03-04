"""Comprehensive mapping of MIME / Content-Type values to file extensions."""

from __future__ import annotations

# Content-Type (lowercase, normalized) -> file extension including leading dot
CONTENT_TYPE_TO_EXT: dict[str, str] = {
    # MIDI
    "audio/midi": ".mid",
    "audio/x-midi": ".mid",
    "audio/mid": ".mid",
    "music/crescendo": ".mid",
    "x-music/x-midi": ".mid",
    # Audio
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/x-mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/vnd.wave": ".wav",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/x-ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/webm": ".weba",
    "audio/vnd.dolby.dd-raw": ".ac3",
    "audio/vnd.dts": ".dts",
    "audio/vnd.dts.hd": ".dtshd",
    "audio/aiff": ".aiff",
    "audio/x-aiff": ".aiff",
    "audio/basic": ".au",
    "audio/x-au": ".au",
    "audio/snd": ".au",
    "audio/x-mpegurl": ".m3u",
    "audio/m3u": ".m3u",
    "audio/pls": ".pls",
    "audio/x-scpls": ".pls",
    "audio/vnd.ms-wma": ".wma",
    "audio/x-ms-wma": ".wma",
    "audio/vnd.rn-realaudio": ".ra",
    "audio/x-pn-realaudio": ".ra",
    "audio/speex": ".spx",
    "audio/x-speex": ".spx",
    "audio/amr": ".amr",
    "audio/3gpp": ".3gp",
    "audio/3gpp2": ".3g2",
    "audio/matroska": ".mka",
    "audio/x-matroska": ".mka",
    "audio/mpeg3": ".mp3",
    "audio/x-mpeg-3": ".mp3",
    "audio/mp4a-latm": ".m4a",
    "audio/mpga": ".mp3",
    # Documents
    "application/pdf": ".pdf",
    "application/x-pdf": ".pdf",
    # MusicXML
    "application/vnd.recordare.musicxml+xml": ".musicxml",
    "application/vnd.recordare.musicxml": ".musicxml",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "text/musicxml": ".musicxml",
    # LilyPond / ABC / text
    "text/plain": ".txt",
    "text/vnd.abc": ".abc",
    "text/x-abc": ".abc",
    "application/x-lilypond": ".ly",
    "text/x-lilypond": ".ly",
    # JSON
    "application/json": ".json",
    "text/json": ".json",
    # ChordPro / chord sheets
    "text/vnd.chordpro": ".cho",
    "application/chordpro": ".cho",
    # MuseScore / Sibelius / other notation
    "application/vnd.musescore": ".mscz",
    "application/x-musescore": ".mscz",
    "application/vnd.sibelius": ".sib",
    "application/x-sibelius": ".sib",
    "application/octet-stream": "",
    "binary/octet-stream": "",
    # Additional audio
    "audio/vnd.audible": ".aa",
    "audio/x-hx-aac-adif": ".aac",
    "audio/x-caf": ".caf",
    "audio/vnd.dts.raw": ".dts",
    "audio/eac3": ".ec3",
    "audio/vnd.dlna.adts": ".adts",
    "audio/vnd.dra": ".dra",
    "audio/l24": ".l24",
    "audio/mobile-xmf": ".xmf",
    "audio/vnd.nuera.ecelp4800": ".ecelp4800",
    "audio/vnd.nuera.ecelp7470": ".ecelp7470",
    "audio/vnd.nuera.ecelp9600": ".ecelp9600",
    "audio/ogg; codecs=opus": ".opus",
    "audio/vnd.rip": ".rip",
    "audio/tsplayerd": ".tsd",
    "audio/vnd.voc": ".voc",
    "audio/vorbis": ".ogg",
    "audio/vnd.wav": ".wav",
}


def extension_from_content_type(content_type: str) -> str:
    """Return file extension (with leading dot) for the given Content-Type header value.

    Args:
    ----
        content_type (Any): Description for content_type.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of extension_from_content_type logic.

    """
    ctype = (content_type or "").split(";")[0].strip().lower()
    return CONTENT_TYPE_TO_EXT.get(ctype, "")
