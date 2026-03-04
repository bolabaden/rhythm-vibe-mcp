# Architecture Notes

For the Web UI-specific architecture rationale and library-selection record, see [WEBUI_RESEARCH_AND_DECISIONS.md](WEBUI_RESEARCH_AND_DECISIONS.md).
For a prompt-to-code implementation snapshot (what is currently shipped), see [IMPLEMENTED_STATUS_AGAINST_PROMPTS.md](IMPLEMENTED_STATUS_AGAINST_PROMPTS.md).

## MCP Server Design

- Transport-agnostic FastMCP server (`rhythm_vibe_mcp.server`).
- Tool outputs are structured JSON for deterministic agent usage.
- Conversion routes are explicit and composable via `plan_music_conversion`.
- Failures return partial artifacts and/or `RobustMusicFallback` instead of hard-stop errors.

## Format Strategy

- Primary engraving/notation target: LilyPond.
- Universal notation interchange: MusicXML.
- Social shorthand ingestion:
  - Primary: ABC notation
  - Secondary: ChordPro
  - Fallback: freeform text -> event model

## Failure-Tolerant Continuation

When any conversion stage fails:

1. Preserve upstream artifacts.
2. Return warning-rich fallback model.
3. Keep enough musical context (title, hint, shorthand, events) for downstream tools/subagents.

This avoids fragile task failure in agentic workflows when one strict parser/compiler rejects input.

## MuseScore Integration

- Public endpoints first (no login when possible).
- Optional authenticated mode via:
  - `MUSESCORE_API_TOKEN` env
  - `set_musescore_auth_token` for session/SSE-like flows

## Planned Next Increments

- Add stronger audio->score transcription choices and quantization controls.
- Add authenticated MuseScore actions beyond read-only calls where API permits.
- Add explicit conversion capability probing for installed binaries.
- Add round-trip validation tests for high-value format pairs.

## Contract Freeze Baseline (Prompt 1)

The following interfaces are treated as do-not-break during refactor phases.

- Server module entrypoint remains `rhythm_vibe_mcp.server:main`.
- Server CLI transport contract remains:
  - `--transport` supports `stdio`, `streamable-http`, `sse`, and `http` alias.
  - `--host` / `--port` configure network transports (`streamable-http`, `sse`).
- MCP tool names remain stable:
  - `healthcheck`
  - `fetch_music_from_web`
  - `convert_music`
  - `plan_music_conversion`
  - `audio_or_file_to_sheet`
  - `transpose_song`
  - `normalize_reddit_music_text`
  - `convert_text_notation_to_lily_or_fallback`
  - `compose_story_lily`
  - `set_musescore_auth_token`
  - `musescore_api`
- Tool handlers continue returning JSON string payloads compatible with current tests.
- CLI script entrypoint remains `rhythm_vibe_mcp.cli:main`.
- CLI default server launch parameters remain equivalent to:
  - `python -m rhythm_vibe_mcp.server --transport stdio`

Baseline validation set for this freeze:

- `tests/test_cli.py`
- `tests/test_server_tools.py`
- `tests/test_mcp_integration.py`

## Type Hardening Snapshot (Prompts 15–21)

- Added internal enum-backed finite domains in `runtime_enums.py` for transport, schema type, notation hints, and conversion step identifiers.
- Preserved public wire contracts as plain strings (tool payload keys/values and CLI-visible values remain unchanged).
- Added structural typing boundaries (`TypedDict`) for core payload pathways in server/CLI/converters without runtime behavior changes.
- Captured module-level classification matrix in `docs/TYPE_INVENTORY.md`.
- Full regression boundary after this phase: `pytest` => `122 passed`.
