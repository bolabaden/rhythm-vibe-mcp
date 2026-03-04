"""
Pytest configuration and shared fixtures for rhythm-vibe-mcp.

Best practices applied:
- asyncio_mode = "auto" (pyproject.toml) so async tests run without per-test decorators.
- Fixtures for isolated temp dirs and sample files to avoid touching real filesystem.
- No client-in-fixture pattern for MCP Client (instantiate inside each test to avoid event-loop issues).
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workdir(tmp_path: Path) -> Path:
    """Isolated workspace root for artifact and conversion tests."""
    return tmp_path


@pytest.fixture
def monkeypatch_workdir(monkeypatch: pytest.MonkeyPatch, tmp_workdir: Path) -> Path:
    """Set rhythm_vibe_mcp_WORKDIR so artifacts_dir() uses tmp_path."""
    monkeypatch.setenv("rhythm_vibe_mcp_WORKDIR", str(tmp_workdir))
    return tmp_workdir


@pytest.fixture
def sample_lilypond(tmp_path: Path) -> Path:
    """Minimal valid LilyPond file."""
    content = r"""
\version "2.24.0"
\score {
  { c'4 d' e' f' }
  \layout { }
  \midi { }
}
"""
    p = tmp_path / "sample.ly"
    p.write_text(content.strip(), encoding="utf-8")
    return p


@pytest.fixture
def sample_abc(tmp_path: Path) -> Path:
    """Minimal ABC notation file."""
    content = """
X:1
T:Sample
M:4/4
K:C
C D E F|G A B c|
"""
    p = tmp_path / "sample.abc"
    p.write_text(content.strip(), encoding="utf-8")
    return p


@pytest.fixture
def sample_chordpro(tmp_path: Path) -> Path:
    """Minimal ChordPro snippet (content only)."""
    content = "{title: Test Song}\n[C]Hello [G]world"
    p = tmp_path / "sample.cho"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def sample_midi_minimal(tmp_path: Path) -> Path:
    """Minimal MIDI file (header + one track chunk) for music21/converter tests."""
    # Minimal MIDI: header (14 bytes) + track chunk with end-of-track meta
    header = bytes([
        0x4D, 0x54, 0x68, 0x64, 0x00, 0x00, 0x00, 0x06,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x60,
        0x4D, 0x54, 0x72, 0x6B, 0x00, 0x00, 0x00, 0x04,
        0x00, 0xFF, 0x2F, 0x00,
    ])
    p = tmp_path / "minimal.mid"
    p.write_bytes(header)
    return p


@pytest.fixture
def sample_musicxml_minimal(tmp_path: Path) -> Path:
    """Minimal MusicXML fragment for parser tests."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Part 1</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note></measure></part>
</score-partwise>
"""
    p = tmp_path / "minimal.musicxml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def sample_json_fallback(tmp_path: Path) -> Path:
    """Pre-built fallback JSON for round-trip style tests."""
    content = """{"title": "fixture", "notation_hint": "abc", "shorthand_text": "X:1\\nK:C\\nC", "events": [], "warnings": []}"""
    p = tmp_path / "fallback.json"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _reset_musescore_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset MuseScore env in tests unless a test explicitly sets it."""
    monkeypatch.delenv("MUSESCORE_API_TOKEN", raising=False)
    monkeypatch.delenv("MUSESCORE_API_BASE", raising=False)
