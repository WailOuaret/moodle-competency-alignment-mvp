# Data and Experiment Description

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

An inventory of every dataset in the project, with its purpose, size, and
handling rules.

**Status vocabulary**

| Term | Meaning |
|---|---|
| **Frozen** | Part of the reported experiment. Must not be regenerated. |
| **Derived** | Computed from frozen inputs. May be regenerated deterministically. |
| **Human** | Contains human judgement. Never synthesised or pre-filled. |
| **Optional** | Post-hoc or optional work, isolated from core results. |
| **Pending** | Awaits human input; does not yet exist. |

---

## 1. Raw extraction

### `data/raw/api/`

Verbatim Moodle web-service responses.

| Property | Value |
|---|---|
| Purpose | Immutable record of what Moodle returned |
| Files | `courses.json`, `course_contents_MVP-SW.json`, `course_contents_MVP-DATA.json`, `pages_by_courses.json`, `quizzes_by_courses.json`, `site_info.json`, `extraction_manifest.json` |
| Status | **Frozen** |
| Regenerable | Only against the same live Moodle instance |
| Distribution | **Excluded** — may contain private Moodle fields |

`site_info.json` contains a `userprivateaccesskey` and is excluded from every
archive.

### `data/raw/sql/`

Quiz question text obtained by direct database query, because the web services do
not expose it usably on Moodle 5.2.

| Property | Value |
|---|---|
| Records | 12 quiz questions with answer options |
| Status | **Frozen** |
| Distribution | Excluded from shareable archives |

---

## 2. Processed corpus

### `data/processed/resources.jsonl`

| Property | Value |
|---|---|
| Purpose | Normalised units a teacher acts upon |
| Records | **20** (8 Pages, 12 quiz questions) |
| Status | **Frozen** · Derived from raw extraction |
| Key fields | `resource_id`, `resource_type`, `title`, `text`, `search_text`, `course_shortname`, `section_name`, plus full Moodle provenance |

Each quiz question is an independent resource rather than being folded into its
quiz.

### `data/processed/fragments.jsonl`

| Property | Value |
|---|---|
| Purpose | The unit of model operation and of reference annotation |
| Records | **35** (23 page chunks, 12 quiz-question fragments) |
| Status | **Frozen** |
| Key fields | `fragment_id`, `resource_id`, `fragment_index`, `fragment_type`, `text`, character and word counts, provenance |

Identifiers follow `{resource_id}#f{NNN}`, so the parent resource is recoverable
from the identifier alone.

### `data/processed/competencies.jsonl`

| Property | Value |
|---|---|
| Purpose | The competency catalogue used for retrieval and selection |
| Records | **13** (3 top-level, 10 children) |
| Status | **Frozen** |
| Key fields | `idnumber`, `shortname`, `description_text`, `depth`, `parent_idnumber`, `hierarchy_labels`, `search_text` |

Parent–child relations only; no prerequisite or related-to relations exist.

### `data/processed/utc_gi_mvp_moodle.csv`

The Moodle import CSV generated from the framework subset. An **input** to Moodle,
not a model output. Frozen, with a recorded checksum.

---

## 3. Retrieval and model

### `data/interim/bm25_candidates.jsonl`

| Property | Value |
|---|---|
| Purpose | Top-5 candidates per fragment; defines the model's search space |
| Records | **35** candidate sets, 5 candidates each |
| Status | **Frozen** |
| Key fields | `fragment_id`, `candidates[{idnumber, rank, bm25_score}]`, `query_text` |

Retaining ranks is what makes retrieval failure distinguishable from model error,
both in analysis and in the review interface.

### `data/interim/llm_tasks.jsonl`

| Property | Value |
|---|---|
| Purpose | The exact task sent to the model, including the full prompt |
| Records | **35** |
| Status | **Frozen** |
| Key fields | `task_id`, `fragment_text`, `allowed_idnumbers`, `candidates`, `instructions`, `output_contract`, `prompt` |

Storing the prompt verbatim means the experiment can be audited without
reconstructing it.

### `data/interim/gemini_responses.jsonl` and `gemini_validated.jsonl`

| Property | Value |
|---|---|
| Purpose | Raw and validated model output |
| Records | **35** each; 35 valid, 0 rejected |
| Status | **Frozen** · **must never be regenerated** |
| Key fields | `fragment_id`, `selected[{idnumber, confidence, evidence[], reason}]`, `abstain`, `valid`, `validation_errors` |
| Total predicted labels | 51 |

The model is a third-party service whose behaviour may change. Reproduction
proceeds from these stored responses, not from repeated calls. No restart
mechanism exists.

---

## 4. Human reference

### `data/gold/manual_fragment_annotations.csv`

The reference against which every result is scored.

| Property | Value |
|---|---|
| Purpose | Human-reviewed reference annotation |
| Records | **35** rows, one per fragment |
| Reference labels | **38** |
| Multi-label fragments | 3 |
| Ambiguous fragments | 1 (`page:3#f003`) |
| Fragments with no applicable competency | **0** |
| Annotator | Wail Ouaret |
| Date | 18 September 2026 |
| Status | **Frozen · Human** |
| Validation | `scripts/12_validate_manual_annotations.py --mode final` — PASSED |

Labels were assigned **only at child level**; all three top-level competencies
have zero reference support.

One annotator produced all 38 labels. No second annotator participated and no
inter-annotator agreement was measured. These are *human-reviewed reference
annotations*, not independent blinded gold and not machine-generated.

Backups of intermediate states are in `data/gold/annotation_backups/` and are
excluded from distribution archives.

### `data/gold/manual_moodle_links.csv`

Activity-level competency links from Moodle: 10 rows. **Not** used as
question-level ground truth, because such a link describes an entire quiz.
Retained for reference only.

---

## 5. Human evidence review

### `data/reviews/evidence_review.csv`

| Property | Value |
|---|---|
| Purpose | Mechanical and pedagogical assessment of every evidence quotation |
| Records | **83** quotations |
| Mechanically valid | 83 (100 %) |
| Rated `2` / `1` / `0` | 65 / 16 / 2 |
| Reviewer | Wail Ouaret |
| Date | 18 September 2026 |
| Status | **Frozen · Human** · complete |

Two distinct measurements are recorded per row: `mechanically_valid`, computed by
the validator, and `pedagogical_rating`, supplied by a human. They are never
conflated. Character offsets were derived independently for audit; the quotations
were not modified.

The review was performed by the person who produced the reference, so it is a
check of internal consistency rather than an independent assessment.

---

## 6. Aggregated predictions

### `data/processed/resource_predictions.jsonl`

| Property | Value |
|---|---|
| Purpose | Function A — resource to competencies |
| Records | **20** resources, **34** resource-competency mappings |
| Status | **Derived** from validated model output |
| Key fields | `resource_id`, `predicted_competencies[{competency_id, fragment_ids, support_count, max_confidence, evidence}]` |

### `data/processed/competency_resource_index.jsonl`

| Property | Value |
|---|---|
| Purpose | Function B — competency to resources |
| Records | **13**, one per competency; all have at least one resource |
| Status | **Derived** |

All thirteen competencies appear, but the three top-level entries exist only
because of parent–child redundancy. This is predicted coverage, not validated
coverage.

### `data/processed/resource_reference.jsonl`

| Property | Value |
|---|---|
| Purpose | Resource-level reference for evaluation |
| Records | **20** |
| Status | **Derived** from the fragment reference |

Records `reference_derivation` explicitly. Not a second annotation exercise.

---

## 7. Hierarchy analysis

### `data/processed/graph_warnings.jsonl`

| Property | Value |
|---|---|
| Purpose | Hierarchy consistency warnings |
| Records | **17** warnings |
| Status | **Derived** · diagnostic only |
| Findings | 10 fragments with parent–child redundancy, 7 granularity conflicts, 0 invalid references |

Warnings only. Predictions are never modified:
`original_predictions_modified: false`.

### `data/experiments/graph_child_preference_*.jsonl`

| Property | Value |
|---|---|
| Purpose | Post-hoc ablation removing redundant parents |
| Status | **Optional · post-hoc** |
| Location | `data/experiments/` — cannot overwrite core predictions |

Labelled a post-hoc ablation wherever it appears; never presented as the original
system.

---

## 8. Evidence-usefulness pilot

### `data/studies/teacher_study_cases.csv` and `teacher_study_manifest.json`

| Property | Value |
|---|---|
| Purpose | Reproducible A/B design for the evidence-usefulness pilot |
| Records | **12** cases from 51 candidates |
| Conditions | A (evidence hidden) 6 · B (evidence shown) 6 |
| Strata | 4 correct · 4 incorrect · 4 parent–child redundancy |
| Courses | 8 MVP-SW · 4 MVP-DATA |
| Resource types | 6 Pages · 6 quiz questions |
| Seed | 20260918 |
| Status | **Derived** · reproducible |

### `data/studies/teacher_study_responses.csv`

| Property | Value |
|---|---|
| Purpose | Recorded pilot responses |
| Records | **0 — the file does not exist** |
| Status | **Pending** |

No response has been recorded and none will be simulated.

---

## 9. Review decisions

### `data/reviews/corpus_teacher_reviews.csv`

| Property | Value |
|---|---|
| Purpose | Teacher decisions on the frozen corpus |
| Reviewable mappings | 34 |
| Records | **0 — the file does not exist** |
| Status | **Pending · Human** |

Written by the review interface, atomically and after a timestamped backup. No
decision is pre-filled or suggested.

### `data/reviews/teacher_reviews.csv`

| Property | Value |
|---|---|
| Purpose | Runtime application review log — a **different schema** |
| Records | **2**, both `reviewer_role = researcher` |
| Status | **Human** · not corpus validation |

Recorded by Wail Ouaret on 18 September 2026 through the runtime application: one
rejection of `GI_C3`, one acceptance of `GI_C3_1`. These concern an ad-hoc
analysis, not the frozen corpus, and are reported separately from any teacher
validation.

The two files are kept distinct because they use different schemas; merging them
would destroy real recorded decisions.

---

## 10. Results

### `reports/metrics/`

Twelve JSON files, all parsing. Derived; regenerable deterministically.

| File | Content |
|---|---|
| `bm25_metrics.json` | Recall@K, Hit@K, MRR, Top-1 P/R/F1 |
| `constrained_llm_metrics.json` | Micro and macro P/R/F1, exact-set, coverage |
| `macro_label_views.json` | Both macro views with per-label support |
| `error_summary.json` | Error categories, primary categories, evidence quality |
| `evidence_review_summary.json` | Mechanical and pedagogical evidence results |
| `resource_level_metrics.json` | Resource-level evaluation |
| `graph_check_summary.json` | Hierarchy warnings |
| `graph_child_preference_*_metrics.json` | Post-hoc ablation |
| `resource_graph_check_summary.json` | Resource-level hierarchy warnings |
| `teacher_review_summary.json` | Review status; null rates while pending |
| `human_validation_summary.json` | Human-validation status |

### `reports/tables/`

Twenty-three CSV tables: per-fragment and per-competency detail for both systems,
error analysis with worked examples, the system delta, label support, ablation
comparisons, and the review summary.

### `reports/figures/`

Five PNG figures: BM25 Recall@K, error categories, evidence quality, and
fragment- and resource-level system comparisons.

---

## 11. Optional experiments

### `data/experiments/unconstrained_llm_tasks.jsonl`

| Property | Value |
|---|---|
| Purpose | All-13 condition tasks, for the candidate-restriction comparison |
| Records | **35** tasks, 13 candidates each |
| Status | **Optional** · tasks built, **experiment not run** |

An automated audit confirms the two conditions differ only in candidate space: 0
fragment-text mismatches and 0 instruction mismatches across all 35 fragments,
with the same validator reused unchanged.

`unconstrained_gemini_responses.jsonl` and `unconstrained_gemini_validated.jsonl`
do not exist. The manifest records null for them rather than a placeholder.

### `data/experiments/ollama_constrained_*.jsonl`

A post-hoc comparison with a local model, isolated from the core results.

---

## 12. Summary

| Dataset | Records | Status | Regenerable |
|---|---:|---|---|
| Raw extraction | — | Frozen | Only from live Moodle |
| `resources.jsonl` | 20 | Frozen | No |
| `fragments.jsonl` | 35 | Frozen | No |
| `competencies.jsonl` | 13 | Frozen | No |
| `bm25_candidates.jsonl` | 35 | Frozen | No |
| `llm_tasks.jsonl` | 35 | Frozen | No |
| `gemini_validated.jsonl` | 35 | Frozen | **Never** |
| Reference annotations | 35 / 38 labels | Frozen, human | Never |
| Evidence review | 83 | Frozen, human | Never |
| `resource_predictions.jsonl` | 20 / 34 mappings | Derived | Yes |
| `competency_resource_index.jsonl` | 13 | Derived | Yes |
| `resource_reference.jsonl` | 20 | Derived | Yes |
| `graph_warnings.jsonl` | 17 | Derived | Yes |
| Metric files | 12 | Derived | Yes |
| Result tables | 23 | Derived | Yes |
| Pilot design | 12 cases | Derived | Yes, same seed |
| Pilot responses | **0** | Pending | Human only |
| Corpus teacher reviews | **0** | Pending | Human only |
| Runtime reviews | 2 | Human | Never |
| Unconstrained tasks | 35 | Optional | Yes |
| Unconstrained responses | **0** | Optional, not run | Requires authorisation |
