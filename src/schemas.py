"""Pydantic models for episode scripts and series bibles (BUILD.md §8).

`Episode` is the contract between script_gen and every downstream stage;
`SeriesBible` carries cross-episode continuity.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Hook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["video", "library"]
    prompt: str | None = None
    library_clip: str | None = None
    duration_sec: float = Field(gt=0, le=4)
    sfx: str | None = None


class Motion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["ken_burns"] = "ken_burns"
    move: Literal["push_in", "pull_out", "pan_left", "pan_right", "pan_up", "pan_down"]
    duration_sec: float = Field(gt=0)


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    image_prompt: str
    motion: Motion
    narration_text: str
    top_text: str | None = None
    mood: str
    intensity: float = Field(ge=0, le=1)
    duration_sec: float = Field(gt=0)


class Music(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_mood: str
    bpm_hint: int | None = Field(default=None, gt=0)


class Caption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    hashtags: list[str]
    ai_label: bool = True


class Episode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str
    series_id: str
    title: str
    hook_text: str
    hook: Hook
    characters_present: list[str]
    scenes: list[Scene] = Field(min_length=1)
    cliffhanger_text: str
    music: Music
    caption: Caption
    target_duration_sec: float = Field(gt=0)

    @property
    def total_duration_sec(self) -> float:
        """Hook + all scene durations."""
        return self.hook.duration_sec + sum(s.duration_sec for s in self.scenes)


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    appearance_tokens: str
    personality: str
    reference_image: str | None = None
    voice: str | None = None  # path to a sample wav, or a Kokoro voice id


class PlotState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_threads: list[str] = Field(default_factory=list)
    last_cliffhanger: str | None = None
    episode_log: list[str] = Field(default_factory=list)


class SeriesBible(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_id: str
    premise: str
    style_anchor: str
    characters: list[Character] = Field(min_length=1)
    plot_state: PlotState = Field(default_factory=PlotState)
