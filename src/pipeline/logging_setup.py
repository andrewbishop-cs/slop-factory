"""Per-episode logging.

Mirrors pipeline output to both the console and `episodes/<id>/pipeline.log` so that
missing inputs (scripts, images, narration, captions), soft warnings, and full failure
tracebacks are captured for later review rather than scrolling past in a terminal.
The orchestrator calls `setup_episode_logging` once per run; stages use `get_logger`.
"""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER_NAME = "slopfactory"


def setup_episode_logging(episode_dir: Path) -> logging.Logger:
    """Point the shared logger at `<episode_dir>/pipeline.log` (+ console). Idempotent:
    re-running resets handlers so a new episode logs to its own file without duplication."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    episode_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(episode_dir / "pipeline.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def get_logger() -> logging.Logger:
    """The shared pipeline logger. If the orchestrator hasn't configured handlers (e.g. a
    stage is run standalone), Python's last-resort handler still surfaces WARNING+ to stderr."""
    return logging.getLogger(LOGGER_NAME)
