# Evidence-aware error analysis

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Researcher:** Wail Ouaret  
**Date:** 2026-09-18  
**Scope:** constrained Gemini (`gemini-3.5-flash`, temperature 0, BM25 Top-5) against the human-reviewed reference, after Human Gate 2.

This report does not mix optional Ollama outputs into the core Gemini evaluation.

---

## 1. Purpose

Record where constrained Gemini agrees or disagrees with the human-reviewed fragment reference, and whether the model’s exact evidence quotes were judged pedagogically sufficient.

Prediction-correctness flags and evidence-quality flags are separate. They may overlap. Primary category counts partition fragments for presentation; flag counts may overlap.

Join key for evidence review: `fragment_id` + `competency_id`. Quotes are not used as the join key.

---

## 2. Evaluation data

| Item | Count |
|---|---:|
| Fragments | 35 |
| Human-reviewed reference labels | 38 |
| Multi-label reference fragments | 3 |
| Ambiguous reference fragments | 1 (`page:3#f003`) |
| Reference `NONE` fragments | 0 |
| Valid constrained Gemini responses | 35 |
| Evidence-review rows (quotes) | 83 |
| Mechanically valid quotes | 83 |
| Pedagogical ratings | 83 (Gate 2 COMPLETE) |

83 evidence quotes are not 83 predictions. Gemini predicted 51 competency selections across 35 fragments; some selections have more than one quote.

---

## 3. Prediction-error definitions

| Flag | Meaning |
|---|---|
| `retrieval_failure` | A reference ID is absent from BM25 Top-5 |
| `llm_missed_gold_label` | A reference ID is in Top-5 but not selected |
| `llm_wrong_selection` | Gemini selected an ID that is not in the reference set |
| `overprediction` | Predicted set contains extra IDs |
| `underprediction` | Predicted set misses a reference ID |
| `incorrect_abstention` / `correct_abstention` | Empty prediction vs empty or non-empty reference |
| `parent_child_redundancy` | Parent and a direct child are both predicted |
| `ambiguous_gold` | Researcher marked the reference ambiguous |
| `correct_prediction` | Predicted set equals the reference set |

---

## 4. Evidence-quality definitions

Applied only because all 83 pedagogical ratings are complete. Blank ratings are never treated as 0 or 2.

| Flag | Meaning |
|---|---|
| `evidence_clear` | All human ratings for the predicted competency’s quotes are 2 |
| `evidence_partial` | At least one rating is 1 and none is 0 |
| `evidence_unsupported` | At least one rating is 0 |
| `exact_but_weak_evidence` | Quote is a mechanically exact substring and at least one human rating is &lt; 2 |

A mechanically invalid quote is not classified as `exact_but_weak_evidence`.

If one predicted competency has several quotes, every quote is kept. A single rating 0 makes the pair `evidence_unsupported`; it is not averaged away.

---

## 5. Retrieval failures

Overlapping flag count: **1**.

Fragment `quiz_question:1:4#f001` (resource `quiz_question:1:4`, MVP-SW).

- Reference: `GI_C1_3`
- BM25 Top-5: `GI_C1_2`, `GI_C3_2`, `GI_C3`, `GI_C1_1`, `GI_C1_4`
- Gemini prediction: `GI_C1_1`

`GI_C1_3` is not in Top-5, so constrained Gemini could not select it. This is the only missed reference label in the run.

---

## 6. LLM selection behaviour

- `llm_missed_gold_label` = **0**
- Constrained Gemini micro recall = **0.9737**, equal to BM25 Top-5 Recall@5

Therefore the single missed reference label is a **retrieval failure**, not an LLM-selection failure. Every reference label that reached the Top-5 candidate set was selected.

---

## 7. Overprediction

Overlapping flag count: **13** (same 13 fragments as `llm_wrong_selection` in this run).

This is the principal constrained-LLM weakness on this corpus. Extra IDs are often a parent competency predicted together with a matching child.

Examples: `page:1#f002` (reference `GI_C1_1`, predicted `GI_C1` + `GI_C1_1`); `page:2#f001` (reference `GI_C1_3`, predicted `GI_C1` + `GI_C1_3`); `page:3#f001` (reference `GI_C1_4`, predicted `GI_C1_4` + `GI_C2_2`).

---

## 8. Parent-child redundancy

Overlapping flag count: **10**.

Gemini often predicted both a GI parent (`GI_C1`, `GI_C2`, or `GI_C3`) and a child. Examples: `page:1#f002`, `page:2#f001`, `page:4#f003`.

This flag overlaps with overprediction. It does not replace it.

---

## 9. Underprediction

Overlapping flag count: **1**, the same UX quiz fragment `quiz_question:1:4#f001`. The reference `GI_C1_3` was missed because retrieval never offered it.

---

## 10. Ambiguous reference case

Overlapping flag count: **1**: `page:3#f003`.

Reference and prediction are both `GI_C1_4;GI_C2_3`. The researcher marked the reference ambiguous. The predicted set still matches. Primary category is `ambiguous_gold`; the `correct_prediction` flag remains set.

---

## 11. Evidence quality

Quote-level (83 rows):

| Rating | Count | Rate |
|---|---:|---:|
| 2 clear support | 65 | 0.7831 |
| 1 partial / ambiguous | 16 | 0.1928 |
| 0 unsupported | 2 | 0.0241 |
| Mechanically valid | 83 | 1.0000 |

Fragment-level evidence flags (overlapping with prediction flags; mutually exclusive among themselves in this run):

| Flag | Fragments |
|---|---:|
| `evidence_clear` | 23 |
| `evidence_partial` | 11 |
| `evidence_unsupported` | 1 |
| `exact_but_weak_evidence` | 12 |

12 weak-evidence fragments = 11 partial + 1 unsupported. Mechanical validity is 100%; pedagogical clear support is 78.3%. Exact substring validity is not pedagogical relevance.

Prediction pairs (`fragment_id` + `competency_id`): 38 clear, 12 partial, 1 unsupported.

---

## 12. Unsupported evidence cases

One predicted pair, two quotes, both rated 0, both mechanically valid:

- Fragment: `quiz_question:1:4#f001`
- Predicted competency: `GI_C1_1`
- Reference competency: `GI_C1_3`
- Quotes: `User_Centred_Design` and `Testing a prototype with representative users`

The quotes are exact substrings of the quiz stem, but they were judged not to justify `GI_C1_1` (software development). The fragment is about user-centred interface design.

---

## 13. Partial evidence cases

11 fragments have at least one rating 1 and no rating 0. Examples: `page:2#f001`, `page:3#f001`, `page:4#f001`. Several of these are also overpredictions / parent-child pairs: a quote can support the child while only partially supporting the extra parent, or the reverse.

---

## 14. Correct examples

22 fragments have `correct_prediction`. Examples with clear evidence: `page:1#f001` (`GI_C1_1;GI_C1_2`), `page:2#f002` (`GI_C1_3`), `page:3#f002` (`GI_C1_4`).

---

## 15. Main observations

1. BM25 Top-5 Recall@5 = 0.9737 and constrained Gemini micro recall = 0.9737.
2. `llm_missed_gold_label` = 0.
3. The only missed reference label is a retrieval failure on `quiz_question:1:4#f001`.
4. The principal constrained-LLM weakness is overprediction, including parent-child redundancy (10 fragments).
5. 100% of evidence quotes were mechanically valid exact substrings, while 78.3% were judged to clearly support the predicted competency.
6. Both unsupported quotes belong to the same wrong competency on the retrieval-failure fragment.

These statements are measured on this 35-fragment local Moodle corpus. They are not causal claims about all Moodle courses or all LLMs.

---

## 16. Limitations

- Small controlled corpus (20 resources, 35 fragments, 13 competencies).
- Single-researcher reference; no inter-annotator agreement.
- No reference `NONE` fragments, so abstention is not tested.
- Pedagogical ratings are also single-researcher.
- Constrained Gemini may choose only from BM25 Top-5.
- Optional local Ollama is a separate post-hoc experiment and is not used here.

---

## 17. Next experiment

Resource-level evaluation (derived Page unions; quiz questions remain independent resources). Then minimal hierarchy/graph analysis. Teacher UI and teacher decisions are not started.
