# Package contents

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

Two archives are produced, in `dist/`. Both are reproducible builds: entries are
sorted and timestamps and permissions fixed, so rebuilding an unchanged tree
yields an identical checksum.

---

## 1. `Moodle_Competency_Alignment_MVP_FINAL_PROJECT.zip`

The complete shareable project: code, the data needed to reproduce the reported
results, documentation and the delivery package.

| Property | Value |
|---|---|
| Files | 364 |
| Size | 1.36 MB |
| Root folder | `Moodle_Competency_Alignment_MVP/` |
| Checksum | `dist/Moodle_Competency_Alignment_MVP_FINAL_PROJECT.zip.sha256` |

**Contents**

| Path | Content |
|---|---|
| `FINAL_DELIVERY/` | The ten delivery documents plus figures, tables, metrics |
| `src/moodle_competency/` | Python package |
| `scripts/` | Numbered pipeline 01–28 and helpers |
| `tests/` | 435 tests |
| `app/`, `app.py`, `pages/` | Both Streamlit interfaces |
| `data/processed/`, `data/interim/` | Frozen corpus and experiment artefacts |
| `data/gold/`, `data/reviews/` | Human reference and review data |
| `data/studies/`, `data/experiments/` | Pilot design and optional experiments |
| `reports/` | Metrics, tables, figures, working reports |
| `docs/` | Technical documentation |
| `configs/`, `sql/` | Configuration and SQL |
| `README.md`, `requirements*.txt`, `pyproject.toml`, `.env.example` | Setup |

Sufficient to reproduce every reported result without Moodle access or an API
key.

---

## 2. `Moodle_Competency_Alignment_MVP_FINAL_DOCUMENTATION.zip`

The delivery documents with the evidence substantiating them, for a reader who
wants the report rather than the codebase.

| Property | Value |
|---|---|
| Files | 93 |
| Size | 0.46 MB |
| Root folder | `Moodle_Competency_Alignment_MVP_Documentation/` |
| Checksum | `dist/Moodle_Competency_Alignment_MVP_FINAL_DOCUMENTATION.zip.sha256` |

**Contents**

| Path | Content |
|---|---|
| `FINAL_DELIVERY/` | All ten documents |
| `reports/figures/` | 5 figures |
| `reports/tables/` | 23 result tables |
| `reports/metrics/` | 12 metric files |
| `reports/reproducibility_manifest.json` | Artefact checksums |
| `README.md` | Project overview |

Start with `FINAL_DELIVERY/00_READ_ME_FIRST.md`.

---

## Excluded from both archives

Security decisions, not tidiness. The build **aborts** if any staged text file
matches a credential pattern; both archives passed that scan.

| Excluded | Reason |
|---|---|
| `.env` | Live credentials |
| `reports/site_info.json` | Contains a Moodle `userprivateaccesskey` |
| `data/raw/` | API dumps may carry private Moodle fields |
| `reports/logs/`, `reports/api_raw/` | Raw logs and dumps |
| `data/source/` | External reference repository |
| `data/runtime/` | Runtime analyses, not part of the experiment |
| `archive/` | Superseded material and historical backups |
| Review and annotation backup folders | Working state; duplicates the live files |
| `.git/`, `.venv/`, caches, `*.zip` | Build and version-control artefacts |

`.env.example` is included: it holds variable names with no values.

---

## Format

Markdown is the authoritative format. No PDFs are included: the environment has
no Markdown-to-PDF renderer, and installing one was outside the scope of this
delivery. The documents render in any Markdown viewer or text editor.

---

## Status of the work inside

| Item | Status |
|---|---|
| Core research software | Complete |
| Documentation and delivery package | Complete |
| Reference annotation — 35 fragments | Complete |
| Evidence review — 83 quotations | Complete |
| **Teacher or supervisor validation** | **Pending — 0 of 34 mappings** |
| **Evidence-usefulness pilot** | **Pending — designed, no responses** |
| Unconstrained all-13 comparison | Optional — software ready, not run |
| LTI integration | Optional — future work |
| Native Moodle plugin | Deferred |

**No acceptance rate is reported anywhere**, because no teacher or supervisor has
reviewed the corpus. The two decisions on file are the researcher's own, recorded
through the runtime application, and are labelled as such.

---

## Verification

| Check | Result |
|---|---|
| Reference validator | PASSED, 35 of 35 |
| Test suite | 435 passed |
| Compilation | Succeeded |
| Interface render, network disabled | 14 of 14 pages |
| Protected artefact checksums | 21 of 21 unchanged |
| Secret scan on both archives | Passed |

---

## Rebuilding

`scripts/build_final_package_zip.py` produces a single combined archive with its
own `MANIFEST.csv`. The two `dist/` archives above were produced by the delivery
build described in `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md`.

Earlier packaging builds are retained in `archive/superseded_builds/`.
