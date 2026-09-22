# Canonical protected artefact list

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — ENSIA · UTC / Heudiasyc / CNRS — 22 September 2026

The authoritative definition of which files are protected, why, and their
verified checksums. Where any other document states a protected-artefact count,
this file is the reference.

**Canonical count: 21.**
**Verified unchanged: 21 / 21.**

---

## 1. How this set is defined

There is no single `PROTECTED_PATHS` constant in the codebase, and that is what
produced the inconsistency resolved in section 4. Individual scripts declare
*local* guards covering only the files they could plausibly touch — script 22
guards 7 files, script 23 guards 9, script 28 guards 6 — and
`scripts/verify_frozen.py` snapshots the entire repository, which is a different
concept again.

The canonical set is therefore defined by the project methodology rather than by
any one script: **a file is protected when altering it would invalidate a
reported result.** That yields two tiers.

| Tier | Meaning | Count |
|---|---|---:|
| **1** | Frozen inputs and human judgement. Must never be regenerated. | 11 |
| **2** | Derived results. Regenerable deterministically, but any change means a reported number moved. | 10 |
| | **Total** | **21** |

The distinction matters operationally. A Tier 1 change is unrecoverable — the
model responses came from a third-party API and the annotations came from a
person. A Tier 2 change is recoverable by re-running its script, but still
signals that a published figure has shifted.

---

## 2. Tier 1 — frozen inputs and human data

Never regenerate. No script in the project offers a mechanism to do so.

| # | Path | Category | SHA-256 | Status |
|---:|---|---|---|---|
| 1 | `data/processed/resources.jsonl` | Frozen corpus | `fbfb90a87f330cfd8d3571023501f5e0…` | unchanged |
| 2 | `data/processed/fragments.jsonl` | Frozen corpus | `6380f43b95628be59d028d0fcc5d5509…` | unchanged |
| 3 | `data/processed/competencies.jsonl` | Frozen corpus | `27ef8064e5eecc27b2baf0964a9c978a…` | unchanged |
| 4 | `data/interim/bm25_candidates.jsonl` | Frozen retrieval | `4e4e1ec030d8f1bfd17865690c83d66c…` | unchanged |
| 5 | `data/interim/llm_tasks.jsonl` | Frozen model input | `32bc724db8aea5bd11a91bbe7788e839…` | unchanged |
| 6 | `data/interim/gemini_responses.jsonl` | Frozen model output | `0d8095dd1d320504ceeafad30a00eaf0…` | unchanged |
| 7 | `data/interim/gemini_validated.jsonl` | Frozen model output | `4ec9abf4aa1d3b4cdab2b1a5b367bc8e…` | unchanged |
| 8 | `data/gold/manual_fragment_annotations.csv` | Human reference | `3f96afd974db96394ee22239f0293bf1…` | unchanged |
| 9 | `data/gold/manual_moodle_links.csv` | Frozen Moodle data | `a349c5ecbda85e0e50c3ad160ff00d88…` | unchanged |
| 10 | `data/reviews/evidence_review.csv` | Human review | `c0747d433b2b5e98ebcde50dbdd5df98…` | unchanged |
| 11 | `data/reviews/teacher_reviews.csv` | Human review | `ba99c5f445df62e3b41ebb21f996d203…` | unchanged |

**Why each is protected**

- **`resources.jsonl`** — Normalised research resources; the corpus definition. Methodology Section D.
- **`fragments.jsonl`** — The evaluation unit; every metric denominator derives from it. Methodology Section D.
- **`competencies.jsonl`** — Competency catalogue used for retrieval and selection. Methodology Section D.
- **`bm25_candidates.jsonl`** — Defines the model's search space; required to attribute retrieval vs model error. Methodology Section D.
- **`llm_tasks.jsonl`** — The exact prompt sent to the model. Methodology Section D.
- **`gemini_responses.jsonl`** — Historical third-party API output; not reproducible by re-running. Methodology Section D.
- **`gemini_validated.jsonl`** — Validated responses; the experiment itself. Methodology Section D.
- **`manual_fragment_annotations.csv`** — 38 reference labels; one annotator. Human Gate 1. Irreplaceable.
- **`manual_moodle_links.csv`** — Activity-level Moodle links; retained for reference. Methodology Section D.
- **`evidence_review.csv`** — 83 pedagogical ratings. Human Gate 2. Irreplaceable.
- **`teacher_reviews.csv`** — 2 real researcher decisions from the runtime app. Irreplaceable.

---

## 3. Tier 2 — derived results

Regenerable from Tier 1 by the scripts that produced them, and verified
deterministic: re-running `scripts/18_summarize_evidence_review.py` reproduces
its output byte for byte. A change here is not data loss, but it means a figure
quoted in the reports has moved.

| # | Path | Category | SHA-256 | Status |
|---:|---|---|---|---|
| 1 | `data/processed/resource_predictions.jsonl` | Derived aggregation | `fe7b20b01a8c51791573f5672c7e69e0…` | unchanged |
| 2 | `data/processed/competency_resource_index.jsonl` | Derived aggregation | `c1208bc9070e91247809a478e4faac1e…` | unchanged |
| 3 | `data/processed/graph_warnings.jsonl` | Derived analysis | `8ff4856a8504452a03b823fcf9538a2e…` | unchanged |
| 4 | `reports/metrics/bm25_metrics.json` | Frozen result | `f24ff968200a6ceacaee67986dabef19…` | unchanged |
| 5 | `reports/metrics/constrained_llm_metrics.json` | Frozen result | `5ab206050828ec31f3b0cf9e45f7f889…` | unchanged |
| 6 | `reports/metrics/error_summary.json` | Derived result | `5187048b33eaf3fa20bb03eed528baaf…` | unchanged |
| 7 | `reports/metrics/evidence_review_summary.json` | Derived result | `a8a39c440892ac7edf50daefe9009809…` | unchanged |
| 8 | `reports/metrics/resource_level_metrics.json` | Derived result | `9648d05548d6434e209142b9d4b6822d…` | unchanged |
| 9 | `reports/metrics/graph_check_summary.json` | Derived result | `883e14827618edfab634e85961282a4b…` | unchanged |
| 10 | `reports/metrics/macro_label_views.json` | Derived result | `b91b9939a5f9dbd9fff78f6605e82742…` | unchanged |

**Why each is protected**

- **`resource_predictions.jsonl`** — Function A output; 34 reported mappings.
- **`competency_resource_index.jsonl`** — Function B output; 13 reported index rows.
- **`graph_warnings.jsonl`** — 17 hierarchy warnings cited in the results.
- **`bm25_metrics.json`** — Headline retrieval metrics. Methodology Section D.
- **`constrained_llm_metrics.json`** — Headline system metrics. Methodology Section D.
- **`error_summary.json`** — Error taxonomy counts cited throughout.
- **`evidence_review_summary.json`** — Evidence quality figures.
- **`resource_level_metrics.json`** — Resource-level evaluation.
- **`graph_check_summary.json`** — Hierarchy warning summary.
- **`macro_label_views.json`** — Both macro views and per-label support.

---

## 4. Resolution of the 20 vs 21 inconsistency

Earlier documentation reported two different counts. The cause has been
identified precisely.

`reports/FINAL_VALIDATION_REPORT.md` section 3 tabulates **20** files. A later
verification pass checked **21**. Comparing the two sets:

```
21-file set  -  20-file set  =  { data/processed/graph_warnings.jsonl }
```

The difference is exactly one file, and nothing else.

**This was an omission, not a disagreement.** No file's protected status was
reported differently in the two lists, and no file was ever reported unchanged
when it had in fact changed. `graph_warnings.jsonl` — the 17 hierarchy warnings
cited in the results — was simply left out of the earlier table, while its
sibling `graph_check_summary.json` was included.

**Resolution: 21 is canonical.** `graph_warnings.jsonl` belongs in the set on the
same grounds as the other Tier 2 files: it is a recorded experimental output
cited in the reported results. Excluding it while including
`graph_check_summary.json`, which merely summarises it, would be arbitrary.

All current public-facing documentation now states 21.

---

## 5. Pre-cleanup and post-cleanup comparison

All 21 artefacts existed before the final documentation cleanup pass, and all 21
are byte-identical after it. That pass moved and rewrote documentation only; it
did not touch `data/` or `reports/metrics/`.

Independently corroborated by `reports/reproducibility_manifest.json`, which
records the same checksums, and by the per-script guards, which snapshot
checksums before and after execution and abort on change.

---

## 6. What is deliberately **not** protected

| File | Why not |
|---|---|
| `reports/reproducibility_manifest.json` | Records the checksums; regenerated by design on every verification run |
| `reports/tables/*.csv` | Derived presentations of the metric files |
| `reports/figures/*.png` | Regenerated from current metrics |
| `data/experiments/*` | Optional and post-hoc; isolated so they cannot affect core results |
| `data/reviews/corpus_teacher_reviews.csv` | Does not yet exist; awaits human review |
| `data/studies/teacher_study_responses.csv` | Does not yet exist; awaits human responses |
| `data/runtime/*` | Runtime application output, not part of the reported experiment |

---

## 7. Verification

```bash
python scripts/12_validate_manual_annotations.py --mode final
python scripts/20_write_reproducibility_manifest.py
```

Individual scripts verify their own guarded subset before and after running and
abort on any change. Verified 22 September 2026: **21 / 21 unchanged.**
