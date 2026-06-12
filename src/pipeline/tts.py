"""Stage 4 — narration TTS (M3).

Kokoro renders one wav per narrated scene. Voices are *locked*: third-person
narration is read by the series' narrator voice (`settings.tts.narrator_voice`),
while a scene whose `narration_text` is a quoted line is voiced by the character
speaking it — detected as the single bible character named in that scene's
`image_prompt` (the shot's subject) — using that character's `voice` from the bible.
Ambiguous or unattributed lines fall back to the narrator. One KPipeline is built
per language (the voice id's first letter, e.g. `a` = American English) and reused.
"""

from __future__ import annotations

import re
from pathlib import Path

import soundfile as sf
import torch
from kokoro import KPipeline

from src.config import Settings
from src.schemas import Character, Episode, Scene, SeriesBible

SAMPLE_RATE = 24_000  # Kokoro-82M always renders at 24 kHz

_OPEN_QUOTE = "\"“'‘"
_CLOSE_QUOTE = "\"”'’"


def _is_dialogue(text: str) -> bool:
    """A quoted line (a character speaking) rather than third-person narration."""
    t = text.strip()
    return len(t) >= 2 and t[0] in _OPEN_QUOTE and t[-1] in _CLOSE_QUOTE


def _named_characters(text: str, bible: SeriesBible) -> list[Character]:
    return [c for c in bible.characters if re.search(rf"\b{re.escape(c.name)}\b", text, re.IGNORECASE)]


def _voice_for_scene(scene: Scene, bible: SeriesBible, narrator_voice: str) -> tuple[str, str]:
    """Pick (voice_id, speaker_label) for a scene: the speaking character for an
    unambiguous quoted line, else the narrator."""
    if _is_dialogue(scene.narration_text):
        named = _named_characters(scene.image_prompt, bible)
        if len(named) == 1 and named[0].voice:
            return named[0].voice, named[0].name
    return narrator_voice, "narrator"


def _lang_code(voice: str) -> str:
    """Kokoro encodes language in the voice id's first letter (a=American English)."""
    return voice[0] if voice else "a"


def _synthesize(pipeline: KPipeline, text: str, voice: str, speed: float):
    """Run Kokoro and concatenate any chunked output into one mono waveform (numpy)."""
    chunks = [r.audio for r in pipeline(text, voice=voice, speed=speed) if r.audio is not None]
    if not chunks:
        raise RuntimeError(f"Kokoro produced no audio for: {text!r}")
    audio = chunks[0] if len(chunks) == 1 else torch.cat(chunks)
    return audio.detach().cpu().numpy()


def generate_narration(
    settings: Settings,
    episode: Episode,
    bible: SeriesBible,
    episode_dir: Path,
) -> list[Path]:
    """Render `audio/scene_NN.wav` for every narrated scene; returns the paths.

    Idempotent: an existing wav is skipped (delete it to re-render).
    """
    audio_dir = episode_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    narrator_voice = settings.tts.narrator_voice
    speed = settings.tts.speed

    pipelines: dict[str, KPipeline] = {}
    outputs: list[Path] = []
    for scene in episode.scenes:
        text = scene.narration_text.strip()
        if not text:
            print(f"[{episode.episode_id}] tts scene {scene.id:02d}: no narration, skipping")
            continue

        out = audio_dir / f"scene_{scene.id:02d}.wav"
        outputs.append(out)
        if out.exists():
            print(f"[{episode.episode_id}] tts scene {scene.id:02d}: exists, skipping")
            continue

        voice, speaker = _voice_for_scene(scene, bible, narrator_voice)
        lang = _lang_code(voice)
        if lang not in pipelines:
            pipelines[lang] = KPipeline(lang_code=lang)

        print(f"[{episode.episode_id}] tts scene {scene.id:02d}: rendering ({speaker} / {voice})")
        audio = _synthesize(pipelines[lang], text, voice, speed)
        sf.write(str(out), audio, SAMPLE_RATE)

    return outputs
