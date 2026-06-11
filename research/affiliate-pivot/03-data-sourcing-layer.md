# Subtask 03 — Kalodata & the Sourcing Data Layer

**Scope:** Kalodata pricing/data, official API vs. scraping, ToS ban-risk, ToS-safe ingestion design, competitor/official alternatives, and implementing the composite sourcing score.

**Date of research:** 2026-06-10. Pricing and ToS change frequently — every pricing/ToS claim below is flagged and should be re-verified against the live page before building on it.

**Headline finding (read first):** The source doc's "Risk Node #1" assumes scraping the Kalodata UI is the only programmatic path. That assumption is **outdated**. Two real de-risking paths now exist: (a) **Kalodata's own Open API** (official, key-gated, on the Enterprise tier), and (b) **TikTok Shop's official Affiliate APIs** (first-party, free to register, exposes product-by-commission/category search and affiliate order data). The single-point-of-failure framing should be revised: a ToS-safe path exists and should be the design default.

---

## 1. Kalodata — Pricing & Data Exposed

### Claim 1.1 — Pricing tiers (2026)
**Claim:** Kalodata sells three tiers: Starter ~$45.90/mo, Professional ~$99/mo, and Enterprise (custom). Annual billing applies ~30% off; usage is metered by searches/day and detail-page-views/day.
**Evidence:** Starter ≈ $45.90/mo (~$38.30/mo annual): 50 searches/day, 100 detail views/day, 10 tracked shops, 90-day history, no creator-contact export, no AI services. Professional ≈ $99/mo (~$83.20 annual): 250 searches/day, 500 detail views/day, 500 tracked shops, 180-day history, creator-contact export, AI services, 1 sub-account. Enterprise: custom — unlimited usage, **full API access**, custom data exports, dedicated manager. 7-day free trial on all tiers. Note: secondary sources also quote a "$49.99" entry price, so the exact entry number drifts between reviewers.
**Source:** https://simptok.com/how-much-is-kalodata/ · https://www.kalodata.com/pricing · https://www.toolsurf.com/kalodata-pricing/
**Confidence:** Medium (third-party review sites agree on the ~$45.90/$99 structure; exact figures change — verify on kalodata.com/pricing).

### Claim 1.2 — Enterprise tier is where API + bulk export live
**Claim:** Official API access and "custom data exports" are gated to the **Enterprise** plan, which is quote-only (not publicly priced).
**Evidence:** Review sources consistently place "full API access" and "custom data exports" under Enterprise. Public price is undisclosed; third-party estimates range widely ($229–$997+/mo) and are speculative — treat as unknown until a sales quote is obtained from Kalodata ("Charm" is the named sales contact).
**Source:** https://simptok.com/how-much-is-kalodata/ · https://tipsonblogging.com/2025/05/kalodata-pricing/
**Confidence:** Medium on "API is Enterprise-gated"; Low on the dollar figure (all estimates are speculative).

### Claim 1.3 — Data fields exposed (matches the source doc's "Data Layer")
**Claim:** Kalodata exposes product-level GMV + growth rate, commission rate, AUP, sales trend over time, creator/video drivers of GMV, ad-vs-organic split, and category/competitor views — i.e. all fields the composite score needs.
**Evidence:** Aligns with the source doc's "Kalodata — The Data Layer" section and Kalodata's own knowledge base / feature pages. Data is **modeled/estimated**, not actual seller revenue: Kalodata scrapes publicly visible TikTok data (listings, views, engagement, creator profiles) and uses AI to *estimate* sales volume, GMV, and ad spend.
**Source:** https://www.kalodata.com/knowledge · source doc lines 80–91
**Confidence:** High on the field list; High on "modeled not actual" (Kalodata states it estimates GMV).

### Claim 1.4 — Data is estimated, so rankings are "where to look," not ground truth
**Claim:** Because GMV/ad-spend are AI-estimated from public signals, the score should be used as a *screening/ranking* signal, then validated with an organic test before any spend.
**Evidence:** Kalodata's method is scrape-public-data + AI-estimate. Competitor marketing explicitly contrasts "intent" vs. "actual revenue" (FastMoss tracks intent; EchoTik claims actual-revenue accuracy), confirming the whole category is estimation, not seller-reported truth.
**Source:** https://www.echotik.live/blog/echotik-vs-kalodata-vs-fastmoss-more-accurate/ · source doc line 102
**Confidence:** High.

---

## 2. Official API vs. Scraping + ToS (the ban-risk node)

### Claim 2.1 — Kalodata DOES offer an official Open API
**Claim:** A "Kalodata Open API" exists with six modules — Category, Shop, Creator, Product, Video, Livestream — each with ranking + detail endpoints, 20+ interfaces total. Access requires applying for an **access key**; requests are JSON with region/language/currency/date-range params.
**Evidence:** Kalodata Open API overview documents the six modules, 20+ interfaces, and access-key application flow.
**Source:** https://www.scribd.com/document/980319331/Kalodata-Open-API-1 (overview doc) · https://www.kalodata.com/knowledge
**Confidence:** Medium-High that the API exists and has these modules; Low on exact endpoint schemas, rate limits, and field-level coverage (full docs are behind the access-key/Enterprise gate — not publicly verifiable). **Flag:** confirm the API actually returns GMV *growth rate* and *creator count* fields before architecting the score around it.

### Claim 2.2 — Official CSV/manual export exists in the UI
**Claim:** Kalodata supports CSV export from the UI (a Dec 2025 walkthrough exists). Creator-contact export specifically requires Professional+.
**Evidence:** "How to Export Data From Kalodata (CSV) [2026 Full Guide]" (Dec 2025). Tier table gates creator-contact export to Professional.
**Source:** https://www.youtube.com/watch?v=piGiYr9q9KA · https://simptok.com/how-much-is-kalodata/
**Confidence:** Medium (export capability confirmed; exact scope of what's exportable per tier not fully verified).

### Claim 2.3 — ToS PROHIBITS automated scraping/scripts (the ban-risk, confirmed verbatim)
**Claim:** Kalodata's ToS **§4.1.8** explicitly prohibits using "automated scripts to collect information from or otherwise interact with the Services." Related: §4.1.6 bans bypassing access-restriction measures; §4.1.2 bans reverse-engineering; §3.3 lets Kalodata disable any account at its "sole discretion." Breach can trigger account termination **and** a liability/indemnification claim for losses.
**Evidence:** Verbatim from Kalodata's published ToS.
**Source:** https://kalodata.gitbook.io/termsofservice
**Confidence:** High (direct quote from the live ToS as of research date — re-verify section numbering, ToS is versioned).
**>> BAN-RISK FLAG:** UI scraping = explicit ToS violation = account disable at sole discretion + indemnification exposure. If the *entire* sourcing feed runs through one scraped account, it is a true single point of failure exactly as the source doc warns. **Do not build the pipeline on UI scraping.** The official Open API (2.1) and official UI export (2.2) are the sanctioned paths and sidestep §4.1.8 entirely.

---

## 3. ToS-Safe Ingestion Design (concrete recommendation)

### Recommended architecture (decision order)
1. **Primary — TikTok Shop Affiliate Open API (first-party, free).** For the two *gating* variables (commission rate, product/category, open-collaboration status) and for affiliate-order/conversion tracking, use TikTok's own APIs. This is the most ToS-safe path because it is sanctioned, first-party, and doesn't depend on any third-party reseller's account staying un-banned. See §4.
2. **Secondary — Kalodata Enterprise Open API (official, key-gated).** For the *differentiating* signals TikTok's native API does **not** expose — modeled GMV growth rate, sales trend, creator saturation, ad-vs-organic split — subscribe to Enterprise and pull via the access-key API. This is contractually sanctioned (it's their own product), so it does not trip §4.1.8.
3. **Fallback — manual/official CSV export → automated downstream analysis.** If Enterprise API cost is not justified yet, a human runs the saved filter in the UI and triggers the **official CSV export**; the automated scoring pipeline ingests the CSV. This is the design the source doc itself endorses ("manual export + automated downstream analysis is safe"). It is slow and human-gated but ToS-clean.
4. **Never — UI scraping / headless-browser bots / unofficial scraper services** (e.g. Automatio, SociaVault "build a Kalodata clone"). These directly violate §4.1.8 and put the whole feed on one bannable account. Explicitly out of scope for the production pipeline.

### Design rule
Keep **acquisition** (human-triggered official export OR sanctioned API call) cleanly separated from **analysis** (fully automated scoring). The automation lives entirely downstream of a ToS-clean ingestion boundary — a dropped CSV or an API response, never a scraped DOM. This preserves "high automation" on scoring (source doc Stage 1) while removing the ban-risk.

### Resilience
Run **two independent data sources** (e.g. TikTok official API + one of Kalodata/FastMoss/EchoTik) so a ban or API outage on either degrades rather than kills the feed. This directly retires the "single point of failure" from the source doc.

**Source/basis:** §2.3 ToS, §4 alternatives, source doc lines 99–102. **Confidence:** High (design follows directly from the ToS + the existence of official APIs).

---

## 4. Alternatives & Competitors + the Official Path

### Claim 4.1 — A fully-official first-party path EXISTS: TikTok Shop Affiliate APIs
**Claim:** TikTok Shop has officially released Affiliate APIs (via TikTok Shop Partner Center / developers.tiktok.com) that let developers: **find products with open collaborations by category, commission rate, and keyword**; **search creators by GMV/keyword/demographics**; create/manage open + targeted campaigns; **generate affiliate promotion links**; and **search/retrieve affiliate orders for conversion tracking.** Commission rates range 1–80% of GMV. Access: register as an Affiliate app developer on Partner Center; zero App Store listing fees.
**Evidence:** TikTok for Developers launch blog + Partner Center Affiliate Seller/Creator API overview pages.
**Source:** https://developers.tiktok.com/blog/2024-tiktok-shop-affiliate-apis-launch-developer-opportunity · https://partner.tiktokshop.com/docv2/page/affiliate-seller-api-overview · https://partner.tiktokshop.com/docv2/page/affiliate-creator-api-overview
**Confidence:** High that the APIs exist and cover product-by-commission/category search + order tracking; Medium on access friction (Partner Center app review, seller/business authorization likely required — many Partner Center docs are JS-gated and weren't fully verifiable).

### Claim 4.2 — But the official API does NOT expose Kalodata's differentiating signals
**Claim:** TikTok's Affiliate API gives the *gating* variables (commission rate, category, open-collaboration status) and *conversion* data, but does **not** surface modeled **product GMV growth rate, sales trend over time, creator-saturation counts, or ad-vs-organic split** — which are exactly the trend/saturation signals the composite score needs.
**Evidence:** The launch blog's capability list covers search/campaign/links/orders; it does not mention product-level GMV growth or trend analytics. Those are the proprietary modeling layer the third-party tools sell.
**Source:** https://developers.tiktok.com/blog/2024-tiktok-shop-affiliate-apis-launch-developer-opportunity
**Confidence:** Medium-High (absence of mention; verify against full Partner Center field docs).
**Implication:** This is why the design is hybrid — official API for gating + conversions, a third-party tool for trend/saturation. Neither alone covers the full score.

### Alternatives comparison table

| Source | Official API? | Indicative cost (2026, verify) | Data depth | ToS-safety for automation |
|---|---|---|---|---|
| **TikTok Shop Affiliate API** (first-party) | **Yes — sanctioned, first-party** | Free to register; zero App Store listing fee; Partner Center app review | Gating vars (commission, category, open-collab), creator search by GMV, promo links, **affiliate orders/conversions**. No modeled GMV-growth/trend/saturation. | **Safest** — first-party, no third-party ban risk |
| **Kalodata** | Yes — Open API (6 modules, key-gated, **Enterprise tier**) | Starter ~$45.90 / Pro ~$99 / Enterprise custom (API here). API price undisclosed | **Deepest** modeled depth: GMV+growth, AUP, commission, trend, creator/video drivers, ad-vs-organic, category. All score fields. | **API = safe** (sanctioned). **UI scraping = ToS violation §4.1.8 → ban** |
| **FastMoss** | Yes — dedicated **API plan** | Basic ~$47–59 / Pro ~$125–179 / Team ~$399; API custom (~$500–5,000/yr est.) | Strong; markets real-time updates + "intent" trend-spotting; weaker on final GMV accuracy | API = safe; scraping their UI subject to their ToS |
| **EchoTik** | Yes — **TikTok Data API service**; 100 free test calls | ~$9–19/mo entry; custom API plans | Claims **actual-revenue accuracy** vs. estimates; product/creator/video data | API = safe; cheapest entry for API testing |
| **Shoplus** | Limited / not a headline feature | ~$40/mo entry; free limited tier | Budget entry; lighter depth | UI tool; scraping subject to ToS |
| **TikTok Seller Center / Creator Marketplace (TTCM)** | Partial (Seller Center APIs; TTCM via Partner Center) | Tied to seller/partner account | Your own shop's data + marketplace creator collab data; not competitor GMV trends | First-party, safe; not a competitor-radar tool |

**Sources:** https://www.fastmoss.com/pricing · https://echotik.live/en/api-service · https://echotik.live/pricing · https://www.shoplus.net/blogs/kalodata-fastmoss · https://kalodatacoupon.com/Best-tiktok-shop-analytics-tools · https://developers.tiktok.com/blog/2024-tiktok-shop-affiliate-apis-launch-developer-opportunity
**Confidence:** Medium on all dollar figures (third-party, fast-changing — verify each vendor's live pricing page); High on "all four third-party tools offer an official API plan" and "TikTok has a first-party affiliate API."

### Claim 4.3 — Cheapest ToS-safe way to get a third-party API for trend/saturation
**Claim:** **EchoTik** is the lowest-friction paid entry to a sanctioned third-party data API (100 free test calls, ~$9–19/mo entry, custom API plans) and markets actual-revenue accuracy; **FastMoss** has an explicit API plan tier but at higher cost.
**Source:** https://echotik.live/en/api-service · https://www.fastmoss.com/pricing
**Confidence:** Medium.

---

## 5. Implementing the Composite Score

Target formula (source doc line 73):
`score = commission_rate × AUP × GMV_growth_rate × (1 / creator_saturation) × trend_direction`

### Field → source mapping
| Field | Definition | Best ToS-safe source |
|---|---|---|
| `commission_rate` | Affiliate % (gate ≥30%) | **TikTok Affiliate API** (find products by commission rate) or Kalodata API |
| `AUP` | Average unit price (gate $80–250) | TikTok Shop product data / Kalodata product detail |
| `GMV_growth_rate` | WoW or short-window % change in modeled GMV | **Kalodata** (modeled) — *not* in TikTok native API |
| `creator_saturation` | # of creators currently promoting the product | **Kalodata** creator-drivers module — *not* in TikTok native API |
| `trend_direction` | Sales trend slope sign (climbing vs. rolling over) | **Kalodata** sales-trend; cross-check direction of GMV series |
| (gate) open-collab / recruiting | Brand actively accepting affiliates | **TikTok Affiliate API** (products with open collaborations) — authoritative |

### Normalization
- Apply **hard gates first** (drop if commission < 30% or AUP outside $80–250 or brand not open-collab). Gating before scoring prevents a huge GMV from rescuing a 10% offer.
- Normalize each continuous factor to a comparable scale before multiplying — e.g. **percentile rank (0–1) within the candidate set** or min-max per category. Raw multiplication of unbounded units (a $250 AUP × a 400% growth rate) lets one term dominate; percentile-normalize each, or take `log` of AUP and GMV_growth to compress.
- `creator_saturation`: invert as `1/(saturation + k)` with a smoothing constant `k` to avoid divide-by-zero on brand-new products, and **floor** it — the sweet spot is *low-but-rising*, not literally zero (zero creators = unproven). Consider a band penalty rather than pure inverse.
- `trend_direction`: encode as a sign/multiplier in {negative, flat, positive} (e.g. −1 / 0.5 / 1) or the normalized slope, so a rolling-over product is penalized or zeroed regardless of other factors.
- Recommended robust form: `score = Σ wᵢ · normalize(factorᵢ)` (weighted sum of normalized factors) **or** geometric mean, both more stable than raw product. Keep the product form only if every factor is percentile-normalized to (0,1].

### Feeds two downstream consumers
1. **Product selection (Stage 1):** rank gated candidates by score; shortlist the 4–8 "climbing growth + moderate absolute GMV + low-but-rising creator count + trend up" products per the saved filter. Then confirm open/recruiting via the TikTok Affiliate API.
2. **Paid-scaling kill signal (Stage 4):** recompute `GMV_growth_rate` and `trend_direction` on a schedule; when growth decelerates or trend flips negative ("Kalodata deceleration"), fire the early kill/rotate signal to reallocate ad budget. The same normalized series powers both selection and the kill trigger.

**Source/basis:** source doc lines 69–91, 64–66; field availability from §4.1–4.2. **Confidence:** High on field mapping and the gate-then-score + normalize-before-multiply recommendation; the exact weights/normalization are an implementation choice to tune empirically.

---

## Open items / recency flags
- **All pricing is volatile** — re-verify Kalodata, FastMoss, EchoTik, Shoplus live pricing pages before committing. Kalodata Enterprise/API price is **undisclosed** (sales quote required).
- **Kalodata ToS is versioned** — §4.1.8/§4.1.6/§4.1.2/§3.3 confirmed verbatim on the research date; re-check section numbers at https://kalodata.gitbook.io/termsofservice before relying on them.
- **Kalodata Open API field coverage unverified** — confirm it returns GMV *growth rate* and *creator count* (not just snapshots) before architecting the score on it. Full API docs are behind the access-key/Enterprise gate.
- **TikTok Affiliate API access friction** — Partner Center likely requires seller/business authorization + app review; many docs are JS-gated and couldn't be fully read. Confirm onboarding requirements early.
