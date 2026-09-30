# Current status

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Updated:** 2026-09-22  
**Source:** live repository counts

Status values: `COMPLETE` · `WAITING_FOR_HUMAN` · `OPTIONAL / FUTURE EXTENSION` · `DEFERRED`

---

## Snapshot

| Item | Count | Notes |
|---|---:|---|
| Python | 3.12.3 | local `.venv` |
| Package | moodle-competency-mvp 0.1.0 | editable install |
| Moodle | 5.2.1+ | local development instance |
| Courses | MVP-SW, MVP-DATA | |
| Pages | 8 | |
| Quizzes | 2 | not evaluation units |
| Quiz questions | 12 | kept as independent resources |
| Selected UTC GI competencies | 13 | 3 parent + 10 child |
| Normalized resources | 20 | 8 page + 12 quiz_question |
| Fragments | 35 | 23 page_chunk + 12 quiz_question |
| BM25 Top-5 sets | 35 | complete |
| Constrained LLM tasks | 35 | complete |
| Gemini validated responses | **35** | all `valid=true` |
| Human-reviewed reference rows | **35 / 35** | researcher-finalized |
| Annotator | Wail Ouaret | 2026-09-18 |
| Evidence-review rows | **83 / 83** | mechanical 83/83; pedagogical complete |
| Pedagogical ratings | 65 × 2, 16 × 1, 2 × 0 | Human Gate 2 COMPLETE |
| Teacher reviews | **0** | WAITING_FOR_HUMAN |
| Supervisor reviews | **0** | WAITING_FOR_HUMAN |
| Researcher reviews | **2** | not teacher-study results |

Wording: all 35 fragments were reviewed and finalized by the researcher against the 13-competency UTC GI catalogue. The finalized annotation set is the **human-reviewed reference**. It is not independent blinded gold from scratch, and it is not AI-generated gold.

---

## Pipeline status

| Stage | Status |
|---|---|
| Moodle environment and two test courses | COMPLETE |
| 13-competency GI framework import | COMPLETE |
| Resource extraction / fragmentation / BM25 | COMPLETE |
| Constrained Gemini | COMPLETE — 35/35 valid |
| Human-reviewed reference | COMPLETE — 35/35 |
| Pedagogical evidence ratings | COMPLETE |
| Evidence-aware error analysis | COMPLETE |
| Resource-level evaluation | COMPLETE |
| Minimal hierarchy / graph analysis | COMPLETE — post-hoc ablation; original Gemini unchanged |
| Ollama post-hoc comparison | COMPLETE — 35/35 checkpoints in `data/experiments/` |
| Teacher-facing runtime interface | COMPLETE — `streamlit run app.py` |
| Frozen-corpus teacher validation interface | COMPLETE — `streamlit run app/Home.py` (8 pages; untested by a teacher) |
| Evidence-usefulness pilot (Section M) | WAITING_FOR_HUMAN — 12-case design fixed at seed 20260918; 0 responses |
| Teacher review summary (Section N) | WAITING_FOR_HUMAN — 0 of 34 mappings reviewed |
| Validated coverage view (Section O) | COMPLETE — correctly empty until decisions exist |
| Unconstrained all-13 comparison (Section K) | OPTIONAL — software complete and audited; live run not authorized |
| Gemini runtime test | COMPLETE |
| Ollama runtime test | COMPLETE |
| Researcher review | COMPLETE |
| Real teacher/supervisor validation | WAITING_FOR_HUMAN |
| Final research report / demo / figures | COMPLETE |
| LTI | OPTIONAL / FUTURE EXTENSION |
| Native Moodle plugin | DEFERRED |

---

## Human gates

| Gate | Status |
|---|---|
| 1. Human-reviewed fragment reference | COMPLETE |
| 2. Pedagogical evidence 0/1/2 | COMPLETE |
| 3. Teacher/supervisor accept/reject/modify | WAITING_FOR_HUMAN — 0 of 34 |
| 4. Evidence-usefulness pilot | WAITING_FOR_HUMAN — designed, 0 responses |

---

## Immediate next step

A real teacher or supervisor reviews the 34 predicted resource-competency
mappings in the frozen-corpus interface:

```bash
source .venv/bin/activate
streamlit run app/Home.py      # page "2 Teacher Review"
python scripts/28_summarize_teacher_reviews.py
```

See `docs/TEACHER_INTERFACE_GUIDE.md`. Genuine decisions are stored in
`data/reviews/corpus_teacher_reviews.csv`, which has a header and zero
decisions. Demo rows are not validation. The corpus file stays separate from
the runtime app's `data/reviews/teacher_reviews.csv` so the two researcher
decisions are preserved.

**Do not invent decisions.** The researcher reviews already stored are not
teacher validation, and no acceptance rate is reported until real decisions
exist.

---

## Overall status

**WAITING_FOR_HUMAN.** The measured pipeline, evaluation, error analysis,
evidence review, resource-level evaluation, graph ablation, teacher interface,
final reports and demo package are all complete. The project is not COMPLETE
because the teacher interface has not been used by a teacher.

| Check | Result (2026-09-22) |
|---|---|
| `scripts/12_validate_manual_annotations.py --mode final` | PASSED 35/35 |
| `python -m pytest -q` | 435 passed |
| `python -m compileall -q src scripts tests app` | succeeded |
| `python scripts/ui_smoke_check.py` | 14/14 pages OK |
| Protected artefact hashes | 21/21 unchanged |

Full detail: `reports/FINAL_VALIDATION_REPORT.md`.
