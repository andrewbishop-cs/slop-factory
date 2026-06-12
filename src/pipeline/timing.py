"""Shared body-timeline math for captions (M4) and assemble (M5).

Both stages must agree on exactly when each scene starts, or burned captions drift
against the narration. The single rule lives here: a scene's on-screen shot lasts at
least its scripted `duration_sec`, but is never shorter than its narration wav — so the
voiceover is never cut off — and each scene starts at the cumulative sum of the previous
shots' effective durations (the hook, prepended in M7, is a later additive offset).
"""

from __future__ import annotations

from pathlib import Path

import soundfile as sf

from src.schemas import Episode


def narration_wav(audio_dir: Path, scene_id: int) -> Path:
    return audio_dir / f"scene_{scene_id:02d}.wav"


def wav_duration(path: Path) -> float:
    """Seconds of audio at `path`, or 0.0 if it's missing/unreadable."""
    if not path.exists():
        return 0.0
    try:
        return float(sf.info(str(path)).duration)
    except Exception:
        return 0.0


def shot_durations(episode: Episode, audio_dir: Path) -> list[float]:
    """Effective on-screen duration per scene: max(scripted duration, narration length)."""
    return [
        max(scene.duration_sec, wav_duration(narration_wav(audio_dir, scene.id)))
        for scene in episode.scenes
    ]


def scene_offsets(durations: list[float]) -> list[float]:
    """Body-timeline start time of each scene from its effective durations."""
    offsets, t = [], 0.0
    for d in durations:
        offsets.append(t)
        t += d
    return offsets
