## Context

See `proposal.md` - Why/What Changes for motivation. Relevant existing state on Matheus's Oracle VPS (`<VPS_HOST_IP>`, shared by multiple projects):

- **9Router**: already deployed as `decolua/9router:latest` in `rag-knowledge-assistant/docker/docker-compose.yml`, bound to `<TAILSCALE_9ROUTER_IP>:20128` (Tailscale IP) and exposed as an OpenAI-compatible chat-completions endpoint at `/v1`. `rag-knowledge-assistant/app/generation/llm_client.py` already has a working `OpenAICompatibleLLMClient` against it, selected via `LLM_PROVIDER=openai_compatible` / `LLM_BASE_URL` / `LLM_MODEL` env vars.
- **Nginx pattern**: `portfolio-website/infra/nginx/matheusramos.dev.conf` already proxies a sub-path (`/projects/rag/`) to a locally-bound container (`127.0.0.1:8000`), stripping the prefix. New services on this VPS follow the same isolation pattern: bind to `127.0.0.1`, add one new `location` block, never touch existing blocks.
- **portfolio-website**: static Astro site, deployed by rsyncing a `dist/` build to a VPS release dir; it is a separate git repository with its own OpenSpec root, outside this change's edit scope.
- **Target format**: subject line as 2-3 short headline fragments separated by `/`, a `Curiosidade para o dia <date>: ...` opener, then one paragraph per story (`Bold-ish lead sentence: body. As informações são do site <X>.`). No ad teaser, no sponsored block, no per-item editorial remark — each story paragraph keeps only the "As informações são do site X" attribution.

## Goals / Non-Goals

**Goals:**
- Reuse the VPS's existing 9Router deployment and its established OpenAI-compatible client pattern rather than introducing a new LLM integration.
- Keep the new service isolated (own Docker stack, own Nginx location, own data store) so it cannot destabilize `portfolio-website` or `rag-knowledge-assistant`.
- Produce daily drafts automatically, but require a human approval step before anything is emailed.
- Define a stable integration contract (the subscription API) that `portfolio-website` can call from a separate change.

**Non-Goals:**
- Building the actual subscribe button/CTA inside `portfolio-website` - cross-repo, tracked as a follow-up task there.
- A general-purpose ESP replacement (campaign UI, analytics dashboards, list segmentation) - only what's needed to send one daily edition to one list.
- Selecting/creating the Resend account or API key during planning - happens during implementation.
- A multi-user auth system for the draft review/approval step - this is a single-owner tool.
- Evaluating or integrating a paid news API in this iteration - starts with fetch/RSS-based collection from reputable outlets.

## Decisions

**Backend stack: Python/FastAPI, mirroring `rag-knowledge-assistant`.**
Reuses the same language, web framework, dependency-injection style (`app/api/dependencies.py`), and - most importantly - lets the LLM client be copied/adapted almost directly from `rag-knowledge-assistant/app/generation/llm_client.py` instead of re-implementing an OpenAI-compatible client in another language. Alternative considered: Node/TypeScript (to match `portfolio-website`'s Astro/TS stack) - rejected because the 9Router integration and the "reuse existing components" instruction in the source brief both point to the Python implementation as the reference to build from.

**Storage: SQLite, mounted as a volume like `rag-knowledge-assistant`'s `data/` pattern.**
Subscriber counts and daily edition history for a personal newsletter are small; SQLite needs no extra service (unlike Postgres) and keeps the new stack minimal. Alternative considered: Postgres - rejected for now as unnecessary operational overhead at this scale; migration later is possible without any spec change, since storage choice isn't part of the behavior contract.

**News collection: RSS/official feeds from a curated set of reputable outlets, not a paid news API.**
The reference editions cite outlets like BleepingComputer, TechCrunch, The Verge, Ars Technica, The Register, 9to5Google, and 404 Media - all of which publish RSS feeds. This keeps sourcing free, keeps attribution straightforward (feed → article → cited source, satisfying "no invented sources"), and avoids an extra paid dependency. Alternative considered: a commercial news-aggregation API - rejected as unnecessary cost/complexity for a first version; can be added later as an additional source without changing the spec.

**Scheduling: in-process scheduler (e.g., APScheduler) inside the FastAPI service, not a separate cron container.**
One fewer moving part in the Docker stack; the existing VPS pattern (`qdrant` + `router` + `api`) already keeps each concern to one container, and a daily job doesn't warrant its own. Alternative considered: host crontab hitting an internal endpoint, or a dedicated cron container - rejected as added operational surface for no benefit at this volume.

**Draft review/approval: a secret-link-protected endpoint, not a full auth system.**
A single owner needs to view one pending draft and approve it. A bearer-token/secret-link scheme (token stored as an env var / generated per draft) is enough and matches the project's single-user scope. Alternative considered: session-based admin login - rejected as unnecessary complexity for one user.

**Delivery: Resend API, sender `newsletter@matheusramos.dev`, domain verified via new Cloudflare DNS records.**
Per the user's decision. SPF/DKIM/DMARC records are DNS-only (not proxied through Cloudflare's orange cloud), added to the existing `matheusramos.dev` zone without touching the site's existing proxied records.

**Cross-repo integration boundary: a stable HTTPS path for the subscription API, proxied the same way `/projects/rag/` is today.**
E.g. `matheusramos.dev` routes a new `/api/newsletter/` (or similar) location block to the newsletter service's `127.0.0.1:<port>`, so `portfolio-website`'s future CTA can call it same-origin, no CORS needed - mirroring the existing RAG demo's proxy pattern exactly.

## Risks / Trade-offs

- **[Risk]** RSS/official-feed fetching can be incomplete, rate-limited, or occasionally down → **Mitigation**: per spec, if no verifiable news can be retrieved for the day, the system flags the draft incomplete instead of inventing content; feed list is easy to extend.
- **[Risk]** The LLM may still add editorial commentary or drift from the target structure despite prompting → **Mitigation**: deterministic post-processing/validation of the generated draft (e.g., checking each item ends with an "As informações são do site X"-style attribution, no leftover ad-teaser phrasing) before it's marked ready for review.
- **[Risk]** `newsletter@matheusramos.dev` is a brand-new sending identity with no reputation → **Mitigation**: proper SPF/DKIM/DMARC via Resend's setup flow, low initial send volume, monitor bounce/complaint metrics in the Resend dashboard.
- **[Risk]** Shared VPS already runs `rag-knowledge-assistant` and `portfolio-website`; a misconfigured Nginx block could take down the whole domain → **Mitigation**: new service isolated to its own Docker stack and a single new `location` block, always `nginx -t` before reload (existing project convention per `portfolio-website/DEPLOY.md`).
- **[Risk]** SQLite doesn't scale to a large subscriber base or high write concurrency → **Mitigation**: acceptable at personal-newsletter scale; storage is an implementation detail, so migrating to Postgres later requires no spec changes.
- **[Risk]** The required manual approval step could be silently skipped (draft generated, never reviewed) → **Mitigation**: the generation job should surface a clear "draft ready" signal (e.g., a notification to the owner); exact channel is an implementation detail left open below.

## Migration Plan

1. Scaffold the `newsletter-website` backend (FastAPI) and SQLite schema (subscribers, editions/drafts) - no external calls yet.
2. Implement `newsletter/content-generation`: real news fetch (RSS) + 9Router-backed generation; validate structure/no-commentary rules; test by generating drafts locally without sending.
3. Implement `newsletter/subscription`: subscribe/unsubscribe API + SQLite persistence; deploy as a new, isolated Docker Compose stack on the VPS with one new Nginx `location` block (existing configs untouched).
4. Set up Resend (account, domain verification, Cloudflare DNS records for SPF/DKIM/DMARC) and implement `newsletter/delivery`, gated by the approval requirement.
5. Wire up the daily in-process scheduler for automatic draft generation; sending stays manual/approval-gated.
6. Separately, in the `portfolio-website` repo, propose and implement the subscribe CTA against the deployed subscription API.

**Rollback**: every piece is additive and isolated (new Docker stack, new Nginx location block, new DNS records) - rollback is disabling/removing the new stack and location block, with zero impact on the existing `portfolio-website` or `rag-knowledge-assistant` services.

## Open Questions

- Exact seed list of RSS feeds/outlets for `newsletter/content-generation` - start from the outlets cited in the two reference PDFs (BleepingComputer, TechCrunch, The Verge, Ars Technica, The Register, 9to5Google, 404 Media) and extend as needed during implementation; doesn't affect the spec or approach.
- Notification channel for "a new draft is ready for review" (e.g., an email to Matheus via the same Resend setup, vs. another channel) - an implementation detail that doesn't change the approval requirement itself.
- Exact 9Router model/combo id to target (`LLM_MODEL`) for this project - to be read from the 9Router dashboard at implementation time, same as `rag-knowledge-assistant`'s `.env`.
