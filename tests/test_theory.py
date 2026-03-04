"""Contract tests for the theory module.

These tests intentionally lock current behavior before any deeper theory-module refactor.
"""

from __future__ import annotations

import pytest

from rhythm_vibe_mcp.theory import (
    Chord,
    ChordType,
    NeoRiemannian,
    Note,
    RomanNumeralAnalysis,
    Scales,
)


class TestNote:
    def test_midi_number_roundtrip(self) -> None:
        note = Note(0, 4)  # C4
        assert note.midi_number == 60

        restored = Note.from_midi(60)
        assert restored.pitch_class == 0
        assert restored.octave == 4
        assert restored.name() == "C4"

    def test_pitch_class_wraps_mod_12(self) -> None:
        wrapped = Note(14, 3)
        assert wrapped.pitch_class == 2
        assert wrapped.name() == "D3"


class TestScales:
    def test_generate_major_scale_from_c(self) -> None:
        assert Scales.generate_scale(0, Scales.MAJOR) == [0, 2, 4, 5, 7, 9, 11]


class TestChord:
    def test_major_chord_properties(self) -> None:
        chord = Chord(0, ChordType.MAJOR.value)
        assert chord.is_major() is True
        assert chord.is_minor() is False
        assert chord.get_bass() == 0
        assert repr(chord) == "Cmaj"

    def test_inversion_changes_bass_and_repr(self) -> None:
        chord = Chord(0, ChordType.MAJOR.value, inversion=1)
        assert chord.get_bass() == 4
        assert repr(chord) == "Cmaj/E"


class TestNeoRiemannian:
    def test_p_l_r_on_c_major(self) -> None:
        c_major = Chord(0, ChordType.MAJOR.value)

        p = NeoRiemannian.P(c_major)
        assert p.root == 0
        assert p.is_minor() is True

        elll = NeoRiemannian.L(c_major)
        assert elll.root == 4
        assert elll.is_minor() is True

        r = NeoRiemannian.R(c_major)
        assert r.root == 9
        assert r.is_minor() is True


class TestRomanNumeralAnalysis:
    def test_get_chord_major_key(self) -> None:
        dominant = RomanNumeralAnalysis.get_chord("V", key_root=0, is_major_key=True)
        assert dominant.root == 7
        assert dominant.is_major() is True

    def test_get_chord_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown roman numeral"):
            RomanNumeralAnalysis.get_chord("not-a-real-numeral", key_root=0)

def test_fallback_events_to_canonical() -> None:
    from rhythm_vibe_mcp.models import FallbackNoteEvent
    from rhythm_vibe_mcp.theory.ingestion import fallback_events_to_canonical
    
    events = [
        FallbackNoteEvent(pitch="C4", beat=2.0, duration="1/4", velocity=100),
        FallbackNoteEvent(pitch="unknown", measure=2)
    ]
    
    canon = fallback_events_to_canonical(events)
    assert len(canon) == 2
    
    assert canon[0].pitch == 60
    assert canon[0].time.beats == 2.0
    assert canon[0].velocity > 0.78
    assert canon[0].expressions[0].values[0]["value"] == 1.0
    
    assert canon[1].pitch == 60  # default
    assert canon[1].time.beats == 4.0  # measure 2 (4/4) -> beat 4.0
    assert canon[1].expressions[0].values[0]["value"] == 0.5  # low confidence

def test_note_transposition_math() -> None:
    from rhythm_vibe_mcp.theory.pitch import Note, Interval
    n1 = Note.from_name("C4")
    n2 = n1 + Interval.PERFECT_FIFTH
    assert n2.name() == "G4"
    assert n2 - n1 == 7
    
    n3 = Note.from_name("G#5")
    assert n3.pitch_class == 8
    assert n3.octave == 5
