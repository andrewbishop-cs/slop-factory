# 09 — Recommended End-to-End Workflow (Synthesis)

This ties together findings 01–08 into a concrete, buildable plan for an automated pipeline that turns a one-line prompt into a >60s episodic AI character video, lets you approve it, and posts it to TikTok — with cost well below income once the account is monetized.

---

## 0. The local/cloud split (decided)

- **Cloud (one external call):** the **script LLM = Claude Opus 4.8** (~$0.08/episode, ~$5/mo at 2/day). This is the only thing that leaves the machine.
- **Local on the M5 Max (all the heavy production):** image generation, image→video/motion, **TTS voices, music, captions, and final assembly** — all run on-device for ~$0.

So the recurring cost of the whole pipeline is essentially **just the Opus script call** (a few dollars a month) plus negligible electricity. Everything Andrew called "production" stays local by design.

## 1. The architecture at a glance

```
  [you type one line]                          ┌─────────────────────────┐
        │                                      │  series_bible.json      │
        ▼                                      │  (characters, plot state)│
  ┌──────────────┐   reads/updates  ◄──────────┤  persistent memory       │
  │ 1. SCRIPT     │ ─────────────────────────► └─────────────────────────┘
  │ LLM → episode.json (scenes[], prompts, narration, captions, durations)
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ 2. IMAGES     │  ComfyUI API: FLUX.1 Kontext / Pony+CharacterLoRA
  │  one keyframe per scene, character kept consistent
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ 3. MOTION     │  MVP: ffmpeg Ken Burns (pan/zoom) on stills  ← cheap
  │               │  V2: Wan 2.2 / LTX-Video image-to-video clips ← pricey
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ 4. AUDIO      │  TTS per character (Chatterbox/Dia/Kokoro)
  │               │  + generated/royalty-free music bed
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ 5. CAPTIONS   │  WhisperX forced-align → ASS karaoke subtitles
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ 6. ASSEMBLE   │  ffmpeg: stitch clips + audio + music + captions
  │               │  → 1080x1920, 30fps, H.264/AAC, >60s, −14 LUFS
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ 7. APPROVE    │  Streamlit page OR Telegram bot → ✅/❌
  └──────┬───────┘
         ▼ (on approve)
  ┌──────────────┐
  │ 8. UPLOAD     │  TikTok Content Posting API → "Upload to Inbox"
  │               │  → notification on phone → set AI label → tap Post
  └──────────────┘
```

Each stage writes intermediate files to disk (e.g. `episodes/ep_007/`) so the pipeline is resumable and debuggable.

---

## 2. Recommended tech stack

| Stage | Primary choice | Why | Fallback |
|---|---|---|---|
| Orchestration | Python script (stage functions) → later Celery+Redis | Simple, resumable, easy to debug | n8n if you prefer visual wiring |
| Script LLM | **Claude Opus 4.8** (cloud) + prompt caching | Andrew's choice — best hooks/continuity; ~$0.08/ep (~$5/mo at 2/day). Strict JSON via tool_use; run `effort: medium` to keep cost low | Haiku 4.5 (~10× cheaper) or local Qwen3-32B (free) |
| Image gen | FLUX.1 Kontext (ref-image consistency) **or** Pony/SDXL + trained Character LoRA | Same character every episode w/o drift | SD 3.5 Medium (free commercial) |
| Image→video | LTX-Video 2.3 (fast) / Wan 2.2 14B (quality) | Apache-2.0, local | Skip in MVP — use Ken Burns |
| Generation host | **ComfyUI in headless API mode** | POST workflow JSON, fully scriptable | diffusers library |
| TTS | Chatterbox (clone, MIT) / Dia-1.6B (dialogue) / Kokoro (CPU) | Per-character voices, commercial-safe | ElevenLabs ($22/mo) |
| Music | ACE-Step / MusicGen (local) or Epidemic Sound | **Monetization-safe** (NOT trending songs) | TikTok Commercial Music Library |
| Captions | WhisperX forced-align → ASS → ffmpeg burn-in | Word-level karaoke captions, free | pycaps library |
| Assembly | ffmpeg (final) + MoviePy 2.0 (prototyping) | Fast, hardware-encoded | Remotion/Revideo for fancy overlays |
| Approval | Streamlit (desktop) or Telegram bot (mobile) | ~30 lines, instant | drop-to-folder |
| Upload | TikTok Content Posting API — Upload to Inbox | Free, no audit, no ToS risk | Postiz (self-host) / upload-post ($16/mo) |

**Hardware:** 24GB NVIDIA GPU (e.g. RTX 4090) is the sweet spot. Use the Mac for images if needed, but route video-gen to a NVIDIA box or rent cloud GPU (RunPod/Vast.ai) — there's no production-ready Mac video-gen path. For the MVP (Ken Burns instead of video-gen), even modest hardware works.

---

## 3. Build it in phases (don't build it all at once)

**Phase 0 — Manual proof (1 evening).** Hand-make ONE 60s fruit-character episode using the tools above, manually. Post it. This validates the format and your account before automating anything.

**Phase 1 — MVP pipeline (the "image + Ken Burns" version).**
- Script LLM → `episode.json`
- ComfyUI generates one image per scene (with character consistency)
- ffmpeg Ken Burns motion on each image + crossfades
- Local TTS narration + royalty-free music
- WhisperX → burned karaoke captions
- ffmpeg final assemble to spec
- Streamlit approve screen → TikTok Upload-to-Inbox
- **This is fully functional, cheap (~$0.03/video), and avoids the slow/expensive video-gen step.**

**Phase 2 — Quality upgrades.** Swap Ken Burns → real Wan 2.2/LTX-Video clips for hero shots; train a Character LoRA for rock-solid consistency; add distinct character voices; better transitions.

**Phase 3 — Scale & continuity.** Series-bible automation for multi-episode plotlines, scheduling cadence (1–3/day), analytics feedback loop (double down on what gets views).

---

## 4. Cost vs. income (the profitability answer)

- **Marginal cost per video:** ~$0.02–0.05 all-local (just electricity), ~$0.19 hybrid.
- **Income:** Creator Rewards RPM ~$0.40–0.70/1k qualified views (entertainment). $50 payout minimum.
- **Verdict:** Cost is trivially below income — **per-video economics are positive from the first monetized view.** The real constraint is *eligibility + views*, not cost:
  - Need **10k followers + 100k views/30d** to even join Creator Rewards (~2–5 months of consistent posting).
  - Then ~8–10k views/video avg ≈ ~$250/mo.
- **Honest timeline:** $0 months 1–3 (building to eligibility), $10–200/mo months 4–6 if gaining traction. One viral video out-earns months of small ones. Add **TikTok Shop affiliate** (works at 1k followers) for earlier income, and treat **brand deals** as the real money later.

---

## 5. Rules you must follow (compliance checklist)

✅ **Toggle the "AI-generated content" label on every single video** (TikTok auto-detects via C2PA anyway; not disclosing → reach penalty → strikes → eventual demonetization).
✅ **Put genuine original creative input into each video** (unique script/story/angle). Pure templated mass-output = "AI slop" = suppressed + demonetized.
✅ **Only generated or licensed/royalty-free music.** Trending commercial songs block monetization and trigger takedowns.
✅ **Original characters only** — no Disney/Nintendo/Marvel/branded IP look-alikes.
✅ **No real-person deepfakes; nothing involving minor-coded characters** (zero-tolerance ban categories).
✅ **1–3 posts/day**, warm up new accounts for 2–3 weeks, vary posting times.
✅ **Use the official API / approved schedulers only** — no bulk-posting bots (ban risk).
✅ Personal (not Business) account, 18+, in an eligible region (US is fine).

---

## 5b. Algorithm-optimization layer (baked into every video)

Reach is won by retention, not luck. The generator must **always** enforce these (full detail + signal-weighting table in [11-tiktok-algorithm-and-optimization.md](11-tiktok-algorithm-and-optimization.md)). Top rules, by impact:

1. **Hook in frame 1** — open mid-action/mid-dialogue, never a title card. (~70% of viewers decide in 3s.)
2. **Engineer ≥45% completion** — open loops, a mid-video pattern interrupt, scene change every 5–7s, micro-hooks. (Completion rate is the #1 signal; the 70% early-retention bar graduates a video to wider distribution.)
3. **Loopable endings** — a rewatch counts as 200% watch time; loop-designed endings get ~65% more rewatches.
4. **60s+ every episode** — Creator Rewards floor; under 60s earns $0.
5. **Burned captions** — serves the ~30% muted viewers *and* feeds OCR keyword indexing.
6. **Keyword-led caption + speak keywords in first 10s** — TikTok indexes ASR + OCR + caption + hashtags (it's a search engine now). 3–5 targeted hashtags, not 20.
7. **Original or Commercial-Music-Library audio only** — trending commercial songs block monetization.
8. **Register every episode in a TikTok Series** — unlocks "Episode X of Y", autoplay binge-chaining, and the new Short-Drama Feed.
9. **AI label ON at publish** — self-labeling is clean; letting TikTok auto-label is adversarial.
10. **Post 1–2/day, consistent times, 3h+ apart; never duplicate fingerprints.**

These map directly to pipeline features: the script LLM is prompted to produce a frame-1 hook + open loops + a loopable cliffhanger; captions are always burned; metadata is auto-generated keyword-first; the QC gate enforces ≥60s, captions, AI-label, and audio source.

## 5c. Control interface & cadence

See [12-interface-control-and-cadence.md](12-interface-control-and-cadence.md). A local Streamlit panel with three screens: **Series Setup** (the bible — premise, characters, appearance tokens, reference images, voices), **Generate** (one prompt or "continue the story"), and **Review & Approve** (editable script + per-image regenerate + preview player + auto-QC report + push-to-TikTok). Realistic cadence: **1–2 videos/day per account** (TikTok's limit, not the machine's — the M5 Max can batch 40–100/night). Auto-approval graduates in: full human review → automated QC gate → vision-LLM quality score → conditional auto-approve with daily spot-check + circuit breaker.

## 5d. Optimal path to money

See [13-optimal-path-to-money.md](13-optimal-path-to-money.md). Since cost is ~$0, it's a views/retention/serialization game. Stages: lock a differentiated serialized niche → grow to 1k followers (enable **TikTok Shop affiliate** = first dollars) → reach 10k followers + 100k views/30d (**Creator Rewards** eligible) → stack **brand deals (the real money) + affiliate + Creator Rewards** → **cross-post to YouTube Shorts + Reels** (higher RPM, no extra ban risk — the best scaling move, beats multi-account). Power-law reality: one breakout > months of small posts.

## 6. Immediate next steps

1. **Tell me your GPU + VRAM** and whether it's the Mac or a separate machine — this picks the exact model tier and decides local-vs-cloud for video.
2. Decide MVP scope: I recommend **Phase 1 (image + Ken Burns)** first.
3. Register a TikTok developer app and request the `video.upload` scope (no audit needed for Upload-to-Inbox).
4. I can then scaffold the actual repo: stage modules, the `episode.json` schema, the series-bible file, a ComfyUI workflow JSON, and the ffmpeg assembly + Streamlit approval scripts.
