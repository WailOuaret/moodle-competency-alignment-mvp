# Final package contents

**Archive:** `moodle_competency_mvp_FINAL_20260922.zip`
**Root folder inside the archive:** `moodle_competency_mvp_FINAL/`
**Checksum:** see the sidecar `moodle_competency_mvp_FINAL_20260922.zip.sha256`
**Contents:** 306 files + `MANIFEST.csv` · ~0.97 MB
**Built by:** `python scripts/build_final_package_zip.py`

The build is reproducible: entries are sorted and timestamps and permissions are
fixed, so two runs of the same tree produce a byte-identical archive.

The archive's checksum lives in a sidecar file rather than here, because this
document is itself inside the archive — quoting the hash here would invalidate
it on every edit. `MANIFEST.csv` inside the archive gives a SHA-256 for each
individual file.

> An older `moodle_competency_mvp_FINAL.zip` (2026-09-18) is still in the
> repository. It is **superseded** — it predates the `app/` validation
> interface, the five final reports, the supervisor demo package, the
> evidence-usefulness pilot and the unconstrained-comparison software. Use the
> dated archive above.

---

## Where to start when you open it

| Read this | For |
|---|---|
| `reports/RESULTS_ONE_PAGE.md` | the whole study in one page |
| `reports/FINAL_EXPERIMENTAL_RESULTS.md` | the full results report, 18 sections |
| `reports/FINAL_ERROR_ANALYSIS.md` | what goes wrong, with real examples |
| `reports/FINAL_LIMITATIONS.md` | what these numbers can and cannot support |
| `reports/FINAL_TEACHER_REVIEW.md` | teacher-validation status (honestly empty) |
| `reports/FINAL_VALIDATION_REPORT.md` | acceptance checks and artefact integrity |
| `docs/SUPERVISOR_DEMO.md` | 25-step demo script with anticipated questions |
| `docs/TEACHER_INTERFACE_GUIDE.md` | how to run the teacher review |
| `MANIFEST.csv` | path, size and SHA-256 of every file in the archive |

---

## Included

### Code
- `src/` — Python package (retrieval, LLM, evaluation, graph checks, review layers)
- `scripts/` — numbered pipeline scripts 01–28 plus helpers
- `tests/` — pytest suite, **435 tests**
- `app/` — **frozen-corpus teacher validation interface** (Home + 8 pages)
- `app.py`, `pages/` — runtime analysis interface
- `configs/`, `sql/`, `pyproject.toml`, `requirements.txt`, `requirements-lock.txt`

### Results
- `reports/metrics/` — all 12 metric JSON files
- `reports/tables/` — 23 CSV tables, including per-fragment, per-competency, error analysis, error examples, delta and ablation comparisons
- `reports/figures/` — 5 PNG figures
- `reports/reproducibility_manifest.json` — environment, model config, counts, SHA-256 of every artefact

### Explanations
- `reports/FINAL_*.md` — results, error analysis, teacher review, limitations, validation, completion audit
- `reports/RESULTS_ONE_PAGE.md`, `reports/SUPERVISOR_RESULTS_SUMMARY.md`, `reports/SUPERVISOR_DEMO_CHECKLIST.md`
- `reports/FINAL_INTERNSHIP_REPORT.md`, `reports/RESOURCE_LEVEL_EVALUATION.md`, `reports/MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md`, `reports/EVIDENCE_AWARE_ERROR_ANALYSIS.md`
- `docs/` — setup, pipeline, evaluation protocol, data dictionary, current status, demo, teacher guide, annotation guide, LTI feasibility

### Data
- `data/processed/` — 20 resources, 35 fragments, 13 competencies, aggregations, resource reference, graph warnings
- `data/gold/` — the 35-row human-reviewed fragment reference and catalogue
- `data/reviews/` — the 83-row evidence review (all rated) and the runtime researcher reviews
- `data/studies/` — evidence-usefulness pilot design and manifest
- `data/experiments/` — post-hoc graph ablation, Ollama checkpoints, unconstrained tasks
- `data/interim/` — the reproducibility inputs only: `bm25_candidates.jsonl`, `llm_tasks.jsonl`, `gemini_responses.jsonl`, `gemini_validated.jsonl` and their manifests
- `data/templates/`, `data/imports/`

---

## Intentionally excluded

Security decisions, not tidiness. The build **aborts** if any staged text file
matches a key, token or password pattern.

| Excluded | Why |
|---|---|
| `.env` | live secrets |
| `reports/site_info.json` | contains a Moodle `userprivateaccesskey` |
| `data/raw/` | API dumps may carry private Moodle fields |
| `reports/logs/`, `reports/api_raw/` | raw logs and dumps |
| `data/source/competency-tagging/` | external reference repository, not our work |
| `backups/`, `data/gold/annotation_backups/`, `data/reviews/evidence_review_backups/` | working state; duplicates the live files |
| `.venv/`, `__pycache__/`, `.pytest_cache/`, caches | build artefacts |
| `*.zip`, `*.mbz`, `*.log`, files over 5 MB | archives and bulk |

Verified on this build: **0 forbidden entries**, secret scan passed.

---

## Status of what is inside

| | |
|---|---|
| Pipeline, evaluation, error analysis, evidence review | COMPLETE |
| Resource-level evaluation, graph check + ablation | COMPLETE |
| Teacher validation interface (14 pages render) | COMPLETE |
| **Teacher decisions** | **WAITING_FOR_HUMAN — 0 of 34** |
| **Evidence-usefulness pilot** | **WAITING_FOR_HUMAN — designed, 0 responses** |
| Unconstrained all-13 comparison | OPTIONAL — software ready, not run |
| 435 tests · compileall · gold validator · 20/20 protected hashes | all pass |

**No acceptance rate is reported anywhere**, because no teacher has reviewed the
corpus. The two decisions on file are researcher decisions from the runtime app
and are labelled as such.

---

## Rebuilding

```bash
python scripts/build_final_package_zip.py                    # dated filename
python scripts/build_final_package_zip.py --out X.zip --force
```
