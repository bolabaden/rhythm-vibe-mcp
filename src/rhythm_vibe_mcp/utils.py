from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (including parents) if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_text_input(text: str) -> str:
    """Normalize text that may contain literal \n/\t from CLI or JSON so ABC/notation parses.
    Idempotent when input already has real newlines.

    """
    from rhythm_vibe_mcp.constants.escapes import ESCAPE_TO_CHAR

    if "\\n" in text or "\\t" in text:
        return text.replace("\\n", ESCAPE_TO_CHAR["\\n"]).replace(
            "\\t",
            ESCAPE_TO_CHAR["\\t"],
        )
    return text


def workspace_root() -> Path:
    """Return configured workspace root, defaulting to repository root.

    Resolution order:
    1) ``rhythm_vibe_mcp_WORKDIR`` when set
    2) repository root derived from this module path

    """
    from rhythm_vibe_mcp.constants.env import ENV_WORKDIR

    env_root = os.getenv(ENV_WORKDIR)
    if env_root:
        return Path(env_root).resolve()

    return Path(__file__).resolve().parents[2]


def artifacts_dir() -> Path:
    """Return the artifacts directory, creating it if it does not exist."""
    from rhythm_vibe_mcp.constants.paths import ARTIFACTS_SUBDIR

    return ensure_dir(workspace_root() / ARTIFACTS_SUBDIR)


def binary_available(name: str) -> bool:
    """Return whether executable ``name`` is available on ``PATH``."""
    return shutil.which(name) is not None


def run_cmd(command: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a subprocess and return ``(returncode, stdout, stderr)``."""
    from rhythm_vibe_mcp.constants.encodings import (
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
    """Infer normalized format name from file extension."""
    from rhythm_vibe_mcp.constants.formats import format_from_extension

    return format_from_extension(path.suffix)


def looks_like_abc(text: str) -> bool:
    """Return whether input text appears to be ABC notation."""
    from rhythm_vibe_mcp.parsers.abc_parser import looks_like_abc as parser_looks_like_abc

    return parser_looks_like_abc(text)


def ensure_abc_has_default_length(abc_text: str, default: str = "1/8") -> str:
    """Ensure ABC text has L: (default note length) so music21 and other parsers can process notes.
    If L: is already present, return as-is. Otherwise insert L:default after the last header line.

    """
    from rhythm_vibe_mcp.parsers.abc_patterns import (
        ABC_ANY_HEADER_RE,
        ABC_DEFAULT_LENGTH,
        ABC_HAS_LENGTH_RE,
    )

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
    from rhythm_vibe_mcp.constants.abc import (
        ABC_DEFAULT_REF,
        ABC_MINIMAL_HEADER_TEMPLATE,
    )

    prefix = ABC_MINIMAL_HEADER_TEMPLATE.format(ref=ABC_DEFAULT_REF, length=default)
    return f"{prefix}{abc_text}"


def parse_abc_headers(text: str) -> dict[str, str | float | None]:
    """Extract ABC header fields: title, key (tonic), meter, tempo (Q:), default length (L:).

    Args:
    ----
        text (Any): Description for text.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of parse_abc_headers logic.

    """
    from rhythm_vibe_mcp.parsers.abc_parser import parse_abc_headers as parser_parse_abc_headers

    return parser_parse_abc_headers(text)


def parse_abc_note_events(text: str) -> list[tuple[str, str]]:
    """Parse ABC body for note-like tokens; return list of (pitch_hint, duration_hint).
    Pitch: letter + optional octave (,'); duration: derived from L: and multiplier.

    Args:
    ----
        text (Any): Description for text.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of parse_abc_note_events logic.

    """
    from rhythm_vibe_mcp.parsers.abc_parser import (
        parse_abc_note_events as parser_parse_abc_note_events,
    )

    return parser_parse_abc_note_events(text)


def looks_like_chordpro(text: str) -> bool:
    """Executes logic for looks_like_chordpro.

    Args:
    ----
        text (Any): Description for text.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of looks_like_chordpro logic.

    """
    from rhythm_vibe_mcp.parsers.chordpro_parser import (
        looks_like_chordpro as parser_looks_like_chordpro,
    )

    return parser_looks_like_chordpro(text)


def parse_chordpro_events(text: str) -> list[tuple[str, str]]:
    """Extract chord symbols as (chord_label, 'chord') for fallback events.

    Args:
    ----
        text (Any): Description for text.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of parse_chordpro_events logic.

    """
    from rhythm_vibe_mcp.parsers.chordpro_parser import (
        parse_chordpro_events as parser_parse_chordpro_events,
    )

    return parser_parse_chordpro_events(text)


def parse_chordpro_title(text: str) -> str | None:
    """Executes logic for parse_chordpro_title.

    Args:
    ----
        text (Any): Description for text.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of parse_chordpro_title logic.

    """
    from rhythm_vibe_mcp.parsers.chordpro_parser import (
        parse_chordpro_title as parser_parse_chordpro_title,
    )

    return parser_parse_chordpro_title(text)
