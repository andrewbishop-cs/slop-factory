"""Stage 10 STUB — output to ready_to_post/ (M9). Real TikTok upload is deferred.

Copies `final.mp4` + `caption.txt` into `ready_to_post/` and prints
manual-upload instructions for TikTok Studio.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings


def publish(settings: Settings, episode_dir: Path) -> Path:
    """Copy the approved final.mp4 + caption.txt to ready_to_post/; returns the mp4 path."""
    raise NotImplementedError("M9")
