# Reproducibility

A short index. The full guide, with every command, is
`FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md`.

---

## What can be reproduced without credentials

All reported results. The frozen experimental artefacts are in the repository,
so no Moodle access and no API key are required.

```bash
source .venv/bin/activate

python scripts/12_validate_manual_annotations.py --mode final   # PASSED, 35/35
python scripts/15_evaluate_bm25.py
python scripts/16_evaluate_constrained_llm.py
python scripts/19_analyze_errors.py
python scripts/22_evaluate_resource_level.py
python scripts/23_run_graph_checks.py --simulate-child-preference
python scripts/20_write_reproducibility_manifest.py
```

Each script snapshots the checksums of the files it could affect before and
after running, and aborts if any changed.

## What must never be regenerated

| Artefact | Reason |
|---|---|
| `data/interim/gemini_responses.jsonl` | Historical third-party API output |
| `data/interim/gemini_validated.jsonl` | Derived from the above |
| `data/gold/manual_fragment_annotations.csv` | Human work — 38 reference labels |
| `data/reviews/evidence_review.csv` | Human work — 83 ratings |
| `data/processed/*.jsonl` | Frozen corpus definition |
| `data/interim/bm25_candidates.jsonl` | Frozen retrieval state |

The model runner provides no restart mechanism; it resumes from checkpoints
only.

## Protected artefacts

21 files, enumerated with checksums and rationale in
`reports/PROTECTED_ARTIFACT_CANONICAL_LIST.md`.

- **Tier 1 (11)** — frozen inputs and human judgement. Never regenerate.
- **Tier 2 (10)** — derived results. Regenerable and verified deterministic, but
  a change means a published figure moved.

## Determinism

Temperature 0 for the model; fixed seeds for sampling; sorted, fixed-timestamp
archive construction. Re-running `scripts/18_summarize_evidence_review.py`
reproduces its output byte for byte, which was verified.

## Environment

Python 3.12.3. Exact pinned versions in `requirements-lock.txt`; loose ranges
for development in `requirements.txt`.

## Verification

```bash
python -m pytest -q                              # 435 passed
python -m compileall -q src scripts tests app
python scripts/ui_smoke_check.py                 # 14 pages, network blocked
```

Last verified 22 September 2026: validator PASSED 35/35, 435 tests passed,
compile clean, 14/14 pages rendered, 21/21 protected artefacts unchanged.

> The figure reported by `scripts/collect_handoff_facts.py` (221) is a
> **pre-existing regression subset** covering 32 of 39 test files, not the
> project total. The authoritative count comes from `python -m pytest -q`.
