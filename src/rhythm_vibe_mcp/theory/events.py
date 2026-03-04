"""Canonical symbolic event models.

This module defines the basic building blocks of musical events (notes, tempo,
time modifications). It aligns with DAWproject specifications by natively supporting
dual-time semantics (beats and seconds) and preserving per-note expression lanes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class TimePosition:
    """A dual-time pointer capturing both musical time and absolute time."""
    beats: Optional[float] = None
    seconds: Optional[float] = None

@dataclass
class ExpressionLane:
    """A lane of continuous or discrete expression data for a note or track."""
    type: str # e.g. 'timbre', 'pressure', 'pitch', 'gain', 'pan', 'formant'
    values: List[Dict[str, Any]] = field(default_factory=list) # e.g. {"time": ..., "value": ...}

@dataclass
class EventBase:
    """Base class for all canonical timed events."""
    time: TimePosition

@dataclass
class NoteEvent(EventBase):
    """A musical note event with duration, velocity, and expression routing."""
    duration: TimePosition
    pitch: int  # Canonical MIDI note number representation (0-127)
    velocity: float = 0.8  # Normalized 0.0 to 1.0 mapping standard MIDI 0-127
    channel: Optional[int] = None
    expressions: List[ExpressionLane] = field(default_factory=list)
    
@dataclass
class TempoEvent(EventBase):
    """A tempo change event."""
    bpm: float

@dataclass
class TimeSignatureEvent(EventBase):
    """A change in musical meter."""
    numerator: int
    denominator: int

@dataclass
class ProgramChangeEvent(EventBase):
    """A program/instrument routing change event."""
    program: int
    bank_msb: Optional[int] = None
    bank_lsb: Optional[int] = None
    channel: Optional[int] = None

@dataclass
class BarEvent(EventBase):
    """A logical bar/measure marker aligning beats, often used in hybrid ingest."""
    bar_number: int
