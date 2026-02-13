from __future__ import annotations

import os
from typing import Any

import httpx

from lilycode_mcp.http_constants import (
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HTTP_DELETE,
    HTTP_GET,
    HTTP_POST,
    HTTP_PUT,
    MUSESCORE_REQUEST_TIMEOUT,
)
from lilycode_mcp.limits_constants import API_RESPONSE_TEXT_MAX_LEN
from lilycode_mcp.api_response_keys import (
    KEY_JSON,
    KEY_MESSAGE,
    KEY_OK,
    KEY_STATUS_CODE,
    KEY_TEXT,
    KEY_URL,
)
from lilycode_mcp.musescore_constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    MSG_HTTP_ERROR,
)


def musescore_env_auth_headers() -> dict[str, str]:
    from lilycode_mcp.env_constants import ENV_MUSESCORE_TOKEN

    token = os.getenv(ENV_MUSESCORE_TOKEN, "").strip()
    if not token:
        return {}
    return {HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX}{token}"}


def musescore_api_request(
    endpoint: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    base_url: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """
    Best-effort public API wrapper.
    If login is required, pass auth_token or set MUSESCORE_API_TOKEN.
    """
    from lilycode_mcp.env_constants import DEFAULT_MUSESCORE_BASE, ENV_MUSESCORE_BASE

    base_str = base_url or os.getenv(ENV_MUSESCORE_BASE, DEFAULT_MUSESCORE_BASE) or DEFAULT_MUSESCORE_BASE
    url_base = base_str.rstrip("/")
    url = f"{url_base}/{endpoint.lstrip('/')}"
    headers = musescore_env_auth_headers()
    if auth_token:
        headers[HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX}{auth_token}"

    with httpx.Client(timeout=MUSESCORE_REQUEST_TIMEOUT, follow_redirects=True) as client:
        if method.upper() == HTTP_POST:
            res = client.post(url, json=payload or {}, headers=headers)
        elif method.upper() == HTTP_PUT:
            res = client.put(url, json=payload or {}, headers=headers)
        elif method.upper() == HTTP_DELETE:
            res = client.delete(url, headers=headers)
        else:
            res = client.get(url, params=payload or {}, headers=headers)

        if res.status_code >= 400:
            return {
                KEY_OK: False,
                KEY_STATUS_CODE: res.status_code,
                KEY_URL: str(res.url),
                KEY_MESSAGE: MSG_HTTP_ERROR.format(status_code=res.status_code),
                KEY_TEXT: res.text[:API_RESPONSE_TEXT_MAX_LEN],
            }
        ctype = res.headers.get(HEADER_CONTENT_TYPE, "")
        if CONTENT_TYPE_JSON in ctype:
            return {
                KEY_OK: True,
                KEY_JSON: res.json(),
                KEY_STATUS_CODE: res.status_code,
            }
        return {
            KEY_OK: True,
            KEY_TEXT: res.text,
            KEY_STATUS_CODE: res.status_code,
        }
