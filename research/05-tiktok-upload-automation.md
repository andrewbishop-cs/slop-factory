# TikTok Upload Automation Research (2025–2026)

**Research date:** June 10, 2026  
**Purpose:** Evaluate options for programmatically uploading ~1-minute AI character videos to TikTok after human approval.

---

## 1. Official TikTok Content Posting API

### Overview

TikTok's Content Posting API is the only sanctioned path to automated video publishing. It is available at no cost through the TikTok for Developers platform.

**Official documentation:** https://developers.tiktok.com/products/content-posting-api/

### Developer App Registration Process

1. Create a developer account at https://developers.tiktok.com/signup
2. Verify email with a PIN code
3. Accept TikTok Developer Terms & Conditions
4. Create or join an organization, then create a new app
5. Add the "Content Posting API" product to the app configuration
6. Request the `video.publish` and/or `video.upload` scopes, providing a written summary of intended use
7. Submit a working prototype or description of the application
8. Wait 5–7 days for initial review; post-approval, move to production audit (see below)

In 2025 TikTok tightened this process — a working prototype and detailed scope justification are now required to receive the initial client key.

### Direct Post vs. Upload to Inbox (Creator's Draft)

| Feature | Direct Post | Upload to Inbox |
|---|---|---|
| API scope required | `video.publish` | `video.upload` |
| Endpoint | `/v2/post/publish/video/init/` | `/v2/post/publish/content/init/` (MEDIA_UPLOAD mode) |
| Result | Video publishes live immediately | Video appears in creator's TikTok inbox as a draft |
| Creator action needed? | No — fully automated | Yes — creator opens TikTok app, reviews, taps "Post" |
| Requires passing audit? | Yes (for public posts) | **No — works without audit** |
| Unaudited restriction | All posts forced to `SELF_ONLY` | Draft visible to creator only until they post manually |
| Automation of full flow | Full end-to-end | Semi-automated (human final tap) |

**Key insight for human-in-the-loop pipelines:** Upload to Inbox (`video.upload` scope) works without completing the full audit. The creator receives an inbox notification, reviews the video in TikTok's native app, then taps Post. This is the most practical path for a single creator who wants to approve before publishing.

### Audit / Approval Requirement

To enable Direct Post with public visibility, the app must pass TikTok's full production audit:

- **Timeline:** Typically 2–6 weeks, with multiple rounds of feedback
- **What TikTok evaluates:** Privacy policy, UX compliance (privacy level dropdown with no pre-selected default, visible creator nickname, comment/duet/stitch toggles), branded content disclosure flow, data handling
- **Unaudited restriction:** All posts from unaudited apps are forced to `privacy_level: SELF_ONLY`; attempting public posts returns error `unaudited_client_can_only_post_to_private_accounts`
- **5-user cap:** Unaudited apps are limited to 5 distinct user accounts posting within any 24-hour window
- After audit: per-client active-creator cap based on usage estimates submitted during the audit application

### Can an Individual Creator Realistically Get Access?

Yes, but with caveats:

- Any individual can register a developer account and create an app — there is no business or company requirement
- For the Upload to Inbox flow (semi-automated), an individual can get this working relatively quickly without the full audit
- For fully automated Direct Post to public, the audit is required and takes weeks — TikTok scrutinizes use cases carefully
- The audit is designed for third-party platforms serving many creators, but a solo developer building a personal tool can apply and has succeeded historically

### Rate Limits

- **Per-user token:** 6 requests per minute (Content Posting API initialization endpoint)
- **Per-account daily post cap:** ~25 videos per creator account per 24-hour period
- **App-level caps:** Not published; negotiated during audit; response headers `X-RateLimit-Remaining` and `X-RateLimit-Reset` are provided
- **Error codes to watch:** `spam_risk_too_many_posts`, `spam_risk_user_banned_from_posting`

### Video Requirements (via API)

- Formats: MP4, MOV, WEBM, AVI (MP4 + H.264 strongly recommended)
- Max file size: 1 GB
- Duration: 3 seconds to 10 minutes
- Min resolution: 360×360 px; recommended 9:16 aspect ratio
- Caption: up to 2,200 UTF-16 characters
- Upload methods: `FILE_UPLOAD` (chunked, min chunk 5 MB / max 64 MB) or `PULL_FROM_URL` (TikTok pulls from a verified URL prefix)
- Note: The API **cannot** add TikTok's native sounds, stickers, polls, or effects — those require in-app editing

---

## 2. OAuth Scopes and Token Flow

### Required Scopes

| Scope | Purpose | Audit required? |
|---|---|---|
| `video.upload` | Upload video to creator's inbox as draft | No |
| `video.publish` | Directly publish video to creator's profile | Yes (for public posts) |
| `video.list` | Read post performance data (optional) | No |

**Docs:** https://developers.tiktok.com/doc/scopes-overview  
**API scopes reference:** https://developers.tiktok.com/doc/tiktok-api-scopes

### OAuth 2.0 Token Flow

1. Redirect user to TikTok auth URL with `client_key`, requested scopes, and `redirect_uri`
2. User logs in and grants permissions
3. TikTok returns a temporary `code` to `redirect_uri`
4. Server exchanges `code` for `access_token` + `refresh_token`
5. Use `access_token` in `Authorization: Bearer` header for API calls
6. **Access tokens expire after 24 hours** — this is a common integration failure point
7. Refresh tokens last 365 days; call the refresh endpoint with `grant_type=refresh_token`

For a single-creator personal tool, the token can be obtained once and kept alive indefinitely via the refresh endpoint, as long as the refresh is performed before the 24-hour access token window closes.

---

## 3. Third-Party Schedulers / APIs

These services act as wrappers around TikTok's official API, providing a simpler integration surface and often bypassing the need to undergo your own TikTok app audit.

### Services Compared

| Service | Type | TikTok Support | Price (entry) | Price (relevant tier) | Notes |
|---|---|---|---|---|---|
| **Ayrshare** | SaaS API | Yes (direct post + drafts) | $149/mo (1 profile) | $299/mo (Launch, 10 profiles) | Enterprise-grade; best for platforms serving many creators; 28-day free trial |
| **Buffer** | SaaS scheduler | Yes | Free (10 posts/channel) | $6/mo/channel (Essentials) | Good UI; free plan very limited; TikTok on paid plans |
| **Later** | SaaS scheduler | Yes | $18.75/mo (billed annually) | $18.75+/mo | TikTok inbox included; good for creators |
| **Metricool** | SaaS analytics+scheduler | Yes | Free (20 posts/mo) | $20/mo (Starter) | Direct TikTok publishing via official API on all paid plans |
| **Postiz** | Open source (AGPL-3.0), self-hostable | Yes (30+ platforms) | Free (self-hosted) | $29/mo cloud (Standard) | ~30k GitHub stars; best open-source option |
| **Blotato** | SaaS API + AI content tools | Yes | $29/mo (900 posts/mo) | $29/mo | Built by indie creator; good for AI content pipelines |
| **upload-post.com** | SaaS posting API | Yes | $16/mo (5 profiles, unlimited posts) | $16/mo | Lightweight, posting-only focus |
| **PostPeer** | SaaS posting API | Yes | $8.50/1,000 posts | $6/1,000 at volume | Pay-per-post pricing; 20 free posts |

### Key Notes on Third-Party Services

- Third-party services that have already passed TikTok's audit can offer **public Direct Post** without you needing your own audit
- They handle OAuth token management and TikTok API compliance on your behalf
- For a single creator with a small volume pipeline (~1 post/day), the cheapest viable options are Metricool ($20/mo), upload-post ($16/mo), Postiz (self-hosted free or $29/mo cloud), or Blotato ($29/mo)
- Postiz is the standout open-source option: self-hostable for near-zero cost, AGPL-3.0 licensed, supports TikTok among 30+ platforms

---

## 4. Unofficial Automation (Browser Automation / Selenium / Playwright)

> **WARNING: This section documents unofficial approaches. These methods violate TikTok's Terms of Service. Using them risks temporary or permanent account ban, content shadowbanning, and loss of the account. This is presented as factual information about available tools, not a recommendation.**

### How Unofficial Automation Works

Unofficial TikTok uploaders use browser automation frameworks (Playwright, Selenium) to simulate a logged-in user session:

1. Capture browser session cookies from a real login
2. Launch a headless (or visible) browser, injecting those cookies
3. Navigate to TikTok's upload interface and automate form-filling + file upload
4. Bypass authentication by impersonating a legitimate browser session

### Key Tools on GitHub

- **wkaisertexas/tiktok-uploader** (GitHub): Playwright + Python; 740 stars, 166 forks, actively maintained (latest release Feb 2026). Uses cookie injection. Developer's own warning: "the video will fail to upload after too many uploads" — suggests TikTok rate-limits this behavior at the session level.
- **makiisthenes/TiktokAutoUploader**: Uses direct HTTP requests rather than Selenium; actively maintained.
- **firetofficial/tiktok-auto-uploader-selenium**: Selenium + cookies approach.
- **gbiz123/tiktok-captcha-solver**: CAPTCHA-solving library (SadCaptcha) that can be paired with automation — TikTok increasingly serves CAPTCHAs to suspected bots.

### ToS Violation and Risk

TikTok's Terms of Service explicitly prohibit:
- Scraping, crawling, or extracting data/content using automated systems or software, including bots, except as approved in writing by TikTok
- Any automation not done through TikTok's approved API channels

**Consequences observed and documented:**
- Shadowban: 70–90% drop in views; removal from For You Page; typically lasts 14–30 days
- Temporary suspension: days to weeks of account access restriction
- Permanent ban: account termination with no recovery path
- TikTok's May 2025 algorithm update improved detection of bot-like submission patterns
- TikTok removed 211 million videos in Q1 2025, with 87% flagged by automated detection

**Do not use unofficial automation for an account you cannot afford to lose.**

---

## 5. TikTok's Spam and Automation Policy

### Official Rules

Per TikTok's Content Sharing Guidelines (https://developers.tiktok.com/doc/content-sharing-guidelines):

- API clients must "facilitate authentic creators to post original content" — bulk-copying from other platforms is prohibited
- The metadata UI must not pre-select privacy levels or interaction settings — these must be user-chosen
- Creator nicknames must be displayed before posting; apps must stop posting if creators hit their limit
- Explicit user consent and content preview are required before publishing

### Safe Posting Frequency

- **API hard limit:** 25 videos per creator account per 24-hour period
- **Practical safe range for algorithm health:** 1–3 videos per day for a new/growing account; 3–5/day max for established accounts
- **Spam trigger threshold:** 15–20+ videos/day, bulk-following, mass-commenting — these trigger spam filters
- **Pattern TikTok flags as bot-like:** rapid posting of similar-format videos, brand-new app + brand-new account + high frequency
- Error codes `spam_risk_too_many_posts` and `spam_risk_user_banned_from_posting` are returned by the Content Posting API when limits are approached

For a pipeline producing ~1 video/day, spam detection is not a concern assuming the content is genuine and original.

---

## 6. Options Comparison Table

| Approach | Cost | Setup Complexity | Audit Required | Reliability | ToS Risk | Best For |
|---|---|---|---|---|---|---|
| **Official API — Upload to Inbox** | Free (TikTok API) + dev time | Medium (OAuth flow, token refresh, API integration) | No (for draft/inbox mode) | High — official channel | None | Single creator wanting human approval before publish |
| **Official API — Direct Post** | Free (TikTok API) + dev time | High (full audit, UX compliance) | Yes (2–6 weeks for public posts) | Very High | None | Fully automated pipelines at scale |
| **Metricool** | $20/mo | Low (UI + API) | No (Metricool has its own approval) | High | None | Creators wanting a simple scheduler UI |
| **Postiz (self-hosted)** | ~$0 infra (VPS ~$5–20/mo) | Medium (Docker self-host) | No | High | None | Technical creators wanting open-source control |
| **Postiz (cloud)** | $29/mo | Low | No | High | None | Non-technical creators wanting open-source option |
| **Blotato** | $29/mo | Low | No | High | None | AI content creators; good API for automation |
| **upload-post.com** | $16/mo | Low | No | High | None | Simple API-first posting, lowest cost SaaS |
| **Ayrshare** | $149–$299+/mo | Low–Medium | No (Ayrshare's approval) | Very High | None | Enterprise / multi-creator platforms |
| **Buffer / Later** | $6–18/mo | Low | No | High | None | General social media scheduling |
| **Browser automation (Playwright/Selenium)** | Free (dev time + infra) | Medium–High | N/A (bypasses entirely) | Low–Medium (breaks with TikTok UI changes) | **HIGH — ToS violation, ban risk** | Not recommended for production accounts |

---

## 7. Recommended Approach for Human-in-the-Loop Single Creator Pipeline

### Context

The target use case is: automated pipeline generates ~1-minute AI character videos → human reviews and approves → video posts to TikTok. This is inherently a human-in-the-loop flow, not a fully automated spam operation.

### Option A: Official API — Upload to Inbox (Recommended Starting Point)

**How it works:**
1. Pipeline generates video, human reviews and approves in your internal tool
2. On approval, your app calls TikTok's Content Posting API with `video.upload` scope
3. Video is pushed to the creator's TikTok inbox as a draft
4. Creator opens TikTok app, sees inbox notification, reviews, and taps "Post"

**Why this is the right fit:**
- Works **without** completing the full app audit — you can ship immediately
- Requires only the `video.upload` scope, which has fewer restrictions
- The human "tap to post" step aligns perfectly with the approval philosophy
- Zero cost (TikTok API is free), just development time
- No ToS risk
- Token management is straightforward for a single account: one OAuth flow, automated refresh

**Limitations:**
- The final tap must happen in the TikTok mobile app — cannot be fully headless
- If you later want to eliminate that final tap, you'll need to pass the Direct Post audit

**Implementation steps:**
1. Register developer account: https://developers.tiktok.com/signup
2. Create app, add Content Posting API product
3. Request only `video.upload` scope (avoids the harder audit path)
4. Implement OAuth flow for your account (one-time; refresh tokens keep it alive)
5. On video approval in your pipeline, call `/v2/post/publish/content/init/` with `MEDIA_UPLOAD` mode
6. Push to the access token's associated account's inbox
7. Receive TikTok mobile notification; tap to review and post

### Option B: Third-Party Service (Lower Dev Overhead)

If building the OAuth + API integration feels like too much overhead, **Postiz (self-hosted)** or **upload-post.com / Blotato** are the next best choices:

- Postiz self-hosted: free, open source, actively maintained, handles TikTok's API for you
- Blotato or upload-post: $16–$29/mo, simple API, already audited with TikTok

These services typically support both direct post and draft/inbox modes. For the human-in-the-loop use case, use their inbox/draft mode or trigger direct post from your approval webhook.

### Option C: TikTok Official API — Direct Post (Best Long-Term)

If the pipeline matures and you want fully automated end-to-end posting (no mobile tap), pursue the Direct Post audit:

- Budget 4–8 weeks for the audit process
- Ensure your approval UI meets TikTok's UX requirements (no pre-selected privacy levels, creator info displayed, etc.)
- Once approved, calls to `/v2/post/publish/video/init/` with `video.publish` scope post directly to the public profile
- This eliminates the final mobile-tap step entirely

### What to Avoid

- **Browser automation / unofficial tools:** The ban risk is real and the reliability is low. For an account producing content you care about, this is not worth it.
- **Over-posting:** Even with a valid pipeline, posting more than 3–5 videos per day from a single account risks spam flagging. At ~1 video/day you are well within safe limits.

---

## Reference Links

- Content Posting API overview: https://developers.tiktok.com/products/content-posting-api/
- Getting started guide: https://developers.tiktok.com/doc/content-posting-api-get-started
- Upload video (initialize): https://developers.tiktok.com/doc/content-posting-api-reference-upload-video
- Direct post reference: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- Media transfer guide: https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide
- Scopes overview: https://developers.tiktok.com/doc/scopes-overview
- API scopes list: https://developers.tiktok.com/doc/tiktok-api-scopes
- Content sharing guidelines: https://developers.tiktok.com/doc/content-sharing-guidelines
- Rate limits: https://developers.tiktok.com/doc/tiktok-api-v2-rate-limit
- Developer account signup: https://developers.tiktok.com/signup
- Create an app guide: https://developers.tiktok.com/doc/getting-started-create-an-app
- Set up developer portal account: https://developers.tiktok.com/doc/set-up-developer-portal-account
- FAQ: https://developers.tiktok.com/doc/getting-started-faq
- Postiz GitHub (open source scheduler): https://github.com/gitroomhq/postiz-app
- wkaisertexas/tiktok-uploader (unofficial, ToS risk): https://github.com/wkaisertexas/tiktok-uploader
- Ayrshare TikTok API docs: https://www.ayrshare.com/docs/apis/post/social-networks/tiktok
- Blotato: https://www.blotato.com/
- upload-post.com: https://www.upload-post.com/
