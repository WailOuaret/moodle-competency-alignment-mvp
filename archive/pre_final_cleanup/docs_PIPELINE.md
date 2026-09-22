# Pipeline

Software stages in order. Do not rebuild completed extraction unless the Moodle corpus itself changed.

| # | Script | Input | Output |
|---|---|---|---|
| 1 | `01_extract_moodle_rest.py` | Moodle REST | `data/raw/api/`, `reports/api_raw/` |
| 2 | `02_extract_moodle_sql.py` | PostgreSQL (read-only) | quiz questions + competency SQL reports |
| 3 | `03_normalize_resources.py` | REST + SQL | `data/processed/resources.jsonl` |
| 4 | `04_normalize_competencies.py` | SQL competency CSV | `data/processed/competencies.jsonl` |
| 5 | `05_fragment_resources.py` | resources | `data/processed/fragments.jsonl` |
| 6 | `06_retrieve_bm25_candidates.py` | fragments + competencies | `data/interim/bm25_candidates.jsonl` |
| 7 | `07_build_llm_tasks.py` | BM25 + competencies | `data/interim/llm_tasks.jsonl` |
| 8 | `08_validate_response_pipeline.py` | tasks | abstention baseline |
| 9 | `09_test_gemini_alignment.py` | one task | pilot files |
| 10 | `10_run_gemini_alignments.py` | tasks | `gemini_responses.jsonl`, `gemini_validated.jsonl` |
| 11–12 | annotation template + validator | fragments + competencies | `data/gold/manual_fragment_annotations.csv` |
| helper | `manual_annotate_fragments.py` | gold CSV + catalogue | updated gold CSV |
| 13 | `13_aggregate_predictions.py` | fragments + validated Gemini | `resource_predictions.jsonl` (final only if Gemini complete) |
| 14 | `14_build_competency_resource_index.py` | competencies + resource predictions | `competency_resource_index.jsonl` |
| 15 | `15_evaluate_bm25.py` | complete gold + BM25 | `reports/metrics/bm25_metrics.json` |
| 16 | `16_evaluate_constrained_llm.py` | complete gold + complete Gemini | `reports/metrics/constrained_llm_metrics.json` |
| 17–18 | evidence review | validated Gemini + fragments | `data/reviews/evidence_review.csv` |
| helper | `review_evidence_pedagogically.py` | evidence CSV | human 0/1/2 ratings; does not recommend values |
| 19 | `19_analyze_errors.py` | gold + BM25 + Gemini | `reports/tables/error_analysis.csv` |
| 20 | `20_write_reproducibility_manifest.py` | environment + hashes | `reports/reproducibility_manifest.json` |
| 22 | `22_evaluate_resource_level.py` | fragment gold + existing resource predictions | `resource_reference.jsonl`, `reports/metrics/resource_level_metrics.json` |
| 23 | `23_run_graph_checks.py` | frozen Gemini + competencies | `graph_warnings.jsonl`; optional `--simulate-child-preference` under `data/experiments/` |
| 24 | `24_build_unconstrained_tasks.py` | fragments + competencies | `data/experiments/unconstrained_llm_tasks.jsonl` — **no API call** |
| 25 | `25_run_unconstrained_gemini.py` | unconstrained tasks | `data/experiments/unconstrained_gemini_*.jsonl` — **OPTIONAL; refuses without explicit authorization** |
| 26 | `26_evaluate_unconstrained_gemini.py` | unconstrained responses + gold | `reports/metrics/unconstrained_llm_metrics.json` — refuses if the run does not exist |
| 27 | `27_prepare_teacher_study.py` | error analysis + evidence review | `data/studies/teacher_study_cases.csv` + manifest (fixed seed) |
| 28 | `28_summarize_teacher_reviews.py` | teacher review files + predictions | `reports/metrics/teacher_review_summary.json` |

## Unit of analysis

- A **Page** may produce several `page_chunk` fragments; they aggregate back to that Page.
- Each **Quiz question** is one resource and one fragment. Do not collapse 12 questions into 2 Quizzes for the main evaluation.

## Gates

- **Human Gate 1:** 35/35 gold rows pass `python scripts/12_validate_manual_annotations.py --mode final`.
- **Human Gate 2:** 83/83 pedagogical ratings via `python scripts/review_evidence_pedagogically.py`.
- **Gemini authorization:** resume 12 missing tasks only with an explicit instruction; never `--restart`.
- **Human Gate 3:** teacher accept/reject/modify over the 34 predicted mappings, via `streamlit run app/Home.py` → page 2. **Open — 0 of 34.**
- **Human Gate 4:** evidence-usefulness pilot responses, via app page 7. **Open — designed, 0 responses.**
- Scripts 13 (final write), 15, 16 and 19 refuse final outputs while those gates are closed.
- Script 28 reports `null` rates rather than zeros while Gate 3 is open.
- **Optional-experiment authorization:** script 25 spends API quota and refuses to run without `--i-authorize-the-unconstrained-experiment`; `--dry-run` is free and makes no request.

## Framework import path

UTC GI JSON/JSONL → selected 13 IDs → Moodle 5.2 CSV (`data/processed/utc_gi_mvp_moodle.csv`) via `scripts/build_moodle_competency_csv.py` → Moodle native competency tables → Python `competencies.jsonl` for retrieval/LLM.


## Two Streamlit interfaces

They are different tools over different data and must not be confused.

| | Frozen-corpus validation app | Runtime analysis app |
|---|---|---|
| Launch | `streamlit run app/Home.py` | `streamlit run app.py` |
| Data | the fixed 20-resource research corpus | an arbitrary new Moodle resource |
| Purpose | validate the published results | analyse something on demand |
| Writes | `data/reviews/corpus_teacher_reviews.csv` | `data/reviews/teacher_reviews.csv` |
| Pages | Home + 8 | 5 |
| Part of the reported experiment | **yes** | no |

Neither writes to Moodle, to the human-reviewed reference, to the model output,
to the evidence review, or to any metric file. `scripts/ui_smoke_check.py`
renders all 14 pages with outbound sockets blocked, so a page that tried to
reach an external service would fail loudly rather than silently succeed.
