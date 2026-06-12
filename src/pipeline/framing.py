"""Vision-guided Ken Burns framing (M5).

A local moondream2 (Apache-2.0) pass over each rendered scene PNG locates the focal
character so the shot can push *toward* them instead of a blind center zoom. The target is
chosen from the script: a scene whose narration is quoted dialogue focuses the single
speaking character; otherwise it focuses the most prominent present character (largest
detected box). Result is cached to `framing.json` so the vision model only runs once per
episode. When nothing is detected (or framing is disabled) the caller falls back to the
scripted `motion.move`.

Each scene's framing is a push-in: start on the full frame, end zoomed on the focal box,
expressed as `(center_x, center_y, zoom)` normalized pairs consumed by `images.ken_burns`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForCausalLM

from src.config import PROJECT_ROOT, Settings, load_series_bible
from src.pipeline import logging_setup
from src.schemas import Character, Episode, Scene, SeriesBible

MODEL_ID = "vikhyatk/moondream2"
MODEL_REVISION = "2025-06-21"  # pinned: moondream updates frequently
CACHE_FILE = "framing.json"

# Fallback detect phrases when a character has no explicit `detect_phrase` in the bible.
_ANIMAL_WORDS = ("monkey", "cat", "dog", "fox", "frog", "lizard", "rat", "shark", "bird", "bear", "rabbit", "otter")

_OPEN_QUOTE = "\"“'‘"
_CLOSE_QUOTE = "\"”'’"


def _device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def _is_dialogue(text: str) -> bool:
    t = text.strip()
    return len(t) >= 2 and t[0] in _OPEN_QUOTE and t[-1] in _CLOSE_QUOTE


def _present_characters(scene: Scene, bible: SeriesBible) -> list[Character]:
    return [c for c in bible.characters if re.search(rf"\b{re.escape(c.name)}\b", scene.image_prompt, re.IGNORECASE)]


def _detect_phrase(char: Character) -> str:
    if char.detect_phrase:
        return char.detect_phrase
    tokens = char.appearance_tokens.lower()
    for word in _ANIMAL_WORDS:
        if word in tokens:
            return word
    return "character"


def _largest_box(objects: list[dict]) -> tuple[float, float, float, float] | None:
    if not objects:
        return None
    o = max(objects, key=lambda b: (b["x_max"] - b["x_min"]) * (b["y_max"] - b["y_min"]))
    return o["x_min"], o["y_min"], o["x_max"], o["y_max"]


def _push_in(box: tuple[float, float, float, float], settings: Settings) -> dict:
    """Turn a normalized focal box into a start→end push-in (full frame → zoomed on the box)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    span = max(x1 - x0, y1 - y0, 1e-3)
    f = settings.framing
    z_end = max(f.min_zoom, min(f.max_zoom, f.target_fill / span))
    # End center must keep the crop inside the frame at z_end; start is the full frame (center fixed).
    margin = 1.0 / (2.0 * z_end)
    cx = min(max(cx, margin), 1.0 - margin)
    cy = min(max(cy, margin), 1.0 - margin)
    return {"start": [0.5, 0.5, 1.0], "end": [round(cx, 4), round(cy, 4), round(z_end, 4)]}


def _target_box(model, image: Image.Image, scene: Scene, present: list[Character]):
    """Detect the focal character's box: the lone speaker for a quoted line, else the largest
    among the present characters."""
    speaker = present[0] if (_is_dialogue(scene.narration_text) and len(present) == 1) else None
    candidates = [speaker] if speaker else present
    best = None
    best_area = 0.0
    chosen = None
    for char in candidates:
        box = _largest_box(model.detect(image, _detect_phrase(char))["objects"])
        if box is None:
            continue
        area = (box[2] - box[0]) * (box[3] - box[1])
        if area > best_area:
            best, best_area, chosen = box, area, char
    return best, chosen


def compute_framing(settings: Settings, episode: Episode, episode_dir: Path) -> dict[int, dict]:
    """Return `{scene_id: {"start": [...], "end": [...]}}` for scenes with a detected focal
    character. Cached to `framing.json`; scenes absent from the result fall back to scripted moves."""
    log = logging_setup.get_logger()
    if not settings.framing.enabled:
        return {}

    cache = episode_dir / CACHE_FILE
    if cache.exists():
        raw = json.loads(cache.read_text())
        return {int(k): v for k, v in raw.items()}

    images_dir = episode_dir / "images"
    bible = load_series_bible(episode.series_id)
    log.info("framing: loading %s (%s) on %s", MODEL_ID, MODEL_REVISION, _device())
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=True).to(_device())

    framings: dict[int, dict] = {}
    for scene in episode.scenes:
        img_path = images_dir / f"scene_{scene.id:02d}.png"
        if not img_path.exists():
            continue
        present = _present_characters(scene, bible)
        if not present:
            log.info("framing: scene %02d has no named character — scripted move", scene.id)
            continue
        image = Image.open(img_path).convert("RGB")
        box, chosen = _target_box(model, image, scene, present)
        if box is None:
            log.info("framing: scene %02d — no focal box detected, scripted move", scene.id)
            continue
        framings[scene.id] = _push_in(box, settings)
        log.info("framing: scene %02d → focus %s end=%s", scene.id, chosen.name if chosen else "?", framings[scene.id]["end"])

    cache.write_text(json.dumps({str(k): v for k, v in framings.items()}, indent=2) + "\n")
    log.info("framing: wrote %s (%d/%d scenes targeted)", CACHE_FILE, len(framings), len(episode.scenes))
    return framings
