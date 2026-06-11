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


class ImageConfig(BaseModel):
    backend: str = "mflux"
    model: str = "flux-schnell"
    steps: int = 4


class HookConfig(BaseModel):
    backend: str = "ltx"
    max_seconds: float = 4
    allow_library_fallback: bool = True


class TTSConfig(BaseModel):
    backend: str = "kokoro"


class MusicConfig(BaseModel):
    backend: str = "ace-step"
    gain_under_voice: float = 0.18


class CaptionsConfig(BaseModel):
    font: Path = Path("assets/fonts/Bold.ttf")
    words_per_group: int = 4
    position: str = "lower_third"
    active_color: str = "yellow"


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
