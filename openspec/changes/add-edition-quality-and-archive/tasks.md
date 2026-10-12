## 1. Language consistency check

- [ ] 1.1 Reinforce the generation prompt(s) in `app/generation/prompts.py` to explicitly require pt-BR for all content, including headlines/subject.
- [ ] 1.2 Add a per-item language check to `app/generation/validation.py` (or the validation step called from `_generate_once`), covering the subject and every news paragraph; verify with a test asserting a deliberately English item fails the check.
- [ ] 1.3 On a failed language check, regenerate/translate the offending item before the draft is persisted as pending; verify with a test that a regenerated item passes the check afterward.

## 2. Subject-body numeric consistency

- [ ] 2.1 Add a check to `app/generation/validation.py` that extracts numbers from the subject line and confirms each appears in the body; verify with a test using the reported "$1.300"/"US$ 1.299" mismatch shape.
- [ ] 2.2 On a failed check, regenerate the subject line before the draft is persisted as pending; verify with a test that the regenerated subject's numbers match the body.
- [ ] 2.3 Standardize currency formatting as "US$" in the generation prompts and/or a post-processing normalization step; verify with a test covering a "$X" input being normalized to "US$ X".

## 3. Source URL persistence

- [ ] 3.1 Add an `edition_sources` table (`edition_date`, `position`, `url`) via a migration in `app/storage/db.py`, per design.md Decision 3; verify the migration runs cleanly against the existing database.
- [ ] 3.2 Update `app/generation/pipeline.py` to persist each selected article's URL alongside its paragraph's position when saving a draft; verify with a test that `edition_sources` rows match `selected`/`news_paragraphs` order.
- [ ] 3.3 Update `GET /api/newsletter/latest` in `app/api/routes_public.py` to include a `sources` array (aligned by position with the news paragraphs) when available, and omit it (not error) for editions predating this change; verify both cases with tests.
- [ ] 3.4 Update `docs/api-contract.md` to document the new `sources` field on `/latest`, including an example and the "no sources for old editions" behavior.

## 4. Public archive

- [ ] 4.1 Copy `portfolio-website`'s relevant CSS tokens/header/footer styling into this repo, per design.md Decision 4, documenting the source in a comment.
- [ ] 4.2 Implement `GET /newsletter/edicoes/` rendering a chronological list of sent editions (subject, sent date, link to detail); verify it lists all sent editions, most recent first.
- [ ] 4.3 Implement `GET /newsletter/edicoes/<data>/` rendering a single edition's full subject/body/sources; verify it renders correctly for both an edition with sources and one without (pre-migration data).
- [ ] 4.4 Verify visually that both archive pages match the portfolio site's look (header, footer, typography, spacing) at mobile and desktop widths.

## 5. Verification

- [ ] 5.1 Run the existing test suite (`python3 -m unittest discover -s tests -v`) and confirm all tests pass, including the new ones added above.
- [ ] 5.2 Manually generate a test draft with a deliberately non-Portuguese item and a subject/body number mismatch, and confirm both are corrected before the draft would reach pending-review.
- [ ] 5.3 Confirm `GET /api/newsletter/latest`'s response shape is unchanged for existing consumers aside from the additive `sources` field (no field removed or renamed), directly against `docs/api-contract.md`'s documented example.
