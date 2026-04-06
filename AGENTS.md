# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

rhythm-vibe-mcp is a single Python package (not a monorepo) providing an MCP server, CLI client, and Gradio Web UI for AI-assisted music creation. Source lives in `src/rhythm_vibe_mcp/`. Managed exclusively with `uv` (see `.cursorrules`).

### Running services

- **MCP Server (stdio):** `uv run rhythm-vibe-mcp` — default transport is stdio; use `--transport sse` or `--transport streamable-http` with `--host`/`--port` for network transports.
- **Gradio Web UI:** `uv run rhythm-vibe-mcp-webui --host 0.0.0.0 --port 7860`
- **CLI client:** `uv run rhythm-vibe-mcp-cli <tool-name> [args]` — launches a local MCP server over stdio per invocation; see `--help` for available tools.

### Lint, test, build

- **Lint:** `uvx ruff check src/ tests/` — ruff is not a project dependency; run it via `uvx`.
- **Tests:** `uv run pytest tests -v` — all 139 tests are self-contained (external calls are mocked). No network or external binaries needed.
- **Coverage:** `uv run pytest tests --cov=src/rhythm_vibe_mcp --cov-report=term-missing`

### Gotchas

- The `audio` extra (`basic-pitch`) requires Python ≤3.11 due to tensorflow 2.15.0 wheel availability. On Python 3.12+, install without `--extra audio`: `uv sync --extra dev --extra scrape`.
- System binaries `lilypond` and `ffmpeg` are optional. Without them, the server returns structured fallback outputs instead of rendered files. Install via `sudo apt-get install -y lilypond` if needed (ffmpeg is typically pre-installed).
- The Web UI's "AI Music Assistant" chat requires an external LLM backend and may not respond without one configured. The Score Editor (LilyPond Studio) and all MCP tools work independently.
- The Gradio Web UI accordion sections may be sluggish in headless browser environments. For reliable tool invocation and testing, prefer the CLI client (`rhythm-vibe-mcp-cli`) which exercises the same MCP server tools over stdio.
