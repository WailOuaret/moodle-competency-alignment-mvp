# Final experimental results

**Moodle learning resource-to-competency alignment — reduced MVP**

**Researcher:** Wail Ouaret
**Supervisors:** Marie-Hélène Abel · Le Ngoc Luyen
**Institution:** UTC / Heudiasyc / CNRS
**Date:** 2026-09-22
**Status:** measured pipeline `COMPLETE` · teacher validation `WAITING_FOR_HUMAN`

Every number in this report was read from a frozen file in `reports/metrics/`
or `reports/tables/`. Nothing is estimated, and results that do not yet exist
are named as missing rather than approximated.

---

## 1. Problem and scope

A Moodle course accumulates learning resources that are never explicitly linked
to the competencies the programme claims to teach. Teachers cannot answer
"which of my materials covers this competency?", and the reverse question is no
easier. Tagging by hand across a whole curriculum does not scale.

This MVP tests a narrow, checkable version of that problem: **can a retrieval
step plus a constrained language model propose competency alignments that a
teacher can actually verify, with evidence they can check?**

The emphasis on *verify* is the point of the design. The system is not asked to
be right unsupervised; it is asked to be auditable. Every selection must quote
the source text verbatim, so a teacher can judge the justification rather than
trust a score.

### What is in scope

Local Moodle · 2 courses · Pages and quiz questions · a 13-competency subset of
the UTC GI framework · extraction, normalization, fragmentation · BM25
retrieval · constrained LLM selection · exact-evidence validation · resource
aggregation · a human-reviewed reference · fragment- and resource-level
evaluation · error analysis · pedagogical evidence review · a minimal hierarchy
check · a teacher validation interface · reproducibility.

### What was deliberately deferred

A native Moodle PHP plugin, write-back into Moodle, LTI, PDFs / slides / video /
audio / OCR, assignments and rubrics, the full ROME 4.0 framework, graph
visualization, a recommendation engine or learning paths, a curriculum
analytics dashboard, teaches/assesses/supports/mentions classification,
fine-tuning, and institution-wide deployment.

These were cut on supervisor guidance to get one end-to-end path *measured*
rather than several partially built. Section 17 lists them as future work; none
is presented here as done.

---

## 2. Moodle setup

| Item | Value |
|---|---|
| Moodle | 5.2.1+ (Build 20260722), local development instance |
| Courses | `MVP-SW` (Software Engineering and Distributed Systems), `MVP-DATA` |
| Pages | 8 |
| Quizzes | 2 |
| Quiz questions | 12 |
| Primary extraction | Moodle REST web services |
| Fallback extraction | direct SQL, for quiz question text |

Page content came through the REST API. Quiz *question* text is not exposed by
the web services in a usable form on this version, so it was read directly from
the database. That fallback is honest but local-development specific: it would
not transfer unchanged to a managed institutional instance, and it is listed as
a limitation in Section 16.

---

## 3. Competency framework

Thirteen UTC GI competencies: three top-level parents and ten children.

```
GI_C1  Concevoir et développer des logiciels
  ├── GI_C1_1  Développement logiciel (conception, paradigmes, performance, déploiement)
  ├── GI_C1_2  Qualité logicielle et ingénierie soutenable
  ├── GI_C1_3  IHM et UX (mobile/VR/AR)
  └── GI_C1_4  Logiciels distribués et passage à l'échelle
GI_C2  Concevoir et mettre en œuvre des architectures informatiques
  ├── GI_C2_1  Architectures logicielles et matérielles (ressources/énergie)
  ├── GI_C2_2  Architectures communicantes (réseaux, cloud/fog/IoT)
  └── GI_C2_3  Architectures sûres et cybersécurité
GI_C3  Concevoir et mettre en œuvre des systèmes de traitement et d'analyse
  ├── GI_C3_1  Représentation et raisonnement sur les connaissances
  ├── GI_C3_2  Données et bases de données (SQL/NoSQL) & décision
  └── GI_C3_3  Data science / ML / NLP
```

The framework was imported into Moodle as a competency framework, then
normalized into `data/processed/competencies.jsonl` with a stable `idnumber`,
`shortname`, `description_text`, `depth` and `parent_idnumber` per competency.

The hierarchy is **parent/child only**. There are no prerequisite or related-to
relations in this framework, and none were invented anywhere in the pipeline.

---

## 4. Data

| Item | Count |
|---|---:|
| Normalized resources | **20** |
| — Pages | 8 |
| — Quiz questions (independent resources) | 12 |
| Fragments | **35** |
| — `page_chunk` | 23 |
| — `quiz_question` | 12 |
| Fragments in `MVP-SW` / `MVP-DATA` | 16 / 19 |
| Reference competency labels | **38** |
| Multi-label reference fragments | 3 |
| Ambiguous reference fragments | 1 (`page:3#f003`) |
| Reference `NONE` fragments | **0** |

Each quiz question is treated as its own research resource rather than folded
into its quiz, because a quiz as a whole rarely assesses one competency while an
individual question usually does. Pages are chunked; a question is a single
fragment.

### Reference-label distribution

| Competency | Reference support | Predicted |
|---|---:|---:|
| `GI_C1` | **0** | 3 |
| `GI_C1_1` | 3 | 4 |
| `GI_C1_2` | 3 | 3 |
| `GI_C1_3` | 3 | 2 |
| `GI_C1_4` | 4 | 4 |
| `GI_C2` | **0** | 1 |
| `GI_C2_1` | 1 | 1 |
| `GI_C2_2` | 1 | 3 |
| `GI_C2_3` | 4 | 5 |
| `GI_C3` | **0** | 6 |
| `GI_C3_1` | 4 | 4 |
| `GI_C3_2` | 9 | 9 |
| `GI_C3_3` | 6 | 6 |
| **Total** | **38** | **51** |

The human annotator labelled **only at child level**: all three parents have
zero reference support. The model nonetheless predicted a parent 10 times. This
single fact drives most of the error analysis in Section 9.

### The reference annotations — what they are and are not

The 35 rows in `data/gold/manual_fragment_annotations.csv` are
**human-reviewed reference annotations**, finalized by Wail Ouaret on
2026-09-18 and passing `scripts/12_validate_manual_annotations.py --mode final`
with 0 missing, 0 unknown, 0 duplicate, 0 source-text mismatch and 0 incomplete
rows.

They are **not** independent blinded gold produced from scratch, and they are
**not** AI-generated gold. There is one annotator, no second annotator, and
therefore **no measured inter-annotator agreement**. Every score below inherits
that limitation.

---

## 5. BM25 retrieval baseline

`reports/metrics/bm25_metrics.json`

| Metric | Value |
|---|---:|
| Recall@1 | 0.6842 |
| Recall@3 | 0.8684 |
| **Recall@5** | **0.9737** |
| Hit@1 | 0.7429 |
| Hit@3 | 0.8857 |
| Hit@5 | 0.9714 |
| MRR | 0.8310 |
| Top-1 micro precision | 0.7429 |
| Top-1 micro recall | 0.6842 |
| Top-1 micro F1 | 0.7123 |
| Top-1 macro P / R / F1 (all 13) | 0.6538 / 0.5620 / 0.5900 |
| Top-1 TP / FP / FN | 26 / 9 / 12 |

Recall@K is label-level over the 38 reference labels. Hit@K and MRR are
fragment-level over the 35 fragments with a non-empty reference. Parent and
child are distinct labels: retrieving `GI_C3` does not satisfy `GI_C3_2`.

**Recall@5 = 0.9737 is the ceiling for everything downstream.** A model
restricted to the Top-5 can never recover the one reference label BM25 failed
to retrieve. Choosing K = 5 fixes that ceiling at 37 of 38 labels.

---

## 6. BM25 Top-5 + constrained Gemini

`reports/metrics/constrained_llm_metrics.json`

Configuration: `gemini-3.5-flash`, temperature 0, candidates restricted to the
BM25 Top-5, at most 3 selections, abstention permitted, every selection
required to carry an evidence quote that is an exact contiguous substring of
the fragment. 35/35 responses returned, 35/35 valid, 0 invalid accepted, 0
missing.

| Metric | Value |
|---|---:|
| Micro precision | 0.7255 |
| **Micro recall** | **0.9737** |
| Micro F1 | 0.8315 |
| Macro P / R / F1 (all 13) | 0.6833 / 0.7436 / 0.6958 |
| Macro P / R / F1 (gold-supported 10) | 0.8883 / 0.9667 / 0.9046 |
| Exact-set match | 0.6286 |
| Coverage | 1.0 |
| Abstention rate | 0.0 |
| Average predicted labels / fragment | 1.4571 |

### Why two macro views are reported

A single macro number is ambiguous here. Three of the thirteen labels have zero
reference support, so:

- `macro_all_13` = **0.6958** averages those three in as zeros. It *penalises*
  predicting an unsupported parent, which is a real defect worth penalising.
- `macro_gold_supported_labels` = **0.9046** averages over the ten labels the
  reference actually contains. It describes performance on labels that were
  genuinely in play.

Both are reported (`reports/metrics/macro_label_views.json`). Neither replaces
the other, and quoting only the higher one would misrepresent the system. The
original frozen metric files were not overwritten when this second view was
added.

---

## 7. Interpretation

This is the part that matters, and it is more specific than "the LLM helped".

**1. Recall is exactly at the retrieval ceiling.** BM25 Top-5 Recall = 0.9737
and constrained Gemini micro recall = 0.9737. Identical.

**2. The model missed nothing it was offered.** `llm_missed_gold_label = 0`.
Whenever the correct competency was among the five candidates, the model
selected it — in all 37 available cases.

**3. The one miss is therefore a retrieval failure, not a model failure.**
Fragment `quiz_question:1:4#f001` has reference `GI_C1_3` (IHM/UX). The BM25
Top-5 was `GI_C1_2, GI_C3_2, GI_C3, GI_C1_1, GI_C1_4` — `GI_C1_3` is absent, so
the model could not have chosen it. It picked `GI_C1_1` instead. Improving this
case requires better retrieval, not a better model.

**4. The dominant error is overprediction, and it is concentrated.** Of 51
predicted labels, 37 are correct and **14 are false positives**. Ten of those
14 — **71%** — are the three parent competencies that carry zero reference
support. The remaining four are spread across `GI_C1_1`, `GI_C2_2` and
`GI_C2_3`.

**5. Parent-child redundancy is the specific mechanism.** In all 10 affected
fragments the model predicted the parent *and* the correct child, where the
reference has only the child:

| Fragment | Reference | Predicted |
|---|---|---|
| `page:1#f002` | `GI_C1_1` | `GI_C1`, `GI_C1_1` |
| `page:2#f001` | `GI_C1_3` | `GI_C1`, `GI_C1_3` |
| `page:4#f003` | `GI_C2_3` | `GI_C2`, `GI_C2_3` |
| `quiz_question:1:1#f001` | `GI_C1_1` | `GI_C1`, `GI_C1_1` |
| `page:5#f001` | `GI_C3_1` | `GI_C3`, `GI_C3_1` |
| `page:8#f001` | `GI_C3_3` | `GI_C3`, `GI_C3_3` |
| `page:8#f004` | `GI_C3_3` | `GI_C3`, `GI_C3_3` |
| `quiz_question:2:8#f001` | `GI_C3_1` | `GI_C3`, `GI_C3_1` |
| `quiz_question:2:9#f001` | `GI_C3_2` | `GI_C3`, `GI_C3_2` |
| `quiz_question:2:12#f001` | `GI_C3_3` | `GI_C3`, `GI_C3_3` |

Every one is a pure precision loss with no recall gain. The model is not
confused about the topic — it is insufficiently decisive about *granularity*.
This is a specification problem as much as a model problem: the prompt never
told it that the annotator labels at child level only.

**6. The trade-off, stated plainly.** Against BM25 Top-1:

| Metric | BM25 Top-1 | BM25 Top-5 + Gemini | Δ |
|---|---:|---:|---:|
| Micro precision | 0.7429 | 0.7255 | **−0.0174** |
| Micro recall | 0.6842 | 0.9737 | **+0.2895** |
| Micro F1 | 0.7123 | 0.8315 | **+0.1191** |

The constrained model buys a large recall gain for a small precision loss, and
improves F1. It does **not** win on every measure: BM25 Top-1 is slightly more
precise. Claiming the LLM "wins overall" without that qualification would
misstate the result.

**7. Abstention is untested, not good.** Abstention rate is 0.0 and
`correct_abstention` and `incorrect_abstention` are both 0. This is not evidence
of good judgement: the reference set contains **no `NONE` fragments**, so there
was never an occasion on which abstaining was correct. The corpus cannot answer
whether the system knows when to say nothing. Any future corpus should include
deliberately off-topic material.

---

## 8. Evidence quality

`reports/metrics/evidence_review_summary.json`

The model produced **83 evidence quotes** across its 51 selections. Two
independent checks were applied.

**Mechanical validity — 83/83 (100%).** Every quote is an exact contiguous
substring of its fragment. Character offsets were derived independently and
`offset_valid` is `true` for all 83. No quote was paraphrased or invented.

**Pedagogical sufficiency — a human rated all 83** (Human Gate 2, Wail Ouaret,
2026-09-18, resumable terminal helper with timestamped backups):

| Rating | Meaning | Count | Share |
|---|---|---:|---:|
| `2` | clearly supports the competency | 65 | 78.31% |
| `1` | partially relevant / ambiguous | 16 | 19.28% |
| `0` | does not justify the competency | 2 | 2.41% |

**Mechanical validity is not pedagogical sufficiency.** 100% of quotes were
exact, yet 18 of 83 (21.7%) were judged partial or unsupported. An exact-quote
constraint stops fabrication; it does not guarantee the quote proves anything.
That distinction is the main methodological finding of this section.

### Two convergent signals

The evidence review was conducted per quote, without reference to the error
analysis. It nevertheless reproduced both main findings:

**Both `0` ratings fall on the single retrieval-failure fragment.** For
`quiz_question:1:4#f001` / `GI_C1_1` the reviewer wrote *"Prototype testing is
HCI/UX (GI_C1_3), not GI_C1_1 software development"* — independently naming
`GI_C1_3`, which is exactly the reference label BM25 failed to retrieve. Two
different error signals converge on the same fragment and the same correct
answer.

**Parent-level quotes are rated far worse than child-level ones:**

| Quotes for | rating 2 | rating 1 | rating 0 |
|---|---:|---:|---:|
| Parent competencies (`GI_C1`, `GI_C2`, `GI_C3`) | 1 | 11 | 0 |
| Child competencies | 64 | 5 | 2 |

Only 1 of 12 parent quotes was judged clearly supporting, against 64 of 71 child
quotes. The reviewer's comments repeatedly say the same thing — *"parent GI_C3
only by hierarchy"*. So parent predictions are not merely redundant against the
reference; a human independently judged their justifications weak. The
hierarchy problem shows up in the evidence, not only in the score.

---

## 9. Error analysis

`reports/metrics/error_summary.json`, `reports/tables/error_analysis.csv`,
`reports/tables/error_examples.csv`

| Category | Count |
|---|---:|
| `correct_prediction` | 22 |
| `llm_wrong_selection` | 13 |
| `overprediction` | 13 |
| `parent_child_redundancy` | 10 |
| `exact_but_weak_evidence` | 12 |
| `retrieval_failure` | 1 |
| `underprediction` | 1 |
| `llm_missed_gold_label` | **0** |
| `ambiguous_gold` | 1 |
| `correct_abstention` / `incorrect_abstention` | 0 / 0 |

**These flags overlap and are not a partition of the 35 fragments.** One
fragment can be flagged `llm_wrong_selection`, `overprediction` and
`parent_child_redundancy` at once. To give a non-overlapping view, each fragment
also carries a single `primary_error_category`:

| Primary category | Fragments |
|---|---:|
| `correct_prediction` | 21 |
| `llm_wrong_selection` | 12 |
| `ambiguous_gold` | 1 |
| `retrieval_failure` | 1 |
| **Total** | **35** |

### Retrieval versus model

The split is unusually clean. Exactly one reference label was missed, and it was
missed by retrieval. The model contributed **zero** misses and all 14 false
positives. Retrieval limits recall; the model limits precision.

### The ambiguous case

`page:3#f003` was flagged ambiguous by the annotator at annotation time —
before any prediction was seen. Its reference is `GI_C1_4; GI_C2_3`, and the
model predicted exactly that pair. The one fragment the human found genuinely
hard, the model got exactly right, which is worth stating precisely because it
cuts against a tidy narrative.

---

## 10. Resource-level results

`reports/metrics/resource_level_metrics.json`

Teachers act on resources, not fragments, so the system was also scored at
resource level.

**The resource-level reference is derived, not independently annotated.** For a
Page it is the union of the human-reviewed labels of that Page's fragments; for
a quiz question, which is already a single-fragment resource, it is that
fragment's reference. Activity-level Moodle competency links were deliberately
**not** used as question-level gold — they describe a whole quiz and would be a
much coarser signal masquerading as ground truth. This derivation is recorded
inside the metrics file itself.

| Metric | Value |
|---|---:|
| Micro precision | 0.6765 |
| Micro recall | 0.9583 |
| Micro F1 | 0.7931 |
| Macro F1 (all 13) | 0.7026 |
| Macro F1 (gold-supported) | 0.9133 |
| Exact-set match | 0.4500 |
| Subset accuracy | 0.4500 |
| Micro TP / FP / FN | 23 / 11 / 1 |
| Average predicted labels | 1.70 |
| Average reference labels | 1.20 |
| Average absolute label-count error | 0.50 |
| Resources over-predicted | 11 |
| Resources under-predicted | 1 |
| Resources with parent-child redundancy | 9 |

Precision drops from 0.7255 to 0.6765 when moving fragment → resource, because
aggregation unions each fragment's labels: a spurious parent on any one fragment
contaminates the whole resource. Recall stays high (0.9583). Exact-set match
falls to 0.45 — **more than half of resources get a set that is not exactly
right**, almost always by including a redundant parent.

---

## 11. Function A — resource → competencies

`data/processed/resource_predictions.jsonl` · 20/20 resources · **34 predicted
resource-competency alignments**.

Each alignment carries supporting fragment IDs, per-fragment confidences, a
support count, and the exact evidence quotes.

**Example — `page:1`, "Software Development Lifecycle and Deployment" (MVP-SW)**

| Predicted | Confidence | Support | Reference? |
|---|---:|---:|---|
| `GI_C1_1` | 0.95 | 2 fragments | ✅ yes |
| `GI_C1_2` | — | — | ✅ yes |
| `GI_C1` | 0.90 | 1 fragment | ❌ no — parent redundancy |

Evidence for the `GI_C1` prediction: *"A successful software product therefore
combines user requirements, software design, programming paradigms, performance
evaluation, testing, deployment, and maintenance."* — an exact quote, but the
same sentence already justifies `GI_C1_1`. The human rated this quote `1`,
partial. This one resource shows the system's strength and its main weakness
side by side.

---

## 12. Function B — competency → resources

`data/processed/competency_resource_index.jsonl` · 13/13 competencies, and
**every competency has at least one predicted resource**. This is the inverse
direction the supervisors asked for: from a competency to the material that
covers it.

For each competency the index lists the matching resources with course,
resource type, title, supporting fragments, evidence quotes, confidence, a
support count, and teacher decision status (currently `pending` for all).

A caution when reading it: the three parent competencies have entries only
because of the redundancy described in Section 7. `GI_C3` shows 6 matches, none
of which the reference supports. Coverage in the inverse index is *predicted*
coverage, not validated coverage. Validated coverage lives on the separate
coverage page and is empty until teacher decisions exist.

---

## 13. Teacher review

**Status: `WAITING_FOR_HUMAN`. No teacher decision exists for the research
corpus, so no acceptance, edit or rejection rate is reported.**

`reports/metrics/teacher_review_summary.json` records 34 reviewable mappings,
0 reviewed, 34 pending, and `null` for every rate. The rates are null rather
than 0.0 deliberately: 0.0 would read as "no teacher accepted anything", which
is a finding, whereas null correctly says nothing was reviewed.

What exists, recorded honestly:

- **2 researcher decisions** in `data/reviews/teacher_reviews.csv`, made by Wail
  Ouaret on 2026-09-18 through the separate *runtime* app (one `REJECT` of
  `GI_C3`, one `ACCEPT` of `GI_C3_1` — itself an instance of the parent-child
  pattern). These are researcher decisions about a runtime analysis, **not**
  teacher validation of the research corpus, and are reported separately.
- **0 teacher decisions and 0 supervisor decisions.**
  `teacher_or_supervisor_validation_performed = false`.

The interface to collect them is built and renders cleanly (Section 18); the
human step has not happened. See `reports/FINAL_TEACHER_REVIEW.md`.

---

## 14. Post-hoc minimal graph ablation

`reports/metrics/graph_check_summary.json`,
`reports/tables/graph_ablation_comparison.csv`

Labelled **POST-HOC MINIMAL GRAPH ABLATION**. It is *not* part of the original
Gemini run, and it did not modify a single prediction:
`original_predictions_modified = false`.

### Warnings

Using only the parent/child relations actually present in the framework:

| Warning | Count |
|---|---:|
| Fragments checked | 35 |
| `parent_child_redundancy` | 10 fragments (10 pairs) |
| `granularity_conflict` | 7 fragments (7 pairs) |
| `invalid_hierarchy_reference` | **0** |
| Warning rate | 0.2857 |

Most frequent redundant parent: `GI_C3` (6 of 10). Per course: 6 in MVP-DATA,
4 in MVP-SW.

### The ablation

A separate, non-destructive simulated prediction set was produced in which, when
a parent and its direct child are both predicted for a fragment, the parent is
dropped — **in the ablation output only**
(`data/experiments/graph_child_preference_predictions.jsonl`).

| Metric | Original | Child-preference | Δ |
|---|---:|---:|---:|
| Micro precision | 0.7255 | **0.9024** | +0.1769 |
| Micro recall | 0.9737 | 0.9737 | **0.0000** |
| Micro F1 | 0.8315 | **0.9367** | +0.1052 |
| Exact-set match | 0.6286 | **0.9143** | +0.2857 |
| Avg predicted labels | 1.4571 | 1.1714 | −0.2857 |
| Parent-child redundancies | 10 | **0** | −10 |

At resource level the effect is larger still: precision 0.6765 → 0.9200, F1
0.7931 → 0.9388, exact-set 0.45 → 0.90.

**Recall is unchanged at every level.** Dropping the redundant parent costs
nothing in recall because no parent was ever a correct label in this reference —
which follows directly from the annotator labelling only at child level.

**How much to conclude from this.** The ablation confirms the *diagnosis*: this
one failure mode accounts for essentially all of the precision gap. It does not
establish a general technique. The rule exploits a property of this reference
(child-level-only annotation) and was applied after seeing the errors, so the
gain is not an out-of-sample result. On a corpus where a parent label is
sometimes genuinely correct, the same rule would destroy recall. The honest
reading is: *the errors are systematic and addressable*, not *a 0.94 F1 system
exists*.

---

## 15. Optional unconstrained all-13 comparison

**Status: `OPTIONAL` — software complete, experiment not run. No result is
reported because none exists.**

The constrained condition restricts the model to the BM25 Top-5. That caps
recall at the retrieval ceiling and may also flatter precision by hiding
implausible options. Measuring the effect requires a second run where the
candidate space is all 13 competencies.

That software is built and tested (`src/moodle_competency/unconstrained_llm.py`,
scripts 24–26, 44 tests, none of which calls an API). The 35 tasks are built,
and an automated audit confirms the two conditions differ in nothing but the
candidate space: identical model, temperature, selection limit, abstention rule,
exact-substring evidence requirement, output schema, fragment text and
validator, with 0 fragment-text mismatches and 0 instruction mismatches across
all 35 fragments.

The live run spends API quota and therefore requires explicit researcher
authorization; the runner refuses to execute without it. Nothing about the
effect of candidate restriction is claimed here, in either direction.

---

## 16. Limitations

Stated fully, because most of them bound how far these numbers travel.

1. **Small controlled corpus.** 20 resources, 35 fragments, 38 reference labels,
   13 competencies, 2 courses, built for this study. With 38 labels, one label
   is worth 2.6 points of recall. These are existence-proof numbers, not
   population estimates, and no confidence interval is claimed.
2. **Single-annotator reference.** One annotator, no second annotator, **no
   measured inter-annotator agreement**. The reference is human-reviewed, not
   independent blinded gold from scratch, and not AI-generated gold.
3. **Non-independent evidence review.** The same person produced the reference
   and the 83 pedagogical ratings, so the evidence judgement is not independent
   of the labelling judgement. The convergence noted in Section 8 is meaningful
   but is not two independent observers.
4. **No reference `NONE` fragments.** Abstention quality is untestable on this
   corpus. The 0.0 abstention rate is a property of the data, not a virtue of
   the system.
5. **Pages and quiz questions only.** No assignments, rubrics, PDFs, slides,
   video, audio or OCR. Text is clean and short; nothing here shows the pipeline
   survives messy real material.
6. **Local Moodle, with a local-specific fallback.** The SQL route for quiz
   question text would not transfer unchanged to a managed institutional
   instance.
7. **Three parent competencies have zero reference support** yet receive 10
   predictions. This is why two macro views are reported; a single macro number
   would be misleading either way.
8. **The effect of candidate restriction is inferred, not measured.** The
   unconstrained comparison has not been run (Section 15).
9. **Mechanical evidence validity is not pedagogical sufficiency** — 100% versus
   78.3% clear.
10. **The graph ablation is post-hoc and reference-specific** (Section 14). It
    is a diagnosis, not a validated technique.
11. **Teacher usefulness is unmeasured.** 0 teacher and 0 supervisor decisions.
    The 2 existing decisions are researcher decisions and are never counted as
    teacher validation.
12. **External model dependency.** Results depend on `gemini-3.5-flash` through a
    third-party API whose behaviour may drift. Historical responses must never be
    regenerated; reproduction is by frozen artefact and hash, not by re-running.
13. **No significance testing.** Sample size and single-rater design do not
    support inferential claims, so none are made (`significance_tests:
    not_run`).
14. **Confidence scores are uncalibrated.** They are reported as the model gave
    them and were never validated against correctness.

---

## 17. Deferred future work

Explicitly deferred, and **not** done:

| Item | Status |
|---|---|
| Native Moodle PHP plugin | `DEFERRED` |
| Automatic write-back into Moodle | `DEFERRED` |
| LTI integration | `DEFERRED` |
| PDFs, slides, video, audio, OCR | `DEFERRED` |
| Assignments and rubrics as corpus types | `DEFERRED` |
| Full ROME 4.0 framework | `DEFERRED` |
| Graph visualization | `DEFERRED` |
| Recommendation engine / learning paths | `DEFERRED` |
| Curriculum analytics dashboard | `DEFERRED` |
| teaches / assesses / supports / mentions classification | `DEFERRED` |
| Fine-tuning | `DEFERRED` |
| Institution-wide deployment | `DEFERRED` |
| Unconstrained all-13 comparison | `OPTIONAL` — software ready, not run |

The most valuable next steps, in the order the evidence suggests:

1. **Collect real teacher decisions.** The interface exists; the data does not.
   This is the largest gap between what is built and what is known.
2. **Add `NONE` fragments to the corpus** so abstention becomes testable.
3. **Run the unconstrained comparison** to measure rather than assume the effect
   of candidate restriction.
4. **Fix granularity at the prompt, not after the fact** — state the annotation
   convention in the instructions and re-measure, instead of post-hoc pruning.
5. **A second annotator on a subset**, to get any agreement figure at all.

---

## 18. Software and reproducibility status

| Check | Result |
|---|---|
| `scripts/12_validate_manual_annotations.py --mode final` | **PASSED** (35/35) |
| `python -m pytest -q` | **435 passed** |
| `python -m compileall -q src scripts tests app` | succeeded |
| Streamlit render check (14 pages, network blocked) | **all OK** |
| Protected experimental file hashes | unchanged |
| Secrets in generated reports | none (`contains_secrets: false`) |

`reports/reproducibility_manifest.json` records Python 3.12.3, pinned dependency
versions, the model ID, temperature, candidate count, selection limit, corpus
counts, unambiguous reference counts, and SHA-256 hashes of every experimental
artefact — including `None` for outputs that do not exist yet, rather than a
placeholder.

**Overall status: `WAITING_FOR_HUMAN`.** The measured pipeline is complete and
internally consistent. The project is not `COMPLETE` while teacher validation
has not been performed.
