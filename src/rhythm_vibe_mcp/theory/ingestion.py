"""Ingestion adapters to convert between loose formats and canonical models.

This includes importing 'RobustMusicFallback.events' into the strict symbolic canonical models,
while populating confidence metadata and alignment map placeholders when data is missing.
"""

from typing import List

from rhythm_vibe_mcp.models import FallbackNoteEvent, RobustMusicFallback
from rhythm_vibe_mcp.theory.events import NoteEvent, TimePosition, ExpressionLane
from rhythm_vibe_mcp.constants.defaults import FALLBACK_PITCH_UNKNOWN, FALLBACK_DURATION_UNKNOWN

PITCH_NAME_TO_CLASS = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
    "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11
}

def _parse_pitch_to_midi(pitch_str: str) -> int:
    """Best effort parsing of pitch strings like 'C4', 'A#3' into MIDI note."""
    if not pitch_str or pitch_str == FALLBACK_PITCH_UNKNOWN:
        return 60  # Default middle C if unknown

    s = pitch_str.upper().strip()
    
    # Extract octave from end if present
    octave = 4
    octave_str = ""
    pitch_chars = ""
    for char in s:
        if char.isdigit() or char == '-':
            octave_str += char
        else:
            pitch_chars += char
            
    if octave_str:
        try:
            octave = int(octave_str)
        except ValueError:
            pass
            
    pc = PITCH_NAME_TO_CLASS.get(pitch_chars, 0)
    return (octave + 1) * 12 + pc


def fallback_events_to_canonical(fallback_events: List[FallbackNoteEvent]) -> List[NoteEvent]:
    """
    Convert loose FallbackNoteEvents into strict canonical NoteEvents.
    Automatically establishes placeholders for alignment map and low-confidence elements.
    """
    canonical_list = []
    
    for fe in fallback_events:
        # Resolve Pitch
        midi_pitch = _parse_pitch_to_midi(fe.pitch)
        
        # Resolve Time
        # Default fallback is 0 if unknown
        beat_start = float(fe.beat) if fe.beat is not None else 0.0
        if fe.measure is not None:
            # simple assumption: 4/4 if we only know measure.
            beat_start += (fe.measure - 1) * 4.0
            
        time_pos = TimePosition(beats=beat_start)
        
        # Resolve duration 
        # (Very naive parser for loose string duration, mostly assumes nominal constant if unknown)
        duration_beats = 1.0  # Quarter note default
        if fe.duration != FALLBACK_DURATION_UNKNOWN:
            if "1/4" in fe.duration or "quarter" in fe.duration.lower():
                duration_beats = 1.0
            elif "1/8" in fe.duration or "eighth" in fe.duration.lower():
                duration_beats = 0.5
            elif "1/2" in fe.duration or "half" in fe.duration.lower():
                duration_beats = 2.0
            elif "1/16" in fe.duration or "16th" in fe.duration.lower():
                duration_beats = 0.25
        
        duration_pos = TimePosition(beats=duration_beats)
        
        # Resolve velocity
        velocity = 0.8
        if fe.velocity is not None:
            velocity = max(0.0, min(1.0, fe.velocity / 127.0))
            
        # Confidence lane
        confidence_lane = ExpressionLane(
            type="confidence",
            values=[
                {"time": 0.0, "value": 0.5 if fe.pitch == FALLBACK_PITCH_UNKNOWN else 1.0}
            ]
        )
        
        canon_event = NoteEvent(
            time=time_pos,
            duration=duration_pos,
            pitch=midi_pitch,
            velocity=velocity,
            expressions=[confidence_lane]
        )
        canonical_list.append(canon_event)
        
    return canonical_list

