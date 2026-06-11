# 02 — Script & Story Generation Layer

**Research date:** 2026-06-10  
**Scope:** LLM-driven minimal-prompt → structured episode script for TikTok AI character video pipeline

---

## 1. Minimal Prompt → Structured Script

### Approach

The core workflow is a single LLM call (or two-stage call) that takes:

```
Input: one-line premise + series-bible JSON + episode number
Output: full structured JSON episode script
```

This works reliably with any capable instruction-tuned model using **structured output / constrained decoding** — the model is forced to emit valid JSON matching a schema rather than freeform prose.

### Two-Stage vs. One-Stage

**One-stage (recommended for cost):** Combine premise + bible + output schema into a single system prompt. The LLM writes the entire episode JSON in one pass. Works well with Qwen 2.5 / 3 and Claude Haiku.

**Two-stage (better quality):** 
1. First call: LLM generates a "treatment" (prose outline with beat notes, ~200 tokens)
2. Second call: LLM converts treatment into the JSON schema. More reliable for complex arcs.

### Structured Output Enforcement

Modern tooling makes JSON schema compliance essentially guaranteed:

- **Ollama** (local): Pass `format` parameter with JSON schema; uses grammar-based constrained decoding. As of 2025, Ollama uses XGrammar as its default structured generation backend — under 40 µs per token overhead, near-zero latency cost.
- **Claude API**: Use `tool_use` or `response_format: json_schema` to enforce output structure.
- **OpenAI-compatible endpoints** (for local models via LM Studio, llama.cpp server): Pass `response_format: {"type": "json_schema", "json_schema": {...}}`.

**Key gotcha:** Constraining to strict JSON during chain-of-thought reasoning degrades quality. Best practice: let the model "think" freely (either via a scratchpad field or a separate reasoning pass), then output structured JSON. With Claude, use extended thinking before structured output. With local models, add a `"scratchpad"` field at the start of the schema that the model fills first, then the structured fields.

### System Prompt Pattern

```
You are a viral TikTok episode writer for an animated fruit drama series.

SERIES BIBLE (read carefully for continuity):
{series_bible_json}

EPISODE REQUEST:
- Episode number: {N}
- One-line premise: "{user_prompt}"
- Required runtime: 65–80 seconds

OUTPUT RULES:
- Respond ONLY with valid JSON matching this schema (no prose outside JSON)
- Use the scratchpad field to plan before writing scenes
- Every scene must have: image_prompt, motion_prompt, narration_text, on_screen_caption, duration_sec
- Total duration_sec across all scenes must sum to 65–80
- End on a cliffhanger — do NOT resolve all tension

{json_schema_here}
```

---

## 2. Timing & Pacing for >60-Second Videos

### Why 60 Seconds Matters

TikTok's **Creator Rewards Program** requires a hard minimum of **60 seconds** for monetization eligibility. Sub-minute videos earn nothing from the program regardless of views. Videos 65–90 seconds hit the sweet spot: long enough to monetize, short enough to maintain completion rates.

### Words-Per-Minute Targets

| Delivery style | WPM | Words for 65s | Words for 80s |
|---|---|---|---|
| Conversational narration | 140 | ~152 | ~187 |
| Dramatic/slow (telenovela) | 110–120 | ~120–130 | ~147–160 |
| Fast TikTok energy | 160–170 | ~173–184 | ~213–227 |

**Recommendation:** Target 130–150 words total narration for a 65–75s episode. Dramatic pacing (slower) suits the fruit-drama format.

### Scene / Shot Structure for 65–80s

| Component | Duration | Notes |
|---|---|---|
| Cold open / recap hook | 3–5s | Single image, punchy narration callback to last episode |
| Scene 1 — Setup | 8–12s | 2 shots |
| Scene 2 — Rising tension | 10–15s | 2–3 shots |
| Scene 3 — Confrontation | 12–18s | 2–3 shots |
| Scene 4 — Peak drama | 10–15s | 1–2 shots (this is the shareable moment) |
| Scene 5 — Cliffhanger | 5–8s | 1 shot + text card "Part N tomorrow…" |
| **Total** | **~65–80s** | 4–6 scenes, 10–14 shots |

**Shot length guideline:** Average 5–7 seconds per shot. Never hold a still image for more than 8 seconds without motion effect or caption change — TikTok analytics show attention drops sharply.

**Visual change rule:** Change visual stimulus every 2–3 seconds (cut, zoom, text overlay, caption change, motion).

### Narration Word Budget Per Scene

Given 5–7s average shots, aim for **~12–18 words of narration per shot** at dramatic pacing. Each scene narration should be one or two short declarative sentences. Example:

> "Broccoli Queen had not expected this. The message on the phone was from her own daughter."

(~20 words, ~9s at dramatic pace — fits a 10s shot)

---

## 3. Character & Story Continuity Across Episodes

### The Core Problem

LLMs have no memory between calls. Without an explicit record of established facts, the model will contradict prior episodes (different eye color, forgotten plot events, personality drift). The solution is a **series bible JSON file** that is prepended to every script-generation prompt.

### Series Bible Structure

The bible lives as a JSON file that is **read before generation** and **updated after generation**. It has two layers:

1. **Static section** — things that never change (character appearances, personalities, visual style tokens for image generation)
2. **Dynamic section** — running plot state updated each episode (current relationships, unresolved cliffhangers, character locations, episode recap log)

The update step is a second LLM call: after the episode JSON is finalized, ask the model to diff-and-update the dynamic section of the bible.

### Series Bible JSON Schema

```json
{
  "series": {
    "title": "Fruit Island",
    "genre": "telenovela drama",
    "setting": "luxury penthouse district of Fruit City",
    "visual_style": "3D Pixar-style anthropomorphic fruit characters, cinematic lighting, warm saturated colors",
    "tone": "dramatic, over-the-top, slightly comedic, soap opera",
    "episode_count": 0
  },
  "characters": {
    "broccoli_queen": {
      "name": "Broccoli Queen",
      "role": "matriarch villain",
      "personality": "regal, manipulative, deeply emotional beneath cold exterior",
      "appearance_tokens": "anthropomorphic broccoli head, pearl necklace, silk robe, penthouse backdrop, tearful eyes, dramatic lighting",
      "image_style_anchor": "Pixar 3D render, warm amber rim light, photorealistic texture",
      "voice_tone": "low, authoritative, slight tremor when emotional",
      "relationships": {
        "strawberry_rose": "estranged daughter",
        "corn_eli": "loyal servant"
      },
      "current_status": "alive, in penthouse, suspects betrayal",
      "introduced_episode": 1
    },
    "strawberry_rose": {
      "name": "Strawberry Rose",
      "role": "protagonist",
      "personality": "naive but increasingly cunning, wants love and family acceptance",
      "appearance_tokens": "anthropomorphic strawberry, red dress, tear-streaked cheeks, dimly lit apartment",
      "image_style_anchor": "Pixar 3D render, cool blue fill light, soft bokeh background",
      "voice_tone": "breathy, emotional, rising pitch when scared",
      "relationships": {
        "broccoli_queen": "estranged mother",
        "grape_victor": "secret lover"
      },
      "current_status": "alive, in apartment, holding secret letter",
      "introduced_episode": 1
    }
  },
  "plot_state": {
    "active_threads": [
      {
        "id": "inheritance_dispute",
        "description": "Broccoli Queen's will has been altered; Strawberry Rose doesn't know yet",
        "introduced_episode": 2,
        "status": "unresolved"
      },
      {
        "id": "mystery_letter",
        "description": "Strawberry Rose received a letter she hasn't opened",
        "introduced_episode": 3,
        "status": "unresolved",
        "cliffhanger_text": "Who sent the letter?"
      }
    ],
    "resolved_threads": [],
    "last_cliffhanger": "Strawberry Rose's hand trembles as she reaches for the envelope — but then the doorbell rings.",
    "last_episode_summary": "Episode 3: Broccoli Queen learned that Grape Victor visited the apartment. Strawberry Rose found the letter but didn't open it."
  },
  "world": {
    "locations": {
      "penthouse": "luxury high-rise, marble floors, floor-to-ceiling windows, golden hour light",
      "apartment": "modest, warm, plants on windowsill, afternoon light"
    },
    "recurring_props": ["pearl necklace", "mystery envelope", "family portrait with torn corner"]
  },
  "episode_log": [
    {
      "episode": 1,
      "summary": "Introduction of Broccoli Queen and Strawberry Rose. Their estrangement is established.",
      "new_characters": ["broccoli_queen", "strawberry_rose"],
      "resolved_threads": [],
      "cliffhanger": "Broccoli Queen finds Strawberry Rose's photo in the lawyer's briefcase."
    }
  ]
}
```

### Update Workflow

After each episode is generated and approved:

1. Append episode summary to `episode_log`
2. Move resolved threads to `resolved_threads`
3. Add new `active_threads` from episode content
4. Update `last_cliffhanger` and `last_episode_summary`
5. Update `current_status` for any characters whose situation changed

This update can be done with a small follow-up LLM call:

```
Given the episode JSON below, update the dynamic fields of this series bible JSON 
(plot_state, character current_status, episode_log). Return ONLY the updated bible JSON.

EPISODE: {episode_json}
CURRENT BIBLE: {current_bible_json}
```

### Appearance Tokens as Image Generation Anchors

The `appearance_tokens` and `image_style_anchor` fields in each character are copied verbatim into every `image_prompt` for that character's scenes. This is the primary mechanism for visual consistency between episodes. Keep these tokens:
- Specific but not overly long (15–25 words)
- Focused on distinguishing visual traits (color, clothing, lighting style)
- Tested against your image generation model before locking them in

---

## 4. Output JSON Schema: Episode Document

This is the schema the script LLM should output. It is consumed directly by downstream image generation, video motion, TTS, caption, and assembly stages.

```json
{
  "$schema": "episode-v1.0",
  "episode": {
    "series_title": "Fruit Island",
    "episode_number": 4,
    "episode_title": "The Letter",
    "total_duration_sec": 72,
    "hook_text": "She finally opened the letter. And her whole world collapsed.",
    "cliffhanger_text": "The name at the bottom wasn't who she expected.",
    "episode_summary": "Strawberry Rose opens the mystery letter and discovers a shocking revelation about her origins.",
    "new_plot_threads": ["rose_true_parentage"],
    "resolved_plot_threads": ["mystery_letter"]
  },
  "characters_in_episode": ["strawberry_rose", "broccoli_queen"],
  "scenes": [
    {
      "scene_id": "s01",
      "scene_label": "cold_open_recap",
      "duration_sec": 5,
      "image_prompt": "anthropomorphic strawberry character, red dress, tear-streaked cheeks, holding white envelope, dimly lit apartment, Pixar 3D render, cool blue fill light, soft bokeh background, cinematic composition, high detail",
      "motion_prompt": "slow zoom in on envelope, slight hand tremble, static background",
      "narration_text": "Last time on Fruit Island — Strawberry Rose found the letter. Tonight, she finally opens it.",
      "on_screen_caption": "Previously on Fruit Island...",
      "caption_style": "white bold sans-serif, bottom third",
      "shot_type": "medium close-up",
      "characters": ["strawberry_rose"],
      "location": "apartment",
      "mood": "tense, anticipatory"
    },
    {
      "scene_id": "s02",
      "scene_label": "rising_tension_1",
      "duration_sec": 12,
      "image_prompt": "anthropomorphic strawberry character, red dress, wide frightened eyes, letter paper in hands with visible text, warm lamp light from side, Pixar 3D render, soft bokeh background, photorealistic texture",
      "motion_prompt": "slow push in from wide to close-up over 12 seconds, letter paper subtle shake effect",
      "narration_text": "Her eyes moved slowly across the page. Each word more impossible than the last. This couldn't be real.",
      "on_screen_caption": "This can't be real...",
      "caption_style": "white italic serif, center bottom",
      "shot_type": "wide to close-up",
      "characters": ["strawberry_rose"],
      "location": "apartment",
      "mood": "dread, disbelief"
    },
    {
      "scene_id": "s03",
      "scene_label": "peak_drama",
      "duration_sec": 15,
      "image_prompt": "anthropomorphic broccoli character, pearl necklace, silk robe, cold expression, marble penthouse floor, floor-to-ceiling windows, golden hour light streaming in, Pixar 3D render, warm amber rim light, photorealistic texture, dramatic shadow",
      "motion_prompt": "static shot, character turns head slowly to look directly at camera at 10s mark",
      "narration_text": "High above the city, Broccoli Queen set down her phone. She had sent the letter herself. And she knew exactly what it contained.",
      "on_screen_caption": "She knew all along.",
      "caption_style": "white bold sans-serif, bottom third",
      "shot_type": "full shot",
      "characters": ["broccoli_queen"],
      "location": "penthouse",
      "mood": "sinister, calm"
    },
    {
      "scene_id": "s04",
      "scene_label": "cliffhanger",
      "duration_sec": 8,
      "image_prompt": "anthropomorphic strawberry character, red dress, standing in doorway, shocked expression, backlit silhouette, dramatic low key lighting, Pixar 3D render, film grain, wide shot",
      "motion_prompt": "freeze frame at 5s, fade to black slowly",
      "narration_text": "The name at the bottom of the letter. It changed everything.",
      "on_screen_caption": "Part 5 tomorrow. Follow for the next episode.",
      "caption_style": "white bold sans-serif with drop shadow, centered",
      "shot_type": "wide dramatic",
      "characters": ["strawberry_rose"],
      "location": "apartment doorway",
      "mood": "shock, revelation"
    }
  ],
  "audio": {
    "tts_voice": "dramatic_female_en",
    "background_music": "tense_telenovela_loop",
    "music_volume": 0.15,
    "sfx": [
      {"scene_id": "s01", "sound": "paper_rustle", "timing_sec": 2.0},
      {"scene_id": "s04", "sound": "dramatic_sting", "timing_sec": 5.0}
    ]
  },
  "metadata": {
    "target_platform": "tiktok",
    "aspect_ratio": "9:16",
    "resolution": "1080x1920",
    "generated_at": "2026-06-10T00:00:00Z",
    "model_used": "qwen2.5-72b-instruct",
    "series_bible_version": 4
  }
}
```

### Schema Field Notes

| Field | Purpose | Consumed by |
|---|---|---|
| `image_prompt` | Full prompt for image gen (includes character appearance_tokens) | Stable Diffusion / Flux / Midjourney |
| `motion_prompt` | Camera/motion instruction for video model | RunwayML / Kling / LTX-Video |
| `narration_text` | TTS input text | Kokoro / ElevenLabs / Edge TTS |
| `on_screen_caption` | Burned-in subtitle | FFmpeg / CapCut / assembly layer |
| `duration_sec` | Target clip length in seconds | Assembly layer timing |
| `mood` | Optional context for music selection | Audio selection logic |
| `hook_text` | First 3-second voiceover hook | TTS + assembly layer |

---

## 5. Local LLM vs Cloud API

### Quality Tiers for Script Generation

| Model | Type | Creative Writing Quality | JSON Reliability | Recommended For |
|---|---|---|---|---|
| Claude Sonnet 4.6 | Cloud API | Excellent — viral hooks, witty dialogue, pacing | Very high with tool_use | Production quality, early development |
| Claude Haiku 4.5 | Cloud API | Good — solid structure, occasional generic phrasing | High | High-volume cost-optimized cloud |
| Qwen3-32B | Local / API | Very good — strong instruction following, creative | High with structured output | Best local option if GPU available |
| Qwen2.5-72B | Local / API | Good — excellent structured data, adequate creative | High | Local workhorse (requires ~48GB VRAM) |
| Qwen2.5-7B | Local | Adequate — format adherence good, creativity limited | Moderate | Low-resource local fallback |
| Llama 3.3-70B | Local | Good — strong controllability, consistent format | High | Alternative local 70B option |
| Llama 3.1-8B | Local | Weak for dramatic creative writing | Moderate | Not recommended for scripts |
| Mistral Small 3 24B | Local/API | Good — very fast inference, multilingual | High (IFEval: 82.9%) | Speed-priority use cases |
| DeepSeek V3 | API | Good — near-Claude quality at ~$0.14/M input | High | Cheapest capable cloud option |

### Cost Breakdown Per Episode Script

Assume: ~800 tokens input (system prompt + bible), ~1200 tokens output (full episode JSON)

| Model | Input cost | Output cost | Total per episode | Per 100 episodes |
|---|---|---|---|---|
| Claude Sonnet 4.6 | $3/MTok | $15/MTok | ~$0.024 | ~$2.40 |
| Claude Haiku 4.5 | $1/MTok | $5/MTok | ~$0.007 | ~$0.70 |
| DeepSeek V3 | $0.14/MTok | $0.28/MTok | ~$0.0005 | ~$0.05 |
| Qwen API (hosted) | ~$0.40/MTok | ~$2.40/MTok | ~$0.003 | ~$0.30 |
| Local (Ollama) | $0 | $0 | ~$0 | ~$0 (power only) |

**With prompt caching** (Claude): Reusing the same system prompt + series bible across episodes cuts input cost by ~90%, bringing Claude Sonnet per-episode cost to ~$0.004 (under half a cent).

**With batch processing** (Claude): 50% discount on all tokens. For non-real-time generation, batch is the right choice.

### Recommendation

**For initial development:** Use **Claude Haiku 4.5 with prompt caching** — excellent quality for viral hooks and drama scripts, predictable JSON output, ~$0.001–0.004 per episode after caching. The series bible (mostly static content) is cached after the first call.

**For zero-cost at scale:** Run **Qwen2.5-32B or Qwen3-32B via Ollama** locally. Requires a machine with ~24GB VRAM (RTX 3090/4090 or Mac M2/M3 Pro/Max with 32GB unified memory). Quality is close to Haiku, especially for structured/dramatic scripts. An RTX 4070 Ti Super (~$489) pays for itself vs. cloud API in 5–10 months for a high-volume pipeline.

**For mixed strategy:** Use Claude for episode 1 of each series (quality matters most for hooks/character establishment), then switch to local Qwen for subsequent episodes once the bible is established and style is locked in.

---

## 6. Virality & Hook Patterns for TikTok

### The 3-Second Hook Law

68% of viewers decide whether to keep watching within the **first 2 seconds**. The opening shot + first narration line is everything. Proven hook formulas:

| Formula | Example |
|---|---|
| **Curiosity gap** | "She found out what he'd been hiding. And she didn't cry." |
| **Bold statement** | "The most dramatic fruit family in TikTok history just got worse." |
| **Direct address** | "If you watched Part 11, you already know what's coming." |
| **Impossible result** | "One letter destroyed a dynasty that took 30 years to build." |

**Hook generation prompt add-on:** Always include in the system prompt: `"The hook_text field must be a single sentence under 15 words that creates a curiosity gap — it should make the viewer feel they will miss something important if they scroll away."`

### Cliffhanger Architecture for Series Retention

The cliffhanger is the inter-episode retention mechanism. Structure:

1. **Withhold one specific answer** (who sent the letter, who is at the door, what the test result shows)
2. **Drop a partial signal** — show the character's *reaction* to the reveal before cutting, not the reveal itself. The viewer sees the shock; the reveal waits.
3. **End-card CTA**: Always close with on-screen text: `"Part [N+1] tomorrow — follow so you don't miss it"`. This is non-negotiable.
4. **Cold open callback**: Episode N+1 must open by directly answering episode N's cliffhanger question within the first 5 seconds. This is the "algorithmic continuity" signal that drives series watch sequences.

### Episode Length Strategy for Series

- **Episode 1:** 45–65 seconds — shorter, punchy, needs to hook new viewers fast
- **Episodes 2–5:** 65–80 seconds — build lore, deepen characters
- **Mid-series (6+):** 75–90 seconds — longer payoffs are earned once the audience is invested
- **Never exceed 120 seconds** in the early series — viewer investment hasn't been established yet

### Engagement Loop Patterns (Fruit Drama Specific)

Top-performing storyline engines that sustain multi-episode series:

1. **Secret parentage / hidden identity** — slow drip of clues across 8–12 episodes
2. **Inheritance/dynasty conflict** — natural multi-party drama with shifting alliances
3. **Forbidden romance with family opposition** — classic telenovela engine
4. **Revenge arc** — clear antagonist, satisfying long-burn payoff
5. **Paternity/pregnancy reveal** — highest individual-episode virality, use sparingly

---

## 7. Recommended Implementation Stack

```
User input (one-line prompt)
         │
         ▼
[LLM Script Generator]
  - Model: Qwen3-32B (local) or Claude Haiku 4.5 (cloud)
  - Input: prompt + series_bible.json
  - Output: episode_N.json (structured per schema above)
  - Structured output: Ollama format param / Claude tool_use
         │
         ▼
[Bible Updater] (small follow-up LLM call)
  - Diffs episode JSON against bible
  - Updates dynamic plot_state, episode_log, character statuses
  - Writes updated series_bible.json
         │
         ▼
episode_N.json → downstream stages:
  - image_prompt  → Image generation (Flux / SD)
  - motion_prompt → Video model (Kling / LTX)
  - narration_text → TTS (Kokoro / ElevenLabs)
  - on_screen_caption → Assembly / FFmpeg
  - duration_sec  → Assembly timing
```

### Key Library Recommendations

- **Ollama Python SDK** (`ollama` package): `format=` parameter for constrained JSON output
- **Pydantic** v2: Define episode schema as a Pydantic model; use `model.model_json_schema()` to pass to Ollama/Claude
- **jsonschema**: Validate generated episode JSON before passing downstream
- **Claude SDK** (`anthropic` package): Use `tools` parameter with a single tool definition matching the episode schema; model is forced to call it, producing guaranteed-valid JSON

---

## Sources

- [TikTok Script Structure Guide (retiplex.com)](https://www.retiplex.com/blog/how-to-write-tiktok-scripts)
- [TikTok Monetization Requirements 2026 (flowshorts.app)](https://flowshorts.app/blog/tiktok-monetization-requirements)
- [TikTok Series Briefs: Cliffhangers & Commerce Conversion (influencers-time.com)](https://www.influencers-time.com/tiktok-series-briefs-cliffhangers-and-commerce-conversion/)
- [AI Fruit Drama Script Formula (flashloop.app)](https://www.flashloop.app/blog/how-to-make-ai-fruit-drama-videos)
- [Story Bibles for AI: Structured Memory (novarrium.com)](https://novarrium.com/blog/ai-story-bible-structured-memory)
- [Building AI Novel with Consistent Characters (indiehackers.com)](https://www.indiehackers.com/post/i-built-an-ai-that-writes-full-length-novels-with-consistent-characters-heres-what-i-learned-f0d3211a8a)
- [Video Notation Schema (github.com/context-notation)](https://github.com/context-notation/video-notation-schema)
- [Ollama Structured Outputs (ollama.com)](https://ollama.com/blog/structured-outputs)
- [LLM API Pricing Comparison (costgoat.com)](https://costgoat.com/compare/llm-api)
- [Anthropic API Pricing 2026 (finout.io)](https://www.finout.io/blog/anthropic-api-pricing)
- [TikTok Minis: Micro-Dramas (webpronews.com)](https://www.webpronews.com/tiktoks-minis-micro-dramas-revolutionize-engagement-and-revenue/)
- [n8n AI Video from Script Workflow (n8n.io)](https://n8n.io/workflows/6777-generate-ai-videos-from-scripts-with-deepseek-tts-and-togetherai/)
- [Best Open Source LLMs 2026 (huggingface.co)](https://huggingface.co/blog/daya-shankar/open-source-llms)
- [Constrained LLMs with Ollama + Qwen3 (medium.com)](https://medium.com/@rosgluk/constraining-llms-with-structured-output-ollama-qwen3-python-or-go-2f56ff41d720)
- [Video Script Word Count Guide (studiobo.io)](https://www.studiobo.io/blog/what-is-the-ideal-script-length-for-a-60-second-video)
