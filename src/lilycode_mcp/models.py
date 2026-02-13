from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, Field

from lilycode_mcp.app_defaults import (
    ARTIFACT_SOURCE_LOCAL,
    DEFAULT_UNTITLED,
    FALLBACK_DURATION_UNKNOWN,
    FALLBACK_PITCH_UNKNOWN,
    NOTATION_HINT_UNKNOWN,
)

_NotationHint = Literal["abc", "chordpro", "freeform", "unknown"]


SupportedFormat = Literal[
    "lilypond",
    "pdf",
    "musicxml",
    "midi",
    "wav",
    "mp3",
    "m4a",
    "abc",
    "chordpro",
    "json_fallback",
]


class MusicArtifact(BaseModel):
    path: str
    format: SupportedFormat
    source: str = ARTIFACT_SOURCE_LOCAL
    notes: list[str] = Field(default_factory=list)


class FallbackNoteEvent(BaseModel):
    pitch: str = FALLBACK_PITCH_UNKNOWN
    duration: str = FALLBACK_DURATION_UNKNOWN
    velocity: int | None = None
    measure: int | None = None
    beat: float | None = None


class RobustMusicFallback(BaseModel):
    """Ambiguous but resilient representation for partial/failed conversions."""

    title: str = DEFAULT_UNTITLED
    tonic: str | None = None
    meter: str | None = None
    tempo_bpm: float | None = None
    notation_hint: _NotationHint = cast(_NotationHint, NOTATION_HINT_UNKNOWN)
    shorthand_text: str = ""
    events: list[FallbackNoteEvent] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    ok: bool
    message: str
    artifacts: list[MusicArtifact] = Field(default_factory=list)
    fallback: RobustMusicFallback | None = None
