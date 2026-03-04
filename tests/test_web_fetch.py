"""Unit tests for web fetch: download_music_asset with mocked HTTP."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from rhythm_vibe_mcp.integrations.web import download_music_asset


class TestDownloadMusicAsset:
    def test_downloads_to_artifacts_dir(self, monkeypatch_workdir: Path) -> None:
        fake_content = b"fake midi or binary content"
        with patch("rhythm_vibe_mcp.integrations.web.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = fake_content
            mock_resp.raise_for_status = lambda: None
            mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp

            out = download_music_asset("https://example.com/song.mid", out_dir=monkeypatch_workdir)
            assert out == monkeypatch_workdir / "song.mid"
            assert out.exists()
            assert out.read_bytes() == fake_content

    def test_url_without_filename_uses_default(self, monkeypatch_workdir: Path) -> None:
        with patch("rhythm_vibe_mcp.integrations.web.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"data"
            mock_resp.raise_for_status = lambda: None
            mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp

            out = download_music_asset("https://example.com/api/stream", out_dir=monkeypatch_workdir)
            assert out.exists()
            assert "downloaded_music_asset" in out.name or out.suffix == ".bin"

    def test_uses_provided_out_dir(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "custom_downloads"
        custom_dir.mkdir()
        with patch("rhythm_vibe_mcp.integrations.web.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"x"
            mock_resp.raise_for_status = lambda: None
            mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp

            out = download_music_asset("https://example.com/f.x", out_dir=custom_dir)
            assert out.parent == custom_dir
            assert out.exists()
