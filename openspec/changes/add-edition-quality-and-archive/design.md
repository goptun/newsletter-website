## Context

See `proposal.md` for motivation. Relevant current state:

- `app/news/feeds.py`'s `Article` dataclass already has a `url: str` field, populated from the RSS feed entry — the source URL is available at collection time.
- `app/generation/pipeline.py`'s `_generate_once` builds `news_paragraphs` as a list, one per `article` in `selected` (both in the same order), then `generate_daily_edition` joins them into `body = curiosidade + "\n\n" + "\n\n".join(news_paragraphs)`. This positional correspondence between `selected[i]` (which has `.url`) and `news_paragraphs[i]` is what makes persisting sources without restructuring `body` possible.
- `app/storage/editions.py`'s `Edition` only stores `subject` and `body` as plain text; there is no existing structure for per-item metadata.
- `docs/api-contract.md`'s `/api/newsletter/latest` contract returns `{ subject, body, sent_at }`, with `body` as plain text, paragraphs separated by blank lines — this is a stable, documented contract consumed by `portfolio-website`.
- `portfolio-website`'s build is a local `astro build` + rsync (see that repo's `DEPLOY.md`); it does not rebuild on a webhook or on a schedule, so a statically-generated archive page there would go stale immediately after each new edition. Server-side rendering the archive from this FastAPI service (which already serves `/api/newsletter/*` behind the same Nginx) avoids that staleness entirely.

## Goals / Non-Goals

**Goals:**
- Catch language and title/body-consistency defects before an edition reaches the owner's approval link, not after subscribers already received it.
- Make source attribution and an edition archive possible without breaking the existing `/latest` contract or requiring `portfolio-website` to rebuild per edition.

**Non-Goals:**
- Re-checking or backfilling source URLs / language / numeric consistency for already-sent editions — this applies going forward only.
- A full-text search or tagging system for the archive — a simple chronological list is sufficient for this change.
- Changing how editions are approved/rejected/sent (`newsletter/delivery`) — the new checks run before a draft reaches pending-review, not at approval time.

## Decisions

### 1. Where the language/numeric checks run
Add both checks to the existing draft-validation step (`app/generation/validation.py`, called from `_generate_once`/`generate_daily_edition` before a draft is persisted as pending). This is the same place `validate_draft(subject, curiosidade, news_paragraphs)` already runs today, so both new checks compose with existing validation rather than introducing a second pass.

**Alternative considered**: check language/numeric consistency as a separate post-generation job, run independently before the owner's approval link is sent. Rejected — it would let an invalid draft reach `draft`/pending-review state and only get caught later, versus catching it inline where a bad draft can be regenerated immediately, consistent with how the existing "Real, sourced news only" requirement already handles failure (mark incomplete / regenerate before persisting as pending).

### 2. Language detection and correction
Detect language per item (subject + each news paragraph) using the same 9Router-backed LLM client already used for generation (a lightweight classification prompt, not a new dependency), and on a non-pt-BR result, regenerate that item with an explicit pt-BR instruction reinforced in the prompt (per proposal.md). This reuses the existing LLM client rather than adding a language-detection library, keeping the dependency surface the same as the rest of the generation pipeline.

### 3. Source URL persistence: a parallel per-edition sources table
Add a new table (e.g. `edition_sources(edition_date, position, url)`) rather than a JSON column on `editions`, keyed by `edition_date` (already the editions table's natural key) and the paragraph's position among the news items (0-indexed, matching `selected`/`news_paragraphs` order). `/latest` joins this table when building its response and includes a `sources` array aligned by position with the news paragraphs.

**Alternative considered**: a single JSON column on `editions` (e.g. `sources_json`). Rejected in favor of a proper table — this data has a natural per-item shape (one URL per news paragraph), a normalized table is simpler to query for the archive feature (Decision 4) than parsing JSON per row, and it matches this project's existing use of SQLite tables for structured data (`editions`, `subscribers`) rather than JSON blobs.

**Compatibility**: editions sent before this change has no rows in `edition_sources`; `/latest` and the archive both simply return an empty/absent `sources` array for those, per the "Older edition without stored source URLs" scenario in specs.

### 4. Archive rendering: server-side HTML from this FastAPI service
`GET /newsletter/edicoes/` and `GET /newsletter/edicoes/<data>/` render HTML directly in `app/api/routes_public.py` (or a new `app/api/routes_archive.py`), querying `editions` (status = sent) and the new `edition_sources` table. Styling matches `portfolio-website`'s site: copy the site's CSS custom properties/tokens into this service (same approach already used by `rag-knowledge-assistant`'s demo page, which mirrors the portfolio's header/footer/tokens) rather than fetching the portfolio's CSS at request time, to avoid a runtime cross-service dependency for every archive page view.

**Alternative considered**: have `portfolio-website` statically pre-render archive pages at build time by fetching all editions from this API. Rejected — per Context, that build doesn't run on a schedule or webhook, so the archive would only update whenever someone happens to redeploy the portfolio site, defeating the purpose of a growing archive.

## Risks / Trade-offs

- **[Risk]** The language-detection prompt could misclassify a short/ambiguous item (e.g. a headline that's mostly a proper noun). → **Mitigation**: this is a real risk with any automated language check; accepted because the alternative (no check) is the bug this change fixes. If misclassification proves frequent in practice, tune the prompt/threshold as a follow-up, not blocking this change.
- **[Risk]** Copying `portfolio-website`'s CSS tokens into this repo (Decision 4) means the two can drift out of sync over time if one changes without the other being updated. → **Mitigation**: same accepted trade-off already made for `rag-knowledge-assistant`'s demo page; document the token source in this repo the same way.
- **[Trade-off]** Storing sources in a new table (Decision 3) requires a schema migration; simpler than a JSON column to query but is a real, one-time migration step to sequence carefully in tasks.md.
