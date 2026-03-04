from __future__ import annotations

from typing import Literal, cast, Any, Dict, List, Optional
import datetime

from pydantic import BaseModel, Field

from rhythm_vibe_mcp.constants.defaults import (
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
    notation_hint: _NotationHint = cast("_NotationHint", NOTATION_HINT_UNKNOWN) 
    shorthand_text: str = ""
    events: list[FallbackNoteEvent] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    ok: bool
    message: str
    artifacts: list[MusicArtifact] = Field(default_factory=list)
    fallback: RobustMusicFallback | None = None


# --- Project Manifest Entities ---

class TransformHistoryEntry(BaseModel):
    id: str
    tool_name: str
    timestamp: str
    rationale: str
    reversibility_handle: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ProjectProvenance(BaseModel):
    created_at: str
    original_sources: List[MusicArtifact] = Field(default_factory=list)
    generator_model: Optional[str] = None

class ManifestOverlay(BaseModel):
    type: str  # e.g., 'tempo', 'key', 'chords', 'beat_grid'
    data: Any

class PluginStateReference(BaseModel):
    plugin_id: str
    role: Literal["instrument", "noteFX", "audioFX", "analyzer"]
    state_uri: Optional[str] = None
    fallback_dsp: Optional[str] = None

class AlignmentMapContainer(BaseModel):
    anchor_pairs: List[Dict[str, float]] = Field(
        default_factory=list,
        description="List of dicts mapping 'beats' to 'seconds' to align domains."
    )

class ProjectManifest(BaseModel):
    """Canonical serializable project state."""
    version: str = "1.0.0"
    id: str
    title: str = DEFAULT_UNTITLED
    provenance: ProjectProvenance
    available_export_formats: List[SupportedFormat] = Field(default_factory=list)
    
    # Timeline skeleton (Expanded in later phases)
    tracks: List[Any] = Field(default_factory=list)
    plugins: List[PluginStateReference] = Field(default_factory=list)
    alignment_map: AlignmentMapContainer = Field(default_factory=AlignmentMapContainer)
    
    # Meta / Analysis Overlays
    overlays: List[ManifestOverlay] = Field(default_factory=list)
    history: List[TransformHistoryEntry] = Field(default_factory=list)
