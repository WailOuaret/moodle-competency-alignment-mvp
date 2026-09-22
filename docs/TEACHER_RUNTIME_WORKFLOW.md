# Teacher runtime workflow

**Status:** software complete, mock-tested. Live Gemini/Ollama runtime analysis has not been run. Formal teacher study has not started.

## 1. Purpose

The teacher-facing runtime lets a teacher or researcher analyze one learning resource and review competency suggestions with exact textual evidence. It is the practical MVP for Function A (resource → competencies) and Function B (competency → resources).

This is not a new alignment algorithm. It reuses the evaluated pipeline:

extract → normalize → fragment → BM25 Top-5 → constrained LLM (temperature 0, max 3) → exact evidence validation → post-processing hierarchy check → resource aggregation → human accept / reject / modify.

## 2. Relation to the evaluated research pipeline

The frozen Gemini experiment remains the scientific result:

- 35 fragments, 20 resources, 13 UTC GI competencies
- fragment micro P/R/F1 = 0.7255 / 0.9737 / 0.8315
- resource micro P/R/F1 = 0.6765 / 0.9583 / 0.7931
- post-hoc child-preference ablation is separate and must not be described as original Gemini output

Runtime analyses are stored under `data/runtime/` and must never rewrite gold, interim Gemini files, BM25 candidates, frozen metrics, evidence reviews, graph-ablation predictions, or Ollama experiment checkpoints.

## 3. Moodle resource selection (Mode A)

The teacher chooses a course, then a Page or Quiz question from the already-extracted catalogue (`data/processed/resources.jsonl`).

Moodle itself is not modified. The runtime copies text that was already extracted for the MVP. If that catalogue is missing, the UI reports that Moodle is unavailable.

Quiz questions remain one fragment each, as in the evaluated experiment.

## 4. Upload / paste resource (Mode B)

The teacher supplies a title, optional course, and one of:

- pasted text
- TXT
- HTML
- text-native PDF

PDF upload is a runtime/demo capability only. Uploaded files are not added to the frozen evaluation corpus. There is no OCR. If a PDF has no extractable text, the system reports:

`No machine-readable text was found. OCR is outside the current MVP.`

HTML is treated as data. Scripts are stripped and never executed.

## 5. Extraction

`src/moodle_competency/resource_ingestion.py` builds a runtime resource with stable `runtime_resource_id`, SHA-256 hashes, provenance, and `research_status = RUNTIME_DEMO`.

## 6. Fragmentation

The same pedagogical rule as the experiment: prefer author-created structure before arbitrary chunking.

- Page / HTML: heading and paragraph blocks, then the existing deterministic `chunk_text` limit
- Quiz question: one fragment
- pasted text / TXT: paragraph boundaries, then the same chunker if a paragraph is too large

Each fragment keeps `fragment_id`, `runtime_resource_id`, index, type, text, source structure, offsets, and content hash.

## 7. BM25 Top-5

The existing 13 competency profiles are reused. The competency framework is not rebuilt. Each fragment receives five candidates with id, rank, and BM25 score, using `retrieval.py`.

## 8. Constrained LLM

Injectable backends:

- Gemini (same contract as the frozen experiment: Top-5 only, temperature 0, max 3, exact evidence, prompt version `1.0`)
- Ollama (`mistral:latest`) through the existing adapter, optional

If Ollama is down, the UI shows `Ollama backend unavailable.` It does not silently switch to Gemini.

## 9. Evidence validation

`llm_validation.py` rejects:

- competency IDs outside the BM25 Top-5
- invalid confidence
- non-exact evidence
- duplicate selections
- more than three selections

Abstention (no competency) is valid when `abstain` is true and `selected` is empty.

## 10. Hierarchy post-processing

After validation, the system runs the minimal hierarchy checks. The UI label is **Post-processing hierarchy check**. Gemini is not described as having performed graph reasoning.

Two views are kept:

- original model output
- hierarchy-reconciled view (child-preference: if parent + direct child are both predicted, remove the parent from the reconciled copy only)

Original predictions are never destroyed.

## 11. Resource aggregation

Validated fragment labels are aggregated with `aggregation.py`. Resource cards keep supporting fragment ids, evidence quotes, confidences, BM25 ranks, hierarchy warnings, and original vs reconciled labels.

## 12. Teacher / researcher validation

Decisions persist to `data/reviews/teacher_reviews.csv`:

- ACCEPT / REJECT / MODIFY
- MODIFY replacements must be one of the 13 catalogue competencies

Reviewer role is required: `researcher`, `teacher`, or `supervisor`.

Until an actual teacher reviews a resource, do not write “teacher validated”. Wail’s own tests are **researcher review**.

## 13. Competency → resources

The inverse page lists resources linked to a selected competency. **MODEL SUGGESTIONS** are unreviewed predictions. **VALIDATED** contains only ACCEPT or MODIFY decisions. Unreviewed suggestions are never described as validated.

## 14. Runtime vs frozen experiment separation

| Frozen (do not rewrite) | Runtime (new) |
|---|---|
| `data/gold/` | `data/runtime/uploads/` |
| `data/interim/bm25_candidates.jsonl` | `data/runtime/resources/` |
| `data/interim/gemini_*.jsonl` | `data/runtime/fragments/` |
| `data/processed/fragments.jsonl` | `data/runtime/retrieval/` |
| `data/processed/resource_predictions.jsonl` | `data/runtime/model_responses/` |
| `reports/metrics/*.json` (core) | `data/runtime/analyses/` |
| `data/reviews/evidence_review.csv` | `data/runtime/manifests/` |
| `data/experiments/graph_child_preference_predictions.jsonl` | `data/reviews/teacher_reviews.csv` |
| Ollama experiment checkpoints | |

Each analysis writes `data/runtime/manifests/<analysis_id>.json` without API secrets.
