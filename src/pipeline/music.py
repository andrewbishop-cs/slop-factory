"""Stage 5 — music bed (M6).

Generates one instrumental bed for the episode with ACE-Step, keyed to the
episode's mood/intensity arc. ACE-Step lives in its OWN isolated venv
(`settings.music.python`) so its heavy ML deps never touch the main pinned
stack — this stage only builds the prompt and shells out to it. Output:
`audio/music.wav` spanning the full body. Idempotent: an existing wav is reused.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.config import PROJECT_ROOT, Settings
from src.pipeline import logging_setup, timing
from src.schemas import Episode

MAX_DURATION = 240.0  # ACE-Step practical ceiling for a single generation


def _energy_word(intensity: float) -> str:
    if intensity >= 0.75:
        return "high-energy, intense, driving"
    if intensity >= 0.45:
        return "energetic, upbeat"
    return "mellow, atmospheric"


def _build_prompt(episode: Episode) -> str:
    """ACE-Step takes comma-separated style/mood tags. Key it to the episode's
    global mood + the average scene intensity, and force an instrumental bed."""
    intensities = [s.intensity for s in episode.scenes] or [0.5]
    avg = sum(intensities) / len(intensities)
    tags = [
        episode.music.global_mood.strip(),
        "instrumental",
        "no vocals",
        "cinematic underscore for a fast-paced sports cartoon",
        _energy_word(avg),
        "driving percussion, rhythmic",
    ]
    if episode.music.bpm_hint:
        tags.append(f"{episode.music.bpm_hint} bpm")
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tags:
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            ordered.append(t)
    return ", ".join(ordered)


def _resolve(p: Path) -> Path:
    return p if p.is_absolute() else PROJECT_ROOT / p


def generate_music(settings: Settings, episode: Episode, episode_dir: Path) -> Path:
    """Render `audio/music.wav` (≥ body duration) via the isolated ACE-Step venv."""
    log = logging_setup.get_logger()
    audio_dir = episode_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out = audio_dir / "music.wav"
    if out.exists():
        log.info("music: exists, skipping (%s)", out.name)
        return out

    body_len = sum(timing.shot_durations(episode, audio_dir))
    duration = min(MAX_DURATION, max(body_len + 1.0, episode.total_duration_sec))
    prompt = _build_prompt(episode)

    cfg = settings.music
    python = _resolve(cfg.python)
    gen_script = _resolve(cfg.gen_script)
    ckpt = _resolve(cfg.checkpoint_dir)
    if not python.exists():
        raise RuntimeError(
            f"music: ACE-Step interpreter not found at {python}. Set up the isolated "
            "venv (BUILD.md M6) or fix settings.music.python."
        )

    cmd = [
        str(python), str(gen_script),
        "--prompt", prompt,
        "--duration", f"{duration:.2f}",
        "--output", str(out.resolve()),
        "--checkpoint-dir", str(ckpt),
        "--steps", str(cfg.infer_steps),
        "--seed", str(cfg.seed),
    ]
    log.info("music: generating %.1fs bed via ACE-Step — %s", duration, prompt)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-20:])
        log.error("music: ACE-Step failed (exit %d):\n%s", proc.returncode, tail)
        raise RuntimeError(f"music generation failed: ace-step exit {proc.returncode}")
    if not out.exists():
        raise RuntimeError(f"music: ACE-Step reported success but {out} is missing")
    log.info("music: wrote %s", out.name)
    return out
