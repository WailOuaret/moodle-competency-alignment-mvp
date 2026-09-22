# Minimal hierarchy / graph analysis

**Project:** Moodle Learning Resource-to-Competency Alignment MVP  
**Researcher:** Wail Ouaret  
**Date:** 2026-09-18

This document reports a **post-hoc hierarchy ablation**. A deterministic hierarchy rule was applied after the frozen Gemini predictions to assess the effect of removing redundant parent labels.

Do not read this as “Gemini used graph reasoning.” The original Gemini run did not use a graph layer.

## 1. Motivation

Fragment-level error analysis found frequent parent-child redundancy. The human-reviewed reference has no positive support for the three UTC GI top-level parents `GI_C1`, `GI_C2`, and `GI_C3`. This experiment tests whether a minimal hierarchy consistency rule can reduce unnecessary parent predictions.

## 2. Graph used

Only the verified UTC GI parent-child hierarchy from `data/processed/competencies.jsonl` was used. No prerequisite, related-to, part-of, or similarity edges were invented.

- Competency IDs: 13
- Root / parent competencies: 3 (GI_C1, GI_C2, GI_C3)
- Child competencies: 10
- Missing parent references: 0
- Cycles: 0

## 3. Warning rules

- `parent_child_redundancy`: a parent and one of its **direct** children are both predicted for the same fragment or resource.
- `granularity_conflict`: the same parent/child pair is supported by identical or overlapping evidence quotes.
- `invalid_hierarchy_reference`: unknown competency, missing parent reference, or malformed hierarchy relation.

Warnings are non-destructive (`action = warning_only`). Original predictions are not changed.

## 4. Original hierarchy inconsistencies

### Fragments

- Fragments checked: 35
- Fragments with parent-child redundancy: 10
- Redundant parent-child pairs: 10
- Fragments with granularity conflict: 7
- Invalid hierarchy references: 0
- Warning rate: 0.2857

Parent pair frequencies:

- GI_C1: 3
- GI_C2: 1
- GI_C3: 6

Most frequent redundant parent: `GI_C3`.

Per-course redundant fragments: {"MVP-SW": 4, "MVP-DATA": 6}

### Resources

- Resources checked: 20
- Resources with parent-child redundancy: 9
- Redundant resource parent-child pairs: 12

## 5. Child-preference simulation

Rule: if a parent and one or more **direct** children are both predicted, remove the parent from the **simulated** set only. Keep all children. A parent predicted alone is kept. Unrelated labels are kept. Confidence is not used to drop labels.

- Labels removed (parent instances): 10
- Affected fragments: 10
- Removed true human-reference labels: 0

Simulated outputs are stored under `data/experiments/`. `data/interim/gemini_validated.jsonl` was not overwritten.

## 6. Fragment-level before/after metrics

| Metric | Original Gemini | Post-hoc child-preference |
|---|---:|---:|
| Micro precision | 0.7254901961 | 0.9024390244 |
| Micro recall | 0.9736842105 | 0.9736842105 |
| Micro F1 | 0.8314606742 | 0.9367088608 |
| Macro all-13 F1 | 0.6958485958 | 0.6958485958 |
| Macro gold-supported F1 | 0.9046031746 | 0.9046031746 |
| Exact-set match | 0.6285714286 | 0.9142857143 |
| Coverage | 1.0000000000 | 1.0000000000 |
| Abstention | 0.0000000000 | 0.0000000000 |
| Average predicted labels | 1.4571428571 | 1.1714285714 |
| Parent-child redundancy fragments | 10 | 0 |

## 7. Resource-level before/after metrics

| Metric | Original resource Gemini | Post-hoc child-preference |
|---|---:|---:|
| Micro precision | 0.6764705882 | 0.9200000000 |
| Micro recall | 0.9583333333 | 0.9583333333 |
| Micro F1 | 0.7931034483 | 0.9387755102 |
| Macro all-13 F1 | 0.7025641026 | 0.7025641026 |
| Macro gold-supported F1 | 0.9133333333 | 0.9133333333 |
| Exact-set accuracy | 0.4500000000 | 0.9000000000 |
| Average predicted labels | 1.7000000000 | 1.2500000000 |
| Average label-count error | 0.5000000000 | 0.0500000000 |
| Parent-child redundant resources | 9 | 0 |

## 8. Example cases

| fragment_id | parent | child | original | simulated | orig exact | sim exact |
|---|---|---|---|---|---|---|
| `page:1#f002` | `GI_C1` | `GI_C1_1` | `GI_C1_1;GI_C1` | `GI_C1_1` | false | true |
| `page:4#f003` | `GI_C2` | `GI_C2_3` | `GI_C2_3;GI_C2` | `GI_C2_3` | false | true |
| `page:5#f001` | `GI_C3` | `GI_C3_1` | `GI_C3_1;GI_C3` | `GI_C3_1` | false | true |
| `page:1#f002` | `GI_C1` | `GI_C1_1` | `GI_C1_1;GI_C1` | `GI_C1_1` | false | true |

No frozen Gemini fragment predicted a parent without a direct child, so there is no parent-alone preservation example in this run. The child-preference rule therefore never had to keep a lone parent on this corpus.

## 9. Effect on precision

Fragment-level micro precision increased by 0.1769.
Resource-level micro precision increased by 0.2435.

## 10. Effect on recall

Fragment-level micro recall did not change.

Recall is expected to stay the same if no human-reference labels are removed. Measured removed true reference labels: 0.

## 11. Effect on F1

Fragment-level micro F1 increased by 0.1052.

## 12. Effect on exact-set accuracy

Fragment-level exact-set match increased by 0.2857.
Resource-level exact-set accuracy increased by 0.4500.

## 13. Limitations

- This is a post-hoc ablation, not part of the historical Gemini run.
- Only direct parent-child edges are used.
- A two-level UTC GI subset cannot test deeper ancestry rules.
- Teacher validation has not started.
- Small corpus: 35 fragments, 20 resources, 13 competencies.

## 14. Conclusion

A deterministic child-preference rule can be applied after frozen Gemini predictions to drop redundant parents. Original Gemini metrics remain the system-of-record for the constrained LLM run. The ablation is stored separately under `data/experiments/`.

Next phase: teacher-facing runtime analysis + validation interface. Teacher UI is not started. Teacher decisions remain 0.
