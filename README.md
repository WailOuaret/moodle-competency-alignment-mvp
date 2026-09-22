# Moodle Learning Resource-to-Competency Alignment MVP

Aligning Moodle learning resources with a formal competency framework, using
lexical retrieval and a candidate-constrained language model, with every
proposal justified by a verbatim quotation from the source material.

**Researcher:** Wail Ouaret — National Higher School of Artificial Intelligence (ENSIA)
**Supervisors:** Marie-Hélène Abel, Le Ngoc Luyen
**Institution:** Université de Technologie de Compiègne — Heudiasyc (UMR 7253, CNRS)

---

## Overview

Moodle courses accumulate material that is never linked to the competencies a
programme claims to teach. Manual tagging does not scale, and an automatically
assigned tag that a teacher cannot verify is of limited use.

This project tests whether retrieval combined with a constrained language model
can propose those links in a form a teacher can **check**. For each unit of
course material, BM25 retrieves the five nearest competencies; a language model
selects at most three of them and must support each selection with an exact
substring of the source text. A validator rejects any response that invents an
identifier or paraphrases its evidence.

Two directions are supported:

- **Resource → competencies.** What does this material teach?
- **Competency → resources.** Which material covers this competency? An inverse
  index over the first, not a second model.

---

## Research objectives

1. Determine whether lexical retrieval can restrict the competency search space
   without excluding the correct competency.
2. Determine whether requiring verbatim evidence produces justifications a human
   reviewer finds adequate.
3. Characterise the failure modes and attribute them to retrieval or to the
   model.
4. Present the alignments in both directions in a form suitable for teacher
   validation.

---

## Scope

**Included.** A local Moodle instance; two courses; Pages and quiz questions; a
13-competency subset of the UTC *Génie Informatique* framework; extraction,
normalisation and fragmentation; BM25 retrieval; constrained model selection;
exact-evidence validation; resource aggregation; a human-reviewed reference;
fragment- and resource-level evaluation; error analysis; manual evidence review;
a hierarchy consistency check; a teacher validation interface.

**Deferred.** A native Moodle plugin; write-back into Moodle; LTI; PDF, slide,
video and OCR ingestion; assignments and rubrics; the full ROME 4.0 framework;
graph visualisation; recommendation and learning paths; curriculum analytics;
relation-type classification; fine-tuning; institution-wide deployment.

The scope was reduced on supervisory guidance, to complete and measure one path
rather than partially build several.

---

## Methodology

```
Moodle 5.2 (REST + SQL)
   → normalisation            20 resources
   → fragmentation            35 fragments
   → BM25 retrieval           Top-5 candidates per fragment
   → constrained selection    gemini-3.5-flash, T=0, at most 3 selections
   → evidence validation      exact substring required
   → resource aggregation     34 resource-competency mappings
   → hierarchy checks         warnings only
   → teacher validation interface
```

Retrieval and selection are kept as separate stages so that a missed label can
be attributed to one or the other: the candidate set is recorded for every
fragment, which makes the attribution decidable rather than a matter of opinion.

Full detail: `FINAL_DELIVERY/02_METHODOLOGY.md`.

---

## Dataset

| Item | Count |
|---|---:|
| Courses | 2 (`MVP-SW`, `MVP-DATA`) |
| Moodle Pages | 8 |
| Quizzes | 2 |
| Quiz questions (independent resources) | 12 |
| Normalised resources | 20 |
| Fragments | 35 (23 page chunks, 12 quiz questions) |
| UTC GI competencies | 13 (3 parents, 10 children) |
| Reference labels | 38 |
| Multi-label fragments | 3 |
| Ambiguous fragments | 1 |
| Fragments with no applicable competency | 0 |

Quiz questions are treated as independent resources, because a quiz rarely
assesses a single competency while a question usually does.

The reference annotations were produced by **one annotator**. There was no
second annotator and no inter-annotator agreement was measured. They are
referred to throughout as **human-reviewed reference annotations**, not as a
gold standard.

---

## Main results

| Metric | BM25 Top-1 | BM25 Top-5 + constrained model | Difference |
|---|---:|---:|---:|
| Micro precision | 0.7429 | 0.7255 | −0.0174 |
| Micro recall | 0.6842 | 0.9737 | +0.2895 |
| Micro F1 | 0.7123 | 0.8315 | +0.1191 |

BM25 Recall@1/@3/@5 = 0.6842 / 0.8684 / 0.9737 · MRR = 0.8310
Macro F1 = 0.6958 over all 13 labels, 0.9046 over the 10 with reference support
Exact-set match 0.6286 · coverage 1.0 · 1.46 labels per fragment
Resource level: micro P/R/F1 = 0.6765 / 0.9583 / 0.7931, exact-set 0.45
Evidence: 83 of 83 exact substrings; 78.3 % judged clearly supporting

**Three findings.**

- **In the constrained Top-5 condition, the only missed reference label was
  absent from the candidate set.** The model missed no reference label that was
  available among its candidates (`llm_missed_gold_label = 0`). How it would
  behave with all 13 competencies available has not been measured.
- **Precision errors are dominated by parent-child granularity redundancy.**
  Ten of 14 false positives are top-level competencies predicted alongside their
  correct child; the other four are topical confusions. The annotation convention
  labels only at child level, and that was never stated in the prompt.
- **Exact evidence prevents fabrication, not weak reasoning.** All quotations are
  exact substrings; 21.7 % were nonetheless judged partial or inadequate.

The constrained system trades precision for recall and is not uniformly better.
Abstention is **untested**: no fragment in this corpus has "no competency" as its
correct answer.

A post-hoc hierarchy ablation raises fragment F1 to 0.9367, but it was designed
after the errors were observed and is not part of the original system.

---

## System architecture

Each stage writes a durable artefact, so any stage can be inspected
independently and a failure attributed to the stage that produced it. Human
input is never synthesised; optional experiments are isolated under
`data/experiments/` and cannot overwrite a core artefact.

Full detail: `FINAL_DELIVERY/04_SYSTEM_ARCHITECTURE.md`.

---

## Requirements

- Python 3.12
- No Moodle access or API key is required to reproduce the reported results
- Credentials are needed only to extract a new corpus or run a new model
  experiment

Pinned versions in `requirements-lock.txt`; loose ranges in `requirements.txt`.

---

## Installation

```bash
git clone https://github.com/WailOuaret/moodle-competency-alignment-mvp.git
cd moodle-competency-alignment-mvp

python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

Use `requirements-lock.txt` for the exact versions behind the reported results.

See `docs/QUICKSTART.md` for a step-by-step walkthrough.

---

## Running the research validation interface

```bash
streamlit run app/Home.py
```

Browses the fixed 20-resource corpus behind the published results, shows each
suggestion with its evidence quotation and BM25 rank, and collects accept /
reject / modify decisions. Makes **no** model calls, and writes only
`data/reviews/corpus_teacher_reviews.csv`.

Guide: `docs/TEACHER_INTERFACE_GUIDE.md`.

---

## Running the runtime analysis interface

```bash
streamlit run app.py
```

Analyses an arbitrary new Moodle resource on demand. Requires credentials in
`.env`, makes live model calls, and is **not** part of the reported experiment.
Its output is isolated in `data/runtime/`.

---

## Running tests

```bash
python -m pytest -q                              # 435 passed
python -m compileall -q src scripts tests app
python scripts/ui_smoke_check.py                 # 14 pages, network disabled
```

No test contacts an external API.

> `scripts/collect_handoff_facts.py` reports a separate figure (221). That is a
> **pre-existing regression subset** covering 32 of 39 test files, not the
> project total. The authoritative count comes from `python -m pytest -q`.

---

## Validating reference annotations

```bash
python scripts/12_validate_manual_annotations.py --mode final
```

Expect `Status: PASSED`, 35 of 35, with no missing, unknown, duplicate or
incomplete rows and no drift between annotated text and source.

---

## Reproducing evaluation outputs

```bash
python scripts/15_evaluate_bm25.py
python scripts/16_evaluate_constrained_llm.py
python scripts/19_analyze_errors.py
python scripts/22_evaluate_resource_level.py
python scripts/23_run_graph_checks.py --simulate-child-preference
python scripts/20_write_reproducibility_manifest.py
```

Each verifies that protected checksums are unchanged before and after running
and aborts on any change.

Completed extraction and checkpointed model output are frozen experimental
artefacts and must not be regenerated: the model runner offers no restart
mechanism and resumes from checkpoints only.

Full instructions: `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md`.

---

## Project structure

| Path | Content |
|---|---|
| `FINAL_DELIVERY/` | Delivery package — **start here** |
| `src/moodle_competency/` | Python package |
| `scripts/` | Numbered pipeline, 01–28 |
| `app/` | Research validation interface |
| `app.py`, `pages/` | Runtime analysis interface |
| `tests/` | 435 tests |
| `data/processed/`, `data/interim/` | Frozen corpus and experiment artefacts |
| `data/gold/`, `data/reviews/` | Human reference and review data |
| `data/experiments/` | Post-hoc and optional experiments, isolated |
| `reports/` | Metrics, tables, figures, reports |
| `docs/` | Technical documentation |
| `archive/` | Superseded documentation, retained for provenance |

File-by-file detail: `docs/PROJECT_STRUCTURE.md`.

---

## Important files

| File | Why it matters |
|---|---|
| `data/gold/manual_fragment_annotations.csv` | The reference — 35 rows, 38 labels |
| `data/interim/gemini_validated.jsonl` | The model output the results are computed from |
| `data/interim/bm25_candidates.jsonl` | The candidate sets; makes error attribution decidable |
| `data/reviews/evidence_review.csv` | 83 evidence quotations with human ratings |
| `reports/metrics/constrained_llm_metrics.json` | Headline results |
| `reports/PROTECTED_ARTIFACT_CANONICAL_LIST.md` | The 21 protected artefacts and their checksums |
| `reports/reproducibility_manifest.json` | Environment, configuration, all checksums |

---

## Documentation

| Document | Content |
|---|---|
| `FINAL_DELIVERY/00_READ_ME_FIRST.md` | Orientation and reading order |
| `FINAL_DELIVERY/01_FINAL_TECHNICAL_REPORT.md` | Full technical report |
| `FINAL_DELIVERY/02_METHODOLOGY.md` | Methodology |
| `FINAL_DELIVERY/03_RESULTS_AND_ANALYSIS.md` | Results and analysis |
| `FINAL_DELIVERY/04_SYSTEM_ARCHITECTURE.md` | Architecture |
| `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md` | Environment and commands |
| `FINAL_DELIVERY/06_DATA_AND_EXPERIMENT_DESCRIPTION.md` | Dataset inventory |
| `FINAL_DELIVERY/07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md` | Demonstration and validation |
| `FINAL_DELIVERY/08_LIMITATIONS_AND_FUTURE_WORK.md` | Limitations and future work |
| `docs/QUICKSTART.md` | Setup walkthrough |
| `docs/PROJECT_STRUCTURE.md` | Every important file and script |
| `docs/DATA_DICTIONARY.md` | Field-level schema for every dataset |
| `docs/DEVELOPMENT.md` | Conventions for extending the project |

---

## Current status

| Item | Status |
|---|---|
| Core research software | COMPLETE |
| Core evaluation | COMPLETE |
| Documentation | COMPLETE |
| Reference annotation — 35 fragments | COMPLETE |
| Evidence review — 83 quotations | COMPLETE |
| **Supervisor / teacher validation** | **WAITING_FOR_HUMAN — 0 of 34 mappings** |
| **Evidence-usefulness pilot** | **WAITING_FOR_HUMAN — designed, no responses** |
| Unconstrained all-13 experiment | OPTIONAL / NOT RUN |
| LTI integration | OPTIONAL / FUTURE |
| Native Moodle plugin | DEFERRED |

**No acceptance rate is reported anywhere**, because no teacher or supervisor has
reviewed the corpus. The summary records null rather than zero, since zero would
assert that reviewers accepted nothing. Two decisions exist in the repository;
both are the researcher's own, recorded through the runtime interface, and are
reported separately.

Last verified 22 September 2026: validator PASSED 35/35 · 435 tests passed ·
compile clean · 14/14 pages rendered · 21/21 protected artefacts unchanged.

---

## Limitations

Small controlled corpus — with 38 reference labels, one label is worth 2.6 points
of recall. Single annotator, **no inter-annotator agreement**. The evidence review
was performed by the same person, so it is internal consistency rather than
independent validation. No `NONE` fragments, so abstention is untested. Micro
precision is substantially a measure of agreement with a granularity convention.
Pages and quiz questions only. Local Moodle, with a development-specific SQL route
for quiz question text. The hierarchy result is **post-hoc** and
reference-specific. Confidence scores are uncalibrated. **No significance
testing** — the design does not support it.

Full treatment: `FINAL_DELIVERY/08_LIMITATIONS_AND_FUTURE_WORK.md`.

---

## Research context

Carried out as internship research at UTC / Heudiasyc (UMR 7253, CNRS), adapting
the evidence-grounded competency tagging approach of Le, Abel and Laforge to the
constraints of an operational learning management system.

> Le, N. L., Abel, M.-H., & Laforge, B. (2026). *From Learning Resources to
> Competencies: LLM-Based Tagging with Evidence and Graph Constraints.*

---

## License

No licence has been assigned yet. The work was produced as institutional
research at UTC / Heudiasyc / CNRS in collaboration with ENSIA, so the licensing
terms are for the researcher and supervisors to agree; until then, no permission
to reuse is granted or implied.

The corpus is synthetic material created for this study. It contains no student
data and no personal data.
