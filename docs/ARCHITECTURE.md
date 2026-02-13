# Architecture Notes

## MCP Server Design

- Transport-agnostic FastMCP server (`lilycode_mcp.server`).
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
