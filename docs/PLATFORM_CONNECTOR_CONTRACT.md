# Platform connector contract

**Status:** the fields below are what the current engine actually reads.  
**Not implemented:** a live connector for Canvas, D2L, Open edX, Blackboard, or a production REST service.

Code: `src/moodle_competency/resource_contract.py` (`validate_resource_record`, `validate_competency_record`).

Frozen experiment scripts are not required to call this validator. New connectors should.

---

## 1. What a connector must output

One JSON object per learning resource (or per quiz question). The alignment engine does not call the LMS.

```text
LMS API or export
    → connector (platform-specific)
    → normalized resource record
    → existing fragmentation / BM25 / constrained LLM / evidence check
```

## 2. Required fields

| Field | Type | Why |
|---|---|---|
| `resource_id` | non-empty string, no whitespace | Fragment IDs are `{resource_id}#f001`. Must stay stable across reruns. |
| `resource_type` | string | Chooses the fragment strategy. See below. |
| `title` | string | Shown to reviewers and included in the BM25 query. |
| `text` | string | Body that is fragmented. HTML must already be plain text. |

Empty `resource_id` is skipped by `create_fragments`. Empty `text` produces no fragments.

## 3. Optional fields

| Field | Used for |
|---|---|
| `search_text` | BM25 query. Quiz questions put the stem plus answer options here while `text` stays the stem. If omitted, retrieval falls back to `text`. |
| `course_id`, `course_shortname`, `course_fullname` | Provenance and query context (`course_fullname` is searched). |
| `section_name`, `activity_name` | Provenance and BM25 query. |
| `activity_id`, `source_item_id`, `course_module_id`, `section_id`, `section_number` | Provenance and a future write-back. Not required to align. |
| `source_extraction` | How the record was produced (`moodle_rest`, `postgresql_read_only`, `moodle_assignment_adapter`, …). |
| `metadata` | Object. Ignored by retrieval. |

## 4. Stable IDs

- `resource_id` must not change when the title is edited if you want reviews to stay attached.
- Prefer platform IDs (`page:59`, `quiz_question:1:4`, `assignment:44`) over hashes of the text.
- Runtime uploads currently use a content hash (`runtime:{source}:{digest}`). That is fine for a demo and weak for production write-back, because an edit creates a new ID.

## 5. Text normalization

Connectors must:

- strip scripts, styles, and tags;
- keep heading and paragraph breaks where the author used them;
- not send student submissions, grades, or names unless a later protocol explicitly allows it.

The engine tokenizes with a Unicode letter/number pattern (`retrieval.tokenize`). It does not stem and it does not drop stop-words.

## 6. Quiz questions

**Implemented and evaluated:** each Moodle question is its own resource (`resource_type = quiz_question`). Fragmentation emits exactly one fragment and uses `search_text` (stem + `Answer options: …`).

Do not collapse every question into the parent quiz. Activity-level competency links are not question labels.

## 7. Answer options

Options belong in `search_text` and in `metadata`, not as separate competencies. The frozen quiz normalizer (`normalization.normalize_quiz_questions`) already does this. A Canvas or other connector must do the same if questions have choices.

## 8. Framework representation

Separate from the resource. One record per competency:

| Field | Required |
|---|---|
| `idnumber` | yes — the ID the model must return |
| `shortname` | yes |
| `description_text` | yes — plain text |
| `parent_idnumber` | optional; empty for roots; must not equal `idnumber` |
| `framework_idnumber` | optional; used in the BM25 profile |
| `search_text` | optional; built from name, description, parent, framework |

The engine does **not** require the IDs to look like `GI_C1_1`. Hierarchy checks use `parent_idnumber`. One error-analysis helper (`error_analysis.parent_of`) still assumes the `GI_C1_2 → GI_C1` spelling. That helper is experiment reporting, not the alignment path.

## 9. Error handling

`validate_resource_record` returns a list of problems. `assert_resource_record` raises `ResourceContractError`.

Connectors should reject the record before retrieval when required text is missing. They must not invent a competency label to fill a gap.

## 10. Write-back boundary

The contract is **read-only input**. Nothing in this schema writes a competency link back to an LMS.

Official links, if ever written, come only from a later human ACCEPT or MODIFY. See the write-back section of `reports/SCALABILITY_AND_INTEGRATION_AUDIT.md`.

## Resource-type behaviour (code, today)

| `resource_type` | Fragmentation | Evaluated on the frozen corpus? |
|---|---|---|
| `page` | author/length chunks, `page_chunk` | yes |
| `quiz_question` | one fragment | yes |
| `pasted_text`, `uploaded_txt`, `uploaded_html`, `uploaded_pdf` | `resource_chunk` via the generic branch | runtime only, not the 35-fragment metrics |
| `assignment` | `resource_chunk` via `assignment_adapter.normalize_assignment` | **no** — adapter tested offline only |
| anything else with `text` | `resource_chunk` | not evaluated |

`fragmentation.validate_fragments` still **requires 20 resources and 12 quiz questions**. That check is the frozen-corpus acceptance test. Do not use it as the production validator.
