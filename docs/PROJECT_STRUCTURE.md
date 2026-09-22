# Project structure

Every important active file and module, with its purpose, inputs, outputs and
safety properties.

**Script classification**

| Marker | Meaning |
|---|---|
| **OFFLINE / REPRODUCIBLE** | No network access. Safe to re-run. |
| **LIVE API / COST RISK** | Contacts an external API and spends quota. |
| **MOODLE ACCESS** | Requires credentials and a reachable Moodle instance. |
| **HUMAN INPUT** | Requires a person; synthesises nothing. |

---

## Top level

| Path | Role |
|---|---|
| `FINAL_DELIVERY/` | Delivery package — ten documents plus supporting evidence |
| `src/moodle_competency/` | Python package |
| `scripts/` | Numbered pipeline and helper scripts |
| `tests/` | 435 tests |
| `app/` | Research validation interface (Streamlit) |
| `app.py`, `pages/` | Runtime analysis interface (Streamlit) |
| `data/` | Corpus, frozen artefacts, human data, experiments |
| `reports/` | Metrics, tables, figures, reports |
| `docs/` | Technical documentation |
| `configs/`, `sql/` | Configuration and SQL queries |
| `archive/` | Superseded documentation, retained for provenance |

---

## `src/moodle_competency/`

### Moodle access

| Module | Purpose |
|---|---|
| `settings.py` | Loads configuration from `.env`; refuses to run with missing credentials |
| `moodle_client.py` | Authenticated web-service client with pagination and error handling |
| `db_export.py` | Direct SQL extraction for quiz questions and competency tables |
| `html_clean.py` | HTML to plain text, preserving block structure |

### Corpus preparation

| Module | Purpose |
|---|---|
| `normalization.py` | Resource normalisation; merges quiz stem with answer options |
| `competency_normalization.py` | Framework normalisation; resolves the parent-child hierarchy |
| `fragmentation.py` | Page chunking and question-to-fragment mapping; preserves provenance |
| `resource_ingestion.py` | Shared ingestion used by the runtime interface |

### Retrieval and model selection

| Module | Purpose |
|---|---|
| `retrieval.py` | BM25 index, querying, Top-K candidate selection |
| `llm_tasks.py` | Task assembly, prompt construction, output contract |
| `gemini_alignment.py` | API client: retry, backoff, quota handling, response parsing |
| `llm_validation.py` | Response validation, including the exact-substring evidence check |
| `ollama_alignment.py` | Local-model client for the post-hoc comparison |
| `unconstrained_llm.py` | Optional all-13 condition — software only, experiment not run |

`llm_validation.validate_alignment_response` is generic: it keys off each task's
allowed identifiers, so the same validator judges every condition identically.

### Reference and review

| Module | Purpose |
|---|---|
| `annotation.py` | CSV and JSONL I/O, annotation schema, validation |
| `annotation_session.py` | Interactive annotation with resume and timestamped backups |
| `evidence_review.py` | Evidence sheet construction, mechanical validity, character offsets |
| `evidence_review_session.py` | Interactive pedagogical rating; never suggests a rating |
| `ai_assisted_annotation.py` | Draft suggestions — drafts only, never the reference |

### Aggregation and evaluation

| Module | Purpose |
|---|---|
| `aggregation.py` | Fragment to resource; retains supporting fragments and confidences |
| `inverse_index.py` | Competency to resources; match counts and review status |
| `metrics.py` | Micro and macro P/R/F1, Recall@K, Hit@K, MRR, both macro views |
| `evaluation.py` | Human gates, set extraction, comparison tables |
| `resource_evaluation.py` | Derived resource reference and resource-level metrics |
| `error_analysis.py` | Error taxonomy, primary category, worked examples |
| `graph_checks.py` | Hierarchy warnings and the separate non-destructive ablation |

### Interfaces and reporting

| Module | Purpose |
|---|---|
| `corpus_app.py` | Data layer for the research interface; review persistence |
| `teacher_reviews.py` | Review schemas and storage for both interfaces |
| `teacher_study.py` | Evidence-usefulness pilot design and summary |
| `teacher_review_summary.py` | Review summary; reports null rather than zero when nothing is reviewed |
| `coverage.py` | Validated-coverage computation |
| `teacher_ui.py`, `teacher_app_pages.py` | Runtime interface rendering |
| `runtime_analysis.py`, `runtime_storage.py` | Runtime analysis and isolated storage |
| `reproducibility.py` | Manifest, checksums, environment capture, secret check |
| `human_validation_summary.py` | Human-validation status; refuses to invent rates |

`corpus_app.py` contains no Streamlit import. All logic is plain functions, so
the interface behaviour is unit-testable without a browser.

---

## `scripts/`

### Extraction — 01–02

| Script | Class | Inputs | Outputs | When |
|---|---|---|---|---|
| `01_extract_moodle_rest.py` | **MOODLE ACCESS** | Moodle web services | `data/raw/api/` | New corpus only |
| `02_extract_moodle_sql.py` | **MOODLE ACCESS** | Moodle database | `data/raw/sql/` | New corpus only |

Both write frozen artefacts. Already run; do not re-run against the reported
corpus.

### Preparation — 03–05

| Script | Class | Inputs | Outputs | Modifies frozen data |
|---|---|---|---|---|
| `03_normalize_resources.py` | OFFLINE / REPRODUCIBLE | `data/raw/` | `resources.jsonl` | Yes — already frozen |
| `04_normalize_competencies.py` | OFFLINE / REPRODUCIBLE | UTC GI source | `competencies.jsonl` | Yes — already frozen |
| `05_fragment_resources.py` | OFFLINE / REPRODUCIBLE | `resources.jsonl` | `fragments.jsonl` | Yes — already frozen |

### Retrieval and tasks — 06–07

| Script | Class | Inputs | Outputs |
|---|---|---|---|
| `06_retrieve_bm25_candidates.py` | OFFLINE / REPRODUCIBLE | fragments, competencies | `bm25_candidates.jsonl` |
| `07_build_llm_tasks.py` | OFFLINE / REPRODUCIBLE | candidates, competencies | `llm_tasks.jsonl` |

### Model — 08–10

| Script | Class | Notes |
|---|---|---|
| `08_validate_response_pipeline.py` | OFFLINE / REPRODUCIBLE | Validator self-test; no API call |
| `09_test_gemini_alignment.py` | **LIVE API / COST RISK** | Single-task pilot |
| `10_run_gemini_alignments.py` | **LIVE API / COST RISK** | The main model run. Checkpointed; resumes only, no restart mechanism. **Already run — its output is frozen and must never be regenerated.** |

### Reference annotation — 11–12

| Script | Class | Notes |
|---|---|---|
| `11_build_manual_annotation_template.py` | OFFLINE / REPRODUCIBLE | Builds the blank annotation sheet |
| `12_validate_manual_annotations.py` | OFFLINE / REPRODUCIBLE | Validates the reference. Run with `--mode final`. Read-only. |
| `manual_annotate_fragments.py` | **HUMAN INPUT** | Interactive annotation. Complete: 35/35 |

### Aggregation — 13–14

| Script | Class | Outputs |
|---|---|---|
| `13_aggregate_predictions.py` | OFFLINE / REPRODUCIBLE | `resource_predictions.jsonl` |
| `14_build_competency_resource_index.py` | OFFLINE / REPRODUCIBLE | `competency_resource_index.jsonl` |

### Evaluation — 15–16, 19, 22

| Script | Class | Outputs |
|---|---|---|
| `15_evaluate_bm25.py` | OFFLINE / REPRODUCIBLE | `bm25_metrics.json`, per-fragment and per-competency tables |
| `16_evaluate_constrained_llm.py` | OFFLINE / REPRODUCIBLE | `constrained_llm_metrics.json` |
| `19_analyze_errors.py` | OFFLINE / REPRODUCIBLE | `error_summary.json`, `error_analysis.csv`, `error_examples.csv` |
| `22_evaluate_resource_level.py` | OFFLINE / REPRODUCIBLE | `resource_level_metrics.json`, resource tables |

All verify protected checksums before and after running and abort on change.

### Evidence review — 17–18

| Script | Class | Notes |
|---|---|---|
| `17_prepare_evidence_review.py` | OFFLINE / REPRODUCIBLE | Builds the blank rating sheet with offsets |
| `review_evidence_pedagogically.py` | **HUMAN INPUT** | Interactive rating. Complete: 83/83 |
| `18_summarize_evidence_review.py` | OFFLINE / REPRODUCIBLE | `evidence_review_summary.json`. Verified byte-deterministic |

### Hierarchy — 23

| Script | Class | Notes |
|---|---|---|
| `23_run_graph_checks.py` | OFFLINE / REPRODUCIBLE | Warnings only. `--simulate-child-preference` writes a **separate** ablation under `data/experiments/`; original predictions are never modified. `--dry-run` writes nothing. |

### Optional unconstrained comparison — 24–26

| Script | Class | Notes |
|---|---|---|
| `24_build_unconstrained_tasks.py` | OFFLINE / REPRODUCIBLE | Builds tasks and audits condition equivalence. No API call. |
| `25_run_unconstrained_gemini.py` | **LIVE API / COST RISK** | **Refuses to run without `--i-authorize-the-unconstrained-experiment`.** `--dry-run` is free. **NOT RUN.** |
| `26_evaluate_unconstrained_gemini.py` | OFFLINE / REPRODUCIBLE | Refuses to score a run that has not happened; estimates nothing |

### Pilot and review summary — 27–28

| Script | Class | Notes |
|---|---|---|
| `27_prepare_teacher_study.py` | OFFLINE / REPRODUCIBLE | Fixed-seed A/B design; refuses to overwrite once responses exist |
| `28_summarize_teacher_reviews.py` | OFFLINE / REPRODUCIBLE | Reports null rates while nothing is reviewed |

### Optional local model — 29–30

| Script | Class | Notes |
|---|---|---|
| `29_run_ollama_constrained.py` | **LIVE API / COST RISK** (local) | Post-hoc comparison; isolated in `data/experiments/` |
| `30_evaluate_ollama_constrained.py` | OFFLINE / REPRODUCIBLE | Never merged into core metrics |

### Reporting and verification

| Script | Class | Purpose |
|---|---|---|
| `20_write_reproducibility_manifest.py` | OFFLINE / REPRODUCIBLE | Checksums, environment, model configuration |
| `34_summarize_human_validation.py` | OFFLINE / REPRODUCIBLE | Human-validation status |
| `35_generate_final_figures.py` | OFFLINE / REPRODUCIBLE | Regenerates the five figures from current metrics |
| `verify_frozen.py` | OFFLINE / REPRODUCIBLE | Whole-tree freeze snapshot and check |
| `ui_smoke_check.py` | OFFLINE / REPRODUCIBLE | Renders all 14 Streamlit pages **with outbound sockets blocked** |
| `collect_handoff_facts.py` | OFFLINE / REPRODUCIBLE | Inventory. Its test figure is a **pre-existing regression subset**, not the project total |
| `build_final_package_zip.py` | OFFLINE / REPRODUCIBLE | Reproducible archive; aborts on any credential pattern |

---

## `app/` — research validation interface

`streamlit run app/Home.py`. Reads frozen artefacts; makes no model calls.

| File | Page | Writes |
|---|---|---|
| `Home.py` | Course and resource browser | no |
| `_shared.py` | Shared helpers — not a page | no |
| `pages/1_Resource_to_Competencies.py` | Function A with evidence and BM25 rank | no |
| `pages/2_Teacher_Review.py` | Accept / reject / modify / add | **yes — one file** |
| `pages/3_Competency_to_Resources.py` | Function B | no |
| `pages/4_Evidence_Review.py` | Completed evidence review | no |
| `pages/5_Review_Progress.py` | Progress by course and type | no |
| `pages/6_Experiment_Results.py` | Measured results | no |
| `pages/7_Evidence_Usefulness_Pilot.py` | A/B pilot | pilot responses |
| `pages/8_Validated_Coverage.py` | Human-validated coverage only | no |

Writes only `data/reviews/corpus_teacher_reviews.csv`, atomically, after a
timestamped backup. Never writes to Moodle, the reference, the model output, the
evidence review, or any metric file.

## `app.py` and `pages/` — runtime analysis interface

`streamlit run app.py`. Analyses arbitrary new Moodle material. **LIVE API** and
**MOODLE ACCESS**. Not part of the reported experiment; output isolated in
`data/runtime/`.

---

## `data/`

| Path | Status | Content |
|---|---|---|
| `data/raw/` | Frozen, **not published** | Verbatim Moodle output; may carry private fields |
| `data/processed/` | Frozen | 20 resources, 35 fragments, 13 competencies, aggregations |
| `data/interim/` | Frozen | BM25 candidates, model tasks, model responses |
| `data/gold/` | Frozen, human | Reference annotations — 35 rows, 38 labels |
| `data/reviews/` | Human | Evidence review (83, complete); runtime reviews (2) |
| `data/studies/` | Derived | Pilot design; responses do not yet exist |
| `data/experiments/` | Optional | Post-hoc ablation, Ollama, unconstrained tasks |
| `data/runtime/` | Not published | Runtime interface output |

The 21 protected artefacts are enumerated in
`reports/PROTECTED_ARTIFACT_CANONICAL_LIST.md`.

---

## `reports/`

| Path | Content |
|---|---|
| `metrics/` | 12 JSON files — the authoritative numbers |
| `tables/` | 23 CSV tables |
| `figures/` | 5 PNG figures |
| `reproducibility_manifest.json` | Checksums, environment, model configuration |
| `PROTECTED_ARTIFACT_CANONICAL_LIST.md` | The 21 protected files and why |
| `FINAL_*.md` | Working analysis records |
| `logs/`, `api_raw/`, `sql_raw/` | Extraction records — partly unpublished |

---

## `tests/`

435 tests. Each builds its own fixtures in a temporary directory; none reads or
writes real experimental data, and none contacts an external API — the model
client is exercised through a fake session and the unconstrained condition
through hand-written fixture responses.

Regression tests assert the frozen headline metrics, so an accidental change to
evaluation code fails the suite rather than silently moving a published number.

---

## Finding things quickly

| Need | Location |
|---|---|
| Headline numbers | `reports/metrics/constrained_llm_metrics.json` |
| What went wrong | `reports/tables/error_analysis.csv` |
| Worked error examples | `reports/tables/error_examples.csv` |
| The reference annotation | `data/gold/manual_fragment_annotations.csv` |
| Evidence quotations and ratings | `data/reviews/evidence_review.csv` |
| The exact prompt sent to the model | `data/interim/llm_tasks.jsonl` |
| Candidates the model could choose from | `data/interim/bm25_candidates.jsonl` |
| Field definitions | `docs/DATA_DICTIONARY.md` |
| How to run anything | `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md` |
