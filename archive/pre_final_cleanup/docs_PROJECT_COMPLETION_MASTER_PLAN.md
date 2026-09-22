# Moodle Competency MVP — Master Completion Plan

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Workspace:** `~/projects/moodle_competency_mvp`  
**Researcher:** Wail Ouaret, ENSIA  
**Supervisors:** Marie-Hélène Abel and Le Ngoc Luyen (UTC / Heudiasyc / CNRS)

This is an existing research project. Reuse the current implementation. Preserve existing experimental evidence. Do not rebuild completed stages.

Reload this file at the start of every implementation session. Follow it exactly. Respect every human gate and stop condition.

---

## Supervisor-approved functional objectives

### Objective A — Resource → competencies

For every Moodle Page, Quiz question, or pedagogical fragment:

1. extract content;
2. normalize content;
3. fragment content;
4. retrieve BM25 Top-5 competency candidates;
5. let the constrained LLM choose zero, one, or several competencies only from those candidates;
6. require an exact textual evidence quote for every selected competency;
7. validate output;
8. later support teacher validation.

### Objective B — Competency → resources

For any of the 13 UTC GI competencies, show:

- matching resources;
- matching fragments;
- exact evidence;
- confidence;
- teacher validation decision.

This is an inverse index over Objective A, not a second AI model.

Keep Quiz questions as independent research resources. Do not collapse 12 questions into 2 Quiz objects for the main evaluation.

---

## Research questions

Primary:

- **RQ1:** To what extent can Moodle resources and activities be automatically aligned with a competency framework?
- **RQ2:** Do exact textual evidence spans help teachers verify alignment suggestions?

Secondary / optional:

- **RQ3.1:** Does BM25 candidate preselection improve LLM alignment quality?
- **RQ3.2:** Do minimal graph constraints reduce incoherent or redundant predictions?

Do not reintroduce the older larger scope.

---

## Strict research-integrity rules

Never:

- fabricate metrics;
- fabricate human annotations;
- fill human gold automatically;
- use BM25 / Gemini / activity-level labels to generate human gold;
- alter human gold semantic choices automatically;
- invent pedagogical evidence ratings;
- invent teacher accept / reject / modify decisions;
- delete or rewrite valid Gemini checkpoints;
- use `--restart` for the Gemini batch;
- silently change the 13-competency framework;
- expose `.env`, API keys, tokens, passwords, or private Moodle access keys;
- modify Moodle core;
- add ROME 4.0, PDFs, videos, OCR, recommendation, curriculum analytics, or a native Moodle plugin to the current core MVP;
- report preliminary or partial values as final results.

When data is unavailable, say it is pending.

---

## Human gates

### Human Gate 1 — Independent gold annotation

The researcher manually annotates all 35 fragments. Cursor must not decide these labels.

```bash
python scripts/manual_annotate_fragments.py
```

When all 35 are done:

```bash
python scripts/12_validate_manual_annotations.py --mode final
```

Gate opens only when 35/35 human decisions exist and final validation PASSES.

No final BM25 / LLM evaluation may be reported before this gate opens.

### Human Gate 2 — Pedagogical evidence relevance

Mechanical exact-substring validity is automatic.

Pedagogical relevance is human:

- `0` = evidence does not justify the competency
- `1` = partially relevant / ambiguous
- `2` = clearly supports the competency

Cursor may prepare and validate the review sheet, but not fill the ratings.

### Human Gate 3 — Teacher review

The UI may record accept, reject, modify, comment, and evidence relevance.

Cursor may implement the UI and persistence. Real teacher decisions must come from a human.

---

## Gemini authorization gate

Current constrained Gemini status at last count:

- 35 total tasks
- 23 valid saved responses
- 12 missing

Do not make live Gemini API calls until the researcher explicitly says something equivalent to:

> Resume the 12 missing Gemini tasks. Keep the 23 valid checkpoints. Do not use `--restart`.

Before authorization, inspect code, improve retry logic with tests/mocks, and prepare the runner, but do not make live API calls.

---

## Priority order

1. Human gold (Gate 1)
2. Complete constrained Gemini (after API authorization)
3. Fragment → resource aggregation
4. Competency → resources inverse index
5. BM25 evaluation
6. Constrained LLM evaluation
7. Evidence evaluation
8. Error analysis
9. Teacher validation interface
10. Optional unconstrained LLM
11. Optional graph checks
12. Reproducibility / documentation
13. Final report outputs
14. Supervisor demo

Main evaluation has priority over optional extensions.

---

## Phase 2 — Finish constrained Gemini

After explicit authorization, inspect:

- `src/moodle_competency/gemini_alignment.py`
- `scripts/10_run_gemini_alignments.py`

Preserve the existing 23 checkpoints. Never use `--restart`.

Improve 429 handling if necessary:

- parse provider retry duration when present;
- add a small safety margin;
- use exponential fallback only when provider delay is absent;
- checkpoint every success immediately;
- never resend already valid tasks;
- stop cleanly when daily quota is exhausted;
- keep error logs;
- report remaining IDs.

Keep the experiment unchanged: same Gemini model, temperature 0, BM25 Top-5 restriction, max selections 3, same prompt semantics, same JSON schema, exact-evidence requirement.

Target: 35 tasks, 35 valid responses, 0 missing, 0 invalid accepted.

If quota blocks completion, preserve progress and report exact missing task IDs.

---

## Phase 3 — Fragment → resource aggregation

Create:

- `src/moodle_competency/aggregation.py`
- `scripts/13_aggregate_predictions.py`

Outputs:

- `data/processed/resource_predictions.jsonl`
- `data/processed/resource_predictions_manifest.json`

For each resource + competency: deduplicate competency IDs; preserve supporting fragment IDs, evidence, and fragment-level confidences; calculate `max_confidence`, `mean_confidence`, `support_count`.

Page fragments aggregate to their Page. Quiz questions remain independent research resources.

---

## Phase 4 — Competency → resources inverse index

Create:

- `src/moodle_competency/inverse_index.py`
- `scripts/14_build_competency_resource_index.py`

Output: `data/processed/competency_resource_index.jsonl`

Include all 13 competencies, including zero-match competencies. No model call.

---

## Phase 5 — BM25 evaluation

Precondition: Human Gate 1 is open.

Use gold annotations and `data/interim/bm25_candidates.jsonl`.

Create/reuse `src/moodle_competency/metrics.py` and `scripts/15_evaluate_bm25.py`.

Required: Recall@1, Recall@3, Recall@5, BM25 Top-1 precision / recall / F1.

Also report when appropriate: Hit@1/3/5, MRR.

Keep label-level Recall@K separate from fragment-level Hit@K.

Recommended label-level definition:

`Recall@K = gold competency labels present in Top-K / total gold competency labels`

Document handling of no-competency gold rows, multi-label gold rows, parent/child labels, and micro vs macro aggregation.

Do not hard-code real expected results. Add hand-calculated metric tests.

---

## Phase 6 — Constrained LLM evaluation

Preconditions: Human Gate 1 open; ideally 35/35 Gemini responses valid.

Required: micro/macro precision, recall, F1; exact-set match; coverage; abstention rate; average predicted labels per fragment.

Coverage = fraction of fragments with at least one selected competency.  
Abstention = fraction of fragments with no selected competency.

Keep retrieval failure and LLM selection failure separate.

Comparison table must contain at least BM25 Top-1 and BM25 Top-5 + constrained Gemini.

Do not claim superiority beyond the measured data.

---

## Phase 7 — Evidence evaluation

Create evidence-review module and scripts. Output `data/reviews/evidence_review.csv`.

Compute `mechanically_valid` automatically. Leave `pedagogical_rating` blank for the human.

Never merge mechanical validity and pedagogical relevance into one number.

---

## Phase 8 — Error analysis

Classify:

- `retrieval_failure` = gold competency absent from BM25 Top-5
- `llm_wrong_selection` / `llm_missed_gold_label` = gold competency in Top-5 but LLM did not select it, or LLM selected a non-gold label
- `overprediction` / `underprediction`
- `incorrect_abstention`
- `parent_child_redundancy`
- `ambiguous_gold`
- `exact_but_weak_evidence`
- `correct_prediction`
- `correct_abstention`

Prepare at least 3 correct, 3 incorrect, and 2 ambiguous examples. Every example must be traceable to stored data.

---

## Phase 9 — Minimal teacher validation web app

After the main evaluation. Prefer Streamlit. Keep it external to Moodle. Do not build a PHP plugin.

Store reviews in `data/reviews/teacher_reviews.csv`. Never overwrite human gold, Gemini predictions, or source datasets.

Human Gate 3 requires real human use; automated fixtures are not human results.

---

## Phase 10 — Optional unconstrained LLM

Run only after the main constrained evaluation and only with explicit approval/quota.

Same model, temperature, instructions, evidence rules, max selections, schema. Only the candidate space changes from Top-5 to all 13.

Store results separately. Never overwrite constrained outputs.

---

## Phase 11 — Minimal graph checks

After primary evaluation. Non-destructive warnings only. Do not silently modify predictions. Do not build graph visualization, recommendation, or learning paths.

---

## Phase 12 — Reproducibility and documentation

Create/update README, `.env.example`, SETUP, PIPELINE, ANNOTATION_GUIDE, EVALUATION, TEACHER_INTERFACE_GUIDE, SUPERVISOR_DEMO, DATA_DICTIONARY, this file, and CURRENT_STATUS.

`.env.example` may include Gemini placeholders. Never expose secrets.

Git is not required to finish the experiment. Record a git commit hash only if a repository exists.

---

## Phase 13 — Final report outputs

Generate machine-readable result tables first. Prepare report-ready material only from measured values. Label sections COMPLETE / IN PROGRESS / OPTIONAL / DEFERRED.

---

## Phase 14 — Supervisor demo

Create `docs/SUPERVISOR_DEMO.md` covering Moodle hierarchy, both courses, Page and Quiz examples, extraction, BM25, constrained LLM, evidence, gold, metrics, Function A, Function B, teacher interface, limitations.

---

## Deferred work

Do not implement now unless supervisors request it later:

- ROME 4.0
- PDFs / slides / audio / video / OCR
- native Moodle PHP plugin
- LTI integration
- recommendation engine / learning paths
- full graph navigation / curriculum analytics
- teaches / assesses / supports / mentions classification
- fine-tuning
- institution-wide deployment

---

## Protected files

Do not modify unless a later phase explicitly requires it:

- `data/processed/resources.jsonl`
- `data/processed/fragments.jsonl`
- `data/processed/competencies.jsonl`
- `data/interim/bm25_candidates.jsonl`
- `data/interim/llm_tasks.jsonl`
- `data/interim/gemini_responses.jsonl`
- `data/interim/gemini_validated.jsonl`
- `data/gold/manual_moodle_links.csv`
- filled human cells in `data/gold/manual_fragment_annotations.csv`

`manual_moodle_links.csv` is activity-level Moodle reference data, not fragment-level human gold.

---

## Execution protocol

At the start of each phase: inspect existing implementation; reuse current code; state exact files to create/modify; verify protected data will not be overwritten.

At the end of every phase:

1. run phase-specific validation;
2. `python -m pytest -q`
3. `python -m compileall -q src scripts tests`
4. report output counts, files created/modified, assumptions, blockers;
5. update `docs/CURRENT_STATUS.md`;
6. stop if the next phase needs a human gate or live API authorization.

Never silently cross a human gate.

---

## Work allowed while the researcher annotates

Safe software-only work, if explicitly approved, that does not pretend incomplete gold is final:

- aggregation module / tests;
- inverse-index module / tests;
- metrics library / hand-calculated fixture tests;
- BM25 and constrained-LLM evaluation script code;
- evidence-review generator / validator;
- error-analysis code using fixtures;
- teacher-review storage layer;
- Streamlit interface using controlled fixture/demo data;
- documentation, data dictionary, reproducibility utilities.

Do not report final metrics from incomplete gold. Do not fabricate evidence ratings or teacher decisions. Do not make live Gemini calls without authorization.

---

## Stop conditions

Stop and ask for human action when:

1. gold is incomplete but final evaluation is requested;
2. a live Gemini call is needed without authorization;
3. pedagogical evidence ratings are needed;
4. real teacher review decisions are needed;
5. changing historical data would be required;
6. a scientific-protocol decision is ambiguous.

---

## Current next action

Human researcher:

```bash
python scripts/manual_annotate_fragments.py
```

After 35/35:

```bash
python scripts/12_validate_manual_annotations.py --mode final
```

Meanwhile, implement safe software-only phases only after explicit approval.

Do not call Gemini until explicit authorization.

---

## Core acceptance checklist

The supervisor-approved core MVP is complete when:

- 35/35 human gold annotations complete and final validator PASSES;
- 35/35 constrained Gemini responses valid, or a clearly documented unavoidable quota limitation remains;
- fragment → resource aggregation exists;
- competency → resources inverse index exists;
- BM25 Recall@1/3/5 reported;
- BM25 Top-1 P/R/F1 reported;
- constrained LLM micro/macro metrics reported;
- coverage and abstention reported;
- mechanical evidence validity reported;
- human pedagogical evidence evaluation completed or explicitly pending;
- error analysis completed;
- correct / incorrect / ambiguous examples prepared;
- minimal teacher interface works;
- resource → competencies demo works;
- competency → resources demo works;
- all tests pass;
- compile checks pass;
- reproducibility documentation exists;
- no secrets are exposed;
- final report material exists;
- supervisor demo guide exists.

Optional items that do not block core completion:

- unconstrained 13-competency LLM comparison;
- minimal graph warnings.
