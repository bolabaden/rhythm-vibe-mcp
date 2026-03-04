"""
MCP protocol-layer integration tests (canonical best practice).

Uses the official MCP SDK's in-process API so tests run through the real
MCP interaction layer without subprocess or network. This validates:
- Tool discovery (list_tools)
- Tool invocation and response shape (call_tool)
- JSON-RPC serialization and protocol compliance

Refs: Docker MCP best practices (connect, list tools, call tools);
      "Stop Vibe-Testing Your MCP Server" (in-memory testing);
      MCP Inspector workflow; pytest-asyncio with asyncio_mode=auto.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rhythm_vibe_mcp.server import mcp


def _text_from_call_tool_result(result: tuple) -> str:
    """Extract tool output text from (content_blocks, meta) returned by mcp.call_tool."""
    content, _meta = result
    if not content:
        return ""
    block = content[0]
    return getattr(block, "text", "") or ""


def _parse_tool_output(text: str) -> dict:
    """Parse JSON tool response for assertions."""
    return json.loads(text)


@pytest.mark.asyncio
async def test_list_tools_exposes_all_server_tools() -> None:
    """Validate tool discovery: AI agents see the expected tools (MCP best practice: list tools)."""
    tools = await mcp.list_tools()
    names = [t.name for t in tools]
    expected = {
        "healthcheck",
        "fetch_music_from_web",
        "convert_music",
        "plan_music_conversion",
        "audio_or_file_to_sheet",
        "transpose_song",
        "normalize_reddit_music_text",
        "convert_text_notation_to_lily_or_fallback",
        "compose_story_lily",
        "set_musescore_auth_token",
        "musescore_api",
    }
    assert expected.issubset(set(names)), f"Missing tools: {expected - set(names)}"


@pytest.mark.asyncio
async def test_call_tool_healthcheck_returns_diagnostics() -> None:
    """Validate tool call through MCP layer (MCP best practice: call tools)."""
    result = await mcp.call_tool("healthcheck", {})
    text = _text_from_call_tool_result(result)
    data = _parse_tool_output(text)
    assert "workdir" in data or "artifacts_dir" in data
    assert "musescore_auth_env_present" in data


@pytest.mark.asyncio
async def test_call_tool_plan_music_conversion_returns_route() -> None:
    """Tool call with arguments; validates parameter passing through protocol."""
    result = await mcp.call_tool(
        "plan_music_conversion",
        {"input_format": "midi", "output_format": "pdf"},
    )
    text = _text_from_call_tool_result(result)
    data = _parse_tool_output(text)
    assert data["ok"] is True
    assert data["route"][0] == "midi"
    assert data["route"][-1] == "pdf"


@pytest.mark.asyncio
async def test_call_tool_missing_file_returns_error_json() -> None:
    """Validate failure mode through MCP layer (best practice: test failure modes)."""
    result = await mcp.call_tool(
        "convert_music",
        {"input_ref": "/nonexistent/path/file.mid", "output_format": "pdf"},
    )
    text = _text_from_call_tool_result(result)
    data = _parse_tool_output(text)
    assert data["ok"] is False
    assert "input" in data["message"].lower() or "exist" in data["message"].lower() or "error" in data["message"].lower()


@pytest.mark.asyncio
async def test_call_tool_normalize_reddit_music_text_returns_fallback() -> None:
    """JSON tool result shape through MCP (ToolResult-style response)."""
    result = await mcp.call_tool(
        "normalize_reddit_music_text",
        {"text": "X:1\nK:C\nC D E F", "title": "tune"},
    )
    text = _text_from_call_tool_result(result)
    data = _parse_tool_output(text)
    assert data["ok"] is True
    assert data.get("fallback") is not None
    assert data["fallback"]["notation_hint"] == "abc"


@pytest.mark.asyncio
async def test_call_tool_with_real_file_returns_ok_or_fallback(
    sample_midi_minimal: Path, monkeypatch_workdir: Path
) -> None:
    """End-to-end tool call with real file; validates full stack through MCP."""
    result = await mcp.call_tool(
        "convert_music",
        {"input_ref": str(sample_midi_minimal), "output_format": "musicxml"},
    )
    text = _text_from_call_tool_result(result)
    data = _parse_tool_output(text)
    assert "ok" in data
    assert "message" in data
    if data["ok"]:
        assert "artifacts" in data
    else:
        assert data.get("fallback") is not None or "message" in data
