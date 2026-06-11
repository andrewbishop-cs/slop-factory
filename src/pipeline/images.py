"""Stage 2 — keyframe image generation (M2).

One 1080×1920 PNG per scene via mflux / FLUX-schnell, with character
appearance tokens + style anchor prepended for consistency. Also provides
the ffmpeg `zoompan` Ken Burns helper used by assemble.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode, SeriesBible


def generate_images(
    settings: Settings,
    episode: Episode,
    bible: SeriesBible,
    episode_dir: Path,
) -> list[Path]:
    """Render `images/scene_NN.png` for every scene; returns the paths."""
    raise NotImplementedError("M2")


def ken_burns(image: Path, move: str, duration_sec: float, out_path: Path, settings: Settings) -> Path:
    """Turn a still into a moving clip via ffmpeg `zoompan`; returns `out_path`."""
    raise NotImplementedError("M2")
