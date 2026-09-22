"""Evaluate BM25 retrieval against completed human gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.annotation import load_jsonl, read_csv, write_csv, write_json
from moodle_competency.evaluation import (
    HumanGateClosedError,
    PER_LABEL_TABLE_COLUMNS,
    gold_sets_from_rows,
    per_label_table_rows,
    ranked_candidates_from_bm25,
    require_complete_gold,
)
from moodle_competency.metrics import (
    hit_at_k,
    instance_prf,
    macro_prf,
    mean_reciprocal_rank,
    micro_prf,
    recall_at_k,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
CANDIDATES = PROJECT_ROOT / "data" / "interim" / "bm25_candidates.jsonl"
METRICS_PATH = PROJECT_ROOT / "reports" / "metrics" / "bm25_metrics.json"
PER_FRAGMENT = PROJECT_ROOT / "reports" / "tables" / "bm25_per_fragment.csv"
PER_LABEL = PROJECT_ROOT / "reports" / "tables" / "bm25_per_competency.csv"
COMPETENCIES = PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute BM25 Recall@K and Top-1 P/R/F1 after Human Gate 1."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check gold completeness and schemas without writing metrics.",
    )
    return parser.parse_args()


def compute_bm25_metrics(
    rows: list[dict],
    candidate_sets: list[dict],
    label_set: list[str],
) -> dict:
    gold_sets = gold_sets_from_rows(rows)
    ranked = ranked_candidates_from_bm25(rows, candidate_sets)
    top1 = [names[:1] for names in ranked]
    return {
        "status": "COMPLETE",
        "recall_at_1": recall_at_k(gold_sets, ranked, 1),
        "recall_at_3": recall_at_k(gold_sets, ranked, 3),
        "recall_at_5": recall_at_k(gold_sets, ranked, 5),
        "hit_at_1": hit_at_k(gold_sets, ranked, 1),
        "hit_at_3": hit_at_k(gold_sets, ranked, 3),
        "hit_at_5": hit_at_k(gold_sets, ranked, 5),
        "mrr": mean_reciprocal_rank(gold_sets, ranked),
        "top1_micro": micro_prf(gold_sets, top1),
        "top1_macro": macro_prf(gold_sets, top1, label_set),
        "notes": {
            "no_competency_fragments": (
                "Excluded from Recall@K / Hit@K / MRR denominators."
            ),
            "multi_label": (
                "Recall@K is label-level: gold labels found in Top-K "
                "divided by all gold labels."
            ),
            "parent_child": (
                "Parent and child IDs are distinct labels; a parent "
                "does not automatically satisfy a child."
            ),
        },
    }


def main() -> int:
    arguments = parse_arguments()

    try:
        rows = read_csv(GOLD)
        candidates = load_jsonl(CANDIDATES)
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

    print("=== BM25 EVALUATION ===")
    print(f"Gold rows: {len(rows)}")
    print("Human Gate 1: OPEN")

    if arguments.dry_run:
        print("Dry-run: schemas OK. No metrics written.")
        return 0

    label_set = [
        str(item.get("idnumber", "")).strip()
        for item in competencies
        if str(item.get("idnumber", "")).strip()
    ]
    metrics = compute_bm25_metrics(rows, candidates, label_set)
    gold_sets = gold_sets_from_rows(rows)
    ranked = ranked_candidates_from_bm25(rows, candidates)
    write_json(metrics, METRICS_PATH)

    fragment_rows = []

    for row, gold, names in zip(rows, gold_sets, ranked, strict=True):
        top1 = names[:1]
        scores = instance_prf(gold, top1)
        fragment_rows.append(
            {
                "fragment_id": row.get("fragment_id", ""),
                "gold_competency_ids": ";".join(gold),
                "bm25_top1": ";".join(top1),
                "recall_at_5_labels_hit": str(
                    sum(1 for item in gold if item in set(names[:5]))
                ),
                "top1_precision": f"{scores['precision']:.4f}",
                "top1_recall": f"{scores['recall']:.4f}",
                "top1_f1": f"{scores['f1']:.4f}",
            }
        )

    write_csv(
        fragment_rows,
        PER_FRAGMENT,
        [
            "fragment_id",
            "gold_competency_ids",
            "bm25_top1",
            "recall_at_5_labels_hit",
            "top1_precision",
            "top1_recall",
            "top1_f1",
        ],
    )
    top1 = [names[:1] for names in ranked]
    write_csv(
        per_label_table_rows(gold_sets, top1, label_set),
        PER_LABEL,
        PER_LABEL_TABLE_COLUMNS,
    )
    print(f"Wrote {METRICS_PATH}")
    print(json.dumps({k: metrics[k] for k in ("recall_at_1", "recall_at_5")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
