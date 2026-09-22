# Final error analysis

**Moodle learning resource-to-competency alignment — reduced MVP**
**Researcher:** Wail Ouaret · UTC / Heudiasyc / CNRS
**Date:** 2026-09-22
**Sources:** `reports/metrics/error_summary.json`, `reports/tables/error_analysis.csv`,
`reports/tables/error_examples.csv`, `data/reviews/evidence_review.csv`

Every example below is a real row from the frozen experiment. No example is
invented, edited or composited.

---

## 1. Summary

The system makes **one kind of mistake, repeatedly**, and it is not the kind
usually feared of a language model.

- It did not hallucinate a competency. Every predicted ID is a real framework ID.
- It did not fabricate evidence. All 83 quotes are exact substrings.
- It did not miss anything it was shown. `llm_missed_gold_label = 0`.
- It **over-committed on granularity**: given a fragment that teaches a child
  competency, it often predicted the child *and* its parent.

Ten of the 14 false positives — **71%** — are that single pattern.

---

## 2. Category counts

| Category | Count | Note |
|---|---:|---|
| `correct_prediction` | 22 | |
| `llm_wrong_selection` | 13 | |
| `overprediction` | 13 | dominant failure |
| `parent_child_redundancy` | 10 | main sub-cause of overprediction |
| `exact_but_weak_evidence` | 12 | exact quote, weak justification |
| `retrieval_failure` | 1 | the only missed reference label |
| `underprediction` | 1 | same fragment |
| `llm_missed_gold_label` | **0** | nothing retrievable was missed |
| `ambiguous_gold` | 1 | flagged by the annotator |
| `incorrect_abstention` | 0 | untestable — no `NONE` fragments |
| `correct_abstention` | 0 | untestable — no `NONE` fragments |

**These flags overlap and are not a partition of the 35 fragments.** A single
fragment is routinely flagged `llm_wrong_selection` *and* `overprediction` *and*
`parent_child_redundancy` for the same underlying mistake, so the column does
not sum to 35 and must never be read as if it did.

The non-overlapping view assigns each fragment one `primary_error_category`:

| Primary category | Fragments |
|---|---:|
| `correct_prediction` | 21 |
| `llm_wrong_selection` | 12 |
| `ambiguous_gold` | 1 |
| `retrieval_failure` | 1 |
| **Total** | **35** |

---

## 3. Retrieval failure versus model failure

The attribution is unusually clean, because the two stages fail in different
directions.

| Stage | Recall cost | Precision cost |
|---|---:|---:|
| BM25 Top-5 retrieval | 1 missed label | — |
| Constrained model | **0** missed labels | 14 false positives |

**Retrieval sets the recall ceiling; the model sets the precision floor.**

Recall@5 = 0.9737 means BM25 surfaced 37 of 38 reference labels. The model,
restricted to those candidates, selected all 37. Its micro recall is therefore
also 0.9737 — not a coincidence, but the ceiling being reached exactly.

### The single retrieval failure, in full

**Fragment `quiz_question:1:4#f001`** (MVP-SW, quiz question)

| Field | Value |
|---|---|
| Reference | `GI_C1_3` (IHM et UX) |
| BM25 Top-5 | `GI_C1_2`, `GI_C3_2`, `GI_C3`, `GI_C1_1`, `GI_C1_4` |
| Was `GI_C1_3` retrievable? | **No — absent from the candidate set** |
| Predicted | `GI_C1_1` |
| Primary category | `retrieval_failure` |
| Also flagged | `underprediction`, `llm_wrong_selection` |

The correct answer was never on the menu. The model chose the nearest available
option and was wrong. This case cannot be fixed by a better prompt or a stronger
model; it requires better retrieval — a larger K, a different scoring function,
or query expansion over the UX/HCI vocabulary.

It is also the only fragment where the model's evidence was judged worthless by
a human (Section 5), which makes it the one case where three independent signals
agree.

---

## 4. Overprediction and parent-child redundancy

### The pattern

All ten redundancy cases are the same shape: **parent + correct child predicted,
child alone in the reference.**

| Fragment | Course | Reference | Predicted | Redundant parent |
|---|---|---|---|---|
| `page:1#f002` | MVP-SW | `GI_C1_1` | `GI_C1`, `GI_C1_1` | `GI_C1` |
| `page:2#f001` | MVP-SW | `GI_C1_3` | `GI_C1`, `GI_C1_3` | `GI_C1` |
| `page:4#f003` | MVP-SW | `GI_C2_3` | `GI_C2`, `GI_C2_3` | `GI_C2` |
| `quiz_question:1:1#f001` | MVP-SW | `GI_C1_1` | `GI_C1`, `GI_C1_1` | `GI_C1` |
| `page:5#f001` | MVP-DATA | `GI_C3_1` | `GI_C3`, `GI_C3_1` | `GI_C3` |
| `page:8#f001` | MVP-DATA | `GI_C3_3` | `GI_C3`, `GI_C3_3` | `GI_C3` |
| `page:8#f004` | MVP-DATA | `GI_C3_3` | `GI_C3`, `GI_C3_3` | `GI_C3` |
| `quiz_question:2:8#f001` | MVP-DATA | `GI_C3_1` | `GI_C3`, `GI_C3_1` | `GI_C3` |
| `quiz_question:2:9#f001` | MVP-DATA | `GI_C3_2` | `GI_C3`, `GI_C3_2` | `GI_C3` |
| `quiz_question:2:12#f001` | MVP-DATA | `GI_C3_3` | `GI_C3`, `GI_C3_3` | `GI_C3` |

In **every** case the child prediction is correct. The parent adds a false
positive and no true positive. This is a pure precision loss.

Distribution: `GI_C3` 6 · `GI_C1` 3 · `GI_C2` 1. Per course: MVP-DATA 6,
MVP-SW 4. It is not confined to one topic or one course.

### Where the false positives actually come from

| Competency | Reference support | Predicted | False positives |
|---|---:|---:|---:|
| `GI_C3` | 0 | 6 | **6** |
| `GI_C1` | 0 | 3 | **3** |
| `GI_C2` | 0 | 1 | **1** |
| `GI_C2_2` | 1 | 3 | 2 |
| `GI_C1_1` | 3 | 4 | 1 |
| `GI_C2_3` | 4 | 5 | 1 |
| All others | — | — | 0 |
| **Total** | | | **14** |

**10 of 14 false positives are the three zero-support parents.** Precision would
rise from 0.7255 to 0.9024 if those ten disappeared and nothing else changed —
which is exactly what the post-hoc ablation measured.

### Why it happens

The annotator labelled only at child level: all three parents have zero
reference support across 38 labels. The model was never told that. Nothing in
the prompt states the convention, and from the model's point of view predicting
`GI_C3` for a fragment about machine learning is defensible — it is, after all,
true. The reference simply does not count it.

So this is **a specification failure as much as a model failure**. Before
concluding the model is over-eager, the honest correction is that the task was
underspecified. The most promising fix is to state the convention in the prompt
and re-measure, rather than prune afterwards.

### The remaining four false positives

Not hierarchy-related, and genuinely wrong topically:

- `GI_C2_2` predicted 3 times against 1 reference label (2 FP) — the model reads
  general "distributed/networked" language as communicating architectures.
- `GI_C1_1` 1 FP — the retrieval-failure fragment above.
- `GI_C2_3` 1 FP — a topic list naming security terms without teaching them.

Four errors out of 51 predictions is a small residue. If parent redundancy were
solved, this residue would be the whole remaining precision problem.

---

## 5. Evidence quality as an error signal

All 83 quotes are mechanically exact. A human rated all 83 for whether they
*justify* the competency:

| Rating | Count | Share |
|---|---:|---:|
| `2` clearly supports | 65 | 78.31% |
| `1` partial / ambiguous | 16 | 19.28% |
| `0` does not justify | 2 | 2.41% |

`exact_but_weak_evidence` is flagged on **12 fragments**: the quote is real but
the justification is thin.

### Evidence quality tracks the hierarchy problem

| Quotes for | rating 2 | rating 1 | rating 0 |
|---|---:|---:|---:|
| Parent competencies | 1 | 11 | 0 |
| Child competencies | 64 | 5 | 2 |

Only **1 of 12** parent quotes was judged clearly supporting, against **64 of
71** child quotes. The reviewer's comments name the reason directly and
repeatedly:

> *"Quote teaches C3_1; parent GI_C3 only by hierarchy."* — `page:5#f001`
> *"ML-system wrap-up; parent GI_C3 is broader than this quote."* — `page:8#f004`
> *"Security-architecture wrap-up; parent GI_C2 is broader than this quote."* — `page:4#f003`
> *"Child-level user-requirements item; parent GI_C1 only by hierarchy."* — `quiz_question:1:1#f001`

This matters methodologically. The evidence review was done quote by quote,
without consulting the error analysis, yet it independently identified the same
defect the metrics did. The parent predictions are not merely redundant against
one annotator's convention — a human reading only the quote and the competency
judged their justification weak.

### Both `0` ratings land on the retrieval failure

Both quotes rated `0` belong to `quiz_question:1:4#f001` / `GI_C1_1`:

| Quote | Rating | Reviewer comment |
|---|---:|---|
| "User_Centred_Design" | `0` | *Title fragment User_Centred_Design does not justify GI_C1_1.* |
| "Testing a prototype with representative users" | `0` | *Prototype testing is HCI/UX (GI_C1_3), not GI_C1_1 software development.* |

The reviewer independently named `GI_C1_3` — the exact reference label BM25
failed to retrieve. Three signals converge on one fragment: the retrieval metric,
the error classifier, and a human reading the evidence.

It also shows the exact-evidence constraint doing real work in a second way. The
model, unable to find genuine support, quoted a *title token*
("User_Centred_Design"). The quote is exact and passes mechanical validation —
and is visibly inadequate to a human. Requiring exact quotes does not prevent
weak justification, but it makes weak justification **visible**, which is the
property a teacher-facing tool needs.

---

## 6. The ambiguous reference fragment

**`page:3#f003`** — flagged `ambiguous` by the annotator at annotation time,
before any prediction was seen.

| Field | Value |
|---|---|
| Reference | `GI_C1_4`, `GI_C2_3` |
| Predicted | `GI_C1_4`, `GI_C2_3` |
| Result | **exact set match** |

The one fragment the human found genuinely hard, the model got exactly right.
This is reported because it cuts against a tidy narrative: ambiguity for a human
annotator did not translate into difficulty for the model here. With n = 1 it
supports no generalisation whatsoever.

---

## 7. Abstention — why the zeros mean nothing

`correct_abstention = 0` and `incorrect_abstention = 0`, with an abstention rate
of 0.0.

This is **not** a finding about the system. The reference set contains **zero
`NONE` fragments**: every one of the 35 fragments has at least one correct
competency. There was never an occasion on which abstaining was the right
answer, so the system's ability to decline was never tested.

The mechanism exists and is exercised in tests — a clean abstention validates, an
abstention with selections is rejected — but on this corpus it is untested in
the only sense that matters. A future corpus must include deliberately off-topic
material (administrative pages, course logistics, unrelated subject matter)
before any claim about abstention is made.

---

## 8. What the post-hoc ablation shows, and what it does not

Dropping the redundant parent — **in a separate simulated output only**, with the
original predictions untouched:

| Metric | Original | Child-preference | Δ |
|---|---:|---:|---:|
| Micro precision | 0.7255 | 0.9024 | +0.1769 |
| Micro recall | 0.9737 | 0.9737 | 0.0000 |
| Micro F1 | 0.8315 | 0.9367 | +0.1052 |
| Exact-set match | 0.6286 | 0.9143 | +0.2857 |
| Parent-child redundancies | 10 | 0 | −10 |

**Shows:** the errors are systematic, mechanically detectable from the framework
hierarchy alone, and account for essentially the whole precision gap. Recall is
untouched, confirming no parent was ever a correct label here.

**Does not show:** that a 0.94-F1 system exists. The rule was designed after
seeing these errors and exploits a property of this reference (child-level-only
annotation). On a corpus where a parent is sometimes genuinely correct, the same
rule would remove true positives. This is a diagnosis, not a validated
technique, and it is labelled `POST-HOC MINIMAL GRAPH ABLATION` everywhere it
appears.

---

## 9. Conclusions

1. **In the constrained Top-5 condition, the only missed reference label was
   absent from the candidate set.** The model selected every reference label
   available among its candidates, in all 37 cases. Within this condition, recall
   improvements must come from the retrieval stage; behaviour under an
   unrestricted candidate space has not been measured.
2. **Precision errors are dominated by parent-child granularity redundancy.**
   71% of false positives are zero-support parent competencies predicted
   alongside their correct child. The remaining 29% (4 of 14) are topical
   confusions unrelated to hierarchy and are not explained by this cause.
3. **The cause is partly a specification gap.** The child-level-only annotation
   convention was never stated in the prompt. Fixing the instruction is a more
   honest remedy than post-hoc pruning.
4. **Exact-evidence validation works — for a narrower purpose than it appears.**
   It eliminated fabrication entirely, but 21.7% of exact quotes were still
   judged partial or unsupported. Its real value is making weak reasoning
   *visible* to a reviewer, not guaranteeing correctness.
5. **Independent signals converge.** The evidence review, conducted separately,
   reproduced both the retrieval failure and the hierarchy problem — including
   naming the correct missing competency.
6. **Abstention is untested** and must not be reported as a strength.
7. **Every conclusion rests on 38 reference labels from one annotator.** They
   describe this corpus. They are not performance estimates for Moodle courses in
   general.
