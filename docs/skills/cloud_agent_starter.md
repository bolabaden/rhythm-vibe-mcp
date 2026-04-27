# Cloud Agent Starter Skill — rhythm-vibe-mcp

Use this skill whenever you start working on this repository as a Cloud agent. It answers the most common "how do I run / test this?" questions immediately.

---

## 1. First-time setup

```bash
# Install all dev dependencies (Python 3.12+ standard path)
uv sync --extra dev --extra scrape

# Verify environment is healthy
uv run rhythm-vibe-mcp-cli healthcheck
```

Expected healthcheck output includes:
- `"lilypond_available": true` (pre-installed at `/usr/bin/lilypond`)
- `"ffmpeg_available": true` (pre-installed)
- `"supported_formats"` list with ~10 formats

If `lilypond_available` is `false`, install it:
```bash
sudo apt-get install -y lilypond
```

No login, no feature flags, no secrets required to run the core MCP tools and tests.

---

## 2. Running the test suite

```bash
# All tests (self-contained, no network, no binaries needed)
uv run pytest tests -v

# With coverage report
uv run pytest tests --cov=src/rhythm_vibe_mcp --cov-report=term-missing

# Subset: skip any slow/integration marks
uv run pytest tests -v -m "not integration and not slow"
```

All 139 tests should pass in under 2 seconds. Zero network calls are made (all external calls are mocked).

---

## 3. Lint

```bash
# ruff is not a project dep — always invoke via uvx
uvx ruff check src/ tests/
```

Pre-existing line-length violations (E501) are expected (~200+). New code should not introduce new error categories.

---

## 4. MCP server and CLI

### Stdio server (for direct tool invocation)
```bash
uv run rhythm-vibe-mcp
```

### Network transport (for SSE clients)
```bash
uv run rhythm-vibe-mcp --transport sse --host 0.0.0.0 --port 8000
```

### CLI client — invoke any tool directly
```bash
# List available tools
uv run rhythm-vibe-mcp-cli --help

# Tool-level help
uv run rhythm-vibe-mcp-cli healthcheck --help
uv run rhythm-vibe-mcp-cli convert-music --help

# Example tool calls
uv run rhythm-vibe-mcp-cli healthcheck
uv run rhythm-vibe-mcp-cli convert-text-notation-to-lily-or-fallback \
  --text "X:1\nT:Test\nM:4/4\nL:1/8\nK:C\nCDEF GABc|"
uv run rhythm-vibe-mcp-cli compose-story-lily \
  --prompt "a gentle cello sunrise theme" --instrument Cello
```

The CLI introspects `mcp._tool_manager.list_tools()` at runtime — no hardcoded tool names.

---

## 5. Gradio Web UI

```bash
uv run rhythm-vibe-mcp-webui --host 0.0.0.0 --port 7860
```

The UI runs on port 7860. In headless/cloud environments, prefer the CLI for testing MCP tools — the Gradio accordion sections can be slow or unresponsive.

The UI's "AI Music Assistant" chat panel requires a configured LLM backend. All other panels (Score Editor, Theory Lab, conversion tools) work without one.

---

## 6. Area-by-area testing workflows

### MCP tools (server.py)
Use the CLI client for end-to-end testing:
```bash
uv run rhythm-vibe-mcp-cli healthcheck
uv run rhythm-vibe-mcp-cli fetch-music-from-web --url "https://example.com/file.mid"
uv run rhythm-vibe-mcp-cli plan-music-conversion --input-format abc --output-format pdf
```

Test classes: `tests/test_server_tools.py`, `tests/test_mcp_integration.py`

### Format conversion (converters.py, conversion_graph.py)
```bash
uv run pytest tests/test_converters.py -v
```

### Music theory (theory/)
```bash
uv run pytest tests/test_theory.py -v
```

### Fallback model (fallbacks.py)
```bash
uv run pytest tests/test_fallbacks.py -v
```

### MuseScore integration (integrations/musescore.py)
Requires `MUSESCORE_API_TOKEN` env var for live tests; unit tests mock the HTTP layer.
```bash
uv run pytest tests/test_musescore.py -v
```

### Web fetch (integrations/web.py)
```bash
uv run pytest tests/test_web_fetch.py -v
```

### CLI client (cli.py)
```bash
uv run pytest tests/test_cli.py -v
```

---

## 7. Secrets and credentials

| Secret | Where to set | Used by |
|---|---|---|
| `MUSESCORE_API_TOKEN` | Cursor Cloud Secrets or `.env` (git-ignored) | `musescore_api` and `set_musescore_auth_token` tools |
| `MUSESCORE_API_BASE` | `.env` (optional override) | MuseScore API base URL |
| `rhythm_vibe_mcp_WORKDIR` | `.env` (optional override) | Artifact output directory |

Never hardcode token values in source files. The `.env` file is listed in `.gitignore`.

For Cloud agent runs, add secrets via the Cursor Dashboard → Cloud Agents → Secrets.

---

## 8. Common debugging commands

```bash
# Check which Python and uv are in use
uv python list
uv --version

# Inspect installed packages
uv pip list | grep -E "mcp|gradio|music21|pydantic"

# Run a single test file with verbose output
uv run pytest tests/test_server_tools.py -v -s

# Run a single test by name
uv run pytest tests/test_server_tools.py::test_healthcheck -v

# Check LilyPond version
lilypond --version

# Check ffmpeg version
ffmpeg -version 2>&1 | head -1
```

---

## 9. Updating this skill

Add a new entry to this skill file whenever you discover:
- A new testing trick or useful CLI invocation
- An environment quirk specific to Cloud agents
- A common failure mode and its fix
- A new tool or entry point added to `pyproject.toml`

Keep entries concrete and command-focused. Prefer runnable examples over prose explanations.
