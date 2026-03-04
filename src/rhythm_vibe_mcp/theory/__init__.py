"""Music theory and structural models package."""

from rhythm_vibe_mcp.theory.pitch import PitchClass, PITCH_NAMES, Note, Interval
from rhythm_vibe_mcp.theory.scale import Scales
from rhythm_vibe_mcp.theory.chord import Chord, ChordType
from rhythm_vibe_mcp.theory.progression import RomanNumeralAnalysis, Cadences
from rhythm_vibe_mcp.theory.transforms import NeoRiemannian, NegativeHarmony, PitchClassSet
from rhythm_vibe_mcp.theory.rhythm import MathematicalRhythm

# Canonical Event Models
from rhythm_vibe_mcp.theory.events import (
    TimePosition,
    ExpressionLane,
    EventBase,
    NoteEvent,
    TempoEvent,
    TimeSignatureEvent,
    ProgramChangeEvent,
    BarEvent,
)

# Bridge for remaining legacy classes explicitly
from rhythm_vibe_mcp.theory.legacy import (
    VoiceLeading,
    FiguredBass,
    FormAndStructure,
    Acoustics,
    TopologicalVoiceLeading,
    MarkovGenerativeHarmony,
    SerialMatrix,
    PitchClassFourier,
)

__all__ = [
    "TimePosition",
    "ExpressionLane",
    "EventBase",
    "NoteEvent",
    "TempoEvent",
    "TimeSignatureEvent",
    "ProgramChangeEvent",
    "BarEvent",
    "PitchClass",
    "PITCH_NAMES",
    "Note",
    "Interval",
    "Scales",
    "Chord",
    "ChordType",
    "RomanNumeralAnalysis",
    "Cadences",
    "NeoRiemannian",
    "NegativeHarmony",
    "PitchClassSet",
    "MathematicalRhythm",
    "VoiceLeading",
    "FiguredBass",
    "FormAndStructure",
    "Acoustics",
    "TopologicalVoiceLeading",
    "MarkovGenerativeHarmony",
    "SerialMatrix",
    "PitchClassFourier",
]
