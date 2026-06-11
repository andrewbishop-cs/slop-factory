# slop-factory

AI TikTok character-video pipeline (v0). One-line prompt → finished `final.mp4` + `caption.txt` in `ready_to_post/`. Runs entirely locally on Apple Silicon (M5 Max), except a single Claude API call for the script.

The pipeline is **series-agnostic**: each show is a self-contained bible at `config/series/<series_id>.json`, and `--series <id>` selects it — adding a new series is config, not code (see "Add a new series" below).

See `BUILD.md` for the full implementation plan and `research/` for background.

## Setup

```bash
brew install ffmpeg espeak-ng uv
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env            # then fill in ANTHROPIC_API_KEY
uv run python scripts/prefetch_models.py   # optional one-time model prefetch
```

## Run

```bash
# Generate one episode end-to-end (--series names any config/series/<id>.json)
uv run python -m src.pipeline.orchestrator --series sewer-surfers --prompt "Riptide tries to out-run Circuit's new turbo fins"
# Continue the plot from the last cliffhanger
uv run python -m src.pipeline.orchestrator --series sewer-surfers --continue
# Review UI
uv run streamlit run src/ui/app.py
```

## Layout

- `config/` — `settings.yaml` (global) + `series/<id>.json` (one bible per show)
- `src/pipeline/` — stages 1–8 (script → images → tts → music → captions → assemble → qc)
- `src/ui/app.py` — Streamlit review/approve panel
- `src/upload/tiktok_stub.py` — v0 stub: drops approved videos into `ready_to_post/`
- `episodes/<id>/` — per-episode working dir (gitignored)

## Add a new series

1. Create `config/series/<your-series-id>.json` following the `SeriesBible` schema (`src/schemas.py`): `series_id`, `premise`, `style_anchor`, `characters[]`, plus the optional creative-brief fields (`display_name`, `logline`, `setting`, `episode_format`, `tone`, and an `arc` for a planned multi-episode season) that shape how M1 writes that series' episodes.
2. Drop each character's reference image under `assets/characters/<name>/` and set a Kokoro `voice` id per character.
3. Run with `--series <your-series-id>`. No code changes. (Running many series/accounts as an overnight fleet is M10.)
