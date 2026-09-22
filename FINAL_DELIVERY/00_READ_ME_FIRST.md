# Read me first

# Moodle Learning Resource-to-Competency Alignment

## Final delivery package

**Author:** Wail Ouaret
**Supervisors:** Marie-Hélène Abel, Le Ngoc Luyen
**Institution:** Université de Technologie de Compiègne — Heudiasyc (UMR 7253, CNRS)
**Date:** 22 September 2026

---

## What this project does

Moodle courses accumulate material that is never linked to the competencies a
programme claims to teach. This project tests whether lexical retrieval combined
with a constrained language model can propose those links in a form a teacher can
**verify** — each proposal accompanied by a quotation taken verbatim from the
source material.

The emphasis on verification rather than accuracy alone shapes the whole design. A
teacher who cannot see why a competency was assigned has no basis for accepting or
rejecting it.

---

## The result in one table

Evaluated on 35 fragments against 38 reference labels produced by one annotator:

| Metric | BM25 Top-1 | BM25 Top-5 + constrained model | Difference |
|---|---:|---:|---:|
| Micro precision | 0.7429 | 0.7255 | −0.0174 |
| Micro recall | 0.6842 | 0.9737 | +0.2895 |
| Micro F1 | 0.7123 | 0.8315 | +0.1191 |

The constrained system trades a small amount of precision for a substantially
higher recall. It is not uniformly better.

**Three findings shape the interpretation.**

1. **In the constrained Top-5 condition, the only missed reference label was
   absent from the candidate set.** The model selected every reference label that
   was available among its candidates — all 37. What it would select from the
   full 13-competency space has not been measured.
2. **Precision errors are dominated by parent-child granularity redundancy.**
   Ten of the 14 false positives are top-level competencies predicted alongside
   their own correct child; the remaining four are topical confusions unrelated
   to hierarchy. The annotation convention labels only at child level, and that
   convention was never stated in the prompt.
3. **Exact evidence prevents fabrication but not weak reasoning.** All 83
   quotations are exact substrings of their source; a manual review judged 78.3 %
   to clearly support their competency. The constraint's value is that inadequate
   reasoning becomes visible.

---

## Status

| Item | Status |
|---|---|
| Core research software | **Complete** |
| Documentation | **Complete** |
| Final delivery package | **Complete** |
| Reference annotation — 35 fragments | **Complete** |
| Evidence review — 83 quotations | **Complete** |
| **Supervisor or teacher validation** | **Pending — 0 of 34 mappings** |
| **Evidence-usefulness pilot** | **Pending — designed, no responses** |
| Unconstrained all-13 comparison | Optional — software ready, not run |
| LTI integration | Optional — future work |
| Native Moodle plugin | Deferred |

**No teacher or supervisor has reviewed this system.** No acceptance, edit or
rejection rate appears anywhere in this package, because none exists. The two
decisions recorded in the repository are the researcher's own, made through a
separate runtime application, and are labelled as such.

---

## Reading order

**If you have ten minutes** — read this page, then
`03_RESULTS_AND_ANALYSIS.md` sections 4 to 7.

**If you are evaluating the work** — read in order:

| Order | Document | Why |
|---:|---|---|
| 1 | `01_FINAL_TECHNICAL_REPORT.md` | The complete account |
| 2 | `03_RESULTS_AND_ANALYSIS.md` | Results with the analysis behind them |
| 3 | `08_LIMITATIONS_AND_FUTURE_WORK.md` | What the results do not support |
| 4 | `02_METHODOLOGY.md` | How each figure was produced |

**If you will run or extend the system:**

| Order | Document |
|---|---|
| 1 | `04_SYSTEM_ARCHITECTURE.md` |
| 2 | `05_REPRODUCIBILITY_GUIDE.md` |
| 3 | `06_DATA_AND_EXPERIMENT_DESCRIPTION.md` |
| 4 | `09_PROJECT_FILE_GUIDE.md` |

**If you will demonstrate or validate it** — `07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md`.

---

## Contents

| Document | Content |
|---|---|
| `00_READ_ME_FIRST.md` | This page |
| `01_FINAL_TECHNICAL_REPORT.md` | Full technical report |
| `02_METHODOLOGY.md` | Methodology in reproducible detail |
| `03_RESULTS_AND_ANALYSIS.md` | Results, tables and analysis |
| `04_SYSTEM_ARCHITECTURE.md` | Architecture and modules |
| `05_REPRODUCIBILITY_GUIDE.md` | Environment and all commands |
| `06_DATA_AND_EXPERIMENT_DESCRIPTION.md` | Dataset inventory |
| `07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md` | Demonstration and validation |
| `08_LIMITATIONS_AND_FUTURE_WORK.md` | Limitations and future work |
| `09_PROJECT_FILE_GUIDE.md` | Repository guide |
| `figures/` | Figures cited in the reports |
| `tables/` | Result tables |
| `metrics/` | Metric files substantiating every number |
| `demo/` | Demonstration checklist |
| `project_manifest/` | Checksums and environment record |

### Format

**Markdown is the authoritative format for this package.** No PDF versions are
included: the environment has no Markdown-to-PDF renderer (no pandoc, WeasyPrint,
wkhtmltopdf or LibreOffice), and installing one was outside the scope of this
delivery. The documents render correctly in any Markdown viewer, in a text
editor, and on GitHub.

If PDFs are required, `pandoc --pdf-engine=xelatex 01_FINAL_TECHNICAL_REPORT.md
-o 01_FINAL_TECHNICAL_REPORT.pdf` will produce them once pandoc and a LaTeX
engine are installed.

Every figure quoted in these documents can be traced to a file in `metrics/` or
`tables/`.

---

## Running the system

```bash
cd ~/projects/moodle_competency_mvp
source .venv/bin/activate
streamlit run app/Home.py
```

Reproducing the reported results requires no Moodle access and no API key: the
frozen artefacts are in the repository. Full instructions are in
`05_REPRODUCIBILITY_GUIDE.md`.

---

## Verification

Recorded 22 September 2026:

| Check | Result |
|---|---|
| Reference annotation validator | PASSED, 35 of 35 |
| Test suite | 435 passed |
| Compilation | Succeeded |
| Interface render, network disabled | 14 of 14 pages |
| Protected artefact checksums | 21 of 21 unchanged |
| Secrets in generated outputs | None |

---

## Terminology

Two points of wording are maintained throughout, because the distinctions matter.

**"Human-reviewed reference annotations"**, not "gold standard". One annotator
produced all 38 labels; there was no second annotator and no inter-annotator
agreement was measured. Every score is an agreement rate with one person's
judgement.

**"Post-hoc ablation"** for the hierarchy experiment. It raises micro F1 to 0.9367
but was designed after the errors were observed and exploits a property of this
reference. It diagnoses the error; it is not a validated technique and is never
presented as part of the original system.

---

## What would most improve this work

The interface for collecting teacher decisions exists, and no decision has been
recorded. That is the largest gap between what has been built and what is known,
and it takes 30 to 45 minutes to close. The procedure is in
`07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md`, Part B.
