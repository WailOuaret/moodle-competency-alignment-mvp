# System Architecture

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

---

## 1. Overview

The system is a linear pipeline with two human checkpoints and two read-only
presentation surfaces. Each stage writes a durable artefact, so any stage can be
inspected or re-run independently, and a failure can be attributed to the stage
that produced it.

```
┌─────────────────────────────────────────────────────────────────────┐
│  MOODLE 5.2  (local)                                                │
│  2 courses · 8 Pages · 2 Quizzes · 12 questions · 13 competencies   │
└───────────────┬─────────────────────────────────┬───────────────────┘
                │ REST web services               │ direct SQL
                │ (pages, structure)              │ (question text)
                ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  EXTRACTION                              data/raw/                  │
│  Verbatim capture; provenance recorded before any processing        │
└───────────────┬─────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NORMALISATION                           20 resources               │
│  HTML stripped · entities resolved · quiz stem + options merged     │
└───────────────┬─────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRAGMENTATION                           35 fragments               │
│  Pages → 23 chunks · each question → 1 fragment · provenance kept   │
└───────────────┬─────────────────────────────────────────────────────┘
                │
                │         ┌───────────────────────────────────────────┐
                │         │  COMPETENCY CATALOGUE      13 competencies│
                │         │  Moodle CSV import → normalised JSONL     │
                │         └───────────────┬───────────────────────────┘
                ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BM25 RETRIEVAL                          35 × Top-5 candidate sets  │
│  Sets the recall ceiling: Recall@5 = 0.9737                         │
└───────────────┬─────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CONSTRAINED SELECTION                   35 responses               │
│  gemini-3.5-flash · T=0 · ≤3 selections · checkpointed per fragment │
└───────────────┬─────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  EVIDENCE VALIDATION                     35/35 valid, 0 rejected    │
│  Schema · allowed IDs · exact substring · confidence · abstention   │
└───────────────┬─────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRAGMENT PREDICTIONS                    51 predicted labels        │
└───────────────┬─────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RESOURCE AGGREGATION                    20 resources · 34 mappings │
│  Union of fragment labels; supporting fragments retained            │
└───────┬───────────────────────────────────────────┬─────────────────┘
        ▼                                           ▼
┌───────────────────────────┐          ┌────────────────────────────┐
│  HIERARCHY CHECKS         │          │  INVERSE INDEX             │
│  Warnings only            │          │  competency → resources    │
│  Predictions unmodified   │          │  13/13 with ≥1 resource    │
└───────────┬───────────────┘          └────────────┬───────────────┘
            │                                       │
            └───────────────┬───────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TEACHER VALIDATION INTERFACE            app/Home.py + 8 pages      │
│  Both directions · evidence · BM25 rank · warnings · decisions      │
│  Writes exactly one file. Never writes to Moodle or to results.     │
└─────────────────────────────────────────────────────────────────────┘
```

### Evaluation, alongside the pipeline

```
human-reviewed reference (35 fragments, 38 labels)
        │
        ├──▶ BM25 evaluation            Recall@K · Hit@K · MRR · Top-1 P/R/F1
        ├──▶ fragment evaluation        micro/macro P/R/F1 · exact-set
        ├──▶ resource evaluation        derived reference · micro/macro
        └──▶ error analysis             taxonomy · primary category · examples
                   ▲
                   │
        evidence review (83 quotations, rated 0/1/2)
```

---

## 2. Design principles

**Every stage writes a durable artefact.** Nothing important is held only in
memory. A reviewer can inspect the candidate set for any fragment, the exact task
sent to the model, and the raw response.

**The candidate set is recorded.** This is what makes the retrieval/selection
attribution decidable: for any missed label it can be determined whether the
correct competency was ever available.

**Validation precedes acceptance.** A model response enters the evaluation only
after passing schema, identifier, evidence and range checks.

**Frozen artefacts are protected.** Scripts that could overwrite an experimental
output verify protected checksums before and after running, and abort on change.

**Optional work is isolated.** Post-hoc and optional experiments write under
`data/experiments/` and cannot overwrite a core artefact.

**Human input is never synthesised.** No annotation, rating or review decision is
pre-filled or suggested, and rates are reported as null rather than zero where no
decision exists.

---

## 3. Subsystems

### 3.1 Acquisition

Retrieves material from Moodle and stores it verbatim.

| Module | Responsibility |
|---|---|
| `moodle_client.py` | Authenticated web-service calls, pagination, error handling |
| `db_export.py` | SQL extraction for quiz questions and competency tables |
| `settings.py` | Environment configuration; refuses to run with missing credentials |
| `html_clean.py` | HTML to plain text while preserving block structure |

Scripts `01_extract_moodle_rest.py`, `02_extract_moodle_sql.py`.

### 3.2 Preparation

Converts raw Moodle records into evaluation units.

| Module | Responsibility |
|---|---|
| `normalization.py` | Resource normalisation; quiz stem and options merged |
| `competency_normalization.py` | Framework normalisation; hierarchy resolution |
| `fragmentation.py` | Page chunking; question-to-fragment mapping; provenance |
| `resource_ingestion.py` | Shared ingestion used by the runtime application |

Scripts `03`–`05`.

### 3.3 Retrieval

| Module | Responsibility |
|---|---|
| `retrieval.py` | BM25 index, querying, Top-K selection, candidate records |

Script `06_retrieve_bm25_candidates.py`.

### 3.4 Model selection

| Module | Responsibility |
|---|---|
| `llm_tasks.py` | Task assembly, prompt construction, output contract |
| `gemini_alignment.py` | API client, retry and backoff, quota handling, response parsing |
| `llm_validation.py` | Response validation, including the exact-substring check |
| `ollama_alignment.py` | Local-model client for the post-hoc comparison |
| `unconstrained_llm.py` | Optional all-13 condition; **software only, not run** |

Scripts `07`–`10`, and `24`–`26` for the optional condition.

`llm_validation.validate_alignment_response` is deliberately generic: it keys off
each task's allowed identifiers, so the same validator judges the constrained and
unconstrained conditions identically.

### 3.5 Reference and review

| Module | Responsibility |
|---|---|
| `annotation.py` | CSV and JSONL I/O; annotation schema; validation |
| `annotation_session.py` | Interactive annotation with resume and backups |
| `evidence_review.py` | Evidence sheet construction; mechanical validity; offsets |
| `evidence_review_session.py` | Interactive rating with resume and backups |
| `ai_assisted_annotation.py` | Draft suggestions; drafts only, never the reference |

Scripts `11`, `12`, `17`, `18`, `21`, `review_evidence_pedagogically.py`.

### 3.6 Aggregation

| Module | Responsibility |
|---|---|
| `aggregation.py` | Fragment to resource; supporting fragments and confidences |
| `inverse_index.py` | Competency to resources; match counts; review status |

Scripts `13`, `14`.

### 3.7 Evaluation

| Module | Responsibility |
|---|---|
| `metrics.py` | Micro and macro P/R/F1; Recall@K; Hit@K; MRR; two macro views |
| `evaluation.py` | Gates; set extraction; comparison tables |
| `resource_evaluation.py` | Derived resource reference; resource-level metrics |
| `error_analysis.py` | Error taxonomy; primary category; worked examples |

Scripts `15`, `16`, `19`, `22`.

### 3.8 Hierarchy analysis

| Module | Responsibility |
|---|---|
| `graph_checks.py` | Hierarchy warnings; separate non-destructive ablation |

Script `23`.

### 3.9 Presentation

| Module | Responsibility |
|---|---|
| `corpus_app.py` | Data layer for the frozen-corpus interface; review persistence |
| `teacher_reviews.py` | Review schemas and storage for both applications |
| `teacher_study.py` | Evidence-usefulness pilot design and summary |
| `coverage.py` | Validated-coverage computation |
| `teacher_ui.py`, `teacher_app_pages.py` | Runtime application rendering |
| `runtime_analysis.py`, `runtime_storage.py` | Runtime analysis and isolated storage |

Scripts `27`, `28`, `34`, `35`.

The presentation data layer contains no Streamlit import. All logic is in plain
functions, and the pages are thin renderers, so the behaviour is unit-testable
without a browser.

### 3.10 Reproducibility

| Module | Responsibility |
|---|---|
| `reproducibility.py` | Manifest; checksums; environment capture; secret check |
| `human_validation_summary.py` | Human-validation status; refuses to invent rates |

Scripts `20`, `verify_frozen.py`, `ui_smoke_check.py`,
`build_final_package_zip.py`.

---

## 4. The two interfaces

Two Streamlit applications exist. They serve different purposes over different
data and must not be confused.

| | Frozen-corpus validation | Runtime analysis |
|---|---|---|
| Entry point | `app/Home.py` | `app.py` |
| Data | The fixed 20-resource research corpus | An arbitrary new Moodle resource |
| Purpose | Validate the reported results | Analyse material on demand |
| Model calls | None — reads frozen output | Live, on request |
| Writes | `data/reviews/corpus_teacher_reviews.csv` | `data/reviews/teacher_reviews.csv` |
| Storage | Frozen corpus artefacts | `data/runtime/` |
| Part of the experiment | Yes | No |

The frozen-corpus application is the one relevant to the reported results.

### Frozen-corpus pages

| Page | Function |
|---|---|
| `Home` | Course and resource browser |
| `1_Resource_to_Competencies` | Function A, with evidence and retrieval context |
| `2_Teacher_Review` | Accept, reject, modify, add — **the only page that writes** |
| `3_Competency_to_Resources` | Function B, the inverse direction |
| `4_Evidence_Review` | The completed evidence review, read-only |
| `5_Review_Progress` | Coverage by course and resource type |
| `6_Experiment_Results` | Measured results, read-only |
| `7_Evidence_Usefulness_Pilot` | Exploratory A/B comparison |
| `8_Validated_Coverage` | Coverage confirmed by human decision only |

Neither application writes to Moodle, to the reference annotations, to the model
output, to the evidence review, or to any metric file.

---

## 5. Data flow and ownership

| Artefact | Produced by | Consumed by | Status |
|---|---|---|---|
| `data/raw/` | Scripts 01–02 | Normalisation | Frozen |
| `resources.jsonl` | Script 03 | Fragmentation, aggregation | Frozen |
| `competencies.jsonl` | Script 04 | Retrieval, tasks, hierarchy | Frozen |
| `fragments.jsonl` | Script 05 | Retrieval, annotation, evaluation | Frozen |
| `bm25_candidates.jsonl` | Script 06 | Tasks, evaluation, interface | Frozen |
| `llm_tasks.jsonl` | Script 07 | Model run, validation | Frozen |
| `gemini_validated.jsonl` | Script 10 | Aggregation, evaluation | Frozen |
| `manual_fragment_annotations.csv` | Script 11 + human | All evaluation | Frozen, human |
| `resource_predictions.jsonl` | Script 13 | Inverse index, interface | Frozen |
| `competency_resource_index.jsonl` | Script 14 | Interface | Frozen |
| `evidence_review.csv` | Script 17 + human | Error analysis, interface | Frozen, human |
| `reports/metrics/*.json` | Scripts 15–23 | Reports, interface | Derived |
| `corpus_teacher_reviews.csv` | Interface + human | Script 28, coverage | Human, pending |
| `data/experiments/*` | Scripts 23–26, 29 | Optional analyses | Isolated |

---

## 6. Control points

**Human gates.** The pipeline cannot proceed past a gate on synthesised data.
Scripts producing final evaluation output refuse to run while the reference
annotation is incomplete, and the review summary reports null rather than zero
where no decision exists.

**Checksum protection.** Scripts that write near protected artefacts snapshot
their checksums before and after execution and abort on any change.

**Authorisation for cost.** The optional unconstrained experiment refuses to run
without an explicit authorisation flag. A dry run reports its plan and makes no
request.

**Network isolation in testing.** The interface render check patches outbound
sockets to raise, so a page attempting an external call fails loudly rather than
succeeding silently. All 14 pages pass under that condition.

**Secret handling.** Credentials are read from the environment and never written
to a generated artefact. The delivery build scans staged text files for key,
token and password patterns and aborts on a match.

---

## 7. Testing

435 tests covering normalisation, fragmentation, retrieval, task construction,
response validation, metrics, evaluation gates, aggregation, the inverse index,
error analysis, resource evaluation, hierarchy checks, both review layers, the
pilot design, coverage, reproducibility, and the interface data layer.

Tests construct their own fixtures in temporary directories. No test reads or
writes real experimental data, and no test contacts an external API: the model
client is exercised through a fake session, and the unconstrained condition
through hand-written fixture responses.

Regression tests assert the frozen headline metrics, so an accidental change to
the evaluation code fails the suite rather than silently altering a reported
result.
