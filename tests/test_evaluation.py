"""Tests for evaluation readiness gates using temporary gold only."""

from __future__ import annotations

import pytest

from moodle_competency.evaluation import (
    GeminiIncompleteError,
    HumanGateClosedError,
    gold_sets_from_rows,
    predicted_sets_from_gemini,
    ranked_candidates_from_bm25,
    require_complete_gemini,
    require_complete_gold,
)


def test_incomplete_gold_is_rejected() -> None:
    rows = [
        {
            "fragment_id": "page:1#f001",
            "gold_competency_ids": "",
            "no_competency": "",
            "ambiguous": "",
            "annotator": "",
            "annotation_date": "",
        }
    ]

    with pytest.raises(HumanGateClosedError):
        require_complete_gold(rows)


def test_complete_gold_and_prediction_alignment() -> None:
    rows = [
        {
            "fragment_id": "page:1#f001",
            "gold_competency_ids": "GI_C1_1;GI_C1_2",
            "no_competency": "false",
            "ambiguous": "false",
            "annotator": "Wail Ouaret",
            "annotation_date": "2026-09-18",
        }
    ]
    require_complete_gold(rows)
    gold = gold_sets_from_rows(rows)
    predicted = predicted_sets_from_gemini(
        rows,
        [
            {
                "fragment_id": "page:1#f001",
                "valid": True,
                "abstain": False,
                "selected": [{"idnumber": "GI_C1_1"}],
            }
        ],
    )
    ranked = ranked_candidates_from_bm25(
        rows,
        [
            {
                "fragment_id": "page:1#f001",
                "candidates": [
                    {"rank": 2, "idnumber": "GI_C1_2"},
                    {"rank": 1, "idnumber": "GI_C1_1"},
                ],
            }
        ],
    )

    assert gold == [["GI_C1_1", "GI_C1_2"]]
    assert predicted == [["GI_C1_1"]]
    assert ranked == [["GI_C1_1", "GI_C1_2"]]


def test_per_label_and_model_comparison_tables() -> None:
    from moodle_competency.evaluation import (
        model_comparison_rows,
        per_label_table_rows,
    )

    gold = [["GI_C1_1"], ["GI_C1_2"]]
    predicted = [["GI_C1_1"], []]
    rows = per_label_table_rows(
        gold,
        predicted,
        ["GI_C1_1", "GI_C1_2"],
    )

    assert rows[0]["true_positives"] == "1"
    assert rows[1]["false_negatives"] == "1"

    comparison = model_comparison_rows(
        {
            "status": "COMPLETE",
            "top1_micro": {
                "precision": 0.5,
                "recall": 0.25,
                "f1": 1 / 3,
            },
        },
        {
            "status": "COMPLETE",
            "micro_precision": 1.0,
            "micro_recall": 0.5,
            "micro_f1": 2 / 3,
        },
    )

    assert comparison[0]["system"] == "BM25 Top-1"
    assert comparison[1]["system"] == "BM25 Top-5 + constrained Gemini"
    assert comparison[0]["status"] == "COMPLETE"


def test_system_delta_rows_are_factual() -> None:
    from moodle_competency.evaluation import system_delta_rows

    rows = system_delta_rows(
        {
            "top1_micro": {
                "precision": 0.7428571429,
                "recall": 0.6842105263,
                "f1": 0.7123287671,
            }
        },
        {
            "micro_precision": 0.7254901961,
            "micro_recall": 0.9736842105,
            "micro_f1": 0.8314606742,
        },
    )

    by_metric = {row["metric"]: row for row in rows}
    assert list(by_metric) == [
        "micro_precision",
        "micro_recall",
        "micro_f1",
    ]
    precision_delta = float(by_metric["micro_precision"]["absolute_delta"])
    recall_delta = float(by_metric["micro_recall"]["absolute_delta"])
    assert precision_delta < 0
    assert recall_delta > 0
    assert "winner" not in str(rows).lower()


def test_incomplete_gemini_is_rejected() -> None:
    fragments = [
        {"fragment_id": "page:1#f001"},
        {"fragment_id": "page:1#f002"},
    ]
    predictions = [
        {
            "fragment_id": "page:1#f001",
            "valid": True,
            "selected": [],
            "abstain": True,
        }
    ]

    with pytest.raises(GeminiIncompleteError):
        require_complete_gemini(
            fragments=fragments,
            predictions=predictions,
        )
