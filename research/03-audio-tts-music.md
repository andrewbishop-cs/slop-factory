# Audio + Captions Layer Research
## For TikTok AI Character Video Pipeline (1-minute episodic format)

*Research date: June 2026. Focuses on locally-runnable open tools with commercial-viability notes.*

---

## 1. Text-to-Speech (TTS) — Local Models

### 1.1 Model Comparison Table

| Model | Params | VRAM | Speed (RTF) | Voice Cloning | License | Commercial OK? |
|-------|--------|------|-------------|----------------|---------|----------------|
| **Kokoro-82M** | 82M | <1 GB | 0.03 (36× RT on T4) | No — preset voices only (54 voices) | Apache 2.0 | Yes |
| **Piper** | ~few M | <100 MB | 0.008 (CPU real-time) | No — pre-trained voices | MIT | Yes |
| **StyleTTS 2** | ~100M | 2–4 GB | ~5–8× RT on RTX 4070 | Zero-shot via style ref | MIT | Yes |
| **Fish Speech 1.5** | ~500M | ~4 GB | ~8× RT | Yes — 10–30s ref (no fine-tune) | Code: Apache 2.0; Weights: CC-BY-NC-SA 4.0 | **No** (weights) |
| **F5-TTS** | ~335M | ~4–6 GB | ~3–5× RT on RTX 4070 | Yes — zero-shot, ~3s ref | CC-BY-NC 4.0 | **No** |
| **XTTS v2** | 467M | ~4 GB | ~2× RT | Yes — zero-shot, 6s ref, 17 langs | CPML (Coqui shut down Jan 2024) | **Unclear/risky** |
| **Bark (Suno)** | ~1B (large) | 12 GB (large), 4 GB (small) | ~0.3× RT (slow) | Speaker presets + voice conditioning | MIT | Yes |
| **Chatterbox (Resemble AI)** | ~500M | ~6–8 GB | ~4× RT | Yes — zero-shot, few seconds ref | MIT | Yes |
| **Chatterbox Turbo** | — | — | Real-time | Yes | MIT | Yes |
| **OpenVoice v2** | — | ~4–6 GB | Moderate | Yes — 1–5s ref, tone/emotion control | MIT (since Apr 2024) | Yes |
| **Dia-1.6B (Nari Labs)** | 1.6B | 10+ GB | ~40 tok/s on A4000 | Yes + nonverbals (laughs, coughs) | Apache 2.0 | Yes |

**RTF = Real-Time Factor. RTF 0.03 = generates 1s of audio in 0.03s (≈33× faster than real-time).**

### 1.2 Quality Notes (2026 Landscape)

- **Kokoro-82M** topped the TTS Arena leaderboard in early 2025, beating XTTS (467M) and MetaVoice (1.2B) on a blind evaluation despite being 5–15× smaller. It's the go-to for fast, CPU-friendly, no-cloning deployment. Weakness: slightly "stilted" delivery; no voice cloning.
- **F5-TTS** is widely considered the best *overall* for quality + cloning: non-autoregressive flow-matching diffusion transformer, low WER, strong emotion retention, clones from ~3 seconds. However its CC-BY-NC 4.0 license blocks commercial use.
- **Chatterbox** (MIT) from Resemble AI is the recommended commercial voice-cloning default as of mid-2025. Multilingual Chatterbox supports 23 languages. Every generated file includes an imperceptible Perth watermark.
- **Dia-1.6B** is purpose-built for multi-speaker dialogue — it uses `[S1]` / `[S2]` tags and generates natural turn-taking with distinct voices from a single model pass. It also generates nonverbal sounds natively (laughs, coughs, sighs), which is powerful for character personality. Apache 2.0 license. Needs a 10GB+ VRAM GPU.
- **Bark**: MIT licensed, good for emotional expressiveness and nonverbals, but very slow (0.3× RT) and VRAM-hungry (12GB full). Use Bark small (4GB) as a fallback. Best for quirky/expressive voices where speed isn't critical.
- **XTTS v2**: Historically the gold standard for zero-shot cloning. Coqui shut down Jan 2024, and the CPML license has no active commercial licensing path. **Avoid for commercial use.** Use Fish Speech or Chatterbox instead.
- **Fish Speech weights** are CC-BY-NC-SA 4.0 — also not commercially safe.

### 1.3 Recommended Local Stack for This Project

**Primary recommendation: Dia-1.6B for dialogue-heavy character interactions.**

- Use `[S1]` / `[S2]` speaker tags within a single model — perfect for two recurring characters conversing.
- Apache 2.0: safe for commercial TikTok monetization.
- Nonverbal sounds (laughs, gasps) add personality automatically.
- Requires 10+ GB VRAM. If GPU is limited, see fallback below.

**Lightweight fallback (< 4GB VRAM or CPU): Kokoro-82M**

- Apache 2.0, 82M params, runs on T4 or CPU.
- No voice cloning, but 54 built-in voices — assign one fixed voice per character and keep it consistent across episodes.
- Extremely fast: 36× real-time on T4.

**If zero-shot voice cloning is critical and commercial use is needed: Chatterbox (MIT)**

- Clone each character's voice once from a 5–10 second reference recording.
- Store the reference audio per character and reuse it every episode.
- Multilingual, 23 languages.

**OpenVoice v2 (MIT) as tone-control layer:**

- Can be used on top of another TTS to post-process: adjust emotion, accent, rhythm.
- Good for giving an existing voice a specific emotional register per scene.

---

## 2. Distinct Character Voices for Episodic Series

For recurring characters in a multi-episode format, consistency is the key constraint. Two approaches:

### 2.1 Voice Preset Approach (Kokoro / Piper)
- Assign a fixed named voice (e.g., Kokoro voice ID `af_heart` for Character A, `am_adam` for Character B).
- Zero variance — the voice is identical every episode. Predictable but no room to match a specific personality.
- Recommended for rapid iteration and CPU-only pipelines.

### 2.2 Reference-Audio Cloning Approach (Chatterbox / OpenVoice v2 / Dia)
- Record (or synthesize once) a 5–30 second "ground truth" reference clip for each character.
- Store as `characters/char_a/reference.wav`, `characters/char_b/reference.wav`.
- Pass the reference at inference time: each character's voice is cloned from that anchor.
- **Ensures inter-episode consistency** as long as the same reference is used.
- With Dia-1.6B: provide the reference audio as conditioning for each speaker tag.
- With Chatterbox: pass `--reference characters/char_a/reference.wav` per generation call.

### 2.3 Fine-Tuning for Maximum Consistency
- If you have 10–60 minutes of labelled speech for a character (or a voice actor), fine-tuning F5-TTS/E2-TTS achieves MOS ~4.1+ and near-perfect speaker identity. Community benchmarks (SpeechRole Aug 2025) confirm E2-TTS and F5-TTS as top fine-tuning targets.
- **For commercial use**, fine-tune Chatterbox instead (MIT) or Kokoro-derived models with Kokoro's Apache 2.0 codebase.

### 2.4 Metadata / Config Pattern
```yaml
characters:
  narrator:
    tts_model: kokoro
    voice_id: af_heart
    speed: 1.0
  character_a:
    tts_model: chatterbox
    reference_audio: ./voices/char_a_ref.wav
    emotion: playful
  character_b:
    tts_model: dia
    speaker_tag: "[S2]"
    reference_audio: ./voices/char_b_ref.wav
```

---

## 3. Lip-Sync (Optional)

### 3.1 Is Lip-Sync Needed?

For **2D animated / illustrated anthropomorphic characters** (the typical TikTok AI character format), full realistic lip-sync is generally **not needed or appropriate**. These characters typically use:
- A 2–3 frame "open/closed mouth" cycle keyed to audio amplitude (simple and effective).
- Pre-drawn talking poses switched on beat/word boundaries.
- The character's face is expressive but doesn't attempt photorealistic lip-sync.

Realistic lip-sync tools (Wav2Lip, MuseTalk, LatentSync) are designed for **photorealistic human faces** — applying them to illustrated characters looks wrong.

**Skip lip-sync unless your characters are photorealistic 3D/rendered faces.**

### 3.2 Tools (For Reference / Photorealistic Characters)

| Tool | License | VRAM | Quality | Best For |
|------|---------|------|---------|----------|
| **MuseTalk 1.5** | MIT | ~8 GB | High (diffusion-based, sharp lips) | Video footage, real-time 30fps |
| **LatentSync 1.5** (ByteDance) | Apache 2.0 | ~8–10 GB | Very high, good identity preservation | High-quality renders |
| **Wav2Lip** | MIT | ~4 GB | Good sync, slightly blurry lips | Fast, zero-shot on any video |
| **SadTalker** | MIT | ~4–6 GB | Full head motion from still photo | Single-image talking head |

- **MuseTalk 1.5** (MIT, Tencent): Training code open-sourced Apr 2025. Best free option for photorealistic 30fps lip-sync. Works on video clips.
- **LatentSync 1.5** (Apache 2.0, ByteDance, Mar 2025): Works in latent space for faster inference + identity preservation. Strong for pre-rendered 3D character clips.
- **SadTalker** (MIT): Generates full head motion from a single photograph. Useful if your character is a static illustrated portrait that needs to "come alive."
- **Wav2Lip**: The classic. Best sync accuracy, weakest visual quality. Good for rapid prototyping.

**Recommendation for this project:** Skip lip-sync for 2D illustrated characters. If using 3D/photorealistic character renders, use LatentSync 1.5 or MuseTalk 1.5.

---

## 4. Background Music + SFX

### 4.1 Critical Copyright Note for TikTok Monetization

**Using popular commercial songs on TikTok almost always blocks monetization.**

TikTok's July 2025 policy update enforces strict music licensing. Key rules:
- **Personal/organic posts**: You can use some licensed music from TikTok's library, but monetization eligibility is stripped.
- **Commercial content** (brand promotions, sponsored posts, Creator Fund-eligible videos): Must use TikTok's **Commercial Music Library (CML)** or wholly owned/licensed music.
- **Recurring copyright violations** lead to strikes and permanent bans.
- Content ID-style detection catches copyrighted audio even in background.

**For a monetized episodic series, you need either:**
1. AI-generated music (owned by you, no copyright issues), or
2. Licensed royalty-free music from a platform with TikTok commercial clearance.

### 4.2 Local AI Music Generation

| Model | License | VRAM | Output | Notes |
|-------|---------|------|--------|-------|
| **ACE-Step 1.5** | Code: Apache 2.0; Weights: StepFun proprietary (verify current terms) | <4 GB | Full song, vocals optional | Best local option; <10s on RTX 3090; LoRA fine-tuning from a few songs |
| **ACE-Step 1.5 XL** | Same | ~8–12 GB | Higher quality | 4B DiT, released Apr 2026 |
| **MusicGen (Meta)** | MIT | ~4–8 GB | Up to ~30s per prompt | Text-to-music, no vocals; music weights MIT = commercially usable |
| **YuE (m-a-p)** | Apache 2.0 | ~16 GB (7B model) | Full songs with vocals | Lyrics-to-song; first open-source model at commercial Suno quality level |
| **Stable Audio Open 1.0** | Stability AI Community License (not Apache) | 8–12 GB | Up to 47s stereo @ 44.1 kHz | Good for SFX and loops; NC restrictions may apply |
| **AudioCraft / MusicGen** | MIT | 4 GB (small), 8 GB (large) | Loops/stems | Meta's AudioCraft fork with stereo + longer gen |

**Recommended local music stack:**

1. **ACE-Step 1.5** — best quality, <4GB VRAM, runs on a gaming GPU. Use text prompts to generate 60-second background loops matching episode mood. Verify model-weight license terms before commercial release.
2. **MusicGen (MIT)** — safest license. Generate 30s loops, loop them. Use for background underscore tracks.
3. **YuE (Apache 2.0)** — if you want themed songs with vocals for intro/outro. Needs a beefy GPU (7B model).

**For SFX**: Use Stable Audio Open (great for sound design) or curated CC0/public-domain SFX libraries (Freesound.org CC0 filter, BBC Sound Effects Archive).

### 4.3 Licensed Royalty-Free Music Services (Cloud Fallback)

| Service | Cost | TikTok Commercial Coverage |
|---------|------|---------------------------|
| **Epidemic Sound** | $17.99/mo (personal), $59.99/mo (commercial) | Yes — covers both organic and paid TikTok ads |
| **Artlist** | ~$15/mo (social plan) or ~$20/mo (pro) | Yes — universal license, worldwide, perpetual per download |
| **TikTok Commercial Music Library** | Free (in-app) | Yes — specifically cleared for commercial TikTok use |

For a low-budget pipeline, generate music locally with MusicGen/ACE-Step and use the TikTok CML for any premium track needs.

---

## 5. Captions / Subtitles — TikTok-Style Word-by-Word

### 5.1 Why This Matters

"Bouncing word-by-word karaoke captions" are one of the highest-engagement features on TikTok. They:
- Increase watch time (viewers follow along).
- Enable silent-mode viewing (common on TikTok).
- Are expected by TikTok's native auto-caption format.

### 5.2 Pipeline Overview

```
TTS audio output
       ↓
  WhisperX (forced alignment)
       ↓
  Word-level timestamps JSON
       ↓
  Caption renderer (ASS/FFmpeg or pycaps)
       ↓
  Burned-in video with styled word-highlight captions
```

### 5.3 Step 1 — WhisperX for Word-Level Timestamps

**WhisperX** (MIT license) extends OpenAI Whisper with wav2vec2 forced phoneme alignment for ±50ms word-level accuracy (vs ±500ms in vanilla Whisper).

**Why not vanilla Whisper?** Whisper's built-in timestamps are at segment level (~sentence chunks), not word level. For karaoke highlighting you need per-word start/end times.

**Since TTS is your audio source**, you already know the transcript. WhisperX's forced alignment mode is the most efficient path — pass the known transcript + audio and get back per-word timestamps. No transcription step needed.

```python
import whisperx

# Load alignment model once (stores to disk, ~200MB)
model_a, metadata = whisperx.load_align_model(
    language_code="en", device="cuda"
)

# Forced alignment (transcript already known from TTS)
segments = [{"text": full_script}]
result = whisperx.align(
    segments, model_a, metadata, audio, device="cuda"
)

# word_segments contains: {"word": "Hello", "start": 0.12, "end": 0.34}
word_segments = result["word_segments"]
```

**Output format**: each word has `start`, `end` in seconds — fed directly into caption renderer.

**Alternative**: `stable-ts` (MIT) — another Whisper wrapper with word-level timestamps, simpler API, also works as a forced-aligner.

### 5.4 Step 2 — Rendering Styled Captions

#### Option A: ASS Subtitles + FFmpeg (Most Control)

ASS (Advanced SubStation Alpha) supports karaoke timing natively via `\kf` tags.

**Format**: `{\kf43}Hello {\kf52}world` — `\kf43` means the word takes 430ms to fill.

Build the ASS file programmatically from WhisperX word timestamps:

```python
def words_to_ass(word_segments, style="karaoke"):
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H00FFFF00,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,0,2,10,10,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Group words into caption lines (e.g., 4–5 words)
    lines = []
    for i in range(0, len(word_segments), 4):
        chunk = word_segments[i:i+4]
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        
        # Build karaoke text with \kf tags
        kara_text = ""
        for j, w in enumerate(chunk):
            dur_cs = int((w["end"] - w["start"]) * 100)  # centiseconds
            kara_text += f"{{\\kf{dur_cs}}}{w['word']} "
        
        start_str = format_ass_time(start)
        end_str = format_ass_time(end)
        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{kara_text.strip()}")
    
    return ass_header + "\n".join(lines)
```

Burn into video:
```bash
ffmpeg -i video.mp4 -vf "ass=captions.ass" -c:a copy output_captioned.mp4
```

#### Option B: pycaps (Python Library, CSS-Styled)

`pycaps` (GitHub: francozanardi/pycaps) is a Python library for CSS-styled animated subtitles. Designed for TikTok/Shorts/Reels. Handles word-level highlighting with configurable styles.

```bash
pip install pycaps
```

More declarative than raw ASS, but less low-level control.

#### Option C: tiktokcaptions (PyPI)

`pip install tiktokcaptions` — wraps Whisper + OpenCV for TikTok-style captions. Simpler but less configurable.

### 5.5 TikTok Caption Style Best Practices (2025)

- **Font**: Bold, sans-serif. Arial Black, Impact, or Montserrat ExtraBold work well.
- **Size**: Large — at least 60–80px on a 1080×1920 frame. Viewers watch on phones.
- **Color scheme**: White text, black outline (3–4px), with **yellow or cyan fill for active word**.
- **Position**: Center screen, lower third (about 70–80% down the frame).
- **Chunk size**: 3–5 words per line. Never more than one line visible at a time.
- **Active word highlight**: The word currently being spoken gets a fill color change or scale-up animation (`\kf` karaoke fill in ASS, or CSS color transition in pycaps).
- **Background**: Semi-transparent dark pill/rectangle behind each line for legibility over busy backgrounds.

### 5.6 Automated Caption Pipeline Code Sketch

```python
# Full automated caption pipeline
import whisperx
import subprocess

def generate_captioned_video(video_path, audio_path, transcript, output_path):
    # 1. Load WhisperX alignment model (cached after first run)
    model_a, metadata = whisperx.load_align_model("en", "cuda")
    audio = whisperx.load_audio(audio_path)
    
    # 2. Forced alignment (transcript known from TTS)
    result = whisperx.align(
        [{"text": transcript}], model_a, metadata, audio, "cuda"
    )
    words = result["word_segments"]
    
    # 3. Generate ASS file
    ass_content = words_to_ass(words)
    with open("/tmp/captions.ass", "w") as f:
        f.write(ass_content)
    
    # 4. Burn captions into video
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", "ass=/tmp/captions.ass",
        "-c:a", "copy",
        output_path
    ])
```

---

## 6. Loudness / Format Norms for TikTok

### 6.1 Target Specification

| Parameter | Target | Notes |
|-----------|--------|-------|
| **Integrated loudness** | −14 LUFS | ITU-R BS.1770-4. TikTok's normalization target. |
| **True peak** | −1.0 to −1.5 dBTP | Prevents clipping after AAC encode. Use −1.5 to be safe. |
| **Loudness range (LRA)** | 7–11 LU | Typical for speech-forward content. |
| **Audio codec** | AAC-LC | TikTok's preferred codec. |
| **Sample rate** | 44.1 kHz | Standard. |
| **Bitrate** | 256 kbps stereo | Recommended for quality retention after upload compression. |
| **Channels** | Stereo | TikTok renders stereo; mono centered works but stereo is preferred. |

**Note**: There is some debate about whether TikTok normalizes on playback like YouTube/Spotify do. The safest approach is to deliver at exactly −14 LUFS so the platform makes no adjustments. Some creators intentionally master slightly hotter to stand out — but this risks distortion post-encode.

### 6.2 FFmpeg Normalization Commands

**Quick one-pass normalization:**
```bash
ffmpeg -i input.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  output_normalized.wav
```

**Two-pass (more accurate, recommended for production):**
```bash
# Pass 1: measure
ffmpeg -i input.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json \
  -f null /dev/null 2>&1 | tail -n 12 > loudnorm_stats.json

# Pass 2: apply (substitute measured_I, measured_TP, measured_LRA from JSON)
ffmpeg -i input.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=-18.3:measured_TP=-2.1:measured_LRA=8.2:linear=true" \
  output_normalized.wav
```

**Python wrapper (recommended for pipeline integration):**
```bash
pip install ffmpeg-normalize
ffmpeg-normalize input.mp4 -o output.mp4 -t -14 --true-peak -1.5
```

### 6.3 Audio Mixdown Order

For the final 1-minute video audio:

1. **TTS voice track(s)** — highest priority, sit at 0 dB reference.
2. **Background music** — duck to −12 to −18 dB relative to voice. Use a sidechain/ducking filter (`sidechaincompress`) or simply set fixed music level to ~20% of voice.
3. **SFX** — situational; match perceptual loudness to voice.
4. **Master loudnorm** to −14 LUFS after mixdown.

```bash
# Example FFmpeg mixdown: voice + ducked music
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "[1:a]volume=0.15[bg]; [0:a][bg]amix=inputs=2:duration=first[mix]; [mix]loudnorm=I=-14:TP=-1.5[out]" \
  -map "[out]" mixed_audio.wav
```

---

## 7. Cloud TTS Fallback Options

If local compute is unavailable or voice quality needs to be higher for certain scenes:

| Service | Pricing | Voice Cloning | Notes |
|---------|---------|---------------|-------|
| **ElevenLabs** | Free: 10K chars/mo; Starter $5/mo (30K); Creator $22/mo (100K); Pro $99/mo (500K) | Yes — instant voice cloning | Best quality (~4.8 MOS). ~$0.15–0.20/min on paid plans. |
| **OpenAI TTS (tts-1)** | $15 per 1M characters | No | Fast, decent quality. |
| **OpenAI TTS HD (tts-1-hd)** | $30 per 1M characters | No | Higher quality, slower. |
| **OpenAI gpt-4o-mini-tts** | $0.60/1M input tokens + $12/1M audio tokens (~$0.015/min) | Voice instructions via prompt | Most expressive OpenAI TTS option. 2K token input limit. |

**Cost estimate for 1-minute video** (~1,000 words / ~6,000 characters of TTS):
- ElevenLabs Creator plan: ~0.06 minutes of the 100K/month budget — very affordable.
- OpenAI tts-1: ~$0.09 per video at list price.
- Local (Kokoro/Chatterbox): ~$0.00 marginal cost, only electricity.

---

## 8. Recommended Local Stack Summary

```
┌─────────────────────────────────────────────────────────────────┐
│              RECOMMENDED AUDIO PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TTS (character voices)                                         │
│  ├── GPU ≥10GB:  Dia-1.6B (Apache 2.0)                         │
│  │                [S1]/[S2] tags, nonverbals, Apache 2.0        │
│  ├── GPU 4–8GB:  Chatterbox (MIT) with per-character refs       │
│  └── CPU/low:   Kokoro-82M (Apache 2.0) with preset voices     │
│                                                                 │
│  Tone post-processing (optional)                                │
│  └── OpenVoice v2 (MIT) for emotion/accent adjustment           │
│                                                                 │
│  Background Music                                               │
│  ├── Local gen:  ACE-Step 1.5 (Apache code; verify weights)     │
│  │               or MusicGen MIT for cleanest license            │
│  └── Licensed:  Epidemic Sound / Artlist ($15–20/mo)            │
│                                                                 │
│  SFX                                                            │
│  └── Stable Audio Open or Freesound.org (CC0 filter)           │
│                                                                 │
│  Captions                                                       │
│  ├── Alignment:  WhisperX (MIT) forced-align on TTS audio       │
│  └── Render:     ASS + FFmpeg (karaoke \kf tags)                │
│                  or pycaps Python library                        │
│                                                                 │
│  Loudness                                                       │
│  └── ffmpeg-normalize to −14 LUFS / −1.5 dBTP                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. License Risk Summary

| Tool | License | Commercial TikTok Series Safe? |
|------|---------|-------------------------------|
| Kokoro-82M | Apache 2.0 | Yes |
| Piper | MIT | Yes |
| Chatterbox / Chatterbox Turbo | MIT | Yes |
| OpenVoice v2 | MIT (since Apr 2024) | Yes |
| Dia-1.6B | Apache 2.0 | Yes |
| Bark (Suno) | MIT | Yes |
| StyleTTS 2 | MIT | Yes |
| F5-TTS | CC-BY-NC 4.0 | **No** |
| XTTS v2 | CPML (Coqui defunct) | **No / unclear** |
| Fish Speech (weights) | CC-BY-NC-SA 4.0 | **No** |
| MusicGen weights | MIT | Yes |
| YuE | Apache 2.0 | Yes |
| ACE-Step (code) | Apache 2.0 | Yes (verify weights separately) |
| Stable Audio Open | Stability AI Community License | Check — may restrict commercial |
| WhisperX | MIT | Yes |
| MuseTalk 1.5 | MIT | Yes |
| LatentSync 1.5 | Apache 2.0 | Yes |
| Wav2Lip | MIT | Yes |

---

## Sources

- [Best TTS Models 2026 — CodeSOTA](https://www.codesota.com/guides/tts-models)
- [Choosing the Best TTS Models: F5-TTS, Kokoro, SparkTTS, Sesame CSM — DigitalOcean](https://www.digitalocean.com/community/tutorials/best-text-to-speech-models)
- [12 Best Open-Source TTS Models Compared — Inferless](https://www.inferless.com/learn/comparing-different-text-to-speech---tts--models-part-2)
- [Kokoro TTS v1.0 — AI Innovation Hub](https://aiinovationhub.com/kokoro-tts-v1-0-offline-open-source/)
- [Chatterbox Open Source TTS — Resemble AI](https://www.resemble.ai/chatterbox/)
- [Chatterbox Turbo](https://www.resemble.ai/chatterbox-turbo/)
- [Fish Speech GitHub](https://github.com/fishaudio/fish-speech)
- [OpenVoice v2 — myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice)
- [Dia-1.6B TTS — APIdog](https://apidog.com/blog/how-to-run-dia-1-6b-locally-the-open-source-contender-to-eleven-labs/)
- [Local TTS and Voice Cloning 2026 — PromptQuorum](https://www.promptquorum.com/power-local-llm/local-tts-voice-cloning-piper-coqui-xtts)
- [Bark TTS Benchmark — Salad](https://blog.salad.com/bark-benchmark-text-to-speech/)
- [XTTS-v2 Commercial License Discussion](https://github.com/coqui-ai/TTS/discussions/4304)
- [ElevenLabs Pricing 2026 — BIGVU](https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs/)
- [OpenAI TTS Pricing](https://openai.com/api/pricing/)
- [5 Best Open-Source Lip Sync Tools 2026 — lipsync.com](https://lipsync.com/blog/open-source-lip-sync)
- [MuseTalk GitHub](https://github.com/TMElyralab/MuseTalk)
- [LatentSync Review 2026 — ReviewNexa](https://reviewnexa.com/latentsync-review/)
- [ACE-Step GitHub](https://github.com/ace-step/ACE-Step)
- [ACE-Step 1.5 GitHub](https://github.com/ace-step/ACE-Step-1.5)
- [YuE GitHub](https://github.com/multimodal-art-projection/YuE)
- [MusicGen MIT license — ToolMage](https://www.toolmage.com/en/tool/musicgen/)
- [Stable Audio 3.0 — MindStudio](https://www.mindstudio.ai/blog/stable-audio-3-open-weight-music-generation-content-creators)
- [TikTok 2025 Music Licensing Changes — LegisMusic](https://legismusic.com/tiktoks-july-2025-music-licensing-changes)
- [TikTok Commercial Use of Music — TikTok Support](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/commercial-use-of-music-on-tiktok)
- [Epidemic Sound Pricing](https://www.epidemicsound.com/pricing/)
- [Artlist vs Epidemic Sound 2025](https://sites.google.com/site/videoblocksreview/royalty-free-music/epidemic-sound-vs-artlist)
- [WhisperX GitHub](https://github.com/m-bain/whisperX)
- [WhisperX 2026 Guide — LocalAIMaster](https://localaimaster.com/blog/whisperx-guide)
- [Karaoke-Style Word Highlight Captions — VidNo](https://vidno.ai/blog/karaoke-style-word-highlight-captions)
- [pycaps GitHub](https://github.com/francozanardi/pycaps)
- [Target LUFS for TikTok 2025 — ClickyApps](https://clickyapps.com/creator/video/guides/lufs-targets-2025)
- [FFmpeg loudnorm Two-Pass — DEV Community](https://dev.to/masonwritescode/two-pass-loudness-normalization-with-ffmpeg-loudnorm-the-right-way-1nm3)
- [ffmpeg-normalize GitHub](https://github.com/slhck/ffmpeg-normalize)
