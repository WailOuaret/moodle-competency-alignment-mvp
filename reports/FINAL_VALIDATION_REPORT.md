# Final validation report

**Moodle learning resource-to-competency alignment — reduced MVP**
**Researcher:** Wail Ouaret · UTC / Heudiasyc / CNRS
**Validation date:** 2026-09-22
**Interpreter:** `.venv/bin/python` — Python 3.12.3

**Verdict: `WAITING_FOR_HUMAN`.** Every automated check passes and every
protected artefact is byte-identical. The project is **not** marked `COMPLETE`
because Section S forbids that while teacher validation has not been performed.

---

## 1. Acceptance checks

All six required checks were run on 2026-09-22 against the live repository.

| # | Check | Command | Result |
|---:|---|---|---|
| 1 | Reference annotations | `scripts/12_validate_manual_annotations.py --mode final` | **PASSED** |
| 2 | Evidence review | `scripts/18_summarize_evidence_review.py` | **COMPLETE** |
| 3 | Teacher review | `scripts/28_summarize_teacher_reviews.py` | **WAITING_FOR_HUMAN** (correct) |
| 4 | Graph outputs | `scripts/23_run_graph_checks.py --dry-run` | **PASSED** |
| 5 | Test suite | `python -m pytest -q` | **435 passed** |
| 6 | Compile | `python -m compileall -q src scripts tests app` | **succeeded** |

Two additional checks were run beyond the required six:

| # | Check | Command | Result |
|---:|---|---|---|
| 7 | Interface render | `scripts/ui_smoke_check.py` | **14 / 14 pages OK** |
| 8 | Secret scan | regex over `reports/` and `docs/` | **0 matches** |

### 1 — Reference annotations

```
Source fragments: 35        Annotation rows: 35
Missing fragments: 0        Unknown fragments: 0
Duplicate fragments: 0      Source-text mismatches: 0
Unknown catalogue competencies: 0
Incomplete rows: 0
Status: PASSED
```

### 2 — Evidence review

83 rows, 83 mechanically valid (100%), **83/83 human-rated**:
65 × `2`, 16 × `1`, 2 × `0`. `pedagogical_complete: true`, `status: COMPLETE`.
Human Gate 2 is closed.

### 3 — Teacher review

`status: WAITING_FOR_HUMAN` — 34 reviewable mappings, 0 reviewed, 34 pending.
All rates are `null`, not `0.0`. **This is the correct result, not a failure.**
The validator is working precisely because it declines to report a rate with no
denominator.

### 4 — Graph outputs

35 fragments checked · 10 fragment-level parent-child redundancies · 9
resource-level · **0 invalid hierarchy references** ·
`original_predictions_modified: false`. Run as `--dry-run`, so no file was
rewritten during validation.

### 5 — Test suite

**435 passed**, 0 failed, in 3.53 s. Up from 237 at the start of this phase
(+198). No test calls a live API: the Gemini tests drive a `FakeSession`, and
the unconstrained tests use hand-written fixture responses.

### 6 — Compile

`compileall` silent across `src`, `scripts`, `tests` and `app`.

### 7 — Interface render

All 14 Streamlit pages render without exception **with outbound network access
blocked** (sockets patched to raise), so no page can silently reach an external
service:

```
OK  app.py                                    OK  app/pages/3_Competency_to_Resources.py
OK  pages/2_Review_Suggestions.py             OK  app/pages/4_Evidence_Review.py
OK  pages/3_Competency_to_Resources.py        OK  app/pages/5_Review_Progress.py
OK  pages/4_Review_History.py                 OK  app/pages/6_Experiment_Results.py
OK  pages/5_Research_Results.py               OK  app/pages/7_Evidence_Usefulness_Pilot.py
OK  app/Home.py                               OK  app/pages/8_Validated_Coverage.py
OK  app/pages/1_Resource_to_Competencies.py
OK  app/pages/2_Teacher_Review.py
```

### 8 — Secret scan

No API key, password or web-service token pattern appears in any generated
report, doc, metric file or table. `contains_secrets: false` in the
reproducibility manifest. `.env` is untracked and was never read into any
output.

---

## 2. Required content verification

| Requirement | Expected | Actual | |
|---|---:|---:|:--:|
| Reference rows complete | 35 | **35** | ✅ |
| Gemini responses valid | 35 | **35 / 35** | ✅ |
| Resource predictions | 20 | **20** | ✅ |
| Competency-index rows | 13 | **13** | ✅ |
| Metric JSON files parse | all | **12 / 12** | ✅ |
| Evidence review complete | 83 | **83 / 83 rated** | ✅ |
| Teacher review provenance preserved | — | both files intact | ✅ |
| No secret in generated reports | 0 | **0** | ✅ |
| Protected hashes unchanged | all | **21 / 21** | ✅ |
| Optional outputs isolated | — | all in `data/experiments/` | ✅ |

### Metric files that parse

`bm25_metrics` · `constrained_llm_metrics` · `error_summary` ·
`evidence_review_summary` · `graph_check_summary` ·
`graph_child_preference_fragment_metrics` ·
`graph_child_preference_resource_metrics` · `human_validation_summary` ·
`macro_label_views` · `resource_graph_check_summary` ·
`resource_level_metrics` · `teacher_review_summary`

---

## 3. Protected artefact integrity

All 21 protected files were re-hashed and compared against the values recorded
in `reports/FINAL_COMPLETION_AUDIT.md` and
`reports/reproducibility_manifest.json`.

**Result: 21 / 21 unchanged. 0 changed.**

The canonical set is defined in `reports/PROTECTED_ARTIFACT_CANONICAL_LIST.md`. An earlier revision of this table listed 20, omitting `data/processed/graph_warnings.jsonl`; that omission is corrected below.

| File | SHA-256 (first 16) |
|---|---|
| `data/processed/resources.jsonl` | `fbfb90a87f330cfd…` |
| `data/processed/fragments.jsonl` | `6380f43b95628be5…` |
| `data/processed/competencies.jsonl` | `27ef8064e5eecc27…` |
| `data/interim/bm25_candidates.jsonl` | `4e4e1ec030d8f1bf…` |
| `data/interim/llm_tasks.jsonl` | `32bc724db8aea5bd…` |
| `data/interim/gemini_responses.jsonl` | `0d8095dd1d320504…` |
| `data/interim/gemini_validated.jsonl` | `4ec9abf4aa1d3b4c…` |
| `data/gold/manual_fragment_annotations.csv` | `3f96afd974db9639…` |
| `data/gold/manual_moodle_links.csv` | `a349c5ecbda85e0e…` |
| `data/reviews/evidence_review.csv` | `c0747d433b2b5e98…` |
| `data/reviews/teacher_reviews.csv` | `ba99c5f445df62e3…` |
| `data/processed/resource_predictions.jsonl` | `fe7b20b01a8c5179…` |
| `data/processed/competency_resource_index.jsonl` | `c1208bc9070e9124…` |
| `reports/metrics/bm25_metrics.json` | `f24ff968200a6cea…` |
| `reports/metrics/constrained_llm_metrics.json` | `5ab206050828ec31…` |
| `reports/metrics/error_summary.json` | `5187048b33eaf3fa…` |
| `reports/metrics/evidence_review_summary.json` | `a8a39c440892ac7e…` |
| `reports/metrics/resource_level_metrics.json` | `9648d05548d6434e…` |
| `reports/metrics/graph_check_summary.json` | `883e14827618edfa…` |
| `reports/metrics/macro_label_views.json` | `b91b9939a5f9dbd9…` |
| `data/processed/graph_warnings.jsonl` | `8ff4856a8504452a…` |

### A determinism result worth recording

`scripts/18_summarize_evidence_review.py` was **re-run** during this validation
and rewrote `reports/metrics/evidence_review_summary.json`. Its hash is
unchanged. The derived summary is therefore byte-for-byte reproducible from the
same inputs — the regeneration path is deterministic, not merely untouched.

### Derived files intentionally regenerated

Two files were regenerated during this phase, by design, and neither is a
historical experimental artefact:

| File | Why |
|---|---|
| `reports/reproducibility_manifest.json` | derived manifest; extended with 16 new hash entries for the Section K/L/M/N/O artefacts. **All pre-existing hashes are identical.** |
| `reports/metrics/teacher_review_summary.json` + `.csv` | newly created by script 28 (Section N). |

No historical Gemini output was regenerated. `--restart` was never used.

---

## 4. Optional experiment isolation

Every optional output lives under `data/experiments/` and no core file was
overwritten:

```
graph_child_preference_manifest.json              (Section J ablation)
graph_child_preference_predictions.jsonl          (Section J ablation)
graph_child_preference_resource_predictions.jsonl (Section J ablation)
ollama_constrained_manifest.json                  (earlier model comparison)
ollama_constrained_raw_attempts.jsonl
ollama_constrained_responses.jsonl
ollama_constrained_validated.jsonl
unconstrained_llm_tasks.jsonl                     (Section K — tasks only)
unconstrained_llm_tasks_manifest.json             (Section K — tasks only)
```

`unconstrained_gemini_responses.jsonl` and `unconstrained_gemini_validated.jsonl`
**do not exist**, because the optional run has not been authorized. The
reproducibility manifest records `None` for them rather than a placeholder.

### The authorization gate was tested

```
$ python scripts/25_run_unconstrained_gemini.py
REFUSED: this experiment is optional and spends API quota.
It will not run without explicit researcher authorization.
                                                        → exit 3
```

The dry-run path reports the plan and exits without any request. The evaluator
(script 26) likewise refuses with exit 2 and states that nothing will be
estimated in place of a missing run.

---

## 5. Human gates

| Gate | Status | Evidence |
|---|---|---|
| 1 · Human-reviewed fragment reference | **`COMPLETE`** | 35/35, validator PASSED, Wail Ouaret, 2026-09-18 |
| 2 · Pedagogical evidence 0/1/2 | **`COMPLETE`** | 83/83 rated, 2 timestamped backups, 18 written comments |
| 3 · Teacher accept/reject/modify | **`WAITING_FOR_HUMAN`** | 0 of 34; interface built and rendering |
| 4 · Evidence-usefulness pilot | **`WAITING_FOR_HUMAN`** | 12-case design fixed at seed 20260918; 0 responses |

Gate 2 provenance was checked rather than assumed: a single reviewer, a single
date, two backup files written during the session, and 18 substantive free-text
justifications whose content (parent-only and topic-list quotes concentrated in
the `0`/`1` ratings) matches human judgement rather than a default fill.

---

## 6. Section-by-section status

| § | Deliverable | Status |
|---|---|---|
| E | Repository audit | `COMPLETE` |
| F1 | Two macro views | `COMPLETE` |
| F2 | Delta table | `COMPLETE` |
| F3 | Manifest semantics | `COMPLETE` |
| G | Evidence-rating helper | `COMPLETE` |
| H | Evidence-aware error analysis | `COMPLETE` |
| I | Resource-level evaluation | `COMPLETE` |
| J | Graph warnings + ablation | `COMPLETE` |
| **K** | **Unconstrained all-13** | **`OPTIONAL` — software complete, not run** |
| L | Teacher validation interface | `COMPLETE` (built, untested by a teacher) |
| **M** | **Evidence-usefulness pilot** | **`WAITING_FOR_HUMAN` — designed, 0 responses** |
| **N** | **Teacher review summary** | **`WAITING_FOR_HUMAN` — 0 decisions** |
| O | Coverage view | `COMPLETE` (correctly empty) |
| P | Final report package | `COMPLETE` |
| Q | Supervisor demo package | `COMPLETE` |
| R | This validation report | `COMPLETE` |

---

## 7. Why the project is not `COMPLETE`

Section S forbids `COMPLETE` while any of three conditions holds. Checking each:

| Condition | Holds? | |
|---|---|---|
| Pedagogical evidence ratings missing | **No** — 83/83 rated | ✅ cleared |
| Teacher interface untested | **Yes** — renders, but **no teacher has used it** | ❌ blocks |
| Final report / demo package missing | **No** — Sections P and Q delivered | ✅ cleared |

One condition still holds. The correct overall status is **`WAITING_FOR_HUMAN`**.

The two optional items — the unconstrained all-13 comparison and the graph
ablation — do **not** block the reduced MVP, and the supervisors have not
required them.

---

## 8. What is needed to close

### Step 1 — teacher review (~30–45 min)

```bash
source .venv/bin/activate
streamlit run app/Home.py      # → page "2 Teacher Review"
```

Enter a name and role, work through the 34 pending suggestions. Then:

```bash
python scripts/28_summarize_teacher_reviews.py
```

### Step 2 — evidence-usefulness pilot, optional (~15 min, 12 cases)

Same app → page **7 Evidence Usefulness Pilot**. Design already fixed at seed
20260918; conditions balanced 6/6 across three strata and both courses.

### Step 3 — optional unconstrained run, needs authorization

```bash
python scripts/25_run_unconstrained_gemini.py --dry-run   # free, shows the plan
python scripts/25_run_unconstrained_gemini.py --i-authorize-the-unconstrained-experiment
python scripts/26_evaluate_unconstrained_gemini.py
```

### Step 4 — re-validate

Re-run the six acceptance checks plus the smoke check, refresh
`reports/reproducibility_manifest.json`, and update this report.

---

## 9. Statement of integrity

For the record:

- **No human judgement was fabricated.** The 35 reference annotations and the 83
  evidence ratings are Wail Ouaret's own, recorded on 2026-09-18 with backups.
- **No teacher decision was invented.** 0 teacher and 0 supervisor decisions
  exist; the summary stores `null` rates rather than zeros, and the interface
  pre-fills nothing.
- **No optional experiment result was invented.** The unconstrained run has not
  been performed, its output files do not exist, and the evaluator refuses to
  estimate in their place.
- **No measured result was altered.** 21 of 21 protected artefacts are
  byte-identical; the one derived summary that was regenerated reproduced
  exactly.
- **No secret appears in any generated artefact.**

Automated verification is complete and passing. The remaining gap is human, not
technical, and is recorded as such throughout.
