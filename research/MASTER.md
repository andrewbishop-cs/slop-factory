# MASTER — Automated AI TikTok Character-Video Pipeline

**Goal:** From a minimal text prompt → auto-generate a >1-min episodic AI character video (e.g. fruit characters w/ continuing plotlines) → human approval → auto-upload to TikTok → monetize, with **model/compute cost < TikTok income**.

**Owner:** Andrew · **Started:** 2026-06-10 · **Working dir:** `/Users/andrewbishop/video-gen`

> **🔨 BUILD PHASE:** engineering brief = [`/BUILD.md`](../BUILD.md). v0 scope = build the **full local pipeline** (prompt → finished `final.mp4` + `caption.txt` in `ready_to_post/`); **TikTok account/upload is a deferred async blocker (stubbed)**. See [15-v0-spec.md](15-v0-spec.md).

**Key constraints / assumptions:**
- Lots of local compute available; willing to download/run any open model locally.
- Wants minimal-prompt → script → video → approve → auto-post loop.
- Profitability target: recurring cost (mostly electricity + occasional API) < TikTok payout.
- ✅ **Hardware confirmed (2026-06-10):** 14" MacBook Pro, **M5 Max** (18-core CPU, 40-core GPU, 16-core Neural Engine), **64GB unified memory**, 2TB SSD. Strong for local AI — 64GB removes the memory ceiling (full-precision FLUX, no quantization needed); 40-core M5 GPU is ~3–5× an M2 Pro for diffusion. **Phase 1 MVP runs fully local for ~$0** (~3–8 min/video, full FLUX quality). Local video-gen: LTX-Video viable overnight only; Wan 2.2 still needs cloud. See [10-cloud-gpu-and-mac-only.md](10-cloud-gpu-and-mac-only.md) Part 0.

---

## Subtask tracker

| # | Subtask | Status | Findings file |
|---|---------|--------|---------------|
| 01 | Local image + image-to-video generation models | ✅ done | [01-local-generation-models.md](01-local-generation-models.md) |
| 02 | Script / story / character-continuity generation | ✅ done | [02-script-story-generation.md](02-script-story-generation.md) |
| 03 | Audio: TTS voices, music, sound, captions | ✅ done | [03-audio-tts-music.md](03-audio-tts-music.md) |
| 04 | Video assembly pipeline (stitching, ffmpeg, format) | ✅ done | [04-video-assembly-pipeline.md](04-video-assembly-pipeline.md) |
| 05 | TikTok upload automation (APIs, rules) | ✅ done | [05-tiktok-upload-automation.md](05-tiktok-upload-automation.md) |
| 06 | TikTok monetization programs + eligibility | ✅ done | [06-tiktok-monetization.md](06-tiktok-monetization.md) |
| 07 | Rules, AI-disclosure policy, ToS, ban risk | ✅ done | [07-rules-policy-compliance.md](07-rules-policy-compliance.md) |
| 08 | Economics: cost model + profitability/break-even | ✅ done | [08-economics-profitability.md](08-economics-profitability.md) |
| 09 | Synthesis: recommended end-to-end workflow | ✅ done | [09-recommended-workflow.md](09-recommended-workflow.md) |
| 10 | Cloud GPU economics + Mac-only feasibility | ✅ done | [10-cloud-gpu-and-mac-only.md](10-cloud-gpu-and-mac-only.md) |
| 11 | TikTok algorithm deep-dive + optimization checklist | ✅ done | [11-tiktok-algorithm-and-optimization.md](11-tiktok-algorithm-and-optimization.md) |
| 12 | Control interface, cadence & auto-approval design | ✅ done | [12-interface-control-and-cadence.md](12-interface-control-and-cadence.md) |
| 13 | Optimal path to making money | ✅ done | [13-optimal-path-to-money.md](13-optimal-path-to-money.md) |
| 14 | Monetization eligibility — Canadian citizen in US | ✅ done | [14-monetization-eligibility-canadian-in-us.md](14-monetization-eligibility-canadian-in-us.md) |
| 15 | v0 spec (video-hook + image body + scored + desktop upload) | ✅ done | [15-v0-spec.md](15-v0-spec.md) |

Legend: ⏳ in progress · ✅ done · ⚠️ blocked · ⬜ not started

---

## Progress log
- 2026-06-10 — Project scaffolded, master file created, 8 research subagents dispatched.
- 2026-06-10 — All 8 subagents completed and wrote findings files. Synthesis (09) written. Research phase complete.
- 2026-06-10 — Follow-up (10): cloud GPU economics + Mac-only feasibility. Conclusion: **Mac-only Phase 1 MVP is fully viable (~6–7 min/video, $0 cloud cost)**; rent cloud GPU only for optional Phase-2 AI video-gen. User chose "just research for now."
- 2026-06-10 — Hardware confirmed M5 Max/64GB → file 10 Part 0 added: full Phase 1 runs local for ~$0, full-FLUX quality, ~3–8 min/video.
- 2026-06-10 — Follow-up (11/12/13): TikTok algorithm deep-dive + optimization checklist; control-interface/cadence/auto-approval design; optimal money path. Algorithm rules folded into plan (09 §5b–5d).
- 2026-06-10 — Follow-up (14): monetization eligibility for Andrew (Canadian citizen, US resident). **KEY: account REGION (not citizenship) gates Creator Rewards; US eligible, Canada NOT eligible. Must create a fresh US-region TikTok account (US SIM + US App Store + US wifi, no VPN). Reuse US bank/card/PayPal. Tax = W-9 if US resident (SSN/ITIN) — confirm with CPA.**
- 2026-06-10 — US-number sub-question: region signal needs a REAL US +1 with SMS. Data-only travel eSIMs (Airalo standard, Nomad) can't receive the code. Andrew has only a Canadian number (on a Canada+US *data* plan). Solution = add a US line as a 2nd eSIM (dual SIM, keep Canadian number). Cheapest real non-VoIP US lines: **Red Pocket annual ~$30/yr (~$2.50/mo, AT&T eSIM)** = cheapest number-keeper; **Tello $5–10/mo** = most flexible/instant (T-Mobile eSIM). No SSN needed (prepaid, pay w/ US card). Works for TikTok + life. Avoid Google Voice/TextNow/virtual SMS (VoIP, TikTok-blacklisted).
- 2026-06-10 — **Tooling split confirmed: Claude Code = planning/research, Cursor = build.** BUILD.md retrofitted for Cursor handoff (§"How to build this in Cursor" + M0–M9 converted to explicit checkpoints w/ Test/Expected/commit-and-stop). Andrew has `ANTHROPIC_API_KEY`. Series bible is **fully decoupled** from code → building with the "Fridge Detectives" placeholder now; real niche to be brainstormed separately (research task) and dropped in via the bible JSON later — does NOT gate the build.
- 2026-06-10 — **Scope set + build brief written.** Decision: build the entire LOCAL system now (prompt → `final.mp4` + `caption.txt` → `ready_to_post/`); TikTok account/upload deferred & stubbed (async blocker). Engineering reference doc created at `/BUILD.md` (architecture, deps, scaffold, schemas, per-module specs, API keys, build order M0–M9). v0 needs only `ANTHROPIC_API_KEY` (+ optional free HF token).
- 2026-06-10 — Follow-up (15): **v0 spec locked** — 3–4s LTX-Video hook (only video-gen step, ~5–12 min) + FLUX/SDXL image body w/ Ken Burns + TTS narration + word captions + local MusicGen mood score. All free on M5 Max (~$0.08/ep Opus). Upload via **TikTok Studio desktop** (set Mac locale to US, sign up on US wifi → US region, NO phone/App Store needed; schedule up to 10 days ahead). Schedule heuristics + launchd email "post now" notifications, free.

## Rolling key findings (the short version)

**Pipeline shape:** minimal prompt → LLM script (reads a "series bible" JSON for continuity) → character images → motion → TTS voices → music + word-level captions → ffmpeg assembly to 9:16/60s+ → human approve → TikTok upload.

**Generation (01):** FLUX.1 Kontext or Pony/SDXL + a trained Character LoRA for consistent characters; Wan 2.2 (quality) or LTX-Video (speed) for motion. Orchestrate via **ComfyUI headless API**. Sweet spot = 24GB NVIDIA GPU. **Mac is fine for images, weak for video — plan a NVIDIA box or rent cloud GPU for the video step.**

**Script (02):** One LLM call → strict JSON episode schema (scenes[] w/ image_prompt, motion_prompt, narration, caption, duration). A JSON **series bible** (static appearance tokens + dynamic plot_state) carries continuity across episodes. **Decided: Claude Opus 4.8 (cloud)** for best hooks/continuity — ~$0.08/episode (~$5/mo at 2/day; Opus 4.8 = $5/M in, $25/M out, run effort:medium). This is the ONLY cloud call — all production (TTS/music/video/images/assembly) is local on the M5 Max.

**Audio (03):** Local TTS — Dia-1.6B (two-character dialogue), Chatterbox (voice cloning, MIT), or Kokoro (CPU). One reference voice per character. **Generate/royalty-free music only — popular songs block monetization.** Captions: TTS text → WhisperX forced alignment → ASS karaoke → ffmpeg burn-in.

**Assembly (04):** **MVP = static AI images + ffmpeg Ken Burns motion (~10–15× cheaper than full video-gen)**; add real video clips for hero shots later. Existing OSS to borrow from: MoneyPrinterTurbo, ShortGPT (neither does AI characters/consistency). Approval via a small Streamlit page or a Telegram bot.

**Upload (05):** Use the **official Content Posting API → "Upload to Inbox"** (scope `video.upload`, no audit needed, zero ToS risk): pipeline pushes the video to your TikTok inbox, you tap "Post" on your phone = the human-approval step. Avoid browser-automation bots (ban risk). Full auto-post needs the Direct Post audit later.

**Monetization (06):** Creator Rewards needs **10k followers + 100k views/30d + 18+ + US OK + videos >1 min**. RPM ~$0.40–0.70 entertainment (higher for finance/edu). $50 payout min. Affiliate/TikTok Shop is the faster first dollar; brand deals dominate later.

**Rules (07):** **Must toggle the AI-generated label on every video** (C2PA auto-detects anyway; non-disclosure → reach penalty → strikes). Purely templated "AI slop" with no human creative input is demonetized/suppressed → need genuine original scripting. No real-people deepfakes, nothing involving minor-coded characters, no branded IP (Disney/Nintendo/etc.), licensed/original music only. 1–3 posts/day, warm up new accounts.

**Economics (08):** Compute is ~**$0.02–0.05/video** (electricity) all-local; hybrid w/ ElevenLabs ~$0.19. Cost is essentially free — **the real hurdle is getting views**, not covering costs. Realistic: ~$0 months 1–3 (not yet eligible), $10–200/mo months 4–6 if gaining traction. Power-law: one viral video > months of small ones. Costs < income is easy *once eligible*; reaching eligibility is the work.

**✅ Hardware resolved:** M5 Max / 64GB. Verdict: run the **entire Phase 1 MVP locally for ~$0**, full-quality FLUX, ~3–8 min/video, ~40–100 videos per overnight batch. Cloud GPU only needed later for daily-cadence Phase 2 video-gen. Next decision is just whether/when to start building (user chose "research only" for now).
