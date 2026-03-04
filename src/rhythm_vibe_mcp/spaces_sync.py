from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen


API_BASE = "https://huggingface.co/api/spaces"
REPORT_NAME = "SPACES_MUSIC_REPORT.md"


@dataclass
class SpaceRecord:
    space_id: str
    likes: int
    sdk: str
    app_file: str
    folder_name: str


@dataclass
class SpaceAnalysis:
    has_gradio: bool
    has_transformers: bool
    has_diffusers: bool
    has_torch: bool
    has_audio_processing: bool
    key_files: list[str]


def _run_git(args: list[str], *, cwd: Path | None = None) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {details}")


def _fetch_spaces(query: str, *, limit: int) -> list[SpaceRecord]:
    url = (
        f"{API_BASE}?search={quote(query)}&sort=likes&direction=-1&limit={int(limit)}"
    )
    with urlopen(url) as response:
        raw = json.load(response)

    rows: list[SpaceRecord] = []
    for item in raw:
        space_id = str(item.get("id", "")).strip()
        if not space_id or "/" not in space_id:
            continue
        likes = int(item.get("likes", 0) or 0)
        sdk = str(item.get("sdk", "") or "")
        app_file = str(item.get("app_file", "") or "")
        rows.append(
            SpaceRecord(
                space_id=space_id,
                likes=likes,
                sdk=sdk,
                app_file=app_file,
                folder_name=space_id.replace("/", "__"),
            ),
        )
    return rows


def _sync_space(space: SpaceRecord, dest_dir: Path, *, update_existing: bool) -> Path:
    local_path = dest_dir / space.folder_name
    remote_url = f"https://huggingface.co/spaces/{space.space_id}"

    if local_path.exists():
        if update_existing:
            _run_git(["-C", str(local_path), "pull", "--ff-only"])
        return local_path

    _run_git(["clone", remote_url, str(local_path)])
    return local_path


def _analyze_space(local_path: Path) -> SpaceAnalysis:
    key_file_candidates = [
        "app.py",
        "README.md",
        "requirements.txt",
        "demos/musicgen_app.py",
    ]
    key_files = [name for name in key_file_candidates if (local_path / name).exists()]

    combined_text_parts: list[str] = []
    for file_name in key_files:
        file_path = local_path / file_name
        try:
            combined_text_parts.append(file_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
    combined = "\n".join(combined_text_parts).lower()

    return SpaceAnalysis(
        has_gradio=("gradio" in combined),
        has_transformers=("transformers" in combined),
        has_diffusers=("diffusers" in combined),
        has_torch=("torch" in combined),
        has_audio_processing=("pydub" in combined or "ffmpeg" in combined or "torchaudio" in combined),
        key_files=key_files,
    )


def _render_report(
    *,
    spaces: list[SpaceRecord],
    analyses: dict[str, SpaceAnalysis],
    query: str,
) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = []
    lines.append("# Hugging Face Spaces — Music Generative Snapshot")
    lines.append("")
    lines.append(f"Generated: {generated}  ")
    lines.append(
        f"Query basis: `https://huggingface.co/api/spaces?search={query}&sort=likes&direction=-1`",
    )
    lines.append("")
    lines.append("## Selected top popular music-generative Spaces (synced)")
    lines.append("")
    lines.append("| Rank | Space ID | Likes (at fetch time) | SDK | Local folder |")
    lines.append("|---|---|---:|---|---|")
    for index, space in enumerate(spaces, start=1):
        lines.append(
            "| "
            f"{index} | `{space.space_id}` | {space.likes} | {space.sdk or 'unknown'} | "
            f"`vendor/huggingface_spaces/{space.folder_name}` |",
        )

    lines.append("")
    lines.append("## What these Spaces include (automated quick profile)")
    lines.append("")
    lines.append("| Space | Key files | Gradio | Transformers | Diffusers | Torch | Audio tooling |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for space in spaces:
        analysis = analyses[space.space_id]
        key_files_text = ", ".join(analysis.key_files) if analysis.key_files else "none"
        lines.append(
            "| "
            f"`{space.space_id}` | {key_files_text} | "
            f"{'yes' if analysis.has_gradio else 'no'} | "
            f"{'yes' if analysis.has_transformers else 'no'} | "
            f"{'yes' if analysis.has_diffusers else 'no'} | "
            f"{'yes' if analysis.has_torch else 'no'} | "
            f"{'yes' if analysis.has_audio_processing else 'no'} |",
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Ranking is by current likes from the Hugging Face Spaces API.")
    lines.append("- This report is regenerated by the sync command and may change over time.")
    lines.append("- Local folders are git clones of Space repos under `vendor/huggingface_spaces`.")
    lines.append("")
    return "\n".join(lines)


def _prune_old_dirs(dest_dir: Path, keep_folder_names: set[str]) -> list[Path]:
    removed: list[Path] = []
    for child in dest_dir.iterdir():
        if child.name == REPORT_NAME:
            continue
        if child.is_dir() and child.name not in keep_folder_names:
            shutil.rmtree(child)
            removed.append(child)
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rhythm-vibe-refresh-spaces")
    parser.add_argument("--query", default="music")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--dest",
        default="vendor/huggingface_spaces",
        help="Destination folder for synced Space repos and report.",
    )
    parser.add_argument(
        "--skip-update-existing",
        action="store_true",
        help="Do not pull updates for already cloned Space repos.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete local Space dirs in destination that are not in current top-N.",
    )
    args = parser.parse_args(argv)

    if args.top_n <= 0:
        raise ValueError("--top-n must be > 0")
    if args.limit <= 0:
        raise ValueError("--limit must be > 0")

    dest_dir = Path(args.dest).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    all_spaces = _fetch_spaces(args.query, limit=args.limit)
    selected = all_spaces[: args.top_n]

    analyses: dict[str, SpaceAnalysis] = {}
    for space in selected:
        local_path = _sync_space(
            space,
            dest_dir,
            update_existing=not args.skip_update_existing,
        )
        analyses[space.space_id] = _analyze_space(local_path)

    if args.prune:
        keep = {space.folder_name for space in selected}
        _prune_old_dirs(dest_dir, keep)

    report = _render_report(spaces=selected, analyses=analyses, query=args.query)
    (dest_dir / REPORT_NAME).write_text(report, encoding="utf-8")

    print(f"Synced {len(selected)} spaces to: {dest_dir}")
    print(f"Report written: {dest_dir / REPORT_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
