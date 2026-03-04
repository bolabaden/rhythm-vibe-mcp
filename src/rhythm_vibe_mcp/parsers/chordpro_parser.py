from __future__ import annotations


def looks_like_chordpro(text: str) -> bool:
    from rhythm_vibe_mcp.constants.chordpro_directives import CHORDPRO_CHORD_RE

    return bool(CHORDPRO_CHORD_RE.search(text)) or "{title:" in text.lower()


def parse_chordpro_events(text: str) -> list[tuple[str, str]]:
    from rhythm_vibe_mcp.constants.chordpro_directives import CHORDPRO_CHORD_RE

    events: list[tuple[str, str]] = []
    for m in CHORDPRO_CHORD_RE.finditer(text):
        events.append((m.group(1), "chord"))
    return events


def parse_chordpro_title(text: str) -> str | None:
    from rhythm_vibe_mcp.constants.chordpro_directives import extract_chordpro_title

    return extract_chordpro_title(text)
