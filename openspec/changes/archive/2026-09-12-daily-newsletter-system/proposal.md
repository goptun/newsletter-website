## Why

Matheus wants his own daily tech newsletter, integrated with his `portfolio-website` for subscriber capture. The goal is to reuse infrastructure he already runs on his Oracle VPS — the 9Router LLM gateway (already integrated in `rag-knowledge-assistant`) — instead of standing up new LLM infra, and to keep the content objective, with no sponsored/commentary parts.

## What Changes

- New `newsletter-website` backend service (Python/FastAPI, matching the `rag-knowledge-assistant` pattern already deployed on the same VPS) that:
  - Collects recent, relevant tech news from real sources (no invented content).
  - Generates the daily edition via the 9Router LLM gateway (`OpenAICompatibleLLMClient`-style client, reused from `rag-knowledge-assistant`), following the reference newsletter's structure: subject line with 2-3 headline fragments, a "Curiosidade do dia" opener, then one paragraph per news item ending in a source attribution sentence.
  - Drops the sponsored teaser ("E após as notícias de hoje: ...") and drops each news item's closing editorial/commentary sentence, keeping the source-attribution sentence.
  - Produces a **draft**, not a sent email — daily generation is automatic (scheduled), but sending requires manual review/approval (per product decision below).
- New subscriber capture: an email subscription API + storage on the VPS (own database, not an ESP-managed list), so `portfolio-website` can offer a "subscribe" CTA that persists emails.
- New delivery pipeline: sends the approved draft to all subscribers via a transactional email API (Resend), using `newsletter@matheusramos.dev` as the sender identity. DNS records (SPF/DKIM/DMARC) for that domain will be added in Cloudflare during implementation — confirmed feasible, no blocker.
- **Cross-repo dependency, out of scope for this change's implementation**: the actual subscribe button/CTA UI lives in `portfolio-website`, a separate git repository with its own OpenSpec root. This change's `tasks.md` will call out the integration contract (the subscription API endpoint the portfolio button must call), but the button itself must be implemented via a change proposed in the `portfolio-website` repo.

## Capabilities

### New Capabilities
- `newsletter/content-generation`: daily collection of real, sourced tech news and LLM-driven generation (via 9Router) of a draft edition following the reference structure (subject, Curiosidade do dia, news items with source attribution), explicitly excluding sponsored/ad content and per-item editorial commentary.
- `newsletter/subscription`: an API + persistent store for capturing and managing subscriber email addresses, to be called by `portfolio-website`'s subscribe CTA.
- `newsletter/delivery`: review/approval of a generated draft and sending the approved edition to all subscribers via Resend, from `newsletter@matheusramos.dev`.

### Modified Capabilities
(none — greenfield change, no existing specs in this repo)

## Impact

- **New code**: `newsletter-website` backend (news collection, LLM generation client reusing the 9Router integration pattern from `rag-knowledge-assistant`, subscriber API, delivery/send job, draft review surface).
- **New infra on the shared Oracle VPS** (`<VPS_HOST_IP>`): a new Docker service (own `docker-compose.yml`, following the `rag_api`/`router`/`qdrant` pattern), a subscriber database (SQLite/Postgres, proposed in design.md), an Nginx location block for the subscription API (following the existing `/projects/rag/` reverse-proxy pattern) — must not disturb the existing `matheusramos.dev` or `rag.matheusramos.dev` configs.
- **New external dependency**: Resend (transactional email API) account + API key (to be provided during implementation).
- **DNS**: new records on the `matheusramos.dev` zone in Cloudflare for email authentication (SPF/DKIM/DMARC) — DNS-only, not proxied.
- **`portfolio-website` repo** (separate repo, not edited by this change): needs a new subscribe CTA calling the subscription API — tracked as an explicit integration task, to be implemented via that repo's own change.
- **No existing functionality removed**: `portfolio-website`'s current pages/content stay intact; `rag-knowledge-assistant`'s use of 9Router/VPS resources is unaffected (new service is additive).
