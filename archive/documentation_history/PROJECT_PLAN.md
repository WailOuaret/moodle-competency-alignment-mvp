# Moodle Resource-to-Competency Alignment MVP — Living Plan

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Researcher:** Wail Ouaret, ENSIA  
**Supervision:** Marie-Hélène Abel and Le Ngoc Luyen, UTC / Heudiasyc  
**Workspace:** `~/projects/moodle_competency_mvp`  
**This file:** reload at the start of every implementation session. Update the progress boxes after each phase. Do not treat historical counts as current until the repository is re-counted.

**Last progress update:** 2026-09-18 after Phase 1 (blank blinded annotation template).

---

## Honest answer: can the coding agent complete this alone?

**Software, tests, and machine-readable reports: yes.**  
The remaining pipeline is well specified, the repository already contains the core extraction/BM25/LLM-task code, and later stages (aggregation, inverse index, metrics, error analysis, Streamlit review UI, docs) are implementable in this codebase without rebuilding it.

**The whole research deliverable: no, not without Wail.**  
These parts cannot be invented by the agent:

| Task | Who must do it | Why |
|---|---|---|
| Fill `data/gold/manual_fragment_annotations.csv` | Wail (then supervisors review ambiguous cases) | Gold must be independent and blinded. Inventing labels would invalidate evaluation. |
| Approve remaining Gemini API calls | Wail | Quota, cost, and research-integrity rule: no automatic external API calls without approval. |
| Pedagogical evidence ratings 0/1/2 | Wail / teacher | Mechanical exact-quote checks are automatic; pedagogical relevance is human. |
| Teacher accept/reject/modify in the review UI | Wail / teacher | That is the RQ2 human study, not a model output. |
| Moodle production / LTI launch from a live UTC course | Out of current MVP | Supervisors asked for an external Python app first. Native plugin and LTI are later. |
| GitHub remote, commits, pushes | Only if Wail asks | The workspace is currently **not** a git repository. |

**Testing coverage the agent can do**

- Unit tests and `compileall` after every phase (already the project policy).
- Template/final annotation validators.
- Metric unit tests on fixtures, then real metrics only after gold exists.
- Streamlit flow checks (browser or local run) once that phase is approved.
- Dataset count and schema validation.

**Testing the agent cannot honestly claim as complete until humans finish**

- End-to-end evaluation numbers (need filled gold).
- All 35 Gemini predictions (need quota + explicit approval; 12 remain).
- Pedagogical evidence quality (need human 0/1/2 ratings).
- Teacher-usability of evidence (RQ2; needs a person using the UI).

**Practical conclusion:** the agent can take the project from the current stop point through a supervisor-ready prototype **if Wail annotates the 35 fragments and approves the remaining Gemini run**. Those two human gates are on the critical path for the next meeting.

---

## Research questions (supervisor-reduced)

Keep these. Do not expand the scope.

- **RQ1.** To what extent can Moodle resources/activities be automatically aligned with a competency framework?
- **RQ2.** Do exact textual evidence quotes help teachers verify alignment suggestions more easily?

Experimental sub-questions (after main evaluation):

- **RQ3.1.** Does BM25 candidate preselection improve constrained-LLM alignment versus using all 13 competencies?
- **RQ3.2.** Do minimal graph warnings reduce redundant or hierarchically inconsistent predictions?

Not in this MVP: relation types `teaches` / `assesses` / `supports` / `mentions`; recommendation; learning paths; curriculum dashboard; native Moodle PHP plugin; ROME 4.0; PDFs/video/OCR; LLM fine-tuning.

---

## Two prototype functions (frozen)

### Function A — Resource → competencies

For each Moodle Page, Quiz question, or fragment:

content → normalization → fragmentation → BM25 Top-5 → constrained LLM → exact evidence → human validation

Question answered: *which UTC GI competencies does this resource/fragment correspond to?*

### Function B — Competency → resources

Inverse index over Function A. **Not a second model.**

For each of the 13 GI competencies, show:

- matching resources
- matching fragments
- evidence quotes
- confidence
- teacher validation decision

Keep Quiz questions as independent resources. Do not collapse all questions into one Quiz.

---

## Supervisor constraints that must not drift

From Ngoc Luyen Le (scope letter, then progress-report reply):

1. Local Moodle; two test courses; ~10–20 GI competencies; Pages + Quizzes only.
2. BM25 first, then LLM **only among those candidates**.
3. Evidence = exact contiguous excerpt from the fragment.
4. Manual reference corpus is independent of model predictions.
5. Activity-level Moodle mappings ≠ fragment gold. A Page competency must not be copied onto every fragment.
6. Gold annotation and remaining LLM calls may run **in parallel**.
7. Keep already validated Gemini checkpoints. Do not restart them.
8. Mechanical evidence validity is automatic; pedagogical relevance is human (0 unsupported / 1 partial / 2 clearly supports).
9. Teacher UI is a **minimal external Python web app**, later optionally LTI; native PHP plugin is later.
10. Graph checks are a small post-evaluation warning layer, not a visual graph navigator.
11. Next meeting wants: remaining LLM answers if quota allows; manual corpus; Recall@1/3/5; BM25 vs BM25+LLM; precision/recall/F1/coverage/abstention; evidence evaluation; a few correct/incorrect examples; short error analysis; Function A and B demo; optional simple validation table; report update.

---

## Current verified repository state (2026-09-18)

Recount files before assuming these still hold.

| Item | Count | Status |
|---|---:|---|
| Python | 3.12.3 | working venv |
| Package | moodle-competency-mvp 0.1.0 | installed editable |
| Moodle | 5.2.1+ local | recorded in site info |
| Courses | MVP-SW, MVP-DATA | present |
| Pages | 8 | extracted |
| Quizzes | 2 | extracted |
| Quiz questions | 12 | SQL extract |
| Selected GI competencies | 13 (3 parents + 10 children) | processed |
| Normalized resources | 20 (8 pages + 12 questions) | processed |
| Fragments | 35 (23 page_chunk + 12 quiz_question) | processed |
| BM25 Top-5 sets | 35 | complete |
| Constrained LLM tasks | 35 | complete |
| Gemini validated checkpoints | **23 / 23 valid** | preserve |
| Gemini remaining | **12** | quota 429 |
| Unit tests | **56 passed** | after Phase 1 |
| Git at project root | **none** | do not `git init` unless asked |
| Fragment gold | blank template, 0 labels filled | **Wail must annotate** |

Gemini remaining fragment IDs:

`page:6#f002`, `page:6#f003`, `page:7#f001`, `page:7#f002`, `page:7#f003`, `page:8#f001`, `page:8#f002`, `page:8#f003`, `quiz_question:2:8#f001`, `quiz_question:2:9#f001`, `quiz_question:2:10#f001`, `quiz_question:2:12#f001`

Note vs older supervisor wording (“keep the 21 validated responses”): the repository now has **23** valid checkpoints. Never use `--restart`.

---

## Progress tracker

Legend: `[x]` done · `[~]` in progress / blocked on human · `[ ]` not started · `D` deferred on purpose

### A. Environment and Moodle corpus

- [x] Local Moodle 5.2 development instance (Windows 11 + WSL2 + Docker + PostgreSQL 16)
- [x] Two courses: MVP-SW, MVP-DATA
- [x] Import UTC GI subset (13 competencies)
- [x] Manual Moodle activity competency mappings (verified; 20 activity links)
- [x] API accessibility matrix
- [x] REST extraction (course / Page / Quiz metadata)
- [x] Read-only SQL extraction of full Quiz question content
- [x] Normalize 20 resources
- [x] Fragment into 35 pedagogical units
- [x] Normalize 13 competency profiles

### B. Automatic alignment pipeline (Function A, model side)

- [x] BM25 Top-5 for all 35 fragments
- [x] Constrained LLM task builder (JSON schema, max 3 selections, abstention allowed, exact evidence)
- [x] Local validator (candidate IDs + exact substring evidence)
- [x] Gemini pilot
- [x] Checkpointed Gemini batch runner
- [~] Finish remaining 12 Gemini tasks **without deleting 23 checkpoints** — needs Wail approval + quota
- [ ] Improve 429 handling (parse retry duration, safety margin, stop on daily quota) — only with Phase 2 approval

### C. Independent manual reference (human gold)

- [x] Phase 1 software: `annotation.py`, scripts `11`/`12`, tests, `docs/ANNOTATION_GUIDE.md`
- [x] Blank `data/gold/manual_fragment_annotations.csv` (35 rows, labels empty)
- [x] `data/gold/annotation_competency_catalogue.csv` (13 competencies, no BM25/Gemini)
- [x] Template validation PASSED
- [~] **Wail fills the 35 rows blindly** (do not open BM25/Gemini files)
- [ ] Supervisors review ambiguous / disagreement cases
- [ ] Final validation: `python scripts/12_validate_manual_annotations.py --mode final`
- [x] Keep activity-level file `data/gold/manual_moodle_links.csv` separate from fragment gold

### D. Function A aggregation and Function B inverse index

- [ ] Fragment predictions → `data/processed/resource_predictions.jsonl` (max/mean confidence, supporting fragments, evidence)
- [ ] Inverse index `data/processed/competency_resource_index.jsonl` covering all 13 competencies, including zeros

### E. Evaluation (needs completed gold; Gemini complete for the LLM half)

- [ ] BM25 Recall@1, Recall@3, Recall@5
- [ ] BM25 Top-1: micro/macro precision, recall, F1; exact match where appropriate
- [ ] Optional retrieval extras: Hit@k, MRR
- [ ] Constrained LLM vs gold: micro/macro P/R/F1, exact-set match, coverage, abstention, labels/fragment
- [ ] Save `reports/metrics/*.json` and `reports/tables/*.csv`
- [ ] Never fabricate metrics

### F. Evidence evaluation

- [ ] Automatic mechanical validity (exact quote in fragment)
- [ ] Blank human pedagogical review sheet `data/reviews/evidence_review.csv` (ratings 0/1/2 not auto-filled)
- [~] Human pedagogical ratings
- [ ] Aggregate evidence statistics after human review

### G. Error analysis and examples

- [ ] Classify: retrieval_failure, llm_wrong_selection, llm_missed_gold_label, over/underprediction, incorrect_abstention, parent_child_redundancy, ambiguous_gold, exact_but_weak_evidence, correct_prediction, correct_abstention
- [ ] `reports/tables/error_analysis.csv`
- [ ] ≥3 correct, ≥3 incorrect, ≥2 ambiguous examples

### H. Teacher review web app (RQ2) — after core evaluation unless Wail asks earlier

- [ ] Minimal Python web app (Streamlit unless repo already has another stack)
- [ ] Page 1: course selection
- [ ] Page 2: resource → competencies (accept / reject / modify / comment / evidence rating)
- [ ] Page 3: competency → resources
- [ ] Page 4: review progress
- [ ] Store teacher reviews **separately** from gold
- [ ] Tests for storage and transforms
- D Native Moodle PHP plugin
- D LTI embedding (recommended later, not required for next meeting)

### I. Optional after primary evaluation

- D Unconstrained LLM over all 13 competencies (same model, temperature, instructions, evidence rules, schema, max selections; only candidate space changes)
- D Minimal graph warnings: parent_child_redundancy, granularity_conflict, invalid_hierarchy_reference (flags only, do not rewrite predictions)

### J. Reproducibility and report support

- [ ] README.md, docs/SETUP.md, docs/PIPELINE.md, docs/EVALUATION.md, docs/SUPERVISOR_DEMO.md
- [x] docs/ANNOTATION_GUIDE.md
- [x] docs/PROJECT_PLAN.md (this file)
- [ ] `.env.example` placeholders including Gemini key names (no secrets)
- [ ] Reproducibility manifest (Python, deps, model id, config hashes, dataset counts, timestamp; git hash if a repo exists)
- [ ] Machine-readable tables for the final report
- [ ] No claims beyond measured results

---

## Critical path to the next supervisor meeting

Do these in order. Human steps are marked.

1. **Now (Wail):** annotate 35 fragments using `docs/ANNOTATION_GUIDE.md`. Parallel-OK with step 2.
2. **When Wail explicitly approves Phase 2:** resume Gemini for the 12 missing tasks only; never `--restart`; keep 23 checkpoints.
3. **After gold is filled (and preferably after Gemini is complete):** aggregation → inverse index → BM25 metrics → constrained-LLM metrics.
4. Mechanical evidence stats + blank pedagogical review sheet → Wail rates 0/1/2.
5. Error analysis + representative examples.
6. Minimal teacher UI for Function A and Function B demo.
7. Update the written progress report from measured files only.

Evaluation of BM25 can start as soon as fragment gold exists, even if 12 Gemini rows are still missing. LLM comparison needs those 12 rows or a documented incomplete-run protocol (do not hide missing predictions).

---

## Files the agent must never modify unless a later phase explicitly requires it

- `data/processed/resources.jsonl`
- `data/processed/fragments.jsonl`
- `data/processed/competencies.jsonl`
- `data/interim/bm25_candidates.jsonl`
- `data/interim/llm_tasks.jsonl`
- `data/interim/gemini_responses.jsonl`
- `data/interim/gemini_validated.jsonl`
- `data/gold/manual_moodle_links.csv`
- filled human cells in `data/gold/manual_fragment_annotations.csv`

Never print or commit `.env`, Moodle tokens, database passwords, Gemini keys, or `userprivateaccesskey`.

---

## Implementation rules for every later phase

- Inspect existing code first. Reuse loaders, validators, manifests, naming.
- One major phase at a time. Stop and wait for approval.
- After each phase: `python -m pytest -q` and `python -m compileall -q src scripts tests`.
- Do not commit or push unless Wail asks. Do not `git init` unless asked.
- Do not call external APIs unless Wail explicitly approves that phase.
- Do not fill gold labels, pedagogical ratings, or teacher decisions.

---

## Commands

```bash
# tests
python -m pytest -q
python -m compileall -q src scripts tests

# annotation
python scripts/12_validate_manual_annotations.py --mode template
python scripts/12_validate_manual_annotations.py --mode final

# do not regenerate the blank template after annotation has started
# python scripts/11_build_manual_annotation_template.py
```

Gemini resume (Phase 2 only, after explicit approval): use the existing checkpointed runner **without** `--restart`.

---

## Out of scope until supervisors reopen it

ROME 4.0; PDFs; video/audio; OCR; relation classification; recommendation engine; learning paths; advanced curriculum dashboard; native Moodle PHP plugin; LLM fine-tuning; large graph visualization; production deployment; silently changing the competency framework.

---

## Session log

| Date | What happened | Result |
|---|---|---|
| 2026-09-18 | Phase 0 audit | Pipeline exists through 23/35 Gemini; no git repo; 27 tests passed |
| 2026-09-18 | Phase 1 blinded annotation software | Blank 35-row template; 13-competency catalogue; 56 tests passed; **human annotation not filled** |
| | Next | Wail annotates gold; optional parallel Phase 2 Gemini resume after approval |
