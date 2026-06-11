"""Stage 4 — narration TTS (M3).

Kokoro, one locked voice per character, one wav per narrated scene.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode, SeriesBible


def generate_narration(
    settings: Settings,
    episode: Episode,
    bible: SeriesBible,
    episode_dir: Path,
) -> list[Path]:
    """Render `audio/scene_NN.wav` for every narrated scene; returns the paths."""
    raise NotImplementedError("M3")
