"""Mapping of ABC/notation duration strings to human-readable names."""

from __future__ import annotations

from enum import StrEnum


class DurationReadable(StrEnum):
    WHOLE = "whole"
    HALF = "half"
    QUARTER = "quarter"
    EIGHTH = "eighth"
    SIXTEENTH = "sixteenth"
    THIRTY_SECOND = "thirty-second"
    SIXTY_FOURTH = "sixty-fourth"
    HUNDRED_TWENTY_EIGHTH = "hundred-twenty-eighth"
    DOTTED_WHOLE = "dotted whole"
    DOTTED_HALF = "dotted half"
    DOTTED_QUARTER = "dotted quarter"
    DOTTED_EIGHTH = "dotted eighth"
    DOTTED_SIXTEENTH = "dotted sixteenth"
    DOTTED_THIRTY_SECOND = "dotted thirty-second"
    THIRD = "third"
    SIXTH = "sixth"
    TWELFTH = "twelfth"
    TWENTY_FOURTH = "twenty-fourth"
    FORTY_EIGHTH = "forty-eighth"
    NINETY_SIXTH = "ninety-sixth"
    QUINTUPLET = "quintuplet"
    SEPTUPLET = "septuplet"
    NONTUPLET = "nontuplet"
    TENTH = "tenth"
    TWENTIETH = "twentieth"
    FORTIETH = "fortieth"
    EIGHTIETH = "eightieth"
    TWO_THIRDS = "two-thirds"
    FOUR_THIRDS = "four-thirds"

# ABC and common duration fractions -> readable label
# Keys: "1", "1/2", "1/4", "1/8", "1/16", etc. (also "2" for half, "4" for quarter in some notations)
DURATION_TO_READABLE: dict[str, DurationReadable] = {
    "1": DurationReadable.WHOLE,
    "1/1": DurationReadable.WHOLE,
    "2": DurationReadable.HALF,
    "1/2": DurationReadable.HALF,
    "4": DurationReadable.QUARTER,
    "1/4": DurationReadable.QUARTER,
    "8": DurationReadable.EIGHTH,
    "1/8": DurationReadable.EIGHTH,
    "16": DurationReadable.SIXTEENTH,
    "1/16": DurationReadable.SIXTEENTH,
    "32": DurationReadable.THIRTY_SECOND,
    "1/32": DurationReadable.THIRTY_SECOND,
    "64": DurationReadable.SIXTY_FOURTH,
    "1/64": DurationReadable.SIXTY_FOURTH,
    "128": DurationReadable.HUNDRED_TWENTY_EIGHTH,
    "1/128": DurationReadable.HUNDRED_TWENTY_EIGHTH,
    "3/2": DurationReadable.DOTTED_WHOLE,
    "3/4": DurationReadable.DOTTED_HALF,
    "3/8": DurationReadable.DOTTED_QUARTER,
    "3/16": DurationReadable.DOTTED_EIGHTH,
    "3/32": DurationReadable.DOTTED_SIXTEENTH,
    "3/64": DurationReadable.DOTTED_THIRTY_SECOND,
    "2/2": DurationReadable.WHOLE,
    "4/4": DurationReadable.WHOLE,
    "2/4": DurationReadable.HALF,
    "4/8": DurationReadable.HALF,
    "2/8": DurationReadable.QUARTER,
    "4/16": DurationReadable.QUARTER,
    "2/16": DurationReadable.EIGHTH,
    "4/32": DurationReadable.EIGHTH,
    "2/32": DurationReadable.SIXTEENTH,
    "4/64": DurationReadable.SIXTEENTH,
    "1/3": DurationReadable.THIRD,
    "1/6": DurationReadable.SIXTH,
    "1/12": DurationReadable.TWELFTH,
    "1/24": DurationReadable.TWENTY_FOURTH,
    "1/48": DurationReadable.FORTY_EIGHTH,
    "1/96": DurationReadable.NINETY_SIXTH,
    "1/5": DurationReadable.QUINTUPLET,
    "1/7": DurationReadable.SEPTUPLET,
    "1/9": DurationReadable.NONTUPLET,
    "1/10": DurationReadable.TENTH,
    "1/20": DurationReadable.TWENTIETH,
    "1/40": DurationReadable.FORTIETH,
    "1/80": DurationReadable.EIGHTIETH,
    "2/3": DurationReadable.TWO_THIRDS,
    "4/3": DurationReadable.FOUR_THIRDS,
}

# Build extended map with common variants and programmatic expansions
DURATION_TO_READABLE = dict(DURATION_TO_READABLE)

_READABLE_BY_DENOM: dict[int, DurationReadable] = {
    1: DurationReadable.WHOLE,
    2: DurationReadable.HALF,
    4: DurationReadable.QUARTER,
    8: DurationReadable.EIGHTH,
    16: DurationReadable.SIXTEENTH,
    32: DurationReadable.THIRTY_SECOND,
    64: DurationReadable.SIXTY_FOURTH,
    128: DurationReadable.HUNDRED_TWENTY_EIGHTH,
}


def _extend_duration_map() -> None:
    # Add integer-as-denominator variants
    """Executes logic for _extend_duration_map.

    Args:
    ----
        None

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _extend_duration_map logic.

    """
    for denom, label in _READABLE_BY_DENOM.items():
        DURATION_TO_READABLE.setdefault(f"1/{denom}", label)
        DURATION_TO_READABLE.setdefault(str(denom), label)
    # Duplet/triplet variants (e.g. 1/4*2, 1/8*3)
    for base, mult in [
        ("1/4", 2),
        ("1/8", 2),
        ("1/16", 2),
        ("1/4", 3),
        ("1/8", 3),
        ("1/16", 3),
    ]:
        base_readable = DURATION_TO_READABLE.get(base)
        if base_readable is None:
            continue
        for fmt in (f"{base}*{mult}", f"{base} x{mult}"):
            DURATION_TO_READABLE.setdefault(fmt, base_readable)


_extend_duration_map()


def duration_to_readable(d: str) -> str:
    """Return human-readable duration name, or the original string if unknown.

    Args:
    ----
        d (Any): Description for d.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of duration_to_readable logic.

    """
    from rhythm_vibe_mcp.constants.defaults import (
        FALLBACK_DURATION_CHORD,
        FALLBACK_DURATION_UNKNOWN,
    )

    if d in (FALLBACK_DURATION_UNKNOWN, FALLBACK_DURATION_CHORD):
        return d
    norm = d.strip()
    return DURATION_TO_READABLE.get(norm, d)
