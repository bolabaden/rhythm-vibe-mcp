"""
Unit tests for utility functions: format detection, path helpers, and command execution.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from rhythm_vibe_mcp.utils import (
    artifacts_dir,
    binary_available,
    ensure_dir,
    guess_format,
    looks_like_abc,
    looks_like_chordpro,
    run_cmd,
    workspace_root,
)


class TestEnsureDir:
    def test_creates_nested_dir(self, tmp_path: Path) -> None:
        p = tmp_path / "a" / "b" / "c"
        out = ensure_dir(p)
        assert out.exists()
        assert out.is_dir()
        assert out == p

    def test_idempotent(self, tmp_path: Path) -> None:
        p = tmp_path / "exists"
        p.mkdir()
        out = ensure_dir(p)
        assert out == p


class TestWorkspaceRoot:
    def test_default_is_cwd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("rhythm_vibe_mcp_WORKDIR", raising=False)
        root = workspace_root()
        assert root.is_absolute()
        assert root.exists()

    def test_respects_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("rhythm_vibe_mcp_WORKDIR", str(tmp_path))
        root = workspace_root()
        assert root == tmp_path.resolve()


class TestArtifactsDir:
    def test_under_workdir(self, monkeypatch_workdir: Path) -> None:
        ad = artifacts_dir()
        assert ad == monkeypatch_workdir / "artifacts"
        assert ad.exists()


class TestGuessFormat:
    @pytest.mark.parametrize(
        "ext,expected",
        [
            (".ly", "lilypond"),
            (".pdf", "pdf"),
            (".musicxml", "musicxml"),
            (".xml", "musicxml"),
            (".midi", "midi"),
            (".mid", "midi"),
            (".wav", "wav"),
            (".mp3", "mp3"),
            (".m4a", "m4a"),
            (".aiff", "wav"),
            (".flac", "wav"),
            (".caf", "wav"),
            (".adts", "m4a"),
            (".abc", "abc"),
            (".cho", "chordpro"),
            (".chopro", "chordpro"),
            (".pro", "chordpro"),
            (".json", "json_fallback"),
        ],
    )
    def test_known_extensions(self, ext: str, expected: str, tmp_path: Path) -> None:
        p = tmp_path / f"file{ext}"
        p.touch()
        assert guess_format(p) == expected

    def test_unknown_extension_defaults_to_json_fallback(self, tmp_path: Path) -> None:
        p = tmp_path / "file.xyz"
        p.touch()
        assert guess_format(p) == "json_fallback"

    def test_case_insensitive(self, tmp_path: Path) -> None:
        p = tmp_path / "file.MID"
        p.touch()
        assert guess_format(p) == "midi"


class TestBinaryAvailable:
    def test_returns_bool(self) -> None:
        out = binary_available("python")
        assert isinstance(out, bool)

    @patch("rhythm_vibe_mcp.utils.shutil.which")
    def test_uses_which(self, mock_which: object) -> None:
        mock_which.return_value = "/usr/bin/foo"
        assert binary_available("foo") is True
        mock_which.return_value = None
        assert binary_available("nonexistent") is False


class TestRunCmd:
    def test_capture_stdout_stderr(self) -> None:
        code, out, err = run_cmd(["python", "-c", "print('hi'); import sys; print('err', file=sys.stderr)"])
        assert code == 0
        assert "hi" in out
        assert "err" in err

    def test_nonzero_exit(self) -> None:
        code, out, err = run_cmd(["python", "-c", "import sys; sys.exit(3)"])
        assert code == 3

    def test_cwd(self, tmp_path: Path) -> None:
        code, out, err = run_cmd(["python", "-c", "import os; print(os.getcwd())"], cwd=tmp_path)
        assert code == 0
        assert str(tmp_path) in out or tmp_path.name in out


class TestLooksLikeAbc:
    def test_has_header_at_line_start(self) -> None:
        assert looks_like_abc("X:1\nT:Title\nK:C\n") is True
        assert looks_like_abc("M:4/4\nK:G\n") is True
        assert looks_like_abc("K:C\nC D E F") is True

    def test_pitch_only_without_header_not_abc(self) -> None:
        # Conservative: no line-start header -> not ABC (avoids "random text" false positive)
        assert looks_like_abc("C D E F G A B c") is False
        assert looks_like_abc("A B c d e") is False

    def test_plain_text_no_abc(self) -> None:
        assert looks_like_abc("Hello world random text") is False
        assert looks_like_abc("{title: Song}\n[C]Hello") is False
        assert looks_like_abc("") is False


class TestLooksLikeChordpro:
    def test_chord_brackets(self) -> None:
        assert looks_like_chordpro("[C] hello [G] world") is True
        assert looks_like_chordpro("[Am] verse [Fmaj7]") is True

    def test_title_directive(self) -> None:
        assert looks_like_chordpro("{title: My Song}") is True

    def test_plain_text(self) -> None:
        assert looks_like_chordpro("Just lyrics no chords") is False
