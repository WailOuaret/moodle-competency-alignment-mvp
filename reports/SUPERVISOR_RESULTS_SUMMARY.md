# Supervisor results summary

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Researcher:** Wail Ouaret (ENSIA)  
**Supervisors:** Marie-Hélène Abel and Le Ngoc Luyen (UTC / Heudiasyc / CNRS)  
**Date:** 2026-09-22

This note reports **measured** values from the current MVP. It does not report inter-annotator agreement, supervisor agreement, or teacher acceptance rates: those were not collected. Pedagogical evidence ratings below are Human Gate 2 results from the researcher.

## 1. Experimental corpus

| Item | Count |
|---|---:|
| Moodle | 5.2.1+ (local) |
| Courses | 2 (`MVP-SW`, `MVP-DATA`) |
| Pages | 8 |
| Quiz questions (independent resources) | 12 |
| Normalized resources | 20 |
| Fragments | 35 |
| UTC GI competencies | 13 (3 parent + 10 child) |
| BM25 Top-5 sets | 35 |
| Constrained Gemini tasks | 35 |
| Valid Gemini responses | 35 |
| Model | `gemini-3.5-flash` |
| Temperature | 0 |
| Max selections | 3 |
| Candidate restriction | BM25 Top-5 |
| Exact-evidence validator | enabled |

Quiz questions remain independent research resources. They are not collapsed into the two Quiz activities.

## 2. Human-reviewed reference annotations

All 35 fragments were reviewed and finalized by the researcher against the 13-competency UTC GI catalogue. The finalized annotation set is used as the **human-reviewed reference** for evaluation.

| Check | Result |
|---|---|
| Validator | `python scripts/12_validate_manual_annotations.py --mode final` |
| Status | PASSED |
| Rows | 35 |
| Unique fragments | 35 |
| Missing / duplicate / unknown fragments | 0 |
| Unknown competency IDs | 0 |
| Incomplete decisions | 0 |
| Annotator | Wail Ouaret |
| Date | 2026-09-18 |
| NONE labels | 0 |
| Multi-label fragments | 3 |
| Ambiguous fragments | 1 (`page:3#f003`) |
| Total reference labels | 38 |

BM25 and Gemini predictions are evaluated against these researcher-reviewed reference annotations. This set is not described as independent blinded gold produced from scratch. No second annotator was used.

File: `data/gold/manual_fragment_annotations.csv`

## 3. BM25 retrieval results

Source: `reports/metrics/bm25_metrics.json`

| Metric | Value |
|---|---:|
| Recall@1 | 0.6842 |
| Recall@3 | 0.8684 |
| Recall@5 | 0.9737 |
| Hit@1 | 0.7429 |
| Hit@3 | 0.8857 |
| Hit@5 | 0.9714 |
| MRR | 0.8310 |
| BM25 Top-1 precision (micro) | 0.7429 |
| BM25 Top-1 recall (micro) | 0.6842 |
| BM25 Top-1 F1 (micro) | 0.7123 |
| BM25 Top-1 precision (macro) | 0.6538 |
| BM25 Top-1 recall (macro) | 0.5620 |
| BM25 Top-1 F1 (macro) | 0.5900 |

Recall@K is label-level over 38 reference labels. Hit@K and MRR are fragment-level over 35 fragments with non-empty reference sets. Parent and child IDs are distinct labels.

## 4. Constrained Gemini results

Source: `reports/metrics/constrained_llm_metrics.json`  
System: BM25 Top-5 + constrained Gemini (`gemini-3.5-flash`, temperature 0, max 3).

| Metric | Value |
|---|---:|
| Micro precision | 0.7255 |
| Micro recall | 0.9737 |
| Micro F1 | 0.8315 |
| Macro precision | 0.6833 |
| Macro recall | 0.7436 |
| Macro F1 | 0.6958 |
| Exact-set match | 0.6286 |
| Coverage | 1.0000 |
| Abstention rate | 0.0000 |
| Average predicted labels / fragment | 1.4571 |

## 5. BM25 vs BM25+Gemini comparison

Source: `reports/tables/model_comparison.csv`

| System | Micro precision | Micro recall | Micro F1 | Status |
|---|---:|---:|---:|---|
| BM25 Top-1 | 0.7429 | 0.6842 | 0.7123 | COMPLETE |
| BM25 Top-5 + constrained Gemini | 0.7255 | 0.9737 | 0.8315 | COMPLETE |

On this corpus, adding constrained Gemini to BM25 Top-5 raises micro recall and micro F1 relative to BM25 Top-1, with a small drop in micro precision.

## 6. Resource → competency examples

From `data/processed/resource_predictions.jsonl` (Function A). Teacher decisions are still `pending`.

**Page `page:2` — User-Centered Interface Design and Accessibility**

- `GI_C1_3` from fragments `page:2#f001`, `page:2#f002` (support 2, max confidence 0.95)
- `GI_C1` from fragment `page:2#f001` (support 1)

**Quiz question `quiz_question:1:4` — SW_Q3_User_Centred_Design** (kept as its own resource)

- Gemini predicted `GI_C1_1` (the human-reviewed reference for this fragment is `GI_C1_3`; see error analysis)

Page fragments aggregate onto their Page. The 12 quiz questions remain 12 resources.

## 7. Competency → resources examples

From `data/processed/competency_resource_index.jsonl` (Function B). All 13 competencies are present. Teacher decision status is `pending`.

| Competency | Matching resources (examples) |
|---|---|
| GI_C1_3 (HCI / UX) | 1 resource: `page:2` |
| GI_C3_3 (data science / ML / NLP) | 3 resources: `page:8`, `quiz_question:2:12`, `quiz_question:2:13` |
| GI_C3_2 (data / databases) | 5 resources |
| GI_C2 (parent architecture) | 1 resource: `page:4` |

No competency in this run had zero predicted resources.

## 8. Resource-level evaluation — COMPLETE

Source: `reports/metrics/resource_level_metrics.json`  
Reference: **derived** from the human-reviewed fragment labels. This is not a second independent annotation exercise. Native Moodle activity mappings are not question-level gold.

Page gold = union of that Page's fragment labels. Each Quiz question remains an independent resource.

| Metric | Value |
|---|---:|
| Resources | 20 / 20 (8 Pages, 12 Quiz questions) |
| Fragments used | 35 / 35, exactly once |
| Micro precision | 0.6765 |
| Micro recall | 0.9583 |
| Micro F1 | 0.7931 |
| Macro precision (all 13) | 0.7051 |
| Macro recall (all 13) | 0.7308 |
| Macro F1 (all 13) | 0.7026 |
| Macro precision (gold-supported) | 0.9167 |
| Macro recall (gold-supported) | 0.9500 |
| Macro F1 (gold-supported) | 0.9133 |
| Exact-set / subset accuracy | 0.4500 (9 / 20) |
| Average \|predicted − reference\| label count | 0.50 |
| Resource coverage | 1.0000 |
| Resource abstention | 0.0000 |

Fragment-level Gemini micro P/R/F1 = 0.7255 / 0.9737 / 0.8315. Resource-level micro precision is lower on this corpus; Page aggregation may accumulate false-positive labels from several fragments. That is a measured difference, not a causal proof.

Main resource-level errors: 11 overpredicted resources; 9 with parent-child redundancy; 1 false negative (`quiz_question:1:4`, reference `GI_C1_3`, predicted `GI_C1_1` — the same retrieval failure as at fragment level).

Ollama is not included in the Gemini resource-level metric file.

## 9. Error analysis

Source: `reports/metrics/error_summary.json`  
Reference: human-reviewed labels. Pedagogical-evidence flags are applied (Human Gate 2 complete).

Overlapping flag counts are **not** a partition of fragments. Primary category counts partition fragments for presentation.

| Overlapping flag | Fragments |
|---|---:|
| correct_prediction | 22 |
| llm_wrong_selection | 13 |
| overprediction | 13 |
| parent_child_redundancy | 10 |
| retrieval_failure | 1 |
| underprediction | 1 |
| llm_missed_gold_label | 0 |
| incorrect_abstention | 0 |
| correct_abstention | 0 |
| ambiguous_gold | 1 |
| evidence_clear | 23 |
| evidence_partial | 11 |
| evidence_unsupported | 1 |
| exact_but_weak_evidence | 12 |

| Primary category | Fragments |
|---|---:|
| llm_wrong_selection | 12 |
| correct_prediction | 21 |
| retrieval_failure | 1 |
| ambiguous_gold | 1 |

Retrieval failure detail: fragment `quiz_question:1:4#f001` has reference `GI_C1_3`, which is absent from BM25 Top-5 (`GI_C1_2`, `GI_C3_2`, `GI_C3`, `GI_C1_1`, `GI_C1_4`). Gemini therefore could not select the reference label under the Top-5 constraint. `llm_missed_gold_label` is 0: every retrievable reference label was selected.

## 10. Minimal hierarchy / graph experiment — COMPLETE

This is a **post-hoc hierarchy ablation**. It is not part of the original Gemini run. A deterministic hierarchy rule was applied after the frozen Gemini predictions to assess the effect of removing redundant parent labels. Original Gemini metric files were not replaced.

### ORIGINAL SYSTEM (unchanged)

Fragment Gemini: micro P/R/F1 = 0.7255 / 0.9737 / 0.8315; exact-set = 0.6286; parent-child redundancy = 10 fragments.

Resource Gemini: micro P/R/F1 = 0.6765 / 0.9583 / 0.7931; exact-set = 0.4500; parent-child redundancy = 9 resources.

### POST-HOC GRAPH ABLATION

Warnings (non-destructive): 10/35 fragments and 9/20 resources with parent-child redundancy. Invalid hierarchy references = 0. Most frequent redundant parent: `GI_C3` (6 fragment pairs). Parents removed from the simulated set: 10. Removed true human-reference labels: **0**.

| Level | Original | Post-hoc child-preference |
|---|---:|---:|
| Fragment micro P | 0.7255 | 0.9024 |
| Fragment micro R | 0.9737 | 0.9737 |
| Fragment micro F1 | 0.8315 | 0.9367 |
| Fragment exact-set | 0.6286 | 0.9143 |
| Resource micro P | 0.6765 | 0.9200 |
| Resource micro R | 0.9583 | 0.9583 |
| Resource micro F1 | 0.7931 | 0.9388 |
| Resource exact-set | 0.4500 | 0.9000 |

Recall did not change. Precision, F1, and exact-set accuracy increased because unsupported parents were removed. These ablation metrics do not replace the original Gemini results.

Source: `reports/MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md`

## 11. Mechanical and pedagogical evidence — Human Gate 2 COMPLETE

Source: `data/reviews/evidence_review.csv`, `reports/metrics/evidence_review_summary.json`

| Item | Value |
|---|---|
| Evidence rows (quotes, not predictions) | 83 |
| Mechanically valid exact substrings | 83 / 83 = 100% |
| Pedagogical rating 2 (clear support) | 65 / 83 = 78.3% |
| Pedagogical rating 1 (partial / ambiguous) | 16 / 83 = 19.3% |
| Pedagogical rating 0 (unsupported) | 2 / 83 = 2.4% |

**Wording:** 100% of evidence quotes were mechanically valid exact substrings, while 78.3% were judged to clearly support the predicted competency. Mechanical exactness does not guarantee pedagogical relevance. Do not read this as “evidence is 100% correct.”

Both rating-0 quotes belong to fragment `quiz_question:1:4#f001`, predicted competency `GI_C1_1`, with human-reviewed reference `GI_C1_3`. The quotes include `User_Centred_Design` and `Testing a prototype with representative users`. They are exact substrings of the quiz stem, but they were judged not to justify software-development competency `GI_C1_1`.

## 12. Teacher validation — WAITING_FOR_HUMAN

Two interfaces exist and both are **COMPLETE** as software:

| Interface | Launch | Purpose |
|---|---|---|
| **Frozen-corpus validation app** | `streamlit run app/Home.py` | validate the 34 predicted mappings behind these results |
| Runtime analysis app | `streamlit run app.py` | analyse an arbitrary new resource; not part of this experiment |

All 14 Streamlit pages render cleanly with outbound network access blocked
(`python scripts/ui_smoke_check.py`).

**Reviewed: 0 of 34.** Live Gemini and Ollama runtime tests were performed, and
researcher reviews number **2** (REJECT `GI_C3`, ACCEPT `GI_C3_1` on one Gemini
runtime analysis). Those rows are researcher decisions about a runtime analysis,
not teacher validation of this corpus.

| Role | Count |
|---|---:|
| teacher | 0 |
| supervisor | 0 |
| researcher | 2 (runtime app) |

**No teacher acceptance rate is reported.** `reports/metrics/teacher_review_summary.json`
stores `null` for `acceptance_rate`, `edit_rate` and `rejection_rate` — not
`0.0`, which would read as "teachers accepted nothing" rather than "nothing was
reviewed".

The evidence-usefulness pilot (12 stratified cases, conditions balanced 6/6,
seed 20260918) is designed with **0 responses recorded**.

Guide: `docs/TEACHER_INTERFACE_GUIDE.md`. Protocol:
`docs/HUMAN_VALIDATION_PROTOCOL.md`. Detail: `reports/FINAL_TEACHER_REVIEW.md`.

## 13. Optional experiments

- Unconstrained Gemini over all 13 competencies: **SOFTWARE COMPLETE, RUN NOT AUTHORIZED**. The 35 tasks are built and an automated audit confirms the two conditions differ in nothing but the candidate space (0 fragment-text mismatches, 0 instruction mismatches, same validator reused unchanged). The live run spends API quota and refuses to execute without an explicit authorization flag. **No result is claimed in either direction.**
- Local Ollama (`mistral:latest`): **POST-HOC OPTIONAL EXPERIMENT**, stored under `data/experiments/` only. Not mixed into core Gemini metric files.
- Minimal hierarchy / graph analysis: **COMPLETE** as a separate post-hoc ablation. Original Gemini metrics were not replaced.
- ROME, PDFs/video, LTI, Moodle plugin: not run as core MVP.

## 14. Limitations

- Single-researcher human-reviewed reference; no second annotator.
- Small corpus (20 resources, 35 fragments, 13 competencies).
- Constrained Gemini can only choose from BM25 Top-5.
- Parent/child redundancy is frequent in Gemini outputs.
- Pedagogical ratings are also single-researcher.
- Teacher/supervisor validation has not started (UI ready; 0 teacher and 0 supervisor reviews).
- No reference `NONE` fragments, so abstention is **untested**, not good.
- Micro precision is substantially a measure of granularity-convention agreement: 10 of 14 false positives are parent competencies the annotator never labels.
- The hierarchy ablation is **post-hoc** and reference-specific — a diagnosis, not a validated technique.
- **No significance testing.** Sample size and single-rater design do not support inferential claims.
- Results are for this local Moodle MVP only.

Full treatment: `reports/FINAL_LIMITATIONS.md`.

## 15. Full report package

| Document | Contents |
|---|---|
| `reports/RESULTS_ONE_PAGE.md` | one-page summary for a quick read |
| `reports/FINAL_EXPERIMENTAL_RESULTS.md` | the complete results report, 18 sections |
| `reports/FINAL_ERROR_ANALYSIS.md` | error analysis with real examples |
| `reports/FINAL_TEACHER_REVIEW.md` | teacher-validation status, honestly empty |
| `reports/FINAL_LIMITATIONS.md` | what these numbers can and cannot support |
| `reports/FINAL_VALIDATION_REPORT.md` | acceptance checks and artefact integrity |
| `reports/FINAL_COMPLETION_AUDIT.md` | repository audit |
| `docs/SUPERVISOR_DEMO.md` | 25-step demo script with anticipated questions |
| `reports/SUPERVISOR_DEMO_CHECKLIST.md` | printable demo checklist |

**Overall status: `WAITING_FOR_HUMAN`** — every automated check passes (435
tests, 21/21 protected hashes unchanged), and the remaining gap is the teacher
review, which is human rather than technical.
