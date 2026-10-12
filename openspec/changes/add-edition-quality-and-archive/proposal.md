## Why

The 2026-09-24 edition published an entire item in English ("RemControl Android banking malware spreads in Europe…") despite the newsletter being Portuguese-only, and a separate edition's subject line said "$1.300" while the body said "US$ 1.299" — a currency and number mismatch a reader would notice immediately. Neither language nor title/body numeric consistency is currently checked before an edition reaches the owner's approval link. Separately, the site only ever shows the single most recent edition; there's no way for a reader to see which article informed a given paragraph, or to browse past editions at all — `portfolio-website`'s `/latest` response has no source URLs, and nothing renders a list of prior editions.

## What Changes

- Add a per-item Portuguese-language check after generation and before an edition is held for approval: any item (including the subject line) not in pt-BR is regenerated/translated automatically before the draft reaches the pending-review state. Reinforce the generation prompt to explicitly require pt-BR for all content, including headlines.
- Add a subject/body numeric-consistency check: any number that appears in the subject line SHALL also appear in the body; if it doesn't, the subject is regenerated. Standardize currency formatting as "US$" throughout (the source of the "$1.300"/"US$ 1.299" mismatch was inconsistent currency notation, not just a wrong number).
- Persist each news item's original source URL (already collected from the RSS feed as `Article.url`, currently discarded after generation) alongside the edition, and expose it via `GET /api/newsletter/latest` as an additive field — the current response shape (`subject`, `body`, `sent_at`) is unchanged, only extended. Update `docs/api-contract.md` to document the new field.
- Add a server-rendered archive: `GET /newsletter/edicoes/` (list of past sent editions) and `GET /newsletter/edicoes/<data>/` (a single edition's full content), rendered as HTML directly by this FastAPI service — not a separate SSG rebuild, since `portfolio-website`'s build is local/rsync-based and doesn't rebuild on a webhook. Visual style (header, footer, CSS) matches `portfolio-website`'s site design. `portfolio-website` needs a new Nginx `location /newsletter/edicoes/` to proxy to this route (tracked as a dependent task in that repo's `improve-newsletter-page` change).
- **BREAKING**: None. The `/latest` response gains a field, editions already sent are unaffected, and the new archive routes are net-new.

## Capabilities

### New Capabilities
- `newsletter/archive`: Exposes newsletter editions to the public — the source-URL-enriched `/latest` API consumed by `portfolio-website`, and the server-rendered archive of past editions.

### Modified Capabilities
None — the language and numeric-consistency checks are new quality gates on the generation pipeline, not changes to what "Reference structure compliance" already requires structurally (subject/opening/paragraph shape is unchanged; these are new, additive requirements on top of it).

This change adds the following new requirements to `newsletter/content-generation` (same spec file, no new capability directory):
- `Portuguese Language Consistency` — every item, including the subject, is checked and corrected to pt-BR before an edition leaves draft state.
- `Subject-Body Numeric Consistency` — numbers in the subject must appear in the body, with currency standardized as "US$".

## Impact

- **Code**: `app/generation/validation.py` (or equivalent — add language and numeric-consistency checks to the existing draft-validation step), `app/generation/pipeline.py` (persist article URLs alongside generated paragraphs), `app/storage/editions.py` (schema: a new column/table for per-paragraph source URLs), `app/api/routes_public.py` (extend `/latest` response; add the two new archive routes and their HTML rendering).
- **Data**: existing sent editions have no stored source URLs (they predate this change) — the archive and enriched `/latest` response must degrade gracefully for those (no source line/URL for pre-existing editions), not error.
- **Docs**: `docs/api-contract.md` updated for the new `/latest` field and the two new archive endpoints.
- **Cross-repo**: `portfolio-website`'s `improve-newsletter-page` change depends on this change's source URLs and archive routes; see that change's tasks for sequencing (it must confirm this change is live before linking to the archive, to avoid a dead link).
