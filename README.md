# rhythm-vibe-mcp

MCP server for "vibe coding" music with LilyPond-first workflows and resilient fallbacks.

> **Full vision and specification:** See [docs/VISION_AND_SPECIFICATION.md](docs/VISION_AND_SPECIFICATION.md) for the expanded goals, feature scope, error-handling philosophy, and design principles.

## Documentation

| Doc | Description |
|-----|-------------|
| [VISION_AND_SPECIFICATION.md](docs/VISION_AND_SPECIFICATION.md) | Goals, feature scope, error-handling philosophy, MCP best practices |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Server design, format strategy, failure-tolerant continuation |
| [WEBUI_RESEARCH_AND_DECISIONS.md](docs/WEBUI_RESEARCH_AND_DECISIONS.md) | Single-page web UI redesign research, decisions, tradeoffs, and validation notes |
| [IMPLEMENTED_STATUS_AGAINST_PROMPTS.md](docs/IMPLEMENTED_STATUS_AGAINST_PROMPTS.md) | Implementation-only mapping from planning prompts to what currently exists in code/tests |
| [TEST_EVALUATION.md](docs/TEST_EVALUATION.md) | Testing approach and evaluation criteria |

## What this server supports now

- Fetch existing music assets from the web (`fetch_music_from_web`).
- Convert between common music formats (`convert_music`) with best-effort routing:
  - Notation: `lilypond`, `musicxml`, `midi`, `abc`, `pdf`
  - Audio containers: `wav`, `mp3`, `m4a`
  - Fallback: `json_fallback`
- Audio/file to sheet workflow (`audio_or_file_to_sheet`) using transcription/conversion chain.
- Song transposition by semitones (`transpose_song`).
- Musescore API proxy (`musescore_api`) with:
  - public endpoint usage without login where possible
  - login token via env (`MUSESCORE_API_TOKEN`) or session tool (`set_musescore_auth_token`)
- Robust fallback behavior when strict LilyPond or converter steps fail.

## Canonical text-based social shorthand

For "Reddit/phone shorthand", this server treats **ABC notation** as the primary universal text format,
with **ChordPro** as a secondary lead-sheet shorthand.

Tool:
- `normalize_reddit_music_text`: normalizes informal text into a robust event-based fallback model.

Why this choice:
- ABC is compact and human-typable in comments/chats.
- ABC has broad tooling support and maps well to formal notation pipelines.
- ChordPro is widely used for quick chord+lyric communication.

## Error handling model

When strict conversions fail (e.g. LilyPond compile errors), server returns:

- `ok=false` plus diagnostic `message`
- `fallback` object (`RobustMusicFallback`) containing:
  - ambiguous but actionable event data
  - shorthand text snapshot
  - warnings to continue downstream tasks

This keeps multi-step agent tasks moving even when one notation step fails.

## Testing

Unit tests follow MCP server best practices: in-process, no subprocess or network by default, with mocks for external binaries (lilypond, ffmpeg) and HTTP. Run:

```bash
uv sync --extra dev
uv run pytest tests -v
uv run pytest tests --cov=src/rhythm_vibe_mcp --cov-report=term-missing
```

- **conftest.py**: Fixtures for temp workdir, sample LilyPond/ABC/ChordPro/MIDI/MusicXML files, and env isolation.
- **test_models.py**, **test_utils.py**, **test_fallbacks.py**: Pure unit tests for models, format detection, and fallback logic.
- **test_converters.py**: Conversion and route planning with parametrized routes and mocked binaries.
- **test_musescore.py**, **test_web_fetch.py**: API and download logic with mocked httpx.
- **test_server_tools.py**: Tool contract tests (JSON output, error handling) by calling tool functions directly.
- **test_mcp_integration.py**: MCP protocol layer (list_tools, call_tool) in-process.

Use `-m "not integration"` to skip any tests marked as integration (if added later).

To verify all tools return spec-compliant JSON, run the full suite; fixtures in `tests/fixtures/` (e.g. `sample.abc`, `minimal.mid`) are used for file-based tools.

## Quickstart

**With uv (recommended):**

Run from the project directory so the installed package uses source (`src/`). Run `uv sync` to pick up the latest code.

```bash
cd C:\GitHub\rhythm-vibe-mcp
uv sync
uv run rhythm-vibe-mcp
# or: uvx --from . mcp-rhythm-vibe
```

Select transport explicitly when needed:

```bash
uv run rhythm-vibe-mcp --transport stdio
uv run rhythm-vibe-mcp --transport streamable-http --host 127.0.0.1 --port 8000
uv run rhythm-vibe-mcp --transport sse --host 127.0.0.1 --port 8000
```

Supported transports: `stdio`, `streamable-http`, `sse` (`http` is accepted as an alias for `streamable-http`).

Optional extras (audio/transcription, scraping):

```bash
uv sync --extra audio --extra scrape
```

Gradio web UI (guided step-by-step UX):

```bash
uv sync
uv run rhythm-vibe-mcp-webui --host 127.0.0.1 --port 7860
```

The Web UI runs directly from package modules and does not require launching MCP transport first.

Refresh top Hugging Face music Spaces into `vendor/huggingface_spaces` and regenerate report:

```bash
uv run rhythm-vibe-refresh-spaces --query music --top-n 5 --limit 100
```

Optional cleanup of stale cloned Space folders:

```bash
uv run rhythm-vibe-refresh-spaces --query music --top-n 5 --prune
```

**With pip:**

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .
pip install -e ".[audio,scrape]"   # optional
rhythm-vibe-mcp
```

To launch the guided Gradio UI with pip-managed environments:

```bash
pip install -e .
rhythm-vibe-mcp-webui
```

## External binaries/tools (recommended)

- `lilypond` for LilyPond -> PDF/MIDI rendering
- `ffmpeg` for audio container conversion
- `MuseScore` CLI (future route expansion for advanced engraving/export)

Without these tools, the server still returns structured fallback outputs.

## Running with uvx (no PyPI publish)

The package is not on PyPI. Run the tool from the **local project path** so uv installs from the directory:

```bash
# From the project directory (recommended)
cd C:\GitHub\rhythm-vibe-mcp
uvx --from . mcp-rhythm-vibe
```

Or from anywhere using an absolute path:

```bash
uvx --from "C:/GitHub/rhythm-vibe-mcp" mcp-rhythm-vibe
```

Do **not** use `uvx mcp-rhythm-vibe` alone—that looks for the package on PyPI and will fail.

## Cursor MCP config (example)

Using uvx with local path (recommended):

```json
{
  "mcpServers": {
    "rhythm-vibe-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", ".", "mcp-rhythm-vibe"],
      "env": { "RHYTHM_VIBE_MCP_DIR": "C:/GitHub/rhythm-vibe-mcp" },
      "cwd": "C:/GitHub/rhythm-vibe-mcp"
    }
  }
}
```

Alternative (Python from venv):

```json
{
  "mcpServers": {
    "rhythm-vibe-mcp": {
      "command": "python",
      "args": ["-m", "rhythm_vibe_mcp.server"],
      "cwd": "c:/GitHub/rhythm-vibe-mcp"
    }
  }
}
```

## CLI (MCP client over local STDIO)

`rhythm-vibe-mcp-cli` is a client CLI that launches a local MCP server process over STDIO and calls tools through the MCP protocol.

```bash
uv run rhythm-vibe-mcp-cli --help
uv run rhythm-vibe-mcp-cli list-tools
uv run rhythm-vibe-mcp-cli call healthcheck --raw
uv run rhythm-vibe-mcp-cli call plan_music_conversion --arg input_format=abc --arg output_format=pdf
uv run rhythm-vibe-mcp-cli call convert_music --json-args '{"input_ref":"artifacts/sample.musicxml","output_format":"midi"}'
```

By default the CLI launches:

```bash
python -m rhythm_vibe_mcp.server --transport stdio
```

Override server launch details with:

- `--server-command`
- repeated `--server-arg`
- `--server-cwd`

## Current tool surface

- `healthcheck()` — workdir, artifacts_dir, MuseScore env + session token flag, binary availability (lilypond, ffmpeg), and supported_formats list
- `fetch_music_from_web(url)`
- `plan_music_conversion(input_format, output_format)`
- `convert_music(input_ref, output_format)`
- `audio_or_file_to_sheet(input_ref, prefer_output="pdf")`
- `transpose_song(input_ref, semitones, output_format="musicxml")`
- `normalize_reddit_music_text(text, title="reddit_vibe_idea")`
- `convert_text_notation_to_lily_or_fallback(text, target_format="lilypond", title="text_notation_piece")`
- `compose_story_lily(prompt, title="Theme", tempo_bpm=56, instrument="Solo", clef=null, midi_instrument=null, output_format="lilypond")`
- `set_musescore_auth_token(token)`
- `musescore_api(endpoint, method="GET", payload_json="{}", base_url="")`

## Notes on "any/all conversion combinations"

The architecture is built to support full matrix conversion, but some routes depend on external engines.
When a direct route does not exist yet, the server emits fallback output and diagnostics instead of failing hard.

Planned expansion areas:
- route planner with multistep intermediate formats
- richer audio-to-score transcription and quantization choices
- deeper MuseScore integration routes (CLI + public APIs + optional authenticated flows)
