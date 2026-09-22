# Results — one page

**Moodle learning resource → competency alignment · reduced MVP**
Wail Ouaret · UTC / Heudiasyc / CNRS · 2026-09-22

---

## The question

Can retrieval + a constrained LLM propose competency alignments a teacher can
**verify**, with evidence they can check?

## The corpus

2 courses · 20 resources (8 Pages + 12 quiz questions) · 35 fragments ·
13 UTC GI competencies (3 parents + 10 children) · **38 reference labels**,
one annotator, no inter-annotator agreement · **0 `NONE` fragments**.

## The pipeline

Moodle REST + SQL → normalize → fragment → **BM25 Top-5** → **constrained
Gemini** (`gemini-3.5-flash`, temp 0, ≤3 selections) → **exact-substring
evidence validation** → resource aggregation → evaluation.
35/35 responses, 35/35 valid, 0 invalid accepted.

---

## Headline numbers

| Metric | BM25 Top-1 | BM25 Top-5 + Gemini | Δ |
|---|---:|---:|---:|
| Micro precision | 0.7429 | 0.7255 | **−0.017** |
| Micro recall | 0.6842 | **0.9737** | **+0.290** |
| Micro F1 | 0.7123 | **0.8315** | **+0.119** |

BM25 Recall@1/@3/@5 = 0.6842 / 0.8684 / **0.9737** · MRR = 0.8310
Exact-set match 0.6286 · coverage 1.0 · avg 1.46 labels/fragment
Macro F1: **0.6958** (all 13) / **0.9046** (10 gold-supported labels)

> The LLM buys **+0.29 recall for −0.02 precision**. It does *not* win on every
> measure — BM25 Top-1 is slightly more precise.

---

## The three findings

**1 · Recall is retrieval-bound, not model-bound.**
`llm_missed_gold_label = 0`. The model selected **all 37** reference labels
retrieval offered it. The one missed label (`quiz_question:1:4#f001` → `GI_C1_3`)
was absent from the BM25 Top-5 — a **retrieval failure**. Recall = Recall@5
exactly.

**2 · Precision is lost to granularity, not to topic confusion.**
14 false positives; **10 of them (71%)** are the three *parent* competencies,
predicted alongside their correct child. The reference labels only at child
level — a convention the prompt never stated. So this is partly a
**specification gap**, not only a model defect.

**3 · Exact evidence stops fabrication but not weak reasoning.**
**83/83 quotes (100%)** are exact substrings. Yet a human rated only **78.3%**
as clearly supporting; 19.3% partial, 2.4% unsupported. Its real value: it makes
weak justification **visible** to a teacher.

---

## Two signals that converged independently

The evidence review was done quote-by-quote without consulting the metrics, and
found the same two defects:

- **Both `0`-rated quotes** fall on the single retrieval-failure fragment — and
  the reviewer's comment names `GI_C1_3`, exactly the label BM25 missed.
- **Parent quotes rated far worse than child quotes**: only 1 of 12 parent
  quotes judged "clearly supports", against 64 of 71 child quotes.

---

## Post-hoc minimal graph ablation

Dropping the redundant parent — *simulated output only, predictions untouched*:

| | Original | Child-preference |
|---|---:|---:|
| Micro precision | 0.7255 | **0.9024** |
| Micro recall | 0.9737 | 0.9737 *(unchanged)* |
| Micro F1 | 0.8315 | **0.9367** |
| Exact-set match | 0.6286 | **0.9143** |

Confirms the errors are **systematic and mechanically detectable**. It is *not*
a validated technique: the rule was designed after seeing the errors and works
only because no parent is ever correct in this reference.

---

## Honest status

| | |
|---|---|
| Pipeline, evaluation, error analysis, evidence review | `COMPLETE` |
| Resource-level evaluation, graph check + ablation | `COMPLETE` |
| Teacher validation interface (14 pages, all render) | `COMPLETE` |
| **Teacher decisions** | **`WAITING_FOR_HUMAN` — 0 of 34** |
| **Evidence-usefulness pilot** | **`WAITING_FOR_HUMAN` — designed, 0 responses** |
| Unconstrained all-13 comparison | `OPTIONAL` — software ready, not run |
| 435 tests · compileall · gold validator | all pass |

**No acceptance rate is reported** because no teacher decision exists. The two
decisions on file are *researcher* decisions from a separate runtime app.

---

## What these numbers cannot say

- 38 labels from **one annotator**, no agreement measurement — every score is
  agreement with one person.
- **No `NONE` fragments** → abstention is untested, not good.
- Micro precision is substantially a measure of **granularity-convention
  agreement**.
- Pages + quiz questions only; local Moodle; SQL fallback for quiz text.
- **No significance testing** — sample size and design do not support it.

---

## Next, in order of value

1. **Collect real teacher decisions** — the interface exists, the data does not.
2. **Add `NONE` fragments** so abstention becomes testable.
3. **Run the unconstrained comparison** to measure, not assume, the effect of
   candidate restriction.
4. **Fix granularity in the prompt** and re-measure, rather than pruning after
   the fact.
5. **A second annotator on a subset** — any agreement figure at all.
