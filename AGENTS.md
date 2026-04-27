# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

rhythm-vibe-mcp is a single Python package (not a monorepo) providing an MCP server, CLI client, and Gradio Web UI for AI-assisted music creation. Source lives in `src/rhythm_vibe_mcp/`. Managed exclusively with `uv` (see `.cursorrules`).

Key source layout:
- `server.py` — FastMCP server entrypoint and tool registration
- `cli.py` — CLI client (introspects registered tools at runtime)
- `webui.py` — Gradio single-page Web UI
- `converters.py` / `conversion_graph.py` — format conversion routing
- `composer.py` — narrative-to-LilyPond composition
- `fallbacks.py` — `RobustMusicFallback` failure-tolerant model
- `models.py` — Pydantic request/response models
- `runtime_enums.py` — internal finite-domain enums (transport, notation hints, etc.)
- `theory/` — chord, pitch, scale, rhythm, progression, ingestion modules
- `parsers/` — ABC and ChordPro parsers
- `integrations/` — MuseScore API proxy, web fetch
- `services/` — pipeline orchestration, service catalog
- `constants/` — all magic strings/values centralised here

### Environment setup

```bash
uv sync --extra dev --extra scrape   # standard dev setup (Python 3.12+)
uv sync --extra dev --extra scrape --extra audio  # only on Python ≤3.11
```

### Running services

- **MCP Server (stdio):** `uv run rhythm-vibe-mcp` — default transport is stdio; use `--transport sse` or `--transport streamable-http` with `--host`/`--port` for network transports.
- **Gradio Web UI:** `uv run rhythm-vibe-mcp-webui --host 0.0.0.0 --port 7860`
- **CLI client:** `uv run rhythm-vibe-mcp-cli <tool-name> [args]` — launches a local MCP server over stdio per invocation; use `--help` to see available tools.

Registered script aliases (all equivalent entrypoints defined in `pyproject.toml`):
- `rhythm-vibe-mcp` / `mcp-rhythm-vibe` → `server:main`
- `rhythm-vibe-mcp-cli` / `rhythmvibe-cli` → `cli:main`
- `rhythm-vibe-mcp-webui` → `webui:main`
- `rhythm-vibe-refresh-spaces` → `spaces_sync:main`

### MCP tool names (stable contract)

| CLI subcommand | MCP tool name |
|---|---|
| `healthcheck` | `healthcheck` |
| `fetch-music-from-web` | `fetch_music_from_web` |
| `convert-music` | `convert_music` |
| `plan-music-conversion` | `plan_music_conversion` |
| `audio-or-file-to-sheet` | `audio_or_file_to_sheet` |
| `transpose-song` | `transpose_song` |
| `normalize-reddit-music-text` | `normalize_reddit_music_text` |
| `convert-text-notation-to-lily-or-fallback` | `convert_text_notation_to_lily_or_fallback` |
| `compose-story-lily` | `compose_story_lily` |
| `set-musescore-auth-token` | `set_musescore_auth_token` |
| `musescore-api` | `musescore_api` |
| `batch-convert-audio` | `batch_convert_audio` |
| `analyze-audio-performance` | `analyze_audio_performance` |

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `rhythm_vibe_mcp_WORKDIR` | Artifacts working directory | `.` |
| `MUSESCORE_API_TOKEN` | MuseScore authentication token | *(unset)* |
| `MUSESCORE_API_BASE` | MuseScore API base URL | `https://musescore.com/api` |

### Lint, test, build

- **Lint:** `uvx ruff check src/ tests/` — ruff is not a project dependency; run it via `uvx`.
- **Tests:** `uv run pytest tests -v` — all 139 tests are self-contained (external calls are mocked). No network or external binaries needed.
- **Coverage:** `uv run pytest tests --cov=src/rhythm_vibe_mcp --cov-report=term-missing`
- **Skip integration/slow tests:** `uv run pytest tests -v -m "not integration and not slow"`
- **asyncio:** `asyncio_mode = "auto"` is set in `pyproject.toml`; async tests need no extra decoration.

### Gotchas

- The `audio` extra (`basic-pitch`) requires Python ≤3.11 due to tensorflow 2.15.0 wheel availability. On Python 3.12+, install without `--extra audio`: `uv sync --extra dev --extra scrape`.
- System binaries `lilypond` and `ffmpeg` are pre-installed in the Cloud Agent environment (`/usr/bin/lilypond`, `/usr/bin/ffmpeg`). Without them, the server returns structured fallback outputs instead of rendered files.
- The Web UI's "AI Music Assistant" chat requires an external LLM backend and may not respond without one configured. The Score Editor (LilyPond Studio) and all MCP tools work independently.
- The Gradio Web UI accordion sections may be sluggish in headless browser environments. For reliable tool invocation and testing, prefer the CLI client (`rhythm-vibe-mcp-cli`) which exercises the same MCP server tools over stdio.
- `MUSESCORE_API_TOKEN` is sensitive — set it via environment variables or a `.env` file (which is git-ignored). Never hardcode tokens in source files.
- All subprocess calls (`lilypond`, `ffmpeg`, `git`) use list-form arguments, not `shell=True`, so shell-injection through user-supplied paths is not possible.
- `spaces_sync.py` uses `urllib.request.urlopen` (stdlib, no SSL verify override) for the Hugging Face API and clones repos via `git clone`. It is a standalone utility script not wired into the MCP server.
