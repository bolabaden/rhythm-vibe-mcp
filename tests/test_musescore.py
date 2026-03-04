"""
Unit tests for MuseScore API module: auth headers and request wrapper.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from rhythm_vibe_mcp.integrations.musescore import (
    musescore_api_request,
    musescore_env_auth_headers,
)


class TestMusescoreEnvAuthHeaders:
    def test_no_token_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MUSESCORE_API_TOKEN", raising=False)
        assert musescore_env_auth_headers() == {}

    def test_token_set_returns_bearer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MUSESCORE_API_TOKEN", "secret123")
        h = musescore_env_auth_headers()
        assert "Authorization" in h
        assert h["Authorization"] == "Bearer secret123"

    def test_token_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MUSESCORE_API_TOKEN", "  tok  ")
        h = musescore_env_auth_headers()
        assert h["Authorization"] == "Bearer tok"


class TestMusescoreApiRequest:
    def test_get_request_calls_httpx(self) -> None:
        with patch("rhythm_vibe_mcp.integrations.musescore.httpx.Client") as mock_client_cls:
            mock_resp = mock_client_cls.return_value.__enter__.return_value.get.return_value
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.json.return_value = {"data": "ok"}
            mock_resp.raise_for_status = lambda: None

            result = musescore_api_request("scores", method="GET", payload={"q": "test"})
            assert result["ok"] is True
            assert result.get("json") == {"data": "ok"}
            assert result.get("status_code") == 200

    def test_auth_token_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MUSESCORE_API_TOKEN", "env_token")
        with patch("rhythm_vibe_mcp.integrations.musescore.httpx.Client") as mock_client_cls:
            mock_resp = mock_client_cls.return_value.__enter__.return_value.get.return_value
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.json.return_value = {}
            mock_resp.raise_for_status = lambda: None

            musescore_api_request("me", auth_token="session_token")
            call_kw = mock_client_cls.return_value.__enter__.return_value.get.call_args[1]
            assert call_kw["headers"]["Authorization"] == "Bearer session_token"

    def test_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MUSESCORE_API_BASE", "https://custom.api/v1")
        with patch("rhythm_vibe_mcp.integrations.musescore.httpx.Client") as mock_client_cls:
            mock_resp = mock_client_cls.return_value.__enter__.return_value.get.return_value
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.json.return_value = {}
            mock_resp.raise_for_status = lambda: None

            musescore_api_request("scores")
            call_args = mock_client_cls.return_value.__enter__.return_value.get.call_args[0]
            assert "custom.api" in call_args[0]
            assert call_args[0].endswith("/scores") or "scores" in call_args[0]
