"""Fixture tests for teacher-review storage. No invented decisions."""

from __future__ import annotations

from pathlib import Path

from moodle_competency.teacher_reviews import (
    decision_status,
    empty_review_row,
    write_teacher_reviews,
)


def test_blank_row_is_pending(tmp_path: Path) -> None:
    row = empty_review_row(
        resource_id="page:1",
        competency_id="GI_C1_1",
        fragment_ids=["page:1#f001"],
    )
    path = tmp_path / "teacher_reviews.csv"
    write_teacher_reviews([row], path)

    assert row["decision"] == ""
    assert decision_status([row], "page:1", "GI_C1_1") == "pending"
    assert path.exists()


def test_stored_accept_is_not_invented() -> None:
    reviews = [
        {
            "resource_id": "page:1",
            "competency_id": "GI_C1_1",
            "decision": "accept",
        }
    ]

    assert decision_status(reviews, "page:1", "GI_C1_1") == "accept"
    assert decision_status(reviews, "page:2", "GI_C1_1") == "pending"
