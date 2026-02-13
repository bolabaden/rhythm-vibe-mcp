"""
Unit tests for fallback representation: ABC/ChordPro detection and error fallbacks.
"""

from __future__ import annotations

from lilycode_mcp.fallbacks import fallback_from_error, fallback_from_text


class TestFallbackFromText:
    def test_abc_detection(self) -> None:
        text = "X:1\nT:Test\nK:C\nC D E F"
        f = fallback_from_text(text, title="abc_tune")
        assert f.notation_hint == "abc"
        assert f.title == "Test"  # T: header overrides title param
        assert f.tonic == "C"
        assert "X:1" in f.shorthand_text
        assert len(f.events) >= 1
        assert any("ABC" in w or "convert" in w.lower() for w in f.warnings)

    def test_chordpro_detection(self) -> None:
        text = "{title: Song}\n[C]Hello [G]world"
        f = fallback_from_text(text, title="chord_song")
        assert f.notation_hint == "chordpro"
        assert f.title == "Song"
        assert "[C]" in f.shorthand_text
        assert len(f.events) >= 2
        assert any(e.pitch == "C" for e in f.events)
        assert any(e.pitch == "G" for e in f.events)

    def test_freeform_fallback(self) -> None:
        # Use text without ABC headers or 4+ pitch letters (avoid "playing" matching as ABC)
        text = "try playing the notes C and D and E"
        f = fallback_from_text(text, title="reddit_idea")
        assert f.notation_hint == "freeform"
        assert len(f.events) >= 3  # C, D, E extracted
        pitches = {e.pitch for e in f.events}
        assert "C" in pitches
        assert "D" in pitches
        assert "E" in pitches

    def test_empty_title_default(self) -> None:
        f = fallback_from_text("X:1\nK:C", title="untitled")
        assert f.title == "untitled"  # no T: header so param used

    def test_events_only_letter_pitches(self) -> None:
        f = fallback_from_text("A B C D E F G and more words")
        assert len(f.events) == 7
        assert {e.pitch for e in f.events} == {"A", "B", "C", "D", "E", "F", "G"}


class TestFallbackFromError:
    def test_minimal(self) -> None:
        f = fallback_from_error(title="err", warning="something broke")
        assert f.title == "err"
        assert f.notation_hint == "unknown"
        assert f.shorthand_text == ""
        assert f.warnings == ["something broke"]
        assert f.events == []

    def test_with_shorthand(self) -> None:
        f = fallback_from_error(
            title="ly_fail",
            warning="parse error",
            shorthand_text="\\score { c'4 }",
        )
        assert "\\score" in f.shorthand_text
        assert f.warnings == ["parse error"]
