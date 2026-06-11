"""Orchestrator — runs stages 1–8 for an episode, resumable via state.json.

Usage (BUILD.md §11) — `--series` names any bible under config/series/<id>.json:
    uv run python -m src.pipeline.orchestrator --series sewer-surfers --prompt "..."
    uv run python -m src.pipeline.orchestrator --series sewer-surfers --continue
    uv run python -m src.pipeline.orchestrator --series sewer-surfers --episode sewer-surfers_ep_0007 --force images
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import Settings, load_series_bible, load_settings
from src.pipeline import assemble, captions, hook, images, music, qc, script_gen, tts
from src.schemas import Episode

# Pipeline order (script first; assemble after all assets exist).
STAGES = ["script", "images", "tts", "captions", "music", "hook", "assemble", "qc"]

STATE_FILE = "state.json"


def load_state(episode_dir: Path) -> dict[str, bool]:
    path = episode_dir / STATE_FILE
    if path.exists():
        return json.loads(path.read_text())
    return {stage: False for stage in STAGES}


def save_state(episode_dir: Path, state: dict[str, bool]) -> None:
    (episode_dir / STATE_FILE).write_text(json.dumps(state, indent=2) + "\n")


def next_episode_id(settings: Settings, series_id: str) -> str:
    """First unused `<series_id>_ep_NNNN` — episodes are numbered per series."""
    episodes_dir = settings.episodes_dir()
    prefix = f"{series_id}_ep_"
    existing = {p.name for p in episodes_dir.glob(f"{prefix}*")} if episodes_dir.exists() else set()
    n = 1
    while f"{prefix}{n:04d}" in existing:
        n += 1
    return f"{prefix}{n:04d}"


def load_episode(episode_dir: Path) -> Episode:
    return Episode.model_validate_json((episode_dir / "episode.json").read_text())


def run(
    series_id: str,
    prompt: str | None = None,
    episode_id: str | None = None,
    force: list[str] | None = None,
    until: str | None = None,
) -> Path:
    """Run the pipeline for one episode; returns the episode directory."""
    settings = load_settings()
    bible = load_series_bible(series_id)
    force = force or []

    episode_id = episode_id or next_episode_id(settings, series_id)
    episode_dir = settings.episodes_dir() / episode_id
    episode_dir.mkdir(parents=True, exist_ok=True)
    state = load_state(episode_dir)

    for stage in STAGES:
        if state.get(stage) and stage not in force:
            print(f"[{episode_id}] {stage}: done, skipping")
        else:
            print(f"[{episode_id}] {stage}: running")
            run_stage(stage, settings, bible, episode_dir, prompt)
            state[stage] = True
            save_state(episode_dir, state)
        if stage == until:
            break

    return episode_dir


def run_stage(stage, settings, bible, episode_dir, prompt):
    if stage == "script":
        script_gen.generate_script(settings, bible, episode_dir, prompt)
        return
    episode = load_episode(episode_dir)
    if stage == "images":
        images.generate_images(settings, episode, bible, episode_dir)
    elif stage == "tts":
        tts.generate_narration(settings, episode, bible, episode_dir)
    elif stage == "captions":
        captions.generate_captions(settings, episode, episode_dir)
    elif stage == "music":
        music.generate_music(settings, episode, episode_dir)
    elif stage == "hook":
        hook.generate_hook(settings, episode, episode_dir)
    elif stage == "assemble":
        assemble.assemble(settings, episode, episode_dir)
    elif stage == "qc":
        report = qc.run_qc(settings, episode, episode_dir)
        print(json.dumps(report, indent=2))
    else:
        raise ValueError(f"unknown stage: {stage}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the episode pipeline.")
    parser.add_argument("--series", required=True, help="series id (a bible under config/series/<id>.json), e.g. sewer-surfers")
    parser.add_argument("--prompt", help="one-line episode prompt")
    parser.add_argument("--continue", dest="continue_", action="store_true", help="continue from the last cliffhanger")
    parser.add_argument("--episode", help="existing episode id to resume, e.g. sewer-surfers_ep_0007")
    parser.add_argument("--force", nargs="*", default=[], choices=STAGES, help="stages to re-run even if done")
    parser.add_argument("--until", choices=STAGES, help="stop after this stage")
    args = parser.parse_args()

    if not args.prompt and not args.continue_ and not args.episode:
        parser.error("provide --prompt, --continue, or --episode")

    run(args.series, prompt=args.prompt, episode_id=args.episode, force=args.force, until=args.until)


if __name__ == "__main__":
    main()
