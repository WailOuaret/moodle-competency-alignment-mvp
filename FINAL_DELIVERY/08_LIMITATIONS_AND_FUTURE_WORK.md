# Limitations and Future Work

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

This document states what the results support and what they do not. Where a
limitation has a measurable size, that size is given.

---

## Part I — Limitations

## 1. The three that matter most

### 1.1 The corpus is small and was built for this study

Twenty resources, 35 fragments, **38 reference labels**, 13 competencies, two
courses.

With 38 labels, **one label is worth 2.63 points of recall**. The gap between
Recall@5 of 0.9737 and a perfect score is a single quiz question. Figures reported
to four decimal places are exact arithmetic on a small denominator, not stable
estimates; no confidence interval is given because none would be meaningful.

The material was written for this experiment: clean, short, thematically coherent.
Nothing demonstrates that the pipeline survives a real course with inconsistent
formatting, mixed languages, administrative content or legacy material.

### 1.2 One annotator, and no agreement measurement

All 38 reference labels were produced by one person. There was no second
annotator and therefore **no inter-annotator agreement of any kind** — no kappa,
no overlap subset, nothing.

Every score in this project is an agreement rate with one person's judgement. A
different annotator could plausibly have produced a different reference,
particularly on granularity, where a single convention drives the headline
precision figure (section 2.1).

The correct term is **human-reviewed reference annotations**. They are not
independent blinded gold produced from scratch and not machine-generated.

### 1.3 The evidence review is not independent of the reference

The same person produced the reference labels and the 83 pedagogical ratings, on
the same day.

The convergence reported in the analysis — the evidence review independently
identifying the retrieval failure and the parent–child problem — is real, and was
produced by a separate pass over different material (quotations rather than
labels). But it is one person applying one set of intuitions twice, not two
observers agreeing. It should be read as internal consistency, not external
validation.

---

## 2. Limitations that shape specific numbers

### 2.1 The annotation convention drives the precision figure

Labels were assigned **only at child level**: all three top-level competencies
have zero reference support across 38 labels.

Every parent prediction is therefore automatically a false positive. Ten of the
14 false positives — **71 %** — are exactly that. Micro precision is 0.7255;
removing only those ten raises it to 0.9024.

**Micro precision here is substantially a measure of agreement with a granularity
convention**, not of topical correctness. A reference that credited a parent as
partially correct would report a very different precision for identical output.
This is the single most important qualification to attach to the figure 0.7255.

### 2.2 No `NONE` fragments, so abstention is untested

Every one of the 35 fragments has at least one correct competency. The abstention
rate is 0.0 and both `correct_abstention` and `incorrect_abstention` are 0.

**This is a property of the corpus, not of the system.** Abstaining was never the
correct response, so the ability to decline was never exercised. The 0.0 must not
be presented as good judgement.

In deployment this matters: a real course contains syllabi, deadlines and
administrative notices that map to no competency, and the system's behaviour on
them is unknown.

### 2.3 Two macro figures exist and neither is "the" macro score

| View | Value | Interpretation |
|---|---:|---|
| `macro_all_13` | 0.6958 | Averages the unsupported parents in as zeros |
| `macro_gold_supported_labels` | 0.9046 | Averages over the ten labels in play |

The gap is 0.21. Quoting either alone, or without stating which, would mislead
materially. Both are reported throughout.

### 2.4 Resource-level results inherit fragment errors by construction

The resource-level reference is **derived**, not independently annotated: a Page's
labels are the union of its fragments' labels.

The derivation is reasonable but is not a second annotation, and aggregation
amplifies precision errors — a spurious parent on any one fragment contaminates
the whole resource. Resource precision (0.6765) is lower than fragment precision
(0.7255) for this mechanical reason, and exact-set match falls to 0.45.

Activity-level Moodle competency links exist but were deliberately **not** used as
question-level ground truth: they describe a whole quiz and would be a
considerably coarser signal presented as truth.

### 2.5 The hierarchy ablation is post-hoc and reference-specific

The child-preference ablation raises micro F1 from 0.8315 to 0.9367 with no recall
loss. Three qualifications:

1. The rule was formulated **after** observing the errors. It is not an
   out-of-sample result.
2. It works perfectly here only because **no parent is ever a correct label in
   this reference**. On a corpus where a parent is sometimes right, the same rule
   would delete true positives.
3. It is a **separate simulated output**; the original predictions were never
   modified.

It is a diagnosis — the residual error is systematic and mechanically detectable
— not a validated technique.

### 2.6 Confidence scores are uncalibrated

The model reports a confidence per selection. These were **never validated against
correctness** and no calibration curve was computed. They are displayed as a weak
hint and are not probabilities.

---

## 3. Scope limitations

### 3.1 Two resource types only

Moodle Pages and quiz questions. No assignments, rubrics, forums, PDFs, slides,
video, audio or OCR.

Quiz questions are treated as independent resources — a deliberate choice, since a
quiz as a whole rarely assesses one competency. It does mean the corpus is 60 %
quiz questions by count, and that "20 resources" and "2 quizzes" describe the same
material at different granularities.

### 3.2 Local Moodle, with a development-specific extraction route

Moodle 5.2.1+ on a local development instance. Pages came through the REST API;
**quiz question text required direct database access**, because the web services do
not expose it usably on this version.

That route would not transfer unchanged to a managed institutional Moodle, where
direct database access is normally unavailable. Reproducing the pipeline elsewhere
may require solving question extraction differently.

### 3.3 One framework, one language pairing, thirteen competencies

A 13-competency subset of the UTC GI framework, with French competency
descriptions against mostly English resource text. The framework has parent–child
relations only.

Nothing here shows the approach scales to the full ROME 4.0 framework or to
frameworks with hundreds of competencies, where a Top-5 restriction would be far
more aggressive.

### 3.4 External model dependency

Results depend on `gemini-3.5-flash` through a third-party API whose behaviour may
change without notice. Reproduction is therefore **by frozen artefact and
checksum**, not by re-running: the historical responses are protected and must
never be regenerated.

### 3.5 The effect of candidate restriction is reasoned, not measured

The constrained condition may improve precision by hiding implausible options, and
certainly caps recall at the retrieval ceiling. The all-13 comparison that would
measure this **has not been run** — the software is built and audited, but the run
was never authorised.

Statements about *why* the constrained system behaves as it does are therefore
reasoning from the design, not results from a controlled comparison.

---

## 4. What has not been validated by anyone else

### 4.1 No teacher or supervisor validation

**Zero teacher decisions. Zero supervisor decisions.** Thirty-four reviewable
mappings, all pending.

No acceptance, edit or rejection rate is reported anywhere, and the summary stores
`null` rather than `0.0` so the absence cannot be misread as a finding.

The two decisions that exist are **researcher** decisions recorded through the
separate runtime application and are never counted as external validation.

### 4.2 Evidence usefulness is designed but unmeasured

The A/B pilot — 12 stratified cases, conditions balanced 6 and 6, fixed seed —
exists as a reproducible design with no responses. Whether showing the evidence
quotation changes a reviewer's decision, confidence or speed is **unknown**.

If only the researcher eventually performs it, it will be reported as a
**researcher pilot**, never as a teacher study.

### 4.3 Validated coverage is zero

The inverse index shows 13 of 13 competencies with at least one predicted
resource, which reads easily as full coverage. **Validated** coverage is 0 of 13.
Predicted and confirmed coverage are different quantities and the interface keeps
them visibly separate.

---

## 5. Statistical limitations

**No significance test was performed**, and none should be quoted.
`significance_tests: not_run` is recorded in the metric files.

Reasons: 35 fragments and 38 labels; a single annotator; a single evidence rater;
systems compared on the same small sample without correction; and a post-hoc
ablation evaluated on the data that motivated it.

Differences reported here — micro F1 from 0.7123 to 0.8315, for instance — are
**arithmetic facts about this corpus**, not estimated effects with uncertainty,
and must not be written as though they generalise.

---

## 6. What the results do support

The limitations do not empty the work. On this corpus the following are
established facts:

1. The pipeline runs end to end and produces 35 of 35 valid, schema-conformant,
   evidence-backed responses with none rejected.
2. **Every evidence quotation is an exact substring of its source.** Fabricated
   justification did not occur once in 83 quotations.
3. The model selected **every** reference label retrieval offered it — 37 of 37,
   `llm_missed_gold_label = 0`.
4. The failure modes are specific, quantified and mechanically detectable, rather
   than a diffuse tendency to be occasionally wrong.
5. Two review passes converged independently on the same two defects.
6. Everything is reproducible from checksummed frozen artefacts, with no secret in
   any generated output.

That is a working, auditable prototype with a well-characterised error profile. It
is not a validated system, and this document exists so the difference stays
visible.

---

# Part II — Future work

## 7. Immediate, in order of value

### 7.1 Collect real teacher decisions

The interface is built and the data is absent. This is the largest gap between
what exists and what is known, and it is the cheapest to close: 34 mappings, 30 to
45 minutes.

It would answer three questions the metrics cannot: whether parent–child
redundancy is a genuine problem for a teacher or merely a scoring artefact;
whether the evidence quotation changes a decision; and whether an independent
reader agrees with the annotator at all.

### 7.2 Add fragments with no applicable competency

Introducing administrative pages, logistics notices and off-topic material would
make abstention measurable for the first time. At present a central safety
property of the system is untested.

### 7.3 Run the unconstrained all-13 comparison

The software is implemented and audited as identical to the constrained condition
except for the candidate space — 0 fragment-text mismatches and 0 instruction
mismatches across all 35 fragments, with the same validator reused unchanged. It
requires only authorisation to spend API quota.

It would convert a design argument into a measurement.

### 7.4 State the granularity convention in the prompt

The largest measured defect arises from a convention that existed only in the
annotator's practice. Adding one sentence to the instructions and re-measuring
would separate genuine model error from task underspecification — a more honest
remedy than post-hoc pruning, and a cheap experiment.

### 7.5 Engage a second annotator on a subset

Even a 10-fragment overlap would yield an agreement statistic where there is
currently none, and would test whether the child-level convention is shared or
idiosyncratic.

---

## 8. Medium term

**Larger and more realistic corpora.** Real courses with their inconsistencies,
across several institutions and frameworks, to test whether the error profile
holds.

**Retrieval alternatives.** Dense or hybrid retrieval compared against BM25 on the
same corpus. Retrieval sets the recall ceiling, so this is where recall gains must
come from. The single observed failure — a UX competency missed on a fragment
about prototype testing — is exactly the vocabulary-mismatch case dense retrieval
addresses.

**More resource types.** Assignments are the natural next addition, being close to
competency assessment in practice. PDFs and slides would require an extraction
layer.

**Relation typing.** Distinguishing whether a resource *teaches*, *assesses*,
*supports* or merely *mentions* a competency. A quiz question assesses; a Page
teaches. The corpus already contains both, so the distinction is available.

**Richer hierarchy relations.** Prerequisite and related-to relations would
support stronger consistency checks — but only where a framework genuinely encodes
them. The present framework does not, and none were invented.

---

## 9. Deferred

Deferred on supervisory guidance and not presented as completed:

| Item | Status |
|---|---|
| Native Moodle PHP plugin | Deferred |
| Automatic write-back into Moodle | Deferred |
| LTI integration | Optional; future |
| PDF, slide, video, audio, OCR ingestion | Deferred |
| Assignments and rubrics as corpus types | Deferred |
| Full ROME 4.0 framework | Deferred |
| Graph visualisation | Deferred |
| Recommendation engine and learning paths | Deferred |
| Curriculum analytics dashboard | Deferred |
| Relation-type classification | Deferred |
| Model fine-tuning | Deferred |
| Institution-wide deployment | Deferred |

The native Moodle plugin remains deferred unless the supervisors reopen it. A
feasibility note for LTI integration is retained in `docs/`.

---

## 10. A closing note on sequence

The temptation after a result like this is to improve the model. The measurements
argue otherwise.

The model missed nothing it was shown. Its one recall failure belongs to
retrieval, and its principal precision failure is traceable to an instruction that
was never given. Neither is fixed by a better model.

The two most valuable next steps are also the least technical: ask a teacher
whether the output is useful, and tell the model what the annotation convention
is. Both are cheap. Neither has been done.
