from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from rhythm_vibe_mcp.constants.binaries import FFMPEG_BINARY
from rhythm_vibe_mcp.utils import binary_available

TOP_AUDIO_FORMATS: tuple[str, ...] = (
    "mp3",
    "wav",
    "flac",
    "ogg",
    "aac",
    "m4a",
    "wma",
    "aiff",
    "opus",
    "alac",
    "amr",
    "au",
    "ac3",
    "dts",
    "ra",
    "rm",
    "voc",
    "spx",
    "caf",
    "wv",
    "tta",
    "mp2",
    "dsf",
    "dff",
    "adts",
)

ENCODER_ARGS: dict[str, list[str]] = {
    "mp3": ["-c:a", "libmp3lame"],
    "ogg": ["-c:a", "libvorbis"],
    "opus": ["-c:a", "libopus"],
    "aac": ["-c:a", "aac"],
    "m4a": ["-c:a", "aac"],
    "adts": ["-c:a", "aac"],
    "alac": ["-c:a", "alac"],
    "flac": ["-c:a", "flac"],
    "wma": ["-c:a", "wmav2"],
    "amr": ["-ar", "8000", "-c:a", "libopencore_amrnb"],
    "spx": ["-c:a", "libspeex"],
}


def _format_output_path(input_path: Path, output_dir: Path, fmt: str) -> Path:
    if fmt == "alac":
        return output_dir / f"{input_path.stem}.m4a"
    if fmt == "adts":
        return output_dir / f"{input_path.stem}.aac"
    return output_dir / f"{input_path.stem}.{fmt}"


def _resolve_output_dir(input_path: Path) -> Path:
    expected_name = f"{input_path.stem}_formats".lower()
    if input_path.parent.name.lower() == expected_name:
        return input_path.parent
    return input_path.parent / f"{input_path.stem}_formats"


def _convert_one(input_path: Path, output_path: Path, fmt: str) -> dict[str, Any]:
    encoder_args = ENCODER_ARGS.get(fmt, [])
    cmd = [
        FFMPEG_BINARY,
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        *encoder_args,
        str(output_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception as exc:
        return {
            "format": fmt,
            "status": "failed",
            "error": str(exc),
        }

    if proc.returncode != 0 and encoder_args:
        retry_cmd = [
            FFMPEG_BINARY,
            "-hide_banner",
            "-y",
            "-i",
            str(input_path),
            str(output_path),
        ]
        proc = subprocess.run(
            retry_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )

    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        return {
            "format": fmt,
            "status": "failed",
            "error": f"returncode {proc.returncode}",
            "details": err.splitlines()[-1] if err else "ffmpeg conversion failed",
        }

    return {
        "format": fmt,
        "path": str(output_path),
        "status": "success",
    }


def batch_convert_audio_formats(input_path: Path) -> dict[str, Any]:
    if not binary_available(FFMPEG_BINARY):
        return {"ok": False, "message": "ffmpeg not found. Cannot convert audio."}

    if not input_path.exists():
        return {"ok": False, "message": f"Input file not found: {input_path}"}

    output_dir = _resolve_output_dir(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for fmt in TOP_AUDIO_FORMATS:
        out = _format_output_path(input_path, output_dir, fmt)
        results.append(_convert_one(input_path, out, fmt))

    succeeded = sum(1 for row in results if row.get("status") == "success")
    total = len(TOP_AUDIO_FORMATS)
    return {
        "ok": True,
        "message": f"Conversion finished: {succeeded}/{total} succeeded",
        "output_directory": str(output_dir),
        "attempted_formats": list(TOP_AUDIO_FORMATS),
        "results": results,
    }
