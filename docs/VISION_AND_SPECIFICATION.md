# Lilycode MCP Server: Vision and Specification

This document expands the original vision for the rhythm vibe MCP server—a **Model Context Protocol (MCP)** server designed to enable AI agents and humans to "vibe code" music through natural workflows. It describes the goals, feature scope, error-handling philosophy, and design principles in full.

---

## Goal of the Prompt

The overarching goal is to build an **MCP server** that lets AI agents (and users interacting with them) work with music in a **fluid, resilient, and format-agnostic** way. The server should:

1. **Lower friction** — Users can attach or reference music in any common format and expect useful results.
2. **Support "vibe coding"** — Casual, iterative music work: grab something from the web, convert it, transpose it, tweak it, share a shorthand snippet.
3. **Be agent-friendly** — Tools return structured, parseable outputs (JSON) suitable for multi-step agent workflows.
4. **Fail gracefully** — When strict conversion fails, the server returns fallback data so downstream tasks can continue.

The server acts as a **music toolchain adapter** for MCP-compatible clients (Claude Desktop, Cursor, Windsurf, mcp-agent, LangChain, etc.), exposing music operations as tools that LLMs can invoke.

---

## Core Idea: Music Theory + Universal Shorthand
   
**Lilycode** refers to LilyPond—a powerful, text-based music notation system. The server uses LilyPond as the primary engraving/notation target when feasible, but does **not** require users or agents to speak LilyPond directly.

Instead, the server:

- **Ingests** music in many formats: MIDI, WAV, MP3, M4A, PDF, MusicXML, ABC, ChordPro, and informal text.
- **Converts** between formats using best-effort routing (often via intermediate formats like MusicXML).
- **Outputs** in whatever format is needed: PDF, LilyPond source, MusicXML, MIDI, audio, or a structured fallback.

Internally, LilyPond is preferred for high-quality engraving; externally, the server speaks whatever format is most convenient for the user or agent.

---

## Feature Scope (Expanded)

### 1. Fetching Existing Music from the Web

The server can **download publicly available music assets** from URLs. Supported inputs include:

- Direct links to MIDI, WAV, MP3, M4A, MusicXML, ABC, PDF, or LilyPond files.
- Any publicly reachable URL that returns a recognizable music format.

**Tool:** `fetch_music_from_web(url)`

This enables workflows like: "Grab this MuseScore link and convert it to PDF" or "Download this MIDI and transpose it."

---

### 2. Universal Format Conversion (Any-to-Any)

Users and agents should be able to:

- **Attach** a file (or provide a path/URL) in MIDI, WAV, MP3, M4A, LilyPond, MusicXML, ABC, ChordPro, or PDF.
- **Convert** to any of those formats.

All combinations from/to are in scope. When a direct route does not exist, the server:

- Uses intermediate formats (e.g., MIDI → MusicXML → LilyPond → PDF).
- Emits a **route plan** via `plan_music_conversion` so agents understand the path.
- Returns **fallback data** if conversion fails, rather than hard-failing.

**Tools:** `convert_music(input_ref, output_format)`, `plan_music_conversion(input_format, output_format)`, `audio_or_file_to_sheet(input_ref, prefer_output="pdf")`

---

### 3. Transposing a Song / Sheet Music

Transpose a song or sheet by a given number of semitones. Works on:

- Local files (MIDI, MusicXML, LilyPond, ABC, etc.)
- Downloaded assets from the web

**Tool:** `transpose_song(input_ref, semitones, output_format="musicxml")`

---

### 4. MuseScore Integration (Full Support)

The server aims for **complete MuseScore API coverage** where possible:

- **Public endpoints first** — Use any MuseScore API that does not require login.
- **Authenticated mode when needed** — When login is required, support:
  - **Environment variables** — e.g., `MUSESCORE_API_TOKEN`
  - **Session/SSE-style flows** — A tool like `set_musescore_auth_token` allows passing a token during an SSE or long-lived session, so the agent can obtain and inject credentials without hardcoding.

The goal is: anything that can be API'd from MuseScore without requiring interactive login should be exposed. When login is required, it must be configurable via env or session tools.

**Tools:** `musescore_api(endpoint, method, payload_json, base_url)`, `set_musescore_auth_token(token)`

---

### 5. Universal Text-Based Social Shorthand

A key design goal: **support the formats people actually use** when sharing music in informal contexts—Reddit comments, Discord, Twitter, SMS, etc.

Common use cases:

- "Try playing this" — Someone pastes a few chords or a riff.
- "Try using xyz notes and rhythm" — Informal notation in a comment.

The server identifies and normalizes these formats:

| Format | Use case | Example |
|--------|----------|---------|
| **ABC notation** | Compact, human-typable, widely supported | `X:1\nK:C\n|: C E G c |` |
| **ChordPro** | Chord + lyric lead sheets | `[C] Some [G] lyrics [Am] here` |
| **Freeform text** | Ad-hoc chord names, note letters | `C G Am F` or `try C E G` |

The server treats **ABC** as the primary universal text format and **ChordPro** as secondary. When input is ambiguous or non-standard, it normalizes to a **robust event-based fallback model** that preserves enough musical context for downstream tools.

**Tool:** `normalize_reddit_music_text(text, title="reddit_vibe_idea")`

**Tool:** `convert_text_notation_to_lily_or_fallback(text, target_format="lilypond", title="...")`

The MCP server should, where possible, **communicate in these shorthand formats** to users/agents, converting internally to LilyPond or other formal formats when needed.

---

## Error Handling: Robust Fallback and Partial Continuation

### Philosophy

Strict LilyPond conversion (or other parsers/compilers) can fail for many reasons:

- Malformed input from upstream tools or subagents
- Prompts that produce invalid LilyPond
- Missing or misconfigured binaries (lilypond, ffmpeg)
- Unsupported edge cases in the conversion pipeline

When a strict step fails, the **primary goal** is: **do not block the overall task**. The user or agent is often doing a multi-step workflow (e.g., "fetch → convert → transpose → export PDF"). A failure in one step should not cause the whole workflow to abort.

### Strategy

1. **Preserve upstream artifacts** — Keep whatever was successfully produced before the failure.
2. **Return a structured fallback** — Emit a `RobustMusicFallback` object containing:
   - `title`, `tonic`, `meter`, `tempo_bpm` (when known)
   - `notation_hint` (abc, chordpro, freeform, unknown)
   - `shorthand_text` — Raw text snapshot
   - `events` — List of note-like events (pitch, duration hints)
   - `warnings` — Human- and agent-readable diagnostics
3. **Set `ok=false`** — Indicate that the ideal path failed, but still return usable data.
4. **Allow downstream tools to continue** — Subagents can use the fallback to:
   - Retry with a different format
   - Present partial results to the user
   - Feed into other tools that accept looser input

### Canonical and Industry-Standard

The fallback model is designed to be:

- **Canonical** — A single, well-defined schema (`RobustMusicFallback`) used across all tools.
- **Intuitive** — Field names and structure map to common music concepts.
- **MCP-aligned** — JSON-serializable, suitable for tool results; follows patterns used by other MCP servers (structured errors, partial success).

---

## MCP Server Best Practices (2025–2026)

Based on current MCP ecosystem guidance:

1. **Structured tool outputs** — Return JSON (or structured text) so clients can parse results reliably.
2. **Explicit tool descriptions** — Clear docstrings so LLMs know when and how to call each tool.
3. **Transport flexibility** — Support stdio and, where applicable, SSE/HTTPS for cloud and IDE integration.
4. **Secrets via env and session** — Never hardcode credentials; support `MUSESCORE_API_TOKEN` and session-level token injection.
5. **Graceful degradation** — When external binaries or APIs are unavailable, return fallback data instead of crashing.
6. **Idempotency where possible** — Same input → same output for deterministic agent behavior.

---

## Summary

The lilycode MCP server is a **music toolchain MCP server** that:

- Fetches music from the web
- Converts between MIDI, audio, notation, and shorthand formats (any-to-any)
- Transposes songs
- Integrates with MuseScore (public + optional authenticated APIs)
- Normalizes and converts informal text notation (Reddit/phone shorthand)
- Emits robust fallback data on failures so agent workflows can continue

It is designed to be **canonical, intuitive, and industry-standard** for music-focused MCP servers.
