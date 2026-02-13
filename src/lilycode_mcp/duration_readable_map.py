"""Mapping of ABC/notation duration strings to human-readable names."""

# ABC and common duration fractions -> readable label
# Keys: "1", "1/2", "1/4", "1/8", "1/16", etc. (also "2" for half, "4" for quarter in some notations)
DURATION_TO_READABLE: dict[str, str] = {
    "1": "whole",
    "1/1": "whole",
    "2": "half",
    "1/2": "half",
    "4": "quarter",
    "1/4": "quarter",
    "8": "eighth",
    "1/8": "eighth",
    "16": "sixteenth",
    "1/16": "sixteenth",
    "32": "thirty-second",
    "1/32": "thirty-second",
    "64": "sixty-fourth",
    "1/64": "sixty-fourth",
    "128": "hundred-twenty-eighth",
    "1/128": "hundred-twenty-eighth",
    "3/2": "dotted whole",
    "3/4": "dotted half",
    "3/8": "dotted quarter",
    "3/16": "dotted eighth",
    "3/32": "dotted sixteenth",
    "3/64": "dotted thirty-second",
    "2/2": "whole",
    "4/4": "whole",
    "2/4": "half",
    "4/8": "half",
    "2/8": "quarter",
    "4/16": "quarter",
    "2/16": "eighth",
    "4/32": "eighth",
    "2/32": "sixteenth",
    "4/64": "sixteenth",
    "1/3": "third",
    "1/6": "sixth",
    "1/12": "twelfth",
    "1/24": "twenty-fourth",
    "1/48": "forty-eighth",
    "1/96": "ninety-sixth",
    "1/5": "quintuplet",
    "1/7": "septuplet",
    "1/9": "nontuplet",
    "1/10": "tenth",
    "1/20": "twentieth",
    "1/40": "fortieth",
    "1/80": "eightieth",
    "2/3": "two-thirds",
    "4/3": "four-thirds",
}

# Build extended map with common variants and programmatic expansions
DURATION_TO_READABLE: dict[str, str] = dict(DURATION_TO_READABLE)

_READABLE_BY_DENOM: dict[int, str] = {
    1: "whole",
    2: "half",
    4: "quarter",
    8: "eighth",
    16: "sixteenth",
    32: "thirty-second",
    64: "sixty-fourth",
    128: "hundred-twenty-eighth",
}


def _extend_duration_map() -> None:
    # Add integer-as-denominator variants
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
        for fmt in (f"{base}*{mult}", f"{base} x{mult}"):
            DURATION_TO_READABLE.setdefault(fmt, DURATION_TO_READABLE.get(base, base))


_extend_duration_map()


def duration_to_readable(d: str) -> str:
    """Return human-readable duration name, or the original string if unknown."""
    from lilycode_mcp.app_defaults import (
        FALLBACK_DURATION_CHORD,
        FALLBACK_DURATION_UNKNOWN,
    )

    if d in (FALLBACK_DURATION_UNKNOWN, FALLBACK_DURATION_CHORD):
        return d
    norm = d.strip()
    return DURATION_TO_READABLE.get(norm, d)
