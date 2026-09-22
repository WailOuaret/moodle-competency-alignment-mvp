# File naming and cleanup plan

**Moodle Learning Resource-to-Competency Alignment MVP**
**Date:** 22 September 2026

A record of which documentation files were kept, archived or left in place during
the final delivery pass, and why.

**Governing rule.** A file referenced by code, tests or the reproducibility
manifest was not moved or renamed, because doing so would break a checksum record
or a script path. Reference counts below were measured with a grep over `src/`,
`scripts/` and `tests/` before any file was touched.

**Nothing was deleted.** Superseded material was moved into `archive/`, where it
remains inspectable.

---

## Categories

| Category | Meaning |
|---|---|
| **KEEP** | Current, correct and referenced by the delivery |
| **KEEP (code-referenced)** | Referenced by code or the manifest; must not move |
| **ARCHIVE** | Superseded by a delivery document; moved, not deleted |
| **ARCHIVE (development)** | Planning or prompt material from development |
| **GENERATED_INTERNAL** | Produced by a script; stays where the script writes it |

---

## Root

| File | Category | Action |
|---|---|---|
| `README.md` | KEEP | Rewritten for the delivery |
| `FINAL_PACKAGE_CONTENTS.md` | KEEP | Describes the distribution archive |
| `CURSOR_FINAL_PROJECT_COMPLETION_PROMPT (1).md` | ARCHIVE (development) | → `archive/development_prompts/` |
| `moodle_competency_mvp_FINAL.zip` | ARCHIVE | Superseded build; → `archive/` |
| `moodle_competency_mvp_FINAL_20260922.zip` | KEEP | Current build, with checksum sidecar |
| `requirements*.txt`, `pyproject.toml`, `.env.example` | KEEP | Required to run |

The root prompt file is development material written to a coding assistant. It is
not research documentation and does not belong in a delivery, but it is part of
the project history and is therefore archived rather than removed.

---

## `docs/`

| File | Category | Action |
|---|---|---|
| `SETUP.md` | KEEP | Current |
| `PIPELINE.md` | KEEP | Current; updated |
| `EVALUATION.md` | KEEP | Current; updated |
| `DATA_DICTIONARY.md` | KEEP | Current; updated |
| `CURRENT_STATUS.md` | KEEP | Current; updated |
| `ANNOTATION_GUIDE.md` | KEEP | Annotation conventions |
| `HUMAN_VALIDATION_PROTOCOL.md` | KEEP | Validation protocol |
| `TEACHER_INTERFACE_GUIDE.md` | KEEP | Interface guide for a reviewer |
| `SUPERVISOR_DEMO.md` | KEEP | Extended demonstration script |
| `LTI_INTEGRATION_FEASIBILITY.md` | KEEP | Feasibility note for deferred work |
| `TEACHER_DEMO_GUIDE.md` | KEEP (code-referenced) | Hashed in the manifest |
| `TEACHER_RUNTIME_WORKFLOW.md` | KEEP (code-referenced) | Hashed in the manifest |
| `FINAL_COMPLETION_PLAN.md` | ARCHIVE (development) | → `archive/development_prompts/` |
| `PROJECT_COMPLETION_MASTER_PLAN.md` | ARCHIVE (development) | → `archive/development_prompts/` |
| `PROJECT_PLAN.md` | ARCHIVE | Superseded by the delivery report |
| `FINAL_PROJECT_STATUS.md` | ARCHIVE | Superseded by `CURRENT_STATUS.md` |
| `FINAL_DEMO_SCRIPT.md` | ARCHIVE | Superseded by `SUPERVISOR_DEMO.md` |
| `FINAL_SUPERVISOR_DEMO.md` | ARCHIVE | Superseded by `SUPERVISOR_DEMO.md` |
| `SUPERVISOR_QA.md` | ARCHIVE | Superseded by the demo guide's question section |
| `RQ2_VALIDATION_GUIDE.md` | ARCHIVE | Superseded by `HUMAN_VALIDATION_PROTOCOL.md` |
| `handoff/` | GENERATED_INTERNAL | Script output; left in place |

### Why two files were archived as development material

`FINAL_COMPLETION_PLAN.md` is a verbatim copy of a completion prompt written to a
coding assistant; its first line is an instruction, not a description of the
research. `PROJECT_COMPLETION_MASTER_PLAN.md` contains directives addressed to a
tool ("… must not decide these labels"). Both record real methodological
decisions — notably that the annotator, not the tool, produces the reference — so
they are preserved in `archive/development_prompts/` rather than discarded. They
are simply not delivery documents.

---

## `reports/`

| File | Category | Action |
|---|---|---|
| `FINAL_EXPERIMENTAL_RESULTS.md` | KEEP | Working record; superseded for delivery by `FINAL_DELIVERY/01` and `/03` |
| `FINAL_ERROR_ANALYSIS.md` | KEEP | Working record |
| `FINAL_TEACHER_REVIEW.md` | KEEP | Working record |
| `FINAL_LIMITATIONS.md` | KEEP | Working record |
| `FINAL_VALIDATION_REPORT.md` | KEEP | Acceptance record |
| `FINAL_COMPLETION_AUDIT.md` | KEEP | Audit record |
| `SUPERVISOR_RESULTS_SUMMARY.md` | KEEP | Supervisor summary |
| `RESULTS_ONE_PAGE.md` | KEEP | One-page summary; copied into the delivery |
| `SUPERVISOR_DEMO_CHECKLIST.md` | KEEP | Demonstration checklist; copied into the delivery |
| `competency_selection_rationale.md` | KEEP | Records why these 13 competencies |
| `FILE_NAMING_CLEANUP_PLAN.md` | KEEP | This file |
| `FINAL_INTERNSHIP_REPORT.md` | KEEP (code-referenced) | Hashed in the manifest |
| `FINAL_PROJECT_AUDIT.md` | KEEP (code-referenced) | Hashed in the manifest |
| `EVIDENCE_AWARE_ERROR_ANALYSIS.md` | KEEP (code-referenced) | Hashed in the manifest |
| `HUMAN_VALIDATION_SUMMARY.md` | KEEP (code-referenced) | Written by script 34 |
| `MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md` | KEEP (code-referenced) | Written by script 23 |
| `RESOURCE_LEVEL_EVALUATION.md` | KEEP (code-referenced) | Written by script 22 |
| `FINAL_REPRODUCIBILITY_CHECK.md` | ARCHIVE | Superseded by `FINAL_VALIDATION_REPORT.md` |
| `metrics/`, `tables/`, `figures/` | GENERATED_INTERNAL | Script output |
| `api_raw/`, `sql_raw/`, `logs/` | GENERATED_INTERNAL | Extraction records; excluded from distribution |

### On the report filenames

Several reports in `reports/` are written by numbered scripts and hashed in
`reports/reproducibility_manifest.json`. Renaming them to shorter delivery-style
names would break the manifest and the scripts that write them, and would
invalidate a provenance record for no functional gain.

The resolution is to leave them in place as the **working record**, and to present
the delivery through `FINAL_DELIVERY/`, whose files already carry clean,
ordered names:

| Delivery name | Role |
|---|---|
| `01_FINAL_TECHNICAL_REPORT.md` | Technical report |
| `02_METHODOLOGY.md` | Methodology |
| `03_RESULTS_AND_ANALYSIS.md` | Results and analysis |
| `04_SYSTEM_ARCHITECTURE.md` | Architecture |
| `05_REPRODUCIBILITY_GUIDE.md` | Reproducibility |
| `06_DATA_AND_EXPERIMENT_DESCRIPTION.md` | Data description |
| `07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md` | Demonstration and testing |
| `08_LIMITATIONS_AND_FUTURE_WORK.md` | Limitations and future work |
| `09_PROJECT_FILE_GUIDE.md` | Repository guide |

A reader opening the project sees the ordered delivery package; a reader auditing
provenance finds the working record intact under `reports/`.

---

## `scripts/`

No script was renamed. The numbered sequence is referenced throughout the
documentation and in the manifest, and the numbering records the execution order.

Scripts whose only purpose was generating prose from templates were reviewed for
removal. `35_generate_final_figures.py` was **kept**: it regenerates the five
figures from current metric files and is therefore a genuine reproducibility
tool, not a one-off text generator.

---

## `archive/`

Created during this pass. Nothing here is required to run or understand the
project; it preserves history.

| Directory | Content | Published to GitHub |
|---|---|---|
| `pre_final_cleanup/` | 23 documentation files as they stood before the final editorial pass | yes |
| `documentation_history/` | Superseded report and documentation drafts | yes — current reports link to these |
| `development_prompts/` | Planning and prompt material written to a coding assistant | **no** — git-ignored |
| `superseded_builds/` | Earlier packaging archives | **no** — git-ignored |
| `experiment_backups/` | Phase-2 model checkpoint backups | **no** — git-ignored |

The three unpublished directories are retained locally and in the private
machine backup. They are excluded from the public repository because they are
development scaffolding and binary archives rather than research documentation;
excluding them keeps the published history readable without discarding it.

A consequence worth noting: `reports/frozen_manifest_strengthening.json` and the
table above both reference `CURSOR_FINAL_PROJECT_COMPLETION_PROMPT (1).md` by
name. That file is archived and not published. The references remain because
altering a historical checksum manifest would corrupt a provenance record.

---

## Summary

| Action | Count |
|---|---:|
| Kept in place | 28 |
| Kept, code-referenced and therefore immovable | 8 |
| Archived as superseded documentation | 7 |
| Archived as development material | 3 |
| Deleted | **0** |
