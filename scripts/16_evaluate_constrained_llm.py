"""Evaluate constrained Gemini against completed human gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, read_csv, write_csv, write_json
from moodle_competency.evaluation import (
    GeminiIncompleteError,
    HumanGateClosedError,
    MODEL_COMPARISON_COLUMNS,
    PER_LABEL_TABLE_COLUMNS,
    gold_sets_from_rows,
    model_comparison_rows,
    per_label_table_rows,
    predicted_sets_from_gemini,
    require_complete_gemini,
    require_complete_gold,
)
from moodle_competency.metrics import (
    abstention_rate,
    average_predicted_labels,
    coverage_rate,
    exact_set_match,
    instance_prf,
    macro_prf,
    micro_prf,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
PREDICTIONS = PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl"
FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
METRICS_PATH = (
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json"
)
PER_FRAGMENT = PROJECT_ROOT / "reports" / "tables" / "llm_per_fragment.csv"
PER_LABEL = PROJECT_ROOT / "reports" / "tables" / "llm_per_competency.csv"
COMPARISON = PROJECT_ROOT / "reports" / "tables" / "model_comparison.csv"
BM25_METRICS = PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate constrained Gemini after gold and Gemini gates."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check readiness without writing final metrics.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Compute PARTIAL / NOT FINAL analysis; do not write final paths.",
    )
    return parser.parse_args()


def compute_llm_metrics(
    gold_sets: list[list[str]],
    predicted_sets: list[list[str]],
    label_set: list[str],
    *,
    final: bool,
) -> dict:
    micro = micro_prf(gold_sets, predicted_sets)
    macro = macro_prf(gold_sets, predicted_sets, label_set)
    return {
        "status": "COMPLETE" if final else "PARTIAL / NOT FINAL",
        "final": final,
        "micro_precision": micro["precision"],
        "micro_recall": micro["recall"],
        "micro_f1": micro["f1"],
        "macro_precision": macro["precision"],
        "macro_recall": macro["recall"],
        "macro_f1": macro["f1"],
        "exact_set_match": exact_set_match(gold_sets, predicted_sets),
        "coverage": coverage_rate(predicted_sets),
        "abstention_rate": abstention_rate(predicted_sets),
        "average_predicted_labels": average_predicted_labels(
            predicted_sets
        ),
    }


def main() -> int:
    arguments = parse_arguments()

    try:
        rows = read_csv(GOLD)
        fragments = load_jsonl(FRAGMENTS)
        predictions = load_jsonl(PREDICTIONS)
        competencies = load_jsonl(COMPETENCIES)
        require_complete_gold(rows)
    except HumanGateClosedError as error:
        print(str(error))
        print(
            "Human Gate 1 is not open: manual gold annotations "
            "are incomplete."
        )
        return 2
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("=== CONSTRAINED LLM EVALUATION ===")
    print("Human Gate 1: OPEN")

    try:
        require_complete_gemini(
            fragments=fragments,
            predictions=predictions,
        )
        gemini_complete = True
    except GeminiIncompleteError as error:
        gemini_complete = False
        print(str(error))

        if not arguments.allow_partial:
            print(
                "Refusing FINAL evaluation. Use --allow-partial "
                "only for labelled PARTIAL / NOT FINAL analysis."
            )
            return 3

    if arguments.dry_run:
        print("Dry-run: readiness checked. No metrics written.")
        return 0 if gemini_complete else 3

    gold_sets = gold_sets_from_rows(rows)
    predicted_sets = predicted_sets_from_gemini(rows, predictions)
    label_set = [
        str(item.get("idnumber", "")).strip()
        for item in competencies
        if str(item.get("idnumber", "")).strip()
    ]
    metrics = compute_llm_metrics(
        gold_sets,
        predicted_sets,
        label_set,
        final=gemini_complete,
    )

    if not gemini_complete:
        print("Status: PARTIAL / NOT FINAL")
        print(json.dumps(metrics, indent=2))
        print("Not written to final report paths.")
        return 3

    write_json(metrics, METRICS_PATH)
    fragment_rows = []

    for row, gold, predicted in zip(
        rows,
        gold_sets,
        predicted_sets,
        strict=True,
    ):
        scores = instance_prf(gold, predicted)
        fragment_rows.append(
            {
                "fragment_id": row.get("fragment_id", ""),
                "gold_competency_ids": ";".join(gold),
                "predicted_competency_ids": ";".join(predicted),
                "exact_set_match": str(gold == predicted),
                "precision": f"{scores['precision']:.4f}",
                "recall": f"{scores['recall']:.4f}",
                "f1": f"{scores['f1']:.4f}",
            }
        )

    write_csv(
        fragment_rows,
        PER_FRAGMENT,
        [
            "fragment_id",
            "gold_competency_ids",
            "predicted_competency_ids",
            "exact_set_match",
            "precision",
            "recall",
            "f1",
        ],
    )
    write_csv(
        per_label_table_rows(gold_sets, predicted_sets, label_set),
        PER_LABEL,
        PER_LABEL_TABLE_COLUMNS,
    )

    if BM25_METRICS.exists():
        bm25_metrics = json.loads(
            BM25_METRICS.read_text(encoding="utf-8")
        )

        if (
            bm25_metrics.get("status") == "COMPLETE"
            and metrics.get("status") == "COMPLETE"
        ):
            write_csv(
                model_comparison_rows(bm25_metrics, metrics),
                COMPARISON,
                MODEL_COMPARISON_COLUMNS,
            )

    print(f"Wrote {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
