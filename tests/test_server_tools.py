"""
Tests for MCP server tool contract: tools return JSON strings and handle errors.

Tools are invoked as plain functions (the same handler code the MCP server runs)
so tests stay fast and deterministic. External I/O (fetch, convert) is mocked
where needed. For protocol-layer validation (list_tools, call_tool through the
MCP interaction layer), see test_mcp_integration.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from rhythm_vibe_mcp.server import (
    _SESSION_STATE,
    audio_or_file_to_sheet,
    batch_convert_audio,
    compose_story_lily,
    convert_music,
    convert_text_notation_to_lily_or_fallback,
    fetch_music_from_web,
    healthcheck,
    musescore_api,
    normalize_reddit_music_text,
    plan_music_conversion,
    set_musescore_auth_token,
    transpose_song,
)


def _parse_tool_output(out: str) -> dict:
    """All tools return JSON string; parse for assertions."""
    return json.loads(out)


class TestHealthcheck:
    """healthcheck() returns diagnostics JSON per README: workdir, artifacts_dir, MuseScore env, binary availability."""

    def test_returns_valid_json(self) -> None:
        out = healthcheck()
        data = _parse_tool_output(out)
        assert "workdir" in data or "artifacts_dir" in data
        assert "musescore_auth_env_present" in data

    def test_returns_all_documented_keys(self) -> None:
        """README: workdir, artifacts_dir, MuseScore env, lilypond_available, ffmpeg_available."""
        out = healthcheck()
        data = _parse_tool_output(out)
        assert "workdir" in data
        assert "artifacts_dir" in data
        assert "musescore_auth_env_present" in data
        assert "lilypond_available" in data
        assert "ffmpeg_available" in data

    def test_musescore_env_reflected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MUSESCORE_API_TOKEN", "x")
        out = healthcheck()
        data = _parse_tool_output(out)
        assert data.get("musescore_auth_env_present") is True


class TestPlanMusicConversion:
    """plan_music_conversion(input_format, output_format) returns route or error."""

    def test_returns_route(self) -> None:
        out = plan_music_conversion("midi", "pdf")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert "route" in data
        assert data["route"][0] == "midi"
        assert data["route"][-1] == "pdf"

    def test_no_route_returns_ok_false(self) -> None:
        out = plan_music_conversion("unknown_format", "pdf")
        data = _parse_tool_output(out)
        assert data["ok"] is False
        assert "message" in data

    def test_no_route_includes_hint(self) -> None:
        out = plan_music_conversion("unknown_format", "pdf")
        data = _parse_tool_output(out)
        assert data["ok"] is False
        assert "hint" in data
        assert "abc" in data["hint"].lower() or "format" in data["hint"].lower()

    def test_alias_format_route(self) -> None:
        out = plan_music_conversion("aiff", "lilypond")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert data["route"][0] == "wav"
        assert data["route"][-1] == "lilypond"


class TestNormalizeRedditMusicText:
    """normalize_reddit_music_text(text, title) returns ToolResult-shaped JSON with fallback."""

    def test_abc_detected(self) -> None:
        out = normalize_reddit_music_text("X:1\nK:C\nC D E F", title="tune")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert data.get("fallback") is not None
        assert data["fallback"]["notation_hint"] == "abc"

    def test_freeform_returns_fallback(self) -> None:
        out = normalize_reddit_music_text("try playing C and G", title="idea")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert "fallback" in data
        assert "events" in data["fallback"] or "shorthand_text" in data["fallback"]


class TestConvertTextNotationToLilyOrFallback:
    """convert_text_notation_to_lily_or_fallback returns JSON (ToolResult or fallback)."""

    def test_returns_valid_json(self) -> None:
        out = convert_text_notation_to_lily_or_fallback(
            "C D E", target_format="lilypond"
        )
        data = _parse_tool_output(out)
        assert "ok" in data or "fallback" in data or "notation_hint" in data


class TestComposeStoryLily:
    """compose_story_lily returns a generated lilypond artifact."""

    def test_generates_lilypond_file(self, monkeypatch_workdir: Path) -> None:
        out = compose_story_lily(
            prompt="A quiet landscape that grows gradually more hopeful.",
            title="Test Piece",
            tempo_bpm=56,
        )
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert data["artifacts"][0]["format"] == "lilypond"
        artifact = Path(data["artifacts"][0]["path"])
        assert artifact.exists()
        content = artifact.read_text(encoding="utf-8")
        assert "\\clef" in content
        assert "instrumentName" in content or "instrument" in content

    def test_instrument_param_produces_cello_clef(
        self, monkeypatch_workdir: Path
    ) -> None:
        out = compose_story_lily(
            prompt="Test.",
            title="Cello Test",
            instrument="Cello",
        )
        data = _parse_tool_output(out)
        assert data["ok"] is True
        content = Path(data["artifacts"][0]["path"]).read_text(encoding="utf-8")
        assert "\\clef bass" in content
        assert "Cello" in content
        assert "cello" in content.lower()

    def test_violin_uses_treble_clef(self, monkeypatch_workdir: Path) -> None:
        out = compose_story_lily(
            prompt="Test.",
            title="Violin Test",
            instrument="Violin",
        )
        data = _parse_tool_output(out)
        assert data["ok"] is True
        content = Path(data["artifacts"][0]["path"]).read_text(encoding="utf-8")
        assert "\\clef treble" in content
        assert "Violin" in content


class TestSetMusescoreAuthToken:
    """Session token can be set and used by musescore_api."""

    def test_sets_session_token(self) -> None:
        _SESSION_STATE.clear()
        out = set_musescore_auth_token("test_token_123")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert _SESSION_STATE.get("musescore_token") == "test_token_123"

    def test_token_stripped(self) -> None:
        _SESSION_STATE.clear()
        set_musescore_auth_token("  tok  ")
        assert _SESSION_STATE["musescore_token"] == "tok"


class TestMusescoreApi:
    """musescore_api proxies to musescore_api_request; invalid payload returns error."""

    def test_invalid_payload_json_returns_error(self) -> None:
        out = musescore_api("scores", payload_json="not json")
        data = _parse_tool_output(out)
        assert data.get("ok") is False or "Invalid" in data.get("message", "")

    def test_success_mocked(self) -> None:
        with patch("rhythm_vibe_mcp.server.musescore_api_request") as mock_req:
            mock_req.return_value = {
                "ok": True,
                "json": {"scores": []},
                "status_code": 200,
            }
            out = musescore_api("scores", method="GET", payload_json="{}")
            data = _parse_tool_output(out)
            assert data.get("ok") is True
            assert data.get("json", {}).get("scores") == []


class TestFetchMusicFromWeb:
    """fetch_music_from_web(url) downloads and returns artifact JSON."""

    def test_success_returns_artifact_json(self, monkeypatch_workdir: Path) -> None:
        with patch("rhythm_vibe_mcp.server.download_music_asset") as mock_dl:
            mock_dl.return_value = monkeypatch_workdir / "downloaded.mid"
            (monkeypatch_workdir / "downloaded.mid").write_bytes(b"\x00\x01")
            out = fetch_music_from_web("https://example.com/song.mid")
            data = _parse_tool_output(out)
            assert data["ok"] is True
            assert data["message"] == "download success"
            assert len(data["artifacts"]) == 1
            assert data["artifacts"][0]["format"] == "midi"
            mock_dl.assert_called_once_with("https://example.com/song.mid")

    def test_fetch_failure_returns_structured_error(self) -> None:
        with patch("rhythm_vibe_mcp.server.download_music_asset") as mock_dl:
            mock_dl.side_effect = Exception("403 Forbidden")
            out = fetch_music_from_web("https://example.com/forbidden.mid")
            data = _parse_tool_output(out)
            assert data["ok"] is False
            assert "message" in data
            assert "403" in data["message"] or "fetch failed" in data["message"]


class TestConvertMusic:
    """convert_music(input_ref, output_format) with local path; external convert_any mocked or real."""

    def test_missing_file_returns_error_json(self) -> None:
        out = convert_music("/nonexistent/path/file.mid", "pdf")
        data = _parse_tool_output(out)
        assert data["ok"] is False
        assert (
            "input" in data["message"].lower()
            or "exist" in data["message"].lower()
            or "error" in data["message"].lower()
        )

    def test_real_file_returns_ok_or_fallback(
        self, sample_midi_minimal: Path, monkeypatch_workdir: Path
    ) -> None:
        out = convert_music(str(sample_midi_minimal), "musicxml")
        data = _parse_tool_output(out)
        assert "ok" in data
        assert "message" in data
        if data["ok"]:
            assert "artifacts" in data
        else:
            assert data.get("fallback") is not None or "message" in data


class TestTransposeSong:
    """transpose_song(input_ref, semitones, output_format)."""

    def test_missing_file_returns_error(self) -> None:
        out = transpose_song("/nonexistent/file.mid", 2)
        data = _parse_tool_output(out)
        assert data["ok"] is False

    def test_real_file_succeeds(
        self, sample_midi_minimal: Path, monkeypatch_workdir: Path
    ) -> None:
        out = transpose_song(str(sample_midi_minimal), 0, output_format="musicxml")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert len(data.get("artifacts", [])) >= 1


class TestAudioOrFileToSheet:
    """audio_or_file_to_sheet(input_ref, prefer_output) chains conversion."""

    def test_missing_file_returns_error(self) -> None:
        out = audio_or_file_to_sheet("/nonexistent/x.wav", prefer_output="pdf")
        data = _parse_tool_output(out)
        assert data["ok"] is False

    def test_notation_file_to_sheet(
        self, sample_midi_minimal: Path, monkeypatch_workdir: Path
    ) -> None:
        out = audio_or_file_to_sheet(str(sample_midi_minimal), prefer_output="musicxml")
        data = _parse_tool_output(out)
        assert data["ok"] is True
        assert data.get("artifacts")


class TestBatchConvertAudio:
    """batch_convert_audio(input_ref) returns JSON and handles missing files."""

    def test_missing_file_returns_error(self) -> None:
        out = batch_convert_audio("/nonexistent/path/audio.m4a")
        data = _parse_tool_output(out)
        assert data["ok"] is False
        assert "input" in data.get("message", "").lower() or "exist" in data.get(
            "message",
            "",
        ).lower()
