from __future__ import annotations

from pathlib import Path
from typing import Any

from rhythm_vibe_mcp.audio_to_midi import audio_to_midi_ffmpeg
from rhythm_vibe_mcp.constants.limits import truncate_error
from rhythm_vibe_mcp.converters import convert_any


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def analyze_audio_to_lily(input_path: Path) -> dict[str, Any]:
    """Best-effort performance analysis + transcription artifacts from an audio file."""
    from music21 import converter

    midi_result = convert_any(input_path, "midi")
    if not midi_result.ok or not midi_result.artifacts:
        midi_path = audio_to_midi_ffmpeg(input_path)
        midi_artifact = {
            "path": str(midi_path),
            "format": "midi",
            "notes": ["audio-to-midi fallback used"],
        }
    else:
        midi_path = Path(midi_result.artifacts[0].path)
        midi_artifact = midi_result.artifacts[0].model_dump()

    score = converter.parse(str(midi_path))
    flat_notes = list(score.flat.notes)
    midi_numbers = [int(n.pitch.midi) for n in flat_notes if hasattr(n, "pitch")]
    durations_q = [
        float(getattr(n.duration, "quarterLength", 0.0))
        for n in flat_notes
        if getattr(n, "duration", None)
    ]
    offsets = [float(getattr(n, "offset", 0.0)) for n in flat_notes]
    interval_steps = [
        abs(midi_numbers[idx] - midi_numbers[idx - 1])
        for idx in range(1, len(midi_numbers))
    ]

    short_note_ratio = 0.0
    if durations_q:
        short_notes = [d for d in durations_q if d <= 0.25]
        short_note_ratio = len(short_notes) / len(durations_q)

    big_leap_ratio = 0.0
    if interval_steps:
        big_leaps = [d for d in interval_steps if d >= 7]
        big_leap_ratio = len(big_leaps) / len(interval_steps)

    avg_pitch = round(_safe_mean([float(v) for v in midi_numbers]), 2) if midi_numbers else 0.0
    avg_duration_q = round(_safe_mean(durations_q), 3)
    mean_interval = round(_safe_mean([float(v) for v in interval_steps]), 3)

    text_summary = (
        f"Detected {len(midi_numbers)} notes from {input_path.name}. "
        f"Pitch span: {min(midi_numbers) if midi_numbers else 'n/a'}"
        f"-{max(midi_numbers) if midi_numbers else 'n/a'} (avg {avg_pitch}). "
        f"Rhythmic articulation proxy: short-note ratio {short_note_ratio:.2f}, "
        f"average duration {avg_duration_q} quarter notes. "
        f"Intonation proxy (pitch-center stability): mean melodic step {mean_interval} semitones "
        f"with large-leap ratio {big_leap_ratio:.2f}."
    )

    lily_result = convert_any(midi_path, "lilypond")
    artifacts: list[dict[str, Any]] = [midi_artifact]
    if lily_result.ok and lily_result.artifacts:
        artifacts.extend([artifact.model_dump() for artifact in lily_result.artifacts])

    return {
        "ok": True,
        "message": "audio analysis complete",
        "analysis_text": text_summary,
        "metrics": {
            "note_count": len(midi_numbers),
            "pitch_min_midi": min(midi_numbers) if midi_numbers else None,
            "pitch_max_midi": max(midi_numbers) if midi_numbers else None,
            "avg_pitch_midi": avg_pitch,
            "avg_duration_quarter": avg_duration_q,
            "short_note_ratio": round(short_note_ratio, 4),
            "mean_interval_semitones": mean_interval,
            "large_leap_ratio": round(big_leap_ratio, 4),
            "onset_count": len(offsets),
        },
        "artifacts": artifacts,
        "warnings": [
            "Intonation/articulation values are heuristic proxies from audio-to-MIDI, not studio-grade pitch tracking."
        ],
    }


def safe_analyze_audio_to_lily(input_path: Path) -> dict[str, Any]:
    try:
        return analyze_audio_to_lily(input_path)
    except Exception as exc:
        return {
            "ok": False,
            "message": "audio analysis failed",
            "error": truncate_error(str(exc)),
        }
