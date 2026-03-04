"""Rhythm Vibe Studio – unified single-page web UI.

A comprehensive music intelligence platform:
- AI chat assistant for music commands
- LilyPond score editor with real-time preview
- Music theory lab (scales, chords, rhythms, progressions)
- Format conversion and transposition
- Narrative composition engine
- Embedded audio and MIDI playback (Tone.js)
"""

from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from rhythm_vibe_mcp.composer import build_narrative_lily, write_lily_file
from rhythm_vibe_mcp.constants.binaries import FFMPEG_BINARY, LILYPOND_BINARY
from rhythm_vibe_mcp.constants.defaults import (
    ARTIFACT_SOURCE_GENERATED,
    ARTIFACT_SOURCE_WEB,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_TEXT_PIECE_TITLE,
    DEFAULT_TRANSPOSE_OUTPUT,
)
from rhythm_vibe_mcp.constants.env import ENV_MUSESCORE_TOKEN
from rhythm_vibe_mcp.constants.json import JSON_INDENT
from rhythm_vibe_mcp.constants.paths import is_remote_ref
from rhythm_vibe_mcp.constants.response_keys import (
    KEY_HINT,
    KEY_MESSAGE,
    KEY_OK,
    KEY_ROUTE,
)
from rhythm_vibe_mcp.conversion_graph import (
    FORMAT_JSON_FALLBACK,
    FORMAT_MUSICXML,
    FORMAT_PDF,
    SUPPORTED_CONVERSION_FORMATS,
    TEXT_TO_NOTATION_FORMATS,
    plan_conversion_route,
)
from rhythm_vibe_mcp.converters import (
    convert_abc_text_to_format,
    convert_any,
    normalize_text_to_fallback,
    transpose_with_music21,
)
from rhythm_vibe_mcp.fallbacks import fallback_from_error
from rhythm_vibe_mcp.integrations.web import download_music_asset
from rhythm_vibe_mcp.models import MusicArtifact, ToolResult
from rhythm_vibe_mcp.theory import (
    Chord,
    ChordType,
    FormAndStructure,
    MarkovGenerativeHarmony,
    MathematicalRhythm,
)
from rhythm_vibe_mcp.theory_primitives import PITCH_NAMES, Scales
from rhythm_vibe_mcp.utils import (
    artifacts_dir,
    binary_available,
    guess_format,
    looks_like_abc,
    normalize_text_input,
    run_cmd,
    workspace_root,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _gradio() -> Any:
    return importlib.import_module("gradio")


def _result_json(result: ToolResult) -> str:
    return json.dumps(result.model_dump(), indent=JSON_INDENT)


def _coerce_input_to_path(input_ref: str) -> Path:
    if is_remote_ref(input_ref):
        return download_music_asset(input_ref)
    path = Path(input_ref).expanduser()
    if not path.is_absolute():
        path = (workspace_root() / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input does not exist: {path}")
    return path


def _input_error(*, title: str, exc: Exception) -> str:
    return _result_json(
        ToolResult(
            ok=False,
            message=f"Input error: {exc}",
            fallback=fallback_from_error(
                title=title,
                warning=f"Use a valid local file path or URL. Details: {exc}",
            ),
        ),
    )


def _choose_input(input_ref: str, uploaded_file: str | None) -> str:
    if uploaded_file:
        return uploaded_file
    return (input_ref or "").strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  Backend Tool Wrappers
# ═══════════════════════════════════════════════════════════════════════════════


def _healthcheck_json() -> str:
    payload = {
        "workdir": str(workspace_root()),
        "artifacts_dir": str(artifacts_dir()),
        "musescore_auth_env_present": bool(os.getenv(ENV_MUSESCORE_TOKEN, "")),
        "musescore_session_token_set": False,
        "lilypond_available": binary_available(LILYPOND_BINARY),
        "ffmpeg_available": binary_available(FFMPEG_BINARY),
        "supported_formats": sorted(SUPPORTED_CONVERSION_FORMATS),
    }
    return json.dumps(payload, indent=JSON_INDENT)


def _fetch_music_from_web_json(url: str) -> str:
    try:
        path = download_music_asset(url)
        fmt = guess_format(path)
        return _result_json(
            ToolResult(
                ok=True,
                message="Download successful.",
                artifacts=[
                    MusicArtifact(
                        path=str(path),
                        format=fmt,  # type: ignore[arg-type]
                        source=ARTIFACT_SOURCE_WEB,
                        notes=[],
                    ),
                ],
            ),
        )
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=f"Fetch failed: {exc}",
                fallback=fallback_from_error(
                    title="fetch",
                    warning=f"Check URL and network access. Details: {exc}",
                ),
            ),
        )


def _plan_music_conversion_json(input_format: str, output_format: str) -> str:
    route = plan_conversion_route(input_format, output_format)
    if not route:
        return json.dumps(
            {
                KEY_OK: False,
                KEY_MESSAGE: f"No known route from {input_format} to {output_format}.",
                KEY_HINT: "Try one of: "
                + ", ".join(sorted(SUPPORTED_CONVERSION_FORMATS)),
            },
            indent=JSON_INDENT,
        )
    return json.dumps(
        {
            KEY_OK: True,
            KEY_MESSAGE: f"Route found: {' → '.join(route)}",
            KEY_ROUTE: route,
        },
        indent=JSON_INDENT,
    )


def _convert_music_json(input_ref: str, output_format: str) -> str:
    try:
        input_path = _coerce_input_to_path(input_ref)
    except Exception as exc:
        return _input_error(title="convert", exc=exc)
    return _result_json(convert_any(input_path, output_format))


def _transpose_song_json(
    input_ref: str,
    semitones: int,
    output_format: str = DEFAULT_TRANSPOSE_OUTPUT,
) -> str:
    try:
        input_path = _coerce_input_to_path(input_ref)
    except Exception as exc:
        return _input_error(title="transpose", exc=exc)
    return _result_json(
        transpose_with_music21(input_path, semitones, output_format=output_format),
    )


def _convert_text_notation_json(
    text: str,
    target_format: str = DEFAULT_OUTPUT_FORMAT,
    title: str = DEFAULT_TEXT_PIECE_TITLE,
) -> str:
    normalized = normalize_text_input(text)
    target = (target_format or DEFAULT_OUTPUT_FORMAT).lower()
    if target == FORMAT_JSON_FALLBACK:
        return _result_json(normalize_text_to_fallback(normalized, title=title))
    if looks_like_abc(normalized) and target in TEXT_TO_NOTATION_FORMATS:
        return _result_json(
            convert_abc_text_to_format(normalized, output_format=target, title=title),
        )
    if looks_like_abc(normalized) and target == FORMAT_PDF:
        intermediate = convert_abc_text_to_format(
            normalized, output_format=FORMAT_MUSICXML, title=title
        )
        if not intermediate.ok or not intermediate.artifacts:
            return _result_json(intermediate)
        pdf_result = convert_any(Path(intermediate.artifacts[0].path), FORMAT_PDF)
        return _result_json(pdf_result)
    fallback_result = normalize_text_to_fallback(normalized, title=title)
    if fallback_result.fallback:
        fallback_result = fallback_result.model_copy(
            update={
                "fallback": fallback_result.fallback.model_copy(
                    update={
                        "warnings": [
                            *fallback_result.fallback.warnings,
                            f"For target '{target}', paste ABC notation for best conversion.",
                        ],
                    },
                ),
            },
        )
    return _result_json(fallback_result)


def _compose_story_json(
    prompt: str,
    title: str = "Theme",
    tempo_bpm: int = 56,
    instrument: str = "Solo",
    output_format: str = DEFAULT_OUTPUT_FORMAT,
) -> str:
    try:
        lily = build_narrative_lily(
            prompt=normalize_text_input(prompt),
            title=title,
            tempo_bpm=tempo_bpm,
            instrument=instrument,
        )
        source_path = write_lily_file(title, lily)
        artifacts = [
            MusicArtifact(
                path=str(source_path),
                format="lilypond",
                source=ARTIFACT_SOURCE_GENERATED,
                notes=[f"Instrument: {instrument}"],
            ),
        ]
        message = "LilyPond composition generated."
        if output_format and output_format.lower() != DEFAULT_OUTPUT_FORMAT:
            conversion = convert_any(source_path, output_format.lower())
            if conversion.ok and conversion.artifacts:
                artifacts.extend(conversion.artifacts)
                message = f"Composition generated and converted to {output_format}."
            else:
                return _result_json(
                    ToolResult(
                        ok=True,
                        message="Composition created; optional conversion did not complete.",
                        artifacts=artifacts,
                        fallback=conversion.fallback,
                    ),
                )
        return _result_json(ToolResult(ok=True, message=message, artifacts=artifacts))
    except Exception as exc:
        return _result_json(
            ToolResult(
                ok=False,
                message=f"Composition failed: {exc}",
                fallback=fallback_from_error(
                    title=title, warning=f"Failed to generate composition: {exc}"
                ),
            ),
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  LilyPond Studio — constants, templates, snippets, backend
# ═══════════════════════════════════════════════════════════════════════════════

_LILY_DEFAULT_CODE = r"""\version "2.24.0"
\header {
  title = "Untitled"
  composer = "Composer"
}

\score {
  \relative c' {
    c4 d e f |
    g a b c |
    c b a g |
    f e d c |
  }
  \layout { }
  \midi { }
}
"""

LILY_TEMPLATES: dict[str, str] = {
    "Clean Slate": _LILY_DEFAULT_CODE,
    "Simple Melody": r"""\version "2.24.0"
\header { title = "Simple Melody" }
\score {
  \relative c'' {
    \key g \major \time 3/4
    g4 a b | c b a | g2 fis4 | g2. |
  }
  \layout { }
  \midi { \tempo 4 = 92 }
}
""",
    "Cello Theme": r"""\version "2.24.0"
\header { title = "Cello Theme" }
\score {
  \new Staff {
    \clef bass \key d \minor \time 4/4
    \relative c { d4 e f g | a2 d,2 | bes'4 a g f | e1 | }
  }
  \layout { }
  \midi { \tempo 4 = 72 }
}
""",
    "Piano Chords": r"""\version "2.24.0"
\header { title = "Chord Progression" }
upper = \relative c' { \key c \major \time 4/4 <c e g>1 | <f a c>1 | <g b d>1 | <c e g>1 | }
lower = \relative c { \key c \major \time 4/4 c1 | f,1 | g1 | c1 | }
\score {
  \new PianoStaff << \new Staff \upper \new Staff { \clef bass \lower } >>
  \layout { }
  \midi { \tempo 4 = 80 }
}
""",
    "String Quartet": r"""\version "2.24.0"
\header { title = "Quartet Opening" }
vlnI = \relative c'' { \key c \major \time 4/4 e2 d4 c | b2. a4 | }
vlnII = \relative c'' { \key c \major \time 4/4 c2 b4 a | g2. f4 | }
vla = \relative c' { \key c \major \time 4/4 \clef alto g2 f4 e | d2. c4 | }
vc = \relative c { \key c \major \time 4/4 \clef bass c2 g4 a | b2. c4 | }
\score {
  \new StaffGroup <<
    \new Staff { \set Staff.instrumentName = "Vln I" \vlnI }
    \new Staff { \set Staff.instrumentName = "Vln II" \vlnII }
    \new Staff { \set Staff.instrumentName = "Vla" \vla }
    \new Staff { \set Staff.instrumentName = "Vc" \vc }
  >>
  \layout { }  \midi { }
}
""",
    "Drum Pattern": r"""\version "2.24.0"
\header { title = "Basic Drum Beat" }
\score {
  \new DrumStaff {
    \drummode { \time 4/4 bd4 sn bd sn | bd8 bd sn4 bd8 bd sn4 | }
  }
  \layout { }
  \midi { \tempo 4 = 120 }
}
""",
}

_LILY_SNIPPETS: dict[str, str] = {
    "— notes —": "",
    "Clef: Treble": r"\clef treble",
    "Clef: Bass": r"\clef bass",
    "Clef: Alto": r"\clef alto",
    "— time/key —": "",
    "Time: 4/4": r"\time 4/4",
    "Time: 3/4": r"\time 3/4",
    "Time: 6/8": r"\time 6/8",
    "Key: C major": r"\key c \major",
    "Key: G major": r"\key g \major",
    "Key: D minor": r"\key d \minor",
    "— dynamics —": "",
    "pp": r"\pp",
    "mp": r"\mp",
    "mf": r"\mf",
    "ff": r"\ff",
    "crescendo": r"\< ... \!",
    "decrescendo": r"\> ... \!",
    "— articulation —": "",
    "Staccato": r"\staccato",
    "Accent": r"\accent",
    "Fermata": r"\fermata",
    "Trill": r"\trill",
    "— structure —": "",
    "Slur": r"( ... )",
    "Tie": "~ ",
    "Tuplet 3:2": r"\tuplet 3/2 { c8 d e }",
    "Repeat": r'\repeat volta 2 { \relative c\' { c1 } }',
    "Double barline": r'\bar "||"',
    "Final barline": r'\bar "|."',
    "— tempo —": "",
    "Tempo 60": r"\tempo 4=60",
    "Tempo 80": r"\tempo 4=80",
    "Tempo 120": r"\tempo 4=120",
}


def _svg_cleanup(svg_content: str) -> str:
    svg_content = re.sub(r"<\?xml[^>]*\?>", "", svg_content)
    svg_content = re.sub(r"<!DOCTYPE[^>]*>", "", svg_content)
    svg_content = re.sub(
        r'(<svg[^>]*?)\s+width="[0-9.]+[a-z]*"', r'\1 width="100%"', svg_content
    )
    svg_content = re.sub(
        r'(<svg[^>]*?)\s+height="[0-9.]+[a-z]*"', r"\1", svg_content
    )
    return svg_content.strip()


def _run_lily_cmd(cmd: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "LilyPond timed out after 30 seconds."
    except Exception as exc:
        return -1, "", f"LilyPond subprocess error: {exc}"


def _compile_lily_preview(code: str) -> tuple[str, str, str | None, str | None]:
    """Compile LilyPond code → (svg_html, logs, pdf_path, midi_path)."""
    if not code or not code.strip():
        return "", "No code provided.", None, None
    if not binary_available(LILYPOND_BINARY):
        return (
            '<div class="lily-error"><strong>LilyPond not found.</strong></div>',
            "LilyPond binary not found.",
            None,
            None,
        )
    out_dir = artifacts_dir()
    stem = f"lily_prev_{int(time.monotonic() * 1000) % 99991}"
    for old in out_dir.glob(f"{stem}*"):
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ly", delete=False, encoding="utf-8"
    ) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(code)
    try:
        svg_exit, _, svg_err = _run_lily_cmd(
            [LILYPOND_BINARY, "-dbackend=svg", "-dno-point-and-click",
             "-o", str(out_dir / stem), str(tmp_path)]
        )
        logs = svg_err.strip()
        svg_files = sorted(out_dir.glob(f"{stem}*.svg"))
        if svg_files:
            pages = []
            for f in svg_files:
                raw = f.read_text(encoding="utf-8", errors="replace")
                pages.append(f'<div class="lily-page">{_svg_cleanup(raw)}</div>')
            svg_html = '<div class="lily-preview-wrap">' + "\n".join(pages) + "</div>"
        else:
            err_body = logs or "Compilation produced no SVG output."
            svg_html = f'<div class="lily-error"><pre>{err_body}</pre></div>'
        _run_lily_cmd(
            [LILYPOND_BINARY, "-o", str(out_dir / stem), str(tmp_path)]
        )
        pdf_path = out_dir / f"{stem}.pdf"
        midi_path = out_dir / f"{stem}.midi"
        if not midi_path.exists():
            alt = out_dir / f"{stem}.mid"
            if alt.exists():
                midi_path = alt
        ok = bool(svg_files)
        status_line = (
            "✅ Compiled successfully."
            if ok and svg_exit == 0
            else "⚠️ Compilation error — see logs."
        )
        return (
            svg_html,
            (logs + "\n\n" + status_line).strip() if logs else status_line,
            str(pdf_path) if pdf_path.exists() else None,
            str(midi_path) if midi_path.exists() else None,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Theory Backend
# ═══════════════════════════════════════════════════════════════════════════════

_SCALE_NAMES = [
    "MAJOR", "NATURAL_MINOR", "HARMONIC_MINOR", "MELODIC_MINOR",
    "DORIAN", "PHRYGIAN", "LYDIAN", "MIXOLYDIAN", "AEOLIAN", "LOCRIAN",
    "MAJOR_PENTATONIC", "MINOR_PENTATONIC", "BLUES", "WHOLE_TONE", "OCTATONIC_HW",
]


def _note_grid_html(active_pcs: list[int]) -> str:
    """Chromatic note grid with active notes highlighted."""
    cells = []
    for i, name in enumerate(PITCH_NAMES):
        active = (i % 12) in [p % 12 for p in active_pcs]
        cls = "note-active" if active else "note-inactive"
        cells.append(f'<div class="note-cell {cls}">{name}</div>')
    return '<div class="note-grid">' + "".join(cells) + "</div>"


def _rhythm_grid_html(pattern: list[int]) -> str:
    """Rhythm grid with hits highlighted."""
    cells = []
    for i, hit in enumerate(pattern):
        cls = "beat-hit" if hit else "beat-rest"
        label = str(i + 1)
        cells.append(f'<div class="beat-cell {cls}">{label}</div>')
    return '<div class="beat-grid">' + "".join(cells) + "</div>"


def _theory_explore_scale(root_name: str, scale_name: str) -> str:
    root_idx = PITCH_NAMES.index(root_name) if root_name in PITCH_NAMES else 0
    pattern = getattr(Scales, scale_name, Scales.MAJOR)
    notes = Scales.generate_scale(root_idx, pattern)
    names = [PITCH_NAMES[n % 12] for n in notes]
    label = scale_name.replace("_", " ").title()
    html = f'<div class="theory-out">'
    html += f"<h4>{root_name} {label}</h4>"
    html += f'<p style="font-size:1.15rem;letter-spacing:2px"><strong>{" – ".join(names)}</strong></p>'
    html += f"<p><em>Intervals:</em> <code>{pattern}</code></p>"
    html += _note_grid_html(notes)
    html += "</div>"
    return html


def _theory_build_chord(root_name: str, chord_type_name: str) -> str:
    root_idx = PITCH_NAMES.index(root_name) if root_name in PITCH_NAMES else 0
    ct = ChordType[chord_type_name]
    chord = Chord(root_idx, ct.value)
    names = [PITCH_NAMES[p] for p in chord.pitches]
    label = chord_type_name.replace("_", " ").title()
    html = f'<div class="theory-out">'
    html += f"<h4>{root_name} {label}</h4>"
    html += f'<p style="font-size:1.15rem;letter-spacing:2px"><strong>{" – ".join(names)}</strong></p>'
    html += f"<p><em>Intervals:</em> <code>{ct.value}</code></p>"
    html += _note_grid_html(chord.pitches)
    html += "</div>"
    return html


def _theory_euclidean(pulses: int, steps: int) -> str:
    pulses, steps = max(1, min(int(pulses), 16)), max(2, min(int(steps), 32))
    if pulses > steps:
        pulses, steps = steps, pulses
    pattern = MathematicalRhythm.bjorklund_euclidean(pulses, steps)
    syncopation = MathematicalRhythm.longuet_higgins_syncopation(pattern)
    visual = " ".join(["●" if p else "○" for p in pattern])
    html = f'<div class="theory-out">'
    html += f"<h4>Euclidean Rhythm E({pulses}, {steps})</h4>"
    html += f"<p><strong>{visual}</strong></p>"
    html += f"<p><em>Syncopation index:</em> {syncopation:.3f}</p>"
    html += _rhythm_grid_html(pattern)
    html += "</div>"
    return html


def _theory_progression(form_type: str, start_chord: str, depth: int) -> str:
    form = FormAndStructure.generate_form(form_type)
    markov = MarkovGenerativeHarmony.highly_probable_path(start_chord, int(depth))
    label = form_type.replace("_", " ").title()
    html = f'<div class="theory-out">'
    html += f"<h4>{label} Form</h4>"
    html += f'<p><strong>Structure:</strong> {" → ".join(form)}</p>'
    html += '<table class="prog-table"><tr><th>Section</th><th>Typical Chords</th></tr>'
    for section in form:
        chords = FormAndStructure.typical_chord_progression(section)
        html += f"<tr><td>{section}</td><td>{' – '.join(chords)}</td></tr>"
    html += "</table>"
    html += f"<h4>Markov Chain ({start_chord} → {depth} steps)</h4>"
    html += f'<p style="font-size:1.1rem"><strong>{" → ".join(markov)}</strong></p>'
    html += "</div>"
    return html


# ═══════════════════════════════════════════════════════════════════════════════
#  MIDI Player Helper
# ═══════════════════════════════════════════════════════════════════════════════


def _midi_player_html(midi_path: str) -> str:
    """Generate HTML MIDI player with embedded base64 data for Tone.js playback."""
    try:
        midi_bytes = Path(midi_path).read_bytes()
        b64 = base64.b64encode(midi_bytes).decode("ascii")
        name = Path(midi_path).name
        return (
            f'<div class="midi-player" data-midi="{b64}">'
            f'<button class="midi-btn rvm-midi-play">▶ Play</button>'
            f'<button class="midi-btn rvm-midi-stop">⏹ Stop</button>'
            f'<span class="midi-status">🎹 {name}</span>'
            f"</div>"
        )
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  Workspace Result Handler
# ═══════════════════════════════════════════════════════════════════════════════


def _update_workspace(raw_json: str) -> tuple[str, Any, str, Any, Any, str]:
    """Parse tool result JSON → (status_md, audio_update, midi_html, dl1, dl2, raw_json).

    Returns gr.update() values for the shared workspace output components.
    """
    gr = _gradio()
    try:
        data = json.loads(raw_json)
    except Exception:
        return (
            "⚠️ Could not parse output",
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            raw_json,
        )

    ok = data.get("ok", True)
    parts = ["✅ **Success**" if ok else "⚠️ **Needs attention**"]
    msg = data.get("message", "")
    if msg:
        parts.append(msg)

    audio_path = None
    midi_html = ""
    dl_updates: list[Any] = [
        gr.update(visible=False),
        gr.update(visible=False),
    ]
    dl_idx = 0

    for art in data.get("artifacts", []) or []:
        path_str = art.get("path", "")
        fmt = art.get("format", "")
        path = Path(path_str) if path_str else None
        if not path or not path.exists():
            parts.append(f"📄 {fmt}: *file not found*")
            continue
        parts.append(f"📄 **{fmt.upper()}**: `{path.name}`")
        if fmt in ("wav", "mp3", "m4a"):
            audio_path = str(path)
        elif fmt == "midi" and not midi_html:
            midi_html = _midi_player_html(str(path))
        if dl_idx < 2:
            dl_updates[dl_idx] = gr.update(
                visible=True, value=str(path), label=f"⬇ {path.name}"
            )
            dl_idx += 1

    fb = data.get("fallback") or {}
    warnings = fb.get("warnings", []) if isinstance(fb, dict) else []
    if warnings:
        parts.append("\n**Warnings:** " + "; ".join(warnings))

    return (
        "\n\n".join(parts),
        gr.update(value=audio_path, visible=bool(audio_path)),
        midi_html,
        dl_updates[0],
        dl_updates[1],
        json.dumps(data, indent=2),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  AI Chat Dispatch
# ═══════════════════════════════════════════════════════════════════════════════

_AI_HELP = """**🤖 AI Music Assistant — Commands**

**Theory:**
• `C major scale` — explore any scale (major, minor, dorian, etc.)
• `A minor chord` — build any chord (major, minor, dim, aug, 7th…)
• `euclidean 5 8` — generate Euclidean rhythm
• `progression pop` — song form + chord progressions

**Create:**
• `compose [description]` — generate a LilyPond piece
• `compose cello sunset theme` — with instrument + mood

**Tools:**
• `health` — system diagnostics
• `help` — show this guide

**Text Notation:**
• Paste ABC notation directly and it will be parsed
"""


def _parse_root(text: str) -> int:
    upper = text.upper()
    for idx, name in sorted(enumerate(PITCH_NAMES), key=lambda x: -len(x[1])):
        if name in upper:
            return idx
    return 0


def _parse_scale_type(text: str) -> str:
    mapping = {
        "harmonic minor": "HARMONIC_MINOR",
        "melodic minor": "MELODIC_MINOR",
        "natural minor": "NATURAL_MINOR",
        "minor pentatonic": "MINOR_PENTATONIC",
        "major pentatonic": "MAJOR_PENTATONIC",
        "whole tone": "WHOLE_TONE",
        "minor": "NATURAL_MINOR",
        "major": "MAJOR",
        "dorian": "DORIAN",
        "phrygian": "PHRYGIAN",
        "lydian": "LYDIAN",
        "mixolydian": "MIXOLYDIAN",
        "aeolian": "AEOLIAN",
        "locrian": "LOCRIAN",
        "blues": "BLUES",
        "pentatonic": "MAJOR_PENTATONIC",
        "octatonic": "OCTATONIC_HW",
    }
    lower = text.lower()
    for kw, attr in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if kw in lower:
            return attr
    return "MAJOR"


def _parse_chord_type(text: str) -> ChordType:
    mapping = {
        "major seventh": ChordType.MAJOR_SEVENTH,
        "maj7": ChordType.MAJOR_SEVENTH,
        "minor seventh": ChordType.MINOR_SEVENTH,
        "min7": ChordType.MINOR_SEVENTH,
        "m7": ChordType.MINOR_SEVENTH,
        "dominant seventh": ChordType.DOMINANT_SEVENTH,
        "dom7": ChordType.DOMINANT_SEVENTH,
        "half diminished": ChordType.HALF_DIMINISHED_SEVENTH,
        "fully diminished": ChordType.FULLY_DIMINISHED_SEVENTH,
        "diminished": ChordType.DIMINISHED,
        "dim": ChordType.DIMINISHED,
        "augmented": ChordType.AUGMENTED,
        "aug": ChordType.AUGMENTED,
        "sus2": ChordType.SUS2,
        "sus4": ChordType.SUS4,
        "minor": ChordType.MINOR,
        "min": ChordType.MINOR,
        "major": ChordType.MAJOR,
        "maj": ChordType.MAJOR,
    }
    lower = text.lower()
    for kw, ct in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if kw in lower:
            return ct
    return ChordType.MAJOR


def _ai_respond(
    message: str,
    history: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Route chat message to appropriate backend and return (cleared_input, updated_history)."""
    msg = message.strip()
    if not msg:
        return "", history

    def _add(user: str, bot: str) -> list[dict[str, Any]]:
        return [*history, {"role": "user", "content": user}, {"role": "assistant", "content": bot}]

    lower = msg.lower()

    # Help
    if lower in ("help", "?", "commands", "h"):
        history = _add(msg, _AI_HELP)
        return "", history

    # Health
    if any(w in lower for w in ("health", "status", "diagnostic")):
        raw = _healthcheck_json()
        data = json.loads(raw)
        lines = [f"- **{k}:** `{v}`" for k, v in data.items()]
        resp = "### 🔧 System Status\n\n" + "\n".join(lines)
        history = _add(msg, resp)
        return "", history

    # Scale
    if "scale" in lower:
        root_idx = _parse_root(lower)
        scale_attr = _parse_scale_type(lower)
        pattern = getattr(Scales, scale_attr, Scales.MAJOR)
        notes = Scales.generate_scale(root_idx, pattern)
        names = [PITCH_NAMES[n % 12] for n in notes]
        label = scale_attr.replace("_", " ").title()
        resp = f"**{PITCH_NAMES[root_idx]} {label}**\n\nNotes: **{' – '.join(names)}**\n\nIntervals: `{pattern}`"
        history = _add(msg, resp)
        return "", history

    # Chord
    if "chord" in lower and "progression" not in lower:
        root_idx = _parse_root(lower)
        ct = _parse_chord_type(lower)
        chord = Chord(root_idx, ct.value)
        names = [PITCH_NAMES[p] for p in chord.pitches]
        label = ct.name.replace("_", " ").title()
        resp = f"**{PITCH_NAMES[root_idx]} {label}**\n\nNotes: **{' – '.join(names)}**\n\nIntervals: `{ct.value}`"
        history = _add(msg, resp)
        return "", history

    # Euclidean rhythm
    if "euclidean" in lower or "bjorklund" in lower:
        nums = re.findall(r"\d+", msg)
        pulses = int(nums[0]) if len(nums) >= 1 else 3
        steps = int(nums[1]) if len(nums) >= 2 else 8
        if pulses > steps:
            pulses, steps = steps, pulses
        pattern = MathematicalRhythm.bjorklund_euclidean(pulses, steps)
        visual = " ".join(["●" if p else "○" for p in pattern])
        sync = MathematicalRhythm.longuet_higgins_syncopation(pattern)
        resp = f"**E({pulses}, {steps})**\n\n{visual}\n\nSyncopation: {sync:.3f}"
        history = _add(msg, resp)
        return "", history

    # Progression
    if "progression" in lower:
        form_map = {
            "pop": "pop_modern",
            "aaba": "aaba",
            "sonata": "sonata",
            "rondo": "rondo",
            "blues": "blues_12_bar",
            "strophic": "strophic",
        }
        form_type = "pop_modern"
        for k, v in form_map.items():
            if k in lower:
                form_type = v
                break
        form = FormAndStructure.generate_form(form_type)
        lines = [f"**{form_type.replace('_', ' ').title()}**: {' → '.join(form)}\n"]
        for section in form:
            chords = FormAndStructure.typical_chord_progression(section)
            lines.append(f"- **{section}**: {' – '.join(chords)}")
        markov = MarkovGenerativeHarmony.highly_probable_path("I", 8)
        lines.append(f"\n**Markov (I → 8):** {' → '.join(markov)}")
        history = _add(msg, "\n".join(lines))
        return "", history

    # Compose
    if any(w in lower for w in ("compose", "create music", "write music", "generate music")):
        instruments = {
            "cello": "Cello",
            "violin": "Violin",
            "viola": "Viola",
            "flute": "Flute",
            "piano": "Piano",
        }
        instrument = "Solo"
        for k, v in instruments.items():
            if k in lower:
                instrument = v
                break
        raw = _compose_story_json(prompt=msg, instrument=instrument)
        data = json.loads(raw)
        if data.get("ok"):
            files = [a["path"] for a in data.get("artifacts", [])]
            resp = f"✅ **Composition generated!** ({instrument})\n\n"
            resp += "\n".join([f"- `{Path(f).name}`" for f in files])
            resp += "\n\nLoad it in the **Score Editor** below to view and edit."
        else:
            resp = f"⚠️ {data.get('message', 'Composition failed')}"
        history = _add(msg, resp)
        return "", history

    # Default: try as text notation
    try:
        raw = _convert_text_notation_json(text=msg)
        data = json.loads(raw)
        if data.get("ok"):
            arts = data.get("artifacts", [])
            resp = f"✅ Interpreted as text notation.\n\n{data.get('message', '')}"
            for a in arts:
                resp += f"\n- `{Path(a['path']).name}` ({a['format']})"
        else:
            fb = data.get("fallback", {}) or {}
            events = fb.get("events", [])
            if events:
                resp = f"Parsed {len(events)} event(s) from your input.\n\n"
                resp += f"Notation hint: {fb.get('notation_hint', 'unknown')}"
            else:
                resp = "I'm not sure what to do with that. Type **help** for commands."
        history = _add(msg, resp)
    except Exception:
        history = _add(msg, "Something went wrong. Type **help** for commands.")
    return "", history


# ═══════════════════════════════════════════════════════════════════════════════
#  Sample MP3 Finder
# ═══════════════════════════════════════════════════════════════════════════════


def _discover_sample_mp3_urls(max_results: int = 12) -> list[str]:
    source_pages = [
        "https://samplelib.com/mp3.html",
        "https://samplelib.com/",
        "https://www.soundhelix.com/audio-examples",
    ]
    found: list[str] = []
    seen: set[str] = set()
    for page_url in source_pages:
        try:
            resp = httpx.get(page_url, timeout=12.0, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            continue
        abs_matches = re.findall(
            r'https?://[^"\'\s>]+\.mp3(?:\?[^"\'\s>]*)?', html, flags=re.IGNORECASE
        )
        rel_matches = re.findall(
            r'href=["\']([^"\']+\.mp3(?:\?[^"\']*)?)["\']', html, flags=re.IGNORECASE
        )
        candidates = [*abs_matches, *[urljoin(page_url, m) for m in rel_matches]]
        for c in candidates:
            n = c.strip()
            if not n.lower().startswith(("http://", "https://")) or n in seen:
                continue
            seen.add(n)
            found.append(n)
            if len(found) >= max_results:
                return found
    if found:
        return found
    try:
        sr = httpx.get(
            "https://archive.org/advancedsearch.php"
            "?q=mediatype%3Aaudio%20AND%20format%3A%22VBR%20MP3%22"
            "&fl%5B%5D=identifier&rows=25&page=1&output=json",
            timeout=12.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        sr.raise_for_status()
        docs = (sr.json().get("response") or {}).get("docs", [])
    except Exception:
        return found
    for doc in docs:
        identifier = str(doc.get("identifier", "")).strip()
        if not identifier:
            continue
        try:
            mr = httpx.get(
                f"https://archive.org/metadata/{identifier}",
                timeout=12.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            mr.raise_for_status()
            files = mr.json().get("files", [])
        except Exception:
            continue
        for fe in files:
            name = str(fe.get("name", "")).strip()
            if not name.lower().endswith(".mp3"):
                continue
            candidate = f"https://archive.org/download/{identifier}/{name}"
            if candidate in seen:
                continue
            seen.add(candidate)
            found.append(candidate)
            if len(found) >= max_results:
                return found
    return found


# ═══════════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════════

_UI_CSS = """
/* ── Global ── */
.studio-header { text-align: center; padding: 0.4rem 0 0; margin-bottom: 0; }
.studio-header h1 {
    margin: 0 !important; font-size: 1.65rem;
    background: linear-gradient(135deg, #ff9800, #ff5722);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.studio-sub {
    text-align: center; color: var(--body-text-color-subdued);
    font-size: 0.88rem; margin: 0.1rem 0 0.5rem;
}
/* ── Chat ── */
.chat-row { gap: 6px !important; }
/* ── Note grid ── */
.note-grid { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; margin: 0.5rem 0; }
.note-cell {
    width: 38px; height: 38px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 0.78rem; transition: all 0.2s;
    border: 2px solid var(--border-color-primary);
}
.note-active { background: #ff9800 !important; border-color: #ff9800 !important; color: #fff !important; box-shadow: 0 0 8px rgba(255,152,0,0.4); }
.note-inactive { background: var(--background-fill-secondary); color: var(--body-text-color-subdued); }
/* ── Beat grid ── */
.beat-grid { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; margin: 0.5rem 0; }
.beat-cell {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 0.72rem; transition: all 0.2s;
}
.beat-hit { background: #ff9800; color: #fff; }
.beat-rest { background: transparent; border: 2px solid var(--border-color-primary); color: var(--body-text-color-subdued); }
/* ── Progression table ── */
.prog-table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; }
.prog-table td, .prog-table th { padding: 6px 10px; border: 1px solid var(--border-color-primary); font-size: 0.85rem; }
.prog-table th { background: var(--background-fill-secondary); font-weight: 600; }
/* ── Theory output ── */
.theory-out { margin-top: 0.4rem; }
/* ── MIDI Player ── */
.midi-player {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; background: var(--background-fill-secondary);
    border-radius: 8px; margin: 0.5rem 0;
}
.midi-btn {
    padding: 6px 14px; border-radius: 16px; border: none; cursor: pointer;
    font-weight: 600; font-size: 0.82rem; transition: opacity 0.2s;
}
.midi-btn:hover { opacity: 0.85; }
.rvm-midi-play { background: #ff9800; color: #fff; }
.rvm-midi-stop { background: #ef5350; color: #fff; }
.midi-status { color: var(--body-text-color-subdued); font-size: 0.82rem; }
/* ── LilyPond Studio ── */
.studio-toolbar { gap: 6px !important; align-items: flex-end !important; }
.studio-row { gap: 0.75rem !important; }
#rvm-editor-wrap {
    width: 100%; height: 480px; border: 1px solid #3c4048;
    border-radius: 6px; overflow: hidden; position: relative;
    background: #1e1e1e; box-shadow: 0 2px 8px rgba(0,0,0,0.35);
}
#rvm-monaco-host { width: 100%; height: 100%; }
#rvm-monaco-loading {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    color: #888; font-family: sans-serif; font-size: 0.9rem; pointer-events: none;
}
#lily-preview-html > div {
    min-height: 440px; max-height: 70vh; overflow-y: auto;
    background: #ffffff; border: 1px solid #d0d5dd; border-radius: 6px;
    padding: 12px 16px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.06);
}
.lily-preview-wrap { display: block; }
.lily-page { display: block; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb; }
.lily-page:last-child { border-bottom: none; margin-bottom: 0; }
.lily-page svg { display: block !important; width: 100% !important; height: auto !important; }
.lily-placeholder {
    display: flex; flex-direction: column; gap: 0.5rem;
    align-items: center; justify-content: center; height: 420px;
    color: #9ca3af; font-style: italic; background: #f9fafb; border-radius: 6px;
}
.lily-error { padding: 12px; background: #fff3f3; border-left: 4px solid #e74c3c; border-radius: 4px; color: #c0392b; font-size: 0.85rem; }
.lily-error pre { margin: 6px 0 0; white-space: pre-wrap; word-break: break-all; font-family: monospace; font-size: 0.8rem; }
.lily-dl-row { gap: 8px !important; margin-top: 4px !important; }
/* ── Result card ── */
.result-card { border: 1px solid var(--border-color-primary); border-radius: 0.6rem; padding: 0.7rem; }
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  JavaScript — Monaco + Tone.js + MIDI Player
# ═══════════════════════════════════════════════════════════════════════════════

_UI_JS = r"""
() => {
    /* ── Tone.js + @tonejs/midi CDN loading ── */
    let _toneLoading = false;
    let _currentSynths = [];

    function _loadScript(url, cb) {
        const s = document.createElement('script');
        s.src = url; s.onload = cb;
        s.onerror = () => console.warn('CDN load failed:', url);
        document.head.appendChild(s);
    }

    function ensureTone(cb) {
        if (window.Tone && window.Midi) { cb(); return; }
        if (_toneLoading) { setTimeout(() => ensureTone(cb), 300); return; }
        _toneLoading = true;
        _loadScript('https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js', () => {
            _loadScript('https://cdn.jsdelivr.net/npm/@tonejs/midi@2.0.28/build/Midi.js', cb);
        });
    }

    window.__rvmPlayMidi = function(b64) {
        ensureTone(async () => {
            window.__rvmStopMidi();
            try {
                const bin = atob(b64);
                const bytes = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                const midi = new Midi(bytes.buffer);
                await Tone.start();
                const now = Tone.now() + 0.1;
                let maxT = 0;
                midi.tracks.forEach(track => {
                    if (!track.notes.length) return;
                    const synth = new Tone.PolySynth(Tone.Synth, {
                        maxPolyphony: 16,
                        envelope: { attack: 0.02, decay: 0.1, sustain: 0.3, release: 0.4 }
                    }).toDestination();
                    _currentSynths.push(synth);
                    track.notes.forEach(n => {
                        synth.triggerAttackRelease(n.name, n.duration, now + n.time, n.velocity);
                        maxT = Math.max(maxT, n.time + n.duration);
                    });
                });
                document.querySelectorAll('.midi-status').forEach(el => el.textContent = '▶ Playing...');
                setTimeout(() => {
                    document.querySelectorAll('.midi-status').forEach(el => el.textContent = '⏹ Done');
                }, (maxT + 1) * 1000);
            } catch(e) {
                console.error('MIDI play error:', e);
                document.querySelectorAll('.midi-status').forEach(el => el.textContent = '❌ Error');
            }
        });
    };

    window.__rvmStopMidi = function() {
        _currentSynths.forEach(s => { try { s.releaseAll(); s.dispose(); } catch(e){} });
        _currentSynths = [];
        document.querySelectorAll('.midi-status').forEach(el => el.textContent = '⏹ Stopped');
    };

    /* Event delegation for MIDI buttons */
    if (!window.__rvmMidiBound) {
        window.__rvmMidiBound = true;
        document.addEventListener('click', (e) => {
            const play = e.target.closest('.rvm-midi-play');
            if (play) {
                const container = play.closest('.midi-player');
                const b64 = container ? container.dataset.midi : null;
                if (b64) window.__rvmPlayMidi(b64);
                return;
            }
            if (e.target.closest('.rvm-midi-stop')) { window.__rvmStopMidi(); }
        });
    }

    /* ── Monaco LilyPond Monarch tokenizer ── */
    const LILY_MONARCH = {
        tokenPostfix: '.ly',
        brackets: [
            { open: '(', close: ')', token: 'bracket.parenthesis' },
            { open: '{', close: '}', token: 'bracket.curly' },
            { open: '[', close: ']', token: 'bracket.square' },
            { open: '<<', close: '>>', token: 'bracket.triangle' },
        ],
        tokenizer: {
            root: [
                { regex: /[-_^]?\\[a-zA-Z][a-zA-Z-]*/, action: { token: 'keyword' } },
                { regex: /"/, action: { token: 'string', bracket: '@open', next: '@dstring' } },
                { regex: /%{/, action: { token: 'comment', next: '@mlcomment' } },
                { regex: /%.+/, action: { token: 'comment' } },
                { regex: /<</, action: { token: 'bracket.triangle' } },
                { regex: />>/, action: { token: 'bracket.triangle' } },
                { regex: /</, action: { token: 'string' } },
                { regex: />/, action: { token: 'string' } },
                {
                    regex: /\b[a-h](is|es)*(is|es)*[,']*(\\!|[?!])?(?![A-Za-z])(128|64|32|16|8|4|2|1|\\breve|\\longa)?[.]*(\s*\*\s*\d+(\/\d+)?)*?/,
                    action: { token: 'string' }
                },
                { regex: /\b[rs](?![A-Za-z])(128|64|32|16|8|4|2|1)?[.]*/, action: { token: 'type.identifier' } },
                { regex: /\b(128|64|32|16|8|4|2|1)\b/, action: { token: 'number' } },
                { regex: /\d+\/\d+/, action: { token: 'number.fraction' } },
                { regex: /\d+/, action: { token: 'number' } },
                { regex: /[{}()[\]]/, action: { token: '@brackets' } },
                { include: '@whitespace' },
                { regex: /[^\s{}\[\]()<>%"\\]+/, action: { token: 'identifier' } },
            ],
            whitespace: [
                { regex: /[ \t\r\n]+/, action: { token: 'white' } },
            ],
            mlcomment: [
                { regex: /[^%]+/, action: { token: 'comment' } },
                { regex: /%{/, action: { token: 'comment', next: '@push' } },
                { regex: /%}/, action: { token: 'comment', next: '@pop' } },
                { regex: /[%]/, action: { token: 'comment' } },
            ],
            dstring: [
                { regex: /[^\\"]+/, action: { token: 'string' } },
                { regex: /\\./, action: { token: 'string.escape' } },
                { regex: /"/, action: { token: 'string', bracket: '@close', next: '@pop' } },
            ],
        },
    };

    /* ── Monaco initialisation ── */
    function initMonaco() {
        const hostEl = document.getElementById('rvm-monaco-host');
        if (!hostEl || window.__rvmEditor) return;

        if (!window.__rvmLilyRegistered) {
            window.__rvmLilyRegistered = true;
            monaco.languages.register({ id: 'lilypond' });
            monaco.languages.setMonarchTokensProvider('lilypond', LILY_MONARCH);
            monaco.languages.setLanguageConfiguration('lilypond', {
                comments: { lineComment: '%', blockComment: ['%{', '%}'] },
                brackets: [['(', ')'], ['{', '}'], ['[', ']'], ['<<', '>>']],
                autoClosingPairs: [
                    { open: '{', close: '}' }, { open: '(', close: ')' },
                    { open: '[', close: ']' }, { open: '"', close: '"' },
                    { open: '<<', close: '>>' },
                ],
            });
        }

        const loadingEl = document.getElementById('rvm-monaco-loading');
        if (loadingEl) loadingEl.style.display = 'none';

        const backingEl = document.querySelector('#lily-code-backing textarea');
        const initialCode = (backingEl && backingEl.value) || '';

        window.__rvmEditor = monaco.editor.create(hostEl, {
            value: initialCode,
            language: 'lilypond',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace",
            lineNumbers: 'on',
            wordWrap: 'off',
            autoClosingBrackets: 'always',
            scrollBeyondLastLine: false,
            renderLineHighlight: 'all',
            smoothScrolling: true,
            cursorBlinking: 'smooth',
            padding: { top: 8, bottom: 8 },
        });

        function syncToGradio() {
            const val = window.__rvmEditor.getValue();
            const ta = document.querySelector('#lily-code-backing textarea');
            if (!ta) return;
            try {
                const ns = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value').set;
                ns.call(ta, val);
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            } catch(e) {
                ta.value = val;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }

        window.__rvmEditor.onDidChangeModelContent(() => syncToGradio());

        window.__rvmLoadTemplate = function(code) {
            if (window.__rvmEditor) {
                window.__rvmEditor.setValue(code || '');
                window.__rvmEditor.focus();
            }
        };

        window.__rvmHighlightErrors = function(logs) {
            if (!window.__rvmEditor || !logs) return;
            const model = window.__rvmEditor.getModel();
            if (!model) return;
            const markers = [];
            const rx = /(?:.*\.ly:)?(\d+):(\d+):\s*([ew].*)/gm;
            let m;
            while ((m = rx.exec(logs)) !== null) {
                markers.push({
                    severity: monaco.MarkerSeverity.Error,
                    startLineNumber: parseInt(m[1], 10),
                    startColumn: parseInt(m[2], 10),
                    endLineNumber: parseInt(m[1], 10),
                    endColumn: parseInt(m[2], 10) + 10,
                    message: m[3].trim(),
                });
            }
            monaco.editor.setModelMarkers(model, 'lilypond', markers);
        };
    }

    function loadMonacoCDN() {
        if (window.__rvmMonacoLoading) return;
        window.__rvmMonacoLoading = true;
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs/loader.js';
        script.onload = function() {
            window.require.config({
                paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' }
            });
            window.require(['vs/editor/editor.main'], function() { initMonaco(); });
        };
        script.onerror = function() {
            const el = document.getElementById('rvm-monaco-loading');
            if (el) el.textContent = 'Monaco CDN unavailable — use the text box below.';
        };
        document.head.appendChild(script);
    }

    function waitForHost(maxMs, cb) {
        const start = Date.now();
        function check() {
            if (document.getElementById('rvm-monaco-host')) { cb(); return; }
            if (Date.now() - start < maxMs) requestAnimationFrame(check);
        }
        check();
    }

    waitForHost(8000, loadMonacoCDN);
}
"""

_MONACO_EDITOR_HTML = (
    '<div id="rvm-editor-wrap">'
    '<div id="rvm-monaco-loading">Loading Monaco editor\u2026</div>'
    '<div id="rvm-monaco-host" style="width:100%;height:100%;"></div>'
    "</div>"
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Build App — Single-Page Layout
# ═══════════════════════════════════════════════════════════════════════════════

_FORMAT_CHOICES = sorted(
    ["abc", "json_fallback", "lilypond", "m4a", "midi", "mp3", "musicxml", "pdf", "wav"]
)


def build_app(css: str | None = None) -> Any:
    gr = _gradio()

    blocks_kwargs: dict[str, Any] = {"title": "Rhythm Vibe Studio"}

    with gr.Blocks(**blocks_kwargs) as app:
        # ── Header ─────────────────────────────────────────────────────────
        gr.HTML(
            '<div class="studio-header"><h1>🎵 Rhythm Vibe Studio</h1></div>'
        )
        gr.Markdown(
            "AI-powered music intelligence — compose, convert, analyze, and edit",
            elem_classes=["studio-sub"],
        )

        # ══════════════════════════════════════════════════════════════════
        # 1. AI Music Assistant
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("🤖 AI Music Assistant", open=True):
            gr.Markdown(
                "Chat with the AI to explore theory, compose music, or run tools. "
                "Type **help** for commands.",
            )
            chatbot = gr.Chatbot(
                value=[],
                height=280,
                show_label=False,
            )
            with gr.Row(elem_classes=["chat-row"]):
                chat_input = gr.Textbox(
                    placeholder="Try: 'C major scale', 'compose cello sunset', 'euclidean 5 8'…",
                    show_label=False,
                    scale=6,
                    container=False,
                )
                chat_send = gr.Button("Send", variant="primary", scale=1)

        # ══════════════════════════════════════════════════════════════════
        # 2. Workspace — shared output viewer
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("🎧 Workspace — Output & Preview", open=True):
            ws_status = gr.Markdown(
                "*Run any tool or chat command to see results here.*"
            )
            ws_audio = gr.Audio(
                label="Audio Playback", visible=False, interactive=False
            )
            ws_midi = gr.HTML("")
            with gr.Row():
                ws_dl_1 = gr.DownloadButton(
                    label="⬇ Download", value=None, visible=False, variant="secondary"
                )
                ws_dl_2 = gr.DownloadButton(
                    label="⬇ Download", value=None, visible=False, variant="secondary"
                )
            with gr.Accordion("Raw JSON", open=False):
                ws_json = gr.Code("", language="json")

        _ws_outputs = [ws_status, ws_audio, ws_midi, ws_dl_1, ws_dl_2, ws_json]

        # ══════════════════════════════════════════════════════════════════
        # 3. Score Editor (LilyPond Studio)
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("🎼 Score Editor — LilyPond Studio", open=True):
            gr.Markdown(
                "Real-time LilyPond editor. Type code, hit **▶ Compile** or enable "
                "**⚡ Auto-render** for live preview."
            )
            with gr.Row(elem_classes=["studio-toolbar"]):
                template_dd = gr.Dropdown(
                    label="Template",
                    choices=list(LILY_TEMPLATES.keys()),
                    value=None,
                    interactive=True,
                    scale=2,
                )
                snippet_dd = gr.Dropdown(
                    label="Snippet",
                    choices=[k for k in _LILY_SNIPPETS],
                    value=None,
                    interactive=True,
                    scale=2,
                )
                auto_chk = gr.Checkbox(label="⚡ Auto-render", value=True, scale=1)
                compile_btn = gr.Button(
                    "▶ Compile", variant="primary", scale=1
                )

            with gr.Row(equal_height=False, elem_classes=["studio-row"]):
                with gr.Column(scale=1, min_width=380):
                    gr.HTML(value=_MONACO_EDITOR_HTML, elem_id="lily-monaco-wrapper")
                    lily_backing = gr.Textbox(
                        value=_LILY_DEFAULT_CODE,
                        label="LilyPond source (synced with Monaco)",
                        elem_id="lily-code-backing",
                        lines=4,
                        max_lines=10,
                        interactive=True,
                    )

                with gr.Column(scale=1, min_width=380):
                    lily_preview = gr.HTML(
                        value='<div class="lily-placeholder">🎼 Edit code then compile</div>',
                        elem_id="lily-preview-html",
                    )
                    with gr.Row(elem_classes=["lily-dl-row"]):
                        lily_pdf_dl = gr.DownloadButton(
                            label="⬇ PDF",
                            value=None,
                            visible=False,
                            variant="secondary",
                        )
                        lily_midi_dl = gr.DownloadButton(
                            label="⬇ MIDI",
                            value=None,
                            visible=False,
                            variant="secondary",
                        )
                    lily_midi_player = gr.HTML("")
                    with gr.Accordion("Compiler logs", open=False):
                        lily_logs = gr.Textbox(
                            label="Output", lines=6, interactive=False
                        )

            last_compiled = gr.State("")
            studio_timer = gr.Timer(value=1.5, active=True)

        # ══════════════════════════════════════════════════════════════════
        # 4. Theory Lab
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("🔬 Theory Lab", open=False):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🎵 Scale Explorer")
                    with gr.Row():
                        scale_root = gr.Dropdown(
                            choices=list(PITCH_NAMES),
                            value="C",
                            label="Root",
                            scale=1,
                        )
                        scale_type = gr.Dropdown(
                            choices=_SCALE_NAMES,
                            value="MAJOR",
                            label="Scale",
                            scale=2,
                        )
                    scale_btn = gr.Button("Explore", variant="primary", size="sm")
                    scale_out = gr.HTML("")

                with gr.Column():
                    gr.Markdown("### 🎹 Chord Builder")
                    with gr.Row():
                        chord_root = gr.Dropdown(
                            choices=list(PITCH_NAMES),
                            value="C",
                            label="Root",
                            scale=1,
                        )
                        chord_type_dd = gr.Dropdown(
                            choices=[ct.name for ct in ChordType],
                            value="MAJOR",
                            label="Type",
                            scale=2,
                        )
                    chord_btn = gr.Button("Build", variant="primary", size="sm")
                    chord_out = gr.HTML("")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🥁 Euclidean Rhythm")
                    with gr.Row():
                        pulses_s = gr.Slider(
                            1, 16, 3, step=1, label="Pulses (hits)"
                        )
                        steps_s = gr.Slider(2, 32, 8, step=1, label="Steps (total)")
                    rhythm_btn = gr.Button(
                        "Generate", variant="primary", size="sm"
                    )
                    rhythm_out = gr.HTML("")

                with gr.Column():
                    gr.Markdown("### 🔗 Progression & Form")
                    with gr.Row():
                        prog_form = gr.Dropdown(
                            choices=[
                                "pop_modern",
                                "aaba",
                                "sonata",
                                "rondo",
                                "blues_12_bar",
                                "strophic",
                            ],
                            value="pop_modern",
                            label="Form",
                            scale=2,
                        )
                        prog_start = gr.Dropdown(
                            choices=["I", "ii", "iii", "IV", "V", "vi", "vii°"],
                            value="I",
                            label="Start",
                            scale=1,
                        )
                    prog_depth = gr.Slider(
                        4, 16, 8, step=1, label="Markov depth"
                    )
                    prog_btn = gr.Button(
                        "Generate", variant="primary", size="sm"
                    )
                    prog_out = gr.HTML("")

        # ══════════════════════════════════════════════════════════════════
        # 5. Convert & Transform
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("🔄 Convert & Transform", open=False):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Convert")
                    conv_input = gr.Textbox(
                        label="File path or URL",
                        placeholder="artifacts/sample.musicxml or https://…",
                    )
                    conv_file = gr.File(label="Upload", type="filepath")
                    conv_format = gr.Dropdown(
                        label="Output format",
                        choices=_FORMAT_CHOICES,
                        value="midi",
                    )
                    conv_btn = gr.Button("Convert", variant="primary")

                with gr.Column(scale=1):
                    gr.Markdown("### Transpose")
                    trans_input = gr.Textbox(
                        label="File path or URL",
                        placeholder="artifacts/sample.musicxml",
                    )
                    trans_file = gr.File(label="Upload", type="filepath")
                    trans_semi = gr.Slider(
                        -24, 24, 2, step=1, label="Semitones"
                    )
                    trans_format = gr.Dropdown(
                        label="Output format",
                        choices=["musicxml", "midi", "lilypond", "json_fallback"],
                        value="musicxml",
                    )
                    trans_btn = gr.Button("Transpose", variant="primary")

            with gr.Accordion("Text Notation → Convert", open=False):
                notation_text = gr.Textbox(
                    label="Paste ABC / ChordPro / freeform notation",
                    lines=8,
                    placeholder="X:1\nT:Simple Tune\nM:4/4\nL:1/4\nK:C\nC D E F | G A B c |",
                )
                with gr.Row():
                    notation_title = gr.Textbox(
                        label="Title", value="text_notation_piece"
                    )
                    notation_format = gr.Dropdown(
                        label="Target format",
                        choices=["lilypond", "musicxml", "midi", "json_fallback", "pdf"],
                        value="lilypond",
                    )
                notation_btn = gr.Button(
                    "Convert text notation", variant="primary"
                )

        # ══════════════════════════════════════════════════════════════════
        # 6. Compose
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("🎭 Compose from Prompt", open=False):
            compose_prompt = gr.Textbox(
                label="Describe the music",
                lines=5,
                placeholder="Warm cello melody that feels like sunrise over a quiet ocean.",
            )
            with gr.Row():
                compose_title = gr.Textbox(label="Title", value="Theme", scale=2)
                compose_instrument = gr.Dropdown(
                    label="Instrument",
                    choices=["Solo", "Cello", "Violin", "Viola", "Flute", "Piano"],
                    value="Solo",
                    scale=2,
                )
            with gr.Row():
                compose_tempo = gr.Slider(
                    30, 180, 56, step=1, label="Tempo BPM"
                )
                compose_format = gr.Dropdown(
                    label="Output format",
                    choices=["lilypond", "musicxml", "midi", "pdf"],
                    value="lilypond",
                )
            compose_btn = gr.Button(
                "Generate Composition", variant="primary"
            )

        # ══════════════════════════════════════════════════════════════════
        # 7. Resources
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("📂 Resources", open=False):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Sample MP3 Finder")
                    gr.Markdown("Scrape known sources for working MP3 URLs.")
                    find_btn = gr.Button(
                        "Find sample MP3 URLs", variant="secondary"
                    )
                    sample_status = gr.Markdown("")
                    sample_urls = gr.Textbox(
                        label="Sample MP3 URLs", lines=6, interactive=False
                    )

                with gr.Column():
                    gr.Markdown("### Fetch from URL")
                    fetch_url = gr.Textbox(
                        label="Asset URL",
                        placeholder="https://example.com/song.mp3",
                    )
                    fetch_btn = gr.Button("Fetch", variant="primary")

            with gr.Accordion("Route Planner", open=False):
                with gr.Row():
                    route_in = gr.Dropdown(
                        label="From", choices=_FORMAT_CHOICES, value="musicxml"
                    )
                    route_out = gr.Dropdown(
                        label="To", choices=_FORMAT_CHOICES, value="midi"
                    )
                route_btn = gr.Button("Plan route", variant="secondary")

        # ══════════════════════════════════════════════════════════════════
        # 8. System
        # ══════════════════════════════════════════════════════════════════
        with gr.Accordion("⚙ System", open=False):
            health_btn = gr.Button("Run Healthcheck", variant="secondary")

        # ══════════════════════════════════════════════════════════════════
        # Event Wiring
        # ══════════════════════════════════════════════════════════════════

        # ── AI Chat ──────────────────────────────────────────────────────
        chat_send.click(
            fn=_ai_respond,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot],
        )
        chat_input.submit(
            fn=_ai_respond,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot],
        )

        # ── LilyPond Studio ─────────────────────────────────────────────
        def _on_compile(code: str) -> tuple[str, str, Any, Any, str, str]:
            svg, logs, pdf, midi = _compile_lily_preview(code)
            gr_ = _gradio()
            pdf_u = gr_.update(visible=bool(pdf), value=pdf) if pdf else gr_.update(visible=False)
            midi_u = (
                gr_.update(visible=bool(midi), value=midi)
                if midi
                else gr_.update(visible=False)
            )
            midi_html = _midi_player_html(midi) if midi else ""
            return svg, logs, pdf_u, midi_u, midi_html, code

        def _on_timer_tick(
            code: str, last: str, auto: bool
        ) -> tuple[Any, Any, Any, Any, Any, str]:
            gr_ = _gradio()
            if not auto or not code or code.strip() == last.strip():
                skip = gr_.update()
                return skip, skip, skip, skip, skip, last
            svg, logs, pdf, midi = _compile_lily_preview(code)
            pdf_u = gr_.update(visible=bool(pdf), value=pdf) if pdf else gr_.update(visible=False)
            midi_u = (
                gr_.update(visible=bool(midi), value=midi)
                if midi
                else gr_.update(visible=False)
            )
            midi_html = _midi_player_html(midi) if midi else gr_.update()
            return svg, logs, pdf_u, midi_u, midi_html, code

        _studio_outputs = [
            lily_preview,
            lily_logs,
            lily_pdf_dl,
            lily_midi_dl,
            lily_midi_player,
            last_compiled,
        ]

        compile_btn.click(
            fn=_on_compile, inputs=[lily_backing], outputs=_studio_outputs
        )
        studio_timer.tick(
            fn=_on_timer_tick,
            inputs=[lily_backing, last_compiled, auto_chk],
            outputs=_studio_outputs,
        )

        def _on_template(name: str) -> tuple[str, Any]:
            code = LILY_TEMPLATES.get(name, "")
            return code, _gradio().update(value=None)

        def _on_snippet(code: str, name: str) -> tuple[str, Any]:
            text = _LILY_SNIPPETS.get(name, "")
            if not text or text.startswith("—"):
                return code, _gradio().update(value=None)
            return (code.rstrip() + "\n" + text), _gradio().update(value=None)

        template_dd.change(
            fn=_on_template, inputs=[template_dd], outputs=[lily_backing, template_dd]
        )
        snippet_dd.change(
            fn=_on_snippet,
            inputs=[lily_backing, snippet_dd],
            outputs=[lily_backing, snippet_dd],
        )

        # ── Theory Lab ───────────────────────────────────────────────────
        scale_btn.click(
            fn=_theory_explore_scale,
            inputs=[scale_root, scale_type],
            outputs=[scale_out],
        )
        chord_btn.click(
            fn=_theory_build_chord,
            inputs=[chord_root, chord_type_dd],
            outputs=[chord_out],
        )
        rhythm_btn.click(
            fn=_theory_euclidean,
            inputs=[pulses_s, steps_s],
            outputs=[rhythm_out],
        )
        prog_btn.click(
            fn=_theory_progression,
            inputs=[prog_form, prog_start, prog_depth],
            outputs=[prog_out],
        )

        # ── Convert & Transform → Workspace ──────────────────────────────
        def _on_convert(ref: str, file: str | None, fmt: str) -> tuple:
            chosen = _choose_input(ref, file)
            raw = _convert_music_json(chosen, fmt)
            return _update_workspace(raw)

        def _on_transpose(
            ref: str, file: str | None, semi: int, fmt: str
        ) -> tuple:
            chosen = _choose_input(ref, file)
            raw = _transpose_song_json(chosen, int(semi), fmt)
            return _update_workspace(raw)

        def _on_notation(text: str, fmt: str, title: str) -> tuple:
            raw = _convert_text_notation_json(text, fmt, title.strip() or "text_notation_piece")
            return _update_workspace(raw)

        conv_btn.click(
            fn=_on_convert,
            inputs=[conv_input, conv_file, conv_format],
            outputs=_ws_outputs,
        )
        trans_btn.click(
            fn=_on_transpose,
            inputs=[trans_input, trans_file, trans_semi, trans_format],
            outputs=_ws_outputs,
        )
        notation_btn.click(
            fn=_on_notation,
            inputs=[notation_text, notation_format, notation_title],
            outputs=_ws_outputs,
        )

        # ── Compose → Workspace ──────────────────────────────────────────
        def _on_compose(
            prompt: str,
            title: str,
            tempo: int,
            instrument: str,
            fmt: str,
        ) -> tuple:
            raw = _compose_story_json(
                prompt=prompt,
                title=title.strip() or "Theme",
                tempo_bpm=int(tempo),
                instrument=instrument,
                output_format=fmt,
            )
            return _update_workspace(raw)

        compose_btn.click(
            fn=_on_compose,
            inputs=[
                compose_prompt,
                compose_title,
                compose_tempo,
                compose_instrument,
                compose_format,
            ],
            outputs=_ws_outputs,
        )

        # ── Resources ────────────────────────────────────────────────────
        def _on_find_samples() -> tuple[str, str, str]:
            urls = _discover_sample_mp3_urls(max_results=12)
            if not urls:
                return "⚠️ No samples found.", "", ""
            lines = [f"{i + 1}. {u}" for i, u in enumerate(urls)]
            return (
                f"✅ Found {len(urls)} sample MP3 URL(s).",
                "\n".join(lines),
                urls[0],
            )

        find_btn.click(
            fn=_on_find_samples,
            outputs=[sample_status, sample_urls, fetch_url],
        )

        def _on_fetch(url: str) -> tuple:
            raw = _fetch_music_from_web_json(url=(url or "").strip())
            return _update_workspace(raw)

        fetch_btn.click(fn=_on_fetch, inputs=[fetch_url], outputs=_ws_outputs)

        def _on_route(inf: str, outf: str) -> tuple:
            raw = _plan_music_conversion_json(inf, outf)
            return _update_workspace(raw)

        route_btn.click(
            fn=_on_route, inputs=[route_in, route_out], outputs=_ws_outputs
        )

        # ── System ───────────────────────────────────────────────────────
        def _on_health() -> tuple:
            raw = _healthcheck_json()
            return _update_workspace(raw)

        health_btn.click(fn=_on_health, outputs=_ws_outputs)

        # ── Load JS ──────────────────────────────────────────────────────
        app.load(fn=lambda: None, js=_UI_JS)

    return app


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="rhythm-vibe-mcp-webui")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args(argv)

    # Try to use a nice theme; fall back to default
    try:
        import gradio as _gr
        theme = _gr.themes.Soft(primary_hue="orange", secondary_hue="amber")
    except Exception:
        theme = None

    app = build_app()
    launch_kwargs: dict[str, Any] = {
        "server_name": args.host,
        "server_port": args.port,
        "share": args.share,
        "css": _UI_CSS,
    }
    if theme:
        launch_kwargs["theme"] = theme
    try:
        app.launch(**launch_kwargs)
    except TypeError:
        # Fallback: strip unknown kwargs
        for k in ("theme", "css"):
            launch_kwargs.pop(k, None)
        legacy_app = build_app(css=_UI_CSS)
        legacy_app.launch(**launch_kwargs)


if __name__ == "__main__":
    main()
