"""Standalone ACE-Step generator — runs in the ISOLATED ace-step venv.

`music.py` (in the main pinned venv) shells out to this with the project's
configured interpreter. Keep this file dependency-light: it must import only
`acestep` + the stdlib, never anything from `src/`, so the two environments
stay fully decoupled.

Generates a single instrumental bed (no vocals) of the requested duration and
writes it to --output (48 kHz wav). ACE-Step auto-selects MPS on Apple Silicon
and forces float32 there.
"""

from __future__ import annotations

import argparse

from acestep.pipeline_ace_step import ACEStepPipeline

# ACE-Step reads lyrics; this tag tells it to render a purely instrumental track.
INSTRUMENTAL = "[instrumental]"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate one instrumental music bed with ACE-Step.")
    ap.add_argument("--prompt", required=True, help="comma-separated style/mood tags")
    ap.add_argument("--duration", type=float, required=True, help="length in seconds")
    ap.add_argument("--output", required=True, help="output wav path")
    ap.add_argument("--checkpoint-dir", default=None, help="ACE-Step checkpoint dir (auto-downloads if absent)")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pipeline = ACEStepPipeline(checkpoint_dir=args.checkpoint_dir, dtype="float32")
    pipeline(
        prompt=args.prompt,
        lyrics=INSTRUMENTAL,
        audio_duration=args.duration,
        infer_step=args.steps,
        manual_seeds=[args.seed],
        save_path=args.output,
        batch_size=1,
        format="wav",
    )
    print(f"acestep_gen: wrote {args.output} ({args.duration:.1f}s)")


if __name__ == "__main__":
    main()
