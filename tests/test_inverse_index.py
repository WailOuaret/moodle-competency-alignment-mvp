"""Tests for competency -> resource inverse index."""

from __future__ import annotations

from moodle_competency.inverse_index import build_competency_resource_index


def competencies() -> list[dict]:
    return [
        {
            "idnumber": "GI_C1_1",
            "shortname": "Dev",
            "description_text": "Software development",
            "parent_idnumber": "GI_C1",
            "depth": 1,
        },
        {
            "idnumber": "GI_C1_2",
            "shortname": "Quality",
            "description_text": "Software quality",
            "parent_idnumber": "GI_C1",
            "depth": 1,
        },
        {
            "idnumber": "GI_C3_3",
            "shortname": "ML",
            "description_text": "Machine learning",
            "parent_idnumber": "GI_C3",
            "depth": 1,
        },
    ]


def predictions() -> list[dict]:
    return [
        {
            "resource_id": "page:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "page",
            "title": "Software Page",
            "predicted_competencies": [
                {
                    "competency_id": "GI_C1_1",
                    "fragment_ids": ["page:1#f001", "page:1#f002"],
                    "evidence": ["Design software."],
                    "max_confidence": 0.9,
                    "mean_confidence": 0.7,
                    "support_count": 2,
                }
            ],
        },
        {
            "resource_id": "quiz_question:1:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "quiz_question",
            "title": "Q1",
            "predicted_competencies": [
                {
                    "competency_id": "GI_C1_1",
                    "fragment_ids": ["quiz_question:1:1#f001"],
                    "evidence": ["requirement"],
                    "max_confidence": 0.8,
                    "mean_confidence": 0.8,
                    "support_count": 1,
                }
            ],
        },
    ]


def test_zero_and_multiple_resources() -> None:
    index = build_competency_resource_index(
        competencies=competencies(),
        resource_predictions=predictions(),
        upstream_completeness="partial",
    )
    by_id = {item["competency_id"]: item for item in index}

    assert set(by_id) == {"GI_C1_1", "GI_C1_2", "GI_C3_3"}
    assert by_id["GI_C3_3"]["match_count"] == 0
    assert by_id["GI_C3_3"]["resources"] == []
    assert by_id["GI_C1_1"]["match_count"] == 2
    assert by_id["GI_C1_1"]["resources"][0]["resource_id"] == "page:1"
    assert by_id["GI_C1_1"]["resources"][0]["fragment_ids"] == [
        "page:1#f001",
        "page:1#f002",
    ]
    assert by_id["GI_C1_1"]["resources"][0]["teacher_decision_status"] == (
        "pending"
    )
    assert by_id["GI_C1_1"]["upstream_completeness"] == "partial"


def test_all_thirteen_competencies_represented() -> None:
    thirteen = [
        {"idnumber": f"GI_C{index}", "shortname": str(index), "depth": 0}
        for index in range(1, 14)
    ]
    index = build_competency_resource_index(
        competencies=thirteen,
        resource_predictions=[],
        upstream_completeness="complete",
    )

    assert len(index) == 13
    assert all(item["match_count"] == 0 for item in index)
