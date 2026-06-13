"""Configuration loading: settings.yaml + .env (BUILD.md §6/§8).

Every module gets its config through `load_settings()` / `load_series_bible()`
rather than reading files or env vars directly.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

from src.schemas import SeriesBible

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
SERIES_DIR = PROJECT_ROOT / "config" / "series"

load_dotenv(PROJECT_ROOT / ".env")


class PathsConfig(BaseModel):
    episodes: Path = Path("episodes")
    ready_to_post: Path = Path("ready_to_post")
    models: Path = Path("models")


class VideoConfig(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    target_duration_sec: int = 72
    min_duration_sec: int = 62
    # Per-shot pacing: each scene is one held image. Vary shot length in this range
    # (quick cuts on punchy dialogue, a beat longer on emotional/establishing shots).
    min_shot_sec: float = 4
    max_shot_sec: float = 7


class ImageConfig(BaseModel):
    backend: str = "mflux"
    model: str = "flux2-klein-4b"  # Apache-2.0, on-device trainable, native multi-reference editing
    steps: int = 4
    quantize: int | None = None  # 4 or 8 to shrink memory footprint; None = full precision
    guidance: float = 1.0  # klein-4b is distilled → must be 1.0
    # Character consistency:
    use_references: bool = True  # feed each character's reference image so the model keeps them consistent
    lora_path: str | None = None  # global LoRA override; if unset, the series bible's `lora` is used
    lora_scale: float = 1.0


class HookConfig(BaseModel):
    backend: str = "ltx"  # ltx (generate) | library (pick a clip) | kenburns (image-motion only)
    max_seconds: float = 4
    allow_library_fallback: bool = True  # on ltx failure, fall back to the image-motion ken-burns hook
    # LTX-Video image-to-video (diffusers). Conditions on a FLUX keyframe so the motion clip
    # stays on-style; rendered small then upscaled to video.{width,height}. Heavy on MPS — the
    # hook stage frees FLUX before loading LTX, and never runs concurrently with image gen.
    model: str = "Lightricks/LTX-Video"
    steps: int = 30
    gen_width: int = 480  # LTX gen resolution (÷32); upscaled+cropped to the video size
    gen_height: int = 832
    frame_rate: int = 24  # LTX native rate; the clip is retimed to video.fps on encode
    ltx_guidance: float = 4.5  # higher → LTX follows the "explosive action" prompt harder (more motion)
    seed: int = 42
    # Hook SFX: render `episode.hook.sfx` (the scripted sound, e.g. "metal groan into water roar")
    # to matching audio with AudioLDM2 (diffusers/MPS) instead of the generic synthesized stinger.
    # Falls back to the synth stinger when disabled, when `hook.sfx` is empty, or on any failure.
    sfx: bool = True
    sfx_model: str = "cvssp/audioldm2"
    sfx_steps: int = 120
    sfx_guidance: float = 3.5


class TTSConfig(BaseModel):
    backend: str = "kokoro"
    # Kokoro voice for third-person narration; quoted character dialogue uses that
    # character's own `voice` from the bible (falling back to this when unset).
    narrator_voice: str = "am_onyx"  # deep, theatrical — dramatic narration
    narrator_speed: float = 1.1  # punchy but weighty
    speed: float = 1.2  # character dialogue: faster = younger/more energetic


class MusicConfig(BaseModel):
    backend: str = "ace-step"
    gain_under_voice: float = 0.18  # base music level under narration (linear gain) before sidechain ducking
    duck: bool = True  # sidechain-compress the bed against the narration so it dips while the VO speaks
    # ACE-Step runs in its own isolated venv (separate from the main pinned stack); music.py shells out to it.
    python: Path = Path("models/acestep/venv/bin/python")
    gen_script: Path = Path("scripts/acestep_gen.py")
    checkpoint_dir: Path = Path("models/acestep/checkpoints")
    infer_steps: int = 30
    seed: int = 42


class CaptionsConfig(BaseModel):
    font: Path = Path("assets/fonts/Bold.ttf")
    words_per_group: int = 4
    position: str = "lower_third"
    active_color: str = "yellow"


class FramingConfig(BaseModel):
    """Vision-guided Ken Burns (M5). When enabled, a local moondream2 pass locates the
    focal character per scene and the shot pushes in toward them; otherwise the scripted
    `motion.move` is used as-is."""

    enabled: bool = True
    target_fill: float = 0.6  # the focal box should occupy ~this fraction of the frame at the end of the push-in
    min_zoom: float = 1.15  # ensure a noticeable move even when the subject is already large
    max_zoom: float = 1.6


class AudioConfig(BaseModel):
    target_lufs: float = -14
    true_peak: float = -1.5


class LLMConfig(BaseModel):
    model: str = "claude-opus-4-8"
    effort: str = "medium"


class Settings(BaseModel):
    paths: PathsConfig = PathsConfig()
    video: VideoConfig = VideoConfig()
    image: ImageConfig = ImageConfig()
    hook: HookConfig = HookConfig()
    tts: TTSConfig = TTSConfig()
    music: MusicConfig = MusicConfig()
    captions: CaptionsConfig = CaptionsConfig()
    framing: FramingConfig = FramingConfig()
    audio: AudioConfig = AudioConfig()
    llm: LLMConfig = LLMConfig()

    def episodes_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.episodes

    def ready_to_post_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.ready_to_post

    def models_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.models


def load_settings(path: Path = SETTINGS_PATH) -> Settings:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Settings.model_validate(data)


def load_series_bible(series_id: str) -> SeriesBible:
    path = SERIES_DIR / f"{series_id}.json"
    return SeriesBible.model_validate_json(path.read_text())


def save_series_bible(bible: SeriesBible) -> None:
    path = SERIES_DIR / f"{bible.series_id}.json"
    path.write_text(bible.model_dump_json(indent=2) + "\n")


def anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — add it to .env")
    return key
