# 08 — Economics, Cost & Profitability Model
*Last updated: June 2026*

---

## Executive Summary

Running a local-AI TikTok pipeline **can** be cash-flow positive, but the economics are narrower than influencer hype suggests. The core bottleneck is not compute cost (which is genuinely tiny) — it is the **revenue side**: TikTok RPM is modest, qualified-view rates are opaque, and new accounts spend months below the monetization eligibility threshold. A single viral video can flip the P&L instantly; consistent profitability at scale requires either high-RPM niche selection or secondary revenue (sponsorships, affiliates).

---

## 1. Local Generation Cost (Electricity)

### 1.1 Power Draw — RTX 4090 Workstation

| Component | Typical AI Load |
|---|---|
| RTX 4090 GPU | 350–450 W (spec TBP 450 W; image-to-video averages ~235 W; LLM inference ~380 W) |
| CPU (i9-13900K / Ryzen 9) | 125–200 W |
| Motherboard + RAM + storage | 60–100 W |
| **Total system (conservative)** | **550–750 W** |
| **Total system (peak burst)** | **~780 W** |

For sustained AI generation work we can use **600 W as a working average** — GPU running at ~350 W average (a blend of image-gen, video-gen, TTS, render, idle waits) plus rest-of-system.

### 1.2 Time to Generate One ~1-Minute Video

A 60-second TikTok built from a pipeline of local models requires:

| Step | Tool | RTX 4090 Time |
|---|---|---|
| Script generation (LLM, ~500 tokens out) | Local Llama 3.1 8B / Mistral | ~5 s |
| Voiceover 60-sec audio | Kokoro-82M TTS | ~5–10 s |
| Scene images (8–12 × SDXL/FLUX Schnell) | ComfyUI | 30–60 s (3–5 s each) |
| Video clips (3–5 × 3-sec clips @ 480p, Wan 2.1 / LTX-Video) | ComfyUI | 5–15 min (LTX ~90 s/clip; Wan 2.1 ~4.5 min/clip) |
| Subtitles + render + mux | FFmpeg / Python | ~15–30 s |
| **Total GPU wall-clock time** | | **~8–20 min per video** |

**Working estimate: 12 minutes average GPU time per video** (using LTX-Video for clips, ~90 s each, plus image-gen and overhead).

If using slower Wan 2.1 for higher quality (4.5 min/clip × 4 clips = 18 min + overhead), the upper end is ~25 min per video.

### 1.3 Electricity Cost Per Video

```
Rate used: $0.18/kWh (US average residential June 2026)
System draw: 600 W = 0.6 kW
Generation time: 12 min = 0.2 hours

Energy per video = 0.6 kW × 0.2 h = 0.12 kWh
Cost per video   = 0.12 kWh × $0.18 = $0.0216
```

| Scenario | Gen Time | kWh | Cost @ $0.18/kWh |
|---|---|---|---|
| Fast pipeline (LTX-Video, 480p) | 8 min | 0.080 | **$0.014** |
| Standard pipeline (LTX-Video + SDXL) | 12 min | 0.120 | **$0.022** |
| Quality pipeline (Wan 2.1 + FLUX Dev) | 25 min | 0.250 | **$0.045** |
| High electricity state (e.g., California $0.30/kWh), standard | 12 min | 0.120 | **$0.036** |

**Bottom line: electricity cost is $0.02–$0.05 per video.** Even at California rates with premium models, it stays under $0.05.

### 1.4 Amortized Hardware Cost (Optional)

| Hardware | Price | Lifespan | Monthly (÷36) | Per video @ 3/day |
|---|---|---|---|---|
| RTX 4090 GPU | ~$1,800 (used ~$900) | 3–4 yr | $50–$42 | $0.56–$0.47 |
| Full workstation (w/ GPU) | ~$3,500 | 4 yr | $73 | $0.81 |

If the machine already exists or serves other purposes, hardware amortization is a sunk cost — marginal cost per video remains near electricity only. Included here for completeness; **omit from per-video cost if machine is already owned**.

---

## 2. API Costs

### 2.1 All-Local Scenario (Near-$0)

| Component | Tool | Per-video cost |
|---|---|---|
| Script | Llama 3.1 8B / Mistral local | **$0.00** |
| TTS | Kokoro-82M (open-source, local) | **$0.00** |
| Image gen | FLUX Schnell / SDXL local | **$0.00** |
| Video gen | Wan 2.1 / LTX-Video local | **$0.00** |
| Scheduler | n8n (self-hosted) | **$0.00** |
| **Total API cost** | | **$0.00** |
| **Total marginal cost (elec only)** | | **~$0.022** |

### 2.2 Hybrid Scenario (Paid APIs for Quality/Convenience)

| Component | Service | Usage | Per-video cost |
|---|---|---|---|
| Script (1,000 tok in + 500 tok out) | Claude Haiku 4.5 ($1/$5 per M) | 1,000+500 tokens | **$0.003** |
| Voiceover (60-sec ≈ 750 chars) | ElevenLabs Creator plan ($22/mo, 100k chars) | ~750 chars | **$0.165** |
| Scheduling | Buffer / Later (free tier) | — | **$0.00** |
| **Total API cost (hybrid)** | | | **~$0.17** |
| **Total marginal cost** | | | **~$0.19** |

> **Note on ElevenLabs**: At the Creator plan ($22/mo for ~100,000 characters), 750 chars per 60-sec narration = ~133 videos per month before the plan runs out. If you exceed that, overage via API costs $0.30/1,000 chars → $0.225/video. The Economics math favors switching to local Kokoro TTS (comparable quality for most niches) once past ~50 videos/month.

### 2.3 Cost Per Video Summary

| Scenario | Electricity | APIs | **Total per video** |
|---|---|---|---|
| All-local, standard quality | $0.022 | $0.00 | **$0.022** |
| All-local, high quality (Wan 2.1) | $0.045 | $0.00 | **$0.045** |
| Hybrid (ElevenLabs + Claude Haiku) | $0.022 | $0.168 | **$0.190** |
| Hybrid, high quality gen | $0.045 | $0.168 | **$0.213** |

---

## 3. Revenue Side — TikTok Creator Rewards

### 3.1 Program Requirements (Must-Meet Before Any Income)

- 10,000+ followers
- 100,000+ video views in the last 30 days
- Videos must be **>1 minute long** (enforced hard cutoff)
- First 1,000 qualified FYP views per video earn nothing (minimum threshold)
- Only "qualified views" (≥5 seconds watch, FYP-sourced, non-fraudulent) generate revenue

### 3.2 RPM Rates by Niche (per 1,000 qualified views)

| Niche Category | RPM Range | Notes |
|---|---|---|
| Finance / investing / business | $1.00–$3.00 | Highest advertiser CPM, older demographic |
| Tech / AI / software | $0.80–$2.00 | Strong advertiser interest |
| Health / wellness / education | $0.60–$1.50 | Broad appeal |
| General entertainment / lifestyle | $0.40–$0.80 | Most AI faceless content lands here |
| Comedy / dance / trends | $0.20–$0.50 | Low RPM, high virality potential |

**Conservative blended RPM for AI-faceless content: $0.50–$0.80**
**Optimistic (niche-targeted): $1.00–$1.50**

Note: "Qualified views" are consistently a fraction of total views. Community estimates suggest **40–70% of total views become qualified views** depending on content (longer videos with good retention qualify more; short-attention content less). TikTok does not publish this ratio officially.

### 3.3 Revenue per Video at Various View Counts

Using $0.60 conservative RPM and 55% qualified-view rate:

| Total Views | Qualified Views (55%) | Revenue @ $0.60 RPM | Revenue @ $1.00 RPM |
|---|---|---|---|
| 1,000 | 550 | $0.33 | $0.55 |
| 5,000 | 2,750 | $1.65 | $2.75 |
| 10,000 | 5,500 | $3.30 | $5.50 |
| 50,000 | 27,500 | $16.50 | $27.50 |
| 100,000 | 55,000 | $33.00 | $55.00 |
| 500,000 | 275,000 | $165.00 | $275.00 |
| 1,000,000 | 550,000 | $330.00 | $550.00 |

**Real-world validation**: Creator case study of 21M views in 30 days → $3,000 earned ≈ $0.143/1,000 total views. This implies either low qualified-view rate or low niche RPM — consistent with general entertainment content. Finance/tech creators self-report $0.50–$1.50 per 1,000 total views.

---

## 4. Break-Even Analysis

### 4.1 Monthly Fixed Costs

| Scenario | Monthly cost (marginal only) | Notes |
|---|---|---|
| All-local, 3 videos/day | 90 × $0.022 = **$1.98** | Near-zero |
| All-local, 10 videos/day | 300 × $0.022 = **$6.60** | Still negligible |
| Hybrid, 3 videos/day | 90 × $0.190 = **$17.10** | ElevenLabs plan dominates |
| Hybrid, 10 videos/day | 300 × $0.190 = **$57.00** | Need upgraded ElevenLabs tier |

### 4.2 Break-Even Views Per Month

Assuming each video averages the same view count (unrealistic — power-law distribution in practice), monthly views needed to cover costs at $0.60 RPM conservative:

| Scenario | Monthly cost | Views needed @ $0.60 RPM, 55% qual | Videos/mo | Views/video needed |
|---|---|---|---|---|
| All-local, 3/day | $1.98 | ~6,000 | 90 | ~67 avg |
| All-local, 10/day | $6.60 | ~20,000 | 300 | ~67 avg |
| Hybrid, 3/day | $17.10 | ~51,818 | 90 | ~576 avg |
| Hybrid, 10/day | $57.00 | ~172,727 | 300 | ~576 avg |

**Key insight**: The all-local scenario is so cheap that breaking even on electricity alone requires near-trivial view counts. The real question is reaching monetization eligibility (10K followers + 100K views/month) and producing videos that earn meaningful revenue — not covering the electricity bill.

### 4.3 Realistic Target: Covering Time & Effort

Even if electricity is nearly free, the creator's time has value. At $20/hr:

| Time investment | Effective cost/mo | Views needed (@ $0.60 RPM) |
|---|---|---|
| 1 hr/day (setup, review, edit prompts) | $600 | ~1.8M qualified views |
| 2 hr/day | $1,200 | ~3.6M qualified views |
| 30 min/day (well-automated) | $300 | ~0.9M qualified views |

At 90 videos/month, to earn $300 from Creator Rewards, each video needs ~10,000 qualified views on average — i.e., about 18,000 total views each. That is attainable but not automatic.

---

## 5. Revenue Scenario Table (Monthly, 3 Videos/Day = 90/mo)

Modeling different average view levels per video, all-local scenario:

| Avg views/video | Total monthly views | Revenue @ $0.60 RPM | Revenue @ $1.00 RPM | Profit (all-local) | Profit (hybrid) |
|---|---|---|---|---|---|
| 500 (struggling) | 45,000 | $14.85 | $24.75 | **$12.87** | **-$2.25** |
| 2,000 (small traction) | 180,000 | $59.40 | $99.00 | **$57.42** | **$42.30** |
| 5,000 (decent) | 450,000 | $148.50 | $247.50 | **$146.52** | **$131.40** |
| 10,000 (solid) | 900,000 | $297.00 | $495.00 | **$295.02** | **$279.90** |
| 25,000 (one viral/wk) | 2,250,000 | $742.50 | $1,237.50 | **$740.52** | **$725.40** |
| 100,000 (consistent viral) | 9,000,000 | $2,970.00 | $4,950.00 | **$2,968.02** | **$2,952.90** |

*All-local cost: $1.98/mo. Hybrid cost: $17.10/mo. RPM assumes 55% qualified-view rate.*

**One genuinely viral video (1M+ views)** earns $330–$550 in a single event — more than months of consistent small-scale posting.

---

## 6. Scaling Economics

### 6.1 Cost at Scale

The all-local model scales almost linearly with electricity:

| Videos/day | Monthly videos | Monthly electricity cost | Monthly hybrid API cost |
|---|---|---|---|
| 1 | 30 | $0.66 | ~$5.70 |
| 3 | 90 | $1.98 | ~$17.10 |
| 10 | 300 | $6.60 | ~$57.00 |
| 24 | 720 | $15.84 | *$136.80 (need Scale plan)* |

At 10+ videos/day, a single RTX 4090 becomes the bottleneck:
- Standard pipeline: 12 min/video → max ~5 videos/hour → **120/day max**, saturating the GPU 24/7
- High-quality (Wan 2.1): 25 min/video → max ~2.4 videos/hour → **57/day max**

A second 4090 doubles throughput; electricity doubles proportionally.

### 6.2 Where It Breaks

| Limit | Threshold | Impact |
|---|---|---|
| TikTok posting sweet spot | 2–3 videos/day per account | >4–5/day risks algo suppression (diminishing reach, not hard ban) |
| Multiple accounts | TikTok prohibits coordinated inauthentic behavior; auto-scheduler flagging risk | Permanent ban risk; each account needs unique device fingerprint / IP |
| AI content labeling | TikTok auto-detects C2PA watermarks from DALL-E, Midjourney, Adobe; unlabeled = strike | Must disclose AI; third violation = 30-day posting block; fifth = account termination |
| Content quality dilution | Each video in a volume strategy gets less individual attention | Engagement rate drops; algo reduces distribution; RPM declines |
| Monetization eligibility | Must maintain 100K views/30 days | Failing to maintain threshold can suspend Creator Rewards access |

**Practical ceiling for single-account, responsible operation: 2–3 videos/day, 60–90/month**

---

## 7. Honest Assessment — First 3–6 Months

### 7.1 Month-by-Month Reality

| Phase | Typical situation | Realistic revenue |
|---|---|---|
| Month 1–2 | Building library; likely < 1,000 followers; not monetization-eligible | **$0** |
| Month 3 | May hit 10K followers if content connects; still building to 100K views/30 days threshold | **$0–$10** |
| Month 4–5 | Eligible if account took off; earning but small | **$10–$100/mo** |
| Month 6 | Meaningful if one video went semi-viral | **$50–$500/mo** |
| Month 12+ | Established niche account with series effect | **$200–$2,000/mo** |

These are **median** outcomes. The distribution is extremely bimodal: most new accounts earn almost nothing from Creator Rewards in year one; a small fraction hit one viral video and leap to $1,000+ in a week.

### 7.2 What Actually Drives Profitability

1. **Niche RPM**: Choosing finance/tech/education over entertainment can 2–5× revenue on the same view counts. This single decision matters more than any cost optimization.

2. **One viral video**: The economics are not linear. At TikTok's power-law distribution, the top 5% of videos drive ~80% of revenue. One 500K-view video earns more than 300 × 1,000-view videos combined. Pipeline automation's real value: more shots at going viral.

3. **Retention / series effect**: Accounts that build recurring viewers (series content, "part 2" hooks) see much better qualified-view conversion than one-off content, because returning viewers watch longer.

4. **Secondary revenue**: Creator Rewards alone rarely justify the time investment. Successful faceless AI accounts layer in:
   - Affiliate links ($5–$50/conversion for AI tools, SaaS products)
   - Digital products / courses ($27–$97 direct offers)
   - Brand sponsorships once 50K+ followers reached ($200–$1,000/video)
   These can 5–10× the all-in monthly revenue versus Creator Rewards only.

5. **The real cost is opportunity time**: At $0.02/video electricity, compute is not the constraint. Human time for prompt engineering, quality review, niche strategy, and trend monitoring is what determines success.

### 7.3 Profitability Target: Is It Achievable?

**"Total recurring cost < TikTok income" is trivially achievable on a pure electricity basis** — 67 average views per video covers the electricity bill. However, making the project worthwhile against the creator's time requires consistent 10K–50K average views per video, which demands niche selection, iteration on hooks, and at minimum 3–6 months of building an audience.

---

## 8. Sensitivity Table

| Variable | Conservative | Base Case | Optimistic |
|---|---|---|---|
| RPM | $0.40 | $0.60 | $1.20 |
| Qualified-view rate | 40% | 55% | 70% |
| Avg views per video | 2,000 | 8,000 | 30,000 |
| Videos per month | 60 | 90 | 90 |
| Monthly revenue | $19.20 | $237.60 | $2,268 |
| Monthly cost (all-local) | $1.32 | $1.98 | $1.98 |
| Monthly profit (all-local) | **$17.88** | **$235.62** | **$2,266** |
| Monthly cost (hybrid) | $11.40 | $17.10 | $17.10 |
| Monthly profit (hybrid) | **$7.80** | **$220.50** | **$2,251** |

---

## 9. Key Data Sources & Assumptions

- **Electricity**: US residential average $0.18/kWh (June 2026, EIA data via electricchoice.com). High-cost states (CA, HI) use $0.28–$0.43/kWh.
- **GPU power**: RTX 4090 ~235 W average during image-to-video (Valdi.ai benchmark); ~350–450 W during mixed workloads. Total system 600 W used as working average.
- **Video generation time**: LTX-Video ~90 s/clip on 4090; Wan 2.1 ~4.5 min/clip at 480p. Pipeline total ~12 min standard, ~25 min quality.
- **TikTok RPM**: $0.40–$1.50 general range; $1.00–$3.00 for finance/tech (influencermarketinghub.com, miraflow.ai, calculatecreator.com, 2026 data).
- **ElevenLabs**: Creator plan $22/mo = 100K chars ≈ 133 × 60-sec videos.
- **Claude Haiku 4.5**: $1.00/$5.00 per M tokens input/output.
- **Hardware**: RTX 4090 ~$1,800 new; ~$900 used. 3-year amortization.
- **AI content policy risk**: TikTok removed 51,618 synthetic media videos H2 2025; unlabeled AI content triggers escalating strikes (permanent ban at 5th offense).

---

*Sources consulted: electricchoice.com, valdi.ai, localaimaster.com, miraflow.ai, influencermarketinghub.com, rupa.pro, calculatecreator.com, elevenlabs.io, platform.claude.com, auditsocials.com, autofaceless.ai*
