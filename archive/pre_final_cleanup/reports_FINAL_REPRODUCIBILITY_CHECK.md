# Final reproducibility check

**Date:** 2026-09-18  
**Rule:** no `.env` content, no API keys, no Moodle tokens, no DB passwords, no `userprivateaccesskey` values in packaged artefacts.

`reports/reproducibility_manifest.json` sets `contains_secrets: false` and does not read `.env`.

## Tests and compile

| Command | Result |
|---|---|
| `python -m pytest -q` | 221 passed |
| `python -m compileall -q src scripts tests app.py pages` | succeeded |
| `python scripts/34_summarize_human_validation.py` | HUMAN VALIDATION NOT YET PERFORMED |
| `python scripts/35_generate_final_figures.py` | wrote `reports/figures/` |

## Environment

| Item | Value |
|---|---|
| Python | 3.12.3 |
| Package | 0.1.0 |
| Moodle (recorded) | 5.2.1+ (Build: 20260722) |
| Model | gemini-3.5-flash, temperature 0, prompt 1.0 |
| pytest | 9.1.1 |
| streamlit | 1.64.0 |
| rank-bm25 | 0.2.2 |
| scikit-learn | 1.9.0 |
| google-genai | 2.14.0 |
| pypdf | 6.19.0 |
| matplotlib | 3.11.2 |
| beautifulsoup4 | 4.15.0 |

## Dataset counts

20 resources, 35 fragments, 13 competencies, 35/35 Gemini validated, 35/35 human-reviewed reference rows, 38 reference labels, 3 multi-label, 1 ambiguous, 0 NONE.

## Frozen experiment hashes (unchanged)

| File | SHA-256 |
|---|---|
| `data/gold/manual_fragment_annotations.csv` | `3f96afd974db96394ee22239f0293bf1b641548836072839909b3992cf92fd53` |
| `data/interim/bm25_candidates.jsonl` | `4e4e1ec030d8f1bfd17865690c83d66cec24fb256d8dc5e3dd523a27325bcaee` |
| `data/interim/gemini_validated.jsonl` | `4ec9abf4aa1d3b4cdab2b1a5b367bc8ed9512b6b85616d053809dd6770e03a03` |
| `reports/metrics/bm25_metrics.json` | `f24ff968200a6ceacaee67986dabef19bc08eb04a026696232a91924c3366ab2` |
| `reports/metrics/constrained_llm_metrics.json` | `5ab206050828ec31f3b0cf9e45f7f889060c666e489d666fe2d1a36789e43248` |
| `data/reviews/evidence_review.csv` | `c0747d433b2b5e98ebcde50dbdd5df9836190447abfe93f7ef67bc10cc65c667` |
| `reports/metrics/resource_level_metrics.json` | `9648d05548d6434e209142b9d4b6822d2cd5ae296eacbd61640af030fa4c90a2` |
| `data/experiments/graph_child_preference_predictions.jsonl` | `13dc984c2cb386723cb36943133b872015fe516d88468149a12597fbc901938a` |
| `data/experiments/ollama_constrained_validated.jsonl` | `c3f78f02802b47b62cfc77b405797b012e3020dfbd43d83a434e731f0f8d53bf` |

## Final report / table / figure hashes

| File | SHA-256 |
|---|---|
| `reports/FINAL_INTERNSHIP_REPORT.md` | `0c4a33c476fdfceeecd44cb1a161a9f475901fd60ae55daa808dd0660b97751d` |
| `reports/tables/final_results_summary.csv` | `bc3408a2aea6d1f5b0d9d96247798df165f9635ecc5d479c6bef5a42308072e3` |
| `reports/tables/final_key_examples.csv` | `91b6df3fa243bc790ddd43eb541c08dc223b82f4537151a96a66a203db89f983` |
| `reports/HUMAN_VALIDATION_SUMMARY.md` | `57053ecea3be26468e33b44b1e8bb0756bfe9813d1c7f1ce7dd9b8e9ceb37e78` |
| `reports/figures/bm25_recall_at_k.png` | `23132ccfdd412d2e73c2f3142e2095227f0c44fb4dfc6e73f0a657f35d816d1d` |
| `reports/figures/fragment_system_comparison.png` | `94fdbe6d3dc9d81c0049a7c96de527def1043af1fcbbfa61e697b71fb3d2789b` |
| `reports/figures/resource_system_comparison.png` | `c9be276017712d7a4160779daff15ca4abcf31bba7d570f72e6ae8997440d687` |
| `reports/figures/evidence_quality.png` | `8303833253a4d268dfb1e3f8330a7a62d7f923b30e10fa0673312eea9643b27f` |
| `reports/figures/error_categories.png` | `ac7f0efb179ee6fac2ce05dafef7566cd1222e2a4418ca633b7359d614a6936a` |

Teacher app files hashed in the manifest: `app.py`, `teacher_app_pages.py`, `teacher_ui.py`, `runtime_analysis.py`, `runtime_storage.py`, `resource_ingestion.py`.

## Secret scan notes

- `.env` is not in the backup ZIP.
- `reports/site_info.json` and `data/raw/` are excluded (Moodle private fields).
- Documentation may mention the *names* of secret keys; packaged files must not contain live values.

Full hash table: `reports/reproducibility_manifest.json`.
