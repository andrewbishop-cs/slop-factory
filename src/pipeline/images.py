"""Stage 2 — image generation (M2).

One keyframe per scene via mflux (FLUX-schnell on MLX), rendered portrait and
saved to `images/scene_NN.png`. Also `ken_burns()`: turn a still into a moving
clip (ffmpeg `zoompan`) — defined here, exercised by assemble in M5.

Character identity across shots (BUILD.md §9) is held by three layers, weakest → strongest:
  1. Prompt anchoring (always on): every scene prompt is prefixed with the exact
     `appearance_tokens` of the characters in that shot + the series `style_anchor`,
     so the model re-describes the same character and art style every time.
  2. Stable per-character seed (always on): each character gets a deterministic seed
     so its renders stay in the same visual "family" and re-runs are reproducible.
  3. A trained character LoRA (opt-in via `image.lora_path`): the production-grade lock —
     a small adapter trained on a character's reference images that reproduces that exact
     character. FLUX-Kontext / img2img reference conditioning is the prototype alternative.
Layers 1–2 ship now; layer 3 plugs in via config without changing this stage.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from mflux.models.common.config import ModelConfig
from mflux.models.flux.variants.txt2img.flux import Flux1
from PIL import Image

from src.config import Settings
from src.schemas import Character, Episode, Scene, SeriesBible

_MOVES = ("push_in", "pull_out", "pan_left", "pan_right", "pan_up", "pan_down")


def _round_up_16(n: int) -> int:
    """FLUX needs dimensions that are multiples of 16."""
    return ((n + 15) // 16) * 16


def _gen_dims(width: int, height: int) -> tuple[int, int]:
    return _round_up_16(width), _round_up_16(height)


def _stable_seed(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _characters_in_scene(scene: Scene, bible: SeriesBible) -> list[Character]:
    """Characters whose name is mentioned in the scene's image prompt."""
    present = [c for c in bible.characters if re.search(rf"\b{re.escape(c.name)}\b", scene.image_prompt, re.IGNORECASE)]
    return present


def _build_prompt(scene: Scene, bible: SeriesBible, characters: list[Character]) -> str:
    """Anchor the shot with each character's fixed appearance + the series style."""
    parts: list[str] = []
    for c in characters:
        parts.append(f"{c.name} ({c.appearance_tokens})")
    who = ("Characters — " + "; ".join(parts) + ". ") if parts else ""
    return f"{who}{scene.image_prompt.strip()} Art style: {bible.style_anchor}."


def _load_model(settings: Settings) -> Flux1:
    image = settings.image
    model_name = image.model.removeprefix("flux-")  # "flux-schnell" -> "schnell"
    lora_paths = [image.lora_path] if image.lora_path else None
    lora_scales = [image.lora_scale] if image.lora_path else None
    return Flux1(
        model_config=ModelConfig.from_name(model_name),
        quantize=image.quantize,
        lora_paths=lora_paths,
        lora_scales=lora_scales,
    )


def _center_crop(img: Image.Image, width: int, height: int) -> Image.Image:
    if img.size == (width, height):
        return img
    left = max(0, (img.width - width) // 2)
    top = max(0, (img.height - height) // 2)
    return img.crop((left, top, left + width, top + height))


def generate_images(settings: Settings, episode: Episode, bible: SeriesBible, episode_dir: Path) -> list[Path]:
    """Render one PNG per scene into `<episode_dir>/images/`. Skips scenes already rendered."""
    images_dir = episode_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    target_w, target_h = settings.video.width, settings.video.height
    gen_w, gen_h = _gen_dims(target_w, target_h)

    model: Flux1 | None = None
    outputs: list[Path] = []
    for scene in episode.scenes:
        out = images_dir / f"scene_{scene.id:02d}.png"
        outputs.append(out)
        if out.exists():
            print(f"[{episode.episode_id}] image scene {scene.id:02d}: exists, skipping")
            continue

        characters = _characters_in_scene(scene, bible)
        prompt = _build_prompt(scene, bible, characters)
        # Seed off the characters in the shot so a character stays in one visual family.
        seed_key = characters[0].name if characters else episode.series_id
        seed = _stable_seed(episode.series_id, seed_key, str(scene.id))

        if model is None:
            model = _load_model(settings)

        print(f"[{episode.episode_id}] image scene {scene.id:02d}: rendering (seed {seed})")
        result = model.generate_image(
            seed=seed,
            prompt=prompt,
            num_inference_steps=settings.image.steps,
            width=gen_w,
            height=gen_h,
            guidance=settings.image.guidance,
        )
        _center_crop(result.image, target_w, target_h).save(out)

    return outputs


def _zoompan_filter(move: str, frames: int, width: int, height: int, fps: int) -> str:
    """Build an ffmpeg zoompan expression for a Ken Burns move (no commas → argv-safe)."""
    n = max(1, frames - 1)
    zoom = 1.10
    centered_x = "iw/2-(iw/zoom/2)"
    centered_y = "ih/2-(ih/zoom/2)"
    if move == "push_in":
        z, x, y = f"1+0.10*on/{n}", centered_x, centered_y
    elif move == "pull_out":
        z, x, y = f"1.10-0.10*on/{n}", centered_x, centered_y
    elif move == "pan_left":
        z, x, y = f"{zoom}", f"(iw-iw/zoom)*(1-on/{n})", centered_y
    elif move == "pan_right":
        z, x, y = f"{zoom}", f"(iw-iw/zoom)*(on/{n})", centered_y
    elif move == "pan_up":
        z, x, y = f"{zoom}", centered_x, f"(ih-ih/zoom)*(1-on/{n})"
    elif move == "pan_down":
        z, x, y = f"{zoom}", centered_x, f"(ih-ih/zoom)*(on/{n})"
    else:
        raise ValueError(f"unknown ken burns move: {move!r} (expected one of {_MOVES})")
    # Pre-upscale 2x to reduce zoompan's integer-step jitter.
    return f"scale=iw*2:ih*2,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps}"


def ken_burns(
    image_path: Path,
    move: str,
    duration_sec: float,
    out_path: Path,
    *,
    fps: int,
    width: int,
    height: int,
) -> Path:
    """Render a still into a `duration_sec` Ken Burns clip at `out_path` (H.264)."""
    frames = max(2, round(duration_sec * fps))
    vf = _zoompan_filter(move, frames, width, height, fps)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
            "-t", f"{duration_sec}", "-r", str(fps),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path
