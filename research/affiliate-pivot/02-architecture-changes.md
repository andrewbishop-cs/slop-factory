# Subtask 02 — Concrete Repo Architecture & Code-Change Map (Affiliate Pivot)

Scope: how to add a TikTok Shop **affiliate content track** to the existing character-video
pipeline as a *second mode in one codebase* — minimal, additive, non-breaking. All claims are
grounded in the actual repo as of this read.

**Critical context for every claim below:** the pipeline is **fully scaffolded but not yet
implemented**. Every stage in `src/pipeline/*.py` is `raise NotImplementedError("M…")`
(`script_gen.py`, `images.py`, `tts.py`, `music.py`, `captions.py`, `hook.py`, `assemble.py`,
`qc.py`) and `src/upload/tiktok_stub.py:publish` is `raise NotImplementedError("M9")`. Only
`src/schemas.py`, `src/config.py`, and `src/pipeline/orchestrator.py` carry real logic. This
means the affiliate track should be designed to land **alongside** the M0–M9 build, not bolted
onto finished code — which is a large reuse win (no rework of working code) but also means the
affiliate features depend on stages that don't run yet.

---

## A. STAGES list & data contract today (evidence)

- `orchestrator.py:20` — `STAGES = ["script", "images", "tts", "captions", "music", "hook", "assemble", "qc"]`.
- `orchestrator.py:67-78` — the run loop iterates `STAGES`, skips stages flagged done in
  `state.json`, supports `--force <stage>` and `--until <stage>`. State dict is keyed by stage name
  (`load_state` initializes `{stage: False for stage in STAGES}`).
- `orchestrator.py:81-102` — `run_stage()` is a hard-coded `if/elif` dispatch on stage name; each
  branch calls a fixed `module.function(settings, episode, bible, episode_dir, ...)`.
- `script_gen.generate_script(settings, bible, episode_dir, prompt)` is the only stage that takes
  `prompt`; all others load `episode.json` via `load_episode()` first (`orchestrator.py:85`).
- Episode is the single contract: `Episode` (schemas.py:60) with `hook`, `scenes[]`, `music`,
  `caption`, `cliffhanger_text`. `SeriesBible` (schemas.py:99) carries `characters[]` + `plot_state`.
- Upload is a single deferred stub, **not in STAGES** — it's invoked from the Streamlit UI on
  approve per BUILD.md §9 (`ui/app.py` "On approve → calls upload/tiktok_stub.py").

This architecture is friendly to additive change: stages are name-keyed and the orchestrator's only
coupling points are the `STAGES` list and the `run_stage` dispatch. Adding a stage = append name +
add an `elif`.

---

## B. Claims

### Claim 1 — schemas.py: add a `Product` model + an affiliate-aware Scene/Caption, do NOT fork `Episode`. (confidence: high)

Evidence/reasoning: `Episode` is the universal contract every stage consumes
(`orchestrator.py:85` loads it for all non-script stages). Forking it into `AffiliateEpisode`
would force a change to every stage signature and the `run_stage` dispatch. Cheaper and non-breaking:
keep one `Episode`, add **optional** affiliate fields that default to `None`/empty so existing
character episodes validate unchanged. Concretely:

- New `Product(BaseModel)`: `product_id: str`, `name: str`, `affiliate_link: str`,
  `aup_usd: float` (the $80–250 gating var), `commission_rate: float` (the ≥0.30 gating var),
  `brand: str`, `category: str | None`, `demo_notes: str` (how to show it on camera),
  `image_refs: list[str]` (paths under a new `assets/products/<product_id>/` dir),
  `key_features: list[str]`, `disclosure_required: bool = True`. The source doc's two gating
  variables (AUP $80–250, commission ≥30%) and "demo notes / winning angle" map directly onto these.
- New `Scene.scene_type: Literal["story", "product_demo", "product_broll", "cta"] = "story"`.
  Default `"story"` keeps every current scene valid. `images.py`/`assemble.py` branch on it later.
- New optional `Scene.product_id: str | None = None` so a scene can reference which product it shows.
- `Caption` additions: `affiliate_disclosure: str | None = None` (e.g. "#ad"),
  `showcase_product_id: str | None = None` (TikTok Shop product-link/showcase tag),
  `cta_text: str | None = None`. `ai_label` already exists and is reused for the AI-disclosure rule
  the source doc calls out (risk node #2: disclosure rules).
- `Episode` additions (all optional): `mode: Literal["story", "affiliate"] = "story"`,
  `product: Product | None = None`, `cta: CTA | None = None` (a small model:
  `text`, `appears_after_scene_id`, `affiliate_link`).
- `SeriesBible` additions: a new optional `product_slots: list[ProductSlot] = []` where
  `ProductSlot` ties a product into the story world (`product_id`, `presenter_character: str`,
  `integration_note: str`) — this encodes the LOCKED decision that *characters act as presenters*
  and "inject real products into the story world."

> **NOTE — `extra="forbid"` everywhere is a friction point.** Every model uses
> `model_config = ConfigDict(extra="forbid")` (e.g. schemas.py:15, 33, 53, 61). Adding fields is
> fine, but it means any older `episode.json` written before the new fields is still fine (missing
> optional fields default), yet you can NOT sneak undeclared affiliate keys past validation — all
> affiliate fields must be declared explicitly. This is good hygiene but forces the schema work to
> be complete before any affiliate stage can emit data.

### Claim 2 — Add a sourcing/scoring stage that runs BEFORE `script`, gated by mode. (confidence: medium)

Evidence/reasoning: The source doc Stage 1 ("Sourcing": pull Kalodata, score & shortlist) and the
composite score `commission_rate × AUP × GMV_growth × (1/saturation) × trend` produce the `Product`
that the script then dramatizes. In repo terms this is a new
`src/pipeline/sourcing.py:select_product(settings, bible, episode_dir) -> Product` that writes
`product.json` into the episode dir. It must run before `script` because `script_gen` needs the
product to write `product_demo`/`cta` scenes.

Two integration options against `STAGES`:
- **Preferred (minimal):** do NOT put sourcing in the main `STAGES` loop. Make it a separate entry
  command (e.g. `--source` or a tiny `src/pipeline/sourcing.py` CLI) that emits a product brief, and
  have `script_gen` read `product.json` when `mode == "affiliate"`. Keeps the resumable
  `STAGES`/`state.json` machinery untouched.
- **Alternative:** prepend `"sourcing"` to `STAGES` and add an `elif stage == "sourcing"` branch.
  This is clean but changes `STAGES` for *story* episodes too (they'd carry a no-op sourcing stage),
  so it needs a mode guard (`if episode.mode == "affiliate"`).

> **FRICTION — sourcing data acquisition is the source doc's risk node #1** (Kalodata scraping
> likely violates ToS). The architecture should treat `sourcing.py` as a thin reader of a
> **manually exported** Kalodata file (CSV/JSON dropped into a configured path), NOT a scraper. The
> scoring math is fully automatable; the *acquisition* must stay manual. Encode this by having
> `sourcing.py` read from `settings.affiliate.kalodata_export_path`.

### Claim 3 — `script_gen` is modified (not replaced) to branch on mode; reuse Opus structured-output path. (confidence: high)

Evidence/reasoning: `generate_script(settings, bible, episode_dir, prompt)` (script_gen.py:15) is
the one stage already designed to take a `prompt` and produce a schema-valid `Episode`. For affiliate
mode it reads `product.json`, injects product + presenter character + the reverse-engineered winning
angle (source doc Stage 2) into the prompt, and emits an `Episode` with `mode="affiliate"`,
`scene_type` of `product_demo`/`product_broll`/`cta`, and populated `caption.affiliate_disclosure`/
`showcase_product_id`. Same Opus 4.8 structured-output mechanism, same `Episode` schema, same bible
caching — only the system prompt + a product context block change. This is the **biggest reuse win**:
script generation, the entire downstream render path, and the resumable orchestrator all stay intact.

### Claim 4 — `images.py` is supplemented (not modified) by a product-broll/screen path; `assemble`/`tts`/`captions`/`music`/`qc` stay as-is. (confidence: medium)

Evidence/reasoning:
- `images.generate_images` (images.py:16) renders one keyframe per scene from `image_prompt`.
  For `scene_type == "product_broll"` it should composite the real product image (from
  `Product.image_refs` / `assets/products/<id>/`) instead of generating a fictional keyframe — and
  for "faceless product UGC" the b-roll is the product asset under Ken Burns. Cleanest: keep
  `generate_images` and add a sibling helper `product_broll(scene, product, ...)` it dispatches to
  on `scene.scene_type`. The existing `ken_burns()` helper (images.py:26) is reused verbatim for
  product stills — a direct reuse win.
- **AI-avatar presenter render path** (the second locked format) is genuinely new and does NOT fit
  `images.py` (which produces stills). It needs a new `src/pipeline/avatar.py:render_presenter(...)`
  producing a talking-head clip of the character presenter, lip-synced to the narration wav. This is
  a new stage/asset type, the largest net-new piece. It slots between `tts` and `assemble`
  (it consumes narration audio).
- `tts.py` (Kokoro, voice per character) is reused verbatim — the presenter character's locked voice
  reads the product script; no change to `generate_narration` signature.
- `captions.py` is reused; the only addition is rendering the disclosure/CTA text, which can be
  driven from new `Caption` fields without changing the `generate_captions` signature.
- `music.py` is reused as-is (mood bed under voiceover; affiliate UGC still wants a bed).
- `assemble.py` is modified internally to (a) overlay CTA/showcase text near the end and (b) splice
  avatar clips when present — but its signature `assemble(settings, episode, episode_dir)` is
  unchanged, so the orchestrator dispatch (`orchestrator.py:97`) doesn't move.
- `qc.py` gets new affiliate checks (disclosure present, affiliate_link non-empty, product image
  shown, CTA present) — additive to the report dict; signature unchanged.

### Claim 5 — affiliate-link handling belongs in the upload/showcase layer, not the render. (confidence: high)

Evidence/reasoning: TikTok Shop affiliate links are attached as a product **showcase / link** on the
post, not burned into the pixels (burning a URL into video is both ugly and unclickable). The repo's
`upload/tiktok_stub.py:publish` (the stage that writes `caption.txt` + drops into `ready_to_post/`)
is the right home: extend it to also write the affiliate link + `showcase_product_id` into
`caption.txt`/a sidecar `affiliate.txt` and print "attach TikTok Shop product link X; set
branded-content/#ad toggle." This keeps the render stages product-agnostic and matches the deferred
real-uploader plan in BUILD.md. The `caption.txt` writer in `assemble.py` should append the
disclosure line when `mode == "affiliate"`.

### Claim 6 — settings.yaml gets one additive `affiliate:` block + a `mode` default; nothing existing changes. (confidence: high)

Evidence/reasoning: `config.py` builds `Settings` from nested pydantic sub-models, each with
defaults (e.g. `MusicConfig`, config.py:55), and `load_settings` does
`Settings.model_validate(data)` (config.py:98-101). A new optional `AffiliateConfig` sub-model with a
default means existing `settings.yaml` (which has no affiliate block) still loads unchanged. Add to
`settings.yaml`:

```yaml
affiliate:
  enabled: false                       # master toggle; story mode unaffected when false
  kalodata_export_path: assets/affiliate/kalodata_export.csv   # MANUAL export (risk node #1)
  product_assets: assets/products      # per-product image/demo refs
  min_aup_usd: 80
  max_aup_usd: 250
  min_commission_rate: 0.30
  formats: [faceless_ugc, avatar_presenter]
  default_format: faceless_ugc
  disclosure_tag: "#ad"
```

And a corresponding `AffiliateConfig(BaseModel)` in `config.py` plus `affiliate: AffiliateConfig =
AffiliateConfig()` on `Settings`. New asset dirs: `assets/products/<product_id>/` and
`assets/affiliate/`.

---

## C. REUSE / MODIFY / ADD table

| Module / file | Disposition | What happens |
|---|---|---|
| `src/schemas.py` | **MODIFY (additive)** | Add `Product`, `CTA`, `ProductSlot`; add optional fields to `Scene` (`scene_type`, `product_id`), `Caption` (`affiliate_disclosure`, `showcase_product_id`, `cta_text`), `Episode` (`mode`, `product`, `cta`), `SeriesBible` (`product_slots`). All default-valued → story episodes unaffected. |
| `src/config.py` | **MODIFY (additive)** | Add `AffiliateConfig` sub-model + `affiliate` field on `Settings`. Defaults keep old `settings.yaml` valid. |
| `config/settings.yaml` | **MODIFY (additive)** | Add `affiliate:` block (Claim 6). |
| `config/series/*.json` | **REUSE / optional MODIFY** | Existing bibles load unchanged (`product_slots` defaults to `[]`). A new affiliate series can populate `product_slots`. |
| `src/pipeline/orchestrator.py` | **MODIFY (small)** | Add `avatar` to `STAGES` (mode-guarded) + one `elif` in `run_stage`; optionally wire `sourcing`. Dispatch is name-keyed so this is a 2–4 line change. |
| `src/pipeline/script_gen.py` | **MODIFY** | Branch on `mode`: affiliate prompt injects product + presenter + winning angle, emits affiliate scene types + disclosure caption. Same Opus structured-output + `Episode` schema. |
| `src/pipeline/images.py` | **MODIFY (additive)** | Dispatch on `scene.scene_type`; add `product_broll()` helper that composites real product assets. `ken_burns()` reused verbatim. |
| `src/pipeline/tts.py` | **REUSE** | Presenter character's locked Kokoro voice reads the product script. No signature change. |
| `src/pipeline/captions.py` | **REUSE (data-driven)** | Renders disclosure/CTA from new `Caption` fields; no signature change. |
| `src/pipeline/music.py` | **REUSE** | Mood bed under voiceover. Unchanged. |
| `src/pipeline/hook.py` | **REUSE** | Hook still opens the video (the converting "angle" hook). Unchanged signature; affiliate prompt just feeds a product-relevant hook. |
| `src/pipeline/assemble.py` | **MODIFY (internal only)** | Splice avatar clips when present; overlay CTA/showcase near end; append disclosure line to `caption.txt`. Signature unchanged. |
| `src/pipeline/qc.py` | **MODIFY (additive)** | New affiliate checks (disclosure present, affiliate_link set, product shown, CTA present). Report dict additive. |
| `src/upload/tiktok_stub.py` | **MODIFY** | Write affiliate link + showcase product id + #ad reminder into output sidecar; print TikTok Shop product-link instructions. |
| `src/pipeline/sourcing.py` | **ADD (new)** | Read manual Kalodata export → composite score → emit `product.json`. Runs before `script`. NOT a scraper (risk node #1). |
| `src/pipeline/avatar.py` | **ADD (new)** | AI-avatar presenter render path: talking-head character clip lip-synced to narration. New stage between `tts` and `assemble`. Largest net-new piece. |
| `assets/products/`, `assets/affiliate/` | **ADD (new dirs)** | Product image/demo refs + manual Kalodata export. |

**Biggest reuse win:** the entire render spine — `Episode` contract, `script_gen` structured output,
`tts`, `captions`, `music`, `hook`, `ken_burns`, and the resumable `STAGES`/`state.json` orchestrator
— is reused with zero or signature-stable changes. Affiliate mode is mostly a schema extension + a
script-prompt branch + product-asset compositing.

**Biggest friction point:** the **AI-avatar presenter** format has no home in the current stack
(every visual stage produces stills via `images.py`; nothing does talking-head video / lip-sync).
It's a genuinely new stage (`avatar.py`) and a new asset/model dependency, and it's the format the
source doc says ROAS is most sensitive to (risk node #2: synthetic UGC underperforms / trips
disclosure). Faceless product-UGC (b-roll + voiceover) reuses far more and should ship first.

---

## D. Migration sequence (M0–M9 style, additive, non-breaking)

These assume the existing v0 milestones (BUILD.md M0–M9) proceed in parallel/first; affiliate
milestones are labelled MA-n and each is independently testable. The guiding rule (per LOCKED
decisions): **never break the story pipeline** — every step is mode-guarded and defaults to story.

- **MA0 — Schemas + config (no behavior change).** Add `Product`/`CTA`/`ProductSlot`, optional
  affiliate fields on `Scene`/`Caption`/`Episode`/`SeriesBible`, `AffiliateConfig`, and the
  `affiliate:` settings block. *Test:* existing `fridge-detectives.json` and the BUILD.md §8 example
  episode still validate; a hand-written affiliate `episode.json` (mode="affiliate" + product) also
  validates. *Checkpoint:* commit. No stage runs differently yet.

- **MA1 — Sourcing reader.** `sourcing.py` reads a manual Kalodata export, applies the composite
  score, writes `product.json` + a shortlist. *Test:* feed a sample export → top product matches
  hand-computed score; products failing AUP/commission gates are dropped. *(Risk node #1: reader,
  not scraper.)*

- **MA2 — Affiliate script branch.** `script_gen` mode branch: given `product.json`, emit an
  affiliate `Episode` (product_demo/broll/cta scenes + disclosure caption + showcase id). *Test:*
  `--prompt` with an affiliate series yields a schema-valid affiliate episode; a story prompt is
  byte-for-byte unchanged from before.

- **MA3 — Faceless product b-roll (format 1, the high-reuse one).** `images.py` dispatch +
  `product_broll()` compositing real product assets; reuse `ken_burns`, `tts`, `captions`, `music`,
  `assemble`. *Test:* an affiliate episode renders a watchable faceless-UGC `final.mp4` (product
  shown under Ken Burns + presenter-voice voiceover + captions). This is the first end-to-end
  affiliate video and proves the reuse thesis.

- **MA4 — CTA/showcase injection + disclosure.** `assemble` overlays CTA near the end and appends the
  #ad/disclosure line to `caption.txt`; `qc` adds affiliate checks. *Test:* QC fails an affiliate
  episode missing disclosure or affiliate_link; passes a complete one.

- **MA5 — Affiliate-link / showcase handoff.** Extend `tiktok_stub.publish` to emit the affiliate
  link + showcase product id + branded-content reminder into `ready_to_post/`. *Test:* approving an
  affiliate episode lands the video + an `affiliate.txt` with the link and instructions.

- **MA6 — AI-avatar presenter (format 2, the net-new one).** New `avatar.py` stage + `STAGES`/dispatch
  wiring (mode-guarded), `assemble` splices avatar clips. *Test:* an affiliate episode with
  `format: avatar_presenter` renders a talking-head presenter clip lip-synced to narration, spliced
  into the final cut; story episodes and faceless-UGC episodes are unaffected. Built last because it
  is the riskiest/highest-cost piece (mirrors BUILD.md building the fragile hook last).

- **MA7 (optional, later) — Variant generation for organic testing.** `script_gen` emits N hook/angle
  variants per product (source doc Stage 2→3) for the organic-test-before-spend gate. Out of scope
  for the core architecture change; flag only.

---

## E. Places the current design fights the affiliate use case (flags)

1. **Stills-only visual stack.** `images.py` produces one PNG per scene; there is no video-of-a-person
   path. Avatar-presenter UGC needs lip-synced talking-head video → new `avatar.py`. (high)
2. **`hook.duration_sec` capped ≤4s** (`schemas.py:20`, `Field(gt=0, le=4)`). Fine for story hooks,
   but some product UGC hooks ("watch what this does") run longer. May need to relax the cap for
   affiliate mode or rely on a longer first scene. (medium)
3. **`min_duration_sec: 62`** (settings.yaml:2) and the ≥62s QC gate target a long story format.
   High-converting product UGC is often 15–34s. Affiliate mode likely needs its own min-duration
   target, or the QC gate becomes a false negative for short shoppable clips. (medium)
4. **Sourcing acquisition (Kalodata) cannot be automated safely** (source doc risk node #1). The
   architecture must keep `sourcing.py` a reader of a manual export; designing it as a scraper would
   be a single point of failure that can ban the account. (high)
5. **No analytics/feedback loop in the pipeline.** The flywheel (organic test → pick winners → Spark
   Ads) needs post-publish metrics back into sourcing/variant selection. The current orchestrator is
   one-shot generate-only with a stub uploader; closing the flywheel is a later, larger effort beyond
   this additive change. (medium)
6. **Everything is still `NotImplementedError`.** Affiliate stages depend on story stages that don't
   run yet; affiliate work realistically interleaves with M2–M9 rather than building on a finished v0.
   (high)
