"""Stage 1 — script generation (M1).

One-line prompt (or "continue") + series bible → validated `episode.json`
via Claude Opus 4.8 structured output. Updates the bible's `plot_state`.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode, SeriesBible


def generate_script(
    settings: Settings,
    bible: SeriesBible,
    episode_dir: Path,
    prompt: str | None = None,
) -> Episode:
    """Generate `episode.json` in `episode_dir`. `prompt=None` means continue the plot."""
    raise NotImplementedError("M1")
