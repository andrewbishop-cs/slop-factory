# BUILD.md — AI TikTok Character-Video Pipeline (v0, local on M5 Max)

**Purpose of this doc:** the single engineering reference for the whole program — a local AI video factory that first builds an audience with character series across multiple accounts, then layers a TikTok Shop **affiliate** content track onto that audience to monetize it. Architecture, dependencies, project scaffold, config/schemas, per-module specs, API keys, and build order. The v0 factory (M0–M9) is **Phase 0**; the multi-account scale-out (M10) and the affiliate track (MA0–MA7) are **Phases 0→2** — see §0.5. Copy-paste sections of this when prompting the build.

**Companion docs:** `research/15-v0-spec.md` (the format/scope), `research/MASTER.md` (research index). Read those for the "why"; this doc is the "how to build."

> **Tooling split:** this project is **planned in Claude Code** (research + this doc) and **built in Cursor**. This doc is the context bridge — drop it into Cursor as the plan.

---

## How to build this in Cursor (read first)

This file is the implementation plan. Hand it to Cursor and build **one milestone at a time** with a checkpoint after each.

**Current state (read before prompting Cursor):** environment setup is **done** (§3 brew deps incl. `ffmpeg`/`espeak-ng`, the `.venv` with the §4 packages pinned into `requirements.txt`/`pyproject.toml`; MPS verified `True`) and **M0–M2 are complete**: `src/schemas.py`, `src/config.py`, `src/pipeline/orchestrator.py` (resumable), `config/settings.yaml`, the `sewer-surfers` series bible (20-episode season arc), `scripts/m0_check.py` (`ALL PASS`); **M1** `script_gen.py` (Anthropic structured output, per-series creative brief, 4–7s shot pacing, idempotent plot-state); **M2** `images.py` on **FLUX.2-klein-4B** (Apache-2.0) with the full consistency stack — prompt anchoring (`style_anchor` + `world_anchor`), multi-reference character conditioning (FLUX.2 edit path + `scripts/establish_characters.py`), and an opt-in trained cast-LoRA (`scripts/train_character_lora.py`) — plus the `ken_burns()` ffmpeg helper. Stages tts/captions/music/hook/assemble/qc are still `NotImplementedError` stubs. Known gap: `stable-audio-tools` (M6 music) won't install on Python 3.12 — deferred, use the ACE-Step repo route at M6. **Next milestone: M3 (`tts`).** Build M3→M9 in order, one milestone per commit.

**Setup in Cursor:**
1. Add `BUILD.md` to the Cursor chat as context (optionally also `research/15-v0-spec.md` for the "why").
2. **Set up the environment first** (§3 brew + §4 `uv pip install`) — until this runs, `scripts/m0_check.py` fails at `import torch` for environment reasons, not code reasons. Don't misread that as a code bug.
3. Then build milestones **M0 → M9 in order** (Section 10), where M0 = verify the existing scaffold rather than recreate it. Each milestone is self-contained and independently testable — that's deliberate so checkpoints are meaningful.
4. **Checkpoint protocol after every milestone:** run the milestone's **Test**, confirm the **Expected** result, `git commit`, then **stop and wait** for your go-ahead before the next milestone.

**Kickoff prompt to paste into Cursor:**
> "Use `BUILD.md` as the implementation plan for this project. The **M0 scaffold already exists** (`src/`, `config/`, `scripts/`) — do **not** rebuild it from scratch. Instead: (1) set up the environment per §3 (brew: ffmpeg, espeak-ng) and §4 (`uv pip install`); (2) **audit the existing M0 code against §7 (structure), §8 (schemas), and §2/§9 (conventions)** and fix any gaps; (3) run the M0 checkpoint test `uv run python scripts/m0_check.py` and confirm it prints `MPS available: True` and `M0 checkpoint: ALL PASS`; (4) `git commit`, then **stop**. Do not start M1 until I say go."

**Ground rules for the build agent:**
- Follow the project structure (§7), config + schemas (§8), and per-module specs (§9) exactly. Each module reads config via `src/config.py` and validates with `src/schemas.py`.
- Default config (§8) is **mflux / FLUX.2-klein-4B** (Apache-2.0) for images and the commercial-safe stack — don't substitute models unless told to. (klein-4B was chosen over FLUX-schnell because mflux dropped FLUX.1 LoRA *training* and klein adds native multi-reference editing for character consistency.)
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
| Image gen (option A, simplest Mac) | **mflux** (MLX) → **FLUX.2-klein-4B** | `pip install mflux` | klein-**4B** = Apache-2.0 (commercial OK); on-device LoRA-trainable; native multi-reference editing. klein-**9B** & FLUX-**dev/Kontext** = **non-commercial**. (FLUX.1-schnell: inference-only — mflux dropped FLUX.1 training.) |
| Image gen (option B, fullest toolkit) | **ComfyUI** + SDXL/**Pony** | clone ComfyUI repo | SDXL/Pony commercially usable; gives IP-Adapter/ControlNet/LoRA for consistency. |
| Char consistency | **FLUX.2 multi-reference + trained cast-LoRA** | `scripts/establish_characters.py`, `scripts/train_character_lora.py` | klein-4B does both on commercial-safe weights: reference images now, trained LoRA later. |
| Video hook | **LTX-Video** | `diffusers` `LTXPipeline` or ComfyUI | Apache-2.0. Slow on MPS (~5–12 min/clip) — fallback = hook-clip library. |
| TTS | **Kokoro** | `pip install kokoro` (or `kokoro-onnx`) | Apache-2.0 (commercial OK). Chatterbox (MIT) later for cloning. |
| Music | **ACE-Step** (preferred) or **Stable Audio Open** | repo / `stable-audio-tools` | ACE-Step = Apache-2.0. Stable Audio Open = Stability Community License (commercial < $1M rev). **AVOID MusicGen weights — CC-BY-NC (non-commercial)** despite MIT code. |
| Captions (timestamps) | **WhisperX** (forced align) | `pip install whisperx` | Forced alignment needs no HF token (wav2vec2). Don't enable diarization. |
| Caption render + assembly | **ffmpeg** | `brew install ffmpeg` | The workhorse: `zoompan` (Ken Burns), `ass` (captions), `xfade`, `h264_videotoolbox` HW encode. |
| Loudness | **ffmpeg-normalize** | `pip install ffmpeg-normalize` | Target −14 LUFS / −1.5 dBTP. |
| Review UI | **Streamlit** | `pip install streamlit` | localhost dashboard. |
| Schemas/validation | **pydantic v2** | `pip install pydantic` | Validates `episode.json`. |
| Env/secrets | **python-dotenv** | `pip install python-dotenv` | reads `.env`. |

> **Commercial-licensing rule of thumb (matters once monetizing):** for the *monetized* account use commercial-safe weights — **FLUX.2-klein-4B or SDXL/Pony** for images, **ACE-Step / Stable Audio Open** for music, **Kokoro** for TTS. For *prototyping only*, FLUX.2-klein-9B / FLUX-dev/Kontext are fine. Full detail in `research/01` and `research/03`.

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

**Short answer: you do not download models by hand.** There are two mechanisms. The one manual prerequisite is a single HF gate click + `HF_TOKEN` for FLUX.2-klein-4B (see the table below) — everything else needs zero manual steps.

**(a) Lazy auto-download (default behavior).** Each library fetches its weights from Hugging Face on first use and caches them in `~/.cache/huggingface` — `mflux`→FLUX.2-klein, `kokoro`→Kokoro, `whisperx`→its alignment model, diffusers `LTXPipeline.from_pretrained(...)`→LTX, ACE-Step→its checkpoint. The first run of each stage is slow (one-time download); every run after is instant. Nothing for you to do — except FLUX.2-klein-4B, which is gated (one-time "Agree" + `HF_TOKEN` in `.env`, which `src/config.py` auto-loads).

**(b) Eager prefetch (recommended — one command).** Run a small `scripts/prefetch_models.py` once to pull everything up front, so the first real pipeline run isn't waiting on downloads (and so it works offline afterward). Uses `huggingface_hub.snapshot_download`.

**Default-stack model access (mostly automatic; FLUX.2-klein-4B needs a one-time gate click):**

| Model (default) | HF repo | Gated? | Token / manual step? |
|---|---|---|---|
| FLUX.2-klein-4B (images) | `black-forest-labs/FLUX.2-klein-4B` | **Yes** (Apache-2.0 but access-walled) | Click "Agree to access" once on the HF page, set `HF_TOKEN` in `.env` |
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

So: **the only ever-manual action is clicking "Agree to access" once on a gated model's web page + setting `HF_TOKEN`.** You hit this for FLUX.2-klein-4B (the default image model — BFL access-walled it) and for any opt-in upgrade (FLUX-dev/Kontext, Stable Audio Open). Everything else is automatic.

**`scripts/prefetch_models.py` (programmatic prefetch):**
```python
import os
from huggingface_hub import snapshot_download

REPOS = [
    "black-forest-labs/FLUX.2-klein-4B",  # default image model (Apache-2.0; one-time HF gate click)
    "Lightricks/LTX-Video",
    "hexgrad/Kokoro-82M",
    "ACE-Step/ACE-Step-v1-3.5B",
    # Optional upgrades (need HF_TOKEN + a one-time license click):
    # "black-forest-labs/FLUX.1-Kontext-dev",
    # "stabilityai/stable-audio-open-1.0",
]

token = os.environ.get("HF_TOKEN") or None  # passed when present → works for gated + ungated
for repo in REPOS:
    print("↓", repo); snapshot_download(repo_id=repo, token=token)   # → ~/.cache/huggingface
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
│   ├── prefetch_models.py        # one-command programmatic model download (Section 5)
│   ├── establish_characters.py   # lock canonical character references for a series (M2 consistency)
│   └── train_character_lora.py   # train a per-series cast-LoRA on FLUX.2-klein (M2 consistency, Tier 2)
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
image: { backend: mflux, model: flux2-klein-4b, steps: 4, guidance: 1.0, use_references: true, quantize: null, lora_path: null, lora_scale: 1.0 }  # klein-4b distilled (guidance 1.0); use_references = multi-ref consistency; lora_path overrides the series' trained LoRA
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
    "prompt": "cartoony anthropomorphic surfer on a neon hydro-board rockets off a sewer spillway, huge spray, exaggerated wipeout, dynamic camera, clean simple Super Mario-style 3D cartoon, smooth glossy surfaces, oversized head and big eyes, stubby limbs, non-realistic",
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
  "style_anchor": "clean simple 3D cartoon style like the modern Super Mario Bros. Movie / Nintendo games: smooth simplified glossy toy-like surfaces, bold simple shapes, exaggerated NON-realistic proportions (oversized heads, very large eyes, small rounded bodies, stubby limbs), minimal surface texture (no realistic fur strands/pores), bright saturated colors, soft clean cinematic lighting — deliberately non-realistic cartoony anthropomorphic animals, never photorealistic",
  "tone": "high-energy Pixar-style sports rivalry with comedic beats and real stakes",
  "episode_format": "A ~60-75s self-contained beat that also advances the season arc: frame-1 hook, stakes setup, gadgets-vs-nerve contrast where relevant, loopable cliffhanger. NOT every episode is a race — vary purpose per arc.episode_purposes.",
  "arc": {
    "total_episodes": 20,
    "synopsis": "A season-long rivalry; ep 1 opens on a high-stakes race, then rising action through wins, defeats, and new strategies toward the climactic Sewer Crown race.",
    "finale": "Episode 20 is the Sewer Crown race: it reveals the winner and closes on a victory lap.",
    "episode_purposes": ["a spaced-out race/heat", "a new board or strategy", "a defeat/setback", "character or relationship beat", "training run", "rising buildup toward a race"],
    "pacing_notes": "Space races out as anticipated tentpole events; fill between them with strategy and character episodes; plant seeds for the finale and escalate as ep 20 nears."
  },
  "world_anchor": "The neon underground world (storm drains, flood tunnels, graffiti concrete, board-building dens/workshops) — GENERAL, every shot; any board is a water hydro-board, never motorcycles/wheels/rails/roads.",
  "riding_anchor": "Actively surfing: balanced on hydro-boards on rushing neon water, spray flying — injected ONLY into shots flagged on_board (grounded shots get an on-foot/solid-ground anchor instead).",
  "characters": [
    {
      "name": "circuit",
      "appearance_tokens": "a small golden-brown monkey with amber eyes and a long tail, cool-toned beach streetwear (open cyan-and-white windbreaker, cargo board-shorts, neon-yellow slides), snorkel goggles up on his head, yellow #3",
      "board_tokens": "a sensor-studded cyan hydro-board bristling with small fins",
      "personality": "brainy, calculating; wins by out-engineering the course",
      "reference_image": "assets/characters/circuit/ref.png",
      "lora_trigger": "sscircuit",
      "voice": "am_michael"
    },
    {
      "name": "riptide",
      "appearance_tokens": "a lean charcoal-black cat with green eyes and a spiky fur mohawk, bold warm-toned beach streetwear (magenta-and-black rashguard tank, open palm-print bomber, wave-print board-shorts), white #7",
      "board_tokens": "a stripped-down minimalist neon-orange speed hydro-board",
      "personality": "reckless, fearless; rides on pure instinct",
      "reference_image": "assets/characters/riptide/ref.png",
      "lora_trigger": "ssriptide",
      "voice": "am_adam"
    }
  ],
  "lora": { "path": "assets/characters/sewer-surfers/lora.safetensors", "scale": 1.0, "trained": false },
  "plot_state": {
    "active_threads": ["the race for the Sewer Crown is dead even"],
    "last_cliffhanger": null,
    "episode_log": []
  }
}
```
> Consistency fields: `style_anchor` (art style) + `world_anchor` (GENERAL world look, every shot) are injected into every image prompt; **scene variation** — each `Scene` carries a `location` (forces a real, frame-filling environment, killing the reference sheet's blank backdrop) and an `on_board` flag (true only for active riding). Riding shots add `riding_anchor` + each rider's `board_tokens`; grounded shots get an explicit on-foot/solid-ground anchor and **no** board (so dialogue/interior beats aren't forced onto boards/water). Each character's `reference_image` drives FLUX.2 multi-reference conditioning; `lora_trigger` + the series `lora` block wire in the optional trained cast-LoRA. See `images.py` (§9) and the M2 consistency workflow.

---

## 9. Module specs (copy each as a build prompt)

Each module: **Purpose · Input · Output · Key libs · Done-when.** All read config via `src/config.py` and validate with `src/schemas.py`.

**`schemas.py`** — Purpose: pydantic models `SeriesBible`, `Episode`, `Scene`, `Hook`, `Music`, `Caption`. Done-when: `Episode.model_validate_json()` accepts the example above and rejects malformed input.

**`script_gen.py`** — Purpose: one-line prompt (or "continue") + series bible → validated `episode.json`. Input: `series_id`, optional `prompt`. Output: `episodes/<id>/episode.json`. Key libs: `anthropic` (Opus 4.8, structured output via `output_config.format` = `{type: json_schema, schema: Episode.model_json_schema()}` with `output_config.effort` from `settings.llm.effort`; the series bible is the cached system prefix). Notes: the bible's creative brief — `premise`/`setting`/`tone`/`episode_format` + per-character `personality` — is injected so each series writes structurally distinct episodes; scene `image_prompt`s name characters and describe the shot only (appearance_tokens + style_anchor are prepended at render in M2, so don't restate them). Enforce frame-1 hook, ≥62s total (sum scene durations + hook), per-scene `mood`+`intensity`, loopable `cliffhanger_text`, keyword-led `caption.description`; `episode_id`/`series_id` are set from the orchestrator, not the model. **Shot pacing for retention:** each scene is one held image, so the prompt asks for varied shot lengths in `video.min_shot_sec`..`max_shot_sec` (4–7s; quick cuts on punchy dialogue, longer on emotional/establishing beats, 7s hard ceiling) → ~12 short shots for a 72s ep, cutting to the speaker in dialogue rather than lingering; scenes over the max get a non-fatal warning. After generating, update bible `plot_state` (`last_cliffhanger` + `episode_log`). Done-when: produces a schema-valid episode whose durations sum ≥ `min_duration_sec`.

**`images.py`** — Purpose: render one keyframe per scene with character consistency. Input: `episode.json` + bible. Output: `images/scene_NN.png` (1080×1920). Key lib: mflux on **FLUX.2-klein-4B** (Apache-2.0) — a single `Flux2KleinEdit(ModelConfig.from_name("flux2-klein-4b"))` serves every scene (with no references it falls back to txt2img, so one loaded model covers ref and non-ref shots). guidance must be `1.0` (distilled). **Character identity is held by three layers (weakest→strongest):** (1) **prompt anchoring** — detect which bible characters are named in `image_prompt`, prefix their exact `appearance_tokens` (body+outfit only, board moved to `board_tokens`) + the series `style_anchor`, and append the GENERAL `world_anchor` (e.g. "any board is a water hydro-board, never motorcycles" — stops board→motorbike drift). **Scene variation (`_build_prompt`):** the reference sheets put each character on a board against a blank studio backdrop, so the edit path leaks board+water+white-bg; we steer positively against it — always inject the scene `location` + "environment fills the frame, never a plain/studio/empty background", and branch on `scene.on_board`: riding shots add `riding_anchor` + per-rider `board_tokens`, grounded shots get an explicit on-foot/solid-ground anchor with no board/water (so dialogue & workshop beats aren't forced onto the water). (2) **multi-reference conditioning** — pass each present character's `reference_image` as `generate_image(image_paths=[...])` so the model reproduces the *same* character in new compositions (the main lock, no training; create the refs once with `scripts/establish_characters.py`); (3) **trained cast-LoRA** — one per-series LoRA over all characters keyed by per-character `lora_trigger`, trained by `scripts/train_character_lora.py` on klein-4B and loaded via `bible.lora` (or `image.lora_path` override); when active, character names are swapped for their trigger tokens in the prompt. Render at dims rounded up to a multiple of 16 (1080→1088), then center-crop to the exact video size. Per-scene PNGs are skipped if they already exist (intra-stage resume; delete the folder to re-render after a model/prompt change). Include `ken_burns(img_path, move, duration_sec, out, *, fps, width, height) -> clip` helper using ffmpeg `zoompan` (2× pre-scale to cut jitter; comma-free expressions so it's argv-safe). Done-when: N portrait PNGs, visually consistent character across scenes.

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
- **Build:** `images.py` on FLUX.2-klein-4B (prompt anchoring + `world_anchor` + multi-reference conditioning + opt-in cast-LoRA) + `ken_burns()` ffmpeg helper. Consistency tooling: `scripts/establish_characters.py` (lock canonical refs), `scripts/train_character_lora.py` (Tier-2 LoRA, dataset → `mflux-train`).
- **Test:** `uv run python scripts/establish_characters.py --series sewer-surfers` then `uv run python -m src.pipeline.orchestrator --series sewer-surfers --episode <id> --force images --until images` (first run downloads klein-4B, one-time; needs the HF gate + `HF_TOKEN`).
- **Expected:** one 1080×1920 PNG per scene in `images/`; with references locked, the same character renders consistently across scenes (eyeball it).
- **🛑 Checkpoint:** commit `"M2: image gen + ken burns"`. Stop.

> **Consistency workflow (M2):** (1) `establish_characters.py` renders one canonical reference per character → `assets/characters/<name>/ref.png`. (2) The images stage feeds those refs to klein's multi-reference edit path — strong identity, no training. (3) For the production lock, curate ~15-30 captioned shots into `assets/characters/<series>/dataset/` (caption each with the character's `lora_trigger`) and run `train_character_lora.py` → trains one cast-LoRA, writes it back into the bible (`lora.trained=true`), and the next render loads it automatically.

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

**M6 — Music** *(done — ACE-Step in an isolated venv, shelled out to)*
- **Install (first):** ACE-Step is **NOT** installed into the main `.venv` (its torch/transformers pins would fight the mflux/kokoro/whisperx stack). Instead it lives in its own venv:
  - `git clone --depth 1 https://github.com/ace-step/ACE-Step models/acestep/ACE-Step`
  - `uv venv models/acestep/venv --python 3.12 && uv pip install --python models/acestep/venv/bin/python -e models/acestep/ACE-Step`
  - **`uv pip install --python models/acestep/venv/bin/python torchcodec`** — required: torchaudio ≥2.9 routes `torchaudio.save()` through TorchCodec, so the vendored ACE-Step save path fails with `ImportError: TorchCodec is required` without it.
  - First generation lazy-downloads the 3.5B checkpoint (~10GB) to `models/acestep/checkpoints`. ACE-Step auto-selects **MPS** on Apple Silicon and forces float32 there. License: Apache-2.0. **Note:** `stable-audio-tools` (Stable Audio Open) is *not viable on Python 3.12* — legacy pins fail to build. **Don't run music generation concurrently with FLUX image gen — loading both 3.5B+ models at once OOMs.**
- **Build:** `scripts/acestep_gen.py` is a dependency-light standalone generator that runs *inside the isolated venv* (imports only `acestep` + stdlib). `music.py` (main venv) builds an instrumental prompt from `music.global_mood`/`bpm_hint` + the average scene `intensity`, then shells out to `settings.music.python` to render `audio/music.wav` (one bed ≥ body length; idempotent). `assemble.py` mixes it under the narration: a per-scene, intensity-driven `volume` envelope (louder on action peaks, extra duck on dialogue scenes, stepped at scene cuts) + optional sidechain ducking against the VO (`music.duck`), then the existing `ffmpeg-normalize` −14 LUFS pass. `assemble.py` also gained a standalone CLI (`python -m src.pipeline.assemble --episode <id>`) to bridge around the not-yet-built M7 hook stage.
- **Test:** `--force music --until music`, then `python -m src.pipeline.assemble --episode <id>`.
- **Expected:** `final.mp4` has a mood-matched bed under the narration, swelling on high-intensity scenes and dipping under dialogue, integrated ≈ −14 LUFS. *(Verified on `sewer-surfers_ep_0001`.)*
- **🛑 Checkpoint:** commit `"M6: music score"`. Stop.

**M7 — Hook** *(done — keyframe-conditioned LTX i2v, with an image-motion fallback)*
- **Build:** `hook.py` produces `hook.mp4` (silent portrait, ≤ `hook.max_seconds`). Three backends:
  - **`ltx` (default):** render a FLUX **keyframe** from `episode.hook.prompt` via `images.generate_keyframe` (reuses the M2 character + style anchoring, so the opener is *on-model* — LTX text-to-video alone would look like a different show), free FLUX, then animate that keyframe with **LTX-Video image-to-video** (`diffusers` `LTXImageToVideoPipeline`, MPS, bf16). Gen res `hook.gen_width×gen_height` (÷32), `num_frames` snapped to LTX's `8k+1` within the cap, then upscaled+cropped to the video size. First run lazy-downloads `Lightricks/LTX-Video`. On **any** LTX failure (and `allow_library_fallback`) it falls back to the kenburns hook below, so the riskiest dep never hard-fails a run.
    - **Motion depends on the keyframe.** i2v *extends* the keyframe, so a static/standing keyframe yields tame ambient motion (water/hair) — the model can't invent a rail-grind from a crouch. `script_gen` therefore writes `hook.prompt` as a single PEAK-ACTION moment caught mid-motion (mid-air jump, rail grind, hard cutback with spray, near-wipeout) featuring one named character; `hook.py` appends an explosive-motion suffix to the LTX prompt and raises `hook.ltx_guidance` so LTX follows it. If motion is still too tame, escalate the backend (CogVideoX-5B / Wan 2.2 i2v / LTX-13B are all available in `diffusers` with no new deps — character identity is preserved by the keyframe regardless of model).
  - **`kenburns`:** skip LTX entirely — an aggressive push-in (+ slight rise) on the keyframe via `images.ken_burns`. Reliable, fast, no extra model.
  - **`library`** (or `hook.type == "library"`): pick `hook.library_clip` / any clip from `assets/hook_library/`.
  - **OOM safety:** the hook stage frees FLUX + empties the MPS cache (`_free_mps`) **before** LTX loads — FLUX + LTX co-resident is what OOMs. Don't run image gen concurrently with the hook stage. (Verified fine sequentially on a 64GB M5 Max.)
- **SFX (in `hook.py`):** `_generate_sfx` renders the scripted `episode.hook.sfx` (e.g. "metal groan into explosive water roar") to `hook_sfx.wav` with **AudioLDM2** (`diffusers` `AudioLDM2Pipeline`, MPS, 16 kHz text-to-audio; first run lazy-downloads `cvssp/audioldm2`). Idempotent; runs after the video, frees the model. Disabled (`hook.sfx: false`), empty `hook.sfx`, or any failure → assemble's synth stinger.
- **Prepend + audio (in `assemble.py`):** when `hook.mp4` exists, `_build_hook_segment` burns a minimal "show open" — the **series title** (`bible.display_name`) at the top and the **episode number** at the bottom (Impact font, outlined + shadowed), deliberately **caption-free** so the eye stays on the video. Hook audio is the scripted SFX (`hook_sfx.wav`) layered with a sub-bass thump for low-end punch, or — when no SFX was rendered — a **synthesized riser→impact stinger** (filtered pink-noise whoosh + the sub-bass). Then `_concat_av` re-encodes hook+body into one clip before the `ffmpeg-normalize` −14 LUFS pass. Captions stay body-relative because the hook is joined *after* the body is captioned. (`assemble` now takes the optional `bible` for the title; the standalone CLI loads it from `series_id`.)
- **Test:** `--force hook --until hook` (or `rm hook.mp4` first, since the stage is idempotent), then `python -m src.pipeline.assemble --episode <id>`. The kenburns fallback + the full prepend/stinger/concat/normalize chain were verified end-to-end (hook 3.7s + body, AAC 48 kHz stereo, normalized).
- **Expected:** video opens with the ≤4s hook + stinger, then the scored body; total ≥62s. (If LTX is flaky on MPS, the kenburns fallback still produces a valid hook.)
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

### Post-v0 follow-ups (deferred polish — not blockers)

Tracked here so they aren't lost; pick up after Phase 0 core is green.

**Intelligent Ken Burns framing — known limitations.** The M5 framing pass (`src/pipeline/framing.py`, moondream2) picks a per-scene focal box and pushes the Ken Burns move toward it. Verified on `ep_0001`: **8/13 scenes targeted** (scene 1 → Circuit, scene 5 → Circuit's line, scene 6 → Riptide's line); the scene-1 end frame lands its push-in squarely on the detected character. Two honest gaps:
- **(a) No true intra-shot A→B speaker panning.** Panning from one speaker to another mid-shot needs multi-speaker scenes, which is a schema change. Today `script_gen` already splits a dialogue exchange into separate single-speaker shots, so per-shot targeting covers most of the intended effect — full intra-shot panning is a nice-to-have, not required.
- **(b) Unnamed group shots fall back to scripted moves.** Scenes phrased as a group ("both riders", "the tunnels merge") have no single focal target, so framing defers to the scripted `motion.move` rather than guessing. This is intended behavior, not a bug.

**Hook SFX — done (AudioLDM2).** `hook.py::_generate_sfx` now renders `episode.hook.sfx` to `hook_sfx.wav` via AudioLDM2 (`cvssp/audioldm2`, MPS), and `assemble` layers it with a sub-bass thump as the hook audio; the synthesized riser→impact stinger remains the fallback when SFX is disabled/empty/fails. *Possible later polish:* a quick "pick-best of N" on the SFX, or a tiny curated `assets/sfx/` library to skip generation entirely.

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
- **Licensing before monetizing:** switch any prototype-only weights (FLUX-dev/Kontext, klein-9B, MusicGen) to commercial-safe ones (FLUX.2-klein-4B/SDXL, ACE-Step/Stable Audio Open) before the account earns.

---

## 13. Definition of done (v0)

Running the orchestrator on a one-line prompt produces, with no manual steps, a **spec-compliant `final.mp4` (1080×1920, 30fps, ≥62s, −14 LUFS, burned karaoke captions, video hook + scored body + narration)** plus a `caption.txt`, reviewable and approvable in the Streamlit UI, landing in `ready_to_post/`. TikTok upload remains a manual/deferred step.
