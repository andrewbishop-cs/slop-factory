# BUILD.md — AI TikTok Character-Video Pipeline (v0, local on M5 Max)

**Purpose of this doc:** the single engineering reference for building the v0 system. Architecture, dependencies, project scaffold, config/schemas, per-module specs, API keys, and build order. Copy-paste sections of this when prompting the build.

**Companion docs:** `research/15-v0-spec.md` (the format/scope), `research/MASTER.md` (research index). Read those for the "why"; this doc is the "how to build."

> **Tooling split:** this project is **planned in Claude Code** (research + this doc) and **built in Cursor**. This doc is the context bridge — drop it into Cursor as the plan.

---

## How to build this in Cursor (read first)

This file is the implementation plan. Hand it to Cursor and build **one milestone at a time** with a checkpoint after each.

**Setup in Cursor:**
1. Add `BUILD.md` to the Cursor chat as context (optionally also `research/15-v0-spec.md` for the "why").
2. Build milestones **M0 → M9 in order** (Section 10). Each is self-contained and independently testable — that's deliberate so checkpoints are meaningful.
3. **Checkpoint protocol after every milestone:** run the milestone's **Test**, confirm the **Expected** result, `git commit`, then **stop and wait** for your go-ahead before the next milestone.

**Kickoff prompt to paste into Cursor:**
> "Use `BUILD.md` as the implementation plan for this project. Implement **milestone M0 only** — match the scaffold in §7, the schemas in §8, and the conventions in §2/§9. When M0 is done, run its checkpoint Test, show me the result, `git commit`, and **stop**. Do not start M1 until I say go."

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

## 1. System architecture

```
one-line prompt ─┐
                 ▼
        ┌──────────────────┐   reads/writes
        │ 1. script_gen     │◄────────────► config/series_bible.json   (continuity)
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
cd /Users/andrewbishop/video-gen
uv venv --python 3.12          # creates .venv
source .venv/bin/activate

# Core
uv pip install anthropic pydantic python-dotenv streamlit
# Torch (MPS) + media
uv pip install torch torchaudio soundfile librosa numpy pillow
# Image gen (option A)
uv pip install mflux
# TTS + captions
uv pip install kokoro whisperx
# Music (choose one; ACE-Step from repo, or stable-audio-tools)
uv pip install stable-audio-tools        # OR clone ACE-Step repo
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
video-gen/
├── BUILD.md                      # this doc
├── README.md
├── pyproject.toml / requirements.txt
├── .env / .env.example
├── .gitignore                    # .env, .venv/, models/, episodes/, ready_to_post/
├── config/
│   ├── settings.yaml             # paths, model choices, resolution, target duration, caption style
│   └── series/
│       └── fridge-detectives.json   # the series bible (one per show)
├── assets/
│   ├── characters/<char>/        # reference image(s) + voice sample wav
│   ├── hook_library/             # reusable hook clips (slap/fall/trip…)
│   └── fonts/                    # caption font (e.g. a bold TTF)
├── models/                       # weights (+ optional ComfyUI/) — gitignored
├── episodes/                     # per-episode working dirs — gitignored
│   └── ep_0007/
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
video: { width: 1080, height: 1920, fps: 30, target_duration_sec: 72, min_duration_sec: 62 }
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
  "episode_id": "ep_0007",
  "series_id": "fridge-detectives",
  "title": "The Banana Peel Betrayal",
  "hook_text": "He never saw it coming.",
  "hook": {
    "type": "video",
    "prompt": "cartoon walnut detective in a fedora slips on a banana peel, exaggerated slapstick fall, dynamic camera, 3D Pixar style",
    "library_clip": null,
    "duration_sec": 3.5,
    "sfx": "comedic whoosh then thud"
  },
  "characters_present": ["walnut", "banana"],
  "scenes": [
    {
      "id": 1,
      "image_prompt": "<walnut appearance_tokens> sitting in a dim fridge office, neon light, <style_anchor>",
      "motion": { "type": "ken_burns", "move": "push_in", "duration_sec": 6 },
      "narration_text": "Detective Walnut thought it was an ordinary Tuesday.",
      "top_text": null,
      "mood": "noir-calm",
      "intensity": 0.3,
      "duration_sec": 6
    }
  ],
  "cliffhanger_text": "Who left the peel? Part 8 tomorrow.",
  "music": { "global_mood": "noir comedic tension", "bpm_hint": 90 },
  "caption": {
    "description": "Detective Walnut's worst Tuesday yet 🥜 #aianimation #cartoon #brainrot",
    "hashtags": ["#aianimation", "#cartoon", "#fridgedetectives"],
    "ai_label": true
  },
  "target_duration_sec": 72
}
```

### `series_bible.json` schema (continuity)
```json
{
  "series_id": "fridge-detectives",
  "premise": "A walnut detective and his anxious banana sidekick solve petty crimes in a fridge.",
  "style_anchor": "consistent 3D Pixar-style render, soft cinematic lighting, vibrant",
  "characters": [
    {
      "name": "walnut",
      "appearance_tokens": "a plump cartoon walnut wearing a tiny grey fedora, big expressive eyes",
      "personality": "deadpan, world-weary",
      "reference_image": "assets/characters/walnut/ref.png",
      "voice": "assets/characters/walnut/voice.wav"   // or a Kokoro voice id
    }
  ],
  "plot_state": {
    "active_threads": ["who keeps stealing the cheese"],
    "last_cliffhanger": "Who left the peel?",
    "episode_log": ["ep_0006: cheese goes missing"]
  }
}
```

---

## 9. Module specs (copy each as a build prompt)

Each module: **Purpose · Input · Output · Key libs · Done-when.** All read config via `src/config.py` and validate with `src/schemas.py`.

**`schemas.py`** — Purpose: pydantic models `SeriesBible`, `Episode`, `Scene`, `Hook`, `Music`, `Caption`. Done-when: `Episode.model_validate_json()` accepts the example above and rejects malformed input.

**`script_gen.py`** — Purpose: one-line prompt (or "continue") + series bible → validated `episode.json`. Input: `series_id`, optional `prompt`. Output: `episodes/<id>/episode.json`. Key libs: `anthropic` (Opus 4.8, `effort: medium`, structured output via tool_use/`output_config.format` against the `Episode` JSON schema; cache the bible). Notes: enforce frame-1 hook, ≥62s total (sum scene durations + hook), per-scene `mood`+`intensity`, loopable `cliffhanger_text`, keyword-led `caption.description`. After generating, update bible `plot_state`. Done-when: produces a schema-valid episode whose durations sum ≥ `min_duration_sec`.

**`images.py`** — Purpose: render one keyframe per scene with character consistency. Input: `episode.json` + bible. Output: `images/scene_NN.png` (1080×1920). Key libs: mflux (FLUX-schnell) **or** ComfyUI API. Notes: prepend each scene's `image_prompt` with the character `appearance_tokens` + `style_anchor`; for consistency use a trained character LoRA (commercial) or FLUX-Kontext reference (prototype). Include `ken_burns(img, move, duration) -> clip` helper using ffmpeg `zoompan`. Done-when: N portrait PNGs, visually consistent character across scenes.

**`hook.py`** — Purpose: produce the 3–4s hook clip. Input: `episode.hook`. Output: `hook.mp4` (portrait, ≤4s). Key libs: diffusers `LTXPipeline` (MPS) or ComfyUI; fallback to a clip from `assets/hook_library/` when `type:"library"` or LTX fails. Notes: cap seconds; expect slowness (~5–12 min); stylized/cartoon prompts; pick-best loop optional. Done-when: a portrait ≤4s clip exists (generated or library).

**`tts.py`** — Purpose: narration audio per scene. Input: scenes' `narration_text` + character voice. Output: `audio/scene_NN.wav`. Key libs: Kokoro (locked voice per character). Done-when: one wav per narrated scene, correct voice.

**`music.py`** — Purpose: mood-matched score. Input: scene `mood`/`intensity` array + `music.global_mood`. Output: `audio/music.wav` spanning total duration. Key libs: ACE-Step or Stable Audio Open. Notes: v0 = one track with an arc from the mood sequence (or per-section gen + crossfade). Done-when: a music bed ≥ video length.

**`captions.py`** — Purpose: word-level karaoke captions. Input: narration wavs + their text. Output: `captions.ass`. Key libs: WhisperX **forced alignment** (text known → word timestamps) → write ASS with `\kf` karaoke tags; style from config (bold, active-word color, lower third); optional top text band per scene `top_text`. Done-when: ASS file whose word timings match the narration.

**`assemble.py`** — Purpose: final render. Input: hook.mp4, scene images (+ken_burns), narration wavs, music.wav, captions.ass. Output: `final.mp4` + `caption.txt`. Key libs: ffmpeg (concat hook+body via `xfade`; overlay `ass`; mix narration + music at `gain_under_voice`; `ffmpeg-normalize` to −14 LUFS; encode `h264_videotoolbox` + AAC, 1080×1920@30). Write `caption.txt` = description + hashtags + "AI-generated label: ON". Done-when: spec-compliant MP4 ≥62s that plays with synced captions + audio.

**`qc.py`** — Purpose: pass/fail gate. Checks: duration ≥ min; all scene images present; captions.ass non-empty & aligned; loudness ≈ −14 LUFS; resolution/fps/codec correct; (optional) character-consistency score (embedding similarity vs reference). Output: `qc_report` (dict) shown in UI. Done-when: returns pass + itemized report, fails loudly on any miss.

**`orchestrator.py`** — Purpose: run stages 1–8 for an episode, resumable. Input: `--series`, `--prompt`/`--continue`, `--force`. Behavior: create `episodes/<id>/`, run each stage, update `state.json`, skip done stages. Done-when: `uv run python -m src.pipeline.orchestrator --series fridge-detectives --prompt "walnut slips on a banana peel"` yields `final.mp4` + passing QC.

**`ui/app.py` (Streamlit)** — Purpose: review/approve. Shows: episode script (editable), image gallery with **🔄 re-roll per image**, the `final.mp4` player, the QC report, the auto-caption. Buttons: **Re-roll image**, **Re-render**, **Approve → ready_to_post**, **Reject (note)**. On approve → calls `upload/tiktok_stub.py`. Done-when: you can generate → review → approve a video end-to-end from the browser.

**`upload/tiktok_stub.py` (STUB — deferred)** — Purpose: stand-in for real upload. Behavior: copy `final.mp4` + `caption.txt` into `ready_to_post/`, print: *"Ready. Manually upload via TikTok Studio (desktop) when your US account is live — set AI-label ON, paste caption.txt."* Done-when: approved videos land in `ready_to_post/`. (Real uploader/scheduler/email = later phase.)

---

## 10. Build plan — milestones & checkpoints

Build in order. After each milestone: run **Test**, confirm **Expected**, then **🛑 Checkpoint** = `git commit` and stop for confirmation. Don't proceed on a failing test.

> **Sequencing note:** M5 gets you a *watchable* video (images + narration + captions) **before** the slow/fragile hook (M7) and music (M6). Don't build the hook first.

---

**M0 — Skeleton**
- **Build:** project structure (§7), `config.py`, `schemas.py` (§8 models), `config/settings.yaml`, placeholder bible `config/series/fridge-detectives.json`, `.env.example`, `.gitignore`, `scripts/prefetch_models.py`, `pyproject.toml`/`requirements.txt`. Empty stage modules with signatures.
- **Test:** `python -c "import torch; print(torch.backends.mps.is_available())"` and validate the §8 example episode against `schemas.Episode`.
- **Expected:** MPS prints `True`; the example `episode.json` validates; the directory tree matches §7.
- **🛑 Checkpoint:** `git commit -m "M0: skeleton + schemas"`. Stop.

**M1 — Script** *(needs `ANTHROPIC_API_KEY`)*
- **Build:** `script_gen.py` — Opus 4.8, structured output against the `Episode` schema, reads the bible (cached), updates `plot_state`.
- **Test:** `uv run python -m src.pipeline.orchestrator --series fridge-detectives --prompt "walnut slips on a banana peel" --until script`
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
- **🛑 Checkpoint:** commit `"M9: ready_to_post output — v0 complete"`. Stop.

**Deferred (do not build in v0):** real TikTok upload, scheduling-into-TikTok, email "post now" notifications. Build once the US-region account exists.

---

## 11. Run commands

```bash
source .venv/bin/activate
# Generate one episode end-to-end
uv run python -m src.pipeline.orchestrator --series fridge-detectives --prompt "walnut slips on a banana peel"
# Continue the plot from the last cliffhanger
uv run python -m src.pipeline.orchestrator --series fridge-detectives --continue
# Force re-run a stage
uv run python -m src.pipeline.orchestrator --series fridge-detectives --episode ep_0007 --force images
# Review UI
uv run streamlit run src/ui/app.py
# (If using ComfyUI) start it first in another terminal:
python models/ComfyUI/main.py --listen 127.0.0.1 --port 8188
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
