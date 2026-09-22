"""Tests for fragment-to-resource aggregation."""

from __future__ import annotations

import pytest

from moodle_competency.aggregation import (
    IncompletePredictionsError,
    aggregate_fragment_predictions,
    completeness_report,
)


def resources() -> list[dict]:
    return [
        {
            "resource_id": "page:1",
            "resource_type": "page",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "title": "Software Page",
            "activity_name": "Software Page",
        },
        {
            "resource_id": "quiz_question:1:1",
            "resource_type": "quiz_question",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "title": "Q1",
            "activity_name": "Quiz",
        },
    ]


def fragments() -> list[dict]:
    return [
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "text": "Design software systems.",
        },
        {
            "fragment_id": "page:1#f002",
            "resource_id": "page:1",
            "text": "Test software quality.",
        },
        {
            "fragment_id": "quiz_question:1:1#f001",
            "resource_id": "quiz_question:1:1",
            "text": "What is a requirement?",
        },
    ]


def competencies() -> list[dict]:
    return [
        {"idnumber": "GI_C1_1", "shortname": "Dev"},
        {"idnumber": "GI_C1_2", "shortname": "Quality"},
    ]


def prediction(
    fragment_id: str,
    selected: list[dict],
    abstain: bool = False,
) -> dict:
    return {
        "fragment_id": fragment_id,
        "valid": True,
        "abstain": abstain,
        "selected": selected,
    }


def test_single_fragment_quiz_stays_independent() -> None:
    preds = [
        prediction(
            "page:1#f001",
            [
                {
                    "idnumber": "GI_C1_1",
                    "evidence": ["Design software systems."],
                    "confidence": 0.9,
                }
            ],
        ),
        prediction("page:1#f002", []),
        prediction(
            "quiz_question:1:1#f001",
            [
                {
                    "idnumber": "GI_C1_2",
                    "evidence": ["requirement"],
                    "confidence": 0.8,
                }
            ],
        ),
    ]
    preds[1]["abstain"] = True
    records, manifest = aggregate_fragment_predictions(
        fragments=fragments(),
        resources=resources(),
        competencies=competencies(),
        predictions=preds,
        allow_partial=False,
    )
    quiz = next(
        item
        for item in records
        if item["resource_id"] == "quiz_question:1:1"
    )

    assert manifest["final"] is True
    assert quiz["resource_type"] == "quiz_question"
    assert quiz["predicted_competencies"][0]["competency_id"] == "GI_C1_2"


def test_multi_fragment_page_merges_same_competency() -> None:
    preds = [
        prediction(
            "page:1#f001",
            [
                {
                    "idnumber": "GI_C1_1",
                    "evidence": ["Design software systems."],
                    "confidence": 0.5,
                }
            ],
        ),
        prediction(
            "page:1#f002",
            [
                {
                    "idnumber": "GI_C1_1",
                    "evidence": ["Test software quality."],
                    "confidence": 0.9,
                },
                {
                    "idnumber": "GI_C1_2",
                    "evidence": ["Test software quality."],
                    "confidence": 0.7,
                },
            ],
        ),
        prediction("quiz_question:1:1#f001", []),
    ]
    preds[2]["abstain"] = True
    records, _manifest = aggregate_fragment_predictions(
        fragments=fragments(),
        resources=resources(),
        competencies=competencies(),
        predictions=preds,
    )
    page = next(
        item for item in records if item["resource_id"] == "page:1"
    )
    by_id = {
        item["competency_id"]: item
        for item in page["predicted_competencies"]
    }

    assert by_id["GI_C1_1"]["support_count"] == 2
    assert by_id["GI_C1_1"]["max_confidence"] == 0.9
    assert by_id["GI_C1_1"]["mean_confidence"] == 0.7
    assert "Design software systems." in by_id["GI_C1_1"]["evidence"]
    assert "GI_C1_2" in by_id
    assert page["predicted_competencies"][0]["competency_id"] == "GI_C1_1"


def test_missing_prediction_is_partial() -> None:
    preds = [
        prediction(
            "page:1#f001",
            [
                {
                    "idnumber": "GI_C1_1",
                    "evidence": ["Design software systems."],
                    "confidence": 1.0,
                }
            ],
        )
    ]
    coverage = completeness_report(
        fragments=fragments(),
        predictions=preds,
    )

    assert coverage["complete"] is False
    assert "page:1#f002" in coverage["missing_fragment_ids"]

    with pytest.raises(IncompletePredictionsError):
        aggregate_fragment_predictions(
            fragments=fragments(),
            resources=resources(),
            competencies=competencies(),
            predictions=preds,
            allow_partial=False,
        )

    records, manifest = aggregate_fragment_predictions(
        fragments=fragments(),
        resources=resources(),
        competencies=competencies(),
        predictions=preds,
        allow_partial=True,
    )

    assert manifest["final"] is False
    assert manifest["prediction_completeness"] == "partial"
    assert len(records) == 2


def test_unknown_resource_is_reported() -> None:
    broken = fragments()
    broken[0]["resource_id"] = "page:999"
    preds = [
        prediction(item["fragment_id"], [])
        for item in broken
    ]
    for item in preds:
        item["abstain"] = True

    _records, manifest = aggregate_fragment_predictions(
        fragments=broken,
        resources=resources(),
        competencies=competencies(),
        predictions=preds,
        allow_partial=True,
    )

    assert any("Unknown resource" in error for error in manifest["errors"])


def test_unknown_predicted_fragment() -> None:
    preds = [
        prediction("page:1#f001", []),
        prediction("page:1#f002", []),
        prediction("quiz_question:1:1#f001", []),
        prediction("ghost#f001", []),
    ]
    for item in preds:
        item["abstain"] = True

    _records, manifest = aggregate_fragment_predictions(
        fragments=fragments(),
        resources=resources(),
        competencies=competencies(),
        predictions=preds,
        allow_partial=True,
    )

    assert "ghost#f001" in manifest["unknown_fragment_ids"]
