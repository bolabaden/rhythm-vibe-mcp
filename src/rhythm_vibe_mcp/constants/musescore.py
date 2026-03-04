"""MuseScore API request/response constants."""

from __future__ import annotations

# Authorization header value prefix
AUTH_BEARER_PREFIX = "Bearer "

# Content-Type check for JSON response
CONTENT_TYPE_JSON = "application/json"

# Error message when API returns 4xx/5xx
MSG_HTTP_ERROR = "MuseScore API returned HTTP {status_code}"
