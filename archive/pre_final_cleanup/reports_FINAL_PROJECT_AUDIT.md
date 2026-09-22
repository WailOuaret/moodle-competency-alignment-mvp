# Final project audit

**Project:** Moodle Learning Resource → Competency Alignment MVP  
**Researcher:** Wail Ouaret  
**Date:** 2026-09-18  
**Rule:** inspect, count, hash, and document. Frozen experimental labels and predictions were not rewritten.

Status vocabulary: COMPLETE · WAITING_FOR_HUMAN · OPTIONAL / FUTURE EXTENSION · DEFERRED

---

## Project status

The experimental pipeline and teacher-facing software are complete for the reduced MVP. The remaining blocker for a full internship *evaluation* claim is real teacher or supervisor review. Researcher ACCEPT/REJECT rows exist and do not count.

See `docs/FINAL_PROJECT_STATUS.md`.

---

## Counts (live files)

| Item | Count | Source |
|---|---:|---|
| Courses | 2 (`MVP-SW`, `MVP-DATA`) | resources |
| Pages / Quiz-question resources | 8 / 12 | `data/processed/resources.jsonl` |
| Normalized resources | 20 | resources.jsonl |
| Fragments | 35 | `data/processed/fragments.jsonl` |
| Competencies | 13 | `data/processed/competencies.jsonl` |
| BM25 Top-5 sets | 35 | `data/interim/bm25_candidates.jsonl` |
| Constrained LLM tasks | 35 | `data/interim/llm_tasks.jsonl` |
| Valid Gemini responses | 35 / 35 | `data/interim/gemini_validated.jsonl` |
| Human-reviewed reference rows | 35 / 35 | `data/gold/manual_fragment_annotations.csv` |
| Reference labels | 38 | gold CSV |
| Multi-label / ambiguous / NONE | 3 / 1 / 0 | gold CSV |
| Evidence rows | 83 | `data/reviews/evidence_review.csv` |
| Mechanical exact quotes | 83 / 83 | evidence review |
| Pedagogical 2 / 1 / 0 | 65 / 16 / 2 | evidence review |
| Resource predictions | 20 | `data/processed/resource_predictions.jsonl` |
| Ollama validated checkpoints | 35 | `data/experiments/ollama_constrained_validated.jsonl` |
| Frozen Ollama metrics JSON | absent | not mixed into Gemini metrics |
| Teacher reviews | 0 | `data/reviews/teacher_reviews.csv` |
| Supervisor reviews | 0 | same |
| Researcher reviews | 2 | same; not teacher-study results |
| RQ2 form answers | 0 | `data/templates/human_validation_form.csv` header only |

Wording: the 35 rows are a **human-reviewed reference set**, not fully independent blinded gold created entirely from scratch.

---

## Completed components

- Moodle 5.2 local site, two courses, GI framework import
- Extraction, normalization, fragmentation, BM25, constrained Gemini
- Human-reviewed reference, evidence review, error analysis
- Resource-level evaluation (derived gold)
- Post-hoc hierarchy ablation (original Gemini unchanged)
- Optional Ollama checkpoints
- Streamlit teacher app + live Gemini/Ollama runtime tests
- Final report, demo package, Q&A, LTI feasibility note, figures/tables

---

## Remaining human actions

1. A teacher or supervisor reviews 2–5 resources in the Streamlit UI (`docs/HUMAN_VALIDATION_PROTOCOL.md`).
2. Optional RQ2 evidence on/off rows in `data/templates/human_validation_form.csv`.
3. Then: `python scripts/34_summarize_human_validation.py`

Do not invent those decisions.

---

## Protected-file hashes (must remain unchanged)

| File | SHA-256 |
|---|---|
| `data/gold/manual_fragment_annotations.csv` | `3f96afd974db96394ee22239f0293bf1b641548836072839909b3992cf92fd53` |
| `data/interim/bm25_candidates.jsonl` | `4e4e1ec030d8f1bfd17865690c83d66cec24fb256d8dc5e3dd523a27325bcaee` |
| `data/interim/gemini_validated.jsonl` | `4ec9abf4aa1d3b4cdab2b1a5b367bc8ed9512b6b85616d053809dd6770e03a03` |
| `reports/metrics/bm25_metrics.json` | `f24ff968200a6ceacaee67986dabef19bc08eb04a026696232a91924c3366ab2` |
| `reports/metrics/constrained_llm_metrics.json` | `5ab206050828ec31f3b0cf9e45f7f889060c666e489d666fe2d1a36789e43248` |
| `data/reviews/evidence_review.csv` | `c0747d433b2b5e98ebcde50dbdd5df9836190447abfe93f7ef67bc10cc65c667` |
| `reports/metrics/resource_level_metrics.json` | `9648d05548d6434e209142b9d4b6822d2cd5ae296eacbd61640af030fa4c90a2` |
| `data/experiments/graph_child_preference_predictions.jsonl` | `13dc984c2cb386723cb36943133b872015fe516d88468149a12597fbc901938a` |
| `data/experiments/ollama_constrained_validated.jsonl` | `c3f78f02802b47b62cfc77b405797b012e3020dfbd43d83a434e731f0f8d53bf` |
| `data/processed/resources.jsonl` | `fbfb90a87f330cfd8d3571023501f5e0b416b58aa4833310967e132003d4d40e` |
| `data/processed/fragments.jsonl` | `6380f43b95628be59d028d0fcc5d55096448d49514ee42bce651082ba5568aa2` |
| `data/interim/llm_tasks.jsonl` | `32bc724db8aea5bd11a91bbe7788e839e853d6b726035fab78e5578b5924b66d` |
| `data/interim/gemini_responses.jsonl` | `0d8095dd1d320504ceeafad30a00eaf02b1a8f58b147a4f9f3ac275d18700602` |
| `data/processed/resource_predictions.jsonl` | `fe7b20b01a8c51791573f5672c7e69e0c2e9ff5555febd7b8829d9f32697d66f` |

---

## Runtime directories

Teacher runtime writes to `data/runtime/{uploads,resources,fragments,retrieval,model_responses,analyses,manifests}/`. Live demo manifests present: `an_433ef0bd8a6d9752` (Gemini), `an_5133dbb54c6266db` (Ollama), `an_6e4dd0da7a7ea6ca` (second Gemini). These are isolated from frozen research files.

---

## Report files (finalization set)

- `reports/FINAL_INTERNSHIP_REPORT.md`
- `reports/HUMAN_VALIDATION_SUMMARY.md` (WAITING_FOR_HUMAN if no teacher/supervisor rows)
- `reports/tables/final_results_summary.csv`
- `reports/tables/final_key_examples.csv`
- `reports/figures/` (generated from existing metrics)
- `docs/FINAL_SUPERVISOR_DEMO.md`, `docs/FINAL_DEMO_SCRIPT.md`, `docs/SUPERVISOR_QA.md`
- `docs/LTI_INTEGRATION_FEASIBILITY.md` (not implemented)
- `docs/HUMAN_VALIDATION_PROTOCOL.md`, `docs/RQ2_VALIDATION_GUIDE.md`

---

## Tests and compile

Recorded after this audit’s verification commands:

| Command | Result |
|---|---|
| `python -m pytest -q` | **221 passed** |
| `python -m compileall -q src scripts tests app.py pages` | succeeded |
| `python scripts/34_summarize_human_validation.py` | `HUMAN VALIDATION NOT YET PERFORMED` (2 researcher reviews) |

If tests fail, only genuine software or documentation issues may be fixed. Scientific labels and predictions must not be edited to satisfy tests.

---

## Limitations (audit)

Small controlled corpus; single-researcher reference; no NONE labels; no teacher/supervisor study; hierarchy metrics are post-hoc; Ollama metrics JSON absent; LTI and native plugin not built; runtime demo ≠ frozen experiment.
