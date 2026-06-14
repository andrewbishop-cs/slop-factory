"""Stage 2 — image generation (M2).

One keyframe per scene via mflux on **FLUX.2-klein-4B** (Apache-2.0, on-device
trainable), rendered portrait to `images/scene_NN.png`. Also `ken_burns()`: turn a
still into a moving clip (ffmpeg `zoompan`) — defined here, exercised by assemble (M5).

Character identity across shots (BUILD.md §9), weakest → strongest:
  1. Prompt anchoring (always on): every prompt is prefixed with the exact
     `appearance_tokens` of the characters in the shot + the series `style_anchor`
     + `world_anchor` (recurring props/setting, e.g. "hydro-boards, never motorcycles").
  2. Multi-reference conditioning (on when references exist): FLUX.2's edit path takes
     each present character's `reference_image` as `image_paths=[...]`, so the model
     reproduces the *same* character while composing the new scene. This is the main
     identity lock and needs no training — run `scripts/establish_characters.py` once.
  3. Trained per-series LoRA (opt-in `bible.lora`): the production lock; when present we
     load it and swap each character's name for its `lora_trigger` in the prompt.
A single `Flux2KleinEdit` instance serves all scenes — with no references it falls back
to plain text-to-image, so reference and non-reference scenes share one loaded model.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from mflux.models.common.config import ModelConfig
from mflux.models.flux2.variants import Flux2KleinEdit
from PIL import Image

from src.config import PROJECT_ROOT, Settings
from src.schemas import Character, Episode, Motion, Scene, SeriesBible

_MOVES = ("push_in", "pull_out", "pan_left", "pan_right", "pan_up", "pan_down")


def _round_up_16(n: int) -> int:
    """FLUX needs dimensions that are multiples of 16."""
    return ((n + 15) // 16) * 16


def _gen_dims(width: int, height: int) -> tuple[int, int]:
    return _round_up_16(width), _round_up_16(height)


def _stable_seed(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _present_characters(episode: Episode, bible: SeriesBible) -> list[Character]:
    """Characters listed in the episode's `characters_present` (matched to the bible)."""
    present = {p.lower() for p in episode.characters_present}
    return [c for c in bible.characters if c.name.lower() in present]


def _characters_in_scene(scene: Scene, episode: Episode, bible: SeriesBible) -> list[Character]:
    """Characters in a shot: those named in the prompt, else the episode's present cast.

    The Flux2KleinEdit path requires at least one reference image, so a scene that
    names nobody (e.g. "both riders burst out") must still resolve to the present
    cast rather than producing an empty reference list (which crashes mflux).
    """
    named = [c for c in bible.characters if re.search(rf"\b{re.escape(c.name)}\b", scene.image_prompt, re.IGNORECASE)]
    return named or _present_characters(episode, bible)


def _lora_args(settings: Settings, bible: SeriesBible) -> tuple[list[str] | None, list[float] | None]:
    """Resolve the LoRA to load: explicit config override wins, else the series' trained LoRA."""
    if settings.image.lora_path:
        path = PROJECT_ROOT / settings.image.lora_path
        if path.exists():
            return [str(path)], [settings.image.lora_scale]
    if bible.lora and bible.lora.trained:
        path = PROJECT_ROOT / bible.lora.path
        if path.exists():
            return [str(path)], [bible.lora.scale]
    return None, None


def _use_trigger(bible: SeriesBible) -> bool:
    return bool(bible.lora and bible.lora.trained and (PROJECT_ROOT / bible.lora.path).exists())


def _build_prompt(scene: Scene, bible: SeriesBible, characters: list[Character], use_trigger: bool) -> str:
    """Anchor the shot, leading with the art style (diffusion weights early tokens most).

    Reference-image conditioning tends to copy the neutral character sheet — and the sheets
    here put each character standing on a board against a blank studio backdrop, so the edit
    path leaks all three: a board under the feet, a water splash, and a plain white background.
    With klein's forced `guidance=1.0` the negative-prompt path is disabled, so we steer
    positively against each leak:
      - inject the scene `mood` as an explicit performance + demand a dynamic pose;
      - for solo shots assert a single subject to suppress background clones;
      - always demand a fully-rendered `location` filling the frame (kills the blank backdrop);
      - branch on `scene.on_board`: riding shots get the boards + rushing-water `riding_anchor`,
        while grounded shots get an explicit on-foot / solid-ground anchor and the per-character
        board tokens are withheld (so dialogue/interior beats aren't forced onto boards or water).
    """
    parts: list[str] = []
    labels: list[str] = []
    for c in characters:
        label = c.lora_trigger if (use_trigger and c.lora_trigger) else c.name
        labels.append(label)
        parts.append(f"{label} ({c.appearance_tokens})")
    who = ("Characters — " + "; ".join(parts) + ". ") if parts else ""

    emotion = (
        f" Emotion and acting: clearly express {scene.mood} through a vivid, exaggerated facial "
        f"expression and a dynamic mid-action body pose — not a neutral standing pose, not a faint smile."
    )
    if len(labels) == 1:
        framing = (
            f" Single subject: only {labels[0]} appears — exactly one character, "
            f"no duplicate, cloned, mirrored, or background copies of the character."
        )
    elif len(labels) > 1:
        framing = (
            f" Exactly these {len(labels)} characters appear ({', '.join(labels)}) — "
            f"no extra, duplicate, or cloned characters."
        )
    else:
        framing = ""

    setting = f" Setting — {scene.location.strip()}." if scene.location.strip() else ""
    # Always fill the frame with the environment; the reference sheets are shot on a blank studio
    # backdrop and the edit path will copy that empty background unless we explicitly forbid it.
    environment = (
        " The full location is rendered in detail behind and around the characters and fills the "
        "entire frame — never a plain white, grey, gradient, studio, seamless, or empty background."
    )
    world = f" World: {bible.world_anchor.strip()}" if bible.world_anchor else ""

    if scene.on_board:
        boards = "; ".join(f"{c.name} on {c.board_tokens}" for c in characters if c.board_tokens)
        ride = f" {bible.riding_anchor.strip()}" if bible.riding_anchor else ""
        mode = f"{ride}" + (f" Boards in this shot: {boards}." if boards else "")
    else:
        # Counter the reference sheet's board-under-feet + water splash for non-riding beats. A board
        # may still appear as an object (built, carried, leaning) — it just isn't being ridden.
        mode = (
            " The characters are on foot on solid ground — standing, walking, sitting, crouching, "
            "leaning, or gesturing on a solid surface (concrete walkway, floor, ledge, workshop floor). "
            "They are NOT surfing in this shot: no board under their feet and no rushing water beneath "
            "them — the ground is solid, dry footing. Any board present is an inert object being built, "
            "carried, or leaning, never ridden."
        )

    return (
        f"{bible.style_anchor}. In this exact style: {who}{scene.image_prompt.strip()}"
        f"{emotion}{framing}{setting}{environment}{world}{mode}"
    )


def _scene_reference_paths(characters: list[Character], settings: Settings) -> list[str]:
    """Existing reference images for the characters in a shot (multi-reference conditioning)."""
    if not settings.image.use_references:
        return []
    paths: list[str] = []
    for c in characters:
        if c.reference_image:
            path = PROJECT_ROOT / c.reference_image
            if path.exists():
                paths.append(str(path))
    return paths


def _load_model(settings: Settings, bible: SeriesBible) -> Flux2KleinEdit:
    lora_paths, lora_scales = _lora_args(settings, bible)
    return Flux2KleinEdit(
        model_config=ModelConfig.from_name(settings.image.model),
        quantize=settings.image.quantize,
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
    use_trigger = _use_trigger(bible)

    model: Flux2KleinEdit | None = None
    outputs: list[Path] = []
    for scene in episode.scenes:
        out = images_dir / f"scene_{scene.id:02d}.png"
        outputs.append(out)
        if out.exists():
            print(f"[{episode.episode_id}] image scene {scene.id:02d}: exists, skipping")
            continue

        characters = _characters_in_scene(scene, episode, bible)
        prompt = _build_prompt(scene, bible, characters, use_trigger)
        references = _scene_reference_paths(characters, settings)
        if settings.image.use_references and not references:
            raise ValueError(
                f"scene {scene.id:02d}: Flux2KleinEdit requires at least one reference image, but none were "
                f"found for {[c.name for c in characters] or 'this scene'}. Run scripts/establish_characters.py "
                f"--series {episode.series_id} first, or disable image.use_references."
            )
        seed_key = characters[0].name if characters else episode.series_id
        seed = _stable_seed(episode.series_id, seed_key, str(scene.id))

        if model is None:
            model = _load_model(settings, bible)

        ref_note = f"{len(references)} ref(s)" if references else "no refs"
        print(f"[{episode.episode_id}] image scene {scene.id:02d}: rendering (seed {seed}, {ref_note})")
        result = model.generate_image(
            seed=seed,
            prompt=prompt,
            num_inference_steps=settings.image.steps,
            width=gen_w,
            height=gen_h,
            guidance=settings.image.guidance,
            image_paths=references or None,
        )
        _center_crop(result.image, target_w, target_h).save(out)

    return outputs


def generate_keyframe(
    settings: Settings,
    episode: Episode,
    bible: SeriesBible,
    prompt_text: str,
    out_path: Path,
    *,
    seed_key: str = "hook",
) -> Path:
    """Render one keyframe PNG from a free-form prompt (used by the hook stage).

    Reuses the scene prompt-anchoring + reference conditioning so the frame keeps character
    identity and series style. The FLUX instance is local and falls out of scope on return,
    so the heavy model is freed before the hook stage loads LTX. Idempotent.
    """
    if out_path.exists():
        return out_path
    # A throwaway single-shot scene to reuse the anchoring/reference machinery. The hook is always a
    # peak-action riding moment, so flag it on_board so the board + rushing-water anchor applies.
    scene = Scene(
        id=1,
        image_prompt=prompt_text,
        location="mid-action in a neon-lit storm-drain tunnel, rushing water and spray",
        on_board=True,
        motion=Motion(move="push_in", duration_sec=1.0),
        narration_text="",
        mood=episode.music.global_mood,
        intensity=1.0,
        duration_sec=1.0,
    )
    characters = _characters_in_scene(scene, episode, bible)
    prompt = _build_prompt(scene, bible, characters, _use_trigger(bible))
    references = _scene_reference_paths(characters, settings)
    if settings.image.use_references and not references:
        raise ValueError(
            f"hook keyframe: Flux2KleinEdit requires at least one reference image, but none were found "
            f"for {[c.name for c in characters] or 'this episode'}. Run scripts/establish_characters.py first."
        )

    target_w, target_h = settings.video.width, settings.video.height
    gen_w, gen_h = _gen_dims(target_w, target_h)
    seed = _stable_seed(episode.series_id, seed_key, episode.episode_id)
    model = _load_model(settings, bible)
    result = model.generate_image(
        seed=seed,
        prompt=prompt,
        num_inference_steps=settings.image.steps,
        width=gen_w,
        height=gen_h,
        guidance=settings.image.guidance,
        image_paths=references or None,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _center_crop(result.image, target_w, target_h).save(out_path)
    return out_path


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


def _zoompan_explicit(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    frames: int,
    width: int,
    height: int,
    fps: int,
) -> str:
    """Ken Burns between two explicit framings `(center_x, center_y, zoom)` in normalized
    coords — used by the vision-guided pass to push in toward a focal character. Expressions
    stay comma-free (zoompan params split on ':' and filters on ',') so the -vf arg is safe."""
    cx0, cy0, z0 = start
    cx1, cy1, z1 = end
    n = max(1, frames - 1)
    z = f"{z0}+({z1}-{z0})*on/{n}"
    cx = f"{cx0}+({cx1}-{cx0})*on/{n}"
    cy = f"{cy0}+({cy1}-{cy0})*on/{n}"
    # top-left of the crop = center*size - half the (size/zoom) visible window; zoompan also clamps to edges.
    x = f"iw*({cx})-iw/(2*({z}))"
    y = f"ih*({cy})-ih/(2*({z}))"
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
    frame_start: tuple[float, float, float] | None = None,
    frame_end: tuple[float, float, float] | None = None,
) -> Path:
    """Render a still into a `duration_sec` Ken Burns clip at `out_path` (H.264).

    With `frame_start`/`frame_end` (each `(center_x, center_y, zoom)`, normalized) the motion
    interpolates between them (vision-guided framing); otherwise it uses the scripted `move`.
    """
    frames = max(2, round(duration_sec * fps))
    if frame_start is not None and frame_end is not None:
        vf = _zoompan_explicit(frame_start, frame_end, frames, width, height, fps)
    else:
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
