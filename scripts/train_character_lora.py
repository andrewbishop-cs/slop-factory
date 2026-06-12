"""Train a per-series character LoRA on FLUX.2-klein-4B (M2 consistency, Tier 2).

This is the production-grade identity lock layered on top of reference conditioning.
One *cast* LoRA per series captures all main characters, each tied to its
`lora_trigger` token, so it handles solo and multi-character scenes with a single
adapter. mflux drives the training (`mflux-train`); we just generate a correct
FLUX.2-klein config and wire the result back into the series bible.

Workflow:
  1. Curate a dataset (the human-in-the-loop step): put ~15-30 consistent images of the
     characters in  assets/characters/<series>/dataset/  as `name01.png` + `name01.txt`,
     where each `.txt` caption leads with that character's lora_trigger, e.g.
        "ssriptide, teal mohawk surfer riding a neon hydro-board down a storm drain"
     Seed it from the references made by establish_characters.py (+ FLUX.2 edit variations).
  2. Train:   uv run python scripts/train_character_lora.py --series sewer-surfers
  3. The script writes the trained LoRA path into the bible and flips `lora.trained`,
     so the next images run loads it automatically (and swaps names → triggers in prompts).

Validate the generated config without a multi-hour run:  add  --dry-run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.config import PROJECT_ROOT, load_series_bible, save_series_bible
from src.schemas import LoraSpec

# FLUX.2-klein-4B transformer: 5 double blocks + 20 single blocks (see model_config overrides).
_KLEIN_DOUBLE_BLOCKS = 5
_KLEIN_SINGLE_BLOCKS = 20
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _lora_targets(rank: int) -> list[dict]:
    double = ["attn.to_q", "attn.to_k", "attn.to_v", "attn.to_out"]
    single = ["attn.to_qkv_mlp_proj", "attn.to_out"]
    targets = [
        {"module_path": f"transformer_blocks.{{block}}.{leaf}", "blocks": {"start": 0, "end": _KLEIN_DOUBLE_BLOCKS}, "rank": rank}
        for leaf in double
    ]
    targets += [
        {"module_path": f"single_transformer_blocks.{{block}}.{leaf}", "blocks": {"start": 0, "end": _KLEIN_SINGLE_BLOCKS}, "rank": rank}
        for leaf in single
    ]
    return targets


def _build_config(epochs: int, rank: int, quantize: int | None, learning_rate: float) -> dict:
    return {
        "model": "flux2-klein-4b",
        "data": "dataset",  # resolved relative to this train.json
        "seed": 42,
        "steps": 4,  # klein is 4-step distilled
        "quantize": quantize,
        "max_resolution": 1024,
        "low_ram": False,
        "training_loop": {"num_epochs": epochs, "batch_size": 1, "timestep_low": 0, "timestep_high": 4},
        "optimizer": {"name": "AdamW", "learning_rate": learning_rate},
        "checkpoint": {"save_frequency": max(10, epochs // 4), "output_path": "training"},
        "lora_layers": {"targets": _lora_targets(rank)},
    }


def _dataset_images(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.is_dir():
        return []
    return sorted(p for p in dataset_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTS)


def _scaffold_dataset(series_id: str, dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    triggers = [c.lora_trigger or c.name for c in load_series_bible(series_id).characters]
    readme = dataset_dir / "README.txt"
    readme.write_text(
        "Character LoRA training set for series '" + series_id + "'.\n\n"
        "Add ~15-30 consistent images here, each as <name>.png + <name>.txt (same stem).\n"
        "Each .txt is a caption that LEADS with the character's trigger token, e.g.:\n"
        + "".join(f"  - {t}, <short description of the shot>\n" for t in triggers)
        + "\nMix solo shots of each character (varied pose/angle/expression) and a few\n"
        "two-character shots (caption with both triggers). Seed from the references made by\n"
        "establish_characters.py, then add FLUX.2 edit variations. Re-run the trainer when ready.\n"
    )
    print(f"Scaffolded dataset folder: {dataset_dir}")
    print(f"Triggers for this series: {', '.join(triggers)}")
    print("Add curated images + caption .txt files there, then re-run this script.")


def _newest_lora(output_root: Path) -> Path | None:
    candidates = list(output_root.rglob("*.safetensors")) if output_root.exists() else []
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def train(series_id: str, epochs: int, rank: int, quantize: int | None, learning_rate: float, dry_run: bool) -> int:
    bible = load_series_bible(series_id)
    series_dir = PROJECT_ROOT / "assets" / "characters" / series_id
    dataset_dir = series_dir / "dataset"

    images = _dataset_images(dataset_dir)
    if len(images) < 5:
        print(f"Only {len(images)} training image(s) in {dataset_dir} (need ~15-30).")
        _scaffold_dataset(series_id, dataset_dir)
        return 1

    config = _build_config(epochs, rank, quantize, learning_rate)
    config_path = series_dir / "train.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Wrote training config: {config_path} ({len(images)} images, rank {rank}, {epochs} epochs)")

    cmd = [sys.executable, "-m", "mflux.models.common.cli.train", "--config", str(config_path)]
    if dry_run:
        cmd.append("--dry-run")
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Training failed.", file=sys.stderr)
        return result.returncode
    if dry_run:
        return 0

    lora = _newest_lora(series_dir / "training")
    if lora is None:
        print(f"Training finished but no .safetensors found under {series_dir / 'training'}.", file=sys.stderr)
        return 1
    rel = lora.relative_to(PROJECT_ROOT)
    if bible.lora is None:
        bible.lora = LoraSpec(path=str(rel), scale=1.0, trained=True)
    else:
        bible.lora.path = str(rel)
        bible.lora.trained = True
    save_series_bible(bible)
    print(f"Trained LoRA: {rel}")
    print(f"Updated bible '{series_id}': lora.trained=true. The next images run will load it.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a per-series character LoRA on FLUX.2-klein-4B.")
    parser.add_argument("--series", required=True, help="series id (config/series/<id>.json)")
    parser.add_argument("--epochs", type=int, default=100, help="training epochs over the dataset")
    parser.add_argument("--rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--quantize", type=int, choices=[4, 8], help="quantize the base model during training")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--dry-run", action="store_true", help="validate the config without training")
    args = parser.parse_args()
    raise SystemExit(train(args.series, args.epochs, args.rank, args.quantize, args.learning_rate, args.dry_run))


if __name__ == "__main__":
    main()
