"""Hand-calculated tests for the reusable metrics library."""

from __future__ import annotations

from moodle_competency.metrics import (
    abstention_rate,
    average_predicted_labels,
    coverage_rate,
    exact_set_match,
    gold_supported_labels,
    hit_at_k,
    instance_prf,
    macro_prf,
    macro_prf_views,
    mean_reciprocal_rank,
    micro_prf,
    per_label_prf,
    recall_at_k,
)


LABELS = ["A", "B", "C"]


def test_perfect_prediction() -> None:
    scores = instance_prf(["A", "B"], ["B", "A"])

    assert scores == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_no_prediction_on_gold() -> None:
    scores = instance_prf(["A"], [])

    assert scores["precision"] == 0.0
    assert scores["recall"] == 0.0
    assert scores["f1"] == 0.0


def test_correct_abstention_no_competency() -> None:
    scores = instance_prf([], [])

    assert scores == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_overprediction() -> None:
    scores = instance_prf(["A"], ["A", "B"])

    assert scores["precision"] == 0.5
    assert scores["recall"] == 1.0
    assert scores["f1"] == 2 / 3


def test_underprediction() -> None:
    scores = instance_prf(["A", "B"], ["A"])

    assert scores["precision"] == 1.0
    assert scores["recall"] == 0.5
    assert scores["f1"] == 2 / 3


def test_exact_set_match() -> None:
    gold = [["A"], ["A", "B"], []]
    predicted = [["A"], ["A"], []]

    assert exact_set_match(gold, predicted) == 2 / 3


def test_coverage_and_abstention() -> None:
    predicted = [["A"], [], ["B", "C"]]

    assert coverage_rate(predicted) == 2 / 3
    assert abstention_rate(predicted) == 1 / 3
    assert average_predicted_labels(predicted) == 1.0


def test_micro_vs_macro() -> None:
    gold = [["A", "B"], ["C"]]
    predicted = [["A"], ["A"]]
    micro = micro_prf(gold, predicted)
    macro = macro_prf(gold, predicted, LABELS)

    # tp=1 (A), fp=1 (second A), fn=2 (B and C)
    assert micro["true_positives"] == 1
    assert micro["false_positives"] == 1
    assert micro["false_negatives"] == 2
    assert micro["precision"] == 0.5
    assert micro["recall"] == 1 / 3
    assert macro["precision"] != micro["precision"]


def test_recall_hit_mrr() -> None:
    gold = [["B", "C"], ["A"], []]
    ranked = [
        ["A", "B", "X", "Y", "Z"],
        ["X", "Y", "A", "B", "C"],
        ["A", "B", "C", "D", "E"],
    ]

    # Gold labels: B,C from first (B in top1? no; B in top3 yes; C no until later)
    # First instance gold {B,C}: Top-1 {A} -> 0/2; Top-3 {A,B,X} -> B only = 1/2
    # Second gold {A}: Top-1 {X} -> 0; Top-3 {X,Y,A} -> 1
    # Empty gold excluded.
    assert recall_at_k(gold, ranked, 1) == 0.0
    assert recall_at_k(gold, ranked, 3) == (1 + 1) / 3
    assert hit_at_k(gold, ranked, 1) == 0.0
    assert hit_at_k(gold, ranked, 3) == 1.0
    # MRR: first instance first gold at rank 2 (B) -> 0.5; second A at rank 3 -> 1/3
    assert mean_reciprocal_rank(gold, ranked) == (0.5 + (1 / 3)) / 2


def test_zero_denominator_empty_collections() -> None:
    assert recall_at_k([], [], 5) == 0.0
    assert hit_at_k([[]], [[]], 5) == 0.0
    assert mean_reciprocal_rank([[]], [[]]) == 0.0
    assert micro_prf([[]], [[]])["f1"] == 1.0


def test_macro_views_zero_support_and_absent_labels() -> None:
    """Hand-calculated fixture covering four label kinds.

    Labels:
    - A: gold-supported, predicted correctly
    - B: gold-supported, predicted correctly
    - PARENT: predicted but absent from gold (zero reference support)
    - ABSENT: never in gold and never predicted
    """

    labels = ["PARENT", "A", "B", "ABSENT"]
    gold = [["A"], ["B"], ["A"]]
    predicted = [["A", "PARENT"], ["B"], ["A"]]

    rows = {row["competency_id"]: row for row in per_label_prf(gold, predicted, labels)}

    assert rows["A"]["support"] == 2
    assert rows["A"]["predicted_count"] == 2
    assert rows["A"]["true_positives"] == 2
    assert rows["A"]["false_positives"] == 0
    assert rows["A"]["false_negatives"] == 0
    assert rows["A"]["precision"] == 1.0
    assert rows["A"]["recall"] == 1.0
    assert rows["A"]["f1"] == 1.0
    assert rows["A"]["gold_supported"] is True

    assert rows["B"]["support"] == 1
    assert rows["B"]["true_positives"] == 1
    assert rows["B"]["precision"] == 1.0

    assert rows["PARENT"]["support"] == 0
    assert rows["PARENT"]["predicted_count"] == 1
    assert rows["PARENT"]["true_positives"] == 0
    assert rows["PARENT"]["false_positives"] == 1
    assert rows["PARENT"]["false_negatives"] == 0
    assert rows["PARENT"]["precision"] == 0.0
    assert rows["PARENT"]["recall"] == 0.0
    assert rows["PARENT"]["f1"] == 0.0
    assert rows["PARENT"]["gold_supported"] is False

    assert rows["ABSENT"]["support"] == 0
    assert rows["ABSENT"]["predicted_count"] == 0
    assert rows["ABSENT"]["true_positives"] == 0
    assert rows["ABSENT"]["false_positives"] == 0
    assert rows["ABSENT"]["false_negatives"] == 0
    assert rows["ABSENT"]["precision"] == 0.0
    assert rows["ABSENT"]["gold_supported"] is False

    assert gold_supported_labels(gold, labels) == ["A", "B"]

    views = macro_prf_views(gold, predicted, labels)
    # Unweighted mean over PARENT, A, B, ABSENT.
    assert views["macro_all_13"]["precision"] == 0.5
    assert views["macro_all_13"]["recall"] == 0.5
    assert views["macro_all_13"]["f1"] == 0.5
    assert views["macro_gold_supported_labels"]["precision"] == 1.0
    assert views["macro_gold_supported_labels"]["recall"] == 1.0
    assert views["macro_gold_supported_labels"]["f1"] == 1.0
    assert views["gold_supported_label_count"] == 2
    assert views["zero_gold_support_label_ids"] == ["PARENT", "ABSENT"]
    # Existing full-universe macro is unchanged.
    assert views["macro_all_13"] == macro_prf(gold, predicted, labels)
