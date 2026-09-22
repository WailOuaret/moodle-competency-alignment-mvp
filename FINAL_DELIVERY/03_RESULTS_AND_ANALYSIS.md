# Results and Analysis

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

Every figure below is read from a frozen result file under `reports/metrics/` or
`reports/tables/`. Results that do not exist are named as absent rather than
estimated.

---

## 1. Corpus

| Property | Value |
|---|---:|
| Courses | 2 (`MVP-SW`, `MVP-DATA`) |
| Moodle Pages | 8 |
| Quizzes | 2 |
| Quiz questions | 12 |
| Normalised resources | 20 |
| Fragments | 35 |
| — Page chunks | 23 |
| — Quiz-question fragments | 12 |
| Fragments in `MVP-SW` / `MVP-DATA` | 16 / 19 |
| Competencies | 13 (3 parents, 10 children) |
| Reference labels | 38 |
| Multi-label fragments | 3 |
| Ambiguous fragments | 1 |
| Fragments with no applicable competency | 0 |

Source: `data/processed/`, `data/gold/manual_fragment_annotations.csv`.

### Label distribution

| Competency | Reference support | Predicted | False positives |
|---|---:|---:|---:|
| `GI_C1` | 0 | 3 | 3 |
| `GI_C1_1` | 3 | 4 | 1 |
| `GI_C1_2` | 3 | 3 | 0 |
| `GI_C1_3` | 3 | 2 | 0 |
| `GI_C1_4` | 4 | 4 | 0 |
| `GI_C2` | 0 | 1 | 1 |
| `GI_C2_1` | 1 | 1 | 0 |
| `GI_C2_2` | 1 | 3 | 2 |
| `GI_C2_3` | 4 | 5 | 1 |
| `GI_C3` | 0 | 6 | 6 |
| `GI_C3_1` | 4 | 4 | 0 |
| `GI_C3_2` | 9 | 9 | 0 |
| `GI_C3_3` | 6 | 6 | 0 |
| **Total** | **38** | **51** | **14** |

The three competencies with zero reference support are the three top-level
competencies, and they account for 10 of the 14 false positives. This single
observation organises most of the analysis that follows.

---

## 2. Retrieval

Source: `reports/metrics/bm25_metrics.json`.

| Metric | Value |
|---|---:|
| Recall@1 | 0.6842 |
| Recall@3 | 0.8684 |
| Recall@5 | 0.9737 |
| Hit@1 | 0.7429 |
| Hit@3 | 0.8857 |
| Hit@5 | 0.9714 |
| Mean reciprocal rank | 0.8310 |

Recall@K is label-level over the 38 reference labels; Hit@K and MRR are
fragment-level over the 35 fragments.

BM25 Top-1 as a standalone classifier:

| Metric | Value |
|---|---:|
| Micro precision | 0.7429 |
| Micro recall | 0.6842 |
| Micro F1 | 0.7123 |
| Macro precision (all 13) | 0.6538 |
| Macro recall (all 13) | 0.5620 |
| Macro F1 (all 13) | 0.5900 |
| Macro F1 (10 supported) | 0.7670 |
| True positives / false positives / false negatives | 26 / 9 / 12 |

### Discussion

Lexical retrieval alone places the correct competency first in roughly
two-thirds of cases and within five in almost all. An MRR of 0.8310 indicates the
correct competency is typically at rank one or two when present.

Recall@5 of 0.9737 is the operative figure: it **fixes the ceiling** for any
system that selects only from the Top-5. Thirty-seven of 38 reference labels are
reachable; one is not, irrecoverably.

The gap between Recall@1 (0.6842) and Recall@5 (0.9737) is the margin a selection
stage can exploit. It is large enough to be worth a second stage, which is the
premise of the design.

---

## 3. Constrained selection

Source: `reports/metrics/constrained_llm_metrics.json`. Configuration:
`gemini-3.5-flash`, temperature 0, BM25 Top-5 candidates, at most 3 selections,
mandatory exact evidence. 35 of 35 responses valid; none rejected.

| Metric | Value |
|---|---:|
| Micro precision | 0.7255 |
| Micro recall | 0.9737 |
| Micro F1 | 0.8315 |
| Macro precision (all 13) | 0.6833 |
| Macro recall (all 13) | 0.7436 |
| Macro F1 (all 13) | 0.6958 |
| Macro precision (10 supported) | 0.8883 |
| Macro recall (10 supported) | 0.9667 |
| Macro F1 (10 supported) | 0.9046 |
| Exact-set match | 0.6286 |
| Coverage | 1.0 |
| Abstention rate | 0.0 |
| Mean predicted labels per fragment | 1.4571 |

### The two macro views

Source: `reports/metrics/macro_label_views.json`.

| System | `macro_all_13` F1 | `macro_gold_supported` F1 |
|---|---:|---:|
| BM25 Top-1 | 0.5900 | 0.7670 |
| BM25 Top-5 + constrained model | 0.6958 | 0.9046 |

The 0.21 gap for the constrained system is entirely attributable to the three
zero-support competencies entering the first average as zeros. Both views are
reported because each answers a different question: `macro_all_13` asks how well
the system uses the full framework, `macro_gold_supported` asks how well it
handles the competencies the reference actually contains. Reporting only the
second would conceal a genuine defect; reporting only the first would understate
performance on labels that were in play.

---

## 4. Comparison

Source: `reports/tables/system_delta_summary.csv`.

| Metric | BM25 Top-1 | BM25 Top-5 + constrained model | Difference |
|---|---:|---:|---:|
| Micro precision | 0.7429 | 0.7255 | −0.0174 |
| Micro recall | 0.6842 | 0.9737 | +0.2895 |
| Micro F1 | 0.7123 | 0.8315 | +0.1191 |

### Discussion

The constrained system increased micro recall from 0.6842 to 0.9737 and micro F1
from 0.7123 to 0.8315 relative to BM25 Top-1, while micro precision decreased
from 0.7429 to 0.7255.

The recall gain is large, the precision cost small, and F1 improves. But the
system is **not uniformly better**: a user who values precision above recall
would prefer the baseline on this corpus. Which is preferable depends on the
task. For a teacher reviewing suggestions, a missed competency is invisible and
therefore uncorrectable, whereas a spurious one is visible and takes a moment to
reject. That asymmetry favours recall — but it is an argument about use, not a
measurement, and it is offered as such.

Micro recall matches Recall@5 to four decimal places. Section 5 explains why this
is not a coincidence.

---

## 5. Retrieval errors and model errors

Source: `reports/metrics/error_summary.json`, `reports/tables/error_analysis.csv`.

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
| `correct_abstention` | 0 |
| `incorrect_abstention` | 0 |

**These categories overlap and are not a partition of the 35 fragments.** One
mistake commonly triggers three of them. The non-overlapping view:

| Primary category | Fragments |
|---|---:|
| `correct_prediction` | 21 |
| `llm_wrong_selection` | 12 |
| `ambiguous_gold` | 1 |
| `retrieval_failure` | 1 |
| **Total** | **35** |

### Attribution

| Stage | Missed labels | False positives |
|---|---:|---:|
| BM25 Top-5 retrieval | 1 | — |
| Constrained selection | **0** | 14 |

Within this condition the separation is unusually clean. Retrieval bounds the
recall attainable here; the model bounds
precision.

`llm_missed_gold_label = 0` means the model selected every one of the 37
reference labels that retrieval offered it. Its micro recall therefore equals
Recall@5 exactly, and the match in section 4 is structural rather than
coincidental.

### The single retrieval failure

Fragment `quiz_question:1:4#f001`:

| Field | Value |
|---|---|
| Reference | `GI_C1_3` (IHM et UX) |
| BM25 Top-5 | `GI_C1_2`, `GI_C3_2`, `GI_C3`, `GI_C1_1`, `GI_C1_4` |
| Reference label retrievable | No |
| Predicted | `GI_C1_1` |

The correct competency was never available. No prompt change or stronger model
could recover it; the remedy lies in retrieval — a larger K, a different scoring
function, or vocabulary expansion over the HCI and UX terms that distinguish
`GI_C1_3`.

---

## 6. Granularity

The 14 false positives by source:

| Source | Count | Share |
|---|---:|---:|
| Top-level competencies (`GI_C1`, `GI_C2`, `GI_C3`) | 10 | 71 % |
| Topical confusion (`GI_C2_2` ×2, `GI_C1_1`, `GI_C2_3`) | 4 | 29 % |

All ten follow one pattern: the model predicted the parent together with the
**correct** child, where the reference contains only the child.

| Fragment | Course | Reference | Predicted |
|---|---|---|---|
| `page:1#f002` | MVP-SW | `GI_C1_1` | `GI_C1`, `GI_C1_1` |
| `page:2#f001` | MVP-SW | `GI_C1_3` | `GI_C1`, `GI_C1_3` |
| `page:4#f003` | MVP-SW | `GI_C2_3` | `GI_C2`, `GI_C2_3` |
| `quiz_question:1:1#f001` | MVP-SW | `GI_C1_1` | `GI_C1`, `GI_C1_1` |
| `page:5#f001` | MVP-DATA | `GI_C3_1` | `GI_C3`, `GI_C3_1` |
| `page:8#f001` | MVP-DATA | `GI_C3_3` | `GI_C3`, `GI_C3_3` |
| `page:8#f004` | MVP-DATA | `GI_C3_3` | `GI_C3`, `GI_C3_3` |
| `quiz_question:2:8#f001` | MVP-DATA | `GI_C3_1` | `GI_C3`, `GI_C3_1` |
| `quiz_question:2:9#f001` | MVP-DATA | `GI_C3_2` | `GI_C3`, `GI_C3_2` |
| `quiz_question:2:12#f001` | MVP-DATA | `GI_C3_3` | `GI_C3`, `GI_C3_3` |

Distribution: `GI_C3` six, `GI_C1` three, `GI_C2` one; MVP-DATA six, MVP-SW four.
The pattern is not confined to one topic or course.

### Discussion

Each instance is a pure precision loss with no recall benefit. The model
identifies the subject matter correctly and is insufficiently decisive about the
level at which to report it.

The cause is partly a specification gap. The annotator labelled only at child
level; the prompt never stated that convention. Predicting `GI_C3` for a fragment
about machine learning is defensible in isolation — the reference simply does not
count it.

This bounds how the precision figure should be read. **Micro precision here is
substantially a measure of agreement with a granularity convention**, not of
topical correctness. An identical output scored against a reference that credited
a parent as partially correct would yield a markedly different precision. The
appropriate remedy is to state the convention in the instructions and re-measure,
rather than to prune the output afterwards.

---

## 7. Evidence quality

Source: `reports/metrics/evidence_review_summary.json`.

| Property | Value |
|---|---:|
| Evidence quotations | 83 |
| Mechanically valid exact substrings | 83 (100 %) |
| Offset validity | 83 (100 %) |
| Rated `2` — clearly supports | 65 (78.3 %) |
| Rated `1` — partially relevant | 16 (19.3 %) |
| Rated `0` — does not justify | 2 (2.4 %) |
| Fragments flagged `exact_but_weak_evidence` | 12 |

### Discussion

Complete mechanical validity coexists with 21.7 % of quotations judged partial or
unsupported. The exact-substring constraint eliminated fabrication entirely — not
one of 83 quotations was invented — while providing no assurance that the quoted
material demonstrates the competency.

The constraint's practical contribution is therefore **inspectability** rather
than correctness. A weak justification remains weak, but it is visible in the
quotation itself and a reviewer can reject it in seconds.

### Evidence quality and hierarchy level

| Quotations supporting | Rated 2 | Rated 1 | Rated 0 |
|---|---:|---:|---:|
| Top-level competencies | 1 | 11 | 0 |
| Child competencies | 64 | 5 | 2 |

One of twelve quotations for a top-level competency was judged clearly adequate,
against 64 of 71 at child level. The reviewer's comments name the reason
consistently — a quotation teaches the child and supports the parent only through
the hierarchy.

This matters methodologically. The evidence review was conducted quotation by
quotation, without reference to the error analysis, and it independently
identified the same defect the metrics did. The parent predictions are not merely
misaligned with one annotator's convention; a reader assessing each quotation on
its own terms judged the justification weak.

### The two unsupported quotations

Both belong to `quiz_question:1:4#f001`, the retrieval-failure fragment:

| Quotation | Rating | Reviewer comment |
|---|---:|---|
| `User_Centred_Design` | 0 | Title fragment does not justify `GI_C1_1` |
| `Testing a prototype with representative users` | 0 | Prototype testing is HCI/UX (`GI_C1_3`), not `GI_C1_1` |

The reviewer independently named `GI_C1_3` — the label retrieval had failed to
supply. Three signals converge on one fragment: the retrieval metric, the error
classifier and a human reading the evidence.

The case also shows a secondary effect of the constraint. Unable to find genuine
support, the model quoted a title token. The quotation is exact, passes
mechanical validation, and is plainly inadequate to a reader — the failure was
surfaced rather than hidden.

---

## 8. Resource-level behaviour

Source: `reports/metrics/resource_level_metrics.json`. The resource-level
reference is **derived** from the fragment reference and is not a second
annotation.

| Metric | Fragment level | Resource level |
|---|---:|---:|
| Micro precision | 0.7255 | 0.6765 |
| Micro recall | 0.9737 | 0.9583 |
| Micro F1 | 0.8315 | 0.7931 |
| Macro F1 (all 13) | 0.6958 | 0.7026 |
| Macro F1 (supported) | 0.9046 | 0.9133 |
| Exact-set match | 0.6286 | 0.4500 |

| Additional resource-level measure | Value |
|---|---:|
| Subset accuracy | 0.4500 |
| True / false positives, false negatives | 23 / 11 / 1 |
| Mean predicted labels | 1.70 |
| Mean reference labels | 1.20 |
| Mean absolute label-count error | 0.50 |
| Over-predicted resources | 11 |
| Under-predicted resources | 1 |
| Resources with parent–child redundancy | 9 |

### Discussion

Precision falls by 0.049 from fragment to resource level, for a mechanical
reason: aggregation takes the union of a resource's fragment labels, so a
spurious parent on any one fragment contaminates the resource. Eleven of twenty
resources are over-predicted, nine of them through parent–child redundancy.

Exact-set match falls further, from 0.6286 to 0.4500. Fewer than half of
resources receive exactly the right label set — in almost every case through one
additional parent label.

This is the figure closest to a teacher's experience, since a teacher receives a
resource with a set of proposed competencies. It indicates that slightly more than
half the resources would require an edit, and that the edit is usually the removal
of one redundant label.

---

## 9. Hierarchy warnings and the post-hoc ablation

Source: `reports/metrics/graph_check_summary.json`,
`reports/tables/graph_ablation_comparison.csv`.

### Warnings

| Warning | Count |
|---|---:|
| Fragments checked | 35 |
| `parent_child_redundancy` | 10 fragments |
| `granularity_conflict` | 7 fragments |
| `invalid_hierarchy_reference` | 0 |
| Warning rate | 0.2857 |

Most frequent redundant parent: `GI_C3` (6 of 10). Per course: MVP-DATA 6,
MVP-SW 4. At resource level, 9 of 20 resources carry a redundancy.

No invalid hierarchy reference was found: every predicted relation exists in the
framework.

### The ablation

A separate simulated prediction set removes the parent where a parent and its
direct child are both predicted. The original predictions were not modified
(`original_predictions_modified: false`) and the output is written under
`data/experiments/`.

| Metric | Original | Child-preference | Difference |
|---|---:|---:|---:|
| Micro precision | 0.7255 | 0.9024 | +0.1769 |
| Micro recall | 0.9737 | 0.9737 | 0.0000 |
| Micro F1 | 0.8315 | 0.9367 | +0.1052 |
| Exact-set match | 0.6286 | 0.9143 | +0.2857 |
| Mean predicted labels | 1.4571 | 1.1714 | −0.2857 |
| Parent–child redundancies | 10 | 0 | −10 |

Resource level:

| Metric | Original | Child-preference | Difference |
|---|---:|---:|---:|
| Micro precision | 0.6765 | 0.9200 | +0.2435 |
| Micro recall | 0.9583 | 0.9583 | 0.0000 |
| Micro F1 | 0.7931 | 0.9388 | +0.1457 |
| Exact-set match | 0.4500 | 0.9000 | +0.4500 |
| Mean absolute label-count error | 0.50 | 0.05 | −0.45 |

### Discussion

Recall is unchanged at both levels. Removing the redundant parent costs nothing
in recall because no top-level competency is ever a correct label in this
reference — a direct consequence of the child-level annotation convention.

**What this establishes.** The residual precision loss is systematic,
mechanically detectable from the framework hierarchy alone, and attributable
almost entirely to one failure mode. A single deterministic rule using no
information beyond the framework closes most of the gap.

**What it does not establish.** That a system achieving F1 0.9367 exists. The
rule was formulated after inspecting the errors and depends on a property of this
reference. On a corpus where a top-level competency is sometimes correct, the
same rule would remove true positives. It is a diagnosis, not a validated
technique, and it is labelled a post-hoc ablation wherever it appears.

---

## 10. What these results do not establish

1. **Not a performance estimate.** With 38 reference labels, one label is worth
   2.63 points of recall. The figures are exact arithmetic on a small
   denominator, not estimates with quantified uncertainty. No significance test
   was performed.

2. **Not validated against multiple annotators.** One annotator produced all 38
   labels; no inter-annotator agreement was measured. Every score is an agreement
   rate with one person's judgement.

3. **Not independent evidence assessment.** The evidence review was performed by
   the annotator. Its convergence with the metrics is internal consistency, not
   independent confirmation.

4. **Nothing about abstention.** No fragment has "no applicable competency" as its
   correct answer. The 0.0 abstention rate is a property of the corpus, not of the
   system.

5. **Nothing about the effect of candidate restriction.** The unconstrained
   comparison over all thirteen competencies has not been run. Statements about
   why the constrained system behaves as it does are reasoning from the design,
   not measurement.

6. **Nothing about teacher usefulness.** No teacher or supervisor has reviewed the
   output. There are 34 reviewable mappings and none has been assessed; no
   acceptance rate is reported anywhere.

7. **Nothing about messy material.** The corpus was constructed for this study —
   clean, short, thematically coherent text in two courses.

8. **Nothing about confidence calibration.** Confidence scores were never
   validated against correctness.

---

## 11. Summary

| Finding | Evidence |
|---|---|
| In the Top-5 condition, the only missed label was absent from the candidate set | `llm_missed_gold_label = 0`; micro recall = Recall@5 = 0.9737 |
| The single missed label is a retrieval failure | `GI_C1_3` absent from the Top-5 of `quiz_question:1:4#f001` |
| Constrained selection trades precision for recall | −0.0174 precision, +0.2895 recall, +0.1191 F1 |
| Precision errors are dominated by parent-child redundancy | 10 of 14 false positives are zero-support parents; 4 are topical |
| The cause is partly underspecification | The child-level convention was never stated in the prompt |
| Exact evidence prevents fabrication, not weak reasoning | 100 % exact; 78.3 % judged clearly supporting |
| Two independent reviews converge | Evidence review located the same retrieval failure and named `GI_C1_3` |
| Aggregation amplifies precision errors | Resource precision 0.6765 against fragment 0.7255 |
| The residual error is systematic | Post-hoc ablation: precision +0.1769, recall unchanged |
| Teacher usefulness is unmeasured | 0 of 34 mappings reviewed |
