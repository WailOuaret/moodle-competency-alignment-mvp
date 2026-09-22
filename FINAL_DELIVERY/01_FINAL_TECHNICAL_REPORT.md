# Aligning Moodle Learning Resources with Competencies Using Retrieval-Constrained Language Models

## Final Technical Report

**Author:** Wail Ouaret
**Supervisors:** Marie-Hélène Abel, Le Ngoc Luyen
**Institution:** Université de Technologie de Compiègne — Heudiasyc (UMR 7253, CNRS)
**Date:** 22 September 2026
**Document status:** Final
**Project status:** Core research software complete; supervisor validation pending

---

## 1. Executive summary

This report describes a minimum viable system that proposes links between Moodle
learning resources and the competencies of a formal framework, and that presents
each proposal with a verbatim quotation from the source material as its
justification.

The system combines lexical retrieval with a candidate-constrained language
model. For each unit of course material, BM25 retrieves the five most similar
competencies from a 13-competency subset of the UTC *Génie Informatique*
framework. A language model then selects at most three of those five, and must
support each selection with an exact substring of the source text. A validator
rejects any response that invents a competency identifier or paraphrases its
evidence.

On a controlled corpus of 20 resources and 35 fragments, evaluated against 38
reference labels produced by a single annotator, the constrained system reaches a
micro recall of 0.9737 and a micro F1 of 0.8315, compared with 0.6842 and 0.7123
for a BM25 Top-1 baseline. Micro precision is marginally lower, 0.7255 against
0.7429. The system therefore trades a small amount of precision for a
substantially higher recall.

Two findings shape the interpretation. First, in the constrained Top-5
condition the single reference label the system fails to recover was absent from
the retrieved candidate set, and the model missed no reference label that was
available among its candidates. Whether a model given the full 13-competency
space would recover that label is a separate question and has not been measured. Second, precision errors are dominated by
parent-child granularity redundancy. Ten of the fourteen false positives are
top-level parent competencies predicted alongside their own correct child, and
the annotation convention — which assigns labels only at child level — was never
communicated to the model. The remaining four are topical confusions unrelated
to the hierarchy.

All 83 evidence quotations are exact substrings of their source fragments. A
subsequent manual review of those quotations judged 78.3 % to clearly support the
associated competency, 19.3 % to be partially relevant, and 2.4 % to provide no
justification. Requiring verbatim evidence therefore eliminates fabricated
support without guaranteeing that the support is pedagogically adequate; its
practical value is that inadequate reasoning becomes visible to a reviewer.

The reference annotations were produced by one person. No second annotator
participated and no inter-annotator agreement was measured. No teacher or
supervisor has yet reviewed the system's output. The results below therefore
characterise a working prototype with a well-described error profile; they do not
constitute a validated performance estimate.

---

## 2. Research context

Learning management systems accumulate material faster than that material can be
described. A Moodle course of moderate size contains pages, quizzes, assignments
and files that were authored over several years, often by different people, and
that carry no explicit relation to the competencies the programme claims to
develop. The competency framework and the course content exist in the same
system but remain unconnected.

This gap has practical consequences. A teacher revising a course cannot easily
determine which existing material already addresses a given competency. A
programme committee cannot verify that each competency is covered somewhere. A
student cannot navigate from a competency they wish to acquire to the resources
that teach it.

Manual tagging is the obvious remedy and does not scale. Assigning competencies
by hand across a full curriculum requires sustained effort from people whose time
is scarce, and the resulting annotations decay as content changes.

Automatic tagging with a language model is an equally obvious alternative and
raises a different problem. A teacher who cannot see why a tag was assigned has
no basis for accepting or rejecting it, and an unverifiable tag is of limited
use in an educational setting where the teacher remains accountable for the
course. The work reported here takes that constraint as its starting point.

---

## 3. Problem statement

Given a set of Moodle learning resources and a competency framework, produce
resource–competency alignments that a teacher can verify and correct, together
with evidence sufficient for that verification.

The requirement of verifiability, rather than accuracy alone, drives the system
design. A proposal accompanied by a quotation from the material can be assessed
by a reader in seconds. A proposal accompanied only by a confidence score cannot.

---

## 4. Research questions

**RQ1.** Can lexical retrieval restrict the competency search space sufficiently
to make constrained language-model selection tractable, without excluding the
correct competency?

**RQ2.** Does requiring verbatim textual evidence produce justifications that a
human reviewer finds adequate?

**RQ3.** What are the dominant failure modes of a retrieval-constrained alignment
system, and are they attributable to retrieval or to the model?

**RQ4.** Can the resulting alignments be presented in both directions — resource
to competency and competency to resource — in a form suitable for teacher
validation?

RQ2 is answered here only in part. The mechanical property of the evidence was
measured, and a manual assessment of pedagogical adequacy was carried out by the
researcher. Whether a teacher finds the evidence useful in practice remains
untested; the instrument for that measurement exists but has not been used.

---

## 5. Objectives

1. Construct a controlled corpus from a local Moodle instance with a known,
   verifiable competency framework.
2. Implement an extraction, normalisation and fragmentation pipeline that
   preserves provenance from Moodle to every evaluated unit.
3. Implement BM25 retrieval over competency descriptions and measure the recall
   ceiling it imposes.
4. Implement candidate-constrained language-model selection with mandatory exact
   evidence and strict response validation.
5. Produce a human-reviewed reference annotation for every fragment.
6. Evaluate at fragment and resource level with clearly defined metrics.
7. Characterise the error profile.
8. Build a teacher-facing interface supporting both directions of the mapping.
9. Ensure reproducibility through frozen artefacts and recorded checksums.

---

## 6. Scope

The scope was reduced on supervisory guidance, in order to complete and measure
one path through the problem rather than partially build several.

**Included.** A local Moodle instance; two courses; Moodle Pages and quiz
questions; a 13-competency subset of the UTC GI framework; extraction,
normalisation and fragmentation; BM25 retrieval; constrained language-model
selection; exact-evidence validation; aggregation to resource level; a
human-reviewed reference; fragment- and resource-level evaluation; error
analysis; manual evidence review; a hierarchy consistency check; a teacher
validation interface; reproducibility controls.

**Deferred.** A native Moodle PHP plugin; automatic write-back of competency
assignments into Moodle; LTI integration; PDF, slide, video, audio and OCR
ingestion; assignments and rubrics as corpus types; the full ROME 4.0 framework;
graph visualisation; recommendation and learning-path generation; curriculum
analytics; classification of the relation type between resource and competency
(teaches, assesses, supports, mentions); model fine-tuning; institution-wide
deployment.

Section 37 treats the deferred items as future work. None is presented here as
completed.

---

## 7. Methodological basis

The approach follows the line of work on evidence-grounded competency tagging
represented by Le, Abel and Laforge (2026), and adapts it to the constraints of
an operational learning management system. Two elements are retained from that
line: the requirement that a model's selection be supported by material quoted
from the source, and the use of a structured competency framework rather than
free-text skill labels.

The adaptation introduced here is the explicit separation of a retrieval stage
from a selection stage, which makes it possible to attribute a failure to one or
the other. That separation turns out to carry most of the analytical weight in
Section 28.

---

## 8. Moodle experimental environment

| Property | Value |
|---|---|
| Moodle version | 5.2.1+ (Build 20260722) |
| Deployment | Local development instance |
| Courses | `MVP-SW` — Software Engineering and Distributed Systems; `MVP-DATA` |
| Pages | 8 |
| Quizzes | 2 |
| Quiz questions | 12 |
| Primary extraction | Moodle REST web services |
| Secondary extraction | Direct SQL |

Page content and course structure were obtained through the web-service API.
Quiz question text is not exposed in a usable form by the web services on this
version, and was read directly from the Moodle database. This fallback is
specific to a local development deployment and would not transfer unchanged to a
managed institutional instance, where direct database access is normally
unavailable. It is recorded as a limitation in Section 34.

---

## 9. Competency framework

Thirteen competencies were selected from the UTC *Génie Informatique* framework:
three top-level competencies and ten children.

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

The subset was imported into Moodle as a native competency framework via CSV, and
independently normalised into a JSON Lines representation used by the retrieval
and selection stages. Both representations derive from the same source and carry
the same identifiers.

The framework encodes parent–child relations only. It contains no prerequisite or
related-to relations, and none were introduced at any stage. The hierarchy
consistency check described in Section 23 uses only relations present in the
framework.

---

## 10. Dataset construction

Twelve quiz questions are treated as independent research resources rather than
being folded into the two quizzes that contain them. A quiz as a whole seldom
assesses a single competency, whereas an individual question usually does;
collapsing questions into quizzes would therefore have introduced label noise
that no downstream stage could remove.

| Item | Count |
|---|---:|
| Normalised resources | 20 |
| — Moodle Pages | 8 |
| — Quiz questions | 12 |
| Fragments | 35 |
| — Page chunks | 23 |
| — Quiz-question fragments | 12 |
| Fragments in `MVP-SW` | 16 |
| Fragments in `MVP-DATA` | 19 |

---

## 11. Extraction

Course structure, Page content and quiz metadata were retrieved through the
Moodle web-service API and stored verbatim before any processing. Quiz question
text and answer options were extracted by SQL query. Every extracted record
retains its Moodle course identifier, course-module identifier, activity
identifier, section and title, so that any fragment evaluated later can be traced
to the Moodle object it came from.

---

## 12. Normalisation

Moodle stores Page content as HTML. Normalisation strips markup while preserving
block structure, resolves entities, collapses whitespace, and removes navigation
and boilerplate. Quiz questions are normalised into a single text field combining
the question stem with its answer options, since the options frequently carry the
technical vocabulary that identifies the competency.

Each normalised resource carries both a display text and a search text; the
latter is used for retrieval indexing.

---

## 13. Fragmentation

Pages are divided into fragments at paragraph boundaries, subject to a target
length, producing 23 fragments from 8 Pages. Each quiz question forms exactly one
fragment.

The fragment is the unit at which the model operates and at which the reference
annotation was produced. Every fragment retains the identifier of its parent
resource, its index within that resource, and the full provenance chain to
Moodle, which makes the aggregation described in Section 21 a lossless
regrouping.

---

## 14. Candidate retrieval

A BM25 index is constructed over the search text of the thirteen competencies,
formed from the short name and the description. For each fragment, the fragment
text is used as the query and the five highest-scoring competencies are retained.

The choice of five candidates is a deliberate trade-off. The value must be large
enough that the correct competency is almost always present, since the selection
stage cannot recover a competency that retrieval did not offer, and small enough
that the selection task remains a discrimination among plausible options rather
than a search over the whole framework. Section 26 reports the recall achieved at
one, three and five candidates.

---

## 15. Constrained model selection

Each fragment and its five candidates are assembled into a task carrying the
fragment text, the candidate descriptions with their hierarchy context, and an
explicit output contract.

| Parameter | Value |
|---|---|
| Model | `gemini-3.5-flash` |
| Temperature | 0 |
| Candidate space | BM25 Top-5 |
| Maximum selections | 3 |
| Abstention | Permitted |
| Evidence | Mandatory, exact substring |
| Output | JSON only |

The instructions require the model to select only from the supplied identifiers,
to select a competency only where the fragment provides direct pedagogical
evidence, to supply at least one verbatim quotation per selection, and to abstain
where no candidate is adequately supported.

Responses are checkpointed per fragment so that an interrupted run resumes rather
than restarting. The historical responses are treated as frozen experimental
artefacts and were never regenerated.

---

## 16. Evidence validation

Every response passes a validator before it is accepted. The validator confirms
that the fragment identifier matches the task, that the response is
schema-conformant, that no more than three competencies are selected, that every
identifier is among those supplied, that each selection carries at least one
quotation, that each quotation is an exact contiguous substring of the fragment
text, that confidence lies in the unit interval, and that an abstention carries no
selections.

A response failing any check is recorded as invalid and excluded. Of 35
responses, 35 were valid and none was rejected.

The exact-substring requirement is the central control on fabrication. A model
cannot assert support that does not appear in the source, because the assertion is
checked mechanically against the source.

---

## 17. Human-reviewed reference annotation

All 35 fragments were annotated against the thirteen-competency catalogue by the
researcher, using a terminal tool that presents one fragment at a time, records
selected competencies, supporting quotations, an ambiguity flag and free-text
comments, saves after each decision, and supports interruption and resumption.

The completed annotation was checked by a validator confirming that every source
fragment has exactly one annotation row, that no unknown fragment or competency
identifier appears, that no fragment text has drifted from its source, and that
no decision is incomplete. The validator reports 35 of 35 rows complete with no
errors.

| Property | Value |
|---|---|
| Annotated fragments | 35 |
| Reference labels | 38 |
| Multi-label fragments | 3 |
| Fragments flagged ambiguous | 1 |
| Fragments with no applicable competency | 0 |
| Annotator | Wail Ouaret |
| Date | 18 September 2026 |

Reference-label distribution, with predictions for comparison:

| Competency | Reference support | Predicted |
|---|---:|---:|
| `GI_C1` | 0 | 3 |
| `GI_C1_1` | 3 | 4 |
| `GI_C1_2` | 3 | 3 |
| `GI_C1_3` | 3 | 2 |
| `GI_C1_4` | 4 | 4 |
| `GI_C2` | 0 | 1 |
| `GI_C2_1` | 1 | 1 |
| `GI_C2_2` | 1 | 3 |
| `GI_C2_3` | 4 | 5 |
| `GI_C3` | 0 | 6 |
| `GI_C3_1` | 4 | 4 |
| `GI_C3_2` | 9 | 9 |
| `GI_C3_3` | 6 | 6 |
| **Total** | **38** | **51** |

The annotator assigned labels exclusively at child level. All three top-level
competencies have zero reference support. This convention was applied
consistently, but was never stated in the model's instructions, and it accounts
for most of the precision loss analysed in Section 28.

**Terminology.** These annotations are referred to throughout as
*human-reviewed reference annotations*. They were produced by one person. They
are not independent blinded gold annotations produced from scratch, and they are
not machine-generated. No second annotator participated, and no inter-annotator
agreement statistic was computed. Every score in this report is an agreement rate
with one annotator's judgement.

---

## 18. Evaluation methodology

Predictions and references are compared as sets of competency identifiers per
unit. Parent and child identifiers are distinct labels: predicting `GI_C3` does
not satisfy a reference of `GI_C3_2`.

Micro-averaged precision, recall and F1 pool true positives, false positives and
false negatives across all units. Macro-averaged values compute per-competency
scores and average them without weighting.

Because three competencies have zero reference support, two macro views are
reported. `macro_all_13` averages over the full label universe and so penalises
predicting an unsupported competency. `macro_gold_supported_labels` averages over
the ten competencies the reference actually contains. Neither replaces the other,
and reporting only one would misrepresent the system.

Retrieval is assessed with label-level Recall@K over the 38 reference labels,
fragment-level Hit@K over the 35 fragments, and mean reciprocal rank. Set-level
behaviour is assessed with exact-set match, coverage, abstention rate and the
mean number of predicted labels per unit.

---

## 19. Error analysis methodology

Each fragment is classified against a set of non-exclusive categories:
`correct_prediction`, `retrieval_failure`, `llm_missed_gold_label`,
`llm_wrong_selection`, `overprediction`, `underprediction`,
`parent_child_redundancy`, `ambiguous_gold`, `correct_abstention`,
`incorrect_abstention`, and `exact_but_weak_evidence`.

The distinction between `retrieval_failure` and `llm_missed_gold_label` carries
the analytical weight: the former marks a reference label absent from the
candidate set, the latter a reference label present in the candidate set but not
selected. Together they partition the possible causes of a missed label.

Because the categories overlap — a single mistake commonly triggers three of them
— each fragment is additionally assigned one `primary_error_category`, and the
reported flag counts must not be read as a partition of the corpus.

---

## 20. Evidence review methodology

Mechanical validity establishes only that a quotation appears in the source. It
does not establish that the quotation justifies the competency.

Each of the 83 quotations was therefore rated manually on a three-point scale:
`0` where the quotation does not justify the competency, `1` where it is
partially relevant or ambiguous, `2` where it clearly supports the competency.
The review tool presents one quotation at a time with its fragment and
competency, never suggests a rating, saves after each decision, and creates
timestamped backups.

Character offsets for each quotation were derived independently for audit
purposes; the quotations themselves were not modified.

This review was performed by the researcher, who also produced the reference
annotations. It is consequently a check of internal consistency rather than an
independent assessment.

---

## 21. Resource-level aggregation

Teachers act on resources rather than on fragments, so predictions are aggregated
upward. A resource is predicted to address a competency when any of its fragments
predicts that competency; the aggregate record retains the supporting fragment
identifiers, the individual confidences, a support count and the evidence
quotations.

The resource-level reference is **derived** from the fragment reference: for a
Page it is the union of its fragments' labels, and for a quiz question, already a
single-fragment resource, it is that fragment's labels. This derivation is
recorded in the output file itself. It is not an independent second annotation,
and the resulting figures inherit every property of the fragment annotation.

Activity-level competency links available in Moodle were deliberately not used as
question-level references. Such a link describes an entire quiz and would
constitute a considerably coarser signal presented as ground truth.

---

## 22. Hierarchy analysis

A consistency check examines each prediction set against the parent–child
relations in the framework and emits three kinds of warning:
`parent_child_redundancy` where a competency and its direct parent are both
predicted for the same unit; `granularity_conflict` where predictions mix levels
of the hierarchy in a way warranting review; and `invalid_hierarchy_reference`
where a predicted identifier refers to a relation not present in the framework.

The check is diagnostic. It emits warnings and does not alter predictions.

A separate ablation, described in Section 31, simulates the effect of preferring
the child when both a parent and its child are predicted. Its output is written to
a distinct location and the original predictions are left untouched.

---

## 23. Teacher validation interface

A Streamlit application presents the frozen corpus for review. It provides a
course and resource browser; a resource-to-competency view showing each proposal
with its confidence, its BM25 rank, its evidence quotation and rating, its
hierarchy context and any warning; a review page recording accept, reject, modify
and add decisions together with an assessment of evidence usefulness; a
competency-to-resource view; a read-only display of the evidence review; a
progress view; a read-only display of the measured results; an evidence-usefulness
pilot; and a validated-coverage view.

Displaying the BM25 rank is a deliberate design choice. A reviewer who sees that a
competency was never retrieved can distinguish a retrieval failure from a model
error, which is precisely the distinction that determines what should be improved.

The interface writes exactly one file. It does not write to Moodle, to the
reference annotations, to the model output, to the evidence review, or to any
metric file. Writes are atomic and preceded by a timestamped backup.

A second, separate application analyses arbitrary new Moodle resources on demand.
It is not part of the reported experiment and uses a different storage location.

---

## 24. Inverse view

The competency-to-resource index inverts the mapping, listing for each of the
thirteen competencies the resources predicted to address it, with course,
resource type, title, supporting fragments, evidence, confidence, support count
and review status.

All thirteen competencies have at least one predicted resource. This should be
read with care: the three top-level competencies appear only as a consequence of
the redundancy described in Section 28. Predicted coverage and validated coverage
are distinct quantities, and the interface keeps them visibly separate.

---

## 25. Experimental results

### 25.1 Retrieval

| Metric | Value |
|---|---:|
| Recall@1 | 0.6842 |
| Recall@3 | 0.8684 |
| Recall@5 | 0.9737 |
| Hit@1 | 0.7429 |
| Hit@3 | 0.8857 |
| Hit@5 | 0.9714 |
| Mean reciprocal rank | 0.8310 |

BM25 Top-1 evaluated as a standalone classifier:

| Metric | Value |
|---|---:|
| Micro precision | 0.7429 |
| Micro recall | 0.6842 |
| Micro F1 | 0.7123 |
| Macro F1 (all 13) | 0.5900 |
| True / false positives, false negatives | 26 / 9 / 12 |

Recall@5 of 0.9737 establishes the ceiling for the constrained system: 37 of 38
reference labels are available to the selection stage.

### 25.2 Constrained selection

| Metric | Value |
|---|---:|
| Micro precision | 0.7255 |
| Micro recall | 0.9737 |
| Micro F1 | 0.8315 |
| Macro precision / recall / F1 (all 13) | 0.6833 / 0.7436 / 0.6958 |
| Macro precision / recall / F1 (10 supported) | 0.8883 / 0.9667 / 0.9046 |
| Exact-set match | 0.6286 |
| Coverage | 1.0 |
| Abstention rate | 0.0 |
| Mean predicted labels per fragment | 1.4571 |

### 25.3 Comparison

| Metric | BM25 Top-1 | BM25 Top-5 + constrained model | Difference |
|---|---:|---:|---:|
| Micro precision | 0.7429 | 0.7255 | −0.0174 |
| Micro recall | 0.6842 | 0.9737 | +0.2895 |
| Micro F1 | 0.7123 | 0.8315 | +0.1191 |

---

## 26. Interpretation

**Recall coincides with the retrieval ceiling.** BM25 Recall@5 and the micro
recall of the constrained system are both 0.9737. The correspondence is exact
rather than approximate, and follows from the count in Section 28: the model
selected every reference label that retrieval made available.

**The single missed label is a retrieval failure.** For fragment
`quiz_question:1:4#f001`, whose reference is `GI_C1_3`, the retrieved candidates
were `GI_C1_2`, `GI_C3_2`, `GI_C3`, `GI_C1_1` and `GI_C1_4`. The correct
competency was absent, so the model could not have selected it. The count of
`llm_missed_gold_label` is zero across the corpus. Improving this case requires a
better retrieval stage, not a better model or prompt.

**The trade-off is real and must be stated as such.** The constrained system
raises micro recall by 0.2895 and micro F1 by 0.1191 relative to BM25 Top-1,
while lowering micro precision by 0.0174. It is not uniformly superior, and
describing it as such would misrepresent the measurement.

**Abstention is untested rather than accurate.** The abstention rate is 0.0, and
both `correct_abstention` and `incorrect_abstention` are zero. The reference
contains no fragment for which the correct answer is "no competency", so
abstaining was never the right response. The corpus cannot support any claim
about the system's ability to decline.

---

## 27. Error analysis

| Category | Count |
|---|---:|
| `correct_prediction` | 22 |
| `llm_wrong_selection` | 13 |
| `overprediction` | 13 |
| `parent_child_redundancy` | 10 |
| `exact_but_weak_evidence` | 12 |
| `retrieval_failure` | 1 |
| `underprediction` | 1 |
| `llm_missed_gold_label` | 0 |
| `ambiguous_gold` | 1 |
| `correct_abstention` / `incorrect_abstention` | 0 / 0 |

These categories overlap. The non-overlapping assignment:

| Primary category | Fragments |
|---|---:|
| `correct_prediction` | 21 |
| `llm_wrong_selection` | 12 |
| `ambiguous_gold` | 1 |
| `retrieval_failure` | 1 |
| **Total** | **35** |

### 27.1 The dominant error

Of 51 predicted labels, 37 are correct and 14 are false positives. Ten of those
fourteen are the three top-level competencies. In every affected fragment the
model predicted the parent alongside the correct child:

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

Each is a pure precision loss carrying no recall benefit. The model is not
mistaken about the subject matter; it is insufficiently decisive about
granularity.

The cause is partly a specification gap. The annotator labelled only at child
level and the prompt never stated that convention. Predicting `GI_C3` for a
fragment about machine learning is defensible in itself; the reference simply
does not count it. Correcting the instruction and re-measuring would be a more
honest remedy than pruning the output afterwards.

The remaining four false positives are topical rather than hierarchical:
`GI_C2_2` twice, where general distributed-systems vocabulary was read as
communicating architectures; `GI_C1_1` once, on the retrieval-failure fragment;
and `GI_C2_3` once, on a list of topics naming security terms without teaching
them.

### 27.2 The ambiguous fragment

Fragment `page:3#f003` was flagged ambiguous by the annotator before any
prediction was seen. Its reference is `GI_C1_4` and `GI_C2_3`, and the model
predicted exactly that pair. The one fragment the annotator found genuinely
difficult was labelled correctly. With a single instance this supports no
generalisation, and is recorded because it runs against the expected pattern.

---

## 28. Evidence analysis

| Property | Value |
|---|---:|
| Evidence quotations | 83 |
| Mechanically valid exact substrings | 83 (100 %) |
| Offset validity | 83 (100 %) |
| Rated `2`, clearly supporting | 65 (78.3 %) |
| Rated `1`, partially relevant | 16 (19.3 %) |
| Rated `0`, not justifying | 2 (2.4 %) |

Complete mechanical validity coexists with 21.7 % of quotations judged partial or
unsupported. The exact-substring constraint prevents fabrication; it does not
ensure that the quoted material demonstrates the competency. Its practical
contribution is that inadequate reasoning becomes visible rather than concealed
behind a score.

Two observations from the review reinforce findings obtained independently by the
metrics.

**Evidence quality varies sharply with hierarchy level.**

| Quotations for | Rated 2 | Rated 1 | Rated 0 |
|---|---:|---:|---:|
| Top-level competencies | 1 | 11 | 0 |
| Child competencies | 64 | 5 | 2 |

One of twelve quotations supporting a top-level competency was judged clearly
adequate, against 64 of 71 at child level. The reviewer's comments identify the
reason consistently, for instance that a quotation teaches `GI_C3_1` and supports
`GI_C3` only by hierarchy. The parent predictions are therefore not merely
redundant relative to an annotation convention; a reader assessing the quotation
on its own terms judged the justification weak.

**Both unsupported quotations fall on the retrieval-failure fragment.** For
`quiz_question:1:4#f001` the reviewer recorded that prototype testing belongs to
`GI_C1_3` rather than to the predicted `GI_C1_1` — independently naming the
competency that retrieval had failed to supply. The same fragment also
illustrates a secondary effect of the evidence constraint: unable to locate
genuine support, the model quoted a title token, `User_Centred_Design`. The
quotation is exact and passes mechanical validation, and is plainly inadequate to
a reader.

---

## 29. Resource-level results

| Metric | Value |
|---|---:|
| Micro precision | 0.6765 |
| Micro recall | 0.9583 |
| Micro F1 | 0.7931 |
| Macro F1 (all 13) | 0.7026 |
| Macro F1 (supported) | 0.9133 |
| Exact-set match | 0.4500 |
| Subset accuracy | 0.4500 |
| True / false positives, false negatives | 23 / 11 / 1 |
| Mean predicted labels | 1.70 |
| Mean reference labels | 1.20 |
| Mean absolute label-count error | 0.50 |
| Over-predicted resources | 11 |
| Under-predicted resources | 1 |
| Resources with parent–child redundancy | 9 |

Precision falls from 0.7255 at fragment level to 0.6765 at resource level.
Aggregation unions the labels of a resource's fragments, so a spurious parent on
any single fragment contaminates the whole resource. Exact-set match falls to
0.45: most resources receive a set that is not exactly correct, in nearly every
case through an additional parent label.

---

## 30. Post-hoc hierarchy ablation

A separate simulated prediction set was produced in which, where a parent and its
direct child are both predicted, the parent is removed. The original predictions
were not modified, and the output was written to a distinct location.

| Metric | Original | Child-preference | Difference |
|---|---:|---:|---:|
| Micro precision | 0.7255 | 0.9024 | +0.1769 |
| Micro recall | 0.9737 | 0.9737 | 0.0000 |
| Micro F1 | 0.8315 | 0.9367 | +0.1052 |
| Exact-set match | 0.6286 | 0.9143 | +0.2857 |
| Mean predicted labels | 1.4571 | 1.1714 | −0.2857 |
| Parent–child redundancies | 10 | 0 | −10 |

At resource level the corresponding figures are precision 0.6765 to 0.9200, F1
0.7931 to 0.9388, and exact-set match 0.45 to 0.90.

Recall is unchanged at both levels, because no top-level competency is ever a
correct label in this reference.

**What this establishes, and what it does not.** It establishes that the residual
precision loss is systematic, mechanically detectable from the framework
hierarchy alone, and attributable almost entirely to one failure mode. It does
not establish a general technique. The rule was formulated after inspecting the
errors and depends on a property of this particular reference; on a corpus where a
top-level competency is sometimes the correct label, the same rule would remove
true positives. The result is a diagnosis, not a validated method, and is
labelled as a post-hoc ablation wherever it appears.

---

## 31. Discussion

The measurements support a narrow but reasonably firm conclusion: on this corpus,
retrieval-constrained selection with mandatory verbatim evidence produces
alignments whose errors are systematic and diagnosable rather than arbitrary.

The clean separation between retrieval failure and selection failure is the most
useful structural property of the design. Because the candidate set is recorded
for every fragment, each missed label can be attributed to a specific stage. In
this corpus the attribution is unambiguous: retrieval accounts for all missed
labels and the model accounts for all false positives. That decomposition tells a
developer where to work, which an aggregate score does not.

The evidence requirement behaves differently from the way it is usually
motivated. It is commonly proposed as a guarantee of correctness; here it
functions as a guarantee of *inspectability*. Fabrication was eliminated
completely, yet more than a fifth of quotations were judged inadequate by a human
reader. The value delivered is that the inadequacy was visible in the quotation
itself.

The granularity problem is the clearest instance of a broader methodological
point. The system's largest measured defect arises from a convention that existed
only in the annotator's practice and was never communicated to the model. A
substantial part of what is reported as model error is more accurately
underspecification of the task. That distinction matters for what should be
changed first.

---

## 32. Threats to validity

**Construct validity.** Agreement with one annotator's labels is used as a proxy
for correct alignment. The parent–child result demonstrates the weakness of that
proxy directly: an identical output would score very differently under an
annotation convention that accepted a parent as partially correct.

**Internal validity.** The researcher designed the system, produced the reference
annotations and rated the evidence. The evidence review was conducted as a
separate pass over different material and independently reproduced two findings,
which is reassuring but is not independent observation.

**External validity.** The corpus was constructed for this study: two courses,
clean short text, coherent topics. Nothing here demonstrates behaviour on courses
with inconsistent formatting, mixed languages, administrative content or legacy
material.

**Statistical validity.** With 38 reference labels, one label is worth 2.63
points of recall. Differences are exact arithmetic on a small denominator, not
estimates with quantified uncertainty. No significance test was performed and none
should be inferred.

**Post-hoc analysis.** The hierarchy ablation was designed after the errors were
observed and evaluated on the data that motivated it.

---

## 33. Limitations

1. Small controlled corpus: 20 resources, 35 fragments, 38 reference labels, 13
   competencies, two courses.
2. A single annotator, with no second annotator and no measured inter-annotator
   agreement.
3. The evidence review was performed by the same person who produced the
   reference, and is therefore not independent.
4. No fragment has "no applicable competency" as its correct answer, so
   abstention quality cannot be assessed.
5. Micro precision is substantially a measure of agreement with a granularity
   convention.
6. Only Moodle Pages and quiz questions are covered.
7. The instance is local, and quiz-question extraction depends on direct database
   access.
8. The effect of candidate restriction is reasoned from the design rather than
   measured; the unconstrained comparison has not been run.
9. Mechanical evidence validity does not imply pedagogical adequacy.
10. The hierarchy ablation is post-hoc and specific to this reference.
11. No teacher or supervisor has reviewed the output.
12. The system depends on an external model API whose behaviour may change;
    reproduction relies on frozen artefacts and recorded checksums.
13. No significance testing is claimed.
14. Confidence scores were never calibrated and are not probabilities.

---

## 34. Reproducibility

Every experimental artefact is recorded with a SHA-256 checksum in a manifest
that also captures the Python version, pinned dependency versions, the model
identifier, temperature, candidate count, selection limit and corpus counts. The
manifest records a null checksum for artefacts that do not exist, rather than a
placeholder.

Historical model responses are treated as frozen and were never regenerated.
Reproduction proceeds from the recorded artefacts rather than from repeated API
calls, since a third-party model cannot be assumed stable over time.

Validation at the time of writing:

| Check | Result |
|---|---|
| Reference annotation validator | Passed, 35 of 35 |
| Test suite | 435 passed |
| Compilation check | Succeeded |
| Interface render check, network disabled | 14 of 14 pages |
| Protected artefact checksums | 21 of 21 unchanged |
| Secrets in generated outputs | None |

Operational instructions are given in the reproducibility guide rather than in
this report.

---

## 35. Validation status

| Item | Status |
|---|---|
| Core research software | Complete |
| Documentation | Complete |
| Final delivery package | Complete |
| Reference annotation (35 fragments) | Complete |
| Evidence review (83 quotations) | Complete |
| Teacher or supervisor validation | Pending |
| Evidence-usefulness pilot | Designed; no responses recorded |
| Unconstrained comparison | Optional; not run |
| LTI integration | Optional; future work |
| Native Moodle plugin | Deferred |

No teacher or supervisor has reviewed the corpus. There are 34 reviewable
resource–competency mappings and none has been assessed. Consequently no
acceptance, edit or rejection rate is reported anywhere in this delivery; the
summary stores null values rather than zeros, since zero would assert that
reviewers accepted nothing.

Two decisions exist in the repository, recorded by the researcher through the
runtime application on 18 September 2026. They concern an ad-hoc analysis rather
than the frozen corpus, and are reported separately as researcher decisions.

---

## 36. Future work

**Immediate, in order of value.**

1. Collect teacher decisions. The interface exists and the data does not; this is
   the largest gap between what has been built and what is known.
2. Introduce fragments with no applicable competency, so that abstention becomes
   measurable.
3. Run the unconstrained comparison over all thirteen competencies, to measure
   rather than assume the effect of candidate restriction. The software is
   implemented and audited as identical to the constrained condition except for
   the candidate space.
4. State the granularity convention in the model instructions and re-measure,
   instead of correcting the output afterwards.
5. Engage a second annotator on a subset, to obtain any agreement statistic.

**Medium term.** Larger corpora drawn from real courses; multiple institutions
and frameworks; dense or hybrid retrieval compared against BM25; additional
Moodle resource types, particularly assignments; classification of the relation
between resource and competency.

**Deferred.** A native Moodle plugin and automatic write-back remain deferred
unless reopened by the supervisors. LTI integration is recorded as an optional
future extension.

---

## 37. Conclusion

The work delivers an operational pipeline from a Moodle instance to
evidence-supported competency alignments, evaluated at two levels of granularity
against a human-reviewed reference, with a characterised error profile and a
teacher-facing interface for validation in both directions.

On this corpus, constrained selection raises micro recall from 0.6842 to 0.9737
and micro F1 from 0.7123 to 0.8315 relative to a BM25 Top-1 baseline, at a cost
of 0.0174 in micro precision. In this condition the only missed reference label
was absent from the candidate set and the model missed none that was available
to it; precision errors are dominated by a systematic confusion between levels
of the competency hierarchy — a confusion traceable in part to an
annotation convention that was never communicated to the model.

Requiring verbatim evidence eliminated fabricated justification entirely, while
leaving more than a fifth of quotations inadequate in a human reader's judgement.
The contribution of the constraint is therefore inspectability rather than
correctness, which is the property a teacher-facing tool most needs.

What has been established is a working prototype whose failure modes are
understood. What has not been established is whether the output is useful to a
teacher. The instrument for that measurement has been built and has not yet been
used, and no claim about teacher acceptance appears anywhere in this delivery.

---

## References

Le, N. L., Abel, M.-H., & Laforge, B. (2026). *From Learning Resources to
Competencies: LLM-Based Tagging with Evidence and Graph Constraints.*

---

## Companion documents

| Document | Content |
|---|---|
| `02_METHODOLOGY.md` | Detailed methodology |
| `03_RESULTS_AND_ANALYSIS.md` | Complete results and analysis |
| `04_SYSTEM_ARCHITECTURE.md` | Architecture and module responsibilities |
| `05_REPRODUCIBILITY_GUIDE.md` | Environment and commands |
| `06_DATA_AND_EXPERIMENT_DESCRIPTION.md` | Dataset inventory |
| `07_SUPERVISOR_DEMO_AND_TESTING_GUIDE.md` | Demonstration and validation procedure |
| `08_LIMITATIONS_AND_FUTURE_WORK.md` | Limitations and future work |
| `09_PROJECT_FILE_GUIDE.md` | Repository guide |
