# Supervisor Demonstration and Testing Guide

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

Part A is a ten-minute demonstration. Part B is the validation exercise, in which
the supervisor records their own independent judgements.

---

## Preparation

```bash
cd ~/projects/moodle_competency_mvp
source .venv/bin/activate
streamlit run app/Home.py
```

Opens at <http://localhost:8501>. Also have the local Moodle instance open, and
`FINAL_DELIVERY/03_RESULTS_AND_ANALYSIS.md` to hand.

A quick confidence check before starting:

```bash
python scripts/12_validate_manual_annotations.py --mode final   # PASSED, 35/35
python -m pytest -q                                             # 435 passed
python scripts/ui_smoke_check.py                                # 14 pages OK
```

---

# Part A — Demonstration (10 minutes)

### 1. The problem *(1 min)*

A Moodle course accumulates material that is never linked to the competencies the
programme claims to teach. A teacher cannot ask which resources cover a given
competency, and manual tagging does not scale. The question addressed here is
whether retrieval plus a constrained language model can propose alignments a
teacher can **verify**, with evidence they can check rather than a score they must
trust.

### 2. The two courses *(30 s)*

*Moodle → MVP-SW and MVP-DATA.*

Twenty resources: 8 Pages and 12 quiz questions. Each quiz question is treated as
its own resource, because a quiz rarely assesses one competency while a question
usually does.

### 3. The competency framework *(1 min)*

*Moodle → Site administration → Competencies → UTC GI framework.*

Thirteen competencies: three parents and ten children. Parent–child relations
only; no prerequisites exist in this framework and none were invented. The
hierarchy becomes important at step 11.

### 4. A Page *(30 s)*

*Moodle → MVP-SW → "Software Development Lifecycle and Deployment".*

This becomes resource `page:1` and splits into two fragments.

### 5. A quiz question *(30 s)*

*Moodle → MVP-DATA quiz → preview a question.*

Its own resource, one fragment.

### 6. A fragment *(30 s)*

*Application → Home → MVP-SW → expand `page:1`.*

Thirty-five fragments in total: 23 Page chunks and 12 quiz questions. The fragment
is the unit the model sees and the unit that was annotated.

### 7. Retrieval *(1 min)*

*Application → 1 Resource to Competencies → `page:1` → Fragment-level detail.*

BM25 retrieves the five nearest competencies per fragment, shown with scores and
with a mark against those the model selected.

**Recall@5 is 0.9737, and this fixes the ceiling for everything downstream.**

### 8. Constrained selection *(1 min)*

*Same page, the prediction cards.*

`gemini-3.5-flash`, temperature 0, restricted to those five, at most three
selections. Thirty-five of 35 responses valid, none rejected.

### 9. Exact evidence *(1 min)*

*Same page, an evidence block.*

Every selection must quote the fragment verbatim, checked mechanically. All 83
quotations passed: **no fabricated justification anywhere in the experiment**.

A manual review then rated each quotation for whether it actually justifies the
competency: 78.3 % clearly supporting, 19.3 % partial, 2.4 % inadequate. Exactness
prevents fabrication; it does not guarantee good reasoning. What it guarantees is
that weak reasoning is visible.

### 10. Results *(2 min)*

*Application → 6 Experiment Results.*

| Metric | BM25 Top-1 | With constrained selection |
|---|---:|---:|
| Micro precision | 0.7429 | 0.7255 |
| Micro recall | 0.6842 | 0.9737 |
| Micro F1 | 0.7123 | 0.8315 |

Three points:

- **The only missed label was one retrieval never offered.** The model selected
  every reference label available among its candidates —
  `llm_missed_gold_label = 0`. What it would do with all 13 available is
  untested.
- **The trade-off is real.** +0.29 recall for −0.02 precision. Not uniformly
  better.
- **Abstention is untested.** The rate is 0.0, but no fragment in this corpus has
  "no competency" as its correct answer, so abstaining was never right.

Two macro figures are reported — 0.6958 over all thirteen labels and 0.9046 over
the ten with reference support — because three competencies have zero support and
a single macro number would mislead either way.

### 11. The dominant error *(1 min)*

*Application → 1 Resource to Competencies → `page:1` → the `GI_C1` card with its
warning.*

Fourteen false positives, of which **ten are top-level competencies predicted
alongside their own correct child**.

The honest part: the annotation convention assigns labels only at child level, and
that convention was never stated in the prompt. Predicting `GI_C3` for a
machine-learning fragment is defensible; the reference simply does not count it.
Micro precision here is therefore substantially a measure of agreement with a
granularity convention.

The evidence review reached the same conclusion independently: only 1 of 12
quotations supporting a parent was judged clearly adequate, against 64 of 71 at
child level.

### 12. Both directions *(1 min)*

*Application → 3 Competency to Resources → select `GI_C3_2`.*

The inverse view: from a competency to the resources that cover it, with evidence.
All thirteen competencies have at least one predicted resource — though for the
three parents that is the redundancy just described. Predicted coverage is not
validated coverage.

### 13. The review interface *(30 s)*

*Application → 2 Teacher Review, then 5 Review Progress.*

Where a teacher accepts, rejects or modifies each of the 34 suggestions.

**Progress shows 0 of 34.** No acceptance rate is reported anywhere, because none
exists. The two decisions on file are researcher decisions from a separate
runtime application and are labelled as such.

### 14. Limitations *(1 min)*

Twenty resources, 35 fragments, 38 reference labels — one label is worth 2.6
points of recall. **One annotator, no inter-annotator agreement.** The evidence
review was by the same person, so it is internal consistency rather than
independent validation. No `NONE` fragments, so abstention is untested. Pages and
quiz questions only. No significance testing: the design does not support it.

---

# Part B — Supervisor validation

This is the part that produces new information. The system has been measured
against one annotator's reference; it has never been assessed by anyone else.

## What is asked

Review some or all of the 34 suggested resource–competency pairs and record, for
each, whether it is correct. Roughly 30–45 minutes for the full set; a partial
review is useful.

## Procedure

**1. Open the interface.**

```bash
source .venv/bin/activate
streamlit run app/Home.py
```

**2. Go to *2 Teacher Review*.**

**3. In the left sidebar, enter your own name and select role `supervisor`.**

Both are required. The role determines how the decisions are reported: a
`researcher` role is reported separately and never counted as external
validation.

**4. For each suggestion, record your own judgement.**

| Action | When |
|---|---|
| **ACCEPT** | The competency genuinely fits the resource |
| **REJECT** | It does not fit |
| **MODIFY** | It is wrong, and you can name the competency that is right |

Optionally record whether the evidence quotation was useful:

| Rating | Meaning |
|---|---|
| `0` | It did not justify the competency |
| `1` | Partly |
| `2` | It clearly justified the competency |

There is also a form at the foot of the page to **add** a competency the system
missed entirely.

**5. Press *Save this decision* on each card.** Nothing is stored otherwise.

**6. When finished:**

```bash
python scripts/28_summarize_teacher_reviews.py
```

## Controls in place

- **Nothing is pre-filled.** No decision is selected by default and none is
  suggested.
- **Your name and role are recorded** with every decision.
- Each save takes a timestamped backup and writes atomically.
- Re-deciding replaces your earlier answer rather than adding a duplicate.
- The interface writes exactly one file. It does not write to Moodle, to the
  reference annotations, to the model output, to the evidence review, or to any
  metric file.
- Rates are computed only once decisions exist; until then they are recorded as
  null rather than zero.

## What to look at when judging

**BM25 rank** — the position the competency held in retrieval. "Not retrieved"
means the model could not have chosen it, which distinguishes a retrieval failure
from a model error.

**The evidence quotation** — verbatim from the resource. The question is whether
it justifies the competency, not merely whether it appears.

**Warning markers** — `parent_child_redundancy` means both a parent and its child
were predicted. Whether that is a genuine problem or harmless is itself worth your
judgement, and is not something the reference can answer.

## Three questions your review would answer

1. **Is parent–child redundancy actually a problem?** It costs 0.18 micro
   precision against the reference. A teacher may regard tagging a resource with
   both `GI_C3` and `GI_C3_2` as harmless. If so, the headline precision figure
   overstates the real defect.
2. **Does the evidence quotation change your decision?** This is what the
   optional pilot on page 7 measures.
3. **Do you agree with the annotator at all?** With one annotator and no
   agreement statistic, your decisions would be the first independent check on
   whether the reference is broadly reasonable.

## Optional — evidence-usefulness pilot (15 minutes)

*Application → 7 Evidence Usefulness Pilot.*

Twelve cases, each shown either with the evidence quotation visible or hidden
behind an explicit action. Decision, confidence and elapsed time are recorded.

The design is fixed at seed 20260918 and is exploratory. No significance test
will be computed, and if only the researcher participates it will be reported as
a researcher pilot rather than a teacher study.

---

## Current status

| Item | Status |
|---|---|
| Core research software | Complete |
| Documentation and delivery package | Complete |
| Reference annotation (35 fragments) | Complete |
| Evidence review (83 quotations) | Complete |
| **Supervisor or teacher validation** | **Pending — 0 of 34** |
| **Evidence-usefulness pilot** | **Pending — designed, no responses** |
| Unconstrained comparison | Optional; not run |
| LTI integration | Optional; future |
| Native Moodle plugin | Deferred |
