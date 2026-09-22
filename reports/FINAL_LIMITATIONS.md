# Final limitations

**Moodle learning resource-to-competency alignment — reduced MVP**
**Researcher:** Wail Ouaret · UTC / Heudiasyc / CNRS
**Date:** 2026-09-22

This document exists so that no reader has to reconstruct the caveats from the
results. It states what these numbers can and cannot support. Where a limitation
has a size, the size is given.

---

## 1. The three that matter most

If only three things are remembered from this report, these are they.

### 1.1 The corpus is small and was built for this study

20 resources · 35 fragments · **38 reference labels** · 13 competencies · 2
courses.

With 38 labels, **one label is worth 2.63 points of recall**. The difference
between Recall@5 = 0.9737 and a perfect 1.0 is a single quiz question. Metrics
of this precision — reported to four decimal places — are exact arithmetic on a
tiny denominator, not stable estimates. No confidence interval is given because
none would be meaningful.

The material was written for this experiment: clean, short, thematically
coherent. Nothing here demonstrates the pipeline survives a real course with
inconsistent formatting, mixed languages, administrative noise or legacy
content.

### 1.2 There is one annotator and no agreement measurement

All 38 reference labels come from **one person** (Wail Ouaret, 2026-09-18).
There is no second annotator, and therefore **no inter-annotator agreement of
any kind** — no kappa, no overlap subset, nothing.

Every score in this project is an agreement rate with one person's judgement. A
different annotator could plausibly have produced a different reference,
particularly on granularity, where a single convention choice drives the
headline precision figure (§2.1).

The correct term is **human-reviewed reference annotations**. They are not
independent blinded gold produced from scratch, and they are not AI-generated
gold.

### 1.3 The evidence review is not independent of the reference

The same person produced the reference labels *and* the 83 pedagogical evidence
ratings, on the same day.

The convergence reported in the error analysis — the evidence review
independently flagging the retrieval-failure fragment and the parent-child
problem — is real and was produced by a separate pass over different material
(quotes rather than labels). But it is **one mind applying one set of intuitions
twice**, not two observers agreeing. It should be read as internal consistency,
not as external validation.

---

## 2. Limitations that shape specific numbers

### 2.1 The annotation convention drives the headline precision figure

The annotator labelled **only at child level**: all three parent competencies
have zero reference support across 38 labels.

Consequence: every parent prediction is automatically a false positive. Ten of
the 14 false positives (**71%**) are exactly that. Micro precision is 0.7255;
removing only those ten raises it to 0.9024.

So **micro precision here is substantially a measure of granularity convention
agreement**, not of topical correctness. A reference that accepted a parent as
partially correct would report a very different precision for identical model
output. This is the single most important thing to understand before quoting
0.7255.

### 2.2 There are no `NONE` fragments, so abstention is untested

Every one of the 35 fragments has at least one correct competency. The abstention
rate is 0.0 and both `correct_abstention` and `incorrect_abstention` are 0.

**This is a property of the corpus, not a property of the system.** There was
never an occasion on which abstaining was correct, so the system's ability to
decline was never exercised. The 0.0 must never be presented as good judgement.

In deployment this matters: a real course contains syllabi, deadlines,
administrative notices and logistics pages that map to no competency. How the
system handles them is **unknown**.

### 2.3 Two macro numbers exist and neither is "the" macro score

Because three of thirteen labels have zero reference support:

- `macro_all_13` = 0.6958 — averages the unsupported parents in as zeros
- `macro_gold_supported_labels` = 0.9046 — averages over the ten labels in play

The gap is 0.21. Quoting either alone without the other, or without saying which
is which, would materially mislead. Both are reported everywhere.

### 2.4 Resource-level results inherit fragment-level errors by construction

The resource-level reference is **derived**, not independently annotated: a
Page's labels are the union of its fragments' labels.

This is a reasonable derivation, but it is not a second annotation exercise, and
aggregation amplifies precision errors — a spurious parent on any one fragment
contaminates the whole resource. Resource-level precision (0.6765) is lower than
fragment-level (0.7255) for this mechanical reason, and exact-set match falls to
0.45.

Activity-level Moodle competency links exist in `data/gold/manual_moodle_links.csv`
but were deliberately **not** used as question-level gold: they describe a whole
quiz and would be a much coarser signal presented as ground truth.

### 2.5 The graph ablation is post-hoc and reference-specific

The child-preference ablation raises micro F1 from 0.8315 to 0.9367 with no
recall loss. Three caveats:

1. The rule was designed **after** observing the errors. It is not an
   out-of-sample result.
2. It works perfectly here only because **no parent is ever a correct label in
   this reference**. On a corpus where a parent is sometimes right, the same rule
   would destroy true positives.
3. It is a **separate simulated output**. The original predictions were never
   modified (`original_predictions_modified = false`).

It is a diagnosis — the errors are systematic and mechanically detectable — not
a validated technique, and is labelled `POST-HOC MINIMAL GRAPH ABLATION`
throughout.

### 2.6 Confidence scores are uncalibrated

The model reports a confidence per selection. These were **never validated
against correctness** and no calibration curve was computed. They are displayed
in the interface as a weak hint and should not be treated as probabilities.

---

## 3. Scope limitations

### 3.1 Two resource types only

Moodle Pages and quiz questions. **No** assignments, rubrics, forums, PDFs,
slides, video, audio or OCR.

Quiz questions are treated as independent resources — a deliberate choice, since
a quiz as a whole rarely assesses one competency while a question usually does.
It does mean "20 resources" and "2 quizzes" describe the same material at
different granularities, and that the corpus is 60% quiz questions by count.

### 3.2 Local Moodle, with a local-specific extraction path

Moodle 5.2.1+ on a local development instance. Pages came through the REST API;
**quiz question text required direct SQL access**, because the web services do
not expose it usably on this version.

That fallback would not transfer unchanged to a managed institutional Moodle,
where direct database access is normally unavailable. Reproducing this pipeline
elsewhere may require solving question extraction differently.

### 3.3 One framework, one language, 13 competencies

A 13-competency subset of the UTC GI framework, with French competency
descriptions against mostly English resource text. The framework has parent/child
relations only — no prerequisites, no related-to links — and none were invented.

Nothing here shows the approach scales to the full ROME 4.0 framework or to
frameworks with hundreds of competencies, where BM25 Top-5 would be a far more
aggressive restriction.

### 3.4 External model dependency

Results depend on `gemini-3.5-flash` through a third-party API whose behaviour
may change without notice. Reproduction is therefore **by frozen artefact and
hash**, not by re-running: the historical responses are protected and must never
be regenerated.

### 3.5 The effect of candidate restriction is inferred, not measured

The constrained condition may improve precision by hiding implausible options,
and definitely caps recall at the retrieval ceiling. The all-13 unconstrained
comparison that would measure this **has not been run** — the software is built
and audited, but the live run was never authorized.

So statements about *why* the constrained system behaves as it does are
reasoning from the design, not from a controlled comparison.

---

## 4. What has not been validated by a human

### 4.1 No teacher validation exists

**0 teacher decisions. 0 supervisor decisions.** 34 reviewable mappings, all
pending.

No acceptance rate, edit rate or rejection rate is reported anywhere, and the
summary stores `null` rather than `0.0` so the absence cannot be misread.

The two decisions that exist are **researcher** decisions from the separate
runtime app and are never counted as teacher validation.

### 4.2 Evidence usefulness is designed but unmeasured

The A/B pilot (12 stratified cases, conditions balanced 6/6, fixed seed) exists
as a reproducible design with no responses. Whether showing the evidence quote
changes a reviewer's decision, confidence or speed is **unknown**.

If only the researcher eventually performs it, it will be reported as a
**researcher pilot**, never as a teacher study.

### 4.3 Validated coverage is zero

The inverse index shows 13/13 competencies with at least one predicted resource,
which can easily read as full coverage. **Validated** coverage is 0 of 13.
Predicted coverage and confirmed coverage are different things, and the
interface keeps them visibly separate.

---

## 5. Statistical limitations

**No significance test was run**, and none should be quoted. `significance_tests:
not_run` is recorded in the metric files.

Reasons: n = 35 fragments and 38 labels; a single annotator; a single rater for
evidence; systems compared on the same tiny sample without correction; and the
graph ablation evaluated post-hoc on the data that motivated it.

Differences reported here — for instance micro F1 0.7123 → 0.8315 — are
**arithmetic facts about this corpus**, not estimated effects with uncertainty.
They should never be written as though they generalise.

---

## 6. What the results do support

To be fair to the work, the limitations do not empty it. On this corpus, the
following are established facts, not claims:

1. The full pipeline runs end to end and produces 35/35 valid, schema-conformant,
   evidence-backed responses with 0 invalid accepted.
2. **Every evidence quote is an exact substring of its source.** Fabricated
   justification did not occur once in 83 quotes.
3. The model selected **every** reference label that retrieval offered it
   (`llm_missed_gold_label = 0`, 37 of 37).
4. The failure modes are **specific, quantified and mechanically detectable** —
   not a diffuse "the model is sometimes wrong".
5. Two independent review passes converged on the same two defects.
6. Everything is reproducible from hashed frozen artefacts, with no secret in any
   generated report.

That is a working, auditable prototype with a well-characterised error profile.
It is not a validated system, and this document exists so the difference stays
visible.
