"""Human-validation summary tests. No invented teacher-study results."""

from __future__ import annotations

from pathlib import Path

from moodle_competency.human_validation_summary import (
    WAITING_MESSAGE,
    summarize_human_validation,
    write_empty_validation_form,
    write_human_validation_outputs,
)


def test_zero_reviews_waiting(tmp_path: Path) -> None:
    summary = summarize_human_validation([])
    assert summary["status"] == "WAITING_FOR_HUMAN"
    assert summary["message"] == WAITING_MESSAGE
    assert summary["teacher_review_count"] == 0
    assert summary["supervisor_review_count"] == 0
    assert summary["acceptance_rate"] is None


def test_researcher_reviews_do_not_count_as_teacher_study() -> None:
    reviews = [
        {
            "reviewer_role": "researcher",
            "reviewer_name": "Wail Ouaret",
            "decision": "ACCEPT",
            "runtime_resource_id": "runtime:moodle:abc",
            "competency_id": "GI_C3_1",
        },
        {
            "reviewer_role": "researcher",
            "reviewer_name": "Wail Ouaret",
            "decision": "REJECT",
            "runtime_resource_id": "runtime:moodle:abc",
            "competency_id": "GI_C3",
        },
    ]
    summary = summarize_human_validation(reviews)
    assert summary["status"] == "WAITING_FOR_HUMAN"
    assert summary["researcher_review_count"] == 2
    assert summary["teacher_review_count"] == 0
    assert summary["supervisor_review_count"] == 0
    assert summary["suggestions_reviewed"] == 0


def test_teacher_reviews_are_summarized(tmp_path: Path) -> None:
    reviews = [
        {
            "review_id": "r1",
            "analysis_id": "an_1",
            "runtime_resource_id": "runtime:page:1",
            "competency_id": "GI_C1_2",
            "decision": "ACCEPT",
            "reviewer_name": "Teacher A",
            "reviewer_role": "teacher",
            "review_date": "2026-09-18",
            "backend": "gemini",
            "model": "gemini-3.5-flash",
        },
        {
            "review_id": "r2",
            "analysis_id": "an_1",
            "runtime_resource_id": "runtime:page:1",
            "competency_id": "GI_C1",
            "decision": "MODIFY",
            "replacement_competency_id": "GI_C1_2",
            "reviewer_name": "Teacher A",
            "reviewer_role": "teacher",
            "review_date": "2026-09-18",
            "backend": "gemini",
            "model": "gemini-3.5-flash",
        },
    ]
    form = [
        {
            "condition": "with_evidence",
            "decision": "ACCEPT",
            "evidence_usefulness_rating": "5",
            "confidence_in_decision": "4",
            "decision_time_seconds": "20",
        }
    ]
    summary = summarize_human_validation(reviews, form)
    assert summary["status"] == "COMPLETE"
    assert summary["teacher_review_count"] == 2
    assert summary["accept_count"] == 1
    assert summary["modify_count"] == 1
    assert summary["acceptance_rate"] == 0.5
    assert summary["modification_rate"] == 0.5
    assert summary["reviewer_count"] == 1
    assert summary["evidence_usefulness"]["n"] == 1
    assert summary["significance_tests"] == "not_run"

    written = write_human_validation_outputs(
        project_root=tmp_path,
        reviews=reviews,
        form_rows=form,
    )
    assert written["report"].exists()
    assert "Teacher A" in written["table"].read_text(encoding="utf-8")


def test_empty_form_has_headers_only(tmp_path: Path) -> None:
    path = tmp_path / "human_validation_form.csv"
    write_empty_validation_form(path)
    text = path.read_text(encoding="utf-8")
    assert "evidence_usefulness_rating" in text
    assert text.count("\n") == 1
