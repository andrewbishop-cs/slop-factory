# Local AI Generation Models for Episodic Character Video

**Research date:** June 2026  
**Scope:** Locally runnable open models for (a) stylized character image generation and (b) image/text → video, as of 2025–2026. Audio/lip-sync excluded (separate agent).

---

## Table of Contents

1. [Text-to-Image Models](#1-text-to-image-models)
2. [Character Consistency Methods](#2-character-consistency-methods)
3. [Image-to-Video & Text-to-Video Models](#3-image-to-video--text-to-video-models)
4. [Tooling & Orchestration](#4-tooling--orchestration)
5. [VRAM Tier Table](#5-vram-tier-table)
6. [Apple Silicon Notes](#6-apple-silicon-notes)
7. [Recommended Stack](#7-recommended-stack)
8. [Open Issues & Blockers](#8-open-issues--blockers)

---

## 1. Text-to-Image Models

### FLUX.1 [dev] — Black Forest Labs
- **Repo:** https://huggingface.co/black-forest-labs/FLUX.1-dev
- **Parameters:** 12B rectified flow transformer
- **License:** FLUX.1-dev Non-Commercial License. Commercial use requires a paid license from BFL (self-serve portal available as of mid-2025). **NOT freely commercial.**
- **VRAM:** ~24 GB at BF16; FP8 quantized brings it to ~12 GB; community GGUF Q6 runs on 16 GB.
- **Generation time:** RTX 4090 ~12–18s/image at 1024×1024 (BF16). Apple M3 Max ~105s; M4 Max ~85s.
- **Style quality:** Excellent photorealism and stylized outputs. With appropriate LoRA or style prompt it handles cartoon/3D looks well. No native reference-image consistency.
- **Note:** FP8 not supported on Apple MPS. Use GGUF Q6 on macOS.

### FLUX.1 Kontext [dev] — Black Forest Labs *(Key consistency tool)*
- **Repo:** https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev
- **License:** Non-commercial (same BFL portal for commercial). Dev weights open.
- **VRAM:** BF16 needs ~24 GB; FP8 checkpoint ~12 GB; FP4 (Blackwell only) ~7 GB.
- **Generation time:** ~9s/edit at FP4 on RTX 4090 (2.29 it/s); BF16 slower (~25–35s).
- **Why it matters:** Kontext performs *in-context* image generation — you feed a reference character image + text instruction and it places that exact character in a new scene, preserving identity without any fine-tuning. Multi-turn editing keeps consistency over many iterations. This is the single most important tool for character consistency in 2025–2026.
- **ComfyUI support:** Native workflow in official ComfyUI docs.

### FLUX.1 [schnell] — Black Forest Labs
- **Repo:** https://huggingface.co/black-forest-labs/FLUX.1-schnell
- **License:** Apache 2.0 — **fully commercial-friendly.**
- **VRAM:** Same as dev (~12–24 GB depending on quant).
- **Generation time:** RTX 4090 ~2–4s/image. Apple M-series ~30–50s.
- **Use case:** Fast draft generation; lower quality than dev. Good for rapid iteration.

### FLUX.2 [dev] — Black Forest Labs (released Nov 2025)
- **Repo:** https://huggingface.co/black-forest-labs/FLUX.2-dev
- **Parameters:** 32B open-weight model
- **License:** FLUX.2-dev Non-Commercial License. Commercial requires BFL license.
- **VRAM:** ~48 GB+ at BF16 — **not consumer GPU friendly.** Enterprise/multi-GPU only.
- **Note:** The 4B "klein" variant is Apache 2.0 and runs at ~13 GB, but quality is notably lower.

### Stable Diffusion 3.5 Large / Medium — Stability AI
- **Repo:** https://huggingface.co/stabilityai/stable-diffusion-3.5-large (8.1B) and stable-diffusion-3.5-medium (2.5B)
- **License:** Stability AI Community License — **free commercial use up to $1M annual revenue.**
- **VRAM:**
  - Large: ~24 GB at FP16 (can reduce to ~16 GB with BitsAndBytes 4-bit + CPU offload)
  - Medium: ~6 GB at FP16 with T5 encoder offloaded; ~9–10 GB with full encoders
- **Generation time:** Medium on RTX 4090 ~5–10s; on Apple M4 Air 16 GB ~15–25s.
- **Style quality:** Good prompt adherence, improved text rendering. Less fine-tune ecosystem than SDXL. Medium is the recommended local option.

### Stable Diffusion XL (SDXL) — Stability AI
- **Repo:** https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- **License:** CreativeML Open RAIL+M — commercial use allowed (with restrictions on harmful content).
- **VRAM:** 6–8 GB at FP16 with typical settings.
- **Generation time:** RTX 4090 ~3–7s; Apple Silicon ~20–40s.
- **Style quality:** Mature ecosystem, largest LoRA library on CivitAI. Not the sharpest quality in 2026 but extremely versatile with community fine-tunes.
- **For cartoon style:** Use SDXL-based fine-tunes (see below).

### Pony Diffusion V6 XL — PurpleSmartAI (SDXL fine-tune)
- **Available:** CivitAI
- **License:** OpenRAIL (non-commercial default; check CivitAI page for current terms)
- **VRAM:** Same as SDXL (~6–8 GB)
- **Why use it:** Trained on 2.6M+ curated images including anime, cartoon, and anthropomorphic/furry characters. Massive LoRA ecosystem on CivitAI. Uses "score tags" (`score_9`, `score_8_up`) and `source_cartoon`/`source_anime` tags for quality gating. Ideal for stylized fruit/object characters with anthropomorphic looks.
- **Note:** SDXL LoRAs don't transfer to Flux models — separate training needed.

### SD 3.5 Large Turbo
- Distilled version of SD 3.5 Large using Adversarial Diffusion Distillation — 4-step generation, ~6–8x faster than base Large. Same $1M commercial license threshold.

---

## 2. Character Consistency Methods

This is the **critical challenge** for an episodic series. The same fruit character must look identical across clips and episodes. Multiple complementary techniques exist:

### 2a. FLUX.1 Kontext (Recommended — Zero Training)
Kontext is the biggest 2025 breakthrough for character consistency. Feed one reference image + text instruction → get the same character in a new pose/environment. Demonstrated strong identity preservation through many rounds of multi-turn editing without any fine-tuning or LoRA. Best for:
- Generating episode-by-episode images of the same character
- Placing characters in new scenes/backgrounds
- Style variations while preserving identity

**Workflow in ComfyUI:** Load reference image → Kontext node → text instruction → output. Can chain for multiple characters in same scene.

### 2b. IP-Adapter FaceID + ControlNet (Recommended — Zero Training)
For SDXL/Pony/SD 3.5 workflows:
- **IP-Adapter FaceID Plus V2** (`cubiq/ComfyUI_IPAdapter_plus`) injects identity from reference images at generation time — no training needed
- Combine with **ControlNet** (OpenPose or depth) for pose control
- Recommended weights: IP-Adapter FaceID at 0.75, ControlNet at 0.6–0.8
- For cartoon/object characters (not human faces), use `ip_adapter_plus_face_sd15` or SDXL equivalent with the character's defining visual
- "Triple-lock" stack: IP-Adapter (face/identity) + Character LoRA (body/style) + ControlNet (pose)

### 2c. Character LoRA Training (Highest Consistency — Requires Training)
Train a small LoRA that "locks in" your specific character:
- **Dataset:** 30–100 images of the character in varied poses/lighting/backgrounds
- **Tools:** Kohya SS (most features), AI Toolkit/SimpleTuner (simpler), ComfyUI-Realtime-Lora
- **Steps:** 1,500–2,000 typical; up to 3,000 for complex characters
- **Training time:** 1–2h for SDXL (8–12 GB VRAM); 3–5h for Flux (24 GB VRAM)
- **VRAM needed:** 8–12 GB for SDXL/Pony; 24 GB+ for Flux LoRAs
- **File size:** 50–250 MB depending on rank and model
- **Model-specific:** SDXL LoRAs don't work on Flux; each model family needs separate training
- **Best for:** Production pipelines generating 500+ images of the same character

### 2d. InstantID (Human-Face Characters)
- Plug-and-play module using facial recognition embeddings + IdentityNet for spatial control
- Single reference image → consistent face across styles/poses
- Better fidelity than IP-Adapter for faces; slightly less text-editability
- Primarily for humanoid characters; less useful for fruit/object anthropomorphs

### 2e. Stable Video Infinity (SVI 2.0 Pro) — For Video Consistency
- **Repo:** https://github.com/vita-epfl/Stable-Video-Infinity (ICLR 2026 Oral)
- Pairs with Wan 2.2 I2V 14B model
- Uses "Error Recycling Fine Tuning" — feeds imperfect frames back during training so model learns to recover from drift
- Produces infinite-length video by passing motion latents between overlapping 5-second passes
- Preserves character identity, outfit, and environment across the full clip chain
- **Key for this project:** Enables generating 60s+ videos from a single reference image with consistent character throughout

---

## 3. Image-to-Video & Text-to-Video Models

Most models produce 4–6 second clips. Strategy for 60s videos: chain 12–15 overlapping clips using Stable Video Infinity or similar latent-handoff techniques.

### Wan 2.2 — Alibaba/Wan-Video (RECOMMENDED)
- **Repo:** https://github.com/Wan-Video/Wan2.2
- **License:** Apache 2.0 — **fully commercial.**
- **Variants:**
  - 5B: T2V + I2V at 720p on consumer GPUs
  - 14B I2V: High quality image-to-video (most relevant for character animation)
  - 14B T2V: Text-to-video
- **VRAM:**
  - 5B: ~12 GB at 480p; ~16 GB at 720p
  - 14B FP8: ~22–26 GB at 720p (with T5 on CPU: ~13–15 GB GPU VRAM + 24 GB RAM)
  - 14B GGUF Q4: ~6–8 GB GPU VRAM (with T5 on CPU)
- **Clip length:** Up to ~6 seconds (adjustable via frame count)
- **Generation time on RTX 4090:**
  - 5B at 480p: ~4 min/5s clip
  - 14B FP8 at 720p: ~9 min/5s clip (FP8 optimization → ~60–120s at reduced steps)
- **Apple Silicon:** Community fork `Wan2mac` targets MPS; `Wan2GP` has early Mac support. Expect 3–4x slower than RTX 4090.
- **Why top pick:** Apache 2.0 commercial license, best motion quality, native ComfyUI support, compatible with Stable Video Infinity 2.0 for long-form generation, largest community.

### LTX-Video 2.3 / LTX-2 — Lightricks
- **Repo:** https://github.com/Lightricks/LTX-Video ; LTX-2 on HuggingFace
- **License:** Apache 2.0 with $10M annual revenue threshold (free below that). **Commercially viable for this project.**
- **Parameters:** LTX-2.3 is a 22B model with rebuilt VAE and 4x larger text connector; supports native audio generation
- **VRAM:**
  - Min: 12 GB (RTX 3060) at reduced settings
  - Comfortable: 16–24 GB for 720p FP8
  - Full: 32 GB for BF16 1080p
- **Clip length:** Up to 20 seconds at 540p; ~5s at 1080p; ~8–10s at 720p
- **Generation time on RTX 4090:** ~90s per 5s clip at 720p
- **Apple Silicon:** M2/M3 Max with 64 GB unified memory works, ~8x slower than 4090 — borderline usable.
- **Portrait mode:** Native 9:16 support (1080×1920) — ideal for TikTok
- **Notable:** LTX Desktop open-source app available for non-technical users; also has `LTX2-Infinity` workflow for infinite-length generation

### HunyuanVideo 1.5 — Tencent
- **Repo:** https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- **License:** Tencent Hunyuan Community License — custom license. Allows commercial use but **excludes EU/UK/South Korea**; large-scale use (>100M MAU) requires Tencent approval.
- **Parameters:** 8.3B (consumer-friendly distilled version of 13B original)
- **VRAM:**
  - HunyuanVideo 1.5: 14 GB+ for consumer GPUs
  - Original 13B: 32–48 GB at full precision; FP8+tiling can reach ~8 GB
- **Clip length:** ~5–6 seconds
- **Generation time on RTX 4090:** ~5–6 min/5s clip (original); 1.5 faster but not benchmarked widely
- **Apple Silicon:** `HunyuanVideo_MLX` project enables Metal acceleration; FramePack runs with "massive headroom" on M-series but raw video is slow
- **Note:** License territorial restrictions may be a concern depending on publishing jurisdiction

### CogVideoX 1.5 — THUDM (Zhipu AI)
- **Repo:** https://huggingface.co/zai-org/CogVideoX-5b
- **License:** CogVideoX License for 5B (not Apache 2.0); 2B is Apache 2.0. Check current terms — broadly permissive for non-commercial; commercial use of 5B unclear.
- **VRAM:** 5B model: 24–32 GB (8-bit quant reduces to ~16 GB)
- **Clip length:** 10-second near-720p clips from the 5B model
- **Generation time:** Not well benchmarked publicly; similar to HunyuanVideo class
- **Use case:** 10-second clips are useful for longer scenes; decent quality

### Mochi 1 — Genmo
- **Repo:** https://github.com/genmoai/mochi
- **License:** Apache 2.0 — **fully commercial.**
- **Parameters:** 10B AsymmDiT architecture
- **VRAM:** 60 GB official; optimized ComfyUI path brings it to ~20 GB; community reports ~12 GB minimum
- **Clip length:** Up to 5.4 seconds at 30fps, 480p only
- **Generation time:** ~8 min/5s clip on RTX 4090
- **Status:** As of 2026, largely superseded by Wan 2.2 and LTX-2 in quality and efficiency. Apache 2.0 is a plus, but limited to 480p.

### AnimateDiff (SD 1.5 / SDXL based)
- **Repo:** https://github.com/guoyww/AnimateDiff
- **Status:** No longer primary tool for most creators (2025). Superseded by dedicated video models.
- **Use case:** Still relevant for highly stylized, "animated" cartoon looks using SD 1.5/SDXL checkpoints + motion modules. Produces 2–4 second clips.
- **Advantage:** Inherits entire SD/SDXL LoRA ecosystem; very controllable style via base checkpoint choice
- **VRAM:** 8–12 GB depending on base model
- **Clip length:** 16–32 frames (0.5–2s at 16fps; 1–4s at 8fps)

### Stable Video Diffusion (SVD) — Stability AI
- **Status:** Legacy (2023–2024). Superseded by Wan 2.2, LTX-Video. Only 14–25 frames (~2–4s) at 1024×576.
- **Not recommended** for new pipelines.

---

## 4. Tooling & Orchestration

### ComfyUI (STRONGLY RECOMMENDED for automation)
- **Repo:** https://github.com/comfy-org/ComfyUI
- **Why:** Node-based workflow system where every workflow is a JSON file. The server runs headless by default — the UI is just one client. The REST API (`/prompt` endpoint, port 8188) accepts workflow JSON from any HTTP client, making it ideal for scripted batch pipelines.
- **API pattern:**
  ```python
  import json, requests, websocket
  # Submit workflow
  requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow_json})
  # Track via WebSocket /ws for real-time events
  # Retrieve via /history and /view
  ```
- **Key nodes for this project:**
  - `ComfyUI_IPAdapter_plus` (cubiq) — IP-Adapter FaceID
  - `ComfyUI-Wan-Video` — Wan 2.2 native nodes (day-0 support)
  - `ComfyUI-LTXVideo` — LTX-Video support
  - `ComfyUI-VideoHelperSuite` — video I/O, frame extraction
  - `Combine Video Clips v2` (RvTools) — stitching clips
  - `stable-video-infinity` — SVI long-form generation
- **Script examples:** Official repo includes `/script_examples/` for building workflow graphs in Python without UI
- **Speed advantage:** 10–25% faster than A1111 for equivalent operations; handles ControlNet + video chaining in single workflow

### Automatic1111 / Forge Neo
- Still relevant for SD 1.5/SDXL/Pony image generation with a UI
- A1111's API is less flexible for pipeline automation than ComfyUI
- **Forge Neo** is the actively maintained fork of A1111 (2025)
- **Not recommended as primary tool** for this headless pipeline, but useful for iterating on image quality settings manually

### HuggingFace Diffusers (Python library)
- **Use case:** Script-first pipelines without any UI; fine-tune training; research
- All major models (Flux, SD 3.5, Wan, LTX, CogVideoX) have `diffusers` pipelines
- More verbose than ComfyUI but total control; good for custom preprocessing
- Can run entirely headless from Python scripts
- **For LoRA training:** Kohya SS (most mature), AI Toolkit (simpler Flux training), SimpleTuner

### Kohya SS
- **Repo:** https://github.com/bmaltais/kohya_ss
- Training GUI for SD 1.5, SDXL, and Flux LoRAs
- Most flexible, best documented
- Also scriptable via command line for CI/CD LoRA retraining

---

## 5. VRAM Tier Table

### Image Generation Models

| Model | 8 GB | 12 GB | 16 GB | 24 GB (4090) | 32 GB+ | License |
|---|---|---|---|---|---|---|
| Flux.1 schnell | GGUF Q4 only | GGUF Q6 | GGUF Q8 | FP16 native | Full quality | Apache 2.0 ✓ |
| Flux.1 dev | No | Quant only | FP8 | FP8 comfortable | FP16 | Non-commercial |
| Flux.1 Kontext dev | No | FP8 (12 GB) | FP8 | BF16 comfortable | Full | Non-commercial |
| SD 3.5 Medium | ~9–10 GB | Yes | Yes | Yes | Yes | Free <$1M revenue ✓ |
| SD 3.5 Large | No | No | Quantized | Yes | Yes | Free <$1M revenue ✓ |
| SDXL | Yes (6–8 GB) | Yes | Yes | Yes | Yes | OpenRAIL+ ✓ |
| Pony Diffusion V6 XL | Yes (6–8 GB) | Yes | Yes | Yes | Yes | OpenRAIL |
| FLUX.2 dev (32B) | No | No | No | No | ~48 GB+ | Non-commercial |

**Generation time at 1024×1024 on RTX 4090:**
- Flux.1 schnell (FP16): ~2–4s
- Flux.1 dev / Kontext (FP8): ~9–18s
- SD 3.5 Medium: ~5–10s
- SDXL: ~3–7s

### Video Generation Models

| Model | 8 GB | 12 GB | 16 GB | 24 GB (4090) | 32 GB+ | Clip Length | License |
|---|---|---|---|---|---|---|---|
| Wan 2.2 1.3B | GGUF | Yes | Yes | Yes | Yes | ~5s 480p | Apache 2.0 ✓ |
| Wan 2.2 5B | GGUF ~6 GB | Yes | Yes | Yes | Yes | ~5s 720p | Apache 2.0 ✓ |
| Wan 2.2 14B | GGUF ~8 GB | GGUF | FP8 partial | FP8 720p | Full quality | ~5s 720p | Apache 2.0 ✓ |
| LTX-Video 2.3 | No | Min (slow) | FP8 720p | Comfortable | Full 1080p+ | 20s @540p; 5s @1080p | Apache 2.0 ✓ |
| HunyuanVideo 1.5 | No | No | 14 GB+ | Yes | Full | ~5–6s | Custom (no EU/UK) |
| CogVideoX 5B | No | No | 8-bit quant | Yes | Yes | 10s ~720p | CogVideoX license |
| Mochi 1 | No | Community opt. | Community opt. | ~20 GB opt. | 60 GB official | 5.4s 480p | Apache 2.0 ✓ |
| AnimateDiff (SDXL) | Yes | Yes | Yes | Yes | Yes | 2–4s | OpenRAIL+ |

**Video generation time per 5-second clip on RTX 4090:**
- Wan 2.2 5B @ 480p: ~4 min
- Wan 2.2 14B FP8 @ 720p: ~2–9 min (steps dependent)
- LTX-Video 2.3 @ 720p: ~90s (~1.5 min)
- HunyuanVideo 1.5: ~3–5 min (estimated)
- Mochi 1: ~8 min

**LTX-Video 2.3 is the fastest at 720p per clip** (~90s on 4090). Wan 2.2 14B produces better motion quality.

---

## 6. Apple Silicon Notes

The user is on macOS (darwin). Key facts:

- **All Flux models (schnell/dev/Kontext):** Run via PyTorch MPS. Start ComfyUI with `--use-pytorch-cross-attention --force-fp16`. Use **GGUF Q6** quantization — FP8 is NOT supported on MPS. Speed: ~3–5x slower than RTX 4090.
  - M4 Max: ~85s/image for Flux.1 dev; M3 Max: ~105s; M2 Max: ~145s
  - Flux.1 schnell: ~30–50s/image on M-series

- **SD 3.5 Medium:** Works well via Diffusers + MPS. M4 Air 16 GB: ~15–25s at 1024×1024. Offload T5 encoder to CPU after prompt encoding.

- **SDXL / Pony:** Excellent MPS support. ~20–40s/image on M1/M2/M3.

- **Wan 2.2 video:**
  - Official repo doesn't support MPS yet (CUDA-only)
  - `Wan2GP` has early/partial Mac support with `Wan2mac` fork for Apple Silicon
  - Expect 3–4x slower than RTX 4090, so 5s clip = 6–12 min on M-series
  - Viable for testing/prototyping; not recommended for production throughput

- **LTX-Video 2.3:** M2/M3 Max with 64 GB unified memory works, ~12+ min per 5s clip (8x slower than 4090). Borderline for production.

- **HunyuanVideo:** `HunyuanVideo_MLX` fork provides Metal acceleration; FramePack integration reportedly works well. Generation is slow (3–4x vs 4090).

- **Practical recommendation for macOS:** Use the Mac for image generation (Flux/SD 3.5/SDXL are viable). For video generation at production scale, dedicate a separate GPU box (RTX 3090/4090) or cloud GPU (RunPod, Vast.ai). A Mac M3/M4 Max with 64+ GB unified memory can generate video in a pinch but is too slow for a pipeline targeting daily episode output.

---

## 7. Recommended Stack

### For a TikTok "brainrot" episodic fruit/object character pipeline:

#### Image Generation (Character Frames)
**Primary:** `FLUX.1 Kontext [dev]` on RTX 4090 (24 GB) via ComfyUI  
- Feed one canonical reference image of each character + scene description
- Gets correct character in each new scene without LoRA training
- Produces consistent identity through multi-turn editing for episode-to-episode continuity
- License issue: Verify commercial terms with BFL; low-cost commercial license available via self-serve portal

**Alternative (fully free commercial use):** `SD 3.5 Medium` + trained Character LoRA + IP-Adapter FaceID + ControlNet  
- Free up to $1M revenue (Stability AI Community License)  
- Train a LoRA on 30–50 character images using Kohya SS (~2–3h on 12 GB GPU)  
- Use "triple-lock" stack in ComfyUI: IP-Adapter (0.75) + LoRA (0.8) + ControlNet pose

**Style choice for cartoon anthropomorphic look:** Use `Pony Diffusion V6 XL` checkpoint with the LoRA approach instead of SD 3.5. Pony is pre-tuned for anthropomorphic cartoon styles and has the largest community LoRA library for these aesthetics.

#### Video Generation (Animating Characters)
**Primary:** `Wan 2.2 14B I2V` (FP8, T5 on CPU) via ComfyUI  
- Apache 2.0 commercial license — no restrictions
- Feed reference image → generates motion while preserving character
- 720p, ~5s per clip
- Chain clips with **Stable Video Infinity 2.0** LoRA to reach 60s+ without character drift

**For faster turnaround (lower quality):** `Wan 2.2 5B I2V` or `LTX-Video 2.3 FP8`  
- LTX-Video is the fastest per clip (~90s on 4090) and supports up to 20s clips natively

#### Orchestration
**ComfyUI in API/headless mode:**
1. Python script generates episode prompt from script/story system
2. Calls ComfyUI REST API at `/prompt` with Flux Kontext workflow JSON (character image + scene)
3. Waits for image output via `/history` or WebSocket
4. Calls ComfyUI Wan 2.2 I2V workflow with the new image
5. Assembles clips with ffmpeg or ComfyUI video combine nodes
6. Stable Video Infinity handles transition overlap between clips

#### LoRA Training Workflow (One-time per character)
1. Generate or source 30–50 canonical character images (various poses)
2. Auto-caption with LLaVA/Florence-2 + consistent trigger word
3. Train with Kohya SS: ~1,500–2,000 steps, rank 32, 8–12 GB VRAM for SDXL/Pony; 24 GB for Flux
4. Store LoRA file (50–250 MB) per character for all future generation

---

## 8. Open Issues & Blockers

1. **Commercial licensing for Flux.1 Kontext/Dev:** BFL requires license purchase for commercial use. Budget for this. The self-serve portal (available mid-2025) makes it straightforward, but it's not free. If budget is zero: use SD 3.5 Medium + Stability Community License instead.

2. **Wan 2.2 on macOS:** No stable native MPS path. Will need either a dedicated NVIDIA GPU or cloud GPU for video generation. Image generation can stay on Mac; video should move to GPU box.

3. **Video generation speed:** Even with RTX 4090, generating twelve 5-second clips (for a 60-second video) at 720p takes ~1–2 hours for Wan 2.2 14B, or ~18 minutes for LTX-Video 2.3. For daily upload cadence, parallel GPU or reduced resolution (480p) may be needed.

4. **Character consistency in video (not just images):** Flux Kontext handles image consistency, but once you feed an image into Wan 2.2 for animation, inter-clip consistency depends on using the same reference frame for each clip start + Stable Video Infinity latent handoff. If a character "drifts" between clips, regenerate from the canonical reference image.

5. **Pony Diffusion V6 XL license:** Current license terms on CivitAI allow non-commercial use by default. Verify whether commercial terms are available if using Pony as the base.

6. **VRAM for full stack:** To run Flux Kontext (12 GB FP8) + Wan 2.2 14B (22 GB FP8) you cannot keep both loaded simultaneously on a single 24 GB GPU. Unload between stages (ComfyUI does this automatically when switching workflow phases). 32 GB+ (e.g., RTX 3090 + 3090 NVLink or single A6000) would allow smoother batching.

---

## Sources

- https://www.bentoml.com/blog/a-guide-to-open-source-image-generation-models
- https://huggingface.co/black-forest-labs/FLUX.2-dev
- https://github.com/Wan-Video/Wan2.2
- https://huggingface.co/Wan-AI/Wan2.1-T2V-14B
- https://github.com/deepbeepmeep/Wan2GP
- https://github.com/kbadri007/Wan2mac
- https://localaimaster.com/blog/local-ai-video-generation
- https://willitrunai.com/blog/video-generation-gpu-guide-2026
- https://github.com/Lightricks/LTX-Video
- https://ltx.io/model/license
- https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- https://github.com/gaurav-nelson/HunyuanVideo_MLX
- https://huggingface.co/stabilityai/stable-diffusion-3.5-large
- https://stability.ai/news-updates/introducing-stable-diffusion-3-5
- https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev
- https://bfl.ai/announcements/flux-1-kontext
- https://www.together.ai/blog/flux-1-kontext
- https://github.com/vita-epfl/Stable-Video-Infinity
- https://www.runcomfy.com/comfyui-workflows/wan2-1-stand-in-in-comfyui-character-consistent-video-workflow
- https://apatero.com/blog/comfyui-character-consistency-advanced-workflows-2026
- https://github.com/cubiq/ComfyUI_IPAdapter_plus
- https://apatero.com/blog/train-cartoon-lora-complete-guide-2025
- https://huggingface.co/genmo/mochi-1-preview
- https://www.instasd.com/post/wan2-1-performance-testing-across-gpus
- https://medium.com/@ttio2tech_28094/rtx-3090-vs-4090-vs-5090-gpu-speed-test-running-wan2-2-animate-34f4d4b9e3dd
- https://apatero.com/blog/comfyui-vs-automatic1111-comparison-2025
- https://docs.comfy.org/tutorials/video/wan/wan2_2
- https://docs.comfy.org/tutorials/flux/flux-1-kontext-dev
- https://github.com/comfy-org/ComfyUI
- https://willitrunai.com/blog/wan-2-2-vram-requirements
