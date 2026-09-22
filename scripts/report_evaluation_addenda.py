"""Write extra evaluation views without replacing frozen core metric files.

Reads existing BM25 / constrained Gemini metrics and the human-reviewed
reference. Writes NEW files only:

- reports/metrics/macro_label_views.json
- reports/tables/label_support_prf.csv
- reports/tables/system_delta_summary.csv

Does not rewrite bm25_metrics.json, constrained_llm_metrics.json,
model_comparison.csv, gold, or Gemini checkpoints.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, read_csv, write_csv, write_json
from moodle_competency.evaluation import (
    HumanGateClosedError,
    SYSTEM_DELTA_COLUMNS,
    gold_sets_from_rows,
    predicted_sets_from_gemini,
    ranked_candidates_from_bm25,
    require_complete_gold,
    system_delta_rows,
)
from moodle_competency.metrics import macro_prf_views, per_label_prf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
CANDIDATES = PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl"
PREDICTIONS = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
BM25_METRICS = PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json"
LLM_METRICS = PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json"
MACRO_VIEWS = PROJECT_ROOT / "reports" / "metrics" / "macro_label_views.json"
LABEL_TABLE = PROJECT_ROOT / "reports" / "tables" / "label_support_prf.csv"
DELTA_TABLE = PROJECT_ROOT / "reports" / "tables" / "system_delta_summary.csv"

LABEL_TABLE_COLUMNS = (
    "system",
    "competency_id",
    "support",
    "predicted_count",
    "true_positives",
    "false_positives",
    "false_negatives",
    "precision",
    "recall",
    "f1",
    "gold_supported",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Write gold-supported macro views and a BM25/Gemini delta "
            "table without changing frozen core metric JSON files."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute views without writing files.",
    )
    return parser.parse_args()


def _format_label_rows(
    system: str,
    rows: list[dict],
) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []

    for row in rows:
        formatted.append(
            {
                "system": system,
                "competency_id": str(row["competency_id"]),
                "support": str(row["support"]),
                "predicted_count": str(row["predicted_count"]),
                "true_positives": str(row["true_positives"]),
                "false_positives": str(row["false_positives"]),
                "false_negatives": str(row["false_negatives"]),
                "precision": f"{float(row['precision']):.10f}",
                "recall": f"{float(row['recall']):.10f}",
                "f1": f"{float(row['f1']):.10f}",
                "gold_supported": "true" if row["gold_supported"] else "false",
            }
        )

    return formatted


def main() -> int:
    arguments = parse_arguments()

    try:
        gold_rows = read_csv(GOLD)
        require_complete_gold(gold_rows)
        candidates = load_jsonl(CANDIDATES)
        predictions = load_jsonl(PREDICTIONS)
        competencies = load_jsonl(COMPETENCIES)
        bm25_metrics = json.loads(BM25_METRICS.read_text(encoding="utf-8"))
        llm_metrics = json.loads(LLM_METRICS.read_text(encoding="utf-8"))
    except HumanGateClosedError as error:
        print(str(error))
        return 2
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    label_set = [
        str(item.get("idnumber", "")).strip()
        for item in competencies
        if str(item.get("idnumber", "")).strip()
    ]
    gold_sets = gold_sets_from_rows(gold_rows)
    ranked = ranked_candidates_from_bm25(gold_rows, candidates)
    top1 = [names[:1] for names in ranked]
    gemini_sets = predicted_sets_from_gemini(gold_rows, predictions)

    bm25_views = macro_prf_views(gold_sets, top1, label_set)
    gemini_views = macro_prf_views(gold_sets, gemini_sets, label_set)

    payload = {
        "status": "COMPLETE",
        "note": (
            "macro_all_13 is the existing unweighted mean over all 13 "
            "competencies. macro_gold_supported_labels is a second view "
            "over competencies with positive human-reference support. "
            "Frozen bm25_metrics.json and constrained_llm_metrics.json "
            "are not replaced."
        ),
        "bm25_top1": bm25_views,
        "bm25_top5_constrained_gemini": gemini_views,
        "frozen_core_macro_all_13": {
            "bm25_top1": bm25_metrics.get("top1_macro"),
            "bm25_top5_constrained_gemini": {
                "precision": llm_metrics.get("macro_precision"),
                "recall": llm_metrics.get("macro_recall"),
                "f1": llm_metrics.get("macro_f1"),
            },
        },
    }
    delta_rows = system_delta_rows(bm25_metrics, llm_metrics)
    label_rows = _format_label_rows(
        "BM25 Top-1",
        per_label_prf(gold_sets, top1, label_set),
    ) + _format_label_rows(
        "BM25 Top-5 + constrained Gemini",
        per_label_prf(gold_sets, gemini_sets, label_set),
    )

    print("=== EVALUATION ADDENDA ===")
    print(
        "Gemini macro_all_13 F1: "
        f"{float(gemini_views['macro_all_13']['f1']):.4f}"
    )
    print(
        "Gemini macro_gold_supported_labels F1: "
        f"{float(gemini_views['macro_gold_supported_labels']['f1']):.4f}"
    )
    print(
        "Gold-supported labels: "
        f"{gemini_views['gold_supported_label_count']}/"
        f"{gemini_views['all_label_count']}"
    )

    if arguments.dry_run:
        print("Dry-run: no files written.")
        return 0

    write_json(payload, MACRO_VIEWS)
    write_csv(label_rows, LABEL_TABLE, LABEL_TABLE_COLUMNS)
    write_csv(delta_rows, DELTA_TABLE, SYSTEM_DELTA_COLUMNS)
    print(f"Wrote {MACRO_VIEWS}")
    print(f"Wrote {LABEL_TABLE}")
    print(f"Wrote {DELTA_TABLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
