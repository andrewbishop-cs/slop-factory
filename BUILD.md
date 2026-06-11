# BUILD.md — AI TikTok Character-Video Pipeline (v0, local on M5 Max)

**Purpose of this doc:** the single engineering reference for the whole program — a local AI video factory that first builds an audience with character series across multiple accounts, then layers a TikTok Shop **affiliate** content track onto that audience to monetize it. Architecture, dependencies, project scaffold, config/schemas, per-module specs, API keys, and build order. The v0 factory (M0–M9) is **Phase 0**; the multi-account scale-out (M10) and the affiliate track (MA0–MA7) are **Phases 0→2** — see §0.5. Copy-paste sections of this when prompting the build.

**Companion docs:** `research/15-v0-spec.md` (the format/scope), `research/MASTER.md` (research index). Read those for the "why"; this doc is the "how to build."

> **Tooling split:** this project is **planned in Claude Code** (research + this doc) and **built in Cursor**. This doc is the context bridge — drop it into Cursor as the plan.

---

## How to build this in Cursor (read first)

This file is the implementation plan. Hand it to Cursor and build **one milestone at a time** with a checkpoint after each.

**Current state (read before prompting Cursor):** environment setup is **done** (§3 brew deps incl. `ffmpeg`/`espeak-ng`, the `.venv` with the §4 packages pinned into `requirements.txt`/`pyproject.toml`; MPS verified `True`) and **M0 is complete and committed** — `src/schemas.py`, `src/config.py`, `src/pipeline/orchestrator.py` (resumable), all 8 stage modules as `NotImplementedError` stubs, `config/settings.yaml`, the `sewer-surfers` series bible, and `scripts/m0_check.py` (passes `ALL PASS`). Known gap: `stable-audio-tools` (M6 music) won't install on Python 3.12 — deferred, use the ACE-Step repo route at M6. **Next milestone: M1 (`script_gen`).** Build M1→M9 in order, one milestone per commit.

**Setup in Cursor:**
1. Add `BUILD.md` to the Cursor chat as context (optionally also `research/15-v0-spec.md` for the "why").
2. **Set up the environment first** (§3 brew + §4 `uv pip install`) — until this runs, `scripts/m0_check.py` fails at `import torch` for environment reasons, not code reasons. Don't misread that as a code bug.
3. Then build milestones **M0 → M9 in order** (Section 10), where M0 = verify the existing scaffold rather than recreate it. Each milestone is self-contained and independently testable — that's deliberate so checkpoints are meaningful.
4. **Checkpoint protocol after every milestone:** run the milestone's **Test**, confirm the **Expected** result, `git commit`, then **stop and wait** for your go-ahead before the next milestone.

**Kickoff prompt to paste into Cursor:**
> "Use `BUILD.md` as the implementation plan for this project. The **M0 scaffold already exists** (`src/`, `config/`, `scripts/`) — do **not** rebuild it from scratch. Instead: (1) set up the environment per §3 (brew: ffmpeg, espeak-ng) and §4 (`uv pip install`); (2) **audit the existing M0 code against §7 (structure), §8 (schemas), and §2/§9 (conventions)** and fix any gaps; (3) run the M0 checkpoint test `uv run python scripts/m0_check.py` and confirm it prints `MPS available: True` and `M0 checkpoint: ALL PASS`; (4) `git commit`, then **stop**. Do not start M1 until I say go."

**Ground rules for the build agent:**
- Follow the project structure (§7), config + schemas (§8), and per-module specs (§9) exactly. Each module reads config via `src/config.py` and validates with `src/schemas.py`.
- Default config (§8) is **mflux / FLUX-schnell** for images and the commercial-safe stack — don't substitute models unless told to.
- **Do NOT build deferred features** (real TikTok upload, scheduling, email) beyond the `tiktok_stub.py` stub.
- One milestone per commit. Don't run ahead — the value is in testing each stage before layering the next.
- Pin working dependency versions into `requirements.txt`/`pyproject.toml` as you go.

---

## 0. Scope (read first)

- **Build:** one-line prompt → **finished `final.mp4` + `caption.txt`** in `ready_to_post/`. Runs entirely on the M5 Max.
- **Defer (stub only):** TikTok account/upload/scheduling/email. The `upload` module just drops the finished file + caption into `ready_to_post/` and prints manual instructions. Build the real uploader later, once the US-region account exists.
- **Recurring cost:** ~$0.08/episode (Opus 4.8 script call). Everything else is local/free.
- **Target machine:** 14" MacBook Pro, M5 Max, 40-core GPU, 64GB unified memory, macOS (Apple Silicon / `arm64`).

---

## 0.5 Program phases (the full arc — read this to see where v0 fits)

The v0 build below (M0–M9) is **Phase 0 core**: one account's worth of video factory. The full program is three phases. Each builds on a working previous one, and **the story pipeline is never broken** — affiliate is one codebase with two modes (`mode: story | affiliate`, default `story`), gated by a master `affiliate.enabled` toggle that defaults `false`.

| Phase | Goal | Exit gate | Milestones |
|---|---|---|---|
| **0. Factory + audience** | Build the local video factory, then run it as a **fleet across multiple accounts/niches** to reach affiliate eligibility | each target account **≥1,000 followers**, US region, account in good standing | M0–M9 (factory) → **M10 (multi-account scale-out)** |
| **1. Affiliate-capable pipeline** | Add an affiliate content track to the same codebase — additive, mode-guarded, non-breaking | a **faceless-UGC affiliate video renders end-to-end and passes QC**; a story prompt is byte-for-byte unchanged | MA0–MA5 |
| **2. Inject products + organic→paid loop** | Source real products, inject into the story world, test organically, scale winners with Spark Ads | **first attributed commission**; a repeatable organic-test→Spark-Ads loop | MA6–MA7 + ops |

**The governing principle (locked, from the affiliate research — `research/affiliate-pivot/synthesis.md`):**

> **Characters = the attention / audience / world engine (top of funnel). Real-product b-roll = the shot that actually converts (bottom of funnel).** The characters frame, narrate, and earn the watch; the product is shown as a real item in real use, not "held" by a cartoon. This is the *faceless product UGC* format and it ships first; the AI-avatar presenter format (MA6) is the net-new, lower-priority piece.

**Why multi-account is structural, not optional:** Phase-2 revenue is gated on **per-account** affiliate eligibility (≥1k followers), so reaching the follower goal across several accounts in parallel is the rate-limiter on the whole money model. One niche/series per account (never cross-post identical videos — TikTok suppresses duplicates). The factory is built to run all of them from one machine overnight.

**Sequencing rule:** M0–M9 first (a working factory). M10 turns it into a fleet. MA0–MA7 add affiliate and realistically **interleave with M2–M9** rather than waiting for a finished v0 — every stage today is still a `NotImplementedError` stub, so affiliate features land alongside the stages they depend on. Each milestone stays independently testable with its own checkpoint.

---

## 1. System architecture

```
one-line prompt ─┐
                 ▼
        ┌──────────────────┐   reads/writes
        │ 1. script_gen     │◄────────────► config/series/<id>.json   (per-series bible + continuity)
        │ (Opus 4.8, cloud) │
        └────────┬──────────┘
                 ▼  episodes/<id>/episode.json   (validated against schema)
   ┌─────────────┼───────────────────────────────────────┐
   ▼             ▼                ▼              ▼          ▼
┌────────┐  ┌─────────┐     ┌─────────┐    ┌─────────┐  ┌─────────┐
│2.images│  │3.hook    │     │4.tts     │    │5.music  │  │ (assets)│
│ FLUX/  │  │ LTX-Video│     │ Kokoro   │    │ACE-Step/│  │ refs,   │
│ SDXL   │  │ or lib   │     │ per scene│    │StableAud│  │ voices, │
│ MPS    │  │ clip     │     │ wavs     │    │ mood bed│  │ fonts   │
└───┬────┘  └────┬─────┘     └────┬─────┘    └────┬────┘  └─────────┘
    │            │                │               │
    ▼            │                ▼               │
┌────────┐       │           ┌─────────┐          │
│ ken     │      │           │6.captions│         │
│ burns   │      │           │ WhisperX │         │
│ (ffmpeg)│      │           │ → .ass   │         │
└───┬────┘       │           └────┬─────┘          │
    └────────────┴────────────────┴────────────────┘
                 ▼
        ┌──────────────────┐
        │ 7. assemble       │  ffmpeg: hook + body + captions + narration + music
        │ (ffmpeg)          │  → 1080×1920 / 30fps / H.264 / AAC / −14 LUFS
        └────────┬──────────┘
                 ▼  episodes/<id>/final.mp4  + caption.txt
        ┌──────────────────┐
        │ 8. qc gate        │  duration≥60s, captions present, loudness, char-consistency
        └────────┬──────────┘
                 ▼
        ┌──────────────────┐
        │ 9. review (UI)    │  Streamlit: preview, per-image re-roll, approve/reject
        └────────┬──────────┘
                 ▼  approve
        ┌──────────────────┐
        │ 10. upload (STUB) │  → copies to ready_to_post/, prints "upload to TikTok Studio"
        └──────────────────┘
```

**State model:** every episode is a self-contained folder `episodes/<episode_id>/` holding `episode.json`, `images/`, `hook.mp4`, `audio/`, `captions.ass`, `final.mp4`, `caption.txt`, and a `state.json` (which stages are done). The orchestrator is **resumable** — re-running skips completed stages unless `--force`.

---

## 2. Tech stack (stage → tool → package → license note)

| Stage | Tool | Install | License / commercial note |
|---|---|---|---|
| Script LLM | **Claude Opus 4.8** | `anthropic` (pip) | Paid API (~$0.08/ep). The only cloud call. |
| Image gen (option A, simplest Mac) | **mflux** (MLX FLUX) | `pip install mflux` | FLUX-**schnell** = Apache-2.0 (commercial OK). FLUX-**dev/Kontext** = **non-commercial** — prototype only. |
| Image gen (option B, fullest toolkit) | **ComfyUI** + SDXL/**Pony** | clone ComfyUI repo | SDXL/Pony commercially usable; gives IP-Adapter/ControlNet/LoRA for consistency. |
| Char consistency | LoRA / IP-Adapter / FLUX-Kontext | (model files) | Kontext = non-commercial (prototype). For monetized: trained LoRA + SDXL/schnell. |
| Video hook | **LTX-Video** | `diffusers` `LTXPipeline` or ComfyUI | Apache-2.0. Slow on MPS (~5–12 min/clip) — fallback = hook-clip library. |
| TTS | **Kokoro** | `pip install kokoro` (or `kokoro-onnx`) | Apache-2.0 (commercial OK). Chatterbox (MIT) later for cloning. |
| Music | **ACE-Step** (preferred) or **Stable Audio Open** | repo / `stable-audio-tools` | ACE-Step = Apache-2.0. Stable Audio Open = Stability Community License (commercial < $1M rev). **AVOID MusicGen weights — CC-BY-NC (non-commercial)** despite MIT code. |
| Captions (timestamps) | **WhisperX** (forced align) | `pip install whisperx` | Forced alignment needs no HF token (wav2vec2). Don't enable diarization. |
| Caption render + assembly | **ffmpeg** | `brew install ffmpeg` | The workhorse: `zoompan` (Ken Burns), `ass` (captions), `xfade`, `h264_videotoolbox` HW encode. |
| Loudness | **ffmpeg-normalize** | `pip install ffmpeg-normalize` | Target −14 LUFS / −1.5 dBTP. |
| Review UI | **Streamlit** | `pip install streamlit` | localhost dashboard. |
| Schemas/validation | **pydantic v2** | `pip install pydantic` | Validates `episode.json`. |
| Env/secrets | **python-dotenv** | `pip install python-dotenv` | reads `.env`. |

> **Commercial-licensing rule of thumb (matters once monetizing):** for the *monetized* account use commercial-safe weights — **FLUX-schnell or SDXL/Pony** for images, **ACE-Step / Stable Audio Open** for music, **Kokoro** for TTS. For *prototyping only*, FLUX-dev/Kontext (best consistency) is fine. Full detail in `research/01` and `research/03`.

---

## 3. Prerequisites (system)

```bash
# 1. Homebrew (if not installed): https://brew.sh
# 2. System packages
brew install ffmpeg          # video/audio assembly (verify: ffmpeg -hwaccels shows videotoolbox)
brew install espeak-ng       # phonemizer backend for Kokoro TTS
brew install git
brew install uv              # fast Python package/venv manager (or use pip+venv)
# 3. Python 3.11 or 3.12 (uv can manage this): uv python install 3.12
```

PyTorch uses Apple's **MPS** backend automatically on `arm64` macOS — no CUDA. Verify after install: `python -c "import torch; print(torch.backends.mps.is_available())"` → `True`.

---

## 4. Installation (Python env + packages)

```bash
cd /Users/andrewbishop/slop-factory
uv venv --python 3.12          # creates .venv
source .venv/bin/activate

# Core
uv pip install anthropic pydantic python-dotenv streamlit pyyaml   # pyyaml: src/config.py reads settings.yaml
# Torch (MPS) + media
uv pip install torch torchaudio soundfile librosa numpy pillow
# Image gen (option A)
uv pip install mflux
# TTS + captions
uv pip install kokoro whisperx
# Music — ACE-Step (the settings default). Installed at M6 via repo clone, NOT pip — nothing to install here.
#   git clone https://github.com/ace-step/ACE-Step models/ACE-Step && uv pip install -e models/ACE-Step
# DO NOT `uv pip install stable-audio-tools` — it pins legacy deps (sentencepiece 0.1.99, pywavelets 1.4.1)
# that do not build on Python 3.12 (pkgutil.ImpImporter removed). It's the fallback toolkit for Stable Audio
# Open, not the default. If you ever need that fallback, use a separate Python 3.11 env — don't fight the pins here.
# Video hook (diffusers route)
uv pip install diffusers transformers accelerate
# Assembly/loudness
uv pip install ffmpeg-normalize moviepy
```

Pin everything into `requirements.txt` / `pyproject.toml` once it runs. Heavy deps (torch, whisperx) can take a while.

**ComfyUI (only if using image option B / LTX via ComfyUI):**
```bash
git clone https://github.com/comfyanonymous/ComfyUI models/ComfyUI
cd models/ComfyUI && uv pip install -r requirements.txt
python main.py --listen 127.0.0.1 --port 8188   # headless API; pipeline POSTs workflow JSON
```

---

## 5. Model downloads — programmatic, not manual

**Short answer: you do not download models by hand.** There are two mechanisms, and the default stack needs zero manual steps and no token.

**(a) Lazy auto-download (default behavior).** Each library fetches its weights from Hugging Face on first use and caches them in `~/.cache/huggingface` — `mflux`→FLUX, `kokoro`→Kokoro, `whisperx`→its alignment model, diffusers `LTXPipeline.from_pretrained(...)`→LTX, ACE-Step→its checkpoint. The first run of each stage is slow (one-time download); every run after is instant. Nothing for you to do.

**(b) Eager prefetch (recommended — one command).** Run a small `scripts/prefetch_models.py` once to pull everything up front, so the first real pipeline run isn't waiting on downloads (and so it works offline afterward). Uses `huggingface_hub.snapshot_download`.

**The whole commercial-safe DEFAULT stack is UNGATED → fully automatic, no HF token, no clicks:**

| Model (default) | HF repo | Gated? | Token / manual step? |
|---|---|---|---|
| FLUX.1-schnell (images) | `black-forest-labs/FLUX.1-schnell` | No | None |
| LTX-Video (hook) | `Lightricks/LTX-Video` | No | None |
| Kokoro-82M (TTS) | `hexgrad/Kokoro-82M` | No | None |
| ACE-Step (music) | `ACE-Step/ACE-Step-v1-3.5B` | No | None |
| WhisperX align model | auto (torchaudio/HF) | No | None |

**Optional upgrades that ARE gated (one-time license click + token):**

| Model | HF repo | Why you'd use it | Manual step |
|---|---|---|---|
| FLUX.1-dev / Kontext | `black-forest-labs/FLUX.1-Kontext-dev` | Best character consistency (prototype only — non-commercial) | Click "Agree" on the HF page once, set `HF_TOKEN` |
| Stable Audio Open | `stabilityai/stable-audio-open-1.0` | Alt music model | Same one-time click + `HF_TOKEN` |
| SDXL / Pony V6 (option B) | HF or CivitAI | Fullest consistency toolkit | CivitAI: free API key or direct URL (scriptable); HF SDXL is ungated |

So: **the only ever-manual action is clicking "Agree to access" once on a gated model's web page** — and you only hit that if you opt into FLUX-dev/Kontext or Stable Audio Open. The defaults skip it entirely.

**`scripts/prefetch_models.py` (programmatic prefetch):**
```python
import os
from huggingface_hub import snapshot_download

UNGATED = [
    "black-forest-labs/FLUX.1-schnell",
    "Lightricks/LTX-Video",
    "hexgrad/Kokoro-82M",
    "ACE-Step/ACE-Step-v1-3.5B",
]
GATED = [   # only if you opt in — needs HF_TOKEN + a one-time license click on each repo's HF page
    # "black-forest-labs/FLUX.1-Kontext-dev",
    # "stabilityai/stable-audio-open-1.0",
]

for repo in UNGATED:
    print("↓", repo); snapshot_download(repo_id=repo)            # → ~/.cache/huggingface
for repo in GATED:
    print("↓", repo); snapshot_download(repo_id=repo, token=os.environ["HF_TOKEN"])
print("All models cached.")
```
Run once: `uv run python scripts/prefetch_models.py`. (Add `local_dir="models/<name>"` to a `snapshot_download` call if you want weights under `models/` instead of the HF cache.)

**HF token (only if you opt into a gated model):** free token at huggingface.co/settings/tokens → click "Agree" on the gated repo's page → `huggingface-cli login` or set `HF_TOKEN` in `.env`.

---

## 6. API keys & secrets (`.env`)

Create `.env` in the project root (and `.env.example` committed without values). **Gitignore `.env`.**

```bash
# REQUIRED for v0
ANTHROPIC_API_KEY=sk-ant-...        # Opus 4.8 scripts — console.anthropic.com

# OPTIONAL (only for downloading gated models)
HF_TOKEN=hf_...                     # huggingface.co/settings/tokens

# DEFERRED (upload phase — leave blank for v0)
# TIKTOK_CLIENT_KEY=
# TIKTOK_CLIENT_SECRET=
# SMTP_HOST=        # for "post now" emails, later
# SMTP_USER=
# SMTP_PASS=
# NOTIFY_EMAIL=
```

**v0 needs only `ANTHROPIC_API_KEY`** (plus a free `HF_TOKEN` if you use a gated model). No TikTok keys, no SMTP — those are deferred.

---

## 7. Project structure (scaffold)

```
slop-factory/
├── BUILD.md                      # this doc
├── README.md
├── pyproject.toml / requirements.txt
├── .env / .env.example
├── .gitignore                    # .env, .venv/, models/, episodes/, ready_to_post/
├── config/
│   ├── settings.yaml             # paths, model choices, resolution, target duration, caption style
│   └── series/
│       └── sewer-surfers.json       # a series bible (one JSON per show; add more to add series)
├── assets/
│   ├── characters/<char>/        # reference image(s) + voice sample wav
│   ├── hook_library/             # reusable hook clips (slap/fall/trip…)
│   └── fonts/                    # caption font (e.g. a bold TTF)
├── models/                       # weights (+ optional ComfyUI/) — gitignored
├── episodes/                     # per-episode working dirs — gitignored
│   └── sewer-surfers_ep_0007/   # folders are <series_id>_ep_NNNN (numbered per series)
│       ├── episode.json
│       ├── state.json
│       ├── images/ scene_01.png …
│       ├── hook.mp4
│       ├── audio/ scene_01.wav … music.wav mix.wav
│       ├── captions.ass
│       ├── final.mp4
│       └── caption.txt
├── ready_to_post/                # approved final.mp4 + caption.txt awaiting manual upload
├── scripts/
│   └── prefetch_models.py        # one-command programmatic model download (Section 5)
└── src/
    ├── config.py                 # loads settings.yaml + .env
    ├── schemas.py                # pydantic: SeriesBible, Episode, Scene, Hook, Caption
    ├── pipeline/
    │   ├── orchestrator.py       # runs stages 1–9 for an episode; resumable
    │   ├── script_gen.py         # stage 1
    │   ├── images.py             # stage 2 (+ ken_burns helper)
    │   ├── hook.py               # stage 3 (LTX or library pick)
    │   ├── tts.py                # stage 4
    │   ├── music.py              # stage 5
    │   ├── captions.py           # stage 6
    │   ├── assemble.py           # stage 7 (ffmpeg)
    │   └── qc.py                 # stage 8 gate
    ├── upload/
    │   └── tiktok_stub.py        # stage 10 STUB → copies to ready_to_post/, prints instructions
    └── ui/
        └── app.py                # Streamlit review panel
```

---

## 8. Config & schemas

### `config/settings.yaml` (key fields)
```yaml
paths: { episodes: episodes, ready_to_post: ready_to_post, models: models }
video: { width: 1080, height: 1920, fps: 30, target_duration_sec: 72, min_duration_sec: 62, min_shot_sec: 4, max_shot_sec: 7 }  # per-shot pacing: vary 4-7s for retention
image: { backend: mflux, model: flux-schnell, steps: 4 }    # or backend: comfyui
hook:  { backend: ltx, max_seconds: 4, allow_library_fallback: true }
tts:   { backend: kokoro }
music: { backend: ace-step, gain_under_voice: 0.18 }
captions: { font: assets/fonts/Bold.ttf, words_per_group: 4, position: lower_third, active_color: yellow }
audio: { target_lufs: -14, true_peak: -1.5 }
llm:   { model: claude-opus-4-8, effort: medium }
```

### `episode.json` schema (pydantic `Episode`) — concrete example
```json
{
  "episode_id": "sewer-surfers_ep_0007",
  "series_id": "sewer-surfers",
  "title": "The Spillway Showdown",
  "hook_text": "He hit the spillway at full speed.",
  "hook": {
    "type": "video",
    "prompt": "surfer on a neon hydro-board rockets off a sewer spillway, huge spray, exaggerated wipeout, dynamic camera, bold anime ink-outline style",
    "library_clip": null,
    "duration_sec": 3.5,
    "sfx": "rushing water then a comedic splash"
  },
  "characters_present": ["circuit", "riptide"],
  "scenes": [
    {
      "id": 1,
      "image_prompt": "circuit crouched low on his glowing hydro-board at the mouth of a dark flood tunnel, checking telemetry, water rushing toward him",
      "motion": { "type": "ken_burns", "move": "push_in", "duration_sec": 6 },
      "narration_text": "Circuit had run the numbers a thousand times. Tonight, the math would finally beat the madman.",
      "top_text": null,
      "mood": "tense-calm",
      "intensity": 0.3,
      "duration_sec": 6
    }
  ],
  "cliffhanger_text": "Who takes the next heat? The crown's still up for grabs.",
  "music": { "global_mood": "high-energy underground race tension", "bpm_hint": 128 },
  "caption": {
    "description": "Gadgets vs. guts in the sewer race for the crown 🌊 #aianimation #cartoon #brainrot",
    "hashtags": ["#aianimation", "#cartoon", "#sewersurfers"],
    "ai_label": true
  },
  "target_duration_sec": 72
}
```

### `series_bible.json` schema (per-series creative brief + continuity)

**One JSON per series, at `config/series/<series_id>.json`.** The pipeline is series-agnostic — `--series <id>` loads the matching bible and every stage runs off it — so **adding a new series is config, not code** (running many series as an overnight fleet is M10). The required fields (`series_id`, `premise`, `style_anchor`, `characters`) are joined by an optional **creative brief** (`display_name`, `logline`, `setting`, `episode_format`, `tone`, `arc`) that is what makes two series produce structurally different episodes from the same `Episode` schema; `episode_format` and `arc` are fed into the M1 script prompt. The optional **`arc`** (a `SeasonArc`: `total_episodes`, `synopsis`, `finale`, `episode_purposes[]`, `pacing_notes`) turns a series into a planned multi-episode story — M1 computes the current episode's position (`len(plot_state.episode_log)+1`) and uses the arc to vary each episode's purpose (so not every episode is a race) and to deliver the finale on the last episode. All creative-brief fields are optional/defaulted so older bibles still validate.

```json
{
  "series_id": "sewer-surfers",
  "display_name": "Sewer Surfers",
  "logline": "Two rival riders build custom hydro-boards and battle across a season for the Sewer Crown.",
  "premise": "Underground surfers design their own hydro-boards to ride the storm drains; two rivals trade wins and defeats across a season-long duel building toward the Sewer Crown race.",
  "setting": "A neon-lit underground world of storm drains and flood tunnels beneath a rain-soaked city.",
  "style_anchor": "stylized 2D anime aesthetic, bold clean ink outlines, cel-shaded figures, expressive hand-drawn animation, dynamic speed lines, vibrant neon palette over painterly backgrounds",
  "tone": "high-energy sports-anime rivalry with comedic beats and real stakes",
  "episode_format": "A ~60-75s self-contained beat that also advances the season arc: frame-1 hook, stakes setup, gadgets-vs-nerve contrast where relevant, loopable cliffhanger. NOT every episode is a race — vary purpose per arc.episode_purposes.",
  "arc": {
    "total_episodes": 20,
    "synopsis": "A season-long rivalry; ep 1 opens on a high-stakes race, then rising action through wins, defeats, and new strategies toward the climactic Sewer Crown race.",
    "finale": "Episode 20 is the Sewer Crown race: it reveals the winner and closes on a victory lap.",
    "episode_purposes": ["a spaced-out race/heat", "a new board or strategy", "a defeat/setback", "character or relationship beat", "training run", "rising buildup toward a race"],
    "pacing_notes": "Space races out as anticipated tentpole events; fill between them with strategy and character episodes; plant seeds for the finale and escalate as ep 20 nears."
  },
  "characters": [
    {
      "name": "circuit",
      "appearance_tokens": "a wiry inventor in a gadget-studded wetsuit with LED strips and round goggles, board bristling with sensors",
      "personality": "brainy, calculating; wins by out-engineering the course",
      "reference_image": "assets/characters/circuit/ref.png",
      "voice": "am_michael"
    },
    {
      "name": "riptide",
      "appearance_tokens": "a broad-shouldered daredevil in a scarred neon wetsuit with a shark-fin mohawk and a minimalist speed board",
      "personality": "reckless, fearless; rides on pure instinct",
      "reference_image": "assets/characters/riptide/ref.png",
      "voice": "am_adam"
    }
  ],
  "plot_state": {
    "active_threads": ["the race for the Sewer Crown is dead even"],
    "last_cliffhanger": null,
    "episode_log": []
  }
}
```

---

## 9. Module specs (copy each as a build prompt)

Each module: **Purpose · Input · Output · Key libs · Done-when.** All read config via `src/config.py` and validate with `src/schemas.py`.

**`schemas.py`** — Purpose: pydantic models `SeriesBible`, `Episode`, `Scene`, `Hook`, `Music`, `Caption`. Done-when: `Episode.model_validate_json()` accepts the example above and rejects malformed input.

**`script_gen.py`** — Purpose: one-line prompt (or "continue") + series bible → validated `episode.json`. Input: `series_id`, optional `prompt`. Output: `episodes/<id>/episode.json`. Key libs: `anthropic` (Opus 4.8, structured output via `output_config.format` = `{type: json_schema, schema: Episode.model_json_schema()}` with `output_config.effort` from `settings.llm.effort`; the series bible is the cached system prefix). Notes: the bible's creative brief — `premise`/`setting`/`tone`/`episode_format` + per-character `personality` — is injected so each series writes structurally distinct episodes; scene `image_prompt`s name characters and describe the shot only (appearance_tokens + style_anchor are prepended at render in M2, so don't restate them). Enforce frame-1 hook, ≥62s total (sum scene durations + hook), per-scene `mood`+`intensity`, loopable `cliffhanger_text`, keyword-led `caption.description`; `episode_id`/`series_id` are set from the orchestrator, not the model. **Shot pacing for retention:** each scene is one held image, so the prompt asks for varied shot lengths in `video.min_shot_sec`..`max_shot_sec` (4–7s; quick cuts on punchy dialogue, longer on emotional/establishing beats, 7s hard ceiling) → ~12 short shots for a 72s ep, cutting to the speaker in dialogue rather than lingering; scenes over the max get a non-fatal warning. After generating, update bible `plot_state` (`last_cliffhanger` + `episode_log`). Done-when: produces a schema-valid episode whose durations sum ≥ `min_duration_sec`.

**`images.py`** — Purpose: render one keyframe per scene with character consistency. Input: `episode.json` + bible. Output: `images/scene_NN.png` (1080×1920). Key libs: mflux (FLUX-schnell) **or** ComfyUI API. Notes: prepend each scene's `image_prompt` with the character `appearance_tokens` + `style_anchor`; for consistency use a trained character LoRA (commercial) or FLUX-Kontext reference (prototype). Include `ken_burns(img, move, duration) -> clip` helper using ffmpeg `zoompan`. Done-when: N portrait PNGs, visually consistent character across scenes.

**`hook.py`** — Purpose: produce the 3–4s hook clip. Input: `episode.hook`. Output: `hook.mp4` (portrait, ≤4s). Key libs: diffusers `LTXPipeline` (MPS) or ComfyUI; fallback to a clip from `assets/hook_library/` when `type:"library"` or LTX fails. Notes: cap seconds; expect slowness (~5–12 min); stylized/cartoon prompts; pick-best loop optional. Done-when: a portrait ≤4s clip exists (generated or library).

**`tts.py`** — Purpose: narration audio per scene. Input: scenes' `narration_text` + character voice. Output: `audio/scene_NN.wav`. Key libs: Kokoro (locked voice per character). Done-when: one wav per narrated scene, correct voice.

**`music.py`** — Purpose: mood-matched score. Input: scene `mood`/`intensity` array + `music.global_mood`. Output: `audio/music.wav` spanning total duration. Key libs: ACE-Step or Stable Audio Open. Notes: v0 = one track with an arc from the mood sequence (or per-section gen + crossfade). Done-when: a music bed ≥ video length.

**`captions.py`** — Purpose: word-level karaoke captions. Input: narration wavs + their text. Output: `captions.ass`. Key libs: WhisperX **forced alignment** (text known → word timestamps) → write ASS with `\kf` karaoke tags; style from config (bold, active-word color, lower third); optional top text band per scene `top_text`. Done-when: ASS file whose word timings match the narration.

**`assemble.py`** — Purpose: final render. Input: hook.mp4, scene images (+ken_burns), narration wavs, music.wav, captions.ass. Output: `final.mp4` + `caption.txt`. Key libs: ffmpeg (concat hook+body via `xfade`; overlay `ass`; mix narration + music at `gain_under_voice`; `ffmpeg-normalize` to −14 LUFS; encode `h264_videotoolbox` + AAC, 1080×1920@30). Write `caption.txt` = description + hashtags + "AI-generated label: ON". Done-when: spec-compliant MP4 ≥62s that plays with synced captions + audio.

**`qc.py`** — Purpose: pass/fail gate. Checks: duration ≥ min; all scene images present; captions.ass non-empty & aligned; loudness ≈ −14 LUFS; resolution/fps/codec correct; (optional) character-consistency score (embedding similarity vs reference). Output: `qc_report` (dict) shown in UI. Done-when: returns pass + itemized report, fails loudly on any miss.

**`orchestrator.py`** — Purpose: run stages 1–8 for an episode, resumable. Input: `--series`, `--prompt`/`--continue`, `--force`. Behavior: create `episodes/<id>/`, run each stage, update `state.json`, skip done stages. Done-when: `uv run python -m src.pipeline.orchestrator --series sewer-surfers --prompt "Riptide tries to out-run Circuit's new turbo fins"` yields `final.mp4` + passing QC.

**`ui/app.py` (Streamlit)** — Purpose: review/approve. Shows: episode script (editable), image gallery with **🔄 re-roll per image**, the `final.mp4` player, the QC report, the auto-caption. Buttons: **Re-roll image**, **Re-render**, **Approve → ready_to_post**, **Reject (note)**. On approve → calls `upload/tiktok_stub.py`. Done-when: you can generate → review → approve a video end-to-end from the browser.

**`upload/tiktok_stub.py` (STUB — deferred)** — Purpose: stand-in for real upload. Behavior: copy `final.mp4` + `caption.txt` into `ready_to_post/`, print: *"Ready. Manually upload via TikTok Studio (desktop) when your US account is live — set AI-label ON, paste caption.txt."* Done-when: approved videos land in `ready_to_post/`. (Real uploader/scheduler/email = later phase.)

---

## 10. Build plan — milestones & checkpoints

Build in order. After each milestone: run **Test**, confirm **Expected**, then **🛑 Checkpoint** = `git commit` and stop for confirmation. Don't proceed on a failing test.

> **Sequencing note:** M5 gets you a *watchable* video (images + narration + captions) **before** the slow/fragile hook (M7) and music (M6). Don't build the hook first.

---

**M0 — Skeleton**
- **Build:** project structure (§7), `config.py`, `schemas.py` (§8 models), `config/settings.yaml`, a starter bible `config/series/sewer-surfers.json`, `.env.example`, `.gitignore`, `scripts/prefetch_models.py`, `pyproject.toml`/`requirements.txt`. Empty stage modules with signatures.
- **Test:** `python -c "import torch; print(torch.backends.mps.is_available())"` and validate the §8 example episode against `schemas.Episode`.
- **Expected:** MPS prints `True`; the example `episode.json` validates; the directory tree matches §7.
- **🛑 Checkpoint:** `git commit -m "M0: skeleton + schemas"`. Stop.

**M1 — Script** *(needs `ANTHROPIC_API_KEY`)*
- **Build:** `script_gen.py` — Opus 4.8, structured output against the `Episode` schema, reads the bible (cached), updates `plot_state`.
- **Test:** `uv run python -m src.pipeline.orchestrator --series sewer-surfers --prompt "Riptide tries to out-run Circuit's new turbo fins" --until script`
- **Expected:** `episodes/<id>/episode.json` exists, schema-valid, frame-1 hook + per-scene `mood`/`intensity` + loopable `cliffhanger_text` + keyword-led caption, and hook + scene durations sum ≥ 62s.
- **🛑 Checkpoint:** commit `"M1: script gen"`. Stop.

**M2 — Images**
- **Build:** `images.py` (mflux/FLUX-schnell) + `ken_burns()` ffmpeg helper.
- **Test:** run the images stage on the M1 episode.
- **Expected:** one 1080×1920 PNG per scene in `images/`; the character is recognizably consistent across scenes (eyeball it).
- **🛑 Checkpoint:** commit `"M2: image gen + ken burns"`. Stop.

**M3 — TTS**
- **Build:** `tts.py` (Kokoro, locked voice per character).
- **Test:** run the tts stage.
- **Expected:** `audio/scene_NN.wav` per narrated scene; plays cleanly; consistent voice.
- **🛑 Checkpoint:** commit `"M3: tts"`. Stop.

**M4 — Captions**
- **Build:** `captions.py` (WhisperX forced-align → ASS karaoke).
- **Test:** run the captions stage.
- **Expected:** `captions.ass` exists; word timings line up with a sample narration wav.
- **🛑 Checkpoint:** commit `"M4: captions"`. Stop.

**M5 — Assemble (no hook/music yet) — KEY watchable checkpoint**
- **Build:** `assemble.py` — images+ken_burns + narration + burned captions → `final.mp4` (+ `caption.txt`). Skip hook/music for now.
- **Test:** run the assemble stage, then open `episodes/<id>/final.mp4`.
- **Expected:** a **watchable** 1080×1920@30 H.264/AAC video, ≥62s, captions synced to narration. **Watch the whole thing.** This is the iterate-here moment.
- **🛑 Checkpoint:** commit `"M5: watchable body video"`. Stop.

**M6 — Music**
- **Install (first):** clone + editable-install ACE-Step (`git clone https://github.com/ace-step/ACE-Step models/ACE-Step && uv pip install -e models/ACE-Step`); first run lazy-downloads `ACE-Step/ACE-Step-v1-3.5B`. **Note:** `stable-audio-tools` (the Stable Audio Open path) is *not viable on this Python 3.12 env* — its legacy pins fail to build (confirmed during M0 setup). ACE-Step is the only music backend; if it proves painful, the fallback is a separate 3.11 env, not a pip swap here.
- **Build:** `music.py` (ACE-Step) keyed to scene `mood`/`intensity`; mix under narration at `gain_under_voice`; `ffmpeg-normalize` to −14 LUFS.
- **Test:** re-run assemble with music.
- **Expected:** `final.mp4` now has a mood-matched bed under the narration, properly leveled.
- **🛑 Checkpoint:** commit `"M6: music score"`. Stop.

**M7 — Hook** *(riskiest dep — library first)*
- **Build:** `hook.py` — **start with library-clip selection** from `assets/hook_library/`; then add LTX-Video generation behind `allow_library_fallback`. Add the SFX stinger. Prepend hook to `final.mp4`.
- **Test:** run the full pipeline; open `final.mp4`.
- **Expected:** video opens with the ≤4s hook + stinger, then the scored body; total ≥62s. (If LTX is flaky on MPS, library fallback still produces a valid hook.)
- **🛑 Checkpoint:** commit `"M7: hook + stinger"`. Stop.

**M8 — QC gate + Review UI**
- **Build:** `qc.py` (duration/captions/loudness/format/consistency checks) + `ui/app.py` (Streamlit: script, image gallery with per-image re-roll, video player, QC report, approve/reject).
- **Test:** `uv run streamlit run src/ui/app.py` → generate, re-roll one image, approve.
- **Expected:** end-to-end generate→review→approve works in the browser; QC report shows pass/fail per check.
- **🛑 Checkpoint:** commit `"M8: qc + review ui"`. Stop.

**M9 — Output (v0 complete)**
- **Build:** `upload/tiktok_stub.py` — on approve, copy `final.mp4` + `caption.txt` to `ready_to_post/` and print manual-upload instructions.
- **Test:** approve a video in the UI.
- **Expected:** the approved file + caption land in `ready_to_post/`; stub prints the TikTok-Studio reminder. **v0 done.**
- **🛑 Checkpoint:** commit `"M9: ready_to_post output — v0 complete"`. Stop. **Phase 0 core done.**

---

### Phase 0 scale-out — run the factory as a fleet

**M10 — Multi-account fleet**
Goal: run the factory across **N accounts/niches** from one machine to reach follower goals in parallel (Phase-2 revenue is gated on per-account eligibility, so this is the rate-limiter).
- **Build:**
  - **Account registry** `config/accounts.yaml`: list of `{ account_id, handle, series_id, region: us, cadence_per_day, ready_dir }`. One niche/series per account (distinct content — never cross-post identical videos). Add a pydantic `AccountsConfig` in `config.py` (additive, optional).
  - **Per-account output routing:** `ready_to_post/<account_id>/` instead of a single dir. `upload/tiktok_stub.py` routes the finished file by the episode's account. Episode ids are already series-namespaced (`<series_id>_ep_NNNN`, numbered per series) so they stay globally unique across accounts; add the owning `account_id` to `state.json`.
  - **Fleet runner** `scripts/run_fleet.py` (or `orchestrator --account <id>` / `--all`): loop the registry, generate each account's day of episodes under `caffeinate -i`. Reuses the resumable per-episode `state.json` so a crash mid-batch resumes cleanly.
  - **More series bibles:** one `config/series/<niche>.json` per account (the pipeline is already series-decoupled — this is config, not code).
- **Account ops (manual — the unautomatable node, see `research/14-monetization-eligibility-canadian-in-us.md`):** each account needs its own **US-region setup** (US eSIM/SIM, US App Store, US wifi, no VPN), warm-up at 1–3 posts/day, staggered footprint. Track per-account standing + follower count in `accounts.yaml`.
- **Test:** run the fleet for ≥2 series → each `ready_to_post/<account_id>/` gets its day's videos, no cross-account collisions, per-episode resume still works, story episodes unchanged.
- **🛑 Checkpoint:** commit `"M10: multi-account fleet"`. Stop.

---

### Phase 1 — Affiliate-capable pipeline (additive, mode-guarded)

> Full rationale + the REUSE/MODIFY/ADD table live in `research/affiliate-pivot/02-architecture-changes.md`. Guiding rule: **never break the story pipeline** — every affiliate field is optional/default-valued and every branch is mode-guarded (`mode == "affiliate"`), so existing story episodes validate and render byte-for-byte unchanged.

**MA0 — Schemas + config (no behavior change yet)**
- **Build:** in `schemas.py` add `Product` (`product_id`, `name`, `affiliate_link`, `aup_usd`, `commission_rate`, `brand`, `category`, `demo_notes`, `image_refs: list[str]`, `key_features: list[str]`, `disclosure_required: bool = True`), `CTA` (`text`, `appears_after_scene_id`, `affiliate_link`), `ProductSlot` (`product_id`, `presenter_character`, `integration_note`). Add **optional, default-valued** fields: `Scene.scene_type: Literal["story","product_demo","product_broll","cta"] = "story"`, `Scene.product_id: str|None = None`; `Caption.affiliate_disclosure`, `Caption.showcase_product_id`, `Caption.cta_text` (all `|None=None`); `Episode.mode: Literal["story","affiliate"] = "story"`, `Episode.product: Product|None`, `Episode.cta: CTA|None`; `SeriesBible.product_slots: list[ProductSlot] = []`. In `config.py` add `AffiliateConfig` + `affiliate` field on `Settings`; add the `affiliate:` block to `settings.yaml` (`enabled: false`, `kalodata_export_path`, `product_assets: assets/products`, `min_aup_usd: 80`, `max_aup_usd: 250`, `min_commission_rate: 0.30`, `formats: [faceless_ugc, avatar_presenter]`, `default_format: faceless_ugc`, `disclosure_tag: "#ad"`). Add dirs `assets/products/`, `assets/affiliate/`.
- **Test:** existing `sewer-surfers.json` and the §8 example episode still validate; a hand-written `mode:"affiliate"` episode with a `product` also validates; old `settings.yaml` still loads.
- **🛑 Checkpoint:** commit `"MA0: affiliate schemas + config"`. Stop.

**MA1 — Sourcing reader (NOT a scraper — risk node #1)**
- **Build:** `src/pipeline/sourcing.py:select_product(settings, bible, episode_dir) -> Product`. Reads a **manually exported** Kalodata file (or the official API export) from `affiliate.kalodata_export_path`, applies the composite score `commission_rate × aup × gmv_growth × (1/saturation) × trend`, drops anything failing the AUP/commission gates, writes `product.json` + a ranked shortlist. Runs **before** `script` (separate `--source` command; keep the main `STAGES`/`state.json` loop untouched). **Never scrape Kalodata's UI** — its ToS §4.1.8 bans automated collection; this stage only ingests an export/official-API pull (see `research/affiliate-pivot/03-data-sourcing-layer.md`).
- **Test:** feed a sample export → top product matches a hand-computed score; sub-threshold products are dropped.
- **🛑 Checkpoint:** commit `"MA1: sourcing reader + composite score"`. Stop.

**MA2 — Affiliate script branch**
- **Build:** branch `script_gen.generate_script` on `mode`. For affiliate: read `product.json`, inject product + presenter character (from `product_slots`) + the reverse-engineered winning angle into the Opus prompt, emit an `Episode` with `mode:"affiliate"`, `product_demo`/`product_broll`/`cta` scenes, and populated `caption.affiliate_disclosure`/`showcase_product_id`. Same Opus 4.8 structured-output + same `Episode` schema + bible caching — only the system prompt + a product block change.
- **Test:** an affiliate prompt yields a schema-valid affiliate episode; a story prompt is byte-for-byte unchanged from M1.
- **🛑 Checkpoint:** commit `"MA2: affiliate script branch"`. Stop.

**MA3 — Faceless product b-roll (format 1, the high-reuse, ships-first one)**
- **Build:** in `images.py` dispatch on `scene.scene_type`; add a `product_broll(scene, product, ...)` helper that composites the **real product asset** (from `Product.image_refs` / `assets/products/<id>/`) instead of generating a fictional keyframe. Reuse `ken_burns()` verbatim, plus `tts` (presenter's locked Kokoro voice reads the script), `captions`, `music`, `assemble` unchanged.
- **Test:** an affiliate episode renders a watchable faceless-UGC `final.mp4` — real product shown under Ken Burns + presenter-voice voiceover + captions. **This is the first end-to-end affiliate video and proves the reuse thesis.**
- **🛑 Checkpoint:** commit `"MA3: faceless product b-roll"`. Stop. **Phase 1 watchable checkpoint.**

**MA4 — CTA / showcase injection + disclosure (compliance-critical)**
- **Build:** `assemble.py` overlays the CTA near the end and **appends the disclosure line to `caption.txt`**. `qc.py` adds affiliate checks. **Mandatory dual disclosure** (`research/affiliate-pivot/04-affiliate-mechanics-compliance.md`): the pipeline already forces the **AI label** ON; affiliate adds a **second mandatory "disclose commercial content" toggle** — missing it silently kills For-You reach. QC must fail an affiliate episode lacking either disclosure or a non-empty `affiliate_link`.
- **Test:** QC fails an affiliate episode missing disclosure/affiliate_link; passes a complete one; the AI label + #ad/commercial-content reminders are present in the output.
- **🛑 Checkpoint:** commit `"MA4: cta + dual disclosure + qc"`. Stop.

**MA5 — Affiliate-link / showcase handoff**
- **Build:** extend `upload/tiktok_stub.py:publish` to emit the affiliate link + `showcase_product_id` + a branded-content reminder into `ready_to_post/<account_id>/` as a sidecar `affiliate.txt`, and print: *"Attach TikTok Shop product link X; set the AI label AND the commercial-content/#ad toggle."* Links live on the post's product showcase, **not burned into pixels**.
- **Test:** approving an affiliate episode lands the video + an `affiliate.txt` with the link and instructions in the right account folder.
- **🛑 Checkpoint:** commit `"MA5: affiliate link handoff"`. Stop. **Phase 1 complete — affiliate video ships end-to-end.**

---

### Phase 2 — Inject products + organic→paid loop

**MA6 — AI-avatar presenter (format 2, the net-new, build-last one)**
- **Build:** new `src/pipeline/avatar.py:render_presenter(...)` producing a talking-head clip of the presenter character lip-synced to the narration wav. Wire `avatar` into `STAGES` + `run_stage` dispatch **mode-guarded** (only runs for `format: avatar_presenter`), slotted between `tts` and `assemble`; `assemble` splices avatar clips when present. This is the largest net-new piece + a new model dependency — built last (mirrors building the fragile hook last). Note: it triggers the synthetic-content disclosure/brand-approval friction the research flags, so faceless UGC remains the default earner.
- **Test:** an `avatar_presenter` affiliate episode renders a lip-synced presenter clip spliced into the final cut; story and faceless-UGC episodes are unaffected.
- **🛑 Checkpoint:** commit `"MA6: avatar presenter"`. Stop.

**MA7 — Variant generation + the organic→paid gate**
- **Build:** `script_gen` emits **N hook/angle variants** per product for organic testing. Define the **organic-test-before-spend gate** in `qc.py`/an analytics step (from `research/affiliate-pivot/05-economics-paid-scaling.md`): promote a creative to Spark Ads only if it clears **≥45–50% completion, ≥500 engagements, ≥1% organic link-CTR, ≥1 organic sale**. Paid spend math: **break-even ROAS ≈ 3.3 gross** (≈4.2 after ~20% returns) vs TikTok's ~2.2 average — so only proven creatives get budget, concentrated on the current winner across a 4–8 product portfolio.
- **Test:** generate ≥3 variants for one product; the gate correctly flags a winner vs a dud against sample metrics.
- **🛑 Checkpoint:** commit `"MA7: variants + organic→paid gate"`. Stop.

**The cheapest de-risking step (do before MA1, once an account hits ~1k):** run **one MANUAL organic affiliate video** — real-product b-roll framed in the character world, with the showcase link — and measure link-CTR + conversion. The single biggest unvalidated assumption is whether character-framed real-product content converts on high-AUP; empirics here beat building the whole sourcing/scoring stack on faith.

---

**Deferred / human-led (do not automate):** real TikTok upload + scheduling + "post now" email (build once a US account is live); **relationship leverage** — negotiating whitelisting, retainers, bumped commissions (Stage 5 of the flywheel, the compounding edge, intentionally manual); Kalodata/official-API data *acquisition* (manual export only — automating it is the ban-risk single point of failure).

---

## 11. Run commands

```bash
source .venv/bin/activate
# Generate one episode end-to-end
uv run python -m src.pipeline.orchestrator --series sewer-surfers --prompt "Riptide tries to out-run Circuit's new turbo fins"
# Continue the plot from the last cliffhanger
uv run python -m src.pipeline.orchestrator --series sewer-surfers --continue
# Force re-run a stage
uv run python -m src.pipeline.orchestrator --series sewer-surfers --episode sewer-surfers_ep_0007 --force images
# Review UI
uv run streamlit run src/ui/app.py
# (If using ComfyUI) start it first in another terminal:
python models/ComfyUI/main.py --listen 127.0.0.1 --port 8188

# --- Phase 0 scale-out: multi-account fleet (M10) ---
# Generate the day's episodes for one account, or the whole fleet overnight
uv run python scripts/run_fleet.py --account sewer-surfers-main
caffeinate -i uv run python scripts/run_fleet.py --all

# --- Phase 1/2: affiliate mode (MA0+) ---
# 1) Source + score products from a MANUAL Kalodata export (never a scraper)
uv run python -m src.pipeline.sourcing --series <affiliate-series> --source
# 2) Generate an affiliate episode from the top-scored product
uv run python -m src.pipeline.orchestrator --series <affiliate-series> --mode affiliate --continue
```

---

## 12. Mac-specific gotchas

- **MPS, not CUDA.** Some ops fall back to CPU; set `PYTORCH_ENABLE_MPS_FALLBACK=1` if a model errors on an unsupported op.
- **Keep it awake for overnight batches:** run under `caffeinate -i`, plugged in (96W).
- **LTX-Video is the slow/fragile step.** If MPS support is flaky, lean on the **hook-clip library** and only generate fresh hooks occasionally.
- **FLUX FP8 isn't supported on MPS** — use mflux (MLX handles quantization) or GGUF in ComfyUI.
- **64GB is plenty** to keep an image model + TTS + WhisperX resident; you won't swap. Run stages sequentially per episode; parallelize across episodes only if RAM allows.
- **Licensing before monetizing:** switch any prototype-only weights (FLUX-dev/Kontext, MusicGen) to commercial-safe ones (FLUX-schnell/SDXL, ACE-Step/Stable Audio Open) before the account earns.

---

## 13. Definition of done (v0)

Running the orchestrator on a one-line prompt produces, with no manual steps, a **spec-compliant `final.mp4` (1080×1920, 30fps, ≥62s, −14 LUFS, burned karaoke captions, video hook + scored body + narration)** plus a `caption.txt`, reviewable and approvable in the Streamlit UI, landing in `ready_to_post/`. TikTok upload remains a manual/deferred step.
