"""Readiness checks for evaluation scripts. Never fabricates results."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import (
    parse_boolean,
    parse_competency_ids,
    stripped_text,
)
from moodle_competency.annotation_session import is_row_complete
from moodle_competency.aggregation import completeness_report, valid_predictions
from moodle_competency.metrics import f1_score, per_label_counts


PER_LABEL_TABLE_COLUMNS = (
    "competency_id",
    "gold_count",
    "predicted_count",
    "true_positives",
    "false_positives",
    "false_negatives",
    "precision",
    "recall",
    "f1",
)

MODEL_COMPARISON_COLUMNS = (
    "system",
    "micro_precision",
    "micro_recall",
    "micro_f1",
    "status",
)

SYSTEM_DELTA_COLUMNS = (
    "metric",
    "BM25_Top1",
    "BM25_Top5_Gemini",
    "absolute_delta",
)


class HumanGateClosedError(RuntimeError):
    """Raised when fragment gold is incomplete."""


class GeminiIncompleteError(RuntimeError):
    """Raised when constrained Gemini coverage is incomplete."""


def gold_sets_from_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[list[str]]:
    """Extract gold competency ID lists in row order."""

    gold_sets: list[list[str]] = []

    for row in rows:
        ids, errors = parse_competency_ids(
            row.get("gold_competency_ids")
        )

        if errors:
            gold_sets.append([])
            continue

        gold_sets.append(ids)

    return gold_sets


def require_complete_gold(
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Refuse evaluation when Human Gate 1 is closed."""

    incomplete = [
        stripped_text(row.get("fragment_id"))
        for row in rows
        if not is_row_complete(row)
    ]

    if incomplete:
        raise HumanGateClosedError(
            "Human Gate 1 is not open: manual gold "
            "annotations are incomplete. "
            f"Incomplete fragments: {len(incomplete)}."
        )


def require_complete_gemini(
    *,
    fragments: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
) -> None:
    coverage = completeness_report(
        fragments=fragments,
        predictions=predictions,
    )

    if not coverage["complete"]:
        missing = ", ".join(coverage["missing_fragment_ids"])
        raise GeminiIncompleteError(
            "Constrained Gemini is incomplete "
            f"({coverage['available_predicted_fragments']}/"
            f"{coverage['expected_fragments']}). "
            f"Missing: {missing}"
        )


def predicted_sets_from_gemini(
    rows: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
) -> list[list[str]]:
    """Align Gemini selected IDs to annotation/fragment row order."""

    by_fragment = {
        stripped_text(record.get("fragment_id")): record
        for record in valid_predictions(predictions)
    }
    predicted_sets: list[list[str]] = []

    for row in rows:
        fragment_id = stripped_text(row.get("fragment_id"))
        record = by_fragment.get(fragment_id)

        if record is None or record.get("abstain") is True:
            predicted_sets.append([])
            continue

        selected = [
            stripped_text(item.get("idnumber"))
            for item in record.get("selected") or []
            if stripped_text(item.get("idnumber"))
        ]
        predicted_sets.append(selected)

    return predicted_sets


def ranked_candidates_from_bm25(
    rows: Sequence[Mapping[str, Any]],
    candidate_sets: Sequence[Mapping[str, Any]],
) -> list[list[str]]:
    by_fragment = {
        stripped_text(record.get("fragment_id")): record
        for record in candidate_sets
    }
    ranked: list[list[str]] = []

    for row in rows:
        record = by_fragment.get(
            stripped_text(row.get("fragment_id"))
        )

        if record is None:
            ranked.append([])
            continue

        candidates = sorted(
            record.get("candidates") or [],
            key=lambda item: int(item.get("rank") or 10**6),
        )
        ranked.append(
            [
                stripped_text(item.get("idnumber"))
                for item in candidates
                if stripped_text(item.get("idnumber"))
            ]
        )

    return ranked


def no_competency_flags(
    rows: Sequence[Mapping[str, Any]],
) -> list[bool]:
    flags: list[bool] = []

    for row in rows:
        value, _errors = parse_boolean(
            row.get("no_competency"),
            "no_competency",
        )
        flags.append(value is True)

    return flags


def per_label_table_rows(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
    label_set: Sequence[str],
) -> list[dict[str, str]]:
    """Build a per-competency P/R/F1 table. Empty until evaluation runs."""

    counts = per_label_counts(gold_sets, predicted_sets, label_set)
    rows: list[dict[str, str]] = []

    for label in label_set:
        item = counts.get(
            label,
            {
                "tp": 0,
                "fp": 0,
                "fn": 0,
                "gold": 0,
                "predicted": 0,
            },
        )
        tp = int(item["tp"])
        fp = int(item["fp"])
        fn = int(item["fn"])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        rows.append(
            {
                "competency_id": label,
                "gold_count": str(item["gold"]),
                "predicted_count": str(item["predicted"]),
                "true_positives": str(tp),
                "false_positives": str(fp),
                "false_negatives": str(fn),
                "precision": f"{precision:.4f}",
                "recall": f"{recall:.4f}",
                "f1": f"{f1_score(precision, recall):.4f}",
            }
        )

    return rows


def model_comparison_rows(
    bm25_metrics: Mapping[str, Any],
    llm_metrics: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Compare BM25 Top-1 with BM25 Top-5 + constrained Gemini."""

    bm25_top1 = bm25_metrics.get("top1_micro") or {}
    return [
        {
            "system": "BM25 Top-1",
            "micro_precision": f"{float(bm25_top1.get('precision', 0.0)):.4f}",
            "micro_recall": f"{float(bm25_top1.get('recall', 0.0)):.4f}",
            "micro_f1": f"{float(bm25_top1.get('f1', 0.0)):.4f}",
            "status": str(bm25_metrics.get("status", "")),
        },
        {
            "system": "BM25 Top-5 + constrained Gemini",
            "micro_precision": f"{float(llm_metrics.get('micro_precision', 0.0)):.4f}",
            "micro_recall": f"{float(llm_metrics.get('micro_recall', 0.0)):.4f}",
            "micro_f1": f"{float(llm_metrics.get('micro_f1', 0.0)):.4f}",
            "status": str(llm_metrics.get("status", "")),
        },
    ]


def system_delta_rows(
    bm25_metrics: Mapping[str, Any],
    llm_metrics: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Factual BM25 Top-1 vs constrained Gemini deltas. No winner text."""

    bm25_top1 = bm25_metrics.get("top1_micro") or {}
    pairs = (
        (
            "micro_precision",
            float(bm25_top1.get("precision", 0.0)),
            float(llm_metrics.get("micro_precision", 0.0)),
        ),
        (
            "micro_recall",
            float(bm25_top1.get("recall", 0.0)),
            float(llm_metrics.get("micro_recall", 0.0)),
        ),
        (
            "micro_f1",
            float(bm25_top1.get("f1", 0.0)),
            float(llm_metrics.get("micro_f1", 0.0)),
        ),
    )
    rows: list[dict[str, str]] = []

    for name, bm25_value, gemini_value in pairs:
        rows.append(
            {
                "metric": name,
                "BM25_Top1": f"{bm25_value:.10f}",
                "BM25_Top5_Gemini": f"{gemini_value:.10f}",
                "absolute_delta": f"{gemini_value - bm25_value:.10f}",
            }
        )

    return rows
