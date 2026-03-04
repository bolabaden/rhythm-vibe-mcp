from __future__ import annotations

from typing import Literal, cast

from rhythm_vibe_mcp.constants.defaults import (
    DEFAULT_UNTITLED,
    FALLBACK_DURATION_CHORD,
    FALLBACK_DURATION_UNKNOWN,
)
from rhythm_vibe_mcp.parsers.abc_parser import looks_like_abc, parse_abc_headers, parse_abc_note_events
from rhythm_vibe_mcp.parsers.chordpro_parser import (
    looks_like_chordpro,
    parse_chordpro_events,
    parse_chordpro_title,
)
from rhythm_vibe_mcp.constants.chord_qualities import looks_like_chord_token
from rhythm_vibe_mcp.constants.durations import duration_to_readable
from rhythm_vibe_mcp.constants.fallback_msgs import (
    MSG_ABC_HEADERS_NO_EVENTS,
    MSG_ABC_PARSED_USE_CONVERT,
    MSG_CHORDPRO_CHORDS_USE_CONVERT,
    MSG_CHORDPRO_NO_CHORDS,
    MSG_FREEFORM_NO_TOKENS,
    MSG_FREEFORM_TOKENS_USE_ABC,
)
from rhythm_vibe_mcp.models import FallbackNoteEvent, RobustMusicFallback
from rhythm_vibe_mcp.constants.pitches import PITCH_LETTERS
from rhythm_vibe_mcp.runtime_enums import NotationHint

_NotationHintT = Literal["abc", "chordpro", "freeform", "unknown"]


class FallbackFactory:
    """Factory for normalized fallback payloads used across tool pipelines."""

    def from_text(self, text: str, title: str | None = None) -> RobustMusicFallback:
        notation_hint = NotationHint.UNKNOWN
        title_val = title if title is not None else DEFAULT_UNTITLED
        tonic: str | None = None
        meter: str | None = None
        tempo_bpm: float | None = None
        events: list[FallbackNoteEvent] = []
        warnings: list[str] = []

        if looks_like_abc(text):
            notation_hint = NotationHint.ABC
            headers = parse_abc_headers(text)
            t = headers.get("title")
            title_val = t if isinstance(t, str) else title_val
            ton = headers.get("tonic")
            tonic = ton if isinstance(ton, str) else None
            m = headers.get("meter")
            meter = m if isinstance(m, str) else None
            q = headers.get("tempo_bpm")
            tempo_bpm = float(q) if isinstance(q, (int, float)) else None
            for pitch_letter, dur in parse_abc_note_events(text):
                events.append(
                    FallbackNoteEvent(
                        pitch=pitch_letter,
                        duration=duration_to_readable(dur),
                    ),
                )
            if events:
                warnings.append(MSG_ABC_PARSED_USE_CONVERT)
            else:
                warnings.append(MSG_ABC_HEADERS_NO_EVENTS)
        elif looks_like_chordpro(text):
            notation_hint = NotationHint.CHORDPRO
            t = parse_chordpro_title(text)
            if t:
                title_val = t
            for chord_label, dur in parse_chordpro_events(text):
                events.append(FallbackNoteEvent(pitch=chord_label, duration=dur))
            if events:
                warnings.append(MSG_CHORDPRO_CHORDS_USE_CONVERT)
            else:
                warnings.append(MSG_CHORDPRO_NO_CHORDS)
        else:
            notation_hint = NotationHint.FREEFORM
            for token in text.replace("\n", " ").split():
                t = token.strip()
                if not t:
                    continue
                upper = t.upper()
                if upper in PITCH_LETTERS:
                    events.append(
                        FallbackNoteEvent(
                            pitch=upper,
                            duration=FALLBACK_DURATION_UNKNOWN,
                        ),
                    )
                elif len(t) <= 12 and looks_like_chord_token(t):
                    events.append(
                        FallbackNoteEvent(
                            pitch=t,
                            duration=FALLBACK_DURATION_CHORD,
                        ),
                    )
            if not events:
                warnings.append(MSG_FREEFORM_NO_TOKENS)
            else:
                warnings.append(MSG_FREEFORM_TOKENS_USE_ABC)

        return RobustMusicFallback(
            title=title_val or DEFAULT_UNTITLED,
            tonic=tonic,
            meter=meter,
            tempo_bpm=tempo_bpm,
            notation_hint=cast("_NotationHintT", notation_hint.value),
            shorthand_text=text,
            events=events,
            warnings=warnings,
        )

    def from_error(
        self,
        *,
        title: str,
        warning: str,
        shorthand_text: str = "",
    ) -> RobustMusicFallback:
        return RobustMusicFallback(
            title=title,
            shorthand_text=shorthand_text,
            notation_hint=cast(_NotationHintT, NotationHint.UNKNOWN.value),
            warnings=[warning],
        )


_fallback_factory = FallbackFactory()


def fallback_from_text(text: str, title: str | None = None) -> RobustMusicFallback:
    """Functional compatibility wrapper around FallbackFactory.from_text."""
    return _fallback_factory.from_text(text=text, title=title)


def fallback_from_error(
    *,
    title: str,
    warning: str,
    shorthand_text: str = "",
) -> RobustMusicFallback:
    """Functional compatibility wrapper around FallbackFactory.from_error."""
    return _fallback_factory.from_error(
        title=title,
        warning=warning,
        shorthand_text=shorthand_text,
    )
