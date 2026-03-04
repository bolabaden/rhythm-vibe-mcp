"""Unit tests for Pydantic models: validation, serialization, and schema stability."""

from __future__ import annotations

import json

from rhythm_vibe_mcp.models import (
    FallbackNoteEvent,
    MusicArtifact,
    RobustMusicFallback,
    ToolResult,
)


class TestMusicArtifact:
    """MusicArtifact model validation and defaults."""

    def test_minimal_valid(self) -> None:
        a = MusicArtifact(path="/tmp/out.pdf", format="pdf")
        assert a.path == "/tmp/out.pdf"
        assert a.format == "pdf"
        assert a.source == "local"
        assert a.notes == []

    def test_full_valid(self) -> None:
        a = MusicArtifact(
            path="/artifacts/song.mid",
            format="midi",
            source="web",
            notes=["transcribed from audio"],
        )
        assert a.source == "web"
        assert "transcribed" in a.notes[0]

    def test_model_dump_roundtrip(self) -> None:
        a = MusicArtifact(path="x.ly", format="lilypond", notes=["a", "b"])
        d = a.model_dump()
        b = MusicArtifact.model_validate(d)
        assert b.path == a.path and b.notes == a.notes


class TestFallbackNoteEvent:
    """FallbackNoteEvent optional fields."""

    def test_minimal(self) -> None:
        e = FallbackNoteEvent(pitch="C", duration="quarter")
        assert e.velocity is None
        assert e.measure is None

    def test_full(self) -> None:
        e = FallbackNoteEvent(
            pitch="F#",
            duration="eighth",
            velocity=80,
            measure=2,
            beat=2.5,
        )
        assert e.velocity == 80
        assert e.beat == 2.5


class TestRobustMusicFallback:
    """RobustMusicFallback as canonical fallback representation."""

    def test_defaults(self) -> None:
        f = RobustMusicFallback()
        assert f.title == "untitled"
        assert f.notation_hint == "unknown"
        assert f.shorthand_text == ""
        assert f.events == []
        assert f.warnings == []

    def test_with_events_and_warnings(self) -> None:
        f = RobustMusicFallback(
            title="failed_convert",
            notation_hint="abc",
            shorthand_text="X:1\nK:C\nC D E",
            events=[
                FallbackNoteEvent(pitch="C", duration="unknown"),
                FallbackNoteEvent(pitch="D", duration="unknown"),
            ],
            warnings=["LilyPond compile failed"],
        )
        assert len(f.events) == 2
        assert "LilyPond" in f.warnings[0]

    def test_json_serialization(self) -> None:
        f = RobustMusicFallback(title="t", notation_hint="chordpro", warnings=["w1"])
        s = f.model_dump_json()
        parsed = json.loads(s)
        assert parsed["title"] == "t"
        assert parsed["notation_hint"] == "chordpro"
        assert parsed["warnings"] == ["w1"]


class TestToolResult:
    """ToolResult as standard tool return shape."""

    def test_success_no_artifacts(self) -> None:
        r = ToolResult(ok=True, message="done")
        assert r.ok is True
        assert r.artifacts == []
        assert r.fallback is None

    def test_failure_with_fallback(self) -> None:
        fallback = RobustMusicFallback(title="err", warnings=["step failed"])
        r = ToolResult(ok=False, message="conversion failed", fallback=fallback)
        assert r.ok is False
        assert r.fallback is not None
        assert r.fallback.title == "err"

    def test_success_with_artifacts(self) -> None:
        r = ToolResult(
            ok=True,
            message="ok",
            artifacts=[
                MusicArtifact(path="/out.pdf", format="pdf"),
                MusicArtifact(path="/out.mid", format="midi"),
            ],
        )
        assert len(r.artifacts) == 2
        assert r.artifacts[1].format == "midi"

    def test_model_dump_for_mcp_response(self) -> None:
        r = ToolResult(
            ok=True,
            message="done",
            artifacts=[MusicArtifact(path="x.ly", format="lilypond")],
        )
        d = r.model_dump()
        assert d["ok"] is True
        assert len(d["artifacts"]) == 1
        assert d["artifacts"][0]["format"] == "lilypond"

class TestProjectManifest:
    def test_project_manifest_defaults(self) -> None:
        from rhythm_vibe_mcp.models import ProjectManifest, ProjectProvenance
        prov = ProjectProvenance(created_at="2026-03-01T12:00:00Z")
        manifest = ProjectManifest(id="proj_123", provenance=prov)
        assert manifest.version == "1.0.0"
        assert manifest.title == "untitled"
        assert len(manifest.tracks) == 0
