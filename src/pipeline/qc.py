"""Stage 8 — QC gate (M8).

Pass/fail checks on the rendered episode: duration ≥ min, all scene images
present, captions non-empty, loudness ≈ −14 LUFS, resolution/fps/codec,
optional character-consistency score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import Settings
from src.schemas import Episode


def run_qc(settings: Settings, episode: Episode, episode_dir: Path) -> dict[str, Any]:
    """Return an itemized qc_report dict with an overall `passed` bool."""
    raise NotImplementedError("M8")
