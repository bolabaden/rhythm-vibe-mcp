from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from lilycode_mcp.http_constants import DOWNLOAD_REQUEST_TIMEOUT, HEADER_CONTENT_TYPE
from lilycode_mcp.path_constants import DOWNLOAD_FALLBACK_FILENAME
from lilycode_mcp.utils import artifacts_dir, ensure_dir


def _extension_from_content_type(content_type: str) -> str:
    from lilycode_mcp.content_type_map import extension_from_content_type

    return extension_from_content_type(content_type)


def download_music_asset(url: str, out_dir: Path | None = None) -> Path:
    out_dir = ensure_dir(out_dir or artifacts_dir())
    parsed = urlparse(url)
    raw_name = Path(parsed.path).name
    filename = raw_name if raw_name and "." in raw_name else DOWNLOAD_FALLBACK_FILENAME

    with httpx.Client(timeout=DOWNLOAD_REQUEST_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        if "." not in filename:
            inferred_ext = _extension_from_content_type(resp.headers.get(HEADER_CONTENT_TYPE, ""))
            if inferred_ext:
                filename = f"{DOWNLOAD_FALLBACK_FILENAME.removesuffix('.bin')}{inferred_ext}"
        output = out_dir / filename
        output.write_bytes(resp.content)
    return output
