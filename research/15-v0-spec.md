# 15 — v0 Spec (Andrew's "video-hook + image body + scored" approach)

Andrew's proposed v0, confirmed feasible and free on the M5 Max (only recurring cost = ~$0.08/episode Opus script call). This is the concrete thing to build first.

## ⚠️ Scope decision (2026-06-10): build the full LOCAL system now, defer upload

The TikTok account creation (US phone number → US-region account → desktop upload) is an **async blocker** Andrew will handle separately. **It does not block building or running the generation system.**

- **Build now (this is the whole v0):** everything from a one-line prompt → finished, spec-compliant **`final.mp4` + `caption.txt`** dropped into a local **`ready_to_post/`** folder. Fully runnable locally on day one, producing watchable videos you can review and iterate on.
- **Deferred (do later, when the US account is live):** the actual TikTok upload, scheduling-into-TikTok, and email "post now" notifications. These are **stubbed** in the codebase (the upload module just writes the finished file + caption to `ready_to_post/` and prints manual-upload instructions) so they can be filled in without touching the rest.
- **Net:** you can run the entire pipeline and pile up finished videos locally while the phone/account piece happens in parallel. When the account is ready, you manually drag the queued files into TikTok Studio (and optionally wire up the deferred auto-upload module).

**The full engineering build brief lives in [`/BUILD.md`](../BUILD.md)** — architecture, deps, project scaffold, schemas, per-module specs, API keys, and build order. Use that doc for prompting the actual build.

## The format

```
[0–4s]   HOOK — a real generated VIDEO clip (slap / fall / high-motion), highly attention-catching
[4–75s]  BODY — AI still images animated with ffmpeg Ken Burns (pan/zoom), scene by scene
overlay  TTS narration (audio) + on-screen text up top + word-by-word karaoke captions lower third
score    locally-generated music bed, matched to each scene's tension/environment, mixed under narration
out      1080×1920 / 30fps / H.264 / AAC, ≥60s, −14 LUFS → review → desktop upload
```

## Is each piece possible on the M5 Max, free? — Yes, with one caveat

### 1. The 3–4s real-video hook — ✅ feasible (the one slow step)
- Generate **one short clip** with **LTX-Video** locally (MPS). One 3–4s clip ≈ **~5–12 min** on the M5 Max — fine because it's the *only* video-gen step; the rest is fast images.
- **Caveat (be realistic):** fast physical action (a convincing "slap" or "fall") is the *hardest* thing for current local video models — real-world physics can look janky. Mitigations: (a) keep it **stylized/cartoon** (exaggerated motion is far more forgiving and on-brand for these characters), (b) expect to **re-roll a couple times** and pick the best, (c) build a small **reusable hook-clip library** (5–10 good slaps/falls/trips you regenerate rarely and remix). Wan 2.2 would look better but has no Mac path — that's the only reason to ever rent cloud later.

### 2. Image body + Ken Burns — ✅ fast & free
FLUX.1 / SDXL-Pony images (character-consistent) → ffmpeg `zoompan` pan/zoom + crossfades. ~3–8 min for the whole body on the M5 Max.

### 3. Narration + on-screen text + captions — ✅ free
- **Narration:** local TTS (Kokoro/Chatterbox), one locked voice per character.
- **On-screen layout:** a top text band (hook line / context) + **word-by-word karaoke captions** in the lower third (WhisperX forced-align → ASS → ffmpeg burn-in). Exact layout is configurable — confirm placement in the panel.

### 4. Music scored to scene tension/environment — ✅ free, local
- The **script LLM already emits a `mood`/tension tag per scene** (it's in the episode schema). Feed those tags to a local music generator — **MusicGen** (MIT) / **Stable Audio Open** / **ACE-Step** — to produce a mood-matched bed.
- **v0 scope:** generate one track with an arc (or a few per-section clips crossfaded) keyed to the scene moods, plus a punchy **SFX stinger on the hook** (the "slap" hit) timed via ffmpeg. Mix music at ~15–20% under the narration, then loudness-normalize.
- **Later upgrade:** true frame-synced dynamic scoring (intensity curve following the tension graph beat-for-beat). v0 = mood-matched bed + hook stinger, which already reads as "scored."

**Net: v0 runs entirely on the M5 Max for ~$0** (Opus script ~$0.08/ep). Per-video wall-clock ≈ hook clip (~5–12 min) + body/audio/assembly (~5–8 min) ≈ **~15–20 min/video**, batchable overnight.

## Upload — ⏸️ DEFERRED (async blocker; not part of the v0 build)

> v0 deliverable is the finished `final.mp4` + `caption.txt` in `ready_to_post/`. The upload module is a **stub** for now. The notes below are the reference for when the US account is live and you wire it up (or just upload manually).

**Confirmed:** **TikTok Studio (desktop, tiktok.com)** lets you **upload the MP4, set description + hashtags + cover, and schedule (up to 10 days ahead) entirely from the computer — no phone, no app.** Requires a **Creator (or Business) account**. Scheduling is desktop-only.

This means **you never need the US App Store / a phone install.** Account region is set at signup mainly by **device system locale/language (highest-weight signal) + US IP** — the App Store only matters if you install the *mobile app*. So:
- **Set the Mac's system language/region to US English / United States**, sign up to TikTok via **desktop web on US wifi** (US phone number for verification), → clean **US-region** account, no App Store involved.
- Pipeline output for v0: the final **MP4 + a `caption.txt`** (Opus-generated description + 3–5 keyword hashtags + AI-label reminder). You open TikTok Studio, drag the file, paste the caption, schedule. ~30 seconds of manual work, fully phone-free.
- **Later (optional) full auto-post:** Content Posting API *direct-post* (needs TikTok's audit) or a desktop scheduler like Postiz. Note: the API "upload to inbox/drafts" path is actually the *phone* path — so to stay phone-free, **desktop web upload is the right route**, not the API inbox.

## Optimal-schedule analysis + email "post now" notifications ✅ free

- **v0:** best-time heuristics from the algorithm research (e.g. Tue–Thu ~10am–1pm ET, 1–2/day, 3h+ apart). A local **launchd/cron job** on the Mac picks the next queued approved video and **emails you at post time**: *"Post 'Fridge Detectives Ep 7' now — file + caption attached."* Free via SMTP.
- Because TikTok Studio also **schedules** desktop uploads, you can go a step further: at approval time, upload+schedule the next batch in TikTok Studio for the optimal slots, and the email just becomes a heads-up.
- **Later:** once the account has data, pull **your own TikTok analytics** to compute *your audience's* real best times and feed that back into the scheduler (replacing the generic heuristics).

## v0 build checklist
1. Series Setup (bible + characters + reference images + voices).
2. Script via **Opus 4.8** → episode JSON (incl. per-scene mood + a `hook` spec).
3. **Hook:** LTX-Video clip (or pick from hook-clip library).
4. **Body:** FLUX/SDXL images → ffmpeg Ken Burns.
5. **Audio:** TTS narration + MusicGen mood bed + hook SFX stinger; mix + normalize.
6. **Captions:** WhisperX → ASS karaoke → burn-in; add top text band.
7. **Assemble:** ffmpeg → 9:16 spec MP4 + `caption.txt` (desc + hashtags + AI-label).
8. **Review** in the Streamlit panel (per-image re-roll, preview, QC gate) → approve.
9. **Output:** approved `final.mp4` + `caption.txt` → `ready_to_post/`. ← **v0 ends here.**
10. ⏸️ *Deferred:* TikTok upload / scheduling / email notifications (stubbed; build once US account is live).

Everything in steps 1–9 is the v0 build, runs free on the M5 Max, and is specced for engineering in [`/BUILD.md`](../BUILD.md).
