# Video Assembly / Editing / Rendering Pipeline

Research date: June 2026  
Platform target: macOS + local GPU (Apple Silicon or NVIDIA)  
Output target: TikTok ~60-second episodic AI character videos

---

## TikTok Video Format Specification

| Parameter | Specification |
|---|---|
| Resolution | 1080 × 1920 px (portrait) |
| Aspect ratio | 9:16 |
| Frame rate | 30 fps constant (preferred); 60 fps supported but compresses harder |
| Video codec | H.264 (libx264) — most compatible; H.265 works but slower to process |
| Container | MP4 (.mp4) strongly preferred; MOV also supported |
| Video bitrate | 8–15 Mbps VBR recommended; below 5 Mbps triggers TikTok quality flag; above 20 Mbps gets flattened anyway |
| Audio codec | AAC-LC |
| Audio sample rate | 44.1 kHz |
| Audio bitrate | 192–256 kbps stereo |
| Max duration (upload) | 60 minutes (pre-recorded upload); 10 minutes (in-app recording) |
| Min duration | ~3 seconds (functional minimum) |
| File size limit | 72 MB (Android app upload), ~287 MB (iOS), ~500 MB (desktop browser); up to 2 GB for TikTok for Business accounts |
| Pixel format | yuv420p (required for broad device compatibility) |

**For ~60-second episodic content**, the target is 58–62 seconds at 1080×1920, H.264, ~10 Mbps, AAC 44.1 kHz 256 kbps. That yields roughly 80–90 MB — fits desktop upload limit but exceeds Android 72 MB cap. To stay under 72 MB at 60 seconds, cap bitrate at ~9.5 Mbps.

---

## 1. Programmatic Editing Libraries

### MoviePy 2.0

**Status**: Stable release May 2025. Major breaking rewrite from 1.x.

**Key v2.0 changes** (migration-critical):
- Import path changed: `from moviepy.editor import *` is gone; use `from moviepy import VideoFileClip, ...`
- `.set_*()` methods renamed to `.with_*()` (outplace, returns modified copy): e.g. `clip.set_start(2)` → `clip.with_start(2)`
- Resize/crop/rotate are now `clip.resized()`, `clip.cropped()`, `clip.rotated()`
- Effects are now classes, not functions. Apply with `clip.with_effects([effect1, effect2])`; old `clip.fx(vfx.some_effect)` is gone
- `TextClip` now requires a font file path at construction
- Dropped: ImageMagick, PyGame, OpenCV, scipy, scikit dependencies — image manipulation now via Pillow only
- Dropped: `moviepy.video.tools.tracking`, `segmenting`, `io.sliders`
- Python 3.7+ only (dropped Python 2)

**Strengths for this pipeline**:
- Pure Python, easy to install (`pip install moviepy`)
- Handles video concatenation, audio overlay, text/image overlays, volume mixing
- `concatenate_videoclips([clip1, clip2], method="compose")` with crossfade:
  ```python
  from moviepy import VideoFileClip, concatenate_videoclips
  from moviepy.video.fx import CrossFadeIn, CrossFadeOut

  c1 = VideoFileClip("a.mp4").with_effects([CrossFadeOut(0.5)])
  c2 = VideoFileClip("b.mp4").with_effects([CrossFadeIn(0.5)])
  final = concatenate_videoclips([c1, c2], method="compose")
  ```
- Audio mixing: `CompositeAudioClip([narration.with_volume_scaled(1.0), music.with_volume_scaled(0.2)])`
- Good for prototyping; slower than raw FFmpeg for large batches

**Weaknesses**:
- Slow for long renders (Python overhead per frame)
- No hardware-accelerated encoding (always CPU encode through Pillow/FFmpeg subprocess)
- TextClip is awkward — no built-in word-level timing, requires per-word clip assembly or ASS file passthrough
- Not suitable as the sole renderer for production at scale; better used as a clip-assembly orchestrator that calls FFmpeg for the final encode

---

### FFmpeg (direct / ffmpeg-python)

**Status**: FFmpeg 7.1 LTS current; 8.0.1 latest stable (released November 2025). Actively maintained.

**ffmpeg-python** is the best Python binding — fluent API for building filter graphs, still well-maintained.

**Strengths**:
- Fastest possible local encode; hardware acceleration via `-c:v h264_videotoolbox` (Apple Silicon) or `-c:v h264_nvenc` (NVIDIA)
- `xfade` filter for clip-to-clip transitions (dissolve, fade, circleopen, pixelize, etc.)
- `zoompan` filter for Ken Burns effect on static images
- `ass` filter for burning subtitle/caption files
- `concat` demuxer or `concat` filter for multi-clip assembly
- Full control over output encoding parameters, pixel format, bitrate

**Key patterns**:

Concatenate N clips with xfade transitions (dissolve, 0.5s each):
```bash
ffmpeg \
  -i clip1.mp4 -i clip2.mp4 -i clip3.mp4 \
  -filter_complex "
    [0:v]settb=AVTB,fps=30,format=yuv420p[v0];
    [1:v]settb=AVTB,fps=30,format=yuv420p[v1];
    [2:v]settb=AVTB,fps=30,format=yuv420p[v2];
    [v0][v1]xfade=transition=dissolve:duration=0.5:offset=5.5[x01];
    [x01][v2]xfade=transition=dissolve:duration=0.5:offset=11.0[outv]
  " \
  -map "[outv]" -map 0:a \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 256k \
  output.mp4
```

Ken Burns (pan-zoom on a static image):
```bash
ffmpeg -loop 1 -i image.jpg -vf \
  "zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:fps=30,scale=1080:1920" \
  -t 5 -c:v libx264 clip_from_image.mp4
```

Burn ASS captions:
```bash
ffmpeg -i video.mp4 -vf "ass=captions.ass" -c:v libx264 -c:a copy output_captioned.mp4
```

**Weaknesses**:
- Filter graph strings become unmanageable for 15+ clips — need a Python wrapper to generate them
- No built-in "preview in browser" capability — must render to file

---

### Remotion (React-based)

**Status**: Actively maintained 2025–2026. Uses headless Chromium to render React components frame-by-frame, then stitches via FFmpeg.

**Strengths**:
- Full web tech stack — CSS animations, Lottie, SVG, canvas, any npm package
- Excellent for motion-graphics-heavy content (animated captions, overlaid graphics, character UI)
- Cloud rendering available via Remotion Lambda / Remotion Cloud
- Good local headless rendering via Node.js CLI

**Weaknesses for this pipeline**:
- Node.js + React stack is heavy if your pipeline is already Python
- Rendering speed: each frame is a browser screenshot — CPU-bound, slower than native FFmpeg encode
- GPU acceleration requires extra setup (Chromium GPU flags)
- Overkill if you just need clip stitching + captions; better suited if videos need animated UI elements

**Best use case here**: Rendering animated caption overlays or intro/outro title cards as a video layer, then compositing with FFmpeg.

---

### Revideo

**Status**: Open-source fork of Motion Canvas; actively developed 2025–2026. MIT licensed. Company monetizes via cloud rendering at re.video but self-hosted Node.js rendering is free.

**Strengths over Remotion**:
- Built specifically for automated batch video production pipelines
- Template system allows parameterized video generation
- REST API for triggering renders programmatically
- No licensing fees for self-hosted use
- Better TypeScript API for defining animated scenes

**Weaknesses**:
- TypeScript/Node.js — same language friction as Remotion if your stack is Python
- Smaller community than Remotion
- Still maturing; fewer third-party plugins

**Best use case here**: If you want polished animated caption templates or character UI cards and are comfortable with TypeScript, Revideo is the best open-source option. Otherwise, skip and use FFmpeg + ASS.

---

### Library Recommendation for This Pipeline

| Use case | Recommended tool |
|---|---|
| Final assembly & encode of all clips | **FFmpeg directly** (via ffmpeg-python or subprocess) |
| Clip preprocessing, trimming, audio mixing logic | **MoviePy 2.0** (convenient Python API) |
| Ken Burns / zoompan on AI images | **FFmpeg zoompan filter** |
| Caption burn-in | **FFmpeg + ASS subtitles** |
| Animated title cards / UI overlays | **Remotion or Revideo** (optional) |
| Prototype iteration | **MoviePy 2.0** |

---

## 2. Stitching Short Clips to 60+ Seconds

### The Problem

Most open-weights local video models output 2–6 second clips:
- **LTX-Video**: ~5s clips, ~90 sec generation on RTX 4090
- **Wan 2.1/2.2**: ~5s clips, ~4.5 min/clip on RTX 4090
- **HunyuanVideo**: ~5s clips, ~6 min/clip on RTX 4090
- **CogVideoX-5B**: ~6s clips, ~5–8 min/clip

To reach 60 seconds you need 10–30 clips depending on overlap/transitions. Generating 15 × Wan 2.1 clips = ~67 minutes of GPU time on a 4090, or ~20 minutes for LTX-Video. This is expensive and slow for a daily automated pipeline.

### Strategy A: Full Video-Gen Stitching

Generate all clips, normalize to same resolution/fps/timebase, stitch with xfade transitions.

**Key concerns**:
- **Visual continuity**: Each clip is generated independently; character appearance drifts. Mitigate with consistent image conditioning (use I2V with last frame of previous clip as seed).
- **Transition types**: dissolve (0.3–0.5s) works well between scene cuts; avoid hard cuts unless intentional for impact.
- **Audio sync**: Generate audio first; cut clips to match narration timing rather than the reverse.

**Recommended approach**:
1. Generate narration audio first (TTS)
2. Transcribe with Whisper to get word-level timestamps
3. Segment into N scene beats based on narration segments
4. Generate one video clip per scene beat (I2V with character reference)
5. Extend short clips by slowing playback 10–15% (imperceptible) or looping last frame briefly
6. Stitch with 0.4s dissolve transitions in FFmpeg xfade

**Cost**: ~20–70 minutes GPU time per 60s video depending on model and clip count.

---

### Strategy B: Static AI Images + Ken Burns Motion (Recommended for Automation)

Instead of video-gen, generate **AI images** per scene (FLUX, SDXL, etc.) and animate them with FFmpeg's `zoompan` filter to create pan-zoom motion. This is the "Ken Burns effect" approach.

**Pipeline**:
1. Generate narration audio + timestamps
2. Generate 6–12 AI images matching scene descriptions (~2–10 seconds each at generation time)
3. Convert each image to a clip with `zoompan`: slow zoom in, slow pan left/right, or zoom out
4. Add subtle motion blur and fade-in/out per clip
5. Stitch clips with FFmpeg xfade
6. Overlay narration audio + background music
7. Burn ASS captions

**Cost**:
- Image generation: ~2–5 seconds per image on RTX 4090 (FLUX Dev) or ~0.5s (SDXL)
- FFmpeg zoompan render: ~10–30 seconds per clip (CPU)
- Total per video: 1–5 minutes vs 20–70 minutes for full video-gen

**Tradeoff comparison**:

| Dimension | Full Video-Gen | Image + Ken Burns |
|---|---|---|
| GPU time per 60s video | 20–70 min | 2–5 min |
| Visual dynamism | High (motion, action) | Low-moderate (camera movement only) |
| Character consistency | Prone to drift | Stable (same image per scene) |
| Cost at scale | High (GPU hours) | Low |
| "AI video feel" | Yes | No — looks like a slideshow |
| TikTok engagement fit | Better for action content | Fine for narrated story/facts content |
| Automation complexity | Higher | Lower |

**Recommendation**: Start with image + Ken Burns for the MVP pipeline. Add video-gen clips selectively for high-impact moments (e.g., the opening 3 seconds) once the pipeline is stable.

---

## 3. Caption Rendering

### Approach: Whisper → ASS → FFmpeg burn-in

The industry-standard pipeline for word-level karaoke captions:

**Step 1 — Transcribe with Whisper (word timestamps)**:
```python
import whisper
model = whisper.load_model("base")
result = model.transcribe("narration.mp3", word_timestamps=True)
words = [w for seg in result["segments"] for w in seg["words"]]
# Each word: {"word": "hello", "start": 0.0, "end": 0.4}
```

**Step 2 — Generate ASS file with karaoke `\kf` tags**:

ASS karaoke format uses `\kf<centiseconds>` where the fill sweeps across the word progressively:
```
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H00FFFF00,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,3,1,2,80,80,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:04.50,Default,,0,0,0,,{\kf45}Hello {\kf38}world {\kf62}this {\kf40}is
```

Rules for good karaoke captions:
- Show 3–5 words at a time maximum
- Use `\kf` (progressive fill) not `\k` (hard switch) for smooth karaoke feel
- Keep font large (60–80px for 1080p), center-aligned, contrasting color
- Add `\blur4` or `\shad2` in style for legibility on busy backgrounds
- 50–100ms gap between groups of words (prevents strobe)

**Step 3 — Burn into video**:
```bash
ffmpeg -i assembled.mp4 -vf "ass=captions.ass" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p \
  -c:a copy final.mp4
```

### Alternative: MoviePy text overlays

For simpler word-by-word highlighting without ASS:
```python
from moviepy import TextClip, CompositeVideoClip

word_clips = []
for word_info in words:
    txt = TextClip(
        font="/path/to/font.ttf",
        text=word_info["word"],
        font_size=72,
        color="white"
    ).with_start(word_info["start"]).with_end(word_info["end"])
    word_clips.append(txt)

final = CompositeVideoClip([base_video] + word_clips)
```

This works but is slow for long videos — ASS + FFmpeg is faster and gives better visual control.

### Libraries that automate the Whisper → ASS flow

- **auto-subtitle** (GitHub): generates SRT/ASS from audio files using Whisper
- **stable-ts**: Whisper wrapper with more accurate word timestamps and ASS export
- **WhisperX**: batched Whisper with forced alignment for more precise word boundaries

---

## 4. Orchestration

### Recommended Pipeline Architecture

```
[Script LLM] 
    → scene_descriptions[] + narration_text
    → TTS engine (Kokoro, ElevenLabs, Bark)
    → narration.mp3

[Whisper transcribe narration.mp3]
    → word_timestamps.json

[Image generator per scene] (FLUX/SDXL per scene_description)
    → scene_images/scene_00.png ... scene_N.png

[Clip maker per image] (FFmpeg zoompan)
    → clips/clip_00.mp4 ... clip_N.mp4
    (OR video generator: Wan/LTX/CogVideoX per scene)

[Music selector/generator]
    → background_music.mp3

[Assembler]
    → FFmpeg xfade stitch clips
    → Mix narration + music (narration 100%, music 15–20%)
    → Burn ASS captions
    → Output: draft.mp4 (1080x1920, H.264, ~60s)

[Human approval step]
    → Preview served → Approve/Reject
    → If approved: upload to TikTok via API or folder drop

[TikTok upload]
```

### Python Orchestration Options

**Option A: Sequential Python script (simplest)**

A single `pipeline.py` with functions for each stage, called in order. No job queue needed for single-machine use. Add `logging` and intermediate file persistence (save each stage output to disk) so stages can be re-run on failure.

Good enough for: 1–5 videos/day, single machine.

**Option B: Celery + Redis (scalable)**

- Celery 5.6.x (latest stable 2026) with Redis as broker
- Each stage is a Celery task; chain them with `canvas.chain()`
- Allows parallel image generation across GPU workers
- Web dashboard via Flower for monitoring
- Supports retry on failure, soft/hard time limits

Good for: batch production (10+ videos/day), multi-GPU machines.

```python
from celery import chain

workflow = chain(
    generate_images.s(script),       # parallel group possible
    generate_clips.s(),
    assemble_video.s(),
    render_captions.s(),
    queue_for_review.s()
)
result = workflow.apply_async()
```

**Option C: ComfyUI API**

ComfyUI has a REST API (`/queue`, `/history`) that can be called from Python to submit image/video generation jobs. Useful if you're already using ComfyUI for visual generation. Limitations: the ComfyUI job queue is single-threaded per instance; no built-in stage chaining outside the node graph.

---

## 5. Existing Open-Source "AI Faceless Video" Projects

### MoneyPrinterTurbo
- **GitHub**: github.com/harry0703/MoneyPrinterTurbo
- **Stars**: Very active (2025–2026)
- **What it does**: End-to-end pipeline: topic → LLM script → stock video sourcing (Pexels/Pixabay) → TTS voiceover → Whisper subtitles → MoviePy/FFmpeg assembly → output MP4
- **Tech stack**: Python 3.11, MoviePy 2.x, FFmpeg, Streamlit (web UI), FastAPI (REST API), multiple LLM providers
- **Formats**: 9:16 (TikTok/Shorts) and 16:9 (YouTube)
- **Limitations**:
  - Uses stock footage, not AI-generated character video
  - Character consistency not a feature (different stock clips per scene)
  - Whisper model download (~3 GB) required for subtitles
  - No approval/review step built in
  - Minimum 4 CPU cores, 8+ GB VRAM recommended for local use

### ShortGPT
- **GitHub**: github.com/RayVentura/ShortGPT
- **Stars**: ~7,400; maintained as of Feb 2025 (v0.3.0 added Gemini support)
- **What it does**: LLM script generation + ElevenLabs/EdgeTTS voiceover + Pexels/Bing image sourcing + caption generation + MoviePy-based rendering. Three engines: shorts, long-form video, translation/dubbing.
- **Tech stack**: Python, MoviePy, OpenAI, TinyDB
- **Limitations**:
  - Experimental, documentation sparse
  - No AI video generation (uses stock/Bing images)
  - No built-in human approval step
  - 74 open issues; not production-grade
  - Docker setup required

### AI-Youtube-Shorts-Generator (SamurAIGPT)
- **GitHub**: github.com/samuraigpt/ai-youtube-shorts-generator
- **What it does**: Converts long YouTube videos into 9:16 shorts using LLM highlight detection, Whisper transcription, auto vertical cropping. Not a generation pipeline — a repurposing tool.
- **Limitations**: Repurposing only, not generative.

### What These Projects Lack (vs. this pipeline's needs)
- None generate AI character images/video — they rely on stock footage
- None have character consistency or story continuity across clips
- None have a built-in human approval step
- MoneyPrinterTurbo is the closest reference implementation; borrow its MoviePy/FFmpeg assembly patterns and Streamlit UI structure

---

## 6. Human Approval Step

### Recommended: Streamlit Preview UI + Approval Flag

Build a lightweight Streamlit app that:
1. Watches an output folder for new `draft_*.mp4` files
2. Shows the video in a `st.video()` player
3. Displays metadata: scene count, duration, script text, captions preview
4. "Approve" button → moves file to `approved/` folder and triggers upload task
5. "Reject" + text field → moves to `rejected/` folder with notes, optionally re-queues with edits

```python
import streamlit as st
import os, shutil

draft_dir = "/video-gen/output/drafts"
approved_dir = "/video-gen/output/approved"

drafts = sorted(f for f in os.listdir(draft_dir) if f.endswith(".mp4"))
if drafts:
    selected = st.selectbox("Draft videos:", drafts)
    st.video(os.path.join(draft_dir, selected))
    col1, col2 = st.columns(2)
    if col1.button("Approve"):
        shutil.move(os.path.join(draft_dir, selected), approved_dir)
        st.success("Approved!")
    notes = st.text_input("Rejection notes")
    if col2.button("Reject"):
        shutil.move(os.path.join(draft_dir, selected), "/video-gen/output/rejected/")
        st.warning("Rejected")
```

Run with: `streamlit run review.py` — opens at localhost:8501.

### Alternative: Telegram Bot

For mobile-first approval (away from desk):
1. Pipeline sends draft video to Telegram bot chat via `python-telegram-bot`
2. Bot presents inline keyboard: [Approve] [Reject] [Request Edit]
3. On approval, bot calls back to a FastAPI endpoint that moves the file and queues upload
4. n8n can wire this workflow visually if you prefer no-code orchestration

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

async def send_for_review(video_path: str, chat_id: str, bot_token: str):
    app = Application.builder().token(bot_token).build()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve:{video_path}"),
         InlineKeyboardButton("Reject", callback_data=f"reject:{video_path}")]
    ])
    async with app:
        await app.bot.send_video(
            chat_id=chat_id,
            video=open(video_path, "rb"),
            caption="Draft ready for review",
            reply_markup=keyboard
        )
```

### Comparison

| Method | Best for | Pros | Cons |
|---|---|---|---|
| Streamlit web UI | Desktop review | Full video preview, rich UI, easy to build | Requires opening browser, local only |
| Telegram bot | Mobile review | Approve from phone, push notification, persistent | Video size limits (50 MB Telegram cap), need bot setup |
| Discord bot | Team review | Shared channel, reactions as approval | Similar size limits, more complex auth |
| Folder drop + watch | Fully automated | No UI needed | No review — skips the human step |

**Recommendation**: Start with Streamlit for the MVP (simplest, full video preview). Add Telegram bot later for mobile convenience. Note: Telegram's 50 MB bot upload limit means you may need to send a lower-bitrate preview (e.g., 3 Mbps, ~22 MB for 60s) and upload the full-quality version separately on approval.

---

## Recommended Toolchain Summary

| Stage | Tool |
|---|---|
| Script generation | LLM (Claude/GPT/local) |
| TTS narration | Kokoro (free, local) or ElevenLabs |
| Word-level timestamps | WhisperX or stable-ts |
| AI image generation | FLUX Dev (local) or SDXL |
| Image → clip (Ken Burns) | FFmpeg zoompan filter |
| AI video generation (optional) | Wan 2.1 or LTX-Video via ComfyUI |
| Clip stitching + transitions | FFmpeg xfade filter |
| Audio mixing | FFmpeg amix filter |
| Caption generation (ASS) | stable-ts → custom ASS writer |
| Caption burn-in | FFmpeg ass filter |
| Pipeline orchestration | Python + Celery/Redis (or sequential script for MVP) |
| Human approval UI | Streamlit (local) + optional Telegram bot |
| Final encode | FFmpeg libx264, 1080x1920, 30fps, ~10 Mbps, yuv420p |

---

## References

- [MoviePy PyPI](https://pypi.org/project/moviepy/)
- [MoviePy v2.0 Migration Guide](https://zulko.github.io/moviepy/getting_started/updating_to_v2.html)
- [Remotion](https://www.remotion.dev/)
- [Revideo vs Remotion vs Motion Canvas (2026)](https://www.pkgpulse.com/blog/remotion-vs-motion-canvas-vs-revideo-programmatic-video-2026)
- [TikTok Video Sizes Guide 2025 (BigMotion)](https://www.bigmotion.ai/blog/the-ultimate-guide-to-tiktok-video-size)
- [TikTok Video Sizes 2025 (StackInfluence)](https://stackinfluence.com/tiktok-video-sizes-the-ultimate-2025-guide/)
- [FFmpeg xfade filter (OTTVerse)](https://ottverse.com/crossfade-between-videos-ffmpeg-xfade-filter/)
- [Ken Burns Effect with FFmpeg (Bannerbear)](https://www.bannerbear.com/blog/how-to-do-a-ken-burns-style-effect-with-ffmpeg/)
- [MoneyPrinterTurbo GitHub](https://github.com/harry0703/MoneyPrinterTurbo)
- [ShortGPT GitHub](https://github.com/RayVentura/ShortGPT)
- [Karaoke Caption Guide (VidNo)](https://vidno.ai/blog/karaoke-style-word-highlight-captions)
- [FFmpeg Subtitle Burn-in](https://www.mpegflow.com/recipes/burn-captions-into-video)
- [Celery + Redis Production Guide 2025](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7)
- [Local AI Video Generation 2026 (LocalAIMaster)](https://localaimaster.com/blog/local-ai-video-generation)
- [Image-to-Video GPU Cloud Comparison 2026 (Spheron)](https://www.spheron.network/blog/image-to-video-gpu-cloud-ltx-wan-hunyuan/)
