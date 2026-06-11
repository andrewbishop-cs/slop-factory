"""Stage 7 — final render (M5, music in M6, hook prepended in M7).

ffmpeg: Ken Burns scene clips (+hook when available) concatenated with
xfade, ASS captions burned in, narration + music mixed and normalized to
−14 LUFS, encoded h264_videotoolbox 1080×1920@30 + AAC. Also writes
`caption.txt` (description + hashtags + AI-label note).
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.schemas import Episode


def assemble(settings: Settings, episode: Episode, episode_dir: Path) -> Path:
    """Render `final.mp4` + `caption.txt` in `episode_dir`; returns the mp4 path."""
    raise NotImplementedError("M5")
