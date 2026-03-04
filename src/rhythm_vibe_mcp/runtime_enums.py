from __future__ import annotations

from enum import Enum


class ServerTransport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"
    HTTP_ALIAS = "http"


class JsonSchemaType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"


class NotationHint(str, Enum):
    ABC = "abc"
    CHORDPRO = "chordpro"
    FREEFORM = "freeform"
    UNKNOWN = "unknown"


class ConversionStepId(str, Enum):
    LILYPOND_COMPILE = "lilypond_compile_step"
    AUDIO_CONTAINER = "audio_container_step"
    AUDIO_TO_MIDI = "audio_to_midi_step"
    MUSIC21_CONVERT = "music21_convert_step"
    MUSIC21_TRANSPOSE = "music21_transpose_step"
    ABC_TEXT_CONVERT = "abc_text_convert_step"
