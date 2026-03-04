"""Pitch and Interval representations.

This module defines the foundational types for modelling musical pitch.
It provides PitchClass, Note, Interval and transposition/math capabilities.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Union

class PitchClass(IntEnum):
    C = 0
    C_SHARP = 1
    D_FLAT = 1
    D = 2
    D_SHARP = 3
    E_FLAT = 3
    E = 4
    F = 5
    F_SHARP = 6
    G_FLAT = 6
    G = 7
    G_SHARP = 8
    A_FLAT = 8
    A = 9
    A_SHARP = 10
    B_FLAT = 10
    B = 11

PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

class Interval(IntEnum):
    UNISON = 0
    MINOR_SECOND = 1
    MAJOR_SECOND = 2
    MINOR_THIRD = 3
    MAJOR_THIRD = 4
    PERFECT_FOURTH = 5
    TRITONE = 6
    PERFECT_FIFTH = 7
    MINOR_SIXTH = 8
    MAJOR_SIXTH = 9
    MINOR_SEVENTH = 10
    MAJOR_SEVENTH = 11
    OCTAVE = 12

class Note:
    """Represents a musical pitch with an octave."""

    def __init__(self, pitch_class: int | PitchClass, octave: int = 4):
        self.pitch_class: int = int(pitch_class) % 12
        self.octave: int = octave

    @property
    def midi_number(self) -> int:
        return (self.octave + 1) * 12 + self.pitch_class

    @classmethod
    def from_midi(cls, midi_number: int) -> Note:
        octave = (midi_number // 12) - 1
        pitch_class = midi_number % 12
        return cls(pitch_class, octave)
        
    @classmethod
    def from_name(cls, name: str) -> 'Note':
        """Constructor from string like 'C4' or 'D#-1'."""
        s = name.upper().strip()
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
                
        pc_map = {
            "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
            "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
            "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11
        }
        pc = pc_map.get(pitch_chars, 0)
        return cls(pc, octave)

    def name(self) -> str:
        return f"{PITCH_NAMES[self.pitch_class]}{self.octave}"

    def __repr__(self) -> str:
        return self.name()

    def transpose(self, semitones: int | Interval) -> Note:
        """Returns a new Note transposed by the given semitones."""
        new_midi = self.midi_number + int(semitones)
        # Prevent going below MIDI 0 or above 127 roughly, but mathematical wrapping is fine
        return Note.from_midi(max(0, min(127, new_midi)))
        
    def __add__(self, interval: int | Interval) -> Note:
        return self.transpose(interval)
        
    def __sub__(self, other: Union[int, Interval, Note]) -> Union[Note, int]:
        if isinstance(other, Note):
            return self.midi_number - other.midi_number
        return self.transpose(-int(other))
        
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Note):
            return False
        return self.midi_number == other.midi_number

    def __lt__(self, other: Note) -> bool:
        return self.midi_number < other.midi_number

__all__ = [
    "PitchClass",
    "PITCH_NAMES",
    "Note",
    "Interval",
]
