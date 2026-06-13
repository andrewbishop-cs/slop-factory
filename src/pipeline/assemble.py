"""Stage 7 — final render (M5; music in M6, hook prepended in M7).

Builds the watchable body video with ffmpeg:
  1. one Ken Burns clip per scene (reusing `images.ken_burns`), each as long as the
     scene's effective shot duration (`timing.shot_durations`, so narration never clips);
  2. concatenate the clips into a silent body;
  3. lay each scene's narration wav at its scene boundary (padded with silence to the shot
     length) and concatenate into one track the exact length of the video — this is what
     keeps audio locked to the burned captions, which use the same `timing` offsets;
  4. burn `captions.ass` and mux the narration, encoding h264_videotoolbox 1080×1920@30 + AAC;
  5. prepend the M7 hook opener (hook_text burned + SFX stinger) when `hook.mp4` exists;
  6. loudness-normalise to −14 LUFS / −1.5 dBTP with ffmpeg-normalize.
Also writes `caption.txt` (description + hashtags + AI-label note). The music bed (M6) is
mixed under the narration in step 3b; intermediates are kept under `_assemble/` for debugging.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from src.config import Settings, load_series_bible, load_settings
from src.pipeline import framing, images, logging_setup, timing
from src.schemas import Episode, SeriesBible

AUDIO_RATE = 48_000
AUDIO_LAYOUT = "stereo"

# Intensity → music-bed loudness. The per-scene bed gain is `gain_under_voice` scaled by a
# multiplier that ramps with scene intensity (calm setup quiet, climax loud); dialogue scenes
# get an extra duck so the spoken line stays crisp. Levels step at scene cuts (masked by the
# visual cut), so no crossfade is needed. Sidechain ducking still applies on top.
_BED_MULT_MIN = 0.8   # multiplier at intensity 0
_BED_MULT_MAX = 1.4    # multiplier at intensity 1
_BED_DIALOGUE_DUCK = 0.6  # extra attenuation while a character is speaking

_OPEN_QUOTE = "\"“'‘"
_CLOSE_QUOTE = "\"”'’"

# Bold display font for the burned-in hook text (the caption font asset is optional/empty).
_HOOK_FONTS = (
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
)


def _is_dialogue(text: str) -> bool:
    """A fully-quoted line (a character speaking) — mirrors tts._voice_for_scene without
    importing the heavy TTS module at assemble time."""
    t = text.strip()
    return len(t) >= 2 and t[0] in _OPEN_QUOTE and t[-1] in _CLOSE_QUOTE


def _music_volume_expr(episode: Episode, durations: list[float], base_gain: float) -> str:
    """Build a piecewise-constant ffmpeg volume expression (function of time `t`) giving the
    music bed a per-scene gain driven by `intensity` (louder on action, quieter under dialogue)."""
    offsets = timing.scene_offsets(durations)
    gains: list[float] = []
    for scene in episode.scenes:
        mult = _BED_MULT_MIN + (_BED_MULT_MAX - _BED_MULT_MIN) * scene.intensity
        if _is_dialogue(scene.narration_text):
            mult *= _BED_DIALOGUE_DUCK
        gains.append(round(base_gain * mult, 4))

    expr = f"{gains[-1]}"  # default (also covers the music tail past the last scene)
    for i in reversed(range(len(gains))):
        start, end = offsets[i], offsets[i] + durations[i]
        expr = f"if(between(t,{start:.3f},{end:.3f}),{gains[i]},{expr})"
    return expr


def _preflight(episode: Episode, episode_dir: Path) -> None:
    """Log every missing input up front so one run surfaces all gaps. Missing scene images
    are fatal (nothing to show); missing narration/captions degrade gracefully (silence / no
    burned text) but are still logged for awareness."""
    log = logging_setup.get_logger()
    images_dir = episode_dir / "images"
    audio_dir = episode_dir / "audio"

    missing_images = [s.id for s in episode.scenes if not (images_dir / f"scene_{s.id:02d}.png").exists()]
    missing_audio = [
        s.id for s in episode.scenes
        if s.narration_text.strip() and not timing.narration_wav(audio_dir, s.id).exists()
    ]
    for sid in missing_audio:
        log.warning("assemble: scene %02d has narration but no wav — that shot will be silent", sid)
    if not (episode_dir / "captions.ass").exists():
        log.warning("assemble: captions.ass missing — rendering without burned captions")
    if missing_images:
        log.error("assemble: missing scene images %s — run the images stage first", missing_images)
        raise RuntimeError(f"missing scene images: {missing_images}")


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd[:6])} …\n{tail}")


def _scene_audio_segment(wav: Path, duration: float, out: Path) -> None:
    """A segment exactly `duration` long: the narration padded with trailing silence,
    or pure silence when a scene has no narration. All segments share params so they concat cleanly."""
    common = ["-c:a", "pcm_s16le", "-ar", str(AUDIO_RATE), "-ac", "2", "-t", f"{duration}", str(out)]
    if wav.exists():
        _run(["ffmpeg", "-y", "-i", str(wav), "-af", "apad", *common])
    else:
        _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout={AUDIO_LAYOUT}:sample_rate={AUDIO_RATE}", *common])


def _mix_music(settings: Settings, narration: Path, music: Path, out: Path, bed_volume: str) -> Path:
    """Mix the music bed under the narration into one track the length of the narration.

    `bed_volume` is a time-varying ffmpeg volume expression (per-scene, intensity-driven).
    The bed is looped to cover the body and trimmed by `amix duration=first`; with `duck`
    on it's sidechain-compressed against the VO so it dips further while someone speaks.
    `amix normalize=0` keeps full levels — the final −14 LUFS pass handles loudness.
    """
    fmt = f"aformat=sample_rates={AUDIO_RATE}:channel_layouts={AUDIO_LAYOUT}"
    bed = f"volume=eval=frame:volume='{bed_volume}'"
    if settings.music.duck:
        graph = (
            f"[0:a]{fmt},asplit=2[narrk][narrmix];"
            f"[1:a]{fmt},{bed}[bed];"
            f"[bed][narrk]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=250[duck];"
            f"[narrmix][duck]amix=inputs=2:duration=first:normalize=0[aout]"
        )
    else:
        graph = (
            f"[0:a]{fmt}[narr];"
            f"[1:a]{fmt},{bed}[bed];"
            f"[narr][bed]amix=inputs=2:duration=first:normalize=0[aout]"
        )
    _run([
        "ffmpeg", "-y",
        "-i", str(narration.resolve()),
        "-stream_loop", "-1", "-i", str(music.resolve()),
        "-filter_complex", graph, "-map", "[aout]",
        "-c:a", "pcm_s16le", "-ar", str(AUDIO_RATE), "-ac", "2",
        str(out.resolve()),
    ])
    return out


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path.resolve())],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def _hook_font() -> str:
    for f in _HOOK_FONTS:
        if Path(f).exists():
            return f
    return _HOOK_FONTS[0]


def _series_title(episode: Episode, bible: SeriesBible | None) -> str:
    if bible and bible.display_name:
        return bible.display_name
    return re.sub(r"[-_]+", " ", episode.series_id).title()


def _episode_number(episode: Episode) -> int | None:
    match = re.search(r"(\d+)$", episode.episode_id)
    return int(match.group(1)) if match else None


def _drawtext(font: str, text_file: Path, fontsize: int, y: str, color: str = "white") -> str:
    return (
        f"drawtext=fontfile='{font}':textfile='{text_file.resolve()}'"
        f":fontcolor={color}:fontsize={fontsize}:borderw={max(2, round(fontsize * 0.1))}:bordercolor=black"
        f":shadowcolor=black@0.6:shadowx=4:shadowy=4:line_spacing=16"
        f":x=(w-text_w)/2:y={y}:fix_bounds=1"
    )


def _build_hook_segment(episode: Episode, bible: SeriesBible | None, hook_clip: Path, work: Path, fps: int, w: int, h: int) -> Path:
    """Burn the hook overlays onto `hook_clip` + add a synthesized riser→impact stinger.

    A minimal "show open": series title at the top, episode number at the bottom, and the hook
    deliberately free of the running karaoke captions so the eye stays on the video. Audio is the
    scripted SFX (`hook_sfx.wav`, AudioLDM2) when the hook stage rendered it — layered with a
    sub-bass thump for low-end punch — otherwise a synthesized riser→impact stinger. Returns a
    `w×h@fps` clip with AAC audio, ready to prepend.
    """
    out = work / "hookfull.mp4"
    dur = _probe_duration(hook_clip) or episode.hook.duration_sec
    font = _hook_font()

    title_tf = work / "hook_title.txt"
    title_tf.write_text(_series_title(episode, bible).upper() + "\n", encoding="utf-8")
    layers = [_drawtext(font, title_tf, round(h * 0.040), "h*0.07")]
    epnum = _episode_number(episode)
    if epnum is not None:
        ep_tf = work / "hook_ep.txt"
        ep_tf.write_text(f"EPISODE {epnum}\n", encoding="utf-8")
        layers.append(_drawtext(font, ep_tf, round(h * 0.034), "h*0.88", color="yellow"))
    drawtext = ",".join(layers)

    fade_st = max(0.0, dur - 0.12)
    sub_lavfi = f"sine=frequency=60:duration={dur:.3f}"  # sub-bass impact, ramps in near the cut
    sub = f"[2:a]volume=eval=frame:volume='0.45*pow(t/{dur:.3f}\\,4)'[sub]"
    sfx_wav = hook_clip.parent / "hook_sfx.wav"
    if sfx_wav.exists():
        # Scripted SFX (AudioLDM2) as the hook's voice, with the sub-bass for guaranteed low-end punch.
        inputs = ["-i", str(hook_clip.resolve()), "-i", str(sfx_wav.resolve()), "-f", "lavfi", "-i", sub_lavfi]
        audio = (
            f"[1:a]aformat=sample_rates={AUDIO_RATE}:channel_layouts={AUDIO_LAYOUT},"
            f"volume=1.4,afade=t=out:st={fade_st:.3f}:d=0.12[sfx];"
            f"{sub};"
            f"[sfx][sub]amix=inputs=2:normalize=0,"
            f"aformat=sample_rates={AUDIO_RATE}:channel_layouts={AUDIO_LAYOUT}[a]"
        )
    else:
        # Synthesized stinger fallback: a filtered pink-noise whoosh that swells + the sub-bass.
        inputs = [
            "-i", str(hook_clip.resolve()),
            "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.7:duration={dur:.3f}",
            "-f", "lavfi", "-i", sub_lavfi,
        ]
        audio = (
            f"[1:a]highpass=f=180,lowpass=f=6000,volume=eval=frame:volume='0.12+0.7*t/{dur:.3f}'[whoosh];"
            f"{sub.replace('0.45', '0.55')};"
            f"[whoosh][sub]amix=inputs=2:normalize=0,"
            f"afade=t=out:st={fade_st:.3f}:d=0.12,"
            f"aformat=sample_rates={AUDIO_RATE}:channel_layouts={AUDIO_LAYOUT}[a]"
        )
    graph = f"[0:v]{drawtext}[v];{audio}"
    _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
        "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE), "-ac", "2",
        "-movflags", "+faststart", str(out.resolve()),
    ])
    return out


def _concat_av(parts: list[Path], out: Path, fps: int, w: int, h: int) -> None:
    """Concatenate audio+video clips by re-encoding (robust to per-clip codec/timebase
    differences — the hook and body are encoded separately). Normalizes each input first."""
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p.resolve())]
    n = len(parts)
    prep = "".join(
        f"[{i}:v:0]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"setsar=1,fps={fps},format=yuv420p[v{i}];"
        f"[{i}:a:0]aformat=sample_rates={AUDIO_RATE}:channel_layouts={AUDIO_LAYOUT},aresample=async=1[a{i}];"
        for i in range(n)
    )
    streams = "".join(f"[v{i}][a{i}]" for i in range(n))
    graph = f"{prep}{streams}concat=n={n}:v=1:a=1[v][a]"
    _run([
        "ffmpeg", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE), "-ac", "2",
        "-movflags", "+faststart", str(out.resolve()),
    ])


def _concat(segments: list[Path], list_file: Path, out: Path, copy: bool = True) -> None:
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in segments))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]
    cmd += (["-c", "copy"] if copy else [])
    cmd += [str(out)]
    _run(cmd)


def _normalize(settings: Settings, src: Path, dst: Path) -> bool:
    """Two-pass EBU R128 to the configured LUFS/true-peak. Returns True on success."""
    cmd = [
        sys.executable, "-m", "ffmpeg_normalize", str(src), "-o", str(dst), "-f",
        "-t", str(settings.audio.target_lufs), "-tp", str(settings.audio.true_peak),
        "-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE),  # EBU defaults to 192 kHz otherwise
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-10:])
        logging_setup.get_logger().warning("assemble: loudness normalization failed, using un-normalized audio:\n%s", tail)
        return False
    return True


def _write_caption_txt(episode: Episode, out: Path) -> None:
    cap = episode.caption
    hashtags = " ".join(cap.hashtags)
    parts = [cap.description.strip(), "", hashtags]
    if cap.ai_label:
        parts += ["", "AI-generated label: ON"]
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")


def assemble(settings: Settings, episode: Episode, episode_dir: Path, bible: SeriesBible | None = None) -> Path:
    """Render `final.mp4` + `caption.txt` in `episode_dir`; returns the mp4 path.

    `bible` is optional — when provided, the hook opener uses its `display_name` for the
    series title (otherwise the title is derived from the episode's `series_id`)."""
    log = logging_setup.get_logger()
    _preflight(episode, episode_dir)

    images_dir = episode_dir / "images"
    audio_dir = episode_dir / "audio"
    work = episode_dir / "_assemble"
    work.mkdir(parents=True, exist_ok=True)

    fps, w, h = settings.video.fps, settings.video.width, settings.video.height
    durations = timing.shot_durations(episode, audio_dir)
    framings = framing.compute_framing(settings, episode, episode_dir)

    # 1. Ken Burns clip per scene (video only) + 3. per-scene audio segment.
    clips: list[Path] = []
    segments: list[Path] = []
    for scene, dur in zip(episode.scenes, durations):
        img = images_dir / f"scene_{scene.id:02d}.png"
        clip = work / f"clip_{scene.id:02d}.mp4"
        fr = framings.get(scene.id)
        start = tuple(fr["start"]) if fr else None
        end = tuple(fr["end"]) if fr else None
        descr = f"focus {end}" if fr else f"scripted {scene.motion.move}"
        log.info("assemble: ken burns scene %02d (%s, %.2fs)", scene.id, descr, dur)
        images.ken_burns(img, scene.motion.move, dur, clip, fps=fps, width=w, height=h, frame_start=start, frame_end=end)
        clips.append(clip)

        seg = work / f"seg_{scene.id:02d}.wav"
        _scene_audio_segment(timing.narration_wav(audio_dir, scene.id), dur, seg)
        segments.append(seg)

    # 2. Concatenate clips into the silent body; concat the narration segments.
    body = work / "body.mp4"
    _concat(clips, work / "clips.txt", body)
    narration = work / "narration.wav"
    _concat(segments, work / "segs.txt", narration)

    # 3b. Mix the music bed under the narration (ducked); fall back to dry VO if absent.
    music_src = audio_dir / "music.wav"
    audio_track = narration
    if music_src.exists():
        bed_volume = _music_volume_expr(episode, durations, settings.music.gain_under_voice)
        log.info("assemble: mixing music bed (intensity-driven, duck=%s)", settings.music.duck)
        audio_track = _mix_music(settings, narration, music_src, work / "mixed.wav", bed_volume)
    else:
        log.warning("assemble: audio/music.wav missing — rendering with narration only (run the music stage)")

    # 4. Burn captions (run from episode_dir so the .ass path needs no escaping) + mux + encode.
    captions = episode_dir / "captions.ass"
    pre = work / "pre.mp4"
    vf = ["-vf", "subtitles=captions.ass"] if captions.exists() else []
    # Media paths are absolute; only the subtitles filter is resolved against cwd (=episode_dir)
    # so the .ass filename needs no filtergraph escaping.
    _run(
        [
            "ffmpeg", "-y", "-i", str(body.resolve()), "-i", str(audio_track.resolve()),
            *vf,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE),
            "-movflags", "+faststart", "-shortest", str(pre.resolve()),
        ],
        cwd=episode_dir,
    )

    # 4b. Prepend the hook opener (hook_text burned + SFX stinger) when the hook stage ran.
    rendered = pre
    hook_clip = episode_dir / "hook.mp4"
    if hook_clip.exists():
        log.info("assemble: prepending hook %s (+ title/hook_text/episode + stinger)", hook_clip.name)
        hookfull = _build_hook_segment(episode, bible, hook_clip, work, fps, w, h)
        combined = work / "combined.mp4"
        _concat_av([hookfull, pre], combined, fps, w, h)
        rendered = combined
    else:
        log.warning("assemble: hook.mp4 missing — rendering body without an opener (run the hook stage)")

    # 5. Loudness normalize → final.mp4 (fall back to the un-normalized render on failure).
    final = episode_dir / "final.mp4"
    log.info("assemble: normalizing to %s LUFS", settings.audio.target_lufs)
    if not _normalize(settings, rendered, final):
        final.write_bytes(rendered.read_bytes())

    _write_caption_txt(episode, episode_dir / "caption.txt")
    log.info("assemble: wrote %s + caption.txt", final.name)
    return final


def main() -> None:
    """Run the assemble stage standalone (bridges around the not-yet-built M7 hook stage)."""
    parser = argparse.ArgumentParser(description="Assemble final.mp4 for an existing episode.")
    parser.add_argument("--episode", required=True, help="episode id, e.g. sewer-surfers_ep_0001")
    args = parser.parse_args()

    settings = load_settings()
    episode_dir = settings.episodes_dir() / args.episode
    episode = Episode.model_validate_json((episode_dir / "episode.json").read_text())
    logging_setup.setup_episode_logging(episode_dir)
    try:
        bible = load_series_bible(episode.series_id)
    except FileNotFoundError:
        bible = None
    out = assemble(settings, episode, episode_dir, bible)
    print(f"assemble: {out}")


if __name__ == "__main__":
    main()
