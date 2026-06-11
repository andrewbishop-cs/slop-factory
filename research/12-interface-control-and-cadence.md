# 12 — Control Interface, Cadence & Auto-Approval Design

How you actually drive this thing: where you provide context (premise, characters, images, style, voices), how review/approval works, how many videos/day is realistic, and how to graduate to auto-approval safely.

---

## 1. The interface — a local control panel

Recommended: a **local web app (Streamlit)** running on the M5 Max at `localhost:8501`. One app, three screens. Everything is local — no hosting, no cost. (A Telegram bot is a nice *secondary* approval surface for tapping ✅/❌ from your phone, but the main control panel is the web app.)

```
┌──────────────────────────────────────────────────────────┐
│  CONTROL PANEL (Streamlit, localhost)                      │
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ 1. SERIES    │  │ 2. GENERATE  │  │ 3. REVIEW &       │   │
│  │   SETUP      │→ │   EPISODE    │→ │   APPROVE         │   │
│  │ (the bible)  │  │ (one prompt) │  │ (preview + ship)  │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Screen 1 — Series Setup (you do this once per show, then rarely)

This is the editor for the `series_bible.json` that carries continuity. You provide:

- **Premise / world:** one paragraph ("A walnut detective and his anxious banana sidekick solve petty crimes in a fridge.").
- **Characters** (repeatable block per character):
  - Name, personality, role
  - **Appearance tokens** — the exact phrase injected verbatim into every image prompt ("a plump cartoon walnut with a tiny fedora, big expressive eyes, 3D Pixar-style render"). This is the #1 consistency anchor.
  - **Reference image(s):** either upload one, or click *Generate* → the panel makes 4 candidates → you pick the canonical one. Stored as the character's locked reference for FLUX.1 Kontext / IP-Adapter.
  - **Voice:** pick a TTS preset or drop a 5–10s reference clip (Chatterbox clones it). Locked per character.
- **Art style anchor:** a global style string applied to all images ("consistent 3D claymation look, soft studio lighting, vibrant").
- **Plot state:** auto-managed (active threads, last cliffhanger, episode log) — you can read/edit but normally the pipeline updates it.

Output: `series_bible.json` + a `characters/` folder of locked reference images and voice samples.

### Screen 2 — Generate Episode (the everyday action)

- **One input box:** a minimal prompt — *or leave it blank and hit "Continue the story"* and the LLM advances the plot from the last cliffhanger using the bible.
- Optional knobs: target length (default 65–75s), tone, which characters appear.
- Hit **Generate.** The pipeline runs the stages (script → images → motion → TTS → captions → assemble). A progress log streams. ~3–8 min on the M5 Max.

### Screen 3 — Review & Approve (the quality gate)

Shows everything so you can fix any single piece without regenerating the whole video:

- **The script** — scenes, narration lines, on-screen captions, durations. Inline-editable; edit a caption and re-render just that.
- **The keyframe images** — a gallery, one per scene. Each has a **🔄 Regenerate** button (re-rolls just that image, keeping character consistency) and a **replace** option.
- **The assembled preview video** — the actual 9:16 MP4 player with burned captions and audio.
- **Auto-QC report** (see §3) — a checklist: duration ≥60s ✅, captions present ✅, loudness −14 LUFS ✅, hook detected ✅, character-consistency score, no failed gens.
- **Metadata** — auto-drafted caption (keyword-led), 3–5 hashtags, AI-label toggle (defaults ON), Series assignment ("Episode 7 of Fridge Detectives").
- **Actions:** ✅ **Approve & push to TikTok inbox** · 🗓 **Approve & schedule** · ✏️ **Edit** (re-roll specific parts) · ❌ **Reject** (with a note that feeds the next generation).

On approve → the video goes to your TikTok inbox via the Content Posting API; you tap "Post" on your phone (or, once auto-posting is set up, it's scheduled). The note on reject is logged so the system learns your preferences over time.

---

## 2. How many videos per day is realistic?

Two different limits — and the binding one is **not** your machine:

| Limit | Number | Notes |
|---|---|---|
| **Machine throughput (M5 Max)** | ~40–100 videos / overnight batch | 3 min (SDXL) to 8 min (full FLUX) each. Not a bottleneck. |
| **TikTok safe cadence (per account)** | **1–2 / day** | The algorithm and shadowban rules cap useful posting. New accounts: 1/day for the first 1–2 weeks, then up to 2/day, 3+ hours apart. |

So: **post 1–2 videos/day per account.** Posting more on one account does *not* get more reach — it splits your own audience and can trip spam/duplicate detection. The machine's huge headroom isn't wasted, though — it's used for **batching ahead** (generate a week's worth overnight, drip-schedule them) and **iteration** (generate 5 variations of a hook, keep the best one).

**Scaling beyond 1–2/day = more accounts, not more posts.** That's a real lever but a risky one:
- Each account needs a **genuinely distinct niche + distinct characters + distinct content.** Near-identical videos across accounts = instant duplicate-detection ban (TikTok's fingerprinting is strong in 2026).
- Multiple accounts on one IP/device with coordinated behavior risks a "coordinated inauthentic behavior" ban.
- Better first move than multi-account: **cross-post the same content to YouTube Shorts + Instagram Reels** (covered in [13-optimal-path-to-money.md](13-optimal-path-to-money.md)) — more monetization, no extra ban risk.

**Recommended cadence:** 1 account, **2 high-quality videos/day**, all part of an ongoing series. Quality + serialization beats volume on TikTok.

---

## 3. Auto-approval — how to graduate to "set it and forget it"

You start human-in-the-loop, then earn your way to auto-approval. The key is an **automated QC gate** plus a **quality score**, so "auto-approve once they're good" is gated on objective + learned checks, not blind trust.

### Stage 1 — Full human review (weeks 1–4)
Every video reviewed on Screen 3. Meanwhile the system logs your approve/reject decisions and reject-notes → builds a picture of your bar.

### Stage 2 — Automated QC gate (always on, both modes)
Hard pass/fail checks that run on *every* video before it can ship — auto-reject (regenerate) if any fail:
- Duration ≥ 60s (Creator Rewards floor)
- All scenes generated successfully (no blank/failed images)
- Burned captions present and aligned (WhisperX confidence OK)
- Audio loudness ≈ −14 LUFS, no clipping
- Character-consistency score above threshold (embedding similarity of each character vs its locked reference image)
- AI label flag = ON; music = original/CML (never a trending commercial track)
- Format = 1080×1920 / 30fps / H.264

### Stage 3 — Quality score (the "are they good?" judge)
A lightweight **vision-LLM critic** scores each video 0–100 on: hook strength (is something happening in frame 1?), visual coherence, caption correctness, pacing, loopable ending. Cheap (Claude Haiku w/ a few frames, or a local model). You set a threshold.

### Stage 4 — Conditional auto-approve
Once your **manual rejection rate drops below ~10% for 2–3 weeks**, flip on auto-approve with guardrails:
- Auto-ship only videos that **pass QC + score ≥ your threshold**.
- Anything below threshold → held in a "needs review" queue for you.
- **Daily spot-check:** you still eyeball one random auto-shipped video/day.
- **Circuit breaker:** if QC failure rate spikes, or a metric like avg completion-rate drops across recent posts, auto-approve pauses and pings you (Telegram). Protects against a model update silently degrading output.

This gives you real "good ones go out automatically" behavior without risking a bad video (or a policy violation) auto-posting to a monetized account.

---

## 4. Where this plugs into the build

- Series Setup + bible editor → Phase 1.
- Generate + Review/Approve (manual) → Phase 1.
- Auto-QC gate → Phase 1 (cheap, high value).
- Quality-score critic + conditional auto-approve + scheduling → Phase 3.
- Telegram approval/circuit-breaker → Phase 3.
