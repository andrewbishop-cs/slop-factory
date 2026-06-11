# Cloud GPU Economics & Mac-Only Feasibility

**Research date:** June 2026  
**Scope:** GPU rental pricing, cost-per-video modeling, ramp-up spend, Mac-only stage-by-stage feasibility

> **Note (2026-06-10):** The baseline tables below were written for a generic M2 Pro / 16GB Mac. Andrew's actual machine is an **M5 Max (18-core CPU, 40-core GPU, 16-core Neural Engine), 64GB unified memory, 2TB SSD**. See **Part 0** immediately below for the numbers recalculated for that machine — it supersedes the M2 Pro estimates throughout.

---

## Part 0: Recalculated for Andrew's M5 Max / 64GB (the actual machine)

### Why this machine changes the conclusion

Two specs matter for local AI, and this machine is strong on both:

- **64GB unified memory** — on Apple Silicon the GPU shares system RAM, so ~48GB is usable for ML. This **removes the memory ceiling** the baseline worried about. You do **not** need GGUF/quantized models or quality compromises: you can run **FLUX.1-dev at full precision**, keep an image model **and** a local LLM **and** TTS resident simultaneously, and never swap. 16GB Macs can't do this; 64GB does it comfortably.
- **40-core GPU + M5 per-core neural accelerators** — the M5 generation added a matrix/neural accelerator inside every GPU core, which is exactly the math diffusion and LLM inference hammer. Combined with 40 cores (vs ~16–19 on an M2 Pro), this is roughly **3–5× faster than the M2 Pro baseline** for image generation. (Exact M5 Max diffusion benchmarks are still sparse in mid-2026, so the per-image figures below are architecture-scaled estimates — treat as ballpark, to be confirmed on first run.)

### Estimated speeds on the M5 Max (Phase 1 — image + Ken Burns)

| Stage | Model | M2 Pro baseline | **M5 Max / 64GB (est.)** |
|---|---|---|---|
| Image gen | SDXL-Pony 1024² | ~25 s/img | **~5–8 s/img** |
| Image gen | FLUX.1-schnell | ~45 s/img | **~8–15 s/img** |
| Image gen | FLUX.1-dev (full, 30 steps) | ~140 s/img | **~25–45 s/img** |
| TTS | Kokoro (60s speech) | ~5 s | ~3 s |
| Captions | WhisperX (CPU) | ~10 s | ~6 s |
| Assembly | ffmpeg Ken Burns (VideoToolbox) | ~45 s | ~30 s |

**Per-video wall-clock (12 images):**
- **Full FLUX.1-dev quality:** 12 × ~35s + overhead ≈ **~8 minutes/video** — i.e. you can run the *highest-quality* image model and still finish in minutes. This is the payoff of 64GB.
- **SDXL-Pony (fast):** 12 × ~7s + overhead ≈ **~3 minutes/video.**

**Overnight batch:** at ~8 min/video for full-quality FLUX, you can produce **~40 videos in a 6-hour overnight run**, or ~100+ on SDXL. The 14" Pro has active cooling, so it sustains this without the throttling an Air would hit. Plug into the 96W adapter, run `caffeinate -i`, let it run overnight.

### Cost on the M5 Max

**Effectively $0 in compute.** The SoC draws roughly ~40–60W under sustained GPU load, so per-video electricity is well under **$0.01**. The only real recurring cost is the script LLM if you use Claude (~$0.002–0.01/video with Haiku) — and even that can go fully local (see below). **Phase 1 is genuinely free to run on this machine.**

### Local LLM is now viable too (bonus from 64GB)

With 64GB you can run a strong local LLM for scripts and skip the Claude API entirely if you want zero marginal cost:
- **Qwen3-32B / Qwen2.5-32B (4-bit, MLX):** fits easily, good quality for scripts — recommended local option.
- Even larger (70B 4-bit ~40GB) is technically loadable, though slower.
- Trade-off: Claude Haiku still writes better viral hooks for ~$0.002/script. Reasonable to start on Haiku and switch to local Qwen once you have a prompt that works.

### Phase 2 (real AI video-gen) on the M5 Max — partially viable, overnight only

The 64GB removes the *memory* problem, but the *MPS software* problem remains:
- **LTX-Video:** has partial MPS support. Estimate **~5–12 min/clip** on the M5 Max (vs 90s on an RTX 4090). A 60s episode (~12 clips) = **~1–2.5 hours**. **Viable as a free overnight job for occasional "hero shot" clips**, not for daily-cadence full-video-gen.
- **Wan 2.2:** still has no reliable MPS backend — impractical locally regardless of memory. Rent cloud for this.

So the recommendation shifts slightly vs the generic baseline: **you can experiment with local LTX-Video hero shots for free overnight**, and only rent cloud GPU (Vast.ai LTX-Video, ~$0.15/video) when you want video-gen at daily cadence or want Wan 2.2 quality.

### Bottom line for this machine

**Run the entire Phase 1 MVP — including full-quality FLUX images — locally on the M5 Max for ~$0.** No cloud needed, no quality compromise, ~3–8 min/video, ~40–100 videos per overnight batch. Add cloud GPU only for daily-cadence Phase 2 video-gen once your content is proven to pull views. This machine is, if anything, over-specced for Phase 1 — which is good: it means zero friction and zero cost while you focus on the actual hard part (making content people watch).

---

## Part 1: Cloud GPU Rental Pricing (2025–2026 live rates)

### Provider Comparison Table

| GPU | RunPod Community | RunPod Secure | Vast.ai (marketplace) | Spheron | Lambda Labs | Notes |
|-----|-----------------|---------------|----------------------|---------|-------------|-------|
| RTX 4090 (24 GB) | $0.69/hr | ~$0.89–1.10/hr | $0.25–$0.55/hr | $0.55/hr | N/A | Best value for 24GB VRAM work |
| RTX A5000 (24 GB) | $0.27/hr | ~$0.45/hr | $0.20–$0.35/hr | N/A | N/A | Solid budget pick |
| RTX A6000 (48 GB) | $0.49/hr | ~$0.70/hr | $0.30–$0.50/hr | N/A | $0.80/hr | 48GB handles large FLUX batches |
| A100 80GB | $1.49/hr (SXM) | ~$2.00/hr | $0.67–$2.06/hr | $1.07/hr | $2.06/hr | Overkill for this pipeline |
| L40S (48 GB) | $0.86/hr | ~$1.10/hr | ~$0.40–$0.60/hr | $0.72/hr | N/A | Good inference throughput |

**Sources:** RunPod pricing page (May 2026 scrape: RTX 4090 Community ~$0.69/hr); Vast.ai marketplace listings (~$0.35–$0.44/hr median for RTX 4090 April 2026); Spheron blog GPU comparison May 2026.

### Billing Mechanics — Important Details

- **RunPod:** Per-second billing, billed to the millisecond. No minimum charge per session. Pod starts in <30 seconds (FlashBoot serverless: <2 second cold starts). Storage billed separately at $0.10/GB/month (network volumes $0.07/GB/month). **Zero egress fees** — downloading outputs is free.
- **Vast.ai:** Per-second billing. $5 minimum account deposit. Three modes: on-demand (full price), interruptible (~50% cheaper, can be preempted mid-job), reserved (commit days/weeks for discounts). Egress pricing not clearly advertised; budget conservatively.
- **Spheron:** On-demand + spot pricing (40–65% spot discount). SLA-backed reliability vs. Vast.ai's marketplace variability.
- **Lambda Labs:** Hourly billing, fixed pricing, no marketplace variability. More expensive but consistent.

**Key nuance for batch jobs:** Because billing is per-second, you pay only for active compute. A 10-minute image-gen job on a $0.69/hr RTX 4090 costs exactly $0.115. You are NOT locked into hourly minimums on RunPod or Vast.ai.

---

## Part 2: Cost Per Video — Two Scenarios

### Assumptions

- **Target output:** One ~60-second episode = ~10–15 character images + 60s voiceover + captions + final ffmpeg assembly
- **GPU used for costing:** RTX 4090 at $0.50/hr blended (Vast.ai interruptible / RunPod Community average, rounded for safety)

---

### Scenario A: Image + Ken Burns MVP (Phase 1)

**What needs GPU:** Only image generation in ComfyUI. Everything else (TTS, ffmpeg, captions) is CPU/lightweight.

**Image generation workload:**
- SDXL-Pony at 1024×1024: ~5–6 seconds per image on RTX 4090
- FLUX.1-schnell at 1024×1024: ~12–18 seconds per image on RTX 4090
- FLUX.1-dev (30 steps): up to 30–35 seconds per image

- Generate 12 character images (conservative FLUX.1-dev at 35 sec each): **~7 minutes**
- Add 2 minutes for model loading, pod startup, file I/O: **total ~9 minutes GPU time**

**Cost calculation:**
- 9 minutes ÷ 60 × $0.50/hr = **~$0.075 per video**
- At $0.69/hr RTX 4090 RunPod: ~$0.10 per video
- At Vast.ai interruptible $0.30/hr: ~$0.045 per video

**Realistic range: $0.05–$0.12 per video** for Phase 1 (image-only GPU work)

If using SDXL-Pony instead of FLUX (much faster — 5–6 sec/image):
- 12 images × 6 sec = 72 sec + 2 min overhead = ~3.5 min GPU time = **~$0.03 per video**

**Storage overhead (minimal):**
- 12 images × ~4MB each = ~48MB output. At $0.10/GB/month = $0.005/month per 100 videos stored. Negligible.
- Keep a 20GB persistent volume for ComfyUI + models (~$1.40/month flat). Amortized: $0.003/video at 500 videos/month.

**Phase 1 MVP realistic total per video: $0.05–$0.15** (GPU + storage amortized)

---

### Scenario B: Full AI Video Generation (Phase 2 — Wan 2.2 / LTX-Video)

**Benchmarks on RTX 4090:**
- **Wan 2.2** (14B, 1280×720, 81 frames = ~5.4 sec clip): **~4 min 20 sec per clip**
- **LTX-Video** (768×512, 65 frames = ~5 sec clip): **~90 seconds per clip**

**A 60-second episode needs ~11–12 clips of 5 seconds:**

| Model | Time per clip | 12 clips | + overhead | Total GPU | @ $0.50/hr |
|-------|--------------|----------|------------|-----------|------------|
| Wan 2.2 | 4 min 20 sec | 52 min | +8 min | ~60 min | **$0.50** |
| LTX-Video | 90 sec | 18 min | +5 min | ~23 min | **$0.19** |
| LTX-Video @ $0.30/hr | 90 sec | 18 min | +5 min | ~23 min | **$0.12** |

**Phase 2 realistic range: $0.12–$0.60 per video** (10–40× more expensive than Phase 1)

At Wan 2.2 full quality on RunPod RTX 4090 ($0.69/hr): ~$0.69 per video  
At LTX-Video on Vast.ai interruptible: ~$0.10–$0.15 per video

---

## Part 3: Ramp-Up Spend Before First Dollar

### TikTok Creator Rewards Eligibility Gate
- Requires: **10,000 followers + 100,000 qualified views in 30 days**
- Realistic ramp-up: 3–6 months of consistent posting (1–2 videos/day) to build audience
- During this period: **zero revenue, 100% cost out of pocket**

### Spend Table: Cloud Cost During Unmonetized Ramp-Up

**Phase 1 MVP (image + Ken Burns): ~$0.10/video blended estimate**

| Videos/day | Days to ~1M views (est.) | Total videos | Cloud cost (Phase 1) | Cloud cost (Phase 2 Wan) |
|------------|--------------------------|--------------|----------------------|--------------------------|
| 1/day | 120 days | 120 | **$12** | **$83** |
| 2/day | 75 days | 150 | **$15** | **$104** |
| 3/day | 60 days | 180 | **$18** | **$125** |

**Phase 1 (image MVP) ramp-up spend: $12–$18 total** — negligible. This is the single biggest financial argument for Phase 1 first.

**Phase 2 (AI video) ramp-up spend: $83–$125 total** — meaningful but still manageable. The risk is spending this much before confirming the content has an audience.

### Time-to-Profitability (post-eligibility)

Once eligible, at RPM ~$0.50/1k views:
- Break-even on $0.10/video Phase 1 cost: need **200 qualified views per video** (trivial once monetized)
- Break-even on $0.50/video Phase 2 cost: need **1,000 qualified views per video**

**Bottom line on cloud economics:** Phase 1 cloud costs are low enough that profitability is nearly immediate once monetized. Phase 2 requires meaningful viewership to cover costs — do not upgrade to Phase 2 until Phase 1 videos are proven to attract views.

---

## Part 4: Mac-Only Feasibility — Stage-by-Stage Analysis

### Prerequisite: The Phase 1 MVP Has No Real-Time GPU Requirement

The critical insight: **Phase 1 does not require video generation AI at all.** The GPU-intensive step (real video diffusion) is replaced by ffmpeg pan/zoom on static images. This changes the Mac-only picture dramatically.

### Feasibility Table

| Pipeline Stage | Tool | Mac Feasibility | Speed on M2 Pro (typical) | Notes |
|---------------|------|----------------|--------------------------|-------|
| **Script/LLM** | Claude API (cloud) | Excellent | <5 sec | API call, no local compute needed |
| **Script/LLM** | Ollama (local, llama3.2:3B) | Good | ~10–30 tokens/sec | Runs well via MLX on Apple Silicon |
| **Image gen — FLUX.1-dev** | ComfyUI / Draw Things (MPS) | Viable (slow) | ~105–145 sec/image (M2–M3 Max, 32GB) | With GGUF Q6 on 16GB: ~120–150 sec/image |
| **Image gen — FLUX.1-schnell** | ComfyUI (MPS) | Good | ~30–60 sec/image (M2/M3 Pro) | Much faster; lower quality |
| **Image gen — SDXL-Pony** | ComfyUI (MPS) | Good | ~15–40 sec/image (16–32GB) | Fastest option, good character consistency |
| **Image gen — 8GB Mac** | SDXL/FLUX GGUF Q4 | Marginal | 2–5 min/image (16-bit swapping) | Usable but slow; 8GB is painful |
| **TTS — Kokoro** | kokoro-mlx / Python | Excellent | 13–70x real-time | 60s of speech in 1–5 sec. Near-instant. |
| **TTS — Chatterbox** | Python + MPS | Very good | 2–3x faster than CPU | Full MPS support; minutes for 60s audio |
| **WhisperX captions** | Python (CPU fallback) | Good (slow) | ~5–14x real-time for large-v3 | No Metal/MPS support in WhisperX; CPU only. 60s audio = ~4–12 sec transcription |
| **ffmpeg Ken Burns** | ffmpeg (VideoToolbox) | Excellent | Real-time or faster | VideoToolbox hardware encode. This is pure CPU/GPU video assembly — NO AI inference. Very fast. |
| **ffmpeg final assembly** | ffmpeg | Excellent | Real-time to 2x | H.264/HEVC via VideoToolbox hardware acceleration |
| **Wan 2.2 video gen** | ComfyUI (MPS) | Not practical | Est. 30–90+ min/clip | Wan 2.2 is NOT optimized for MPS; likely CPU fallback = impractical |
| **LTX-Video** | Python (MPS) | Marginal | 10–30 min/clip (est.) | Some MPS support but much slower than CUDA; no reliable benchmarks |

### Wall-Clock Time Estimate: One Episode on MacBook (Phase 1 MVP)

Assumption: M2 Pro, 16GB RAM, SDXL-Pony for speed

| Step | Time |
|------|------|
| Script gen (Claude API) | 10 seconds |
| Image gen: 12 images × 25 sec (SDXL, 16GB) | ~5 minutes |
| TTS voiceover (Kokoro, 60s script) | ~5 seconds |
| WhisperX captions (60s audio, CPU) | ~10 seconds |
| ffmpeg Ken Burns + assembly | ~30–60 seconds |
| **Total** | **~6–7 minutes** |

On M2 Max / M3 Max (32GB), using FLUX.1-schnell:
- 12 images × 45 sec = 9 min + other steps = ~10–11 minutes total

On M1 Pro / M2 (16GB) with FLUX.1-dev (slow):
- 12 images × 140 sec = ~28 min + overhead = ~30 minutes per video

**All of these are fully viable for overnight or background operation.**

### Overnight/Background Run Practicality

**MacBook Pro (any generation with active cooling):**
- Sustains multi-hour AI workloads without throttling — the cooling fan activates and maintains clock speed
- Can process 10–20 videos overnight (6 hours) at Phase 1 rates without issue
- Recommend: plugged in, lid can be closed (use `caffeinate -i` to prevent sleep), fan will run audibly

**MacBook Air (no fan — M1/M2/M3/M4/M5):**
- Thermal throttles within 8–15 minutes of sustained MPS load
- Can still work: image gen jobs are not constant — there are natural gaps between ComfyUI iterations
- For batch overnight work: Air will throttle and recover in cycles, adding 20–40% time overhead
- Workaround: use Draw Things (better thermal management) or space jobs with small delays
- The Air is viable but slower; the Pro is noticeably better for sustained overnight work

**Practical overnight batch script:** Queue 15 videos, start at 11pm, wake up to finished content. On M2 Pro, 15 videos × 7 min = ~2 hours. Plenty of buffer.

### What Is NOT Practical on Mac Alone

1. **Wan 2.2 (real video diffusion):** No optimized MPS backend. Likely falls back to CPU — estimated 30–90+ minutes per 5-second clip. A 60-second episode = 10+ hours. Completely impractical.

2. **LTX-Video at scale:** Some MPS support exists, but expect 10–30 min/clip vs. 90 sec on RTX 4090. A 60-second episode = 2–5 hours. Technically possible but very slow for production.

3. **HunyuanVideo, CogVideoX, other large video models:** Not viable on Mac at any practical speed.

---

## Part 5: Recommended Hybrid Approach

Once you're ready to upgrade from Phase 1 to Phase 2:

**Option A — Cloud burst for video gen:**
- Run LLM + image gen + TTS + captions + assembly locally on Mac (free)
- Rent cloud GPU only for the video diffusion step
- Script: upload your 12 character images → run LTX-Video on RunPod/Vast.ai (~23 min) → download videos → assemble on Mac
- Cost: ~$0.15–$0.20 per video (LTX-Video on cheap Vast.ai GPU)
- You only pay for the ~23 minutes of actual video gen compute

**Option B — Dedicated local GPU:**
- RTX 4090 desktop: ~$1,600–$1,800 used (2026 market)
- Payback vs. cloud: at $0.50/video cloud cost and 2 videos/day = $30/month cloud → break-even in ~5 years
- Payback at 10 videos/day = $150/month → break-even in ~12 months
- Only makes sense if you're doing >5 videos/day consistently

---

## Part 6: Bottom-Line Recommendation

### For someone unsure of their hardware who wants low/zero upfront cost:

**Start with Mac-only Phase 1 MVP. It works. It costs essentially nothing.**

The Phase 1 pipeline (SDXL/FLUX images + Ken Burns pan/zoom + Kokoro TTS + ffmpeg assembly) runs entirely on a MacBook with no cloud GPU cost. Total compute cost per video: ~$0.00 (just electricity). The only recurring cost is Claude API for script generation (~$0.002–$0.01/script with Haiku).

This gives you time to:
1. Build content without any financial risk
2. Discover what character/plot formats perform on TikTok
3. Hit the 10k/100k follower/view bar (the real bottleneck, not cost)

**When to add cloud GPU:**
- When you want higher video quality and Phase 1 views are consistently >50k per video
- Budget $15–$25/month for Phase 2 cloud bursting (LTX-Video, ~2 videos/day)
- Use Vast.ai interruptible instances for cheapest rates; RunPod Community for reliability

**Never upgrade to full Phase 2 Wan 2.2 cloud costs until:**
- You have >100k followers (monetized)
- Revenue covers the $30–$50/month cloud spend at 2–3 videos/day

### Decision Matrix

| Your situation | Recommendation |
|---------------|----------------|
| MacBook Air or Pro, any M-series, 16GB+ RAM | Mac-only Phase 1, no cloud needed |
| MacBook with only 8GB RAM | Mac-only Phase 1 is marginal; consider Vast.ai for image gen ($0.03–$0.05/video) |
| No Mac, want zero upfront cost | Vast.ai RTX 4090 interruptible: ~$0.05–$0.10/video Phase 1, very manageable |
| Already have views, want quality upgrade | Add cloud LTX-Video burst: ~$0.15/video Phase 2, ROI positive once monetized |
| Serious production (10+ videos/day) | Consider RTX 4090 desktop purchase; cloud at scale gets expensive |

---

## Sources

- [RunPod GPU Pricing](https://www.runpod.io/pricing)
- [RunPod Pods Pricing Documentation](https://docs.runpod.io/pods/pricing)
- [Vast.ai RTX 4090 Pricing](https://vast.ai/pricing/gpu/RTX-4090)
- [GPU Cloud Pricing Comparison 2026 — Spheron Blog](https://www.spheron.network/blog/gpu-cloud-pricing-comparison-2026/)
- [RTX 4090 Cloud Pricing: 14+ Providers](https://getdeploying.com/gpus/nvidia-rtx-4090)
- [Cloud GPU Pricing 2026 — SynpixCloud](https://www.synpixcloud.com/blog/cloud-gpu-pricing-comparison-2026)
- [Flux on Apple Silicon Complete Guide — Apatero](https://www.apatero.com/blog/flux-apple-silicon-m1-m2-m3-m4-complete-performance-guide-2025)
- [Local AI Video Generation: Wan 2.2, LTX-Video — Local AI Master](https://localaimaster.com/blog/local-ai-video-generation)
- [Wan2.1 Performance Testing Across GPUs — InstaSD](https://www.instasd.com/post/wan2-1-performance-testing-across-gpus)
- [ComfyUI GPU Benchmark Discussion](https://github.com/Comfy-Org/ComfyUI/discussions/2970)
- [Kokoro TTS on Apple Silicon — DEV Community](https://dev.to/xadenai/building-a-local-voice-ai-stack-whisper-ollama-kokoro-tts-on-apple-silicon-eo0)
- [Kokoro TTS CoreML](https://github.com/mattmireles/kokoro-coreml)
- [Whisper Benchmark Apple Silicon — JustVoice](https://justvoice.ai/blog/whisper-benchmark-apple-silicon-m3-m4)
- [M5 MacBook Air Thermal Throttling — SolidAITech](https://www.solidaitech.com/2026/04/m5-macbook-air-local-ai-thermal-throttle-problem.html)
- [LTX-Video GitHub Issue — generation times](https://github.com/Lightricks/LTX-Video/issues/166)
