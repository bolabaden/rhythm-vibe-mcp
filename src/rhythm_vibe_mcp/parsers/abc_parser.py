from __future__ import annotations


def looks_like_abc(text: str) -> bool:
    from rhythm_vibe_mcp.parsers.abc_patterns import ABC_LOOKS_LIKE_RE

    return bool(ABC_LOOKS_LIKE_RE.search(text))


def parse_abc_headers(text: str) -> dict[str, str | float | None]:
    from rhythm_vibe_mcp.parsers.abc_patterns import ABC_HEADER_RE

    out: dict[str, str | float | None] = {
        "default_length": None,
        "meter": None,
        "tempo_bpm": None,
        "title": None,
        "tonic": None,
    }
    for m in ABC_HEADER_RE.finditer(text):
        key, value = m.group(1).upper(), m.group(2).strip()
        if key == "T" and out["title"] is None:
            out["title"] = value or None
        elif key == "K":
            if value:
                first_word = value.split()[0].strip()
                out["tonic"] = first_word[0].upper() if first_word else None
            else:
                out["tonic"] = None
        elif key == "M":
            out["meter"] = value or None
        elif key == "Q":
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
    from rhythm_vibe_mcp.constants.defaults import FALLBACK_DURATION_UNKNOWN
    from rhythm_vibe_mcp.parsers.abc_patterns import (
        ABC_DEFAULT_LENGTH,
        ABC_NOTE_TOKEN_RE,
        ABC_SKIP_KEYS,
    )
    from rhythm_vibe_mcp.constants.pitches import PITCH_LETTERS

    events: list[tuple[str, str]] = []
    lines: list[str] = text.split("\n")
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
