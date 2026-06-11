"""Stage 5 — music bed (M6).

ACE-Step (or Stable Audio Open) score keyed to the scene mood/intensity arc,
spanning at least the full video duration.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode


def generate_music(settings: Settings, episode: Episode, episode_dir: Path) -> Path:
    """Render `audio/music.wav` (≥ total episode duration); returns its path."""
    raise NotImplementedError("M6")
