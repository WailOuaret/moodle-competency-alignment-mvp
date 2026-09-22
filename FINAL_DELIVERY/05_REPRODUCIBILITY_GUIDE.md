# Reproducibility Guide

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

All operational commands for the project are collected here. The report and
analysis documents contain no command-line material.

---

## 1. Environment

| Component | Version |
|---|---|
| Python | 3.12.3 |
| Package | `moodle-competency-mvp` 0.1.0, installed editable |
| Platform of record | WSL2 on Linux 6.6.87 |
| Moodle | 5.2.1+ (Build 20260722), local instance |

Key pinned dependencies: `rank-bm25` 0.2.2, `google-genai` 2.14.0,
`scikit-learn` 1.9.0, `streamlit` 1.64.0, `beautifulsoup4` 4.15.0,
`requests` 2.34.2, `matplotlib` 3.11.2, `pytest` 9.1.1. The complete set is in
`requirements-lock.txt`.

---

## 2. Setup

```bash
cd ~/projects/moodle_competency_mvp

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-lock.txt     # exact pinned versions
pip install -e .                          # editable install of the package
```

`requirements.txt` holds loose ranges for development. Use
`requirements-lock.txt` to reproduce the reported results.

> In this environment `python` is not on `PATH` outside the virtual environment.
> Either activate the environment as above, or prefix commands with
> `.venv/bin/python`.

### Credentials

```bash
cp .env.example .env
```

Then edit `.env`. It is excluded from version control and from every
distribution archive.

| Variable | Purpose |
|---|---|
| `MOODLE_BASE_URL` | Moodle instance URL |
| `MOODLE_TOKEN` | Web-service token |
| `MOODLE_SERVICE_SHORTNAME` | External service short name |
| `MOODLE_SW_COURSE_ID`, `MOODLE_DATA_COURSE_ID` | Course identifiers |
| `GEMINI_API_KEY` | Required only to run a new model experiment |

Reproducing the **reported** results requires no Moodle access and no API key:
the frozen artefacts are in the repository. Credentials are needed only to
extract a new corpus or to run a new model condition.

---

## 3. Verification

Four checks confirm the repository is intact. They are read-only and safe to run
at any time.

```bash
source .venv/bin/activate

python scripts/12_validate_manual_annotations.py --mode final
python -m pytest -q
python -m compileall -q src scripts tests app
python scripts/ui_smoke_check.py
```

Expected:

| Check | Expected result |
|---|---|
| Reference validator | `Status: PASSED`, 35 of 35 |
| Test suite | `435 passed` |
| Compilation | Silent |
| Interface render | `UI smoke check: OK`, 14 pages |

The render check patches outbound sockets to raise, so any page attempting a
network call fails rather than succeeding silently.

### Checksum verification

```bash
python scripts/verify_frozen.py
python scripts/20_write_reproducibility_manifest.py
```

The manifest records SHA-256 for every artefact, the Python version, pinned
dependency versions, the model identifier, temperature, candidate count,
selection limit and corpus counts. Artefacts that do not exist are recorded as
null rather than with a placeholder.

---

## 4. Running the interfaces

### Frozen-corpus validation interface

```bash
source .venv/bin/activate
streamlit run app/Home.py
```

Opens at <http://localhost:8501>. This reviews the fixed 20-resource corpus
behind the reported results. It makes no model calls and writes only
`data/reviews/corpus_teacher_reviews.csv`.

See `07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md` for the review procedure.

### Runtime analysis interface

```bash
streamlit run app.py
```

Analyses an arbitrary new Moodle resource on demand. Requires credentials, makes
live model calls, and is **not** part of the reported experiment. Its output is
isolated in `data/runtime/`.

---

## 5. Pipeline stages

The pipeline has already been run and its outputs are frozen. The sequence is
recorded for understanding and for re-running on a new corpus.

| Script | Stage | Output |
|---|---|---|
| `01_extract_moodle_rest.py` | REST extraction | `data/raw/api/` |
| `02_extract_moodle_sql.py` | SQL extraction | `data/raw/sql/` |
| `03_normalize_resources.py` | Normalisation | `resources.jsonl` |
| `04_normalize_competencies.py` | Framework normalisation | `competencies.jsonl` |
| `05_fragment_resources.py` | Fragmentation | `fragments.jsonl` |
| `06_retrieve_bm25_candidates.py` | Retrieval | `bm25_candidates.jsonl` |
| `07_build_llm_tasks.py` | Task assembly | `llm_tasks.jsonl` |
| `08_validate_response_pipeline.py` | Validator self-test | — |
| `09_test_gemini_alignment.py` | Single-task pilot | `gemini_pilot_*` |
| `10_run_gemini_alignments.py` | Model run | `gemini_validated.jsonl` |
| `11_build_manual_annotation_template.py` | Annotation sheet | annotation CSV |
| `12_validate_manual_annotations.py` | Reference validation | validation report |
| `13_aggregate_predictions.py` | Resource aggregation | `resource_predictions.jsonl` |
| `14_build_competency_resource_index.py` | Inverse index | `competency_resource_index.jsonl` |
| `15_evaluate_bm25.py` | Retrieval evaluation | `bm25_metrics.json` |
| `16_evaluate_constrained_llm.py` | Model evaluation | `constrained_llm_metrics.json` |
| `17_prepare_evidence_review.py` | Evidence sheet | `evidence_review.csv` |
| `18_summarize_evidence_review.py` | Evidence summary | `evidence_review_summary.json` |
| `19_analyze_errors.py` | Error analysis | `error_summary.json` |
| `20_write_reproducibility_manifest.py` | Manifest | `reproducibility_manifest.json` |
| `22_evaluate_resource_level.py` | Resource evaluation | `resource_level_metrics.json` |
| `23_run_graph_checks.py` | Hierarchy checks | `graph_warnings.jsonl` |
| `27_prepare_teacher_study.py` | Pilot design | `data/studies/` |
| `28_summarize_teacher_reviews.py` | Review summary | `teacher_review_summary.json` |

### Human checkpoints

Two stages require a person, and the pipeline will not synthesise either.

```bash
python scripts/manual_annotate_fragments.py        # reference annotation — complete
python scripts/review_evidence_pedagogically.py    # evidence rating — complete
```

Both tools present one item at a time, save after every decision, resume after
interruption, write timestamped backups, and never suggest an answer.

---

## 6. Regenerating derived results

Derived results may be regenerated. Frozen inputs may not.

```bash
source .venv/bin/activate

python scripts/15_evaluate_bm25.py
python scripts/16_evaluate_constrained_llm.py
python scripts/18_summarize_evidence_review.py
python scripts/19_analyze_errors.py
python scripts/22_evaluate_resource_level.py
python scripts/23_run_graph_checks.py --simulate-child-preference
python scripts/28_summarize_teacher_reviews.py
python scripts/20_write_reproducibility_manifest.py
```

Each verifies that protected checksums are unchanged before and after running,
and aborts if any differ. Regeneration is deterministic: re-running the evidence
summary reproduces its output byte for byte, which was verified.

### What must not be regenerated

| Artefact | Reason |
|---|---|
| `data/interim/gemini_responses.jsonl` | Historical model output; a third-party API is not stable over time |
| `data/interim/gemini_validated.jsonl` | Derived from the above |
| `data/gold/manual_fragment_annotations.csv` | Human work |
| `data/reviews/evidence_review.csv` | Human work |
| `data/processed/*.jsonl` | Frozen corpus definition |
| `data/interim/bm25_candidates.jsonl` | Frozen retrieval state |

The model runner offers no restart mechanism; it resumes from checkpoints only.

---

## 7. Optional experiments

### Unconstrained all-13 comparison — not run

This condition removes the retrieval restriction so the effect of candidate
restriction can be measured. The software is implemented and audited; the live
run has not been authorised.

```bash
python scripts/24_build_unconstrained_tasks.py          # no API call
python scripts/25_run_unconstrained_gemini.py --dry-run # no API call
```

The run spends API quota and refuses to execute without explicit authorisation:

```bash
python scripts/25_run_unconstrained_gemini.py --i-authorize-the-unconstrained-experiment
python scripts/26_evaluate_unconstrained_gemini.py
```

Everything is written under `data/experiments/`. The evaluator refuses to score a
run that has not occurred and estimates nothing in its place.

### Local model comparison

```bash
python scripts/29_run_ollama_constrained.py
python scripts/30_evaluate_ollama_constrained.py
```

A post-hoc comparison with a local model, isolated in `data/experiments/` and
never merged into the core metric files.

---

## 8. Building distributions

```bash
python scripts/build_final_package_zip.py
```

Produces a reproducible archive: entries sorted, timestamps and permissions
fixed, so two runs of the same tree yield an identical checksum. The build scans
every staged text file for key, token and password patterns and **aborts** on a
match. `.env`, `reports/site_info.json` (which contains a private access key),
`data/raw/`, logs and backups are excluded by rule.

---

## 9. Troubleshooting

| Symptom | Cause and remedy |
|---|---|
| `python: command not found` | The virtual environment is not active. Run `source .venv/bin/activate` or use `.venv/bin/python`. |
| `MOODLE_TOKEN is not configured` | `.env` is missing or incomplete. Not required to reproduce reported results. |
| `GEMINI_API_KEY is empty` | Only needed for a new model run. |
| A script reports protected files changed | A frozen artefact was modified. Restore it from the archive; do not proceed. |
| Reference validator fails | The annotation file was edited. Restore from `data/gold/annotation_backups/`. |
| `REFUSED: this experiment is optional` | Correct behaviour. The unconstrained run requires an explicit authorisation flag. |
| Streamlit port in use | `streamlit run app/Home.py --server.port 8502`. |
| Interface shows no teacher decisions | Correct. None has been recorded. |

---

## 10. Verified state

Recorded 22 September 2026:

| Check | Result |
|---|---|
| Reference validator | PASSED, 35 of 35 |
| Test suite | 435 passed |
| Compilation | Succeeded |
| Interface render, network disabled | 14 of 14 pages |
| Protected artefact checksums | 21 of 21 unchanged |
| Secrets in generated outputs | None |
| Derived summary determinism | Byte-identical on regeneration |
