"""Evaluate the OPTIONAL all-13 unconstrained Gemini run (Section K).

Scores the unconstrained responses against the same human-reviewed fragment
reference used for the constrained run, with the same metric functions, and
writes a three-system comparison.

This script refuses to run until the unconstrained experiment has actually been
performed. It never estimates, simulates or back-fills a result: with no
responses there is nothing to evaluate, and that is reported as such.

No API call is made here. All outputs carry an ``unconstrained_`` prefix and no
constrained metric file is modified.

    python scripts/26_evaluate_unconstrained_gemini.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, read_csv, write_csv, write_json
from moodle_competency.evaluation import (
    gold_sets_from_rows,
    predicted_sets_from_gemini,
    require_complete_gold,
)
from moodle_competency.metrics import (
    abstention_rate,
    average_predicted_labels,
    coverage_rate,
    exact_set_match,
    macro_prf_views,
    micro_prf,
    per_label_counts,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"

EXPERIMENTS = PROJECT_ROOT / "data" / "experiments"
VALIDATED_IN = EXPERIMENTS / "unconstrained_gemini_validated.jsonl"

CONSTRAINED_METRICS = (
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json"
)
BM25_METRICS = PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json"

METRICS_OUT = (
    PROJECT_ROOT / "reports" / "metrics" / "unconstrained_llm_metrics.json"
)
PER_LABEL_OUT = (
    PROJECT_ROOT / "reports" / "tables" / "unconstrained_per_competency.csv"
)
COMPARISON_OUT = (
    PROJECT_ROOT / "reports" / "tables" / "candidate_restriction_comparison.csv"
)

PER_LABEL_COLUMNS = (
    "competency_id",
    "gold_count",
    "predicted_count",
    "true_positives",
    "false_positives",
    "false_negatives",
)

COMPARISON_COLUMNS = (
    "metric",
    "BM25_Top1",
    "BM25_Top5_constrained_Gemini",
    "All13_unconstrained_Gemini",
    "delta_unconstrained_minus_constrained",
)

PROTECTED_PATHS = (
    PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
    PROJECT_ROOT / "data" / "interim" / "llm_tasks.jsonl",
    PROJECT_ROOT / "reports" / "metrics" / "constrained_llm_metrics.json",
    PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json",
)


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)

    return digest.hexdigest()


def snapshot_protected() -> dict[str, str | None]:
    return {str(path): file_sha256(path) for path in PROTECTED_PATHS}


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the optional all-13 unconstrained Gemini run.",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    if not VALIDATED_IN.exists():
        print(
            "The unconstrained experiment has not been run.\n\n"
            f"  missing: {VALIDATED_IN}\n\n"
            "There is nothing to evaluate, and nothing will be estimated in "
            "its place. Build and run it first:\n"
            "  python scripts/24_build_unconstrained_tasks.py\n"
            "  python scripts/25_run_unconstrained_gemini.py "
            "--i-authorize-the-unconstrained-experiment",
            file=sys.stderr,
        )
        return 2

    validated = load_jsonl(VALIDATED_IN)

    if not validated:
        print(f"{VALIDATED_IN} is empty. Nothing to evaluate.", file=sys.stderr)
        return 2

    before = snapshot_protected()

    gold_rows = read_csv(GOLD)
    require_complete_gold(gold_rows)

    competencies = load_jsonl(COMPETENCIES)
    label_set = [
        str(record.get("idnumber", "")).strip()
        for record in competencies
        if str(record.get("idnumber", "")).strip()
    ]

    gold_sets = gold_sets_from_rows(gold_rows)
    predicted_sets = predicted_sets_from_gemini(gold_rows, validated)

    responded = {
        str(record.get("fragment_id", "")).strip() for record in validated
    }
    missing = [
        str(row.get("fragment_id", "")).strip()
        for row in gold_rows
        if str(row.get("fragment_id", "")).strip() not in responded
    ]

    micro = micro_prf(gold_sets, predicted_sets)
    macro_views = macro_prf_views(gold_sets, predicted_sets, label_set)
    label_counts = per_label_counts(gold_sets, predicted_sets, label_set)

    metrics = {
        "experiment": "unconstrained_all_competencies",
        "experiment_kind": "OPTIONAL POST-CORE CANDIDATE-RESTRICTION COMPARISON",
        "status": "COMPLETE" if not missing else "INCOMPLETE",
        "fragments_scored": len(gold_rows),
        "responses_available": len(validated),
        "fragments_without_response": missing,
        "micro_precision": micro["precision"],
        "micro_recall": micro["recall"],
        "micro_f1": micro["f1"],
        "macro_precision": macro_views["macro_all_13"]["precision"],
        "macro_recall": macro_views["macro_all_13"]["recall"],
        "macro_f1": macro_views["macro_all_13"]["f1"],
        "macro_all_13": macro_views["macro_all_13"],
        "macro_gold_supported_labels": macro_views["macro_gold_supported_labels"],
        "gold_supported_label_ids": macro_views["gold_supported_label_ids"],
        "zero_gold_support_label_ids": macro_views["zero_gold_support_label_ids"],
        "exact_set_match": exact_set_match(gold_sets, predicted_sets),
        "coverage": coverage_rate(predicted_sets),
        "abstention_rate": abstention_rate(predicted_sets),
        "average_predicted_labels": average_predicted_labels(predicted_sets),
        "candidate_space": "all_framework_competencies",
        "constrained_outputs_overwritten": False,
        "comparison_note": (
            "Scored against the same human-reviewed fragment reference, with "
            "the same metric functions, as the constrained run. The only "
            "intended difference between the conditions is the candidate space."
        ),
        "abstention_note": (
            "Abstention quality remains untestable: the reference set contains "
            "no NONE fragments in either condition."
        ),
        "source_files": {
            "unconstrained_gemini_validated.jsonl": file_sha256(VALIDATED_IN),
            "manual_fragment_annotations.csv": file_sha256(GOLD),
        },
    }

    write_json(metrics, METRICS_OUT)

    per_label_rows = [
        {
            "competency_id": competency_id,
            "gold_count": counts.get("gold_count", 0),
            "predicted_count": counts.get("predicted_count", 0),
            "true_positives": counts.get("true_positives", 0),
            "false_positives": counts.get("false_positives", 0),
            "false_negatives": counts.get("false_negatives", 0),
        }
        for competency_id, counts in sorted(label_counts.items())
    ]
    write_csv(per_label_rows, PER_LABEL_OUT, PER_LABEL_COLUMNS)

    # Three-system comparison, factual only. No winner text.
    bm25 = load_json(BM25_METRICS) or {}
    constrained = load_json(CONSTRAINED_METRICS) or {}
    bm25_top1 = bm25.get("top1_micro") or {}

    def fmt(value) -> str:
        return "" if value is None else f"{float(value):.10f}"

    comparison_rows = []

    for name, bm25_value, constrained_value, unconstrained_value in (
        (
            "micro_precision",
            bm25_top1.get("precision"),
            constrained.get("micro_precision"),
            micro["precision"],
        ),
        (
            "micro_recall",
            bm25_top1.get("recall"),
            constrained.get("micro_recall"),
            micro["recall"],
        ),
        (
            "micro_f1",
            bm25_top1.get("f1"),
            constrained.get("micro_f1"),
            micro["f1"],
        ),
        (
            "exact_set_match",
            None,
            constrained.get("exact_set_match"),
            metrics["exact_set_match"],
        ),
        (
            "average_predicted_labels",
            None,
            constrained.get("average_predicted_labels"),
            metrics["average_predicted_labels"],
        ),
    ):
        delta = (
            ""
            if constrained_value is None
            else f"{float(unconstrained_value) - float(constrained_value):.10f}"
        )

        comparison_rows.append(
            {
                "metric": name,
                "BM25_Top1": fmt(bm25_value),
                "BM25_Top5_constrained_Gemini": fmt(constrained_value),
                "All13_unconstrained_Gemini": fmt(unconstrained_value),
                "delta_unconstrained_minus_constrained": delta,
            }
        )

    write_csv(comparison_rows, COMPARISON_OUT, COMPARISON_COLUMNS)

    after = snapshot_protected()
    mutated = [path for path in before if before[path] != after[path]]

    if mutated:
        print("Protected files changed. This is a bug:", file=sys.stderr)

        for path in mutated:
            print(f"  {path}", file=sys.stderr)

        return 8

    if args.quiet:
        return 0

    print(f"Wrote {METRICS_OUT}")
    print(f"Wrote {PER_LABEL_OUT}")
    print(f"Wrote {COMPARISON_OUT}")
    print()
    print(f"Status: {metrics['status']}")

    if missing:
        print(f"  fragments without a response: {len(missing)}")

    print(
        "Unconstrained micro P/R/F1 = "
        f"{micro['precision']:.10f} / {micro['recall']:.10f} / {micro['f1']:.10f}"
    )
    print(
        f"exact-set = {metrics['exact_set_match']:.10f}; "
        f"avg labels = {metrics['average_predicted_labels']:.10f}"
    )
    print()
    print("Constrained metric files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
