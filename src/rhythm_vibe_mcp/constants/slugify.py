"""Constants and helpers for slugifying titles into safe filenames."""

from __future__ import annotations

import re

# Max length for slug (filename stem)
SLUG_MAX_LENGTH = 80

# Regex: remove any character that is not alphanumeric, space, hyphen, underscore
SLUG_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9_ -]+")

# Fallback when slug becomes empty
SLUG_FALLBACK = "piece"


def slugify(text: str, *, max_length: int | None = None) -> str:
    """Convert title to a safe filename stem: strip unsafe chars, collapse spaces to underscore.

    Args:
    ----
        text (Any): Description for text.
        max_length (Any): Description for max_length.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of slugify logic.

    """
    max_len = max_length if max_length is not None else SLUG_MAX_LENGTH
    cleaned = SLUG_SAFE_PATTERN.sub("", text).strip().replace(" ", "_")
    trimmed = cleaned[:max_len] if max_len else cleaned
    return trimmed or SLUG_FALLBACK
