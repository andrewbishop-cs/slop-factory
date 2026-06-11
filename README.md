# video-gen

AI TikTok character-video pipeline (v0). One-line prompt → finished `final.mp4` + `caption.txt` in `ready_to_post/`. Runs entirely locally on Apple Silicon (M5 Max), except a single Claude API call for the script.

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
# Generate one episode end-to-end
uv run python -m src.pipeline.orchestrator --series fridge-detectives --prompt "walnut slips on a banana peel"
# Continue the plot from the last cliffhanger
uv run python -m src.pipeline.orchestrator --series fridge-detectives --continue
# Review UI
uv run streamlit run src/ui/app.py
```

## Layout

- `config/` — `settings.yaml` + per-series bible JSON
- `src/pipeline/` — stages 1–8 (script → images → tts → music → captions → assemble → qc)
- `src/ui/app.py` — Streamlit review/approve panel
- `src/upload/tiktok_stub.py` — v0 stub: drops approved videos into `ready_to_post/`
- `episodes/<id>/` — per-episode working dir (gitignored)
