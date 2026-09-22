"""Evaluate constrained Ollama against the human-reviewed reference.

Writes experiment-only metric files. Does not replace
constrained_llm_metrics.json or model_comparison.csv.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, read_csv, write_csv, write_json
from moodle_competency.evaluation import (
    GeminiIncompleteError,
    HumanGateClosedError,
    PER_LABEL_TABLE_COLUMNS,
    gold_sets_from_rows,
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
    macro_prf_views,
    micro_prf,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
FRAGMENTS = PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
OLLAMA_PREDICTIONS = (
    PROJECT_ROOT / "data" / "experiments" / "ollama_constrained_validated.jsonl"
)
GEMINI_METRICS = PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json"
BM25_METRICS = PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json"
METRICS_PATH = PROJECT_ROOT / "reports" / "metrics" / "ollama_constrained_metrics.json"
PER_FRAGMENT = PROJECT_ROOT / "reports" / "tables" / "ollama_per_fragment.csv"
PER_LABEL = PROJECT_ROOT / "reports" / "tables" / "ollama_per_competency.csv"
COMPARISON = (
    PROJECT_ROOT / "reports" / "tables" / "model_comparison_with_ollama.csv"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Ollama constrained experiment outputs."
    )
    parser.add_argument("--allow-partial", action="store_true")
    return parser.parse_args()


def compute_llm_metrics(
    gold_sets: list[list[str]],
    predicted_sets: list[list[str]],
    label_set: list[str],
    *,
    final: bool,
) -> dict:
    micro = micro_prf(gold_sets, predicted_sets)
    views = macro_prf_views(gold_sets, predicted_sets, label_set)
    macro = views["macro_all_13"]
    return {
        "status": "COMPLETE" if final else "PARTIAL / NOT FINAL",
        "final": final,
        "experiment": "POST-HOC LOCAL OLLAMA COMPARISON",
        "micro_precision": micro["precision"],
        "micro_recall": micro["recall"],
        "micro_f1": micro["f1"],
        "macro_precision": macro["precision"],
        "macro_recall": macro["recall"],
        "macro_f1": macro["f1"],
        "macro_all_13": macro,
        "macro_gold_supported_labels": views["macro_gold_supported_labels"],
        "exact_set_match": exact_set_match(gold_sets, predicted_sets),
        "coverage": coverage_rate(predicted_sets),
        "abstention_rate": abstention_rate(predicted_sets),
        "average_predicted_labels": average_predicted_labels(predicted_sets),
    }


def main() -> int:
    arguments = parse_arguments()

    try:
        rows = read_csv(GOLD)
        require_complete_gold(rows)
        fragments = load_jsonl(FRAGMENTS)
        predictions = load_jsonl(OLLAMA_PREDICTIONS)
        competencies = load_jsonl(COMPETENCIES)
    except HumanGateClosedError as error:
        print(str(error))
        return 2
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("=== OLLAMA CONSTRAINED EVALUATION ===")

    try:
        require_complete_gemini(fragments=fragments, predictions=predictions)
        complete = True
    except GeminiIncompleteError as error:
        complete = False
        print(str(error))

        if not arguments.allow_partial:
            print("Refusing FINAL Ollama evaluation. Use --allow-partial.")
            return 3

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
        final=complete,
    )

    if not complete:
        print(json.dumps(metrics, indent=2))
        print("Not written to final experiment report paths.")
        return 3

    write_json(metrics, METRICS_PATH)
    fragment_rows = []

    for row, gold, predicted in zip(rows, gold_sets, predicted_sets, strict=True):
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

    comparison_rows = []

    if BM25_METRICS.exists():
        bm25 = json.loads(BM25_METRICS.read_text(encoding="utf-8"))
        top1 = bm25.get("top1_micro") or {}
        comparison_rows.append(
            {
                "system": "BM25 Top-1",
                "micro_precision": f"{float(top1.get('precision', 0.0)):.4f}",
                "micro_recall": f"{float(top1.get('recall', 0.0)):.4f}",
                "micro_f1": f"{float(top1.get('f1', 0.0)):.4f}",
                "status": str(bm25.get("status", "")),
            }
        )

    if GEMINI_METRICS.exists():
        gemini = json.loads(GEMINI_METRICS.read_text(encoding="utf-8"))
        comparison_rows.append(
            {
                "system": "BM25 Top-5 + constrained Gemini",
                "micro_precision": f"{float(gemini.get('micro_precision', 0.0)):.4f}",
                "micro_recall": f"{float(gemini.get('micro_recall', 0.0)):.4f}",
                "micro_f1": f"{float(gemini.get('micro_f1', 0.0)):.4f}",
                "status": str(gemini.get("status", "")),
            }
        )

    comparison_rows.append(
        {
            "system": "BM25 Top-5 + constrained Ollama",
            "micro_precision": f"{float(metrics['micro_precision']):.4f}",
            "micro_recall": f"{float(metrics['micro_recall']):.4f}",
            "micro_f1": f"{float(metrics['micro_f1']):.4f}",
            "status": str(metrics["status"]),
        }
    )
    write_csv(
        comparison_rows,
        COMPARISON,
        ["system", "micro_precision", "micro_recall", "micro_f1", "status"],
    )
    print(f"Wrote {METRICS_PATH}")
    print(f"Wrote {COMPARISON}")
    print("Frozen Gemini metric files were not replaced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
