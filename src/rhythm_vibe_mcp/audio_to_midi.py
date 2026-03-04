"""Pure-Python/ffmpeg audio-to-MIDI transcription fallback.

Works on Python 3.13+ without basic_pitch/TensorFlow.
Uses ffmpeg to decode audio to raw PCM, then performs simple pitch detection
via zero-crossing-rate estimation combined with energy gating, and finally
writes a MIDI file via music21.

This is intentionally *best-effort* — it won't match ML-based accuracy, but
it provides a working audio→MIDI→sheet pipeline on every supported Python.
"""

from __future__ import annotations

import math
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from rhythm_vibe_mcp.constants.binaries import FFMPEG_BINARY
from rhythm_vibe_mcp.utils import binary_available

# -------------------------------------------------------------------
# Audio decode
# -------------------------------------------------------------------
_SAMPLE_RATE = 22050
_CHANNELS = 1
_SAMPLE_FMT = "s16le"  # signed 16-bit little-endian
_BYTES_PER_SAMPLE = 2


def _decode_to_pcm(audio_path: Path) -> bytes:
    """Decode any audio file to mono 16-bit PCM at 22050 Hz using ffmpeg."""
    cmd = [
        FFMPEG_BINARY,
        "-hide_banner",
        "-y",
        "-i",
        str(audio_path),
        "-ac",
        str(_CHANNELS),
        "-ar",
        str(_SAMPLE_RATE),
        "-f",
        _SAMPLE_FMT,
        "-acodec",
        f"pcm_{_SAMPLE_FMT}",
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=300,
        check=True,
    )
    return proc.stdout


def _pcm_to_samples(pcm: bytes) -> list[float]:
    """Convert raw PCM bytes to normalized float samples in [-1, 1]."""
    n = len(pcm) // _BYTES_PER_SAMPLE
    samples = struct.unpack(f"<{n}h", pcm[: n * _BYTES_PER_SAMPLE])
    return [s / 32768.0 for s in samples]


# -------------------------------------------------------------------
# Pitch detection  (autocorrelation-based, per-frame)
# -------------------------------------------------------------------
_FRAME_SIZE = 2048  # ~93 ms at 22050 Hz
_HOP_SIZE = 1024  # ~46 ms
_MIN_FREQ = 55.0  # A1 — low cello range
_MAX_FREQ = 1400.0  # well above cello; generous
_ENERGY_THRESHOLD = 0.005  # RMS gate


def _rms(frame: list[float]) -> float:
    return math.sqrt(sum(x * x for x in frame) / max(len(frame), 1))


def _autocorrelation_pitch(frame: list[float], sr: int) -> float | None:
    """Estimate fundamental frequency of a frame via autocorrelation."""
    n = len(frame)
    if n < 2:
        return None

    min_lag = max(1, int(sr / _MAX_FREQ))
    max_lag = min(n - 1, int(sr / _MIN_FREQ))
    if min_lag >= max_lag:
        return None

    best_lag = min_lag
    best_val = -1.0
    for lag in range(min_lag, max_lag + 1):
        corr = 0.0
        for i in range(n - lag):
            corr += frame[i] * frame[i + lag]
        if corr > best_val:
            best_val = corr
            best_lag = lag

    if best_val <= 0:
        return None

    freq = sr / best_lag
    if freq < _MIN_FREQ or freq > _MAX_FREQ:
        return None
    return freq


def _freq_to_midi(freq: float) -> int:
    """Convert frequency (Hz) to nearest MIDI note number."""
    return max(0, min(127, round(69 + 12 * math.log2(freq / 440.0))))


# -------------------------------------------------------------------
# Note event assembly
# -------------------------------------------------------------------

def _detect_notes(
    samples: list[float],
    sr: int = _SAMPLE_RATE,
) -> list[dict[str, Any]]:
    """Run frame-wise pitch detection and group into note events."""
    notes: list[dict[str, Any]] = []
    current_midi: int | None = None
    note_start: float = 0.0

    total_frames = (len(samples) - _FRAME_SIZE) // _HOP_SIZE + 1

    for i in range(total_frames):
        start = i * _HOP_SIZE
        frame = samples[start : start + _FRAME_SIZE]
        t = start / sr

        energy = _rms(frame)
        if energy < _ENERGY_THRESHOLD:
            # Silence — end current note
            if current_midi is not None:
                notes.append({
                    "midi": current_midi,
                    "start": note_start,
                    "end": t,
                })
                current_midi = None
            continue

        freq = _autocorrelation_pitch(frame, sr)
        if freq is None:
            if current_midi is not None:
                notes.append({
                    "midi": current_midi,
                    "start": note_start,
                    "end": t,
                })
                current_midi = None
            continue

        midi_num = _freq_to_midi(freq)

        if current_midi is None:
            current_midi = midi_num
            note_start = t
        elif midi_num != current_midi:
            notes.append({
                "midi": current_midi,
                "start": note_start,
                "end": t,
            })
            current_midi = midi_num
            note_start = t

    # Close trailing note
    if current_midi is not None:
        notes.append({
            "midi": current_midi,
            "start": note_start,
            "end": len(samples) / sr,
        })

    # Filter very short notes (< 50 ms) — likely detection artefacts
    return [n for n in notes if (n["end"] - n["start"]) >= 0.05]


# -------------------------------------------------------------------
# MIDI writing via music21
# -------------------------------------------------------------------

def _notes_to_midi(
    notes: list[dict[str, Any]],
    output_path: Path,
    tempo_bpm: float = 72.0,
) -> Path:
    """Write detected note events to a MIDI file using music21."""
    from music21 import duration, midi, note, stream, tempo

    s = stream.Stream()
    s.append(tempo.MetronomeMark(number=tempo_bpm))

    prev_end = 0.0
    for n in notes:
        gap = n["start"] - prev_end
        if gap > 0.05:
            rest_ql = gap * (tempo_bpm / 60.0)
            r = note.Rest(quarterLength=rest_ql)
            s.append(r)

        dur_sec = n["end"] - n["start"]
        dur_ql = dur_sec * (tempo_bpm / 60.0)
        if dur_ql < 0.0625:
            dur_ql = 0.0625  # minimum 64th note

        m21_note = note.Note(n["midi"])
        m21_note.duration = duration.Duration(quarterLength=dur_ql)
        m21_note.volume.velocity = 80
        s.append(m21_note)
        prev_end = n["end"]

    mf = midi.translate.music21ObjectToMidiFile(s)
    mf.open(str(output_path), "wb")
    mf.write()
    mf.close()
    return output_path


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def audio_to_midi_ffmpeg(
    input_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Transcribe audio to MIDI using ffmpeg + autocorrelation.

    Parameters
    ----------
    input_path:
        Path to any audio file ffmpeg can decode.
    output_path:
        Where to write the .mid file.  If ``None`` a path is generated next
        to the input.

    Returns
    -------
    Path to the written MIDI file.

    Raises
    ------
    RuntimeError
        If ffmpeg is not available or decoding fails.
    """
    if not binary_available(FFMPEG_BINARY):
        raise RuntimeError("ffmpeg is required for audio-to-MIDI transcription")

    pcm = _decode_to_pcm(input_path)
    samples = _pcm_to_samples(pcm)
    notes = _detect_notes(samples)

    if output_path is None:
        output_path = input_path.with_suffix(".mid")

    return _notes_to_midi(notes, output_path)
