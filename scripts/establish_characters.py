"""Establish canonical character references for a series (M2 consistency, Tier 1).

Generates one clean "character sheet" per character with FLUX.2-klein txt2img and
saves it to that character's `reference_image` path in the series bible. Once these
exist, `images.py` feeds them to FLUX.2's multi-reference edit path so every scene
renders the *same* character. Run this once per series (re-run with --force to redo).

    uv run python scripts/establish_characters.py --series sewer-surfers
    uv run python scripts/establish_characters.py --series sewer-surfers --character riptide --force
"""

from __future__ import annotations

import argparse

from mflux.models.common.config import ModelConfig
from mflux.models.flux2.variants import Flux2Klein

from src.config import PROJECT_ROOT, load_series_bible, load_settings
from src.pipeline.images import _round_up_16, _stable_seed
from src.schemas import Character, SeriesBible

# Portrait, multiple of 16 — a 3:4 full-body frame reads identity (outfit, board) well.
REF_WIDTH, REF_HEIGHT = 832, 1216


def _reference_prompt(character: Character, bible: SeriesBible) -> str:
    """Lead with the art style (diffusion weights early tokens most), then the character."""
    world = f" World: {bible.world_anchor.strip()}" if bible.world_anchor else ""
    return (
        f"{bible.style_anchor}. "
        f"In this exact style, a full-body character reference of {character.name}: {character.appearance_tokens}. "
        f"Neutral confident standing pose, facing camera, full figure in frame, clean flat studio "
        f"background, even lighting, no text.{world}"
    )


def establish(series_id: str, only: str | None, force: bool, seed_override: int | None) -> None:
    settings = load_settings()
    bible = load_series_bible(series_id)
    model: Flux2Klein | None = None

    for character in bible.characters:
        if only and character.name != only:
            continue
        if not character.reference_image:
            print(f"  {character.name}: no reference_image path in bible, skipping")
            continue
        out = PROJECT_ROOT / character.reference_image
        if out.exists() and not force:
            print(f"  {character.name}: reference exists ({out}), skipping (use --force to redo)")
            continue

        if model is None:
            model = Flux2Klein(
                model_config=ModelConfig.from_name(settings.image.model),
                quantize=settings.image.quantize,
            )
        seed = seed_override if seed_override is not None else _stable_seed(series_id, character.name, "reference")
        print(f"  {character.name}: rendering reference (seed {seed}) → {out}")
        result = model.generate_image(
            seed=seed,
            prompt=_reference_prompt(character, bible),
            num_inference_steps=settings.image.steps,
            width=_round_up_16(REF_WIDTH),
            height=_round_up_16(REF_HEIGHT),
            guidance=settings.image.guidance,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        result.image.save(out)

    print("Done. Inspect the references, then run the images stage to use them.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate canonical character references for a series.")
    parser.add_argument("--series", required=True, help="series id (config/series/<id>.json)")
    parser.add_argument("--character", help="only this character (default: all)")
    parser.add_argument("--force", action="store_true", help="regenerate even if a reference already exists")
    parser.add_argument("--seed", type=int, help="override the deterministic per-character seed")
    args = parser.parse_args()
    establish(args.series, only=args.character, force=args.force, seed_override=args.seed)


if __name__ == "__main__":
    main()
