# Pre-push validation

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — ENSIA · UTC / Heudiasyc / CNRS — 22 September 2026

Validation run immediately before publication to
<https://github.com/WailOuaret/moodle-competency-alignment-mvp>.

**Result: all checks pass.**

---

## 1. Validation suite

| Check | Command | Result |
|---|---|---|
| Reference annotations | `python scripts/12_validate_manual_annotations.py --mode final` | **PASSED** — 35 / 35 |
| Test suite | `python -m pytest -q` | **435 passed** |
| Compilation | `python -m compileall -q src scripts tests app` | **succeeded** (silent) |
| Interface render | `python scripts/ui_smoke_check.py` | **OK** — 14 / 14 pages |

The render check patches outbound sockets to raise, so any page attempting a
network call fails rather than succeeding silently.

### On the two test counts

`python -m pytest -q` reports **435 passed** across 39 test files. This is the
authoritative project total.

`scripts/collect_handoff_facts.py` reports **221 passed** across 32 files. That
is a **pre-existing regression subset**: it runs only the test files recorded in
the frozen manifest from an earlier hardening phase, excluding 7 files added
afterwards —

```
tests/test_corpus_app.py             tests/test_teacher_review_summary.py
tests/test_coverage.py               tests/test_teacher_study.py
tests/test_handoff_facts.py          tests/test_unconstrained_llm.py
tests/test_verify_frozen.py
```

Its purpose is to show that earlier tests still pass after later work. It is not
a project total, and the script now labels it explicitly as
`pre_existing_regression_subset` in both its console output and
`docs/handoff/facts.json`.

---

## 2. Protected artefacts

**21 / 21 unchanged.** The canonical set, with per-file checksums and rationale,
is `reports/PROTECTED_ARTIFACT_CANONICAL_LIST.md`.

| Tier | Meaning | Count | Status |
|---|---|---:|---|
| 1 | Frozen inputs and human judgement | 11 | unchanged |
| 2 | Derived results | 10 | unchanged |

Specifically confirmed unchanged:

| Artefact | Why it matters |
|---|---|
| `data/interim/gemini_responses.jsonl` | Historical model output; not reproducible by re-running |
| `data/interim/gemini_validated.jsonl` | The experiment itself |
| `data/gold/manual_fragment_annotations.csv` | 38 human reference labels |
| `data/gold/manual_moodle_links.csv` | Frozen Moodle reference links |
| `data/reviews/evidence_review.csv` | 83 human evidence ratings |
| `reports/metrics/bm25_metrics.json` | Headline retrieval results |
| `reports/metrics/constrained_llm_metrics.json` | Headline system results |

### The 20 vs 21 discrepancy, resolved

Earlier documentation reported both figures. The sets differ by exactly one
file — `data/processed/graph_warnings.jsonl` — which was omitted from the table
in `reports/FINAL_VALIDATION_REPORT.md` while its summary
`graph_check_summary.json` was included.

It was an omission, not a disagreement: no file's status was ever reported
differently, and none was reported unchanged when it had changed. **21 is
canonical**, and all current documentation now states 21.

---

## 3. Corrections applied in this pass

| Fix | Change |
|---|---|
| Protected count | Canonical list established; 21 propagated to all current documents |
| Retrieval claim | "Recall is bounded by retrieval" narrowed to the measured claim: in the constrained Top-5 condition, the only missed reference label was absent from the candidate set, and the model missed none available to it |
| Precision claim | "limited by one systematic error" replaced with "precision errors are **dominated by** parent-child granularity redundancy", with the remaining 4 of 14 false positives stated explicitly |
| Test count | 221 relabelled as a pre-existing regression subset in the script, in `facts.json`, and wherever it surfaced |
| `.gitignore` | `data/interim/` was excluded, which would have silently made the published repository non-reproducible. Corrected — all 21 protected artefacts publish |

No measured value was altered. The corrections are to wording and to
classification only.

---

## 4. Publication safety

| Check | Result |
|---|---|
| Secret scan over Git-trackable files | **0 matches** across 395 text files |
| `.env` tracked | **no** — ignored, and the local file is untouched |
| `reports/site_info.json` (private access key) | excluded |
| `data/raw/` (may carry private Moodle fields) | excluded |
| Largest published file | 680 KB (`unconstrained_llm_tasks.jsonl`) |
| Total publish size | 5.13 MB across 405 files |
| Virtual environment, caches, archives | excluded |
| Documented paths that do not exist | **0 of 124 references** |

Detail: `reports/GITHUB_SECRET_SCAN.md`.

---

## 5. Scientific state at publication

Unchanged by this pass.

| Item | Value |
|---|---|
| Corpus | 2 courses · 20 resources · 35 fragments · 13 competencies · 38 reference labels |
| BM25 Recall@1/@3/@5 | 0.6842 / 0.8684 / 0.9737 |
| BM25 Top-1 P/R/F1 | 0.7429 / 0.6842 / 0.7123 |
| Constrained model P/R/F1 | 0.7255 / 0.9737 / 0.8315 |
| Macro F1 (all 13 / supported) | 0.6958 / 0.9046 |
| Evidence | 83 / 83 exact; 65 rated 2, 16 rated 1, 2 rated 0 |
| Resource level P/R/F1 | 0.6765 / 0.9583 / 0.7931 |
| Teacher validation | **0 of 34 — WAITING_FOR_HUMAN** |
| Unconstrained all-13 experiment | **OPTIONAL / NOT RUN** |

No optional live model experiment was run during this pass. No human judgement
was fabricated. No acceptance rate is reported anywhere.

---

## 6. Verdict

Cleared for publication.
