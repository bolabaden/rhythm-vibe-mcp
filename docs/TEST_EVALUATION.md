# Test Suite Evaluation

**Summary:** The tests **do** help ensure the MCP server works. Unit tests cover business logic and tool contracts; **MCP protocol-layer integration tests** (`test_mcp_integration.py`) validate tool discovery and tool calls through the official SDK’s in-process API, aligning with canonical MCP server testing best practices.

---

## Canonical MCP server testing best practices (Tavily / ecosystem)

Industry guidance (Docker MCP best practices, “Stop Vibe-Testing Your MCP Server”, MCP Inspector workflow, FastMCP docs) consistently recommends:

1. **Connect** – Validate that the server can be reached (configuration, readiness).
2. **List tools** – Assert that AI agents see the expected tools (`list_tools()` / `tools/list`).
3. **Call tools** – Exercise tool invocation and **failure modes** through the real MCP interaction layer, not only by calling handler functions in isolation.

**In-process testing** is the idiomatic approach: use the MCP SDK’s test client or the server’s own in-process API (`FastMCP.list_tools()`, `FastMCP.call_tool()`) so tests run the real protocol path without subprocess or network. That catches serialization, parameter passing, and wiring issues while keeping tests fast and deterministic.

This project implements that via the **official MCP Python SDK** (`mcp.server.fastmcp`): `tests/test_mcp_integration.py` uses `await mcp.list_tools()` and `await mcp.call_tool(name, arguments)` against the same `mcp` instance used at runtime.

---

## Do the tests help?

**Yes.** They give real value in these ways:

1. **Tool contract** – Every server tool is invoked as a plain function and its return value is parsed as JSON. That’s the same code path as when an MCP client calls a tool. So:
   - Return shape (e.g. `ok`, `message`, `artifacts`, `fallback`) is asserted.
   - Breaking a tool’s return type or key names will be caught.

2. **Conversion pipeline** – Route planning, single-step conversion, and `convert_any` are well covered. External binaries (lilypond, ffmpeg) are mocked, so tests are deterministic and don’t require system tools. That catches:
   - Wrong routes (e.g. midi → pdf).
   - Missing fallbacks when lilypond/ffmpeg are missing or fail.
   - music21-based conversion and transpose behavior (with real music21, minimal MIDI/MusicXML).

3. **Models and serialization** – Pydantic models (`ToolResult`, `RobustMusicFallback`, `MusicArtifact`, etc.) have validation and round-trip tests. Since the MCP server returns `ToolResult.model_dump()` as JSON, schema or field changes are caught.

4. **Format and fallback logic** – `guess_format`, `looks_like_abc`, `looks_like_chordpro`, and `fallback_from_text` / `fallback_from_error` are tested. That protects the “robust fallback” behavior and notation detection.

5. **I/O and env** – `artifacts_dir`, `workspace_root`, download-to-artifacts (mocked HTTP), and MuseScore auth headers/env are tested. That avoids path and env bugs in real use.

So in terms of **“does the server’s logic and JSON contract work?”** the tests are effective.

---

## What’s not covered (gaps)

| Gap | Impact |
|-----|--------|
| **No stdio/SSE transport tests** | In-process tests use `mcp.list_tools()` / `mcp.call_tool()`; we do not start the server as a subprocess or over HTTP/SSE. Process-bound transport bugs (stdio framing, SSE) are not exercised. |
| **No real binary E2E** | By design: lilypond/ffmpeg are mocked. So “real lilypond on this machine” isn’t asserted; only “when we pretend lilypond fails, we get a fallback”. |
| **Optional deps** | basic_pitch, beautifulsoup4 (optional extras) aren’t exercised. |
| **`convert_text_notation_to_lily_or_fallback`** | Test only checks “valid JSON” with loose assertions; it doesn’t lock in the current behavior (always returning fallback + message). |
| **URL as `input_ref` in `convert_music`** | `_coerce_input_to_path` can run `download_music_asset` for URLs; this is only exercised indirectly via `fetch_music_from_web`. No direct test for `convert_music("https://...", "pdf")`. |

---

## Per-file effectiveness

| File | Role | Effectiveness |
|------|------|---------------|
| **test_models.py** | Model validation, defaults, JSON round-trip | **High** – Protects the JSON shape clients see. |
| **test_utils.py** | Paths, format detection, `run_cmd`, ABC/ChordPro detection | **High** – Core utilities used everywhere. |
| **test_fallbacks.py** | ABC/ChordPro/freeform detection, error fallbacks | **High** – Central to “robust” behavior. |
| **test_converters.py** | Routes, lilypond/ffmpeg/music21 conversion, `convert_any` | **High** – Conversion is the main feature; mocks keep it deterministic. |
| **test_musescore.py** | Auth headers, API request builder (mocked) | **Medium–High** – No real API; still checks wiring. |
| **test_web_fetch.py** | Download to artifacts, filename handling (mocked) | **High** – Covers the only HTTP download path. |
| **test_server_tools.py** | Each tool called as function; JSON parsed and asserted | **High** – Directly exercises the same functions the MCP server exposes. |
| **test_mcp_integration.py** | In-process MCP: `list_tools()`, `call_tool()` with real server instance | **High** – Validates protocol layer, discovery, and tool call serialization (canonical best practice). |

---

## Conclusion

- **In general:** The tests help ensure the MCP server works for **logic, data shapes, tool outputs, and the MCP interaction layer**. Unit tests catch regressions in conversion, fallbacks, models, and JSON; **test_mcp_integration.py** confirms tool discovery and tool calls through the official SDK’s in-process API (list tools → call tools → assert response shape and failure modes).
- **Practice alignment:** The suite now follows canonical MCP server testing: connect (in-process), list tools, call tools (including failure cases), without subprocess or network, using the same code path as real MCP tool invocation.

Recommendation: **Keep all current tests**. The added MCP integration tests close the protocol-layer gap; optional next steps are stdio/SSE transport tests if you need to validate process-bound or HTTP deployment.
