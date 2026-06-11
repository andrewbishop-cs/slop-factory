"""Stage 6 — karaoke captions (M4).

WhisperX forced alignment (narration text is known) → word timestamps →
ASS file with `\\kf` karaoke tags, styled from config.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode


def generate_captions(settings: Settings, episode: Episode, episode_dir: Path) -> Path:
    """Align narration wavs against their text and write `captions.ass`; returns its path."""
    raise NotImplementedError("M4")
