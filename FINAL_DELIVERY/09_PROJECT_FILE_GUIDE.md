# Project File Guide

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

A guide to the repository for a reader who needs to find something. Only
directories that matter are described.

**Classification**

| Marker | Meaning |
|---|---|
| **SOURCE** | Implementation code |
| **FROZEN EXPERIMENT** | Part of the reported experiment; must not be regenerated |
| **DERIVED RESULT** | Computed from frozen inputs; may be regenerated |
| **HUMAN DATA** | Contains human judgement; never synthesised |
| **OPTIONAL EXPERIMENT** | Post-hoc or optional; isolated from core results |
| **DOCUMENTATION** | Written material |

---

## Repository root

```
moodle_competency_mvp/
├── FINAL_DELIVERY/      DOCUMENTATION  — the delivery package; start here
├── src/                 SOURCE         — Python package
├── scripts/             SOURCE         — numbered pipeline, 01–28
├── tests/               SOURCE         — 435 tests
├── app/                 SOURCE         — frozen-corpus validation interface
├── app.py, pages/       SOURCE         — runtime analysis interface
├── data/                              — corpus, experiments, human data
├── reports/                           — metrics, tables, figures, reports
├── docs/                DOCUMENTATION  — technical documentation
├── configs/, sql/       SOURCE         — configuration and SQL
├── archive/             DOCUMENTATION  — superseded material, retained
├── dist/                              — distribution archives
├── README.md            DOCUMENTATION
├── requirements.txt, requirements-lock.txt, pyproject.toml
└── .env.example                        — credential template; .env is never committed
```

---

## `FINAL_DELIVERY/` — **DOCUMENTATION**

The delivery package. A reader should start here.

| File | Content |
|---|---|
| `00_READ_ME_FIRST.md` | Orientation and reading order |
| `01_FINAL_TECHNICAL_REPORT.md` | The complete report |
| `02_METHODOLOGY.md` | Methodology in reproducible detail |
| `03_RESULTS_AND_ANALYSIS.md` | Results with analysis |
| `04_SYSTEM_ARCHITECTURE.md` | Architecture and module responsibilities |
| `05_REPRODUCIBILITY_GUIDE.md` | Environment and all commands |
| `06_DATA_AND_EXPERIMENT_DESCRIPTION.md` | Dataset inventory |
| `07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md` | Demonstration and validation procedure |
| `08_LIMITATIONS_AND_FUTURE_WORK.md` | Limitations and future work |
| `09_PROJECT_FILE_GUIDE.md` | This file |
| `figures/`, `tables/`, `metrics/` | Copies of the evidence cited above |
| `demo/` | Demonstration checklist |
| `project_manifest/` | Checksums and environment record |

---

## `src/moodle_competency/` — **SOURCE**

The Python package, grouped by responsibility.

| Area | Modules |
|---|---|
| Moodle access | `moodle_client`, `db_export`, `settings`, `html_clean` |
| Preparation | `normalization`, `competency_normalization`, `fragmentation`, `resource_ingestion` |
| Retrieval | `retrieval` |
| Model selection | `llm_tasks`, `gemini_alignment`, `llm_validation`, `ollama_alignment`, `unconstrained_llm` |
| Reference and review | `annotation`, `annotation_session`, `evidence_review`, `evidence_review_session`, `ai_assisted_annotation`, `ai_assisted_draft_suggestions` |
| Aggregation | `aggregation`, `inverse_index` |
| Evaluation | `metrics`, `evaluation`, `resource_evaluation`, `error_analysis` |
| Hierarchy | `graph_checks` |
| Interfaces | `corpus_app`, `teacher_reviews`, `teacher_study`, `coverage`, `teacher_ui`, `teacher_app_pages`, `runtime_analysis`, `runtime_storage` |
| Reproducibility | `reproducibility`, `human_validation_summary` |

Where to look first:

| Question | Module |
|---|---|
| How are metrics computed? | `metrics.py` |
| How is a response validated? | `llm_validation.py` |
| How is evidence checked as an exact substring? | `llm_validation.py`, `evidence_review.py` |
| How are errors classified? | `error_analysis.py` |
| What does the interface read and write? | `corpus_app.py` |

---

## `scripts/` — **SOURCE**

Numbered scripts run in order; each writes a durable artefact.

| Range | Stage |
|---|---|
| 01–02 | Extraction from Moodle |
| 03–05 | Normalisation and fragmentation |
| 06–07 | Retrieval and task construction |
| 08–10 | Model validation and run |
| 11–12 | Reference annotation and validation |
| 13–14 | Aggregation and inverse index |
| 15–16 | Evaluation |
| 17–19 | Evidence review and error analysis |
| 20 | Reproducibility manifest |
| 22–23 | Resource-level evaluation and hierarchy checks |
| 24–26 | Optional unconstrained comparison — **not run** |
| 27–28 | Pilot design and review summary |
| 29–30 | Optional local-model comparison |
| 34–35 | Human-validation summary and figures |

Named helpers: `manual_annotate_fragments.py` and
`review_evidence_pedagogically.py` (the two human checkpoints),
`verify_frozen.py`, `ui_smoke_check.py`, `build_final_package_zip.py`.

---

## `app/` — **SOURCE**

The frozen-corpus validation interface. Launch with `streamlit run app/Home.py`.

| File | Page |
|---|---|
| `Home.py` | Course and resource browser |
| `_shared.py` | Shared helpers — not a page |
| `pages/1_Resource_to_Competencies.py` | Function A with evidence |
| `pages/2_Teacher_Review.py` | **The only page that writes** |
| `pages/3_Competency_to_Resources.py` | Function B |
| `pages/4_Evidence_Review.py` | Evidence review, read-only |
| `pages/5_Review_Progress.py` | Progress |
| `pages/6_Experiment_Results.py` | Measured results, read-only |
| `pages/7_Evidence_Usefulness_Pilot.py` | Pilot |
| `pages/8_Validated_Coverage.py` | Validated coverage |

## `app.py` and `pages/` — **SOURCE**

The runtime analysis interface, for analysing an arbitrary new Moodle resource.
**Not part of the reported experiment.** Launch with `streamlit run app.py`.

---

## `data/`

### `data/raw/` — **FROZEN EXPERIMENT**

Verbatim Moodle output. `api/` holds web-service responses; `sql/` holds quiz
question text. **Excluded from distribution**: may contain private Moodle fields,
and `reports/site_info.json` carries a private access key.

### `data/processed/` — **FROZEN EXPERIMENT**

| File | Records |
|---|---:|
| `resources.jsonl` | 20 |
| `fragments.jsonl` | 35 |
| `competencies.jsonl` | 13 |
| `resource_predictions.jsonl` | 20 (34 mappings) — *derived* |
| `competency_resource_index.jsonl` | 13 — *derived* |
| `resource_reference.jsonl` | 20 — *derived* |
| `graph_warnings.jsonl` | 17 — *derived* |

### `data/interim/` — **FROZEN EXPERIMENT**

| File | Records |
|---|---:|
| `bm25_candidates.jsonl` | 35 |
| `llm_tasks.jsonl` | 35 |
| `gemini_responses.jsonl` | 35 |
| `gemini_validated.jsonl` | 35 |

**Must never be regenerated.** The model is a third-party service and the
historical responses are the experiment.

### `data/gold/` — **HUMAN DATA**

`manual_fragment_annotations.csv` — 35 rows, 38 reference labels, by Wail Ouaret
on 18 September 2026. The reference against which everything is scored.

`manual_moodle_links.csv` — 10 activity-level Moodle links, **not** used as
question-level ground truth.

`annotation_backups/` — intermediate states; excluded from distribution.

### `data/reviews/` — **HUMAN DATA**

| File | Content |
|---|---|
| `evidence_review.csv` | 83 quotations, all rated; complete |
| `teacher_reviews.csv` | 2 researcher decisions from the runtime application |
| `corpus_teacher_reviews.csv` | **Does not exist** — awaits teacher review |

The two review files use different schemas and are deliberately kept separate.

### `data/studies/` — **HUMAN DATA** (design **DERIVED**)

`teacher_study_cases.csv` and `teacher_study_manifest.json` — the 12-case pilot
design, seed 20260918.
`teacher_study_responses.csv` — **does not exist**; no response recorded.

### `data/experiments/` — **OPTIONAL EXPERIMENT**

Post-hoc graph ablation, local-model comparison, and unconstrained tasks.
Isolated by construction: nothing here can overwrite a core artefact.

`unconstrained_gemini_validated.jsonl` does not exist — the run was not
authorised.

### `data/runtime/` — **OPTIONAL**

Output of the runtime application. Not part of the reported experiment.

---

## `reports/`

### `reports/metrics/` — **DERIVED RESULT**

Twelve JSON files, all parsing. The authoritative numbers.

| File | Content |
|---|---|
| `bm25_metrics.json` | Recall@K, Hit@K, MRR, Top-1 P/R/F1 |
| `constrained_llm_metrics.json` | Micro and macro P/R/F1, exact-set |
| `macro_label_views.json` | Both macro views |
| `error_summary.json` | Error categories and evidence quality |
| `evidence_review_summary.json` | Evidence results |
| `resource_level_metrics.json` | Resource-level evaluation |
| `graph_check_summary.json` | Hierarchy warnings |
| `teacher_review_summary.json` | Review status; null rates while pending |
| others | Ablation and runtime summaries |

### `reports/tables/` — **DERIVED RESULT**

Twenty-three CSV tables: per-fragment and per-competency detail, error analysis
with worked examples, system deltas, label support, ablation comparisons.

### `reports/figures/` — **DERIVED RESULT**

Five PNG figures.

### `reports/*.md` — **DOCUMENTATION**

Analysis reports. `FINAL_DELIVERY/` supersedes these for delivery purposes; they
are retained as the working record.

### `reports/reproducibility_manifest.json` — **DERIVED RESULT**

Checksums for every artefact, plus environment and model configuration.

### `reports/api_raw/`, `reports/logs/`, `reports/sql_raw/`

Extraction records and logs. **Excluded from distribution.**

---

## `docs/` — **DOCUMENTATION**

| File | Content |
|---|---|
| `SETUP.md` | Environment setup |
| `PIPELINE.md` | Pipeline stages and gates |
| `EVALUATION.md` | Evaluation protocol |
| `DATA_DICTIONARY.md` | Field-level schema for every dataset |
| `CURRENT_STATUS.md` | Live status |
| `ANNOTATION_GUIDE.md` | Annotation conventions |
| `HUMAN_VALIDATION_PROTOCOL.md` | Validation protocol |
| `TEACHER_INTERFACE_GUIDE.md` | Interface guide for a reviewer |
| `SUPERVISOR_DEMO.md` | Extended demonstration script |
| `LTI_INTEGRATION_FEASIBILITY.md` | Feasibility note for deferred LTI work |
| `handoff/` | Generated inventories and smoke-check results |

---

## `tests/` — **SOURCE**

435 tests. Each constructs its own fixtures in a temporary directory; none reads
or writes real experimental data, and none contacts an external API.

Regression tests assert the frozen headline metrics, so an accidental change to
the evaluation code fails the suite rather than silently altering a result.

---

## `archive/` — **DOCUMENTATION**

Superseded material, retained for provenance.

| Directory | Content |
|---|---|
| `pre_final_cleanup/` | Documentation as it stood before the final editorial pass |
| `development_prompts/` | Development planning prompts |
| `documentation_history/` | Superseded report drafts |

Nothing here is required to run or understand the project; it is kept so the
history of the work remains inspectable.

---

## `dist/` — distribution

| File | Content |
|---|---|
| `Moodle_Competency_Alignment_MVP/` | Clean shareable project tree |
| `*_FINAL_PROJECT.zip` | The above, archived |
| `*_FINAL_DOCUMENTATION.zip` | Delivery documents, figures, tables, metrics |
| `WINDOWS_BACKUP_LOCATION.txt` | Path of the private local backup |

Distribution archives exclude `.env`, raw extraction, logs, backups and caches,
and are built by a script that aborts if any staged file matches a credential
pattern.

---

## Finding things quickly

| Need | Location |
|---|---|
| The headline numbers | `reports/metrics/constrained_llm_metrics.json` |
| What the system got wrong | `reports/tables/error_analysis.csv` |
| Worked error examples | `reports/tables/error_examples.csv` |
| The reference annotation | `data/gold/manual_fragment_annotations.csv` |
| Evidence quotations and ratings | `data/reviews/evidence_review.csv` |
| The exact prompt sent to the model | `data/interim/llm_tasks.jsonl` |
| The candidates the model could choose from | `data/interim/bm25_candidates.jsonl` |
| Field definitions | `docs/DATA_DICTIONARY.md` |
| How to run anything | `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md` |
| Artefact checksums | `reports/reproducibility_manifest.json` |
