# MASTER — Affiliate Pivot: TikTok Shop Affiliate Flywheel on the Character-Video Pipeline

**Question:** Given our current local character-video pipeline (script → FLUX images → Ken Burns → Kokoro TTS → captions → music → assemble → QC → ready_to_post, monetized by Creator Rewards), how do we evolve it to capture **TikTok Shop affiliate revenue** (30%+ commission on $80–250 AUP products) — by building an audience with the character series, then **injecting products into the established story world** — and what concretely changes in architecture, sourcing, compliance, and economics?

**Owner:** Andrew · **Started:** 2026-06-10 · **Working dir:** `/Users/andrewbishop/video-gen`
**Source doc:** `~/Downloads/tiktok-affiliate-flywheel.md` · **Prior research:** `research/MASTER.md` (files 01–15)

---

## Locked decisions (from scoping)
1. **Content format:** faceless product UGC + AI-avatar presenter — both realized through the **existing cartoon characters as the presenters/vehicle**.
2. **Strategic frame:** character series = audience front-end → at eligibility, inject products into the story world (sidesteps synthetic-UGC authenticity penalty via established-IP trust).
3. **Reuse posture:** reuse pipeline components, add a new affiliate content track (one codebase, two modes).
4. **Kalodata:** not yet acquired — evaluate cost, official API/export vs scraping ToS, and alternatives.
5. **Depth:** thorough — 6 subagents.

## Budget plan (mindful of usage)
6 parallel subagents, each scoped to ONE area and ONE findings file with structured claims (claim → evidence → source → confidence). Agents reuse existing `research/` files (06/07/08/14 etc.) rather than re-researching settled ground, and use targeted web search only for new/affiliate-specific questions. After fan-out: verify only load-bearing claims, then synthesize the recommended path.

---

## Subtask tracker

| # | Subtask | Scope (one line) | Status | Findings file |
|---|---------|------------------|--------|---------------|
| 01 | Content strategy & character-IP affiliate viability | Does product-injection into cartoon stories convert? Format mapping onto our characters; disclosure/authenticity fit | ✅ | [01-content-strategy.md](01-content-strategy.md) |
| 02 | Repo architecture & code-change map | Concrete changes to schemas/stages/settings/orchestrator; reuse vs modify vs add; migration from current code | ✅ | [02-architecture-changes.md](02-architecture-changes.md) |
| 03 | Kalodata & sourcing data layer | Access cost, official API/export vs scraping ToS (Risk #1), alternatives, composite-score automation | ✅ | [03-data-sourcing-layer.md](03-data-sourcing-layer.md) |
| 04 | Affiliate mechanics, eligibility & Spark Ads compliance | Affiliate Center thresholds, region (Canadian-in-US), attribution, AI disclosure, branded-content toggle, Spark Ads approval (Risk #2) | ✅ | [04-affiliate-mechanics-compliance.md](04-affiliate-mechanics-compliance.md) |
| 05 | Affiliate unit economics & paid scaling | Re-derive economics for commission-on-sales (not RPM); ROAS; organic-test-before-spend gate; break-even | ✅ | [05-economics-paid-scaling.md](05-economics-paid-scaling.md) |
| 06 | Market evidence & competitive proof points | Who actually runs faceless/animated TikTok Shop affiliate accounts; what formats win for high-AUP; category fit | ✅ | [06-market-evidence.md](06-market-evidence.md) |

Legend: ⬜ not started · ⏳ in progress · ✅ done · ⚠️ blocked

---

## Subtask summaries (orchestrator notes)
- **01 Content:** LOW-MED confidence in "characters demo high-AUP products." Positive evidence is all for faceless *real-product b-roll* (one case: 543% GMV, 8.69 ROAS) or mascots endorsing their OWN brand — not fictional characters hawking 3rd-party SKUs. AI/synthetic trust gap (81%→63%) bites hardest above $30. Recommends faceless-UGC-with-real-b-roll as primary; pure character-demo as A/B with a conversion kill-switch; category lane constrained to what the character can credibly feature (kitchen/home/gadget fit; beauty/apparel/supplements mismatch).
- **02 Architecture:** Keep ONE `Episode` contract, add affiliate fields (Product model, optional `Scene.scene_type`, `Caption` disclosure/showcase fields, `Episode.mode`, `SeriesBible.product_slots`), all default-valued → existing episodes validate unchanged. Two new stages: `sourcing.py` (export reader + scorer, before script) and `avatar.py` (talking-head, built last). Render spine + resumable orchestrator reused as-is. Friction: avatar format has no home (net-new stage); `min_duration_sec:62` QC gate fights short shoppable UGC; pipeline is still NotImplementedError stubs (affiliate interleaves with M0–M9 build).
- **03 Data:** Revises Risk Node #1 — a ToS-safe official path EXISTS. Recommend hybrid: TikTok Shop Affiliate Open API (first-party, free) for gating vars + order tracking, plus Kalodata Enterprise Open API + official CSV export for modeled signals (GMV growth, saturation, ad/organic split). UI scraping = explicit ToS breach (Kalodata ToS §4.1.8) → never put production on a scraper. Caveats: pricing volatile/undisclosed; API field coverage unverified behind Enterprise gate.
- **04 Compliance:** Affiliate eligibility = 1,000 followers + 18+ + US-based + clean standing (vs Creator Rewards' 10K/100K-views) — far lower bar; Official-Shop-Creator path has NO follower min. Owner eligible on the same US-region account file 14 prescribes; affiliate adds a hard "US-based" req + separate W-9 (1099-NEC). Commissions 5–30% (30% only via targeted/exclusive plans), 7-day-click attribution. BIGGEST LANDMINE: a SECOND mandatory "disclose commercial content" toggle on top of the AI label — pipeline doesn't handle it; missing it silently kills reach. Animated content not banned from Spark Ads but gated by per-video brand authorization + both toggles + ad-review.
- **05 Economics:** 30% on $80–250 = $24–75 gross/sale (~$19–60 net after ~20% returns). Break-even ROAS ≈ 3.3 gross (4.2 after returns) vs TikTok avg eComm ROAS ~2.2 → quantitative proof that paid loses money without proven creative; organic free-content gate filters for the rare creative that clears it. Proposed gate: ≥45–50% completion, ≥500 engagements, ≥1% organic link-CTR, ≥1 organic sale. vs Creator Rewards: one $120 sale ≈ 60–90k qualified views of RPM → 2–4 orders of magnitude better $/effort; decouples revenue from follower count. Dominant unvalidated assumption: whether character content hits ≥2% CVR on high-AUP.
- **06 Market evidence:** SUBSTANTIALLY UNDERMINES the animated-character thesis. Every documented winner uses a real person and/or physically handled real product showing a result; no surfaced case of a cartoon account driving meaningful 3rd-party high-AUP affiliate GMV. Best animated proof (Duolingo's Duo) drives engagement for its OWN app, not 3rd-party conversion. Real moats (cycle-time, relationships) confirmed. Survivable reframing: character = top-of-funnel attention engine only; real-product demo does the selling.

## Progress log
- 2026-06-10 — Scoping complete (4 decisions locked). Master created. 6 subagents dispatched.
- 2026-06-10 — All 6 subagents returned and wrote findings files. Strong convergence (01/05/06) that the "characters demo high-AUP products" step is the weak link; the audience-front-end half is sound. Dispatching verifiers on load-bearing claims before synthesis.

## Load-bearing claims to verify
1. Animated/synthetic content underperforms on high-AUP affiliate CONVERSION + no documented animated account drives 3rd-party affiliate GMV (the thesis-killer; asserted by 01/05/06, partly on an 81%/63% trust stat). → adversarial refute attempt.
2. TikTok Shop affiliate creator threshold = 1,000 followers (2026) — sets when he can start. → fact-check.
3. Official ToS-safe API path exists (Kalodata Open API + TikTok Shop Affiliate Open API) — revises Risk Node #1. → fact-check.
4. Break-even ROAS ≈ 3.3 — core is arithmetic (1/0.30); accepted, external "TikTok avg 2.2" benchmark noted as medium-confidence.

## Synthesis
✅ **Written → [synthesis.md](synthesis.md)** (2026-06-10).

**Verification results:**
- Claim 1 (animated content can't convert high-AUP / no documented cases): **PARTIALLY-STANDS, MEDIUM.** Operational conclusion holds (lead with real person/real-product handling), but "no cases" is overstated (virtual influencers move money in brand-owned/IP-merch contexts) and the 81/63 trust stat is misapplied (trust ≠ conversion) → retired. Survivable reframe: character = attention engine, real-product b-roll = the seller.
- Claim 2 (1k followers): **PARTIALLY CONFIRMED, MED-HIGH.** 1k to join/bind; open Product Marketplace effectively wants 5k (30-day restricted pilot in 1k–5k); seller-onboarded Official Shop Creator = no minimum.
- Claim 3 (ToS-safe official API path): **CONFIRMED.** TikTok Shop Affiliate Open API (HIGH, first-party), Kalodata Open API exists (MED-HIGH, Enterprise-gated), Kalodata CSV export (MED), Kalodata ToS §4.1.8 bans scraping (HIGH).
- Claim 4 (break-even ROAS ≈3.3): accepted (arithmetic 1/0.30); TikTok avg ~2.2 benchmark = medium-confidence.

**Bottom line:** pivot is worth doing; preserve the character-series-as-audience-engine insight; fix the conversion mechanism (real-product b-roll does the selling, characters provide world/voice/attention); finish v0 → grow to 1k → run ONE manual organic affiliate test before building the sourcing/scoring stack or spending on ads.

- 2026-06-10 — Verification (2 adversarial agents) complete; synthesis written. Research phase complete.
