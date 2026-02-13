from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_text_input(text: str) -> str:
    """
    Normalize text that may contain literal \\n/\\t from CLI or JSON so ABC/notation parses.
    Idempotent when input already has real newlines.
    """
    from lilycode_mcp.escape_sequences import ESCAPE_TO_CHAR

    if "\\n" in text or "\\t" in text:
        return text.replace("\\n", ESCAPE_TO_CHAR["\\n"]).replace(
            "\\t", ESCAPE_TO_CHAR["\\t"]
        )
    return text


def workspace_root() -> Path:
    from lilycode_mcp.env_constants import DEFAULT_WORKDIR, ENV_WORKDIR

    return Path(os.getenv(ENV_WORKDIR, DEFAULT_WORKDIR)).resolve()


def artifacts_dir() -> Path:
    from lilycode_mcp.path_constants import ARTIFACTS_SUBDIR

    return ensure_dir(workspace_root() / ARTIFACTS_SUBDIR)


def binary_available(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(command: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    from lilycode_mcp.encoding_constants import (
        DEFAULT_TEXT_ENCODING,
        SUBPROCESS_DECODE_ERRORS,
    )

    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding=DEFAULT_TEXT_ENCODING,
        errors=SUBPROCESS_DECODE_ERRORS,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def guess_format(path: Path) -> str:
    from lilycode_mcp.format_ext_map import format_from_extension

    return format_from_extension(path.suffix)




def looks_like_abc(text: str) -> bool:
    from lilycode_mcp.abc_patterns import ABC_LOOKS_LIKE_RE

    return bool(ABC_LOOKS_LIKE_RE.search(text))


def ensure_abc_has_default_length(abc_text: str, default: str = "1/8") -> str:
    """
    Ensure ABC text has L: (default note length) so music21 and other parsers can process notes.
    If L: is already present, return as-is. Otherwise insert L:default after the last header line.
    """
    from lilycode_mcp.abc_patterns import ABC_ANY_HEADER_RE, ABC_DEFAULT_LENGTH, ABC_HAS_LENGTH_RE

    default = default or ABC_DEFAULT_LENGTH
    if ABC_HAS_LENGTH_RE.search(abc_text):
        return abc_text
    lines = abc_text.split("\n")
    insert_at = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and ABC_ANY_HEADER_RE.match(stripped):
            insert_at = i
    if insert_at >= 0:
        lines.insert(insert_at + 1, f"L:{default}")
        return "\n".join(lines)
    from lilycode_mcp.abc_constants import ABC_DEFAULT_REF, ABC_MINIMAL_HEADER_TEMPLATE

    prefix = ABC_MINIMAL_HEADER_TEMPLATE.format(ref=ABC_DEFAULT_REF, length=default)
    return f"{prefix}{abc_text}"


def parse_abc_headers(text: str) -> dict[str, str | float | None]:
    """Extract ABC header fields: title, key (tonic), meter, tempo (Q:), default length (L:)."""
    from lilycode_mcp.abc_patterns import ABC_HEADER_RE

    out: dict[str, str | float | None] = {
        "title": None,
        "tonic": None,
        "meter": None,
        "tempo_bpm": None,
        "default_length": None,
    }
    for m in ABC_HEADER_RE.finditer(text):
        key, value = m.group(1).upper(), m.group(2).strip()
        if key == "T" and out["title"] is None:
            # First T: is title; later T: are subtitles per ABC standard.
            out["title"] = value or None
        elif key == "K":
            # K:C -> C; K:Amin / K:A min -> A
            if value:
                first_word = value.split()[0].strip()
                out["tonic"] = first_word[0].upper() if first_word else None
            else:
                out["tonic"] = None
        elif key == "M":
            out["meter"] = value or None
        elif key == "Q":
            # Q:1/4=120 or Q:120
            if "=" in value:
                try:
                    out["tempo_bpm"] = float(value.split("=")[-1].strip())
                except (ValueError, IndexError):
                    pass
            else:
                try:
                    out["tempo_bpm"] = float(value)
                except ValueError:
                    pass
        elif key == "L":
            out["default_length"] = value or None
    return out


def parse_abc_note_events(text: str) -> list[tuple[str, str]]:
    """
    Parse ABC body for note-like tokens; return list of (pitch_hint, duration_hint).
    Pitch: letter + optional octave (,'); duration: derived from L: and multiplier.
    """
    from lilycode_mcp.abc_patterns import ABC_DEFAULT_LENGTH, ABC_NOTE_TOKEN_RE, ABC_SKIP_KEYS
    from lilycode_mcp.app_defaults import FALLBACK_DURATION_UNKNOWN
    from lilycode_mcp.pitch_constants import PITCH_LETTERS

    events: list[tuple[str, str]] = []
    lines = text.split("\n")
    default_len = ABC_DEFAULT_LENGTH
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("L:"):
            default_len = stripped[2:].strip()
            continue
        if any(stripped.startswith(f"{h}:") for h in ABC_SKIP_KEYS):
            continue
        for m in ABC_NOTE_TOKEN_RE.finditer(line):
            pitch_part = m.group(1)
            length_part = m.group(2)
            if not pitch_part:
                continue
            # Strip accidentals/octave marks and extract the base note letter.
            letter_chars = [ch for ch in pitch_part if ch.upper() in PITCH_LETTERS]
            if not letter_chars:
                continue
            letter = letter_chars[0].upper()
            duration = FALLBACK_DURATION_UNKNOWN
            if length_part:
                if length_part.startswith("/"):
                    try:
                        denom = int(length_part[1:])
                        duration = f"1/{denom}"
                    except ValueError:
                        pass
                else:
                    duration = length_part
            else:
                duration = default_len
            events.append((letter, duration))
    return events


def looks_like_chordpro(text: str) -> bool:
    from lilycode_mcp.chordpro_directives_map import CHORDPRO_CHORD_RE

    return bool(CHORDPRO_CHORD_RE.search(text)) or "{title:" in text.lower()


def parse_chordpro_events(text: str) -> list[tuple[str, str]]:
    """Extract chord symbols as (chord_label, 'chord') for fallback events."""
    from lilycode_mcp.chordpro_directives_map import CHORDPRO_CHORD_RE

    events: list[tuple[str, str]] = []
    for m in CHORDPRO_CHORD_RE.finditer(text):
        events.append((m.group(1), "chord"))
    return events


def parse_chordpro_title(text: str) -> str | None:
    from lilycode_mcp.chordpro_directives_map import extract_chordpro_title

    return extract_chordpro_title(text)
