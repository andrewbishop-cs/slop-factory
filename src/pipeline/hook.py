"""Stage 3 — hook clip (M7, riskiest dep — built late, library first).

Produces the ≤4s portrait `hook.mp4` from LTX-Video, falling back to a clip
from `assets/hook_library/` when configured or when generation fails.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode


def generate_hook(settings: Settings, episode: Episode, episode_dir: Path) -> Path:
    """Produce `hook.mp4` (portrait, ≤ settings.hook.max_seconds); returns its path."""
    raise NotImplementedError("M7")
