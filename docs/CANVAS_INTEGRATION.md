# Canvas integration

**Status: architecturally compatible; connector not yet implemented.**

No Canvas course has been extracted. No Canvas outcome set has been indexed. The published metrics are Moodle-only. Do not describe this MVP as validated on Canvas.

The intended path, which matches how Moodle content already enters the engine:

```text
Canvas REST API
    → Canvas adapter (not written)
    → normalized resource / competency records
    → unchanged fragmentation, BM25, constrained model, evidence check
```

Contract: `docs/PLATFORM_CONNECTOR_CONTRACT.md`.

---

## Resource mapping (design)

| Canvas | Normalized `resource_type` | Notes |
|---|---|---|
| Page | `page` | HTML body → `text` after the same cleaning rules |
| Quiz question | `quiz_question` | One resource per question, not per quiz |
| Assignment description | `assignment` | Stem/instructions only. Not student submissions. Adapter pattern exists for Moodle; Canvas variant does not. |
| Discussion topic prompt | not implemented | Would be another adapter if the text is course material |
| File (PDF) | `uploaded_pdf` only if text-native | No OCR |

Stable ID examples: `canvas:page:{course_id}:{page_url}`, `canvas:quiz_question:{quiz_id}:{question_id}`.

## Competency / outcome mapping (design)

| Canvas | Normalized field |
|---|---|
| Outcome id | `idnumber` (stringify; do not invent a second ID) |
| Outcome title | `shortname` |
| Outcome description | `description_text` |
| Outcome group | `framework_idnumber` / parent when the group is a real parent |
| Vendor GUID, if present | keep in `metadata`; do not replace `idnumber` if teachers already know the outcome id |

Canvas outcome groups are not automatically the same thing as Moodle parent competencies. A human must confirm the parent links before hierarchy warnings are meaningful.

## What an implementer would call

These names follow Canvas’s public REST documentation and **require documentation verification** against the tenant’s current API before coding:

- course pages
- quiz questions
- outcome groups and outcomes
- OAuth2 access token for a developer key

Pagination is required. Canvas list endpoints are paged. A connector that stops at the first page will silently drop resources.

HTML in page bodies must be reduced to text before `text` / `search_text` are set. Answer choices on quiz questions must be appended to `search_text` the way `normalize_quiz_questions` does, and must not be copied onto every question from the parent quiz.

## Authentication

Not implemented. A production connector needs a Canvas developer key, OAuth2, and a stored refresh token per institution. Do not put the token in the resource JSON or in git.

## Provenance

Keep Canvas course id, content id, and `updated_at` in `metadata`. Use `updated_at` later for incremental runs (re-align only when the hash of `text` changes). That cache does not exist yet.

## Write-back

Not implemented. If it is added later, the only payload is a teacher-accepted or teacher-modified outcome id, written through Canvas’s outcome-result or rubric API after a documented review record exists. Model output alone must not create an official link. Exact write endpoints **require documentation verification**; they differ by whether the institution uses classic outcomes or a newer mastery service.

## What does not need to change

`fragmentation.create_fragments` (generic branch), `BM25CompetencyRetriever`, `build_alignment_task`, `validate_alignment_response`, `aggregate_fragment_predictions`, `graph_checks` (if `parent_idnumber` is filled).

## What must change

A new package, for example `src/moodle_competency/connectors/canvas.py`, plus fixture tests that never call Canvas. The frozen Moodle JSONL files stay untouched. New metrics files would be required after a real Canvas reference is annotated.
