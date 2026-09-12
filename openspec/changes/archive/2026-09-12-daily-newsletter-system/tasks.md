## 1. Project Scaffolding

- [x] 1.1 Set up a Python/FastAPI project structure in `newsletter-website` (mirroring `rag-knowledge-assistant`'s `app/` layout: `config`, `api`, plus new modules for news collection, generation, subscription, delivery) and verify `uvicorn` boots a minimal health-check endpoint locally.
- [x] 1.2 Define the SQLite schema for `subscribers` (email, status active/unsubscribed, created_at) and `editions` (id, date, subject, body/content, status draft/approved/sent, created_at, sent_at) and verify migrations/schema creation run cleanly against a fresh file.
- [x] 1.3 Add a `.env.example` (following `rag-knowledge-assistant`'s pattern) covering `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `RESEND_API_KEY`, `NEWSLETTER_FROM_ADDRESS`, `REVIEW_SECRET_TOKEN`, `DB_PATH`, and verify the app fails fast with a clear error when a required var is missing.

## 2. Content Generation (`newsletter/content-generation`)

- [x] 2.1 Implement a news-fetching module pulling from a seeded list of RSS feeds (BleepingComputer, TechCrunch, The Verge, Ars Technica, The Register, 9to5Google, 404 Media - see design.md Open Questions) and verify it returns real article titles/URLs/sources for a live run.
- [x] 2.2 Implement selection logic prioritizing relevance, recency, source quality, and topic diversity, and verify a unit test that feeding it a mixed candidate set returns a diverse, non-arbitrary subset.
- [x] 2.3 Port/adapt the `OpenAICompatibleLLMClient` pattern from `rag-knowledge-assistant/app/generation/llm_client.py` to call 9Router (`LLM_BASE_URL`/`LLM_MODEL`) and verify a manual smoke-test request returns generated text through the local 9Router endpoint.
- [x] 2.4 Implement prompt(s) that generate the "Curiosidade do dia" text and per-news-item paragraphs following the reference structure, explicitly excluding sponsored teasers and per-item editorial commentary, ending each item in an "As informações são do site X"-style attribution, and verify against the two reference PDFs' structure by eyeballing a generated sample.
- [x] 2.5 Implement deterministic post-generation validation (subject line present, Curiosidade section present with no ad-teaser phrasing, every news paragraph ends in a source-attribution sentence) and verify a unit test rejects/flags a draft that violates any rule.
- [x] 2.6 Implement the "no real news → flag incomplete, don't fabricate" fallback path and verify a unit test with an empty candidate list produces a flagged/incomplete draft rather than content.
- [x] 2.7 Wire generation into a daily job entry point (callable directly, independent of the scheduler in section 6) and verify running it end-to-end produces a persisted `editions` row in `draft` status.

## 3. Subscription API (`newsletter/subscription`)

- [x] 3.1 Implement `POST /subscribe` (validates email format, persists as active, no-ops on existing active email) and verify tests cover: valid new email, duplicate active email, malformed email.
- [x] 3.2 Implement an unsubscribe endpoint/link tied to a subscriber's email and verify a test confirms an unsubscribed email is excluded from the active-subscriber query used by delivery.
- [x] 3.3 Implement an internal "get active subscribers" query used only by the delivery module and verify it returns only active emails.

## 4. VPS Deployment

- [x] 4.1 Write a `docker/Dockerfile` and `docker/docker-compose.yml` for the new service, binding it to `127.0.0.1:<port>` on the VPS (following the `rag_api` container pattern) and verify `docker compose up` runs the health-check endpoint locally.
- [x] 4.2 Add a new Nginx `location` block to `matheusramos.dev`'s config (new file in this repo's own `infra/nginx/`, not editing `portfolio-website`'s copy) proxying a dedicated path (e.g. `/api/newsletter/`) to the new container, following the `/projects/rag/` prefix-stripping pattern, and verify `nginx -t` passes before any reload instruction is documented.
- [x] 4.3 Document the deploy/rollback steps for this service (mirroring `portfolio-website/DEPLOY.md`) and verify the doc lists how to isolate/rollback this stack without touching `rag_api` or the portfolio site.

## 5. Delivery (`newsletter/delivery`)

- [x] 5.1 Set up the Resend account/domain verification and add the required SPF/DKIM/DMARC DNS records (DNS-only, not proxied) to the `matheusramos.dev` zone in Cloudflare, and verify Resend reports the domain as verified. Domain `matheusramos.dev` confirmed `status: verified` (DKIM + SPF verified) via Resend API.
- [x] 5.2 Implement the Resend send integration (from-address `newsletter@matheusramos.dev`) and verify a manual test send to a single test address succeeds and appears correctly formatted. Live-tested: real send via `ResendClient` to the owner's own address, confirmed `last_event: "delivered"` via the Resend API.
- [x] 5.3 Implement the secret-link/token-protected review endpoint that shows a pending draft and an "Approve & Send" action, and verify unauthorized requests (missing/wrong token) are rejected.
- [x] 5.4 Implement the approval → send flow: on approval, fetch active subscribers (3.3), send via Resend (5.2), mark the edition `sent` with timestamp, and verify a test confirms an edition can't be sent twice (re-approval/re-invocation on an already-`sent` edition is a no-op).
- [x] 5.5 Record per-recipient send failures reported by Resend against the edition, and verify a test with a simulated provider failure captures the failure detail without crashing the send flow.
- [x] 5.6 Implement a "draft ready for review" notification to the owner (e.g., an email via the same Resend setup) triggered when a new draft is generated, and verify it fires after a successful generation run (2.7).

## 6. Scheduling

- [x] 6.1 Add an in-process daily scheduler (e.g., APScheduler) that triggers the generation entry point (2.7) once per day, and verify the job is registered at app startup (log line or introspection endpoint) and can be triggered manually for testing.

## 7. Cross-Repo Follow-Up (tracked here, implemented elsewhere)

- [x] 7.1 Document the finalized subscription API contract (endpoint URL, request/response shape for `/subscribe`) in this repo so it can be handed to a `portfolio-website` change, and verify the doc alone is enough to implement the CTA without needing this repo's source.
- [x] 7.2 In the separate `portfolio-website` repository, propose and implement the subscribe CTA calling this API (out of scope for this change's `apply` - flagged here as the remaining integration step; not verifiable from within this repo). Implemented directly in that repo (`src/components/NewsletterSignup.astro`, `public/newsletter-signup.js`, wired into `src/pages/index.astro`) and verified end-to-end: `npm run build` succeeds, the form's script serves as an external CSP-compliant file, and a real POST through the local dev proxy persisted a subscriber in `newsletter_api`'s database.
