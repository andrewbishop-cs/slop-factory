# SYNTHESIS — Affiliate Pivot: Recommended Path Forward

**Question:** How do we evolve the current character-video pipeline to capture TikTok Shop affiliate revenue by building an audience with the character series, then injecting products — and what concretely changes?

**Date:** 2026-06-10 · Based on subtasks 01–06 + adversarial verification of load-bearing claims.

---

## Direct answer

**The pivot is worth doing, and your strongest insight is correct — but one link in your chain needs surgery.**

- ✅ **Sound:** the character series as an **audience-acquisition front-end**, then monetizing that audience. Affiliate economics beat the old Creator-Rewards plan by **2–4 orders of magnitude per unit of effort** (one $120 sale at 30% ≈ $36 ≈ 60–90k qualified RPM views), and the eligibility bar is far lower (**1,000 followers to join** vs 10k + 100k views). Affiliate also **decouples revenue from follower count** because paid Spark Ads buy reach. *(05, 04 — high confidence.)*
- ⚠️ **Needs surgery:** the assumption that **the cartoon characters themselves demo/sell the high-AUP product**. Across content research (01), market evidence (06), economics (05), and an adversarial refutation pass, the verdict is **MEDIUM-confidence-against**: every documented high-AUP affiliate winner leads with a **real person and/or a physically-handled real product showing a result**. No documented case shows a cartoon account driving audited third-party affiliate GMV on an $80–250 product. Synthetic presenters carry a real authenticity/trust deficit that bites hardest exactly in the high-consideration band you're targeting.

**The fix preserves your whole insight.** Split the two jobs the character was doing:

> **Character = the attention/audience/world engine (top of funnel). Real-product b-roll = the thing that actually converts (bottom of funnel).**

This is the "faceless product UGC" format you already selected — just with the explicit rule that **the selling shot is the real product in real hands/use, framed by your characters' world and voice**, not the cartoon "holding" a SKU. That format is the cheapest documented winner (one case: 543% GMV lift, 8.69 ROAS) and sidesteps the synthetic-conversion problem without requiring a human face on camera.

---

## What verification changed (don't over-claim these)

1. **Retire the "81% vs 63% trust" stat.** It's of uncertain provenance and measures *trust*, not *conversion* — the agents inferred a conversion claim from a trust figure. The defensible version: *"AI-generated influencer content measurably lowers perceived authenticity/brand trust (JMSR study), and AI UGC converts below human UGC; no audited evidence supports cartoon characters converting cold high-AUP affiliate sales."*
2. **Soften "no cases exist."** Virtual influencers (Lu do Magalu ~$16M/yr, Lil Miquela) *do* move money — but as **brand-owned mascots or paid sponsorships in IP/merch**, not cold third-party affiliate. The one genuine character exception is **IP / collectible / fandom-merch with an owned audience** (e.g. a $150 branded figure to your own fans) — worth noting, not your generic high-AUP case.
3. **The "1,000 followers" bar has a second gate.** 1,000 lets you *join/bind* as an affiliate; promoting *other sellers'* products via the open **Product Marketplace effectively wants 5,000**, with a restricted 30-day pilot in the 1k–5k band (≥95% shop-score products, ~5 promo videos + 3 LIVEs/week cap). **Seller-onboarded "Official Shop Creator" = no follower minimum** (but you can only promote that one seller). *(verified MED-HIGH.)*
4. **Risk Node #1 is downgraded — a ToS-safe official path exists.** Use **TikTok Shop's first-party Affiliate Open API** (confirmed, launched Sept 2024 — campaigns, creator/product search, link generation, order/conversion tracking) as the spine, optionally augmented by **Kalodata's Enterprise Open API** for modeled signals (GMV growth, saturation, ad/organic split). **Never scrape Kalodata's UI** — its ToS §4.1.8 verbatim prohibits automated collection. *(verified HIGH for the TikTok API + scraping prohibition; MED-HIGH for Kalodata API; CSV-export claim only MED.)*

---

## Recommended model (revised flywheel)

```
Character story series (free, ~$0/video local)  ──►  Audience + parasocial trust
        │                                                      │
        │  (at ≥1k followers / eligibility)                    ▼
        ▼                                          Faceless product UGC:
Sourcing: TikTok Affiliate Open API (+Kalodata)        characters' WORLD + VOICE
  → composite score → shortlist 4–8 products              wraps REAL-PRODUCT B-ROLL
        │                                                      │  (organic test)
        └──────────────────────────────────────►   Winners only → Spark Ads
                                                          │  (ROAS ≥ ~3.3 gate)
                                                          ▼
                                                 30%+ commission on $80–250 AUP
                                                          │
                                                 Brand trust → better terms
```

Your characters never disappear — they remain the recognizable hook, the narrator, and the reason people watch. They just stop being the *demonstrator* of the product.

---

## Phased roadmap (gated by real thresholds, additive to current build)

**Phase 0 — Finish the v0 character pipeline & grow to 1k (now).**
The pipeline is still `NotImplementedError` stubs — finish M0–M9 (BUILD.md). Post character content on the **US-region account** file 14 prescribes. Goal: cross **1,000 followers** + keep account in good standing. *Affiliate work does not gate this.*

**Phase 1 — Make the pipeline affiliate-capable (additive, no fork).** *(from 02)*
- Extend `schemas.py` **additively, all default-valued** so existing episodes still validate: a `Product` model (name, affiliate_link, AUP, commission, demo notes, real-asset refs), optional `Scene.scene_type` (`story` / `product_demo` / `product_broll` / `cta`), `Caption` disclosure + showcase fields, `Episode.mode`, `SeriesBible.product_slots`.
- New stage `sourcing.py` (reads official-API/export data → composite score → shortlist), runs before `script`.
- `script_gen` gets a mode branch (weave a real-product b-roll + CTA scene into a story episode).
- **Reuse as-is:** tts, captions, music, hook, ken_burns, the resumable `STAGES`/`state.json` orchestrator, assemble (additive only).
- **Fix the QC gate:** `min_duration_sec: 62` fights short shoppable UGC — add an affiliate-specific duration target.
- **Defer `avatar.py`** (lip-synced talking head) — it's the only genuinely net-new render stage and the lowest-priority format given the evidence.

**Phase 2 — Inject products & run the organic→paid loop.** *(from 04, 05)*
- Source real-product b-roll for each shortlisted SKU (the one input the pipeline can't synthesize — the product must be physically handled on camera).
- **Compliance, mandatory:** the pipeline forces the AI label ON, but affiliate adds a **SECOND mandatory toggle — "disclose commercial content"** — missing it silently kills For-You reach. Bake both into the schema + QC gate. File a separate **W-9** (commissions = 1099-NEC).
- Organic-test gate before any spend: **≥45–50% completion, ≥500 engagements, ≥1% organic link-CTR, ≥1 organic sale.** Only winners get Spark Ads (needs ≥5k for open marketplace, or seller-bound path).
- Spend gate: **break-even ROAS ≈ 3.3 gross** (≈4.2 after ~20% returns) vs TikTok's ~2.2 average — i.e. paid only works on already-proven creative. Concentrate budget on the current winner across a 4–8 product portfolio.

---

## Economics snapshot *(05)*
- Per sale: 30% × $80–250 = **$24–75 gross**, ~$19–60 net after returns. Organic content ≈ $0 → organic sales are near-pure margin.
- 30%+ commission is realistic in **premium beauty/wellness/home/fashion**, NOT electronics (5–13%). **But** content research (01) constrains *your* viable category to what the characters can credibly frame — **kitchen / home / gadget** fits a fridge-detectives world; beauty/apparel/supplements are immersion mismatches. **The overlap of "30%+ high-AUP" ∩ "character-credible" is the real sourcing filter** and may be narrow — flagged as an open question.

---

## Confidence & the one thing to validate before building much

- **High:** affiliate > Creator-Rewards economically; eligibility far easier; official ToS-safe data path exists; architecture is additive/low-risk; dual-disclosure compliance requirement.
- **Medium:** that character-framed **real-product b-roll** converts well enough on high-AUP to clear the ROAS gate. This is the single biggest unvalidated assumption.
- **The cheap experiment that de-risks everything:** once at ~1k followers, run **one manual organic affiliate test** — a real-product b-roll video framed in your character world, with the showcase link — and measure link-CTR + conversion **before** investing in the `sourcing.py`/scoring build-out or any ad spend. Empirics here are worth more than more research.

## Open questions
- Size of the "30%+ high-AUP" ∩ "character-credible category" overlap (sourcing fill rate).
- Kalodata Enterprise API/CSV exact field coverage + price (behind a sales gate; CSV export only MED-confidence).
- Whether brands will approve Spark Ads on visibly AI/animated-framed content per-video (gated by brand authorization + ad review).
