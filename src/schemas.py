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
    # Where the shot takes place (e.g. "inside the cluttered sewer-den workshop", "on a concrete
    # ledge over the drain", "mid-run on the rushing water"). Injected at render so every frame is
    # set in a real environment instead of the reference sheet's blank studio backdrop. Defaulted so
    # pre-existing episodes still validate; the writer is instructed to always fill it.
    location: str = ""
    # True ONLY when the characters are actively riding/surfing their boards in this shot. Gates the
    # board + rushing-water "riding" anchor; when false the shot is grounded (on foot, no board).
    on_board: bool = False
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
    appearance_tokens: str  # the character's body + outfit only — NOT their board/equipment (see board_tokens)
    board_tokens: str | None = None  # this rider's hydro-board, injected only into riding (on_board) shots
    personality: str
    reference_image: str | None = None  # canonical "character sheet" used for multi-reference consistency (M2)
    lora_trigger: str | None = None  # rare token this character maps to inside a trained LoRA, e.g. "ssriptide"
    voice: str | None = None  # path to a sample wav, or a Kokoro voice id
    detect_phrase: str | None = None  # short noun for the vision detector to localize this character, e.g. "monkey" (M5 Ken Burns framing)


class PlotState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_threads: list[str] = Field(default_factory=list)
    last_cliffhanger: str | None = None
    episode_log: list[str] = Field(default_factory=list)


class LoraSpec(BaseModel):
    """A trained character/style LoRA for a series (the Tier-2 consistency lock).

    `images.py` loads it on top of the base model when `trained` is true and the
    file exists; until then the pipeline relies on reference-image conditioning.
    """

    model_config = ConfigDict(extra="forbid")

    path: str  # safetensors path, relative to repo root
    scale: float = 1.0
    trained: bool = False  # flipped true by the training script once the file is produced


class SeasonArc(BaseModel):
    """A planned, multi-episode season trajectory so each episode can advance an
    overarching story rather than being a standalone. Optional — series that want
    pure episodic content can omit it.
    """

    model_config = ConfigDict(extra="forbid")

    total_episodes: int = Field(gt=0)
    synopsis: str  # the overarching shape: rising action → climax → resolution
    finale: str  # what the final episode(s) deliver
    episode_purposes: list[str] = Field(default_factory=list)  # palette of episode types to vary across the season
    pacing_notes: str | None = None  # how to space tentpole events, build anticipation, etc.


class SeriesBible(BaseModel):
    """Per-series continuity + creative brief. One JSON file per series under
    `config/series/<series_id>.json`; the pipeline is series-agnostic and loads
    whichever bible `--series` names, so adding a series is config, not code.

    The optional fields below are the per-series creative brief fed into the M1
    script prompt — they're how two series (a detective mystery vs. a sewer race)
    produce structurally different episodes from the same `Episode` schema. All
    are optional/defaulted so older bibles and the M0 checkpoint still validate.
    """

    model_config = ConfigDict(extra="forbid")

    series_id: str
    premise: str
    style_anchor: str  # global art-style tokens prepended to every image prompt
    characters: list[Character] = Field(min_length=1)
    plot_state: PlotState = Field(default_factory=PlotState)

    # Consistency anchors (M2). `world_anchor` is injected into EVERY image prompt like
    # `style_anchor` — the GENERAL world look + negative vehicle constraints (e.g. "never
    # motorcycles"), but NOT riding-only props. `riding_anchor` is injected ONLY into shots flagged
    # `on_board` (the boards + rushing water); grounded shots get an on-foot/solid-ground anchor
    # instead, so dialogue/interior beats aren't forced onto water. `lora` is the optional trained
    # per-series character LoRA.
    world_anchor: str | None = None
    riding_anchor: str | None = None
    lora: LoraSpec | None = None

    # Per-series creative brief (optional, additive — drives M1 script_gen).
    display_name: str | None = None  # human label, e.g. "Sewer Surfers"
    logline: str | None = None  # one-sentence pitch
    setting: str | None = None  # the world / where episodes take place
    episode_format: str | None = None  # how an episode of THIS series is structured
    tone: str | None = None  # comedic / noir / high-energy, etc.
    arc: SeasonArc | None = None  # planned season-long trajectory (None = purely episodic)
