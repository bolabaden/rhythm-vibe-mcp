from __future__ import annotations

from pathlib import Path

from lilycode_mcp.app_defaults import (
    COMPOSER_TAGLINE,
    COMPOSER_TAGLINE_DISPLAY,
    DEFAULT_INSTRUMENT,
    DEFAULT_KEY,
    DEFAULT_TEMPO_BPM,
    DEFAULT_TEMPO_MARK,
    DEFAULT_TIME_SIG,
    DEFAULT_TITLE,
)
from lilycode_mcp.instrument_clef_map import INSTRUMENT_CLEF
from lilycode_mcp.instrument_midi_map import midi_for_instrument
from lilycode_mcp.limits_constants import PROMPT_COMMENT_MAX_LEN, clamp_tempo
from lilycode_mcp.lilypond_constants import (
    DEFAULT_CLEF,
    LILYPOND_EXTENSION,
    LILYPOND_PROMPT_SEED_COMMENT,
    LILYPOND_VERSION,
    lilypond_key,
    lilypond_tempo,
    lilypond_time_sig,
)
from lilycode_mcp.encoding_constants import DEFAULT_TEXT_ENCODING
from lilycode_mcp.slugify_constants import slugify
from lilycode_mcp.utils import artifacts_dir


def _slugify_title(title: str) -> str:
    return slugify(title)


def _clef_for_instrument(instrument: str) -> str:
    k = instrument.lower().strip()
    return INSTRUMENT_CLEF.get(k, DEFAULT_CLEF)


def build_narrative_lily(
    *,
    prompt: str,
    title: str = DEFAULT_TITLE,
    tempo_bpm: int = DEFAULT_TEMPO_BPM,
    instrument: str = DEFAULT_INSTRUMENT,
    clef: str | None = None,
    midi_instrument: str | None = None,
    key: str = DEFAULT_KEY,
    time_sig: str = DEFAULT_TIME_SIG,
    tempo_mark: str = DEFAULT_TEMPO_MARK,
) -> str:
    """
    Build a gentle, playable solo piece from narrative text.

    Lyrical motif structure, slow tempo, singing legato.
    Pitch range suits bass-clef instruments by default; use instrument to set clef and MIDI voice.
    """
    safe_tempo = clamp_tempo(tempo_bpm)
    prompt_comment = " ".join(prompt.split())[:PROMPT_COMMENT_MAX_LEN]
    prompt_seed_comment = LILYPOND_PROMPT_SEED_COMMENT
    inst_display = instrument.strip() or DEFAULT_INSTRUMENT
    clef_val = clef if clef else _clef_for_instrument(inst_display)
    midi_val = midi_instrument if midi_instrument else midi_for_instrument(inst_display)
    key_val = lilypond_key(key)
    time_val = lilypond_time_sig(time_sig)
    tempo_val = lilypond_tempo(tempo_mark)

    return f"""\\version "{LILYPOND_VERSION}"
\\header {{
  title = "{title}"
  composer = "{COMPOSER_TAGLINE}"
  instrument = "{inst_display}"
  tagline = "{COMPOSER_TAGLINE_DISPLAY}"
}}

{prompt_seed_comment}
% {prompt_comment}

global = {{
  \\key {key_val}
  \\time {time_val}
  \\tempo "{tempo_val}" 4={safe_tempo}
}}

partA = \\relative c {{
  e,4\\pp( b'8 e g e) |
  d,4( a'8 d fis d) |
  c,4( g'8 c e c) |
  b,4( fis'8 b d b) |
  e,4( b'8 e g e) |
  d,4( a'8 d fis d) |
  c,4( g'8 c e c) |
  b,2. |
}}

partB = \\relative c {{
  \\repeat unfold 2 {{
    e,8\\p( b' e g e b) |
    d,8( a' d fis d a) |
    c,8( g' c e c g) |
    b,8( fis' b d b fis) |
    e,8( b' e g e b) |
    d,8( a' d fis d a) |
    c,8( g' c e c g) |
    b,2. |
  }}
}}

partC = \\relative c {{
  g,4\\mp( d'8 g b g) |
  a,4( e'8 a c a) |
  b,4( fis'8 b d b) |
  g,2. |
  c,4( g'8 c e c) |
  d,4( a'8 d fis d) |
  e,4( b'8 e g e) |
  d,2. |
  g,4( d'8 g b g) |
  a,4( e'8 a c a) |
  b,4( fis'8 b d b) |
  g,2. |
}}

partD = \\relative c {{
  e,4\\p( e8 fis g a) |
  b4( a8 g fis e) |
  d4( d8 e fis g) |
  a4( g8 fis e d) |
  c4( c8 d e fis) |
  g4( fis8 e d c) |
  b,4( fis'8 b d b) |
  e,2. |
}}

partE = \\relative c {{
  e,4\\mp( b'8 e g e) |
  d,4( a'8 d fis d) |
  c,4( g'8 c e c) |
  b,2. |
  e,4\\< ( b'8 e g e) |
  d,4( a'8 d fis d) |
  c,4( g'8 c e c) |
  b,2\\! r4 |
  e,4\\pp( b'8 e g e) |
  d,4( a'8 d fis d) |
  c,4( g'8 c e c) |
  e,2.\\fermata |
}}

pieceMusic = {{
  \\global
  \\clef {clef_val}
  \\partA
  \\partB
  \\partC
  \\partD
  \\partE
}}

\\score {{
  \\new Staff \\with {{
    instrumentName = "{inst_display}"
    midiInstrument = "{midi_val}"
  }} {{ \\pieceMusic }}
  \\layout {{}}
  \\midi {{}}
}}
"""


def write_lily_file(title: str, lily_source: str) -> Path:
    out = artifacts_dir() / f"{_slugify_title(title)}{LILYPOND_EXTENSION}"
    out.write_text(lily_source, encoding=DEFAULT_TEXT_ENCODING)
    return out
