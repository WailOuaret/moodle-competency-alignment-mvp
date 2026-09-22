"""Tests for evidence-review preparation and summary gates."""

from __future__ import annotations

from pathlib import Path

from moodle_competency.evidence_review import (
    build_evidence_review_rows,
    pedagogical_ratings_complete,
    summarize_evidence_review,
    write_evidence_review,
)


def test_mechanical_validity_and_blank_ratings() -> None:
    rows = build_evidence_review_rows(
        predictions=[
            {
                "fragment_id": "page:1#f001",
                "valid": True,
                "selected": [
                    {
                        "idnumber": "GI_C1_1",
                        "evidence": [
                            "Design software.",
                            "not in fragment",
                        ],
                    }
                ],
            }
        ],
        fragments=[
            {
                "fragment_id": "page:1#f001",
                "resource_id": "page:1",
                "text": "Design software. Deploy it.",
            }
        ],
        competencies=[
            {"idnumber": "GI_C1_1", "shortname": "Dev"}
        ],
    )

    assert len(rows) == 2
    assert rows[0]["mechanically_valid"] == "true"
    assert rows[1]["mechanically_valid"] == "false"
    assert rows[0]["pedagogical_rating"] == ""
    assert pedagogical_ratings_complete(rows) is False

    summary = summarize_evidence_review(rows)

    assert summary["status"] == "WAITING_FOR_HUMAN"
    assert summary["pedagogical_clear_rate"] is None
    assert summary["mechanical_validity_rate"] == 0.5


def test_complete_pedagogical_summary(tmp_path: Path) -> None:
    rows = [
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "competency_id": "GI_C1_1",
            "competency_shortname": "Dev",
            "fragment_text": "Design software.",
            "evidence_quote": "Design software.",
            "mechanically_valid": "true",
            "pedagogical_rating": "2",
            "reviewer": "Wail Ouaret",
            "comment": "",
        },
        {
            "fragment_id": "page:1#f002",
            "resource_id": "page:1",
            "competency_id": "GI_C1_2",
            "competency_shortname": "Quality",
            "fragment_text": "Testing.",
            "evidence_quote": "Testing.",
            "mechanically_valid": "true",
            "pedagogical_rating": "0",
            "reviewer": "Wail Ouaret",
            "comment": "",
        },
    ]
    path = tmp_path / "evidence_review.csv"
    write_evidence_review(rows, path)
    summary = summarize_evidence_review(rows)

    assert summary["status"] == "COMPLETE"
    assert summary["pedagogical_clear_rate"] == 0.5
    assert summary["pedagogical_unsupported_rate"] == 0.5
    assert path.exists()
