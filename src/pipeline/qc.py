"""Stage 8 — QC gate (M8).

Pass/fail checks on the rendered episode against the v0 spec (BUILD.md §9/§13):
duration ≥ min, every scene image present, captions non-empty & aligned, loudness
≈ −14 LUFS, resolution/fps/codec correct. Character-consistency scoring is an optional,
non-blocking placeholder (embedding similarity is a later polish item).

`run_qc` returns an itemized report dict with an overall `passed` bool and also writes
`qc_report.json` into the episode dir so the review UI can read it without recomputing.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from src.config import Settings
from src.schemas import Episode

# How far the integrated loudness may sit from the target before QC fails (LUFS).
LUFS_TOLERANCE = 1.5
# Allowed fps drift (videotoolbox can land a hair off the requested rate).
FPS_TOLERANCE = 0.5


def _check(name: str, passed: bool, detail: str, *, blocking: bool = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail, "blocking": blocking}


def _probe_format(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path.resolve())],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def _duration(probe: dict[str, Any]) -> float:
    try:
        return float(probe.get("format", {}).get("duration", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _stream(probe: dict[str, Any], kind: str) -> dict[str, Any]:
    for s in probe.get("streams", []):
        if s.get("codec_type") == kind:
            return s
    return {}


def _fps(video_stream: dict[str, Any]) -> float:
    rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/0"
    try:
        num, den = rate.split("/")
        den_f = float(den)
        return float(num) / den_f if den_f else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def _measure_lufs(path: Path) -> float | None:
    """Integrated loudness via ffmpeg's ebur128 filter (parsed from stderr)."""
    proc = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(path.resolve()), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    matches = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", proc.stderr)
    return float(matches[-1]) if matches else None


def _captions_aligned(ass_path: Path) -> tuple[bool, str]:
    """captions.ass exists, has Dialogue events, and carries word-level karaoke timing (\\k tags)."""
    if not ass_path.exists():
        return False, "captions.ass missing"
    text = ass_path.read_text(encoding="utf-8", errors="ignore")
    dialogue = [ln for ln in text.splitlines() if ln.startswith("Dialogue:")]
    if not dialogue:
        return False, "captions.ass has no Dialogue events"
    karaoke = sum(len(re.findall(r"\\k[fo]?\d+", ln)) for ln in dialogue)
    if karaoke == 0:
        return False, f"{len(dialogue)} caption lines but no word-level \\k timing"
    return True, f"{len(dialogue)} caption lines, {karaoke} timed word groups"


def run_qc(settings: Settings, episode: Episode, episode_dir: Path) -> dict[str, Any]:
    """Return an itemized qc_report dict with an overall `passed` bool; also writes qc_report.json."""
    checks: list[dict[str, Any]] = []
    final = episode_dir / "final.mp4"

    if not final.exists():
        checks.append(_check("final.mp4 present", False, "final.mp4 not found — run assemble first"))
        report = {"episode_id": episode.episode_id, "passed": False, "checks": checks}
        _write_report(episode_dir, report)
        return report

    probe = _probe_format(final)
    vstream = _stream(probe, "video")
    astream = _stream(probe, "audio")

    # 1. Duration ≥ minimum.
    dur = _duration(probe)
    min_dur = settings.video.min_duration_sec
    checks.append(_check("duration", dur >= min_dur, f"{dur:.1f}s (min {min_dur}s)"))

    # 2. Every scene image present.
    images_dir = episode_dir / "images"
    missing = [s.id for s in episode.scenes if not (images_dir / f"scene_{s.id:02d}.png").exists()]
    checks.append(_check(
        "scene images", not missing,
        "all present" if not missing else f"missing scenes {missing}",
    ))

    # 3. Captions present + word-aligned.
    ok, detail = _captions_aligned(episode_dir / "captions.ass")
    checks.append(_check("captions aligned", ok, detail))

    # 4. Resolution.
    w, h = vstream.get("width"), vstream.get("height")
    res_ok = w == settings.video.width and h == settings.video.height
    checks.append(_check("resolution", res_ok, f"{w}x{h} (want {settings.video.width}x{settings.video.height})"))

    # 5. FPS.
    fps = _fps(vstream)
    fps_ok = abs(fps - settings.video.fps) <= FPS_TOLERANCE
    checks.append(_check("fps", fps_ok, f"{fps:.2f} (want {settings.video.fps})"))

    # 6. Codecs (videotoolbox encodes H.264; audio is AAC).
    vcodec = vstream.get("codec_name", "?")
    acodec = astream.get("codec_name", "?")
    checks.append(_check("codecs", vcodec == "h264" and acodec == "aac", f"video={vcodec}, audio={acodec} (want h264/aac)"))

    # 7. Loudness ≈ target LUFS.
    lufs = _measure_lufs(final)
    if lufs is None:
        checks.append(_check("loudness", False, "could not measure integrated loudness"))
    else:
        target = settings.audio.target_lufs
        checks.append(_check(
            "loudness", abs(lufs - target) <= LUFS_TOLERANCE,
            f"{lufs:.1f} LUFS (target {target} ±{LUFS_TOLERANCE})",
        ))

    # 8. Character consistency — optional, non-blocking placeholder (embedding similarity is a later polish item).
    checks.append(_check(
        "character consistency", True,
        "not scored (optional — embedding similarity is a post-v0 polish item)", blocking=False,
    ))

    passed = all(c["passed"] for c in checks if c["blocking"])
    report = {"episode_id": episode.episode_id, "passed": passed, "checks": checks}
    _write_report(episode_dir, report)
    return report


def _write_report(episode_dir: Path, report: dict[str, Any]) -> None:
    (episode_dir / "qc_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
