# Resource-level evaluation

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Researcher:** Wail Ouaret  
**Date:** 2026-09-18

Predictions are the already-generated constrained Gemini resource aggregations. No new model calls were made.

## 1. Purpose

This phase measures how accurately fragment-level competency predictions aggregate into competency mappings for complete Moodle research resources (Pages and independent Quiz questions).

## 2. Derived resource reference

Resource-level labels are **DERIVED** from the human-reviewed fragment reference in `data/gold/manual_fragment_annotations.csv`. This is not a second independent annotation exercise.

- Resources: 20
- Pages: 8
- Quiz-question resources: 12
- Fragments accounted for: 35 / 35
- Fragments used exactly once: True
- Native Moodle activity mappings used: no (`used_manual_moodle_links=false`)

Derivation strings:

- Page: `union_of_human_reviewed_fragment_labels`
- Quiz question: `human_reviewed_question_fragment_label`

File: `data/processed/resource_reference.jsonl`

## 3. Why Pages use union of fragment labels

A Page is one Moodle learning resource that may be split into several `page_chunk` fragments for retrieval and LLM scoring. The resource-level mapping for that Page is the union of the human-reviewed fragment labels belonging to it. Duplicate labels across fragments are kept once.

Example: fragment labels `GI_C1_1;GI_C1_2` and `GI_C1_1` become resource gold `GI_C1_1;GI_C1_2`.

## 4. Why Quiz questions remain independent

Each Quiz question is already treated as an independent research resource. Question gold is that question's human-reviewed fragment labels. Quiz activity-level Moodle competency associations are not propagated to individual questions. `data/gold/manual_moodle_links.csv` is not used here.

## 5. Resource-level metrics

Source: `reports/metrics/resource_level_metrics.json`  
System: existing `data/processed/resource_predictions.jsonl` (constrained Gemini, no new calls).

| Metric | Value |
|---|---:|
| Resources | 20 |
| Micro precision | 0.6764705882 |
| Micro recall | 0.9583333333 |
| Micro F1 | 0.7931034483 |
| Macro precision (all 13) | 0.7051282051 |
| Macro recall (all 13) | 0.7307692308 |
| Macro F1 (all 13) | 0.7025641026 |
| Macro precision (gold-supported) | 0.9166666667 |
| Macro recall (gold-supported) | 0.9500000000 |
| Macro F1 (gold-supported) | 0.9133333333 |
| Exact-set / subset accuracy | 0.4500000000 |
| Exact-set matches | 9 / 20 |
| Average reference labels | 1.2000000000 |
| Average predicted labels | 1.7000000000 |
| Average |predicted − reference| label count | 0.5000000000 |
| Resource coverage | 1.0000000000 |
| Resource abstention | 0.0000000000 |

`macro_all_13` is the unweighted mean over all 13 UTC GI competencies. `macro_gold_supported_labels` is a second view over competencies with positive derived-reference support. Neither replaces the other.

Exact-set match is the multi-label subset-accuracy rate: the fraction of resources whose predicted set equals the derived reference set.

Ollama is not included in this file.

## 6. Per-resource results

| resource_id | type | reference | predicted | P | R | F1 | exact |
|---|---|---|---|---:|---:|---:|---|
| `page:1` | page | `GI_C1_1;GI_C1_2` | `GI_C1;GI_C1_1;GI_C1_2` | 0.6667 | 1.0000 | 0.8000 | no |
| `page:2` | page | `GI_C1_3` | `GI_C1;GI_C1_3` | 0.5000 | 1.0000 | 0.6667 | no |
| `page:3` | page | `GI_C1_4;GI_C2_3` | `GI_C1_4;GI_C2_2;GI_C2_3` | 0.6667 | 1.0000 | 0.8000 | no |
| `page:4` | page | `GI_C2_1;GI_C2_2;GI_C2_3` | `GI_C2;GI_C2_1;GI_C2_2;GI_C2_3` | 0.7500 | 1.0000 | 0.8571 | no |
| `quiz_question:1:1` | quiz_question | `GI_C1_1` | `GI_C1;GI_C1_1` | 0.5000 | 1.0000 | 0.6667 | no |
| `quiz_question:1:3` | quiz_question | `GI_C1_2` | `GI_C1_2` | 1.0000 | 1.0000 | 1.0000 | yes |
| `quiz_question:1:4` | quiz_question | `GI_C1_3` | `GI_C1_1` | 0.0000 | 0.0000 | 0.0000 | no |
| `quiz_question:1:5` | quiz_question | `GI_C1_4` | `GI_C1_4` | 1.0000 | 1.0000 | 1.0000 | yes |
| `quiz_question:1:6` | quiz_question | `GI_C2_3` | `GI_C2_3` | 1.0000 | 1.0000 | 1.0000 | yes |
| `quiz_question:1:7` | quiz_question | `GI_C1_2` | `GI_C1_2` | 1.0000 | 1.0000 | 1.0000 | yes |
| `page:5` | page | `GI_C3_1` | `GI_C3;GI_C3_1` | 0.5000 | 1.0000 | 0.6667 | no |
| `page:6` | page | `GI_C3_2` | `GI_C3_2` | 1.0000 | 1.0000 | 1.0000 | yes |
| `page:7` | page | `GI_C3_2` | `GI_C3_2` | 1.0000 | 1.0000 | 1.0000 | yes |
| `page:8` | page | `GI_C3_3` | `GI_C3;GI_C3_3` | 0.5000 | 1.0000 | 0.6667 | no |
| `quiz_question:2:8` | quiz_question | `GI_C3_1` | `GI_C3;GI_C3_1` | 0.5000 | 1.0000 | 0.6667 | no |
| `quiz_question:2:9` | quiz_question | `GI_C3_2` | `GI_C3;GI_C3_2` | 0.5000 | 1.0000 | 0.6667 | no |
| `quiz_question:2:10` | quiz_question | `GI_C3_2` | `GI_C3_2` | 1.0000 | 1.0000 | 1.0000 | yes |
| `quiz_question:2:11` | quiz_question | `GI_C3_2` | `GI_C3_2` | 1.0000 | 1.0000 | 1.0000 | yes |
| `quiz_question:2:12` | quiz_question | `GI_C3_3` | `GI_C3;GI_C3_3` | 0.5000 | 1.0000 | 0.6667 | no |
| `quiz_question:2:13` | quiz_question | `GI_C3_3` | `GI_C3_3` | 1.0000 | 1.0000 | 1.0000 | yes |

Overpredicted resources (any false positive): 11
Resources with a false negative: 1
Resources with parent-child redundancy: 9

## 7. Per-competency results

| competency_id | support | predicted | TP | FP | FN | P | R | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `GI_C1` | 0 | 3 | 0 | 3 | 0 | 0.0000 | 0.0000 | 0.0000 |
| `GI_C1_1` | 2 | 3 | 2 | 1 | 0 | 0.6667 | 1.0000 | 0.8000 |
| `GI_C1_2` | 3 | 3 | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `GI_C1_3` | 2 | 1 | 1 | 0 | 1 | 1.0000 | 0.5000 | 0.6667 |
| `GI_C1_4` | 2 | 2 | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `GI_C2` | 0 | 1 | 0 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 |
| `GI_C2_1` | 1 | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `GI_C2_2` | 1 | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 | 0.6667 |
| `GI_C2_3` | 3 | 3 | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `GI_C3` | 0 | 5 | 0 | 5 | 0 | 0.0000 | 0.0000 | 0.0000 |
| `GI_C3_1` | 2 | 2 | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `GI_C3_2` | 5 | 5 | 5 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `GI_C3_3` | 3 | 3 | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

## 8. Main errors

Measured error pattern at resource level is overprediction, often a GI parent predicted together with a child that is already in the derived reference. Exact-set accuracy is therefore lower than fragment-level exact-set match even when the child labels are correct.

- Overpredicted Page example: `page:1` reference `GI_C1_1;GI_C1_2`; extra `GI_C1`.
- Parent-child example: `page:1` predicted `GI_C1;GI_C1_1;GI_C1_2`.
- False-negative example: `quiz_question:1:4` missing `GI_C1_3`.
- Retrieval-failure resource: `quiz_question:1:4` reference `GI_C1_3`; predicted `GI_C1_1`.
- Exact correct example: `quiz_question:1:3` (`GI_C1_2`).
- Independent Quiz-question example: `quiz_question:1:1`.

The only resource-level false negative on the current frozen data is `quiz_question:1:4` (`GI_C1_3` missing; `GI_C1_1` predicted). That is the same retrieval failure already measured at fragment level.

## 9. Relationship to fragment-level results

| Level | Micro P | Micro R | Micro F1 |
|---|---:|---:|---:|
| Fragment-level Gemini | 0.7255 | 0.9737 | 0.8315 |
| Resource-level Gemini | 0.6765 | 0.9583 | 0.7931 |

Fragment-level micro recall and resource-level micro recall are both limited by the same missed reference label `GI_C1_3` on `quiz_question:1:4`. Resource-level micro precision is lower than fragment-level micro precision on this corpus. Page aggregation may accumulate false-positive labels from several fragments (for example a parent predicted on one chunk remains on the Page after union). This is a measured difference, not a causal proof.

## 10. Limitations

- Resource gold is derived from fragment gold; it is not a new human annotation of whole resources.
- Native Moodle activity competency links are not question gold.
- Parent and child IDs remain distinct labels.
- Small corpus: 20 resources, 35 fragments, 13 competencies.
- Constrained Gemini still cannot select a label absent from BM25 Top-5.
- Teacher validation has not started.
- Optional unconstrained Gemini and Ollama resource-level evaluation were not run in this phase.

Next phase: minimal hierarchy / graph analysis. Teacher UI is not started.
