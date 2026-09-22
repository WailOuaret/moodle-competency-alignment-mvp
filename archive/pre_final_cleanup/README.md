# Moodle Learning Resource-to-Competency Alignment MVP

Research prototype that suggests UTC Génie informatique competencies for Moodle Pages and Quiz questions, shows exact textual evidence, and supports human ACCEPT / REJECT / MODIFY review.

**Researcher:** Wail Ouaret (ENSIA)  
**Supervision:** Marie-Hélène Abel and Le Ngoc Luyen (UTC / Heudiasyc / CNRS)

This repository is an existing experimental codebase. Do not rebuild completed extraction or checkpointed Gemini outputs. Do not overwrite frozen metric files.

## Project purpose

Teachers still map Moodle resources to competency frameworks largely by hand. This MVP tests a retrieve-then-generate pipeline:

1. **Function A — Resource → competencies.** Extract text, fragment it, retrieve BM25 Top-5 competencies, let a constrained LLM select among those candidates with an exact evidence quote, then aggregate to the resource.
2. **Function B — Competency → resources.** Inverse index over A. Not a second model.

## Research questions

- **RQ1.** To what extent can Moodle resources and activities be automatically aligned with a competency framework?
- **RQ2.** Do textual evidence spans help teachers verify alignment suggestions? *(teacher/supervisor validation still waiting)*
- **RQ3.1.** What is the role of BM25 candidate preselection?
- **RQ3.2.** Do minimal competency-graph constraints reduce incoherent or redundant predictions? *(answered only as a post-hoc ablation)*

## Architecture

```
Moodle 5.2 (content + imported 13 GI competencies)
    → REST + read-only SQL extraction (experiment)
Python package moodle_competency
    → normalize → fragment → BM25 Top-5 → constrained LLM
    → exact-substring evidence check → resource aggregation
    → optional post-hoc hierarchy warning / child-preference copy
Streamlit app (app.py)
    → Analyze Resource / Review / Competency → Resources / History / Research Results
```

Research experiment files live under `data/interim/`, `data/processed/`, `data/gold/`, and `reports/metrics/`. Runtime analyses live under `data/runtime/` and must not rewrite frozen Gemini outputs.

## Requirements

- Python 3.10+ (development: 3.12.3)
- Local virtualenv
- Optional: local Moodle 5.2 + PostgreSQL to **re-extract** content
- Optional: `GEMINI_API_KEY` for live Gemini
- Optional: Ollama with `mistral:latest` for the local backend
- No OCR. PDFs must be text-native.

See `requirements.txt` and `.env.example`. Never commit `.env`.

## Installation

```bash
cd ~/projects/moodle_competency_mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
cp .env.example .env
```

Fill Moodle / database / Gemini values only if you will call those services. Offline evaluation uses already extracted files.

## Moodle setup assumptions

- Moodle 5.2.1+ in Docker / WSL2 with PostgreSQL
- Courses `MVP-SW` and `MVP-DATA`
- Framework idnumber `UTC_GI_MVP_2026` (13 competencies: GI_C1–C3 and their children)
- Quiz questions are independent research resources (12 questions ≠ 2 Quiz activities)

Moodle does not need to be running to read frozen `data/processed/` files or to open Research Results.

## Run the experimental pipeline

Completed stages should not be rerun against frozen checkpoints. Historical order:

```bash
python scripts/01_extract_moodle_rest.py
python scripts/02_extract_moodle_sql.py
python scripts/03_normalize_resources.py
python scripts/04_normalize_competencies.py
python scripts/05_fragment_resources.py
python scripts/06_retrieve_bm25_candidates.py
python scripts/07_build_llm_tasks.py
# Gemini: resume only; never --restart
python scripts/10_run_gemini_alignments.py
python scripts/12_validate_manual_annotations.py --mode final
python scripts/15_evaluate_bm25.py
python scripts/16_evaluate_constrained_llm.py
python scripts/18_summarize_evidence_review.py
python scripts/19_analyze_errors.py
python scripts/22_evaluate_resource_level.py
python scripts/23_run_graph_checks.py
python scripts/20_write_reproducibility_manifest.py
python scripts/34_summarize_human_validation.py
python scripts/35_generate_final_figures.py
```

Optional Ollama (does not replace Gemini): `python scripts/29_run_ollama_constrained.py`

## Run tests

```bash
python -m pytest -q                                    # 435 passed
python -m compileall -q src scripts tests app
python scripts/ui_smoke_check.py                       # renders all 14 pages, network blocked
```

## Run the interfaces

There are **two** Streamlit apps over different data. Do not confuse them.

### 1. Frozen-corpus validation app — validates the published results

```bash
streamlit run app/Home.py
```

Browses the fixed 20-resource research corpus and collects teacher decisions on
the 34 predicted resource-competency mappings. Pages: course browser · resource
→ competencies · **teacher review** · competency → resources · evidence review ·
review progress · experiment results · evidence-usefulness pilot · validated
coverage. Guide: `docs/TEACHER_INTERFACE_GUIDE.md`.

Writes only `data/reviews/corpus_teacher_reviews.csv` (atomic, with timestamped
backups).

### 2. Runtime analysis app — analyses a new resource on demand

```bash
streamlit run app.py
```

Supported input: existing Moodle Page, existing Moodle Quiz question, pasted text, TXT, HTML, text-native PDF. Not part of the reported experiment; writes `data/reviews/teacher_reviews.csv`.

Reviewer roles for both: `researcher`, `teacher`, `supervisor`. **Researcher reviews are not teacher validation** and are reported separately.

Neither app writes to Moodle, to the human-reviewed reference, to the model output, or to any metric file.

## Directory structure

| Path | Role |
|---|---|
| `src/moodle_competency/` | Library (retrieval, LLM, evaluation, runtime UI helpers) |
| `scripts/` | Numbered pipeline and report scripts |
| `tests/` | pytest suite |
| `app/` | **Frozen-corpus validation interface** (Home + 8 pages) |
| `app.py`, `pages/` | Runtime analysis interface |
| `data/processed/` | Normalized resources, fragments, competencies, aggregations |
| `data/interim/` | BM25 candidates, Gemini checkpoints (do not rewrite) |
| `data/gold/` | Human-reviewed fragment reference |
| `data/reviews/` | Evidence ratings; runtime human reviews |
| `data/experiments/` | Post-hoc graph ablation; optional Ollama and unconstrained checkpoints |
| `data/studies/` | Evidence-usefulness pilot design (responses only when a human answers) |
| `data/runtime/` | Teacher-app analyses (isolated) |
| `data/templates/` | RQ2 validation form (empty until humans fill it) |
| `docs/` | Setup, protocol, demo, LTI feasibility, status |
| `reports/` | Metrics, tables, figures, internship report |

## Main metrics (frozen Gemini experiment)

Human-reviewed reference: 35 fragments, 38 labels.

| System | Headline |
|---|---|
| BM25 | Recall@1/3/5 = 0.6842 / 0.8684 / 0.9737; MRR = 0.8310; Top-1 micro F1 = 0.7123 |
| Gemini fragment | micro P/R/F1 = 0.7255 / 0.9737 / 0.8315; exact-set = 0.6286 |
| Gemini resource | micro P/R/F1 = 0.6765 / 0.9583 / 0.7931; exact-set = 0.45 |
| Evidence | 83/83 exact substrings; 78.3% pedagogically clear |
| Post-hoc hierarchy fragment F1 | 0.9367 (**ablation**, not original Gemini) |

**The trade-off, stated honestly:** against BM25 Top-1 the constrained LLM gains
**+0.290 recall** for **−0.017 precision** (micro F1 0.7123 → 0.8315). It does
*not* win on every measure. `llm_missed_gold_label = 0` — the single missed
reference label is a **retrieval** failure. 10 of 14 false positives are
zero-support **parent** competencies. Abstention rate is 0.0 but **untested**,
because the reference contains no `NONE` fragments.

Details: `reports/FINAL_EXPERIMENTAL_RESULTS.md`,
`reports/FINAL_ERROR_ANALYSIS.md`, `reports/RESULTS_ONE_PAGE.md`.

## Research-versus-runtime separation

| Frozen research | Runtime teacher app |
|---|---|
| 35-fragment Gemini experiment | New analyses under `data/runtime/` |
| `constrained_llm_metrics.json` | Does not update frozen metrics |
| Human-reviewed reference | Reviewer decisions in `teacher_reviews.csv` |
| Hierarchy ablation files under `data/experiments/` | UI can *display* a reconciled copy without rewriting Gemini |

## Status

**WAITING_FOR_HUMAN.** The measured pipeline, evaluation, error analysis,
evidence review, resource-level evaluation, graph ablation, interfaces, reports
and demo package are complete. **0 of 34** mappings have been reviewed by a
teacher, so **no acceptance rate is reported** — `null`, not `0.0`.

| Gate | Status |
|---|---|
| 1 · Human-reviewed fragment reference | COMPLETE — 35/35 |
| 2 · Pedagogical evidence 0/1/2 | COMPLETE — 83/83 |
| 3 · Teacher accept/reject/modify | **WAITING_FOR_HUMAN — 0 of 34** |
| 4 · Evidence-usefulness pilot | **WAITING_FOR_HUMAN — designed, 0 responses** |
| Optional all-13 unconstrained run | OPTIONAL — software ready, not authorized |

See `reports/FINAL_VALIDATION_REPORT.md` and `docs/CURRENT_STATUS.md`.

## Limitations

Small controlled corpus (38 reference labels — one label is 2.6 points of
recall); single-annotator reference with **no inter-annotator agreement** (not
independent blinded gold from scratch); the evidence review was by the same
person, so it is internal consistency rather than independent validation; **no
`NONE` fragments**, so abstention is untested; micro precision is substantially
a measure of granularity-convention agreement; Pages and quiz questions only;
local Moodle with a development-specific SQL fallback; hierarchy results are
**post-hoc** and reference-specific; **no significance testing**; no
teacher/supervisor validation yet; LTI not implemented; native Moodle plugin
deferred.

Full treatment: `reports/FINAL_LIMITATIONS.md`.

## Citation / reference paper

This MVP adapts:

> Ngoc Luyen Le, Marie-Hélène Abel, Bertrand Laforge. *From Learning Resources to Competencies: LLM-Based Tagging with Evidence and Graph Constraints.* 2026.

Internship report: `reports/FINAL_INTERNSHIP_REPORT.md`.
Supervisor demo: `docs/SUPERVISOR_DEMO.md` · `reports/SUPERVISOR_DEMO_CHECKLIST.md`.

## Secrets

Copy `.env.example` to `.env`. Never commit Moodle tokens, database passwords, Gemini keys, or `userprivateaccesskey` values.
