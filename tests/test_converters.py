"""
Unit tests for conversion pipeline: route planning, single-step conversion, and fallback behavior.

External binaries (lilypond, ffmpeg) and optional deps (music21, basic_pitch) are mocked
so tests are deterministic and do not require system tools.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lilycode_mcp.converters import (
    compile_lilypond_to_pdf,
    convert_any,
    convert_audio_container,
    convert_with_music21,
    normalize_text_to_fallback,
    plan_conversion_route,
    transpose_with_music21,
)
from lilycode_mcp.fallbacks import fallback_from_error
from lilycode_mcp.models import ToolResult


class TestPlanConversionRoute:
    """Route planning is pure logic; no mocks needed."""

    @pytest.mark.parametrize(
        "source,target,expected_first_last",
        [
            ("midi", "midi", ["midi"]),
            ("lilypond", "pdf", ["lilypond", "pdf"]),
            ("musicxml", "abc", ["musicxml", "abc"]),
            ("midi", "musicxml", ["midi", "musicxml"]),
            ("wav", "mp3", ["wav", "mp3"]),
            ("abc", "lilypond", ["abc", "lilypond"]),
            ("mp3", "pdf", ["mp3", "midi", "musicxml", "pdf"]),
        ],
    )
    def test_route_exists(
        self,
        source: str,
        target: str,
        expected_first_last: list[str],
    ) -> None:
        route = plan_conversion_route(source, target)
        assert len(route) >= 1
        assert route[0] == expected_first_last[0]
        assert route[-1] == expected_first_last[-1]

    def test_same_format_returns_single_step(self) -> None:
        assert plan_conversion_route("pdf", "pdf") == ["pdf"]
        assert plan_conversion_route("midi", "midi") == ["midi"]

    def test_unknown_source_still_searches(self) -> None:
        route = plan_conversion_route("unknown_format", "json_fallback")
        # unknown not in graph, so no route
        assert route == []

    def test_case_insensitive(self) -> None:
        assert plan_conversion_route("MIDI", "MusicXML") == ["midi", "musicxml"]


class TestCompileLilypondToPdf:
    """LilyPond compile: missing binary or failed run returns fallback."""

    def test_lilypond_missing_returns_fallback(
        self,
        sample_lilypond: Path,
        monkeypatch_workdir: Path,
    ) -> None:
        with patch("lilycode_mcp.converters.binary_available", return_value=False):
            result = compile_lilypond_to_pdf(sample_lilypond)
        assert result.ok is False
        assert "lilypond" in result.message.lower()
        assert result.fallback is not None, result.message
        assert (
            "lilypond" in result.fallback.warnings[0].lower()
            or "installed" in result.fallback.warnings[0].lower()
        )
        assert len(result.fallback.shorthand_text) > 0

    def test_lilypond_fails_returns_fallback(
        self,
        sample_lilypond: Path,
        monkeypatch_workdir: Path,
    ) -> None:
        with (
            patch("lilycode_mcp.converters.binary_available", return_value=True),
            patch(
                "lilycode_mcp.converters.run_cmd", return_value=(1, "", "syntax error")
            ),
        ):
            result = compile_lilypond_to_pdf(sample_lilypond)
        assert result.ok is False
        assert result.fallback is not None, result.message
        assert (
            "syntax" in result.fallback.warnings[0]
            or "error" in result.fallback.warnings[0]
        )


class TestConvertAudioContainer:
    """FFmpeg container conversion: missing binary or failure returns fallback."""

    def test_ffmpeg_missing_returns_fallback(
        self,
        tmp_path: Path,
    ) -> None:
        wav = tmp_path / "x.wav"
        wav.write_bytes(b"\x00" * 100)
        with patch("lilycode_mcp.converters.binary_available", return_value=False):
            result = convert_audio_container(wav, "mp3")
        assert result.ok is False
        assert "ffmpeg" in result.message.lower()

    def test_ffmpeg_fails_returns_fallback(
        self, tmp_path: Path, monkeypatch_workdir: Path
    ) -> None:
        wav = tmp_path / "x.wav"
        wav.write_bytes(b"\x00" * 100)
        with (
            patch("lilycode_mcp.converters.binary_available", return_value=True),
            patch(
                "lilycode_mcp.converters.run_cmd", return_value=(1, "", "Invalid data")
            ),
        ):
            result = convert_audio_container(wav, "mp3")
        assert result.ok is False
        assert result.fallback is not None


class TestConvertWithMusic21:
    """Music21 conversion: uses real music21 when available; tests minimal MIDI/MusicXML."""

    @pytest.mark.parametrize("output_format", ["musicxml", "midi"])
    def test_midi_to_notation(
        self,
        sample_midi_minimal: Path,
        monkeypatch_workdir: Path,
        output_format: str,
    ) -> None:
        result = convert_with_music21(sample_midi_minimal, output_format)
        assert result.ok is True, result.message
        assert len(result.artifacts) == 1
        assert result.artifacts[0].format == output_format
        assert Path(result.artifacts[0].path).exists()

    def test_midi_to_lilypond_ok_or_fallback(
        self, sample_midi_minimal: Path, monkeypatch_workdir: Path
    ) -> None:
        """LilyPond export may require system lilypond; accept success or fallback."""
        result = convert_with_music21(sample_midi_minimal, "lilypond")
        assert result.ok is True or result.fallback is not None
        if result.ok:
            assert len(result.artifacts) == 1
            assert result.artifacts[0].format == "lilypond"

    def test_midi_to_abc_ok_or_fallback(
        self, sample_midi_minimal: Path, monkeypatch_workdir: Path
    ) -> None:
        """ABC export can depend on music21 plugins; accept success or fallback."""
        result = convert_with_music21(sample_midi_minimal, "abc")
        assert result.ok is True or result.fallback is not None
        if result.ok:
            assert len(result.artifacts) == 1
            assert result.artifacts[0].format == "abc"

    def test_unsupported_output_returns_fallback(
        self, sample_midi_minimal: Path, monkeypatch_workdir: Path
    ) -> None:
        result = convert_with_music21(sample_midi_minimal, "unknown_format")
        assert result.ok is False
        assert result.fallback is not None


class TestTransposeWithMusic21:
    """Transposition via music21."""

    def test_transpose_success(
        self,
        sample_midi_minimal: Path,
        monkeypatch_workdir: Path,
    ) -> None:
        result = transpose_with_music21(
            sample_midi_minimal,
            semitones=2,
            output_format="musicxml",
        )
        assert result.ok is True
        assert len(result.artifacts) == 1
        assert "transposed" in result.artifacts[0].path

    def test_unsupported_output_format_returns_fallback(
        self,
        sample_midi_minimal: Path,
    ) -> None:
        result = transpose_with_music21(
            sample_midi_minimal,
            semitones=0,
            output_format="wav",
        )
        assert result.ok is False
        assert result.fallback is not None


class TestNormalizeTextToFallback:
    """Normalize text always returns ok with fallback model."""

    def test_returns_ok_with_fallback(self) -> None:
        result = normalize_text_to_fallback("X:1\nK:C\nC D E", title="t")
        assert result.ok is True
        assert result.fallback is not None
        assert result.fallback.notation_hint == "abc"

    def test_message_indicates_normalization(self) -> None:
        result = normalize_text_to_fallback("hello")
        assert (
            "normalized" in result.message.lower()
            or "fallback" in result.message.lower()
        )


class TestConvertAny:
    """End-to-end conversion with route execution; mock external steps."""

    def test_same_format_route_single_step(
        self,
        sample_abc: Path,
        monkeypatch_workdir: Path,
    ) -> None:
        # abc -> abc: route is [abc]; no conversion steps, so ok and message mentions route
        result = convert_any(sample_abc, "abc")
        assert result.ok is True
        assert "abc" in result.message

    def test_no_route_returns_fallback(
        self,
        tmp_path: Path,
    ) -> None:
        bad = tmp_path / "x.xyz"
        bad.touch()
        result = convert_any(bad, "pdf")
        assert result.ok is False
        assert result.fallback is not None

    def test_json_fallback_output_writes_file(
        self,
        sample_chordpro: Path,
        monkeypatch_workdir: Path,
    ) -> None:
        # chordpro -> json_fallback is a direct route (no lilypond/ffmpeg)
        result = convert_any(sample_chordpro, "json_fallback")
        assert result.ok is True
        assert len(result.artifacts) == 1
        assert result.artifacts[0].format == "json_fallback"
        assert Path(result.artifacts[0].path).exists()
        # Fallback may be set by single-step path; multi-step path collects artifacts only
        content = Path(result.artifacts[0].path).read_text(encoding="utf-8")
        assert (
            "title" in content
            or "shorthand_text" in content
            or "notation_hint" in content
        )

    def test_intermediate_step_failure_returns_fallback(
        self,
        sample_midi_minimal: Path,
        monkeypatch_workdir: Path,
    ) -> None:
        failed_result = ToolResult(
            ok=False,
            message="failed",
            fallback=fallback_from_error(
                title=sample_midi_minimal.stem, warning="mock failure"
            ),
        )
        with patch(
            "lilycode_mcp.converters.convert_with_music21", return_value=failed_result
        ):
            result = convert_any(sample_midi_minimal, "pdf")
        assert result.ok is False
        assert result.fallback is not None
        assert "mock" in result.fallback.warnings[0] or "failed" in result.message
