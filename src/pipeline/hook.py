"""Stage 6 — hook clip (M7, riskiest dep — built late, library first).

Produces the ≤4s portrait `hook.mp4` — the attention-grabbing opener prepended to the
body in assemble. Pipeline:
  1. render a FLUX keyframe from `episode.hook.prompt` (reuses the image stage's character +
     style anchoring, so the opener is on-model), then free FLUX;
  2. animate that keyframe with LTX-Video image-to-video (diffusers, MPS) → a moving clip;
  3. on any LTX failure (when `allow_library_fallback`) fall back to a punchy image-motion
     Ken Burns push-in on the same keyframe — so the riskiest dep never hard-fails the run.
A `library` hook type (or `backend: library`) instead picks a clip from `assets/hook_library/`.
The clip is silent; `hook_text` and the SFX stinger are composited when assemble prepends it.
"""

from __future__ import annotations

import gc
import subprocess
from pathlib import Path

from src.config import PROJECT_ROOT, Settings
from src.pipeline import images, logging_setup
from src.schemas import Episode, SeriesBible

_NEG_PROMPT = (
    "static, no motion, frozen, blurry, low quality, distorted, deformed, "
    "extra limbs, watermark, text, caption, jpeg artifacts"
)
_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd[:6])} …\n{tail}")


def _free_mps() -> None:
    """Release the previous model + MPS cache so FLUX and LTX are never co-resident."""
    gc.collect()
    try:
        import torch

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass


def _library_clip(settings: Settings, episode: Episode) -> Path | None:
    """The named `library_clip`, else any video under assets/hook_library/."""
    lib = PROJECT_ROOT / "assets" / "hook_library"
    if episode.hook.library_clip:
        named = lib / episode.hook.library_clip
        if named.exists():
            return named
    if lib.exists():
        clips = sorted(p for p in lib.iterdir() if p.suffix.lower() in _VIDEO_EXTS)
        if clips:
            return clips[0]
    return None


def _encode_to_spec(src: Path, out: Path, max_seconds: float, fps: int, w: int, h: int) -> None:
    """Scale+crop `src` to a silent portrait `w×h@fps` clip, trimmed to `max_seconds`."""
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}"
    _run([
        "ffmpeg", "-y", "-i", str(src.resolve()), "-t", f"{max_seconds:.3f}",
        "-vf", vf, "-an",
        "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-r", str(fps), "-movflags", "+faststart", str(out.resolve()),
    ])


def _ltx_num_frames(max_seconds: float, frame_rate: int) -> int:
    """Largest LTX-valid frame count (8k+1) whose runtime stays within `max_seconds`."""
    max_n = int(max_seconds * frame_rate)
    n = max_n - ((max_n - 1) % 8)
    return max(9, n)


def _kenburns_hook(keyframe: Path, max_seconds: float, fps: int, w: int, h: int, out: Path) -> None:
    """Image-motion fallback: an aggressive push-in (+ slight rise) on the keyframe."""
    images.ken_burns(
        keyframe, "push_in", max_seconds, out, fps=fps, width=w, height=h,
        frame_start=(0.5, 0.5, 1.0), frame_end=(0.5, 0.46, 1.5),
    )


def _ltx_i2v(settings: Settings, prompt: str, keyframe: Path, max_seconds: float, fps: int, w: int, h: int, out: Path) -> None:
    """Animate the keyframe with LTX-Video image-to-video, then upscale to spec."""
    import torch
    from diffusers import LTXImageToVideoPipeline
    from diffusers.utils import export_to_video, load_image

    cfg = settings.hook
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "mps" else torch.float32
    num_frames = _ltx_num_frames(max_seconds, cfg.frame_rate)

    pipe = LTXImageToVideoPipeline.from_pretrained(cfg.model, torch_dtype=dtype)
    pipe.to(device)
    try:
        image = load_image(str(keyframe.resolve()))
        generator = torch.Generator().manual_seed(cfg.seed)
        result = pipe(
            image=image,
            prompt=f"{prompt}. Cinematic, dynamic camera movement, smooth high-quality motion.",
            negative_prompt=_NEG_PROMPT,
            width=cfg.gen_width,
            height=cfg.gen_height,
            num_frames=num_frames,
            frame_rate=cfg.frame_rate,
            num_inference_steps=cfg.steps,
            generator=generator,
        )
        frames = result.frames[0]
        raw = out.with_name("hook_ltx_raw.mp4")
        export_to_video(frames, str(raw), fps=cfg.frame_rate)
    finally:
        del pipe
        _free_mps()
    _encode_to_spec(raw, out, max_seconds, fps, w, h)


def _generate_sfx(settings: Settings, episode: Episode, episode_dir: Path) -> Path | None:
    """Render `episode.hook.sfx` to `hook_sfx.wav` with AudioLDM2 (text-to-audio, MPS).

    Idempotent. Returns the wav path, or None when SFX is disabled, `hook.sfx` is empty, or
    generation fails — in which case assemble falls back to its synthesized stinger.
    """
    log = logging_setup.get_logger()
    cfg = settings.hook
    if not cfg.sfx or not (episode.hook.sfx and episode.hook.sfx.strip()):
        return None
    out = episode_dir / "hook_sfx.wav"
    if out.exists():
        log.info("hook: sfx exists, skipping")
        return out
    try:
        import soundfile as sf
        import torch
        from diffusers import AudioLDM2Pipeline

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        duration = max(2.0, min(episode.hook.duration_sec, cfg.max_seconds))
        log.info("hook: generating SFX from hook.sfx via %s (%d steps)", cfg.sfx_model, cfg.sfx_steps)
        pipe = AudioLDM2Pipeline.from_pretrained(cfg.sfx_model, torch_dtype=torch.float32)
        pipe.to(device)
        try:
            generator = torch.Generator().manual_seed(cfg.seed)
            audio = pipe(
                prompt=episode.hook.sfx,
                negative_prompt="low quality, music, speech, dialogue, average quality",
                num_inference_steps=cfg.sfx_steps,
                audio_length_in_s=duration,
                guidance_scale=cfg.sfx_guidance,
                num_waveforms_per_prompt=1,
                generator=generator,
            ).audios[0]
        finally:
            del pipe
            _free_mps()
        sf.write(str(out.resolve()), audio, 16_000)  # AudioLDM2 renders at 16 kHz
        log.info("hook: wrote %s (%.2fs SFX)", out.name, duration)
        return out
    except Exception as exc:
        log.warning("hook: SFX generation failed (%s) — assemble will use the synth stinger", str(exc)[:200])
        return None


def generate_hook(settings: Settings, episode: Episode, bible: SeriesBible, episode_dir: Path) -> Path:
    """Produce `hook.mp4` (+ `hook_sfx.wav` when `hook.sfx` is set); returns the mp4 path."""
    log = logging_setup.get_logger()
    out = episode_dir / "hook.mp4"
    if out.exists():
        log.info("hook: video exists, skipping")
    else:
        _produce_hook_video(settings, episode, bible, episode_dir, out)
    _generate_sfx(settings, episode, episode_dir)
    return out


def _produce_hook_video(settings: Settings, episode: Episode, bible: SeriesBible, episode_dir: Path, out: Path) -> Path:
    """Render the silent portrait hook clip to `out` (LTX i2v, with kenburns/library fallbacks)."""
    log = logging_setup.get_logger()
    cfg = settings.hook
    fps, w, h = settings.video.fps, settings.video.width, settings.video.height
    max_seconds = min(episode.hook.duration_sec, cfg.max_seconds)

    # Library path: explicit `type: library` or `backend: library`.
    if episode.hook.type == "library" or cfg.backend == "library":
        clip = _library_clip(settings, episode)
        if clip:
            log.info("hook: using library clip %s", clip.name)
            _encode_to_spec(clip, out, max_seconds, fps, w, h)
            return out
        log.warning("hook: library requested but assets/hook_library has no usable clip — generating instead")

    # Keyframe for i2v (and the Ken Burns fallback). Free FLUX before LTX loads.
    prompt = episode.hook.prompt or episode.hook_text or episode.title
    keyframe = episode_dir / "images" / "hook.png"
    log.info("hook: rendering keyframe %s", keyframe.name)
    images.generate_keyframe(settings, episode, bible, prompt, keyframe, seed_key="hook")
    _free_mps()

    if cfg.backend == "kenburns":
        log.info("hook: image-motion (kenburns) backend, %.2fs", max_seconds)
        _kenburns_hook(keyframe, max_seconds, fps, w, h, out)
        return out

    try:
        log.info("hook: LTX image-to-video (%s, %d steps) — this is slow on MPS", cfg.model, cfg.steps)
        _ltx_i2v(settings, prompt, keyframe, max_seconds, fps, w, h, out)
        log.info("hook: wrote %s (LTX)", out.name)
        return out
    except Exception as exc:
        if not cfg.allow_library_fallback:
            raise
        log.warning("hook: LTX generation failed (%s) — falling back to image-motion hook", str(exc)[:200])
        _free_mps()
        _kenburns_hook(keyframe, max_seconds, fps, w, h, out)
        log.info("hook: wrote %s (kenburns fallback)", out.name)
        return out
