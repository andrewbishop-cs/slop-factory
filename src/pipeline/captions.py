"""Stage 6 — karaoke captions (M4).

WhisperX **forced alignment**: each scene's narration text is already known, so we
align it against that scene's wav to get per-word timestamps (no transcription guesswork),
then emit a single `captions.ass` on the *body* timeline — scene k starts at the sum of the
earlier scenes' `duration_sec`, and its narration is assumed to start at that scene boundary
(the convention M5/assemble must honor when it lays the wavs down). Words are grouped
(`captions.words_per_group`) into karaoke lines using `\\kf` fill tags so the active word
sweeps the configured colour; a scene's optional `top_text` is rendered as a top band for the
whole scene.
"""

from __future__ import annotations

from pathlib import Path

import whisperx

from src.config import PROJECT_ROOT, CaptionsConfig, Settings
from src.pipeline import timing
from src.schemas import Episode

ALIGN_DEVICE = "cpu"  # wav2vec2 forced alignment; CPU is reliable on Apple Silicon and clips are short
ALIGN_LANGUAGE = "en"
AUDIO_SAMPLE_RATE = 16_000  # whisperx.load_audio resamples to 16 kHz

# ASS colours are &HAABBGGRR (alpha, blue, green, red).
_COLORS = {
    "white": "&H00FFFFFF",
    "yellow": "&H0000FFFF",
    "cyan": "&H00FFFF00",
    "green": "&H0000FF00",
    "red": "&H000000FF",
    "magenta": "&H00FF00FF",
    "orange": "&H000099FF",
    "black": "&H00000000",
}


def _ass_time(t: float) -> str:
    cs = max(0, round(t * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    """Neutralise characters that ASS treats specially in an event body."""
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def _font_name(cfg: CaptionsConfig) -> str:
    """Family name for the style. Falls back to a system font when the asset is absent
    (M5 burns with libass; a missing custom font would otherwise render as nothing)."""
    path = PROJECT_ROOT / cfg.font
    if path.exists() and path.stat().st_size > 0:
        return path.stem
    print(f"[captions] font {cfg.font} not found — falling back to Arial")
    return "Arial"


def _load_align_model():
    return whisperx.load_align_model(language_code=ALIGN_LANGUAGE, device=ALIGN_DEVICE)


def _aligned_words(model, metadata, wav_path: Path, text: str) -> tuple[list[dict], float]:
    """Forced-align `text` against `wav_path`; return (words, clip_duration_sec).

    Each word is `{"word", "start", "end"}` with any missing timestamps filled from neighbours
    so the karaoke timeline stays monotonic even for unalignable tokens (digits, symbols)."""
    audio = whisperx.load_audio(str(wav_path))
    duration = len(audio) / AUDIO_SAMPLE_RATE
    segments = [{"text": text.strip(), "start": 0.0, "end": duration}]
    result = whisperx.align(segments, model, metadata, audio, ALIGN_DEVICE, return_char_alignments=False)
    raw = result.get("word_segments", [])

    words: list[dict] = []
    last_end = 0.0
    for w in raw:
        start = w.get("start")
        start = float(start) if start is not None else last_end
        end = w.get("end")
        end = float(end) if end is not None else start
        if end < start:
            end = start
        words.append({"word": w.get("word", ""), "start": start, "end": end})
        last_end = end

    # A trailing word that never got an end time: stretch it to the clip end.
    for w in reversed(words):
        if w["end"] <= w["start"]:
            w["end"] = duration
        break
    return words, duration


def _karaoke_line(words: list[dict], offset: float) -> tuple[float, float, str]:
    """Build one karaoke Dialogue body for a group of words, timed on the global body
    timeline. `\\kf` duration per word runs to the next word's start so the sweep stays in sync."""
    start = offset + words[0]["start"]
    end = offset + words[-1]["end"]
    chunks: list[str] = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else w["end"]
        dur_cs = max(1, round((nxt - w["start"]) * 100))
        chunks.append(f"{{\\kf{dur_cs}}}{_ass_escape(w['word'])} ")
    return start, end, "".join(chunks).rstrip()


def _styles_block(cfg: CaptionsConfig, height: int) -> str:
    font = _font_name(cfg)
    active = _COLORS.get(cfg.active_color.lower(), _COLORS["yellow"])
    inactive = _COLORS["white"]
    outline = _COLORS["black"]
    kara_size = round(height * 0.05)  # ~96px at 1920 — punchy lower-third caption
    top_size = round(height * 0.034)
    margin_v = round(height * 0.22)  # lift bottom-anchored text into the lower third
    # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
    # Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline,
    # Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    return (
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Karaoke,{font},{kara_size},{active},{inactive},{outline},&H64000000,"
        f"-1,0,0,0,100,100,0,0,1,4,2,2,60,60,{margin_v},1\n"
        f"Style: Top,{font},{top_size},{inactive},{inactive},{outline},&H64000000,"
        f"-1,0,0,0,100,100,0,0,1,3,1,8,60,60,90,1\n"
    )


def _header(width: int, height: int) -> str:
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n\n"
    )


def generate_captions(settings: Settings, episode: Episode, episode_dir: Path) -> Path:
    """Align narration wavs against their text and write `captions.ass`; returns its path."""
    audio_dir = episode_dir / "audio"
    durations = timing.shot_durations(episode, audio_dir)
    offsets = timing.scene_offsets(durations)
    words_per_group = max(1, settings.captions.words_per_group)

    model = metadata = None
    events: list[tuple[float, float, str, str]] = []  # (start, end, style, body)

    for scene, offset, shot_dur in zip(episode.scenes, offsets, durations):
        if scene.top_text:
            events.append((offset, offset + shot_dur, "Top", _ass_escape(scene.top_text)))

        text = scene.narration_text.strip()
        wav = audio_dir / f"scene_{scene.id:02d}.wav"
        if not text or not wav.exists():
            if text and not wav.exists():
                print(f"[{episode.episode_id}] captions scene {scene.id:02d}: no wav, skipping karaoke")
            continue

        if model is None:
            model, metadata = _load_align_model()
        words, _ = _aligned_words(model, metadata, wav, text)
        if not words:
            print(f"[{episode.episode_id}] captions scene {scene.id:02d}: alignment produced no words")
            continue

        for i in range(0, len(words), words_per_group):
            group = words[i : i + words_per_group]
            start, end, body = _karaoke_line(group, offset)
            events.append((start, end, "Karaoke", body))
        print(f"[{episode.episode_id}] captions scene {scene.id:02d}: {len(words)} words aligned")

    events.sort(key=lambda e: (e[0], e[1]))
    lines = [
        _header(settings.video.width, settings.video.height),
        _styles_block(settings.captions, settings.video.height),
        "\n[Events]\n",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
    ]
    for start, end, style, body in events:
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},{style},,0,0,0,,{body}\n")

    out = episode_dir / "captions.ass"
    out.write_text("".join(lines), encoding="utf-8")
    print(f"[{episode.episode_id}] captions: wrote {len(events)} events → {out.name}")
    return out
