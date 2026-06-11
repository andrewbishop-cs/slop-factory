# 05 — Affiliate Unit Economics & Paid Scaling
*Subtask 05 of the TikTok Shop affiliate-pivot research. Last updated: June 2026.*

Re-derives the money model for **commission-on-sales** (TikTok Shop affiliate), NOT the view-based Creator Rewards / RPM model in `research/08-economics-profitability.md` and `research/13-optimal-path-to-money.md`. Those remain valid for the *old* model; this file supersedes them for the affiliate pivot.

Format: each claim has **evidence/math**, **source**, **confidence (high/med/low)**. Assumptions are flagged explicitly.

---

## TL;DR for the orchestrator

- **Per sale:** 30% commission on a $80–250 AUP product = **$24–75 gross/sale**, ~**$18–56 net** after returns/clawback drag.
- **Break-even ROAS** on Spark Ads at 30% commission ≈ **3.3** (you must generate $3.30 of GMV per $1 ad spend just to recover spend; the brand pays the commission, so your "revenue" per GMV dollar is the 30% commission). TikTok eCommerce average ROAS is ~2.2 — **below break-even** — which is exactly why the organic-proof gate is non-negotiable.
- **vs. Creator Rewards:** one $120 affiliate sale (~$36 gross) equals the Creator-Rewards payout of **~50,000–90,000 qualified views** at $0.40–0.70 RPM. Affiliate is **2–4 orders of magnitude better $/effort per converting viewer**.

---

## 1. Per-Sale Unit Economics (the core model)

### Claim 1.1 — A single high-AUP affiliate sale pays $24–75 gross.
**Math:** commission = commission_rate × AUP.
- $80 AUP × 30% = **$24**
- $120 AUP × 30% = **$36**
- $250 AUP × 30% = **$75**

This is the central lever. The source flywheel doc gates on AUP $80–250 and commission ≥30% precisely because per-sale dollars, not per-view fractions of a cent, are what let paid traffic close.
**Source:** flywheel doc "The Economic Engine"; arithmetic.
**Confidence:** high (arithmetic), medium on whether 30% is *sustainable* at high AUP (see 1.3).

### Claim 1.2 — Realistic *net* commission is meaningfully below gross because of returns + clawback drag.
**Math (worked example from source):** $10,000 GMV @ 20% commission, 25% return rate:
- Gross commission paid: $2,000
- But returns claw back commission only if the return lands inside the 15–31 day settlement window; revenue is still lost.
- Effective commission rate works out to **$2,000 / $7,500 net GMV = 26.6%** — i.e. the *nominal* rate understates your real cost-of-sale exposure (this is a brand-side cost figure, but the symmetric creator-side risk is clawback of any commission on returned/refunded orders before payout).
- **Creator-side haircut assumption:** apply a **15–25% return/clawback haircut** to gross affiliate commission for high-AUP discretionary goods (higher return rates than cheap impulse buys). $36 gross → ~**$27–31 net**.
**Source:** dashboardly.io (2026 clawback/profit math); flag = the 26.6% figure is a brand cost metric, repurposed here as evidence that returns are a real drag.
**Confidence:** medium. **ASSUMPTION:** 15–25% return haircut is my estimate for the $80–250 band; not directly measured.

### Claim 1.3 — High AUP and high commission are in tension; 30% on $80–250 is optimistic for some categories.
**Evidence:** 2026 category norms:
- US market average commission across all categories: **~13%** (one source cites 13.02%).
- Beauty/personal care: 18–30% (premium/VIP tiers reach 30%+).
- Fashion: 10–22%.
- **Electronics / high-ticket tech: 5–13%** — explicitly lower because high AOV + thin hardware margins leave less room.
**Implication:** the flywheel's "$80–250 AUP **AND** ≥30% commission" sweet spot is most achievable in **premium beauty, wellness, supplements, home, and fashion-adjacent** categories — NOT electronics. The Kalodata filter (AUP $80–250 · commission ≥30%) will naturally exclude most electronics. This is a feature: it steers sourcing toward categories where the unit economics actually work.
**Source:** dashboardly.io, shortformnation.com, hamstergarage.com (2026 commission data).
**Confidence:** high on the category split; the $80–250 @ 30% combo exists but is a *narrow* slice — flag for sourcing (subtask on sourcing should confirm fill rate).

### Unit-economics model (per sale)

| Line | Low ($80 AUP) | Mid ($120 AUP) | High ($250 AUP) |
|---|---|---|---|
| AUP | $80 | $120 | $250 |
| Commission rate | 30% | 30% | 30% |
| **Gross commission** | **$24.00** | **$36.00** | **$75.00** |
| Return/clawback haircut (−20%, assumed) | −$4.80 | −$7.20 | −$15.00 |
| **Net commission/sale** | **$19.20** | **$28.80** | **$60.00** |
| Marginal content cost (amortized, see §5) | ~$0 | ~$0 | ~$0 |
| **Net contribution/sale (organic)** | **~$19** | **~$29** | **~$60** |

Organic content cost is effectively $0 (M5 Max local pipeline + ~$0.08/episode Opus script call per BUILD.md / MASTER.md), so on organic traffic **every sale is almost pure margin**. Paid traffic adds an ad-cost line — that's §3.

---

## 2. Contrast With the Prior RPM / Creator-Rewards Model

### Claim 2.1 — High-AUP affiliate is 2–4 orders of magnitude better $/effort than view-based RPM.
**Math — RPM model (from file 08):** blended entertainment RPM $0.40–0.70 per 1,000 *qualified* views; ~55% of total views qualify. So per 1,000 *total* views ≈ $0.22–0.39.
**Math — equivalence:** one $120 affiliate sale (~$36 gross / ~$29 net) equals:
- $36 / $0.0006 per qualified view = **~60,000 qualified views** of Creator Rewards (≈ 90,000+ total views) at $0.60 RPM.
- At the pessimistic $0.40 RPM that's **~90,000 qualified views** (~160,000 total) per single sale-equivalent.

**Interpretation:** a video that drives even **one** high-AUP sale out-earns a video that pulls ~90k views but converts nothing. The affiliate model monetizes *intent* (a click-to-purchase) rather than *attention* (a 5-second qualified view), and intent on a $120 product is worth ~$36 vs. a qualified view worth ~$0.0006.
**Source:** file 08 RPM figures; arithmetic.
**Confidence:** high (arithmetic on stated RPMs).

### Claim 2.2 — The two models have opposite cost structures and break-even logic.
| Dimension | Creator Rewards (old) | High-AUP Affiliate (new) |
|---|---|---|
| Revenue unit | per 1,000 qualified views | per attributed sale |
| Rate | $0.40–0.70 RPM | $24–75/sale (gross) |
| Eligibility gate | 10k followers + 100k views/30d | **1,000 followers** to enable Shop affiliate |
| Monetizes | attention | purchase intent |
| Cost to scale | $0 (organic only — can't buy RPM) | $0 organic **+ paid ad spend** (Spark Ads) |
| Break-even question | "enough views?" | "ROAS > break-even?" |
| Power-law dependence | extreme (1 viral = months) | softer — a steady 2–5% converting video on paid traffic compounds |
**Source:** file 08, file 13, flywheel doc.
**Confidence:** high.

### Claim 2.3 — Affiliate unlocks revenue ~9x earlier in the account lifecycle.
**Evidence:** TikTok Shop affiliate enables at **1,000 followers**; Creator Rewards needs **10,000 followers + 100,000 views/30 days** (file 13, Stage 1–2). Affiliate can earn in weeks 1–6 vs. Creator Rewards' typical months 4–6.
**Source:** file 13 staged plan.
**Confidence:** high. **ASSUMPTION:** the 1,000-follower TikTok Shop affiliate threshold persists in 2026 (program terms change often — flywheel doc risk note).

---

## 3. Spark Ads / Paid Scaling Math

### Claim 3.1 — Break-even ROAS at 30% commission ≈ 3.3.
**Definition:** ROAS = GMV generated / ad spend. Your revenue is the *commission* on that GMV, not the GMV.
**Math:** break-even (ignoring returns) requires commission_revenue ≥ ad_spend:
- commission_rate × GMV ≥ ad_spend
- 0.30 × GMV ≥ ad_spend
- GMV/ad_spend ≥ 1/0.30 = **3.33 → break-even ROAS ≈ 3.3**.

With the 20% return haircut, effective commission ≈ 24% → break-even ROAS = 1/0.24 ≈ **4.2**.
**Profit target:** to keep ~50% of commission as profit you need ROAS ≈ **6.7** (gross) / **~8.4** (after haircut).
**Source:** arithmetic on flywheel's 30% commission assumption.
**Confidence:** high (math). The key insight: **commission affiliates need a much higher ROAS than a brand selling its own product**, because you only keep 24–30% of each GMV dollar, not the full margin.

### Claim 3.2 — TikTok eCommerce average ROAS (~2.2) is BELOW affiliate break-even — proving the organic-gate thesis.
**Evidence:** TikTok average eCommerce ROAS **2.21** (Triple Whale 2026). FMCG with a hybrid auction + reach/frequency buy averaged **5.7**; hybrid buying lifted ROAS **33.8%** vs. single buy type.
**Interpretation:** *average* TikTok paid traffic (ROAS ~2.2) loses money for a 30%-commission affiliate (needs ~3.3+). Only **above-average, proven-creative** campaigns (the 5.7 FMCG tier) clear break-even with margin. This is the quantitative backbone of the flywheel's "paid affiliate traffic loses money fast if creatives aren't proven first" — the average ad **does** lose money; you must be in the top tier, and the only cheap way to find top-tier creative is the free organic test.
**Source:** triplewhale.com, tikadsuite.com (2026 benchmarks); flywheel doc.
**Confidence:** high.

### Claim 3.3 — Expected CPM/CPC/CVR inputs for the model (2026).
**Evidence (ranges across sources — wide, so model with a band):**
- **CPM:** Spark Ads effective ~$3.54; TikTok blended ~$4.73; conversion-optimized eCommerce ~$4.80 (Lebesgue) to **$9.16 (WebFX)** to **$13.26 (Triple Whale)**. Use **$8–10 CPM** as a planning midpoint for conversion campaigns; Spark Ads run cheaper than cold in-feed.
- **CTR:** platform ~1.77% (2025); Spark Ads with strong creator content **2.0%+**.
- **CVR (click→purchase):** TikTok ad average **~2.0%**; healthy 2–3%; >3% strong. Beauty 2.19%, home/garden 2.42%.
- **Spark Ads edge:** built from organic posts with **500+ prior engagements → 52.4% lower CPC and 44.6% higher landing-page-visit rate** vs. ads from freshly published posts. Spark Ads show 30–142% higher completion and ~69% higher conversion (90-day consistent use) vs. non-Spark in-feed.
**Source:** triplewhale.com, webfx.com, tikadsuite.com, amraandelma.com, digitalapplied.com (2026).
**Confidence:** medium — benchmark spread is large; treat as a band, not a point.

### Claim 3.4 — Worked Spark Ads break-even funnel ($120 AUP, 30% commission).
**ASSUMPTIONS:** CPM $9, CTR 2% (Spark, proven creative), CVR 2.5% (above-average because creative is organic-proven), $120 AUP, 30% commission, 20% return haircut.

```
Spend $100 at $9 CPM        → 11,111 impressions
× 2% CTR                    → 222 clicks
× 2.5% CVR                  → 5.56 sales
× $120 AUP                  → $666 GMV   (ROAS = 6.66)
× 30% commission            → $200 gross commission
× 0.80 (return haircut)     → $160 net commission
− $100 ad spend             → +$60 net profit on $100 spend
```
**Result:** at these *proven-creative* inputs, $100 spend returns ~**$160 net commission → 1.6x net, $60 profit**, ROAS 6.7 (above the 3.3 gross / 4.2 net break-even). Now flip CVR to the platform-average 1.0% and CTR to 1.77%:

```
$100 → 11,111 impr × 1.77% = 197 clicks × 1.0% = 1.97 sales × $120 = $236 GMV
ROAS 2.36 → $71 gross commission × 0.80 = $57 net − $100 spend = −$43 LOSS.
```
**This is the kill/scale fulcrum in one table:** the difference between +$60 and −$43 on identical spend is entirely creative quality (CTR + CVR). Proven creative scales; average creative bleeds.
**Source:** synthesis of §3.3 benchmarks + flywheel 30% assumption.
**Confidence:** medium (assumption-driven illustration; CVR is the most sensitive input — flag).

---

## 2.5 / 4. The Organic-Test-Before-Spend Gate (quantitative "proven")

### Claim 4.1 — "Proven" should be defined on organic signals that *predict* paid CTR/CVR, before any spend.
**Evidence:** watch-time-as-%-of-length is the strongest organic ranking signal in 2026; Spark Ads from posts with **500+ engagements** materially outperform (52.4% lower CPC). Organic CVR on TikTok runs 1–5%.
**Proposed gate (the video must clear ALL before it gets ad budget):**
| Signal | Threshold (proposed) | Why |
|---|---|---|
| Watch-through / completion | **≥ 45–50%** | strongest 2026 ranking signal; predicts paid hold |
| Organic engagement | **≥ 500 engagements** (likes+comments+shares) | the documented Spark-Ads CPC cliff |
| Click-through to product (organic) | **≥ 1%** of views tap the link | proves the creative drives intent, not just watch |
| At least 1–3 organic attributed sales | **≥ 1 sale** | direct proof the funnel converts at this AUP |
| CTR proxy / save+share rate | top quartile of the brand's batch | relative winner selection |
**ASSUMPTION:** thresholds are synthesized from benchmarks, not a single cited rule (no source publishes a canonical "scale gate"). Tune per brand after first cohort.
**Source:** tikadsuite.com, stackmatix.com, ecommop.com (2026); thresholds are my synthesis — flagged low-confidence on exact numbers.
**Confidence:** medium on the *logic*, low on exact threshold values.

### Claim 4.2 — Why average paid traffic loses money (the gate's economic justification).
Restating §3.2 as the gate rationale: average TikTok eCommerce ROAS 2.2 < break-even 3.3–4.2 for a 30% affiliate. **The expected value of spending behind an *unproven* creative is negative.** The organic test costs ~$0 (local generation) and converts the bet from "negative-EV blind spend" to "positive-EV spend behind a creative already exhibiting top-quartile CTR/retention/conversion." The gate is free insurance against the −$43/$100 outcome in §3.4.
**Source:** §3.2 + §3.4 synthesis.
**Confidence:** high (follows from the ROAS math).

---

## 5. Full-Funnel Economics for OUR Model & Portfolio Allocation

### Claim 5.1 — The funnel: free organic audience (cost ~$0) → product injection → commissions → reinvest into Spark Ads.
**Cost facts:** pipeline runs ~$0 locally on M5 Max; ~$0.08/episode for the Opus script call (BUILD.md / MASTER.md). At 2–3 episodes/day that's **~$5–7/month** all-in content cost. So the *organic* arm of the flywheel is essentially free, and **the only real cash input is ad spend**, which is discretionary and gated.
**Funnel stages and where money enters/exits:**
1. Organic character content (cost ~$0) builds audience + generates free creative-performance data.
2. Inject affiliate products into the proven character format → first organic commissions (pure margin, §1).
3. Winners (passing §4 gate) get Spark Ads spend → paid commissions at ROAS > break-even.
4. Commission revenue **partly funds the next ad round** (recycle, see 5.2).
**Source:** flywheel doc; BUILD.md/MASTER.md cost facts.
**Confidence:** high on costs; medium on conversion behavior of *character/UGC* content for affiliate (see risk 5.5).

### Claim 5.2 — Commission revenue partially self-funds ad scaling, but does NOT fully bootstrap from $0.
**Math:** at the §3.4 proven-creative case, $100 spend → $160 net commission. **Recycle ratio ≈ 1.6x per cycle** — but commission settles on a **15–31 day delay** (settlement window), and the first round must be funded from organic commissions or seed capital. So:
- **Cold start:** organic-only commissions accumulate first (weeks 1–8), funding an initial **~$300–1,000 ad seed**.
- **Self-funding once proven:** above break-even, each cycle returns 1.4–1.7x, so spend can grow ~30–60%/cycle *limited by the 2–4 week settlement cash-flow lag*, not by profitability.
**ASSUMPTION:** seed of $300–1,000; recycle 1.4–1.7x at proven ROAS. Flag: settlement lag means the business is **working-capital constrained, not margin constrained** once creatives are proven.
**Source:** §3.4 + settlement window (dashboardly.io).
**Confidence:** medium.

### Claim 5.3 — Portfolio budget allocation: concentrate on the current weekly winner; Kalodata deceleration = kill.
**Model — "budget concentrates on whatever is winning this week":**
- Run 4–8 brands' proven creatives simultaneously, each as its own ad group (TikTok min **$20/day/ad group**, **$50/day/campaign**; effective conversion-optimization minimum is far higher — **~50 conversions/ad-group/week to exit learning phase**, ≈ $1,250/week at a $25 CPA).
- **Allocation rule (proposed):** weekly, rank ad groups by realized net-ROAS over trailing 7 days; reallocate budget toward top performers (e.g. softmax / proportional-to-ROAS-above-breakeven), floor losers to $0.
- **Kill signals (any triggers pause):** (a) trailing-7d net-ROAS < ~3.3 break-even; (b) **Kalodata GMV growth-rate decelerating** for the product (early signal — the offer is rolling over / saturating before your own ROAS shows it); (c) CVR drop below the §4 gate. Kalodata deceleration is the *leading* indicator; your own ROAS decay is the *lagging* one.
- **Scale signal:** trailing-7d net-ROAS sustained > ~5 AND Kalodata GMV still climbing AND CVR holding → increase budget 30–50%/cycle (capped by settlement cash-flow, §5.2).
**Why a portfolio:** the "up-and-coming" window on a hot product is ~2 weeks (flywheel doc), so 4–8 brands de-risk any single offer dying and ensure there's always a winner to concentrate into.
**Source:** flywheel doc (Stage 4, Kalodata); stackmatix.com/tikadsuite.com (min budgets, learning-phase); allocation rule is my synthesis.
**Confidence:** high on the structure; medium on exact thresholds (tune empirically).

### Claim 5.4 — Break-even point and realistic ramp for the whole model.
**Operating break-even (covers ad spend + ~$7/mo content):**
- On organic alone: trivially profitable from the **first sale** (sale nets ~$19–60, content cost ~$0). The old RPM model needed ~67 views/video just for electricity; the affiliate model needs **one sale** to be cash-positive on content.
- On paid: break-even when blended portfolio net-ROAS ≥ 3.3–4.2. Achievable only with the organic gate filtering for top-quartile creative.
**Realistic ramp (ASSUMPTION-heavy — flag as low/medium confidence, no measured data for this specific character→affiliate model):**
| Phase | Followers | Organic affiliate | Paid (Spark) | Net |
|---|---|---|---|---|
| Wk 1–6 | 0 → 1k | enable at 1k; first organic sales trickle | none (no proven creative yet) | ~$0 to low $ |
| Wk 6–12 | 1k → ~10k | a few sales/wk on winners; accumulate ad seed | begin gated tests, small ($300–1k) | low hundreds $/mo |
| Mo 3–5 | 10k → 30k+ | compounding | scale proven creatives across 4–8 brands; recycle commissions | **$ low–mid thousands/mo** if a winner hits |
| Mo 6+ | 30k+ | + whitelisting/retainer leverage (Stage 5) | concentrated on weekly winners | dominated by paid + relationship terms |
**The asymmetry vs. old model:** old RPM ramp was gated by reaching 10k followers + 100k views *before any meaningful revenue*. The affiliate ramp earns from 1k followers and, more importantly, **decouples revenue from your own audience size** — Spark Ads buy reach, so a small account with a proven creative can generate sales far beyond its organic following. That's the structural unlock.
**Source:** flywheel doc, file 13 timeline (re-derived), §1–3 math.
**Confidence:** low–medium on the ramp $ figures (no model-specific data); high on the *structural* point that affiliate decouples revenue from follower count.

### Claim 5.5 — Sensitivity & the dominant risk: CVR of synthetic character/UGC content.
**Evidence:** CVR is by far the most sensitive input (§3.4: same spend swings +$60 to −$43 on CVR alone). The flywheel doc flags that **fully synthetic UGC underperforms on conversion** and can trip Spark Ads brand-approval / disclosure rules — "the variable ROAS is most sensitive to." Our model uses *character* content, not human UGC, which is even less proven for driving purchase intent on $80–250 products.
**Implication:** the entire paid arm's profitability hinges on whether character-driven content can hit ≥2% CVR on high-AUP affiliate. This is **unvalidated** and is the single biggest assumption in this analysis. **Mitigation:** the organic gate (§4) catches this for free — if character content can't clear the organic CVR/CTR thresholds, no spend is ever risked, so the downside is bounded to ~$0.
**Source:** flywheel doc risk nodes; §3.4.
**Confidence:** high that this is the key risk; low on whether character content actually converts (needs empirical test — recommend the orchestrator flag this as the #1 thing to validate).

---

## Assumptions Log (explicit)
1. **30% commission @ $80–250 AUP** is achievable — true mainly in premium beauty/wellness/home/fashion; NOT electronics (5–13%). Sourcing must confirm fill rate. (Claim 1.3)
2. **Return/clawback haircut = 20%** on net commission — estimate for discretionary high-AUP goods, not measured. (1.2)
3. **CVR for character/synthetic content ≥ 2%** — unvalidated; the dominant risk. (5.5)
4. **Spark Ads inputs**: CPM $8–10, CTR 2%, CVR 2.5% for *proven* creative — midpoints of a wide 2026 benchmark band. (3.3–3.4)
5. **§4 gate thresholds** (45–50% completion, 500 engagements, ≥1% link CTR, ≥1 organic sale) — synthesized from benchmarks, not a cited canonical rule; tune per cohort. (4.1)
6. **1,000-follower TikTok Shop affiliate threshold** persists in 2026 (program terms change often). (2.3)
7. **Ramp $ figures** — illustrative, no model-specific data exists. (5.4)

## Sources
- dashboardly.io — TikTok Shop Affiliate Commission 2026 (clawbacks, 26.6% effective, settlement window)
- shortformnation.com, hamstergarage.com — 2026 commission rates by category/tier
- triplewhale.com — TikTok ads benchmarks (ROAS 2.21, FMCG hybrid 5.7, CPM $13.26)
- tikadsuite.com — TikTok ad benchmarks & conversion-rate benchmarks 2026 (CVR 2.01%, CTR 1.77%, Spark Ads CPM $3.54)
- webfx.com — CPM $9.16, CTR 0.84%
- digitalapplied.com, amraandelma.com — Spark Ads stats (completion/conversion lift, 500+ engagement CPC cliff)
- stackmatix.com — TikTok min daily budgets 2026 ($50 campaign / $20 ad group; ~50 conv/wk learning phase)
- ecommop.com — TikTok Shop organic conversion
- Internal: `research/08-economics-profitability.md`, `research/13-optimal-path-to-money.md`, `Downloads/tiktok-affiliate-flywheel.md`, BUILD.md/MASTER.md cost facts
