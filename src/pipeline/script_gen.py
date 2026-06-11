"""Stage 1 — script generation (M1).

One-line prompt (or "continue") + series bible → validated `episode.json`
via Claude Opus 4.8 structured output. Updates the bible's `plot_state`.

The bible is series-agnostic: its creative-brief fields (premise, setting,
`episode_format`, characters, ...) are what make two different series produce
structurally different episodes from the same `Episode` schema.
"""

from __future__ import annotations

import json
from pathlib import Path

from anthropic import Anthropic

from src.config import Settings, anthropic_api_key, save_series_bible
from src.schemas import Episode, SeriesBible

SYSTEM_INSTRUCTIONS = """\
You are the head writer for a vertical short-form (TikTok) animated series. \
You write a single self-contained episode that is engineered to retain a scrolling viewer.

Hard requirements for every episode you write:
- Frame-1 hook: `hook_text` is an instant, curiosity-or-stakes opener, and `hook` is a \
≤4 second clip described in `hook.prompt` (set hook.type to "video"). No slow intros.
- `characters_present` must only contain character names defined in the series bible.
- Each scene's `image_prompt` describes the SHOT — composition, action, framing, lighting beat. \
Refer to characters by their bible name. Do NOT restate a character's physical appearance or the \
global art style: those are applied automatically at render time, so restating them is wasteful.
- Every scene needs `narration_text`, a `mood` (short phrase) and an `intensity` in [0,1] that \
tracks the emotional arc (calmer setup → peak near the climax).
- `cliffhanger_text` must be loopable: it should make the viewer want the next episode and ideally \
loop back into the hook.
- `caption.description` is keyword-led (front-load the searchable hook), includes relevant hashtags, \
and `caption.ai_label` is true.
- `music.global_mood` matches the episode; give a `bpm_hint` when it helps.
- DURATION IS A HARD GATE: hook.duration_sec + sum(scene.duration_sec) MUST be >= the stated \
minimum and should land near the stated target. Budget scene durations to hit it.

Honor the series bible's `episode_format`, `tone`, `setting`, and each character's `personality` \
so the episode is unmistakably an episode of THIS series.

If the series has a SEASON ARC: this episode is one beat in a longer story, not a standalone. \
Use the stated episode number and the arc's `synopsis`/`pacing_notes` to decide this episode's purpose \
— vary it per `episode_purposes` and DON'T default to a race every time (races are spaced tentpole \
events). Advance the overarching plot, plant or pay off a seed toward the finale, and keep continuity \
with the recent episodes. If this is the FINAL episode, deliver the arc's `finale`. Return only the \
structured episode."""


def _render_bible(bible: SeriesBible) -> str:
    """Stable, cacheable text block describing the series for the model."""
    lines: list[str] = []
    lines.append(f"SERIES: {bible.display_name or bible.series_id} (id: {bible.series_id})")
    if bible.logline:
        lines.append(f"LOGLINE: {bible.logline}")
    lines.append(f"PREMISE: {bible.premise}")
    if bible.setting:
        lines.append(f"SETTING: {bible.setting}")
    if bible.tone:
        lines.append(f"TONE: {bible.tone}")
    lines.append(f"ART STYLE (applied at render — do not restate in image prompts): {bible.style_anchor}")
    if bible.episode_format:
        lines.append(f"EPISODE FORMAT: {bible.episode_format}")
    if bible.arc:
        a = bible.arc
        lines.append(f"SEASON ARC ({a.total_episodes} episodes):")
        lines.append(f"  synopsis: {a.synopsis}")
        lines.append(f"  finale: {a.finale}")
        if a.episode_purposes:
            lines.append("  episode purposes to vary across the season:")
            lines.extend(f"    - {p}" for p in a.episode_purposes)
        if a.pacing_notes:
            lines.append(f"  pacing: {a.pacing_notes}")
    lines.append("CHARACTERS:")
    for c in bible.characters:
        lines.append(f"  - {c.name}: {c.personality}. Appearance: {c.appearance_tokens}")
    return "\n".join(lines)


def _render_plot_state(bible: SeriesBible) -> str:
    ps = bible.plot_state
    parts = [
        f"active_threads: {ps.active_threads or '(none)'}",
        f"last_cliffhanger: {ps.last_cliffhanger or '(none — this is an early episode)'}",
        f"recent_episodes: {ps.episode_log[-5:] or '(none yet)'}",
    ]
    return "\n".join(parts)


def episode_number(bible: SeriesBible) -> int:
    """1-based ordinal of the episode about to be written (next after the log)."""
    return len(bible.plot_state.episode_log) + 1


def _render_position(bible: SeriesBible) -> str:
    """Where this episode sits in the season — drives purpose + finale handling."""
    n = episode_number(bible)
    if not bible.arc:
        return f"EPISODE POSITION: this is episode {n} (no fixed season length)."
    total = bible.arc.total_episodes
    if n >= total:
        role = "This is the FINALE — deliver the arc's `finale` (the Sewer Crown race, the winner, a victory lap)."
    elif n == 1:
        role = "Season opener — throw the viewer straight into a high-stakes race to hook them."
    elif n >= total - 2:
        role = "Late season — raise the stakes hard and set up the imminent finale."
    else:
        role = "Mid-season — pick a NON-race purpose from the arc unless a race is specifically earned here; advance the overarching plot and build anticipation."
    return f"EPISODE POSITION: episode {n} of {total}. {role}"


# Validation keywords pydantic emits (from Field(gt=, le=, min_length=, ...)) that
# Anthropic's `json_schema` output format rejects. We strip them from the schema sent
# to the model; pydantic still enforces every one of them when we validate the result.
_UNSUPPORTED_SCHEMA_KEYS = frozenset({
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern", "format", "minItems", "maxItems", "uniqueItems",
})


def _episode_schema() -> dict:
    """Episode JSON schema, sanitized for Anthropic structured output."""
    schema = Episode.model_json_schema()

    def _sanitize(node: object) -> None:
        if isinstance(node, dict):
            for key in _UNSUPPORTED_SCHEMA_KEYS & node.keys():
                del node[key]
            for value in node.values():
                _sanitize(value)
        elif isinstance(node, list):
            for item in node:
                _sanitize(item)

    _sanitize(schema)
    return schema


def _extract_json(resp) -> dict:
    """Collect the structured JSON from the response's text blocks."""
    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    if not text.strip():
        raise RuntimeError("script_gen: model returned no text content")
    return json.loads(text)


def generate_script(
    settings: Settings,
    bible: SeriesBible,
    episode_dir: Path,
    prompt: str | None = None,
) -> Episode:
    """Generate `episode.json` in `episode_dir`. `prompt=None` means continue the plot."""
    episode_id = episode_dir.name
    target = settings.video.target_duration_sec
    minimum = settings.video.min_duration_sec

    if prompt:
        task = f'Write the next episode from this one-line idea:\n"{prompt}"'
    else:
        task = (
            "Continue the series from the current plot state below — pay off or advance "
            "the last cliffhanger and the active threads."
        )

    user_text = (
        f"{task}\n\n"
        f"{_render_position(bible)}\n\n"
        f"CURRENT PLOT STATE:\n{_render_plot_state(bible)}\n\n"
        f"DURATION TARGET: aim for ~{target}s total; the hard minimum (hook + all scenes) "
        f"is {minimum}s. Set target_duration_sec to {target}."
    )

    client = Anthropic(api_key=anthropic_api_key())
    resp = client.messages.create(
        model=settings.llm.model,
        max_tokens=8000,
        system=[
            {"type": "text", "text": SYSTEM_INSTRUCTIONS},
            # The bible is the stable prefix — cache it across episodes of this series.
            {
                "type": "text",
                "text": "SERIES BIBLE\n" + _render_bible(bible),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": user_text}],
        output_config={
            "effort": settings.llm.effort,
            "format": {"type": "json_schema", "schema": _episode_schema()},
        },
    )

    data = _extract_json(resp)
    # The orchestrator owns identity; never trust the model for these.
    data["episode_id"] = episode_id
    data["series_id"] = bible.series_id
    episode = Episode.model_validate(data)

    if episode.total_duration_sec < minimum:
        raise RuntimeError(
            f"script_gen: episode {episode_id} is {episode.total_duration_sec:.1f}s, "
            f"below the {minimum}s minimum (hook + scenes). Re-run to regenerate."
        )

    (episode_dir / "episode.json").write_text(episode.model_dump_json(indent=2) + "\n")
    _update_plot_state(bible, episode)
    return episode


def _update_plot_state(bible: SeriesBible, episode: Episode) -> None:
    """Record this episode in the bible so `--continue` has continuity to build on."""
    bible.plot_state.last_cliffhanger = episode.cliffhanger_text
    bible.plot_state.episode_log.append(f"{episode.episode_id}: {episode.title}")
    save_series_bible(bible)
