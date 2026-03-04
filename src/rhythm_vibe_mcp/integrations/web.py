from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlparse

import httpx

from rhythm_vibe_mcp.constants.http import DOWNLOAD_REQUEST_TIMEOUT, HEADER_CONTENT_TYPE
from rhythm_vibe_mcp.constants.paths import DOWNLOAD_FALLBACK_FILENAME
from rhythm_vibe_mcp.utils import artifacts_dir, ensure_dir


def _extension_from_content_type(content_type: str) -> str:
    from rhythm_vibe_mcp.constants.content_types import extension_from_content_type

    return extension_from_content_type(content_type)


class AssetDownloader(ABC):
    """Abstract downloader interface for external music assets."""

    @abstractmethod
    def download(self, url: str, out_dir: Path | None = None) -> Path:
        """Download a URL into an output directory and return resulting path."""


class HttpxAssetDownloader(AssetDownloader):
    """HTTP downloader implementation backed by httpx."""

    def __init__(
        self,
        *,
        timeout: float = DOWNLOAD_REQUEST_TIMEOUT,
        follow_redirects: bool = True,
    ) -> None:
        self.timeout = timeout
        self.follow_redirects = follow_redirects

    def download(self, url: str, out_dir: Path | None = None) -> Path:
        out_dir = ensure_dir(out_dir or artifacts_dir())
        parsed = urlparse(url)
        raw_name = Path(parsed.path).name
        filename = (
            raw_name if raw_name and "." in raw_name else DOWNLOAD_FALLBACK_FILENAME
        )

        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=self.follow_redirects,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            if "." not in filename:
                inferred_ext = _extension_from_content_type(
                    resp.headers.get(HEADER_CONTENT_TYPE, ""),
                )
                if inferred_ext:
                    filename = (
                        f"{DOWNLOAD_FALLBACK_FILENAME.removesuffix('.bin')}{inferred_ext}"
                    )
            output = out_dir / filename
            output.write_bytes(resp.content)
        return output


_default_downloader: AssetDownloader = HttpxAssetDownloader()


def download_music_asset(url: str, out_dir: Path | None = None) -> Path:
    """Functional compatibility wrapper for the default AssetDownloader."""
    return _default_downloader.download(url=url, out_dir=out_dir)
