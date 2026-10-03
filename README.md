# Moodle Resource-to-Competency Alignment

Align Moodle learning resources with a hierarchical competency framework.
The software proposes mappings a teacher can inspect. It does not write
official competency links into Moodle.

**Researcher:** Wail Ouaret
**Supervisors:** Marie-Hélène Abel, Le Ngoc Luyen
**Institution:** Université de Technologie de Compiègne — Heudiasyc (UMR 7253, CNRS)

Practical setup, the demo, Moodle extraction, and reproduction are in [GUIDE.md](GUIDE.md).

## Overview

An LMS resource is normalised, split into fragments, and compared with the
competency catalogue. BM25 returns a Top-K candidate set. A constrained model
may select only from that set, and each selection must quote an exact substring
of the fragment. Selections are aggregated to the resource, checked against the
parent/child hierarchy, and left for a human decision.

```
LMS resource
  → normalisation
  → fragmentation
  → BM25 Top-K
  → constrained selection
  → exact evidence validation
  → aggregation
  → hierarchy diagnostics
  → human review
```

The system is assistive. A suggestion is not an official Moodle link.

## Motivation

Moodle can store a competency framework and can store links between activities
and competencies. Choosing the link is still a manual pedagogical task. This
project records a candidate set, a constrained selection, and a verbatim
quotation so a reviewer can see what was proposed and why.

## Key properties

- The model may select only competencies from the recorded Top-K set.
- Each selected competency must be supported by an exact substring of the fragment.
- A miss can be attributed to retrieval or to selection, because both stages are stored.
- Parent/child conflicts are reported as warnings. They do not change the model output.
- Fragment decisions are aggregated to the resource, with the supporting fragments kept.
- The same alignments can be read from resource to competency and from competency to resource.
- Accept, reject, and modify decisions are stored separately from the predictions and from the reference labels.
- Gemini, Ollama, and a mock backend implement the same alignment interface.

BM25, a language-model API, and a review form are existing tools. The work is
the way they are constrained and recorded.

## Architecture

```
Moodle / external source
        ↓
source adapter
        ↓
normalized resource
        ↓
fragmentation
        ↓
BM25 Top-K
        ↓
AlignmentBackend
        ↓
response validation
        ↓
aggregation + inverse index
        ↓
hierarchy diagnostics
        ↓
teacher review
```

Moodle-specific code is the REST client, the read-only SQL export used for
quiz-question text, and the two course identifiers in the research
configuration. Fragmentation, retrieval, task construction, validation,
aggregation, and review operate on normalised records. Another LMS needs a
connector that emits those records. No live Canvas, D2L, Open edX, or
Blackboard connector is included.

## Frozen research scope

The measured experiment is:

- 2 Moodle courses (`MVP-SW`, `MVP-DATA`)
- 20 resources (8 pages and 12 quiz questions)
- 35 fragments
- 13 UTC GI competencies
- BM25 Top-5
- constrained Gemini (`gemini-3.5-flash`, temperature 0, at most 3 selections)
- exact-substring evidence checks
- a human-reviewed fragment reference (one annotator)
- a Streamlit review interface

Teacher and supervisor validation of those 34 resource-competency mappings has
not been done. Status: `WAITING_FOR_HUMAN` (0 / 34). No acceptance, rejection,
or modification rate is reported.

## Results

Fragment-level figures below are the frozen experiment. Full files:
`reports/metrics/bm25_metrics.json` and
`reports/metrics/constrained_llm_metrics.json`.

| Stage | Result |
|---|---|
| BM25 | Recall@1 = 0.6842, Recall@3 = 0.8684, Recall@5 = 0.9737, MRR = 0.8310 |
| Constrained Gemini | micro precision 0.7255, recall 0.9737, F1 0.8315; exact-set match 0.6286 |
| Evidence check | 83 / 83 quotations match the source text exactly |
| Missed reference label | 1. `quiz_question:1:4#f001`, gold `GI_C1_3`, absent from the Top-5 |

Pedagogical ratings of those quotations (clear, partial, unsupported) are a
researcher review of the evidence, not a teacher study. Hierarchy comparisons
were computed after the model run. They are diagnostics. They do not replace
the Gemini scores above.

`scaling_checks.py` is a later offline retrieval check. It does not call a
model and does not replace these figures. Retrieval Recall@K on another corpus
is not end-to-end accuracy.

## Installation

Recorded environment: Python 3.12.3 on Linux. WSL is not required.

```bash
git clone https://github.com/WailOuaret/moodle-competency-alignment-mvp.git
cd moodle-competency-alignment-mvp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Copy `.env.example` to `.env` before a live Moodle or Gemini run. The frozen
demo can be opened without those secrets. Details are in [GUIDE.md](GUIDE.md).

## Quick start

```bash
source .venv/bin/activate
streamlit run app/Home.py
```

Open `http://localhost:8501`.

A separate runtime app analyses one new text or Moodle resource:

```bash
streamlit run app.py
```

## Tests

```bash
python scripts/12_validate_manual_annotations.py --mode final
python -m pytest -q
python -m compileall -q src scripts tests app
python scripts/ui_smoke_check.py
```

A successful run finishes without failures.

## Reproducing the frozen experiment

Historical Gemini responses are stored under `data/interim/`. Evaluation
scripts reread those files, the BM25 candidate lists, and the human-reviewed
reference. They do not call Gemini again and they must not overwrite the frozen
files.

```bash
python scripts/15_evaluate_bm25.py --dry-run
python scripts/16_evaluate_constrained_llm.py --dry-run
python -m pytest -q tests/test_core_result_regression.py
```

`--dry-run` does not rewrite the published metric files.
`scripts/10_run_gemini_alignments.py` contacts the model API.

## Project structure

| Path | Role |
|---|---|
| `src/moodle_competency/` | Alignment engine |
| `app/` | Frozen-corpus review interface |
| `app.py`, `pages/` | Runtime analysis interface |
| `scripts/` | Extraction, retrieval, evaluation, verification |
| `tests/` | Automated tests |
| `sql/` | Read-only quiz export used in the research environment |
| `service/` | Development HTTP service around the engine (branch `feature/moodle-plugin`) |
| `moodle-plugin/compalign/` | Moodle plugin prototype `local_compalign`, under development (branch `feature/moodle-plugin`) |
| `docs/` | Architecture, connectors, evaluation, reproducibility |
| `data/processed/`, `data/interim/`, `data/gold/` | Frozen corpus, responses, and reference |
| `reports/metrics/`, `reports/tables/`, `reports/figures/` | Measured results |

## Integration

Moodle Pages are read through the REST web service. Quiz-question text in the
recorded environment uses a local read-only SQL export because the REST
question payload was not sufficient. That SQL path is a research limitation,
not a production design.

A normalised resource needs `resource_id`, `resource_type`, `title`, and
`text`. The contract is described in
[docs/PLATFORM_CONNECTOR_CONTRACT.md](docs/PLATFORM_CONNECTOR_CONTRACT.md).
Adding a resource type means writing an adapter into that shape. The
assignment adapter is tested offline and is not part of the frozen run.
Connecting Canvas, or another LMS, means writing a connector. The Canvas note
in `docs/CANVAS_INTEGRATION.md` is a design. It has not been implemented or
run against a live Canvas site.

## Limitations

- The frozen evaluation uses 20 resources and 35 fragments.
- The reference was produced by one annotator. There is no inter-annotator agreement.
- The reference has no genuine `NONE` fragments, so abstention was not measured on that case.
- Only Pages and quiz questions were evaluated.
- Quiz text depends on a local SQL export.
- There is no production service. `service/` is a development adapter with no queue and no result store.
- The Moodle plugin is under development on the `feature/moodle-plugin` branch. It has only been run with
  the mock backend on one local sandbox, has not been validated by teachers, and does not write competency
  links. It is not a released or production plugin. There is no LTI launch implementation.
- There is no live second-LMS validation.
- Teacher/supervisor review of the frozen mappings is waiting: 0 / 34.

## Roadmap

An HTTP service around the existing engine and a Moodle plugin prototype that
returns suggestions only are under development on the `feature/moodle-plugin`
branch. Not yet built or done: a run of a live model through the plugin, a study
with teachers, and a study export. Write-back of a link is not implemented and
would happen only after an explicit accept or modify. Framework-size and LBG checks in
`scaling_checks.py` measure retrieval behaviour. They are not a licence to
reuse the 13-competency Gemini scores on a new catalogue. K = 5 was selected
on this reference. It is not a universal setting.

## Citation

No publication DOI is attached to this repository yet. Citation information
will be updated when a paper or report is published. Until then, cite the
software repository and the version you used.
