# Evaluation protocol

BM25 and constrained Gemini are evaluated against the **human-reviewed reference annotations** in `data/gold/manual_fragment_annotations.csv`.

All 35 fragments were reviewed and finalized by the researcher (Wail Ouaret, 2026-09-18) against the 13-competency UTC GI catalogue. The finalized annotation set is the reference used for evaluation. This is not described as independent blinded gold produced from scratch, and it is not described as AI-generated gold. The researcher is the final decision-maker for every retained label. There is no second annotator and no measured inter-annotator agreement.

## Reference labels

- Multi-label IDs are semicolon-separated.
- `no_competency=true` means the reference set is empty.
- Activity-level `manual_moodle_links.csv` is **not** fragment-level reference.
- Parent and child IDs are distinct labels. A parent does not automatically credit a child.

Final validation:

```bash
python scripts/12_validate_manual_annotations.py --mode final
```

## BM25 (script 15)

Writes:

- Recall@1 / @3 / @5 — **label-level**: reference labels found in Top-K divided by all reference labels (empty-reference fragments excluded)
- Hit@1 / @3 / @5 — **fragment-level**: at least one reference label in Top-K
- MRR — reciprocal rank of the first reference label
- BM25 Top-1 micro/macro precision, recall, F1 — treating the rank-1 candidate as a singleton prediction

Outputs: `reports/metrics/bm25_metrics.json`, `reports/tables/bm25_per_fragment.csv`, `reports/tables/bm25_per_competency.csv`.

## Constrained LLM (script 16)

Requires the complete reference set and 35/35 valid Gemini responses.

Metrics: micro P/R/F1, exact-set match, coverage, abstention rate, average predicted labels per fragment.

The JSON file keeps the original full-13-label macro fields (`macro_precision`, `macro_recall`, `macro_f1`). A second, clearly named view over competencies with positive human-reference support is written separately to `reports/metrics/macro_label_views.json` as `macro_gold_supported_labels`. That addenda file also repeats `macro_all_13`. Do not treat the gold-supported view as a replacement for the frozen full-13 macro.

A factual BM25 Top-1 vs BM25 Top-5 + Gemini difference table is `reports/tables/system_delta_summary.csv` (no winner text).

Outputs: `reports/metrics/constrained_llm_metrics.json`, `reports/tables/llm_per_fragment.csv`, `reports/tables/llm_per_competency.csv`, `reports/tables/model_comparison.csv`.

Comparison systems: BM25 Top-1 vs BM25 Top-5 + constrained Gemini. An optional local Ollama comparison (same tasks, temperature 0, BM25 Top-5) writes separately to `reports/metrics/ollama_constrained_metrics.json` and `reports/tables/model_comparison_with_ollama.csv`. It does not replace the frozen Gemini metrics.

## Evidence (scripts 17–18)

Mechanical validity = quote is an exact substring of `fragment_text`.

Human Gate 2 is **COMPLETE**: 83/83 pedagogical ratings (65 × 2, 16 × 1, 2 × 0). Summaries are in `reports/metrics/evidence_review_summary.json`.

100% of evidence quotes were mechanically valid exact substrings, while 78.3% were judged to clearly support the predicted competency. Mechanical exactness does not guarantee pedagogical relevance.

## Error analysis (script 19)

Reads gold, BM25, constrained Gemini, and `data/reviews/evidence_review.csv`. Join key: `fragment_id` + `competency_id`.

Prediction-correctness flags and evidence-quality flags are separate and may overlap. `primary_error_category` partitions fragments for presentation only.

Outputs: `reports/tables/error_analysis.csv`, `reports/tables/error_examples.csv`, `reports/metrics/error_summary.json`, `reports/EVIDENCE_AWARE_ERROR_ANALYSIS.md`.

## Resource-level evaluation (script 22)

Resource gold is **DERIVED** from the human-reviewed fragment reference. It is not a second independent annotation exercise.

- Page gold = union of that Page's fragment labels (`reference_derivation = union_of_human_reviewed_fragment_labels`).
- Quiz-question gold = that question's fragment labels (`reference_derivation = human_reviewed_question_fragment_label`).
- `data/gold/manual_moodle_links.csv` is not used. Quiz activity-level Moodle mappings are not question gold.

Evaluates existing `data/processed/resource_predictions.jsonl` (no new Gemini or Ollama calls). Metrics include micro P/R/F1, `macro_all_13`, `macro_gold_supported_labels`, exact-set / subset accuracy, average absolute label-count error, coverage, abstention, per-resource P/R/F1, and per-competency support/TP/FP/FN.

Outputs: `data/processed/resource_reference.jsonl`, `reports/metrics/resource_level_metrics.json`, `reports/tables/resource_level_evaluation.csv`, `reports/tables/resource_level_per_competency.csv`, `reports/tables/resource_level_error_examples.csv`, `reports/RESOURCE_LEVEL_EVALUATION.md`.

## Minimal hierarchy / graph analysis (script 23)

This is a **post-hoc hierarchy ablation**, not part of the historical Gemini run. A deterministic child-preference rule was applied after the frozen Gemini predictions to assess the effect of removing redundant parent labels. Original Gemini and resource-level metric files were not replaced.

Warnings: `parent_child_redundancy`, `granularity_conflict`, `invalid_hierarchy_reference`. Simulated predictions are stored under `data/experiments/`.

Human Gate 2 is complete. Resource-level evaluation is **COMPLETE**. Minimal hierarchy / graph analysis is **COMPLETE**. Ollama remains a post-hoc optional experiment and is not mixed into the Gemini metric files.

Outputs: `data/processed/graph_warnings.jsonl`, `reports/metrics/graph_check_summary.json`, `reports/metrics/graph_child_preference_fragment_metrics.json`, `reports/metrics/graph_child_preference_resource_metrics.json`, `reports/MINIMAL_GRAPH_HIERARCHY_ANALYSIS.md`.


## Teacher review (script 28)

Unit of review is one predicted **(resource, competency)** mapping; there are 34.

Reads `data/reviews/corpus_teacher_reviews.csv` (frozen-corpus decisions) and,
separately, `data/reviews/teacher_reviews.csv` (the runtime app's log). The two
are reported apart and never merged.

**Rates are reported only when real decisions exist.** With nothing reviewed,
`acceptance_rate`, `edit_rate` and `rejection_rate` are `null`, not `0.0`, and
`status` is `WAITING_FOR_HUMAN`. `0.0` would read as "teachers accepted
nothing", which is a finding; `null` correctly says nothing was reviewed. The
denominator for rates is reviewed suggestions, not all 34 mappings; `add`
decisions sit outside it.

Only `reviewer_role` of `teacher` or `supervisor` sets
`teacher_or_supervisor_validation_performed`. A researcher decision is never
reported as teacher validation.

Outputs: `reports/metrics/teacher_review_summary.json`,
`reports/tables/teacher_review_summary.csv`.

## Evidence-usefulness pilot (script 27, app page 7)

Exploratory A/B comparison of judging a suggestion **without** the evidence
quote shown initially (condition A) against **with** it (condition B).

Sampling is stratified over `parent_child_redundancy` / `incorrect_prediction` /
`correct_prediction`, rotating across courses within each stratum, and
conditions are balanced within stratum. A fixed seed plus a saved manifest make
the design exactly reproducible.

Records decision, 1–5 confidence, start/end timestamps, elapsed seconds, and
whether the reviewer opened the hidden evidence. Summaries are descriptive by
condition (median time, acceptance/edit/rejection, median confidence, n).

**No significance test is computed** — sample size and within-reviewer design do
not support one. If only the researcher participates, the result is labelled a
**researcher pilot**, never a teacher study; the label is derived from the
recorded roles, not assumed.

## Validated coverage (Section O)

Coverage counts a (resource, competency) pair only when a human decision
validates it: `accept`, `add`, or the replacement side of a `modify`. A
`reject` validates nothing, and **an unreviewed prediction is not coverage**.

This is why the inverse index can show 13/13 competencies with a predicted
resource while validated coverage is 0/13. Predicted coverage and confirmed
coverage are different quantities and are kept visibly separate.

## Optional unconstrained all-13 comparison (scripts 24–26)

Held identical to the constrained run — same model, temperature 0, ≤3
selections, abstention rule, exact-substring evidence requirement, output
schema, fragment corpus, competency descriptions, and the *same validator*
(`llm_validation.validate_alignment_response`, reused unchanged).

**Only intended difference:** `allowed_idnumbers` is all 13 competencies rather
than the BM25 Top-5. One consequence follows: with no retrieval step the
candidate block omits the `BM25 score:` line, since a fabricated score would add
a signal the condition does not have. `compare_conditions` audits this and
reported 0 fragment-text mismatches and 0 instruction mismatches across all 35
fragments.

All outputs live under `data/experiments/`. The live run spends API quota and
refuses to execute without `--i-authorize-the-unconstrained-experiment`. Script
26 refuses to evaluate a run that has not happened and estimates nothing in its
place. Status: **software complete, experiment NOT RUN**.
