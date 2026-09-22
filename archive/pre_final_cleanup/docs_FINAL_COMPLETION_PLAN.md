# Cursor Master Prompt — Finish the Moodle Competency Alignment MVP

Read this entire prompt before changing anything.

You are finishing an EXISTING research project:

**Moodle Learning Resource-to-Competency Alignment MVP**

Workspace:
`~/projects/moodle_competency_mvp`

Researcher:
**Wail Ouaret**

Supervisors:
- Marie-Hélène Abel
- Le Ngoc Luyen
- UTC / Heudiasyc / CNRS

Do NOT rebuild the project from scratch.

The repository already contains a functioning extraction → normalization → fragmentation → BM25 Top-5 → constrained Gemini → exact-evidence validation → aggregation → evaluation pipeline.

Your job now is to finish the remaining research software, human-review tooling, optional post-core experiments, final reporting, and demo package while preserving all validated results.

---

# A. VERIFIED CURRENT STATE — FREEZE THESE FACTS

Use the live repository to recheck them before changing anything, but the latest verified state is:

## Corpus
- Moodle 5.2.1+
- 2 courses: `MVP-SW`, `MVP-DATA`
- 8 Pages
- 2 Quizzes
- 12 Quiz questions
- 20 normalized research resources
  - 8 Pages
  - 12 Quiz questions kept as independent resources
- 35 fragments
  - 23 Page chunks
  - 12 Quiz-question fragments
- 13 UTC GI competencies
  - 3 parent
  - 10 child
- 38 reference competency labels across the 35 fragments
- 3 multi-label reference fragments
- 1 ambiguous reference fragment
- 0 reference NONE fragments

## Retrieval / LLM
- 35/35 BM25 Top-5 candidate sets
- 35/35 constrained LLM tasks
- 35/35 valid Gemini responses
- model: `gemini-3.5-flash`
- temperature: 0
- BM25 Top-5 restriction
- max selections: 3
- exact-evidence validation enabled
- 0 invalid accepted
- 0 missing Gemini responses

## Reference annotations
- `data/gold/manual_fragment_annotations.csv`
- 35/35 complete
- validator PASSED
- annotator: Wail Ouaret
- date: 2026-09-18
- terminology: **human-reviewed reference annotations**
- do NOT call them “independent blinded gold from scratch”
- do NOT call them “AI-generated gold”
- there is no second annotator
- there is no inter-annotator agreement measurement

## Final current results

### BM25
- Recall@1 = 0.6842105263
- Recall@3 = 0.8684210526
- Recall@5 = 0.9736842105
- Hit@1 = 0.7428571429
- Hit@3 = 0.8857142857
- Hit@5 = 0.9714285714
- MRR = 0.8309523810
- Top-1 micro precision = 0.7428571429
- Top-1 micro recall = 0.6842105263
- Top-1 micro F1 = 0.7123287671
- Top-1 macro precision = 0.6538461538
- Top-1 macro recall = 0.5619658120
- Top-1 macro F1 = 0.5899806076

### BM25 Top-5 + constrained Gemini
- micro precision = 0.7254901961
- micro recall = 0.9736842105
- micro F1 = 0.8314606742
- macro precision = 0.6833333333
- macro recall = 0.7435897436
- macro F1 = 0.6958485958
- exact-set match = 0.6285714286
- coverage = 1.0
- abstention rate = 0.0
- average predicted labels / fragment = 1.4571428571

### Current error flags
- correct_prediction = 22
- llm_wrong_selection = 13
- overprediction = 13
- parent_child_redundancy = 10
- retrieval_failure = 1
- underprediction = 1
- llm_missed_gold_label = 0
- incorrect_abstention = 0
- correct_abstention = 0
- ambiguous_gold = 1
- exact_but_weak_evidence = not yet evaluated because Human Gate 2 is open

### Evidence
- 83 evidence-quote rows
- 83/83 mechanically valid exact substrings
- 0 pedagogical ratings completed

### Aggregation / inverse index
- 35/35 fragments accounted for
- 20 resources
- resource aggregation COMPLETE / FINAL
- 13/13 competency index entries
- 34 predicted resource-competency alignments
- all 13 competencies have at least one predicted resource
- teacher decision status = pending

### Tests
Latest project result:
`118 passed`

Compile:
`python -m compileall -q src scripts tests`
succeeds.

Do not hard-code the test count as a success criterion; future additions will increase it.

---

# B. IMPORTANT INTERPRETATION OF CURRENT RESULTS

Preserve these interpretations in the final report unless later experiments change them.

1. BM25 Top-5 Recall is 0.9737.
2. Constrained Gemini micro Recall is also 0.9737.
3. `llm_missed_gold_label = 0`.
4. Therefore the single missed reference label is a RETRIEVAL FAILURE, not an LLM-selection failure.
5. The constrained Gemini system’s dominant error is OVERPREDICTION, especially parent/child redundancy.
6. There are 10 fragments with parent-child redundancy.
7. BM25 Top-1 has slightly higher micro precision than constrained Gemini:
   - 0.7429 vs 0.7255
8. Constrained Gemini has much higher recall:
   - 0.9737 vs 0.6842
9. Micro F1 improves:
   - BM25 Top-1 0.7123
   - BM25+Gemini 0.8315
10. The corpus contains no reference `NONE` fragments, so abstention quality is NOT meaningfully tested. Report this explicitly.
11. Mechanical evidence validity = 100%, but pedagogical sufficiency is still unknown until Human Gate 2.

Do not claim that Gemini “wins overall” without qualification. State the measured trade-off: higher recall and F1, slightly lower micro precision.

---

# C. SUPERVISOR-APPROVED CORE VS EARLIER BROADER PROPOSAL

The latest reduced MVP has priority.

CORE NOW:
- local Moodle
- limited UTC GI framework
- Pages + Quiz questions
- extraction / normalization / fragmentation
- BM25
- constrained LLM
- exact evidence
- resource aggregation
- human reference
- evaluation
- error analysis
- evidence review
- minimal teacher validation interface
- inverse competency → resource view
- reproducibility
- final report / demo

OPTIONAL AFTER CORE:
- unconstrained all-13 Gemini comparison
- minimal graph consistency / reconciliation experiment

DEFERRED unless supervisors explicitly re-open them:
- native Moodle PHP plugin
- Moodle automatic write-back
- LTI
- PDFs / slides / video / audio / OCR
- assignments / rubrics as new corpus types
- full ROME 4.0
- full graph visualization
- recommendation engine / learning paths
- large curriculum analytics dashboard
- teaches / assesses / supports / mentions classification
- fine-tuning
- institution-wide deployment

Do not expand the project into the old proposal before completing the reduced MVP.

---

# D. PROTECTED DATA — NEVER OVERWRITE SILENTLY

Never modify or regenerate these historical experimental files unless explicitly instructed:

- `data/processed/resources.jsonl`
- `data/processed/fragments.jsonl`
- `data/processed/competencies.jsonl`
- `data/interim/bm25_candidates.jsonl`
- `data/interim/llm_tasks.jsonl`
- `data/interim/gemini_responses.jsonl`
- `data/interim/gemini_validated.jsonl`
- `data/gold/manual_fragment_annotations.csv`
- `data/gold/manual_moodle_links.csv`
- current final metric JSON files

If a new experiment is needed, write to NEW files/directories.

Never use `--restart` for historical Gemini.

Never expose `.env`, API keys, Moodle tokens, passwords, or private access keys.

---

# E. FIRST TASK — FULL REPOSITORY AUDIT BEFORE CODING

Before implementing the remaining phases:

1. Read:
   - `README.md`
   - `docs/PROJECT_COMPLETION_MASTER_PLAN.md`
   - `docs/CURRENT_STATUS.md`
   - `docs/EVALUATION.md`
   - `docs/PIPELINE.md`
   - `docs/DATA_DICTIONARY.md`
   - `reports/SUPERVISOR_RESULTS_SUMMARY.md`
   - current metric JSON files
   - current table CSV files

2. Inspect these modules:
   - `aggregation.py`
   - `inverse_index.py`
   - `metrics.py`
   - `evaluation.py`
   - `evidence_review.py`
   - `error_analysis.py`
   - `teacher_reviews.py`
   - `reproducibility.py`

3. Inspect scripts 13–20.

4. Recheck counts from files.

5. Validate current gold:
   `python scripts/12_validate_manual_annotations.py --mode final`

6. Run:
   `python -m pytest -q`

7. Run:
   `python -m compileall -q src scripts tests`

8. Do not change measured outputs during this audit.

Create:
`reports/FINAL_COMPLETION_AUDIT.md`

Include:
- current counts
- current result files
- current missing deliverables
- current methodological limitations
- exact planned next files

---

# F. FIX SMALL EVALUATION / REPRODUCIBILITY GAPS BEFORE NEW FEATURES

## F1. Clarify macro metrics

Current macro metrics use the full 13-label universe.

Keep those values, but also compute and report a second clearly named macro view over competencies with positive human-reference support:

- `macro_all_13`
- `macro_gold_supported_labels`

Do NOT replace the existing metric silently.

Reason:
3 parent competencies have zero reference support in the current 35-fragment reference but are predicted by Gemini. The full-13 macro score usefully penalizes unsupported parent predictions, while the gold-supported macro view helps interpret performance on labels actually represented in the reference.

Add:
- support count per competency
- predicted count per competency
- TP / FP / FN
- precision / recall / F1

Update tests with hand-calculated fixtures that include:
- labels with zero reference support
- labels predicted but absent from gold
- labels absent from both
- normal supported labels

## F2. Add explicit delta table

Create:
`reports/tables/system_delta_summary.csv`

Columns:
- metric
- BM25_Top1
- BM25_Top5_Gemini
- absolute_delta

At minimum:
- micro precision
- micro recall
- micro F1

No “winner” text is needed. Just factual differences.

## F3. Fix reproducibility manifest semantics

Current manifest has:
- `gold_annotation_count = null`
- `gold_annotation_row_count = 35`
- `gold_annotation_complete_count = 35`

Make the schema unambiguous.

Prefer:
- `reference_annotation_row_count`
- `reference_annotation_complete_count`
- `reference_label_count`
- `multi_label_fragment_count`
- `ambiguous_fragment_count`
- `none_fragment_count`

Keep backward compatibility if needed, but do not leave misleading null values.

Add hashes for:
- evidence review
- error analysis
- final graph outputs when created
- teacher review file when created

---

# G. HUMAN GATE 2 — BUILD A SAFE EVIDENCE-RATING HELPER

Current:
`data/reviews/evidence_review.csv`
has 83 rows and `pedagogical_rating` is blank.

Do NOT fill those ratings automatically.

Create:
- `src/moodle_competency/evidence_review_session.py`
- `scripts/review_evidence_pedagogically.py`
- tests

The helper must show ONE evidence row at a time:

- progress X / 83
- fragment ID
- resource ID
- full fragment text
- competency ID
- competency short name
- exact evidence quote
- mechanically_valid

Ask human:

`Pedagogical relevance [0/1/2]:`

Meaning:
- 0 = evidence does not justify the competency
- 1 = partially relevant / ambiguous
- 2 = clearly supports the competency

Then:
- optional comment
- reviewer
- review date

Save after each row.
Resume after interruption.
Create timestamped backups.
Never modify `mechanically_valid`.
Never recommend a rating.

Support:
- `:q`
- `:s`
- `:b`
- `:p`
- `:h`

Add `review_date` to the review schema if absent, with backward-compatible migration.

Also derive deterministic:
- evidence_start
- evidence_end
- offset_valid

from the exact evidence quote, for audit purposes.
Do not change the quote.

Tests:
- valid rating
- invalid rating
- resume
- backups
- atomic save
- exact substring offset
- duplicate quote behavior documented
- no rating recommendation

After software is built, STOP and tell the human to run:

`python scripts/review_evidence_pedagogically.py`

Do not cross Human Gate 2 automatically.

---

# H. AFTER HUMAN GATE 2 IS COMPLETE

When every evidence row has a valid 0/1/2 human rating:

1. Run:
   `python scripts/18_summarize_evidence_review.py`

2. Fix `scripts/19_analyze_errors.py` so it ACTUALLY reads:
   `data/reviews/evidence_review.csv`

Current error-analysis module supports `exact_but_weak_evidence`, but the current script does not pass pedagogical evidence review data into classification.

Implement:
- group evidence review by fragment + competency
- only activate pedagogical evidence error classes when all required ratings are complete
- pass evidence reviews to `classify_fragment()`
- regenerate error table
- regenerate error summary

Add:
- `primary_category_counts`
- explicit note that category flag counts overlap and are NOT a partition of fragments

Create:
`reports/tables/error_examples.csv`

Required real examples:
- >=3 exact correct predictions
- >=3 incorrect predictions
- ambiguous case(s)
- retrieval failure
- overprediction examples
- parent-child redundancy examples
- exact-but-weak-evidence examples if any

Every example must include real:
- fragment ID
- fragment text excerpt
- reference labels
- BM25 Top-5
- Gemini labels
- evidence quote(s)
- evidence rating if available

No invented examples.

---

# I. RESOURCE-LEVEL EVALUATION

The earlier methodological plan included fragment-level AND resource-level evaluation.

Implement a clearly documented derived resource-level reference:

- For a Page resource:
  union the finalized fragment reference labels belonging to that Page.
- For each Quiz question:
  it is already an independent research resource, so use its fragment reference directly.

Do NOT use activity-level Moodle quiz labels as question-level gold.

Create:
- `src/moodle_competency/resource_evaluation.py`
- `scripts/22_evaluate_resource_level.py`
- tests

Metrics:
- resource-level micro precision / recall / F1
- resource-level macro precision / recall / F1
- exact-set / subset accuracy
- average label-count error
- per-resource table
- per-competency table

Write:
- `reports/metrics/resource_level_metrics.json`
- `reports/tables/resource_level_evaluation.csv`

Document that this resource-level reference is DERIVED from the human-reviewed fragment reference.

---

# J. MINIMAL GRAPH / HIERARCHY EXPERIMENT — AFTER CORE EVALUATION

The current error analysis shows 10 parent-child redundancies.
This is the clearest remaining graph issue.

Implement the supervisor-approved MINIMAL graph layer only.

Create:
- `src/moodle_competency/graph_checks.py`
- `scripts/23_run_graph_checks.py`
- `tests/test_graph_checks.py`

Use only hierarchy actually present in the 13-competency framework.

Do NOT invent prerequisites or related-to relations that are absent.

Required warnings:
- `parent_child_redundancy`
- `invalid_hierarchy_reference`
- `granularity_conflict`

Original predictions must remain unchanged.

Outputs:
- `data/processed/graph_warnings.jsonl`
- `reports/metrics/graph_check_summary.json`
- `reports/tables/graph_warnings.csv`

Also implement a SEPARATE, non-destructive ablation mode:

`--simulate-child-preference`

Rule:
When a parent and direct child are both predicted for the same fragment, produce a separate simulated prediction set that removes the parent ONLY for the ablation output.

Do NOT overwrite Gemini predictions.

Store:
- `data/experiments/graph_child_preference_predictions.jsonl`
- `reports/metrics/graph_child_preference_metrics.json`
- `reports/tables/graph_ablation_comparison.csv`

Evaluate original vs simulated prediction sets against the same reference.

Clearly label this:
`POST-HOC MINIMAL GRAPH ABLATION`

Do not call it part of the original Gemini run.

Tests:
- parent + child
- parent alone
- child alone
- two unrelated children
- invalid parent ID
- no mutation of original input
- deterministic warnings
- separate ablation output

Do not implement graph visualization or recommendation.

---

# K. OPTIONAL UNCONSTRAINED GEMINI EXPERIMENT

This phase is OPTIONAL and must NOT start without explicit researcher authorization because it spends API quota.

Purpose:
directly test the effect of candidate restriction.

Create software first without live calls:

- `src/moodle_competency/unconstrained_llm.py`
- `scripts/24_build_unconstrained_tasks.py`
- `scripts/25_run_unconstrained_gemini.py`
- `scripts/26_evaluate_unconstrained_gemini.py`
- tests with mocked responses

Keep IDENTICAL to constrained experiment:
- same model
- same temperature 0
- same instructions
- same output schema
- same evidence requirement
- same max selections = 3
- same fragment corpus
- same competency descriptions
- same validator semantics

ONLY difference:
candidate space = all 13 competencies instead of BM25 Top-5.

Store separately:
- `data/experiments/unconstrained_llm_tasks.jsonl`
- `data/experiments/unconstrained_gemini_responses.jsonl`
- `data/experiments/unconstrained_gemini_validated.jsonl`
- separate manifests
- separate metrics

Never overwrite constrained outputs.

Do not make a live API call until researcher explicitly says:
`Run the optional unconstrained all-13 Gemini experiment.`

Comparison later:
- BM25 Top-1
- BM25 Top-5 + constrained Gemini
- all-13 unconstrained Gemini
- optional graph-ablation result

---

# L. TEACHER VALIDATION INTERFACE — REQUIRED CORE DELIVERABLE

Build the external teacher-facing validation interface.

Prefer Streamlit.

Create:
- `app/Home.py`
- `app/pages/1_Resource_to_Competencies.py`
- `app/pages/2_Teacher_Review.py`
- `app/pages/3_Competency_to_Resources.py`
- `app/pages/4_Evidence_Review.py`
- `app/pages/5_Review_Progress.py`
- optional `app/pages/6_Experiment_Results.py`
- `docs/TEACHER_INTERFACE_GUIDE.md`

Reuse and extend:
`src/moodle_competency/teacher_reviews.py`

Do NOT write to Moodle.
Do NOT build a PHP plugin.

## View 1 — Course / resource browser
Select:
- MVP-SW
- MVP-DATA

Show resources and fragments.

## View 2 — Resource → competencies
For each prediction show:
- resource
- fragment
- predicted competency
- competency description
- confidence
- BM25 rank when available
- exact evidence
- hierarchy context
- graph warning if available
- current teacher decision

## View 3 — Teacher review
Actions:
- ACCEPT
- REJECT
- MODIFY
- optionally ADD a missing competency
- comment
- evidence relevance 0/1/2

Teacher must explicitly save.

Persist in:
`data/reviews/teacher_reviews.csv`

Never overwrite:
- human reference
- Gemini output
- evidence-review reference
- source datasets

Validate:
- modified IDs are valid
- no duplicated review IDs
- reviewer required
- review timestamp required
- atomic writes
- backups

## View 4 — Competency → resources
Select any of 13 competencies.

Show:
- matching resources
- course
- type
- title
- supporting fragments
- evidence
- confidence
- support count
- teacher status

This is the supervisor-requested inverse direction.

## View 5 — Progress
Show:
- total reviewable resource-competency mappings
- pending
- accepted
- rejected
- modified
- added
- reviewed %
- per-course progress
- per-resource-type progress

## View 6 — Results
Read-only measured results:
- BM25 metrics
- constrained Gemini metrics
- evidence summary when complete
- graph warning summary when available

Do not let the UI alter metric files.

---

# M. TEACHER-CENTRED EVIDENCE USEFULNESS PILOT

The project question about evidence usefulness is not fully answered by exact-substring validity alone.

Implement a SMALL exploratory review mode.

Create:
- `src/moodle_competency/teacher_study.py`
- `scripts/27_prepare_teacher_study.py`
- app page or standalone Streamlit page
- tests

Use a small stratified sample from:
- both courses
- Pages and Quiz questions
- correct and incorrect model cases
- parent-child redundancy cases if possible

Two display conditions:
A. competency suggestion WITHOUT evidence shown initially
B. competency suggestion WITH evidence shown

Record:
- case ID
- condition
- reviewer
- decision
- confidence rating (e.g. 1–5)
- start timestamp
- end timestamp
- elapsed seconds
- comment
- whether evidence was opened/shown

Do not fabricate teacher data.

Randomization must be reproducible with a fixed seed and saved manifest.

This is exploratory, not a claim about all Moodle teachers.

After real review, summarize:
- median review time by condition
- acceptance / edit / rejection by condition
- confidence by condition
- sample size

If only the researcher performs the pilot, label it:
`researcher pilot`
not `teacher study`.

If a supervisor/teacher performs it, record that role accurately.

---

# N. FINAL TEACHER REVIEW SUMMARY

After real teacher/researcher decisions exist:

Create:
- `scripts/28_summarize_teacher_reviews.py`
- `reports/metrics/teacher_review_summary.json`
- `reports/tables/teacher_review_summary.csv`

Report:
- reviewed
- pending
- accepted
- rejected
- modified
- added
- acceptance rate among reviewed
- edit rate
- rejection rate
- evidence-relevance distribution
- per-course counts
- per-resource-type counts

Do not report rates if no real decisions exist.

---

# O. COVERAGE / NAVIGATION VIEW — KEEP SMALL

The old proposal mentioned coverage/navigation, but the reduced MVP should not become a large analytics product.

Implement only a minimal validated mapping view AFTER teacher decisions:

Create:
- `src/moodle_competency/coverage.py`
- app section or page

Show:
- competency → validated resources
- resource → validated competencies
- simple count of validated mappings by course / section / competency
- unmapped resources
- competencies with zero validated resources

Do NOT implement recommendations, learning paths, taught-vs-assessed analytics, or a large dashboard unless explicitly reopened by supervisors.

---

# P. FINAL REPORT PACKAGE

After Human Gate 2 and teacher review are complete, create/update:

- `reports/FINAL_EXPERIMENTAL_RESULTS.md`
- `reports/FINAL_ERROR_ANALYSIS.md`
- `reports/FINAL_TEACHER_REVIEW.md`
- `reports/FINAL_LIMITATIONS.md`
- `reports/SUPERVISOR_RESULTS_SUMMARY.md`
- `docs/CURRENT_STATUS.md`
- `docs/EVALUATION.md`
- `docs/PIPELINE.md`
- `docs/DATA_DICTIONARY.md`
- `README.md`

Final report must include:

## 1. Problem / scope
Reduced MVP and why broader features were deferred.

## 2. Moodle setup
- version
- courses
- Pages
- Quizzes
- REST
- SQL fallback

## 3. Competency framework
- 13 GI competencies
- hierarchy
- Moodle import path
- normalized Python representation

## 4. Data
- 20 resources
- 35 fragments
- type distribution
- reference-label distribution

## 5. BM25
- Recall@1/@3/@5
- Hit@1/@3/@5
- MRR
- Top-1 P/R/F1

## 6. Constrained Gemini
- micro / macro P/R/F1
- exact-set match
- coverage
- abstention
- avg labels

## 7. Interpretation
State:
- constrained Gemini improves recall/F1 relative to BM25 Top-1
- precision is slightly lower
- only reference miss is retrieval failure
- LLM misses no retrievable gold labels
- overprediction is dominant
- parent-child redundancy is frequent
- abstention cannot be fairly judged because reference set has no NONE cases

## 8. Evidence
- exact-substring rate
- offset validity
- 0/1/2 pedagogical review

## 9. Error analysis
- retrieval vs LLM
- overprediction
- parent/child
- ambiguous reference
- evidence quality

## 10. Resource-level results
derived resource reference clearly explained.

## 11. Function A
resource → competency examples

## 12. Function B
competency → resource examples

## 13. Teacher review
only real data

## 14. Optional graph ablation
if actually run

## 15. Optional unconstrained comparison
if actually run

## 16. Limitations
At minimum:
- small controlled synthetic corpus
- single researcher reference
- no measured inter-annotator agreement
- no reference NONE fragments
- Pages + Quiz questions only
- local Moodle
- top-level parent labels absent from reference support
- external Gemini dependency
- SQL Quiz fallback is local-development specific
- teacher usefulness evidence may have small sample

## 17. Deferred future work
list deferred items explicitly.

Never present old proposal goals as already completed unless they truly are.

---

# Q. SUPERVISOR DEMO PACKAGE

Create:
- `docs/SUPERVISOR_DEMO.md`
- `reports/SUPERVISOR_DEMO_CHECKLIST.md`
- `reports/RESULTS_ONE_PAGE.md`

10–15 minute sequence:

1. Research problem
2. Reduced scope
3. Moodle competency hierarchy
4. MVP-SW / MVP-DATA
5. Page example
6. Quiz-question example
7. extraction / normalization
8. fragment
9. BM25 Top-5
10. constrained Gemini
11. exact evidence
12. human-reviewed reference
13. BM25 Recall@1/3/5
14. BM25 Top-1 P/R/F1
15. Gemini micro/macro metrics
16. main interpretation
17. retrieval failure example
18. parent-child overprediction example
19. evidence-review result
20. Function A
21. Function B
22. teacher interface
23. optional graph ablation if available
24. limitations
25. future work

For every demo step:
- exact file / screen to open
- what to say
- likely supervisor question
- concise answer

Screenshot checklist:
- Moodle framework hierarchy
- course competency selection
- Page
- Quiz
- BM25 example
- Gemini evidence
- teacher review interface
- competency → resource page
- progress page

---

# R. FINAL VALIDATION / ACCEPTANCE TEST

Before declaring the core project complete, run:

1. `python scripts/12_validate_manual_annotations.py --mode final`
2. evidence-review validator
3. teacher-review validator
4. graph-output validator if graph phase run
5. `python -m pytest -q`
6. `python -m compileall -q src scripts tests`

Then verify:

- 35 reference rows complete
- 35 Gemini responses valid
- 20 resource predictions
- 13 competency-index rows
- metric JSON files parse
- evidence review complete if Gate 2 closed
- teacher review files preserve provenance
- no secret in generated reports
- protected experiment hashes unchanged unless a documented new version intentionally replaces a derived output
- optional outputs live in `data/experiments/` and do not overwrite core data

Create:
`reports/FINAL_VALIDATION_REPORT.md`

---

# S. FINAL STATUS CLASSIFICATION

Use only:

- COMPLETE
- WAITING_FOR_HUMAN
- OPTIONAL
- DEFERRED
- BLOCKED

Do not mark the complete project COMPLETE while:
- pedagogical evidence ratings are missing
- teacher interface is untested
- final report / demo package is missing

Optional unconstrained Gemini and optional graph ablation do not block the reduced MVP unless supervisors explicitly require them.

---

# T. EXECUTION ORDER FROM THE CURRENT STATE

Proceed in this order:

1. Repository audit + small metric/reproducibility fixes
2. Build Human Gate 2 evidence-rating helper
3. STOP for human evidence ratings
4. Summarize evidence + integrate evidence into error analysis
5. Resource-level evaluation
6. Minimal graph hierarchy warnings + separate ablation
7. Build teacher validation UI
8. STOP for real human teacher/researcher review
9. Summarize teacher review
10. Minimal validated coverage/navigation view
11. Optional unconstrained Gemini SOFTWARE ONLY
12. Ask authorization before any live optional Gemini call
13. Final reports
14. Supervisor demo
15. Final validation report
16. Optional Git/GitHub cleanup only after science is finished

---

# U. TESTING REQUIREMENTS

Every new module must have tests.

Minimum new test files:
- `tests/test_evidence_review_session.py`
- `tests/test_resource_evaluation.py`
- `tests/test_graph_checks.py`
- `tests/test_teacher_study.py`
- `tests/test_teacher_review_summary.py`
- `tests/test_coverage.py`
- `tests/test_unconstrained_llm.py` if implemented

Tests must use temporary fixtures.
Never mutate real experimental data.

Add regression tests for the current measured core metrics so accidental code changes cannot silently alter them.

Regression tests may load small frozen fixture copies or assert hashes/configuration, but do not make tests depend on live API calls.

No test may call Gemini live.

---

# V. FINAL RESPONSE FORMAT AFTER EACH EXECUTION PHASE

Report:

1. files created
2. files modified
3. protected files unchanged
4. test result
5. compile result
6. output counts
7. measured results created
8. limitations
9. human action required
10. exact next command

Never fabricate human judgments.
Never fabricate teacher decisions.
Never fabricate optional experiment results.

Start now with Section E: FULL REPOSITORY AUDIT.
Do not skip directly to UI.
