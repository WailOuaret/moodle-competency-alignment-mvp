# Final completion audit

**Project:** Moodle Learning Resource-to-Competency Alignment MVP
**Researcher:** Wail Ouaret
**Supervisors:** Marie-Hélène Abel · Le Ngoc Luyen — UTC / Heudiasyc / CNRS
**Audit date:** 2026-09-22
**Supersedes:** the 2026-09-18 revision of this file, which described the repository *before* Human Gate 2 closed.
**Audit rule:** inspect and count only. No measured experimental output was rewritten while producing this audit.

Status values used: `COMPLETE` · `WAITING_FOR_HUMAN` · `OPTIONAL` · `DEFERRED` · `MISSING`

---

## 0. Headline: what changed since the previous audit

The completion prompt's frozen snapshot (Section A) was accurate when written but is **stale in four places**. The live repository was re-measured for this audit and the corrected facts are:

| Frozen claim (Section A) | Live repository | Verdict |
|---|---|---|
| `0 pedagogical ratings completed` | 83 / 83 rated (65 × `2`, 16 × `1`, 2 × `0`) | **STALE** — Human Gate 2 is CLOSED |
| `exact_but_weak_evidence = not yet evaluated` | `exact_but_weak_evidence = 12` | **STALE** — evidence is integrated into error analysis |
| `118 passed` | **237 passed** | **STALE** — suite grew, as the prompt anticipated |
| Sections F, G, H, I, J pending | all implemented and run | **STALE** — see §6 |

Everything else in Section A was re-verified against the live files and **matches exactly** (§2, §4).

Consequence for the execution order (Section T): steps 1–6 are already done. The remaining work starts at **step 7 (teacher validation UI)**. This audit does not skip to the UI — it establishes that steps 1–6 genuinely completed, which is what licenses moving on.

---

## 1. Audit checks run

| Check | Command | Result |
|---|---|---|
| Reference-annotation validator | `python scripts/12_validate_manual_annotations.py --mode final` | **PASSED** — 35 / 35, 0 missing, 0 unknown, 0 duplicate, 0 source-text mismatch, 0 incomplete |
| Test suite | `python -m pytest -q` | **237 passed** in 2.80 s |
| Compile check | `python -m compileall -q src scripts tests` | **succeeded** (silent) |
| Protected-file hashes | `sha256sum` vs `reports/reproducibility_manifest.json` | **all match**; nothing modified |

The interpreter is the project virtualenv, `.venv/bin/python` (Python 3.12.3). A bare `python` is not on `PATH` in this shell; every command in this report should be read as `.venv/bin/python …` or run after `source .venv/bin/activate`.

---

## 2. Current counts (re-measured from live files)

### Corpus

| Item | Count | Source file |
|---|---:|---|
| Moodle | 5.2.1+ (Build 20260722) | `reports/site_info.json`, reproducibility manifest |
| Courses | 2 — `MVP-SW`, `MVP-DATA` | resources (10 resources each) |
| Pages | 8 | `data/processed/resources.jsonl` |
| Quizzes | 2 | Moodle extraction — **not** evaluation units |
| Quiz questions kept as independent resources | 12 | `data/processed/resources.jsonl` |
| Normalized resources | **20** (8 `page` + 12 `quiz_question`) | `data/processed/resources.jsonl` |
| Fragments | **35** (23 `page_chunk` + 12 `quiz_question`) | `data/processed/fragments.jsonl` |
| Fragments by course | 16 `MVP-SW` + 19 `MVP-DATA` | `data/processed/fragments.jsonl` |
| UTC GI competencies | **13** (3 parent at depth 0 + 10 child at depth 1) | `data/processed/competencies.jsonl` |

Competency hierarchy actually present in the framework (the only hierarchy the graph layer is allowed to use):

```
GI_C1  Concevoir et développer des logiciels
  ├── GI_C1_1  Développement logiciel (conception, paradigmes, performance, déploiement)
  ├── GI_C1_2  Qualité logicielle et ingénierie soutenable
  ├── GI_C1_3  IHM et UX (mobile/VR/AR)
  └── GI_C1_4  Logiciels distribués et passage à l'échelle
GI_C2  Concevoir et mettre en œuvre des architectures informatiques
  ├── GI_C2_1  Architectures logicielles et matérielles (ressources/énergie)
  ├── GI_C2_2  Architectures communicantes (réseaux, cloud/fog/IoT)
  └── GI_C2_3  Architectures sûres et cybersécurité
GI_C3  Concevoir et mettre en œuvre des systèmes de traitement et d'analyse
  ├── GI_C3_1  Représentation et raisonnement sur les connaissances
  ├── GI_C3_2  Données et bases de données (SQL/NoSQL) & décision
  └── GI_C3_3  Data science / ML / NLP
```

There are no prerequisite or related-to relations in this framework. None were invented.

### Retrieval / LLM

| Item | Count | Source |
|---|---:|---|
| BM25 Top-5 candidate sets | 35 / 35 | `data/interim/bm25_candidates.jsonl` |
| Constrained LLM tasks | 35 / 35 | `data/interim/llm_tasks.jsonl` |
| Gemini responses | 35 / 35 | `data/interim/gemini_responses.jsonl` |
| Validated Gemini responses | 35 / 35, all `valid=true` | `data/interim/gemini_validated.jsonl` |
| Invalid accepted | 0 | validator |
| Missing responses | 0 | validator |
| Model / temperature / max selections | `gemini-3.5-flash` / `0` / `3` | manifest + tasks |
| Candidate restriction | BM25 Top-5 | tasks |
| Exact-evidence validation | enabled | `llm_validation.py` |
| Total predicted labels | **51** across 35 fragments | `gemini_validated.jsonl` |

### Human-reviewed reference (Human Gate 1 — `COMPLETE`)

| Item | Count | Source |
|---|---:|---|
| Reference rows | 35 / 35 complete | `data/gold/manual_fragment_annotations.csv` |
| Reference labels | **38** | same |
| Multi-label reference fragments | 3 | same |
| Ambiguous reference fragments | 1 (`page:3#f003`) | same |
| Reference `NONE` fragments | **0** | same |
| Annotator / date | Wail Ouaret / 2026-09-18 | same |
| Validator | PASSED (`--mode final`) | script 12 |

Reference-label distribution over the 13-label universe:

| Competency | Reference support | Predicted by Gemini |
|---|---:|---:|
| `GI_C1` | **0** | 3 |
| `GI_C1_1` | 3 | 4 |
| `GI_C1_2` | 3 | 3 |
| `GI_C1_3` | 3 | 2 |
| `GI_C1_4` | 4 | 4 |
| `GI_C2` | **0** | 1 |
| `GI_C2_1` | 1 | 1 |
| `GI_C2_2` | 1 | 3 |
| `GI_C2_3` | 4 | 5 |
| `GI_C3` | **0** | 6 |
| `GI_C3_1` | 4 | 4 |
| `GI_C3_2` | 9 | 9 |
| `GI_C3_3` | 6 | 6 |
| **Total** | **38** | **51** |

The three zero-reference-support labels are exactly the three **parent** competencies `GI_C1`, `GI_C2`, `GI_C3`. This is the measured basis for the two macro views (§6, F1) and for the parent-child redundancy finding (§4).

**Wording freeze.** These 35 rows are **human-reviewed reference annotations**. They are *not* independent blinded gold from scratch, and they are *not* AI-generated gold. There is one annotator, no second annotator, and no inter-annotator agreement measurement.

### Evidence review (Human Gate 2 — `COMPLETE`)

| Item | Value | Source |
|---|---:|---|
| Evidence-quote rows | 83 | `data/reviews/evidence_review.csv` |
| Mechanically valid exact substrings | 83 / 83 (100 %) | same |
| `offset_valid` | 83 / 83 `true` | same |
| Pedagogical ratings filled | **83 / 83** | same |
| — rating `2` (clearly supports) | 65 (78.31 %) | same |
| — rating `1` (partial / ambiguous) | 16 (19.28 %) | same |
| — rating `0` (does not justify) | 2 (2.41 %) | same |
| Reviewer / date | Wail Ouaret / 2026-09-18 | same |
| Free-text comments written | 18 | same |
| Timestamped backups | 2 | `data/reviews/evidence_review_backups/` |

Provenance was checked, not assumed. The ratings carry a single reviewer, a single review date, two timestamped backup files written during the session, and 18 substantive free-text justifications (for example, for `quiz_question:1:4#f001` / `GI_C1_1`: *"Prototype testing is HCI/UX (GI_C1_3), not GI_C1_1 software development"*). The `0` and `1` ratings concentrate on parent-only and topic-list quotes, which is the pattern a human rater would produce and not a pattern a default-fill would produce. These are treated as genuine human judgements.

### Aggregation / inverse index

| Item | Count | Source |
|---|---:|---|
| Fragments accounted for | 35 / 35 | `data/processed/resource_predictions.jsonl` |
| Resource-level predictions | 20, FINAL | same |
| Predicted resource–competency alignments | 34 | same |
| Competency → resource index rows | 13 / 13 | `data/processed/competency_resource_index.jsonl` |
| Competencies with zero predicted resources | 0 | same |
| Derived resource-level reference rows | 20 | `data/processed/resource_reference.jsonl` |
| Graph warnings | 17 | `data/processed/graph_warnings.jsonl` |
| Teacher decision status | **pending** | inverse index |

---

## 3. Protected files — hashes verified unchanged

Every hash below was recomputed during this audit and matches `reports/reproducibility_manifest.json`.

| File | SHA-256 |
|---|---|
| `data/processed/resources.jsonl` | `fbfb90a87f330cfd8d3571023501f5e0b416b58aa4833310967e132003d4d40e` |
| `data/processed/fragments.jsonl` | `6380f43b95628be59d028d0fcc5d55096448d49514ee42bce651082ba5568aa2` |
| `data/processed/competencies.jsonl` | `27ef8064e5eecc27b2baf0964a9c978a47de3b63338bd6642f658c1578650436` |
| `data/interim/bm25_candidates.jsonl` | `4e4e1ec030d8f1bfd17865690c83d66cec24fb256d8dc5e3dd523a27325bcaee` |
| `data/interim/llm_tasks.jsonl` | `32bc724db8aea5bd11a91bbe7788e839e853d6b726035fab78e5578b5924b66d` |
| `data/interim/gemini_responses.jsonl` | `0d8095dd1d320504ceeafad30a00eaf02b1a8f58b147a4f9f3ac275d18700602` |
| `data/interim/gemini_validated.jsonl` | `4ec9abf4aa1d3b4cdab2b1a5b367bc8ed9512b6b85616d053809dd6770e03a03` |
| `data/gold/manual_fragment_annotations.csv` | `3f96afd974db96394ee22239f0293bf1b641548836072839909b3992cf92fd53` |
| `data/gold/manual_moodle_links.csv` | `a349c5ecbda85e0e50c3ad160ff00d887ece1e1d1db68d7355d44a022bf67745` |
| `reports/metrics/bm25_metrics.json` | `f24ff968200a6ceacaee67986dabef19bc08eb04a026696232a91924c3366ab2` |
| `reports/metrics/constrained_llm_metrics.json` | `5ab206050828ec31f3b0cf9e45f7f889060c666e489d666fe2d1a36789e43248` |
| `reports/metrics/error_summary.json` | `5187048b33eaf3fa20bb03eed528baafba6ccc8d30852ec85108d5fc1904b22b` |
| `reports/metrics/evidence_review_summary.json` | `a8a39c440892ac7edf50daefe90098098ed676bfaf7b39b5dd706c5a52388964` |
| `reports/metrics/resource_level_metrics.json` | `9648d05548d6434e209142b9d4b6822d2cd5ae296eacbd61640af030fa4c90a2` |
| `reports/metrics/graph_check_summary.json` | `883e14827618edfab634e85961282a4b38dcf9b7bdbcebf34517a22c2a378c3b` |
| `reports/metrics/macro_label_views.json` | `b91b9939a5f9dbd9fff78f6605e82742342946676fabf20c099a563f99ff93c1` |
| `data/reviews/evidence_review.csv` | `c0747d433b2b5e98ebcde50dbdd5df9836190447abfe93f7ef67bc10cc65c667` |
| `data/reviews/teacher_reviews.csv` | `ba99c5f445df62e3b41ebb21f996d2033c26e34ccdb27839229690c89752d9c3` |

`data/gold/manual_moodle_links.csv` holds **activity-level** Moodle competency links (10 rows). It is *not* fragment-level reference and is not used as question-level gold.

---

## 4. Measured core results (unchanged by this audit)

### BM25 — `reports/metrics/bm25_metrics.json`

| Metric | Value |
|---|---:|
| Recall@1 | 0.6842105263 |
| Recall@3 | 0.8684210526 |
| Recall@5 | 0.9736842105 |
| Hit@1 | 0.7428571429 |
| Hit@3 | 0.8857142857 |
| Hit@5 | 0.9714285714 |
| MRR | 0.8309523810 |
| Top-1 micro P / R / F1 | 0.7428571429 / 0.6842105263 / 0.7123287671 |
| Top-1 macro P / R / F1 (all 13) | 0.6538461538 / 0.5619658120 / 0.5899806076 |
| Top-1 micro TP / FP / FN | 26 / 9 / 12 |

Recall@K is label-level over the 38 reference labels. Hit@K and MRR are fragment-level over the 35 non-empty reference fragments. Parent and child IDs are distinct labels — a parent does not automatically satisfy a child.

### BM25 Top-5 + constrained Gemini — `reports/metrics/constrained_llm_metrics.json`

| Metric | Value |
|---|---:|
| Micro P / R / F1 | 0.7254901961 / 0.9736842105 / 0.8314606742 |
| Macro P / R / F1 (all 13) | 0.6833333333 / 0.7435897436 / 0.6958485958 |
| Exact-set match | 0.6285714286 |
| Coverage | 1.0 |
| Abstention rate | 0.0 |
| Average predicted labels / fragment | 1.4571428571 |

All twelve values match Section A exactly.

### Error flags — `reports/metrics/error_summary.json`

| Category | Count | Note |
|---|---:|---|
| `correct_prediction` | 22 | |
| `llm_wrong_selection` | 13 | |
| `overprediction` | 13 | dominant error |
| `parent_child_redundancy` | 10 | |
| `retrieval_failure` | 1 | `quiz_question:1:4#f001`; reference `GI_C1_3` absent from Top-5 |
| `underprediction` | 1 | same fragment |
| `llm_missed_gold_label` | **0** | every retrievable reference label was selected |
| `incorrect_abstention` | 0 | |
| `correct_abstention` | 0 | no reference `NONE` fragments exist |
| `ambiguous_gold` | 1 | `page:3#f003` |
| `exact_but_weak_evidence` | **12** | now measured — Gate 2 closed |
| `evidence_clear` | 23 | |
| `evidence_partial` | 11 | |
| `evidence_unsupported` | 1 | |

The summary already carries `primary_category_counts` alongside `overlapping_flag_counts`, and states that flag counts overlap and are **not** a partition of the 35 fragments.

### Interpretation freeze (Section B — all eleven points re-verified)

1. BM25 Top-5 Recall = 0.9737; constrained Gemini micro Recall = 0.9737. The ceiling set by retrieval is exactly the recall the LLM achieves.
2. `llm_missed_gold_label = 0`. The single missed reference label is therefore a **retrieval failure**, not an LLM-selection failure.
3. The dominant Gemini error is **overprediction** (13 fragments), of which **parent-child redundancy** (10 fragments) is the largest identified sub-cause.
4. BM25 Top-1 has slightly **higher** micro precision than constrained Gemini: 0.7429 vs 0.7255 (Δ −0.0174).
5. Constrained Gemini has much **higher** recall: 0.9737 vs 0.6842 (Δ +0.2895).
6. Micro F1 improves: 0.7123 → 0.8315 (Δ +0.1191).
7. Abstention quality is **not** meaningfully tested — the reference set contains no `NONE` fragments. This must be stated explicitly in the final report.
8. Mechanical evidence validity is 100 %; pedagogical sufficiency is now measured: 78.31 % clear, 19.28 % partial, 2.41 % unsupported.
9. Gemini must **not** be described as "winning overall" without the stated trade-off: higher recall and F1, slightly lower micro precision.

---

## 5. Modules inspected

| Module | LOC | Role | Audit note |
|---|---:|---|---|
| `aggregation.py` | 308 | Fragment → resource (Function A) | FINAL write gated on complete Gemini set; 20/20 written |
| `inverse_index.py` | 135 | Competency → resources (Function B) | 13/13 rows; teacher status stays `pending` with no real review |
| `metrics.py` | 468 | Micro/macro P/R/F1, Recall@K, Hit@K, MRR | now exposes both `macro_all_13` and `macro_gold_supported_labels` |
| `evaluation.py` | 296 | Gates + table builders | does not fabricate metrics; delta table helper present |
| `evidence_review.py` | 254 | Mechanical validity + rating sheet | 14 columns incl. `review_date`, `evidence_start`, `evidence_end`, `offset_valid` |
| `evidence_review_session.py` | 285 | Gate 2 interactive helper | resume, backups, atomic save; never recommends a rating |
| `error_analysis.py` | 802 | Category flags | **now receives** pedagogical ratings from script 19 |
| `teacher_reviews.py` | 346 | Review storage | two schemas — see §7 finding T-1 |
| `reproducibility.py` | 491 | Manifest, no secrets | unambiguous reference-count fields; `contains_secrets=false` |
| `resource_evaluation.py` | 1204 | Resource-level eval (Section I) | derived reference documented in output JSON |
| `graph_checks.py` | 1686 | Hierarchy warnings + ablation (Section J) | `original_predictions_modified=false` asserted in output |

Scripts present: 01–23, 29, 30, 34, 35 plus named helpers (`review_evidence_pedagogically.py`, `report_evaluation_addenda.py`, `verify_frozen.py`, `ui_smoke_check.py`, …). Missing numbered scripts: **24, 25, 26, 27, 28**.

---

## 6. Section-by-section completion state

| § | Deliverable | Status | Evidence |
|---|---|---|---|
| **E** | Repository audit | `COMPLETE` | this file |
| **F1** | `macro_all_13` + `macro_gold_supported_labels` | `COMPLETE` | `reports/metrics/macro_label_views.json`, `reports/tables/label_support_prf.csv`; frozen metric JSONs untouched |
| **F2** | Delta table | `COMPLETE` | `reports/tables/system_delta_summary.csv` — 3 metrics, signed deltas, no winner text |
| **F3** | Manifest semantics | `COMPLETE` | `reference_annotation_row_count=35`, `reference_annotation_complete_count=35`, `reference_label_count=38`, `multi_label_fragment_count=3`, `ambiguous_fragment_count=1`, `none_fragment_count=0`; no misleading nulls; hashes cover evidence review, error analysis, graph outputs, teacher review |
| **G** | Gate 2 helper | `COMPLETE` | `evidence_review_session.py`, `scripts/review_evidence_pedagogically.py`, `tests/test_evidence_review_session.py` |
| **Gate 2** | Human pedagogical ratings | `COMPLETE` | 83/83 rated by Wail Ouaret, 2026-09-18 |
| **H** | Evidence-aware error analysis + examples | `COMPLETE` | `error_summary.json` (`exact_but_weak_evidence=12`, `primary_category_counts`), `reports/tables/error_examples.csv` |
| **I** | Resource-level evaluation | `COMPLETE` | `resource_evaluation.py`, `scripts/22_…`, `reports/metrics/resource_level_metrics.json`, `reports/tables/resource_level_evaluation.csv` |
| **J** | Minimal graph warnings + ablation | `COMPLETE` | `graph_checks.py`, `scripts/23_…`, `graph_warnings.jsonl` (17), `graph_check_summary.json`, ablation under `data/experiments/` |
| **K** | Unconstrained all-13 Gemini | **`MISSING` / `OPTIONAL`** | no `unconstrained_llm.py`, no scripts 24–26 — software must be built; **no live call without explicit authorization** |
| **L** | Teacher validation UI (`app/`) | **`MISSING`** | `app/` does not exist; see §7 finding T-2 |
| **M** | Evidence-usefulness pilot | **`MISSING`** | no `teacher_study.py`, no script 27 |
| **N** | Teacher review summary | **`MISSING` / `BLOCKED`** | no script 28; and only 2 researcher decisions exist (§7, T-1) |
| **O** | Minimal coverage view | **`MISSING`** | no `coverage.py`; correctly sequenced *after* teacher decisions |
| **P** | Final report package | **`MISSING`** (4 of 5 files) | `SUPERVISOR_RESULTS_SUMMARY.md` exists; `FINAL_EXPERIMENTAL_RESULTS.md`, `FINAL_ERROR_ANALYSIS.md`, `FINAL_TEACHER_REVIEW.md`, `FINAL_LIMITATIONS.md` absent |
| **Q** | Supervisor demo package | **`MISSING`** | `docs/SUPERVISOR_DEMO.md`, `reports/SUPERVISOR_DEMO_CHECKLIST.md`, `reports/RESULTS_ONE_PAGE.md` absent (older `FINAL_SUPERVISOR_DEMO.md` / `FINAL_DEMO_SCRIPT.md` exist but do not follow the 25-step format) |
| **R** | Final validation report | **`MISSING`** | `reports/FINAL_VALIDATION_REPORT.md` absent |

### Human gates

| Gate | Status |
|---|---|
| 1. Human-reviewed fragment reference | `COMPLETE` |
| 2. Pedagogical evidence 0/1/2 | `COMPLETE` (83/83) |
| 3. Teacher accept / reject / modify | **`WAITING_FOR_HUMAN`** — UI does not exist yet |

---

## 7. Findings that change the plan

**T-1 — `data/reviews/teacher_reviews.csv` is already occupied by a different schema.**
Section L says to persist teacher decisions in `data/reviews/teacher_reviews.csv`. That file already exists and holds **2 real researcher decisions** under the *runtime* review schema (`review_id, analysis_id, runtime_resource_id, fragment_id, competency_id, suggested_by_model, original_prediction, reconciled_prediction, decision, replacement_competency_id, comment, reviewer_name, reviewer_role, review_date, backend, model`), written by the separate runtime app on 2026-09-18 by Wail Ouaret (`reviewer_role=researcher`): one `REJECT` of `GI_C3` and one `ACCEPT` of `GI_C3_1`.

`teacher_reviews.py` also defines a **second, core-corpus** schema (`TEACHER_REVIEW_COLUMNS`: `review_id, resource_id, competency_id, fragment_ids, decision, modified_competency_ids, comment, evidence_relevance, reviewer, review_date`) which currently has no data file. The two schemas have different columns and cannot share one CSV.

**Resolution adopted:** the Section L UI will write the core-corpus reviews to **`data/reviews/corpus_teacher_reviews.csv`**, leaving `data/reviews/teacher_reviews.csv` untouched as the runtime review log. This is a deliberate, documented deviation from the literal path in Section L, taken because Section D forbids silent overwrites and Section R requires that "teacher review files preserve provenance". Overwriting the file would destroy two real human decisions. Both files will be hashed in the manifest and both will be read by the summary in Section N.

**T-2 — a Streamlit app exists, but it is not the Section L app.**
`app.py` at the repository root plus `pages/2_Review_Suggestions.py`, `3_Competency_to_Resources.py`, `4_Review_History.py`, `5_Research_Results.py` implement the **runtime** workflow: ingest an arbitrary new Moodle resource, analyse it live, and review those suggestions (`runtime_analysis.py`, `runtime_storage.py`, `teacher_app_pages.py`). Section L asks for a different interface — one over the **frozen 20-resource / 35-fragment research corpus**, with a course browser, evidence display, hierarchy context, graph warnings, an inverse competency→resource view, progress, and read-only results.

**Resolution adopted:** build the Section L app under `app/` as specified, reusing `teacher_reviews.py`, `inverse_index.py`, `error_analysis.py` and the frozen metric files. The existing runtime app is left in place and untouched; the interface guide will state plainly which app is which, so a supervisor is never shown two apps without explanation.

**T-3 — Section N cannot report rates yet.**
Only 2 researcher decisions exist and `reviewer_role=teacher` count is 0. `reports/metrics/human_validation_summary.json` already encodes this correctly (`status: WAITING_FOR_HUMAN`, `acceptance_rate: null`, `teacher_or_supervisor_validation_performed: false`). Script 28 will be built to compute rates *only* when real decisions exist, and to emit nulls with an explicit `WAITING_FOR_HUMAN` status otherwise. No rate will be invented.

**T-4 — documentation drift is minor.**
`docs/CURRENT_STATUS.md` is already accurate post-Gate-2 (it records 83/83 ratings and Gate 2 COMPLETE). `README.md` quotes correct metrics. The earlier audit's complaint that "README says 23 validated checkpoints" no longer applies. The stale artefact was this audit file itself, now replaced.

---

## 8. Current methodological limitations

Carried forward and re-verified. These are properties of the study, not defects to fix by coding.

1. **Small controlled synthetic corpus** — 20 resources, 35 fragments, 13 competencies, 2 courses. Results are an existence proof of the pipeline, not a population estimate.
2. **Single-researcher reference** — one annotator (Wail Ouaret). No second annotator, **no measured inter-annotator agreement**. Not independent blinded gold from scratch; not AI-generated gold.
3. **Single-rater evidence review** — the same person produced the reference and the 83 pedagogical ratings, so the evidence judgement is not independent of the reference judgement.
4. **No reference `NONE` fragments** — abstention rate (0.0) and abstention quality are therefore **untestable** on this corpus. `correct_abstention` and `incorrect_abstention` are both 0 by construction, not by merit.
5. **Pages + Quiz questions only** — no assignments, rubrics, PDFs, slides, video, audio or OCR.
6. **Local Moodle 5.2.1+**; the SQL Quiz-question fallback is local-development specific and would not transfer to a managed institutional instance unchanged.
7. **Three parent competencies have zero reference support** (`GI_C1`, `GI_C2`, `GI_C3`) yet receive 10 predictions. The full-13 macro view penalises this; the gold-supported macro view excludes it. Both are reported; neither alone is the honest number.
8. **Candidate restriction is untested against its alternative** — constrained Gemini may only choose from BM25 Top-5. The all-13 unconstrained comparison (Section K) has not been run, so the *effect* of restriction is inferred, not measured.
9. **Mechanical evidence validity ≠ pedagogical sufficiency** — 100 % of quotes are exact substrings, but 18 of 83 were rated partial or unsupported by the human reviewer.
10. **Teacher usefulness is not measured** — 0 teacher and 0 supervisor decisions exist. The 2 existing decisions are researcher decisions and must never be reported as teacher validation.
11. **External Gemini dependency** — historical responses must never be regenerated with `--restart`; reproduction depends on a third-party API whose behaviour may drift.
12. **No significance testing** — sample size and single-rater design do not support inferential claims. `significance_tests: not_run` is the correct record.

---

## 9. Exact planned next files

Execution resumes at Section T step 7. Planned order and files:

### Step 7 — Section L: teacher validation UI (core deliverable)
- `app/Home.py` — course / resource browser (`MVP-SW`, `MVP-DATA`)
- `app/pages/1_Resource_to_Competencies.py`
- `app/pages/2_Teacher_Review.py` → writes `data/reviews/corpus_teacher_reviews.csv` (see T-1)
- `app/pages/3_Competency_to_Resources.py`
- `app/pages/4_Evidence_Review.py` (read-only over the closed Gate 2)
- `app/pages/5_Review_Progress.py`
- `app/pages/6_Experiment_Results.py` (read-only; never writes metric files)
- `src/moodle_competency/corpus_app.py` — pure, testable data layer for the pages
- `docs/TEACHER_INTERFACE_GUIDE.md`
- `tests/test_corpus_app.py`, extend `tests/test_teacher_reviews.py`

### Step 7b — Section M: evidence-usefulness pilot
- `src/moodle_competency/teacher_study.py`
- `scripts/27_prepare_teacher_study.py` (fixed seed + saved manifest)
- `app/pages/7_Evidence_Usefulness_Pilot.py`
- `tests/test_teacher_study.py`

### Step 8 — **STOP.** Human teacher / researcher review. No decision is invented.

### Step 9 — Section N: teacher review summary
- `scripts/28_summarize_teacher_reviews.py`
- `reports/metrics/teacher_review_summary.json`, `reports/tables/teacher_review_summary.csv`
- `tests/test_teacher_review_summary.py`

### Step 10 — Section O: minimal coverage view
- `src/moodle_competency/coverage.py`, `app/pages/8_Coverage.py`, `tests/test_coverage.py`

### Step 11–12 — Section K: unconstrained Gemini, **software only**
- `src/moodle_competency/unconstrained_llm.py`
- `scripts/24_build_unconstrained_tasks.py`, `25_run_unconstrained_gemini.py`, `26_evaluate_unconstrained_gemini.py`
- `tests/test_unconstrained_llm.py` (mocked responses only; no test calls Gemini live)
- outputs confined to `data/experiments/unconstrained_*`
- **no live call** until the researcher says verbatim: `Run the optional unconstrained all-13 Gemini experiment.`

### Steps 13–15 — Sections P, Q, R
- `reports/FINAL_EXPERIMENTAL_RESULTS.md`, `FINAL_ERROR_ANALYSIS.md`, `FINAL_TEACHER_REVIEW.md`, `FINAL_LIMITATIONS.md`; refresh `SUPERVISOR_RESULTS_SUMMARY.md` and `docs/{CURRENT_STATUS,EVALUATION,PIPELINE,DATA_DICTIONARY}.md`, `README.md`
- `docs/SUPERVISOR_DEMO.md`, `reports/SUPERVISOR_DEMO_CHECKLIST.md`, `reports/RESULTS_ONE_PAGE.md`
- `reports/FINAL_VALIDATION_REPORT.md`

Step 16 (Git / GitHub cleanup) is **out of scope by researcher instruction** for this pass.

### Files that must not be touched
Everything in §3, plus `data/interim/gemini_raw_attempts.jsonl` and `backups/`. New experiments write only to `data/experiments/`. `reports/reproducibility_manifest.json` is derived and may be regenerated.

---

## 10. Overall status

**`WAITING_FOR_HUMAN`** — and not `COMPLETE`, because Section S forbids `COMPLETE` while the teacher interface is untested and the final report and demo package are missing. Both conditions currently hold.

The measured science through resource-level evaluation and the post-hoc graph ablation is finished and internally consistent. What remains is the teacher-facing interface, one more human gate, and the written deliverables.
