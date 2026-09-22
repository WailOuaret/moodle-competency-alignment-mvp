"""Tests for the Section N teacher-review summary.

The central property under test is that the summary never invents a rate. With
no real decisions the rates must be ``None`` — not ``0.0``, which would read as
"nobody accepted anything" rather than "nothing was reviewed".
"""

from __future__ import annotations

import pytest

from moodle_competency.teacher_review_summary import (
    REVIEWED_DECISIONS,
    TEACHER_ROLES,
    summarize_teacher_reviews,
    summary_table_rows,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def mapping(
    resource_id: str,
    competency_id: str,
    *,
    course: str = "MVP-SW",
    resource_type: str = "page",
) -> dict[str, str]:
    return {
        "resource_id": resource_id,
        "competency_id": competency_id,
        "course_shortname": course,
        "resource_type": resource_type,
    }


def review(
    resource_id: str,
    competency_id: str,
    decision: str,
    *,
    reviewer: str = "Test Teacher",
    reviewer_role: str = "teacher",
    evidence_relevance: str = "",
) -> dict[str, str]:
    return {
        "review_id": f"{resource_id}|{competency_id}",
        "resource_id": resource_id,
        "competency_id": competency_id,
        "decision": decision,
        "reviewer": reviewer,
        "reviewer_role": reviewer_role,
        "evidence_relevance": evidence_relevance,
        "review_date": "2026-09-22",
    }


@pytest.fixture()
def mappings() -> list[dict[str, str]]:
    return [
        mapping("page:1", "GI_C1_1"),
        mapping("page:1", "GI_C1"),
        mapping("page:2", "GI_C2_3"),
        mapping(
            "quiz_question:1:1",
            "GI_C3_2",
            course="MVP-DATA",
            resource_type="quiz_question",
        ),
    ]


# --------------------------------------------------------------------------
# The empty case — the one that matters most
# --------------------------------------------------------------------------


def test_no_reviews_reports_waiting_and_no_rates(mappings) -> None:
    summary = summarize_teacher_reviews([], mappings)

    assert summary["status"] == "WAITING_FOR_HUMAN"
    assert summary["message"]
    assert summary["reviewed"] == 0
    assert summary["pending"] == 4
    assert summary["reviewable_mappings"] == 4


def test_rates_are_none_not_zero_without_reviews(mappings) -> None:
    summary = summarize_teacher_reviews([], mappings)

    for metric in ("acceptance_rate", "edit_rate", "rejection_rate"):
        assert summary[metric] is None, f"{metric} must be None, not 0.0"


def test_no_reviews_means_no_teacher_validation(mappings) -> None:
    summary = summarize_teacher_reviews([], mappings)

    assert summary["teacher_or_supervisor_validation_performed"] is False
    assert summary["reviewer_roles"] == {}


def test_empty_summary_table_writes_blank_rates_not_zero(mappings) -> None:
    rows = summary_table_rows(summarize_teacher_reviews([], mappings))
    by_metric = {row["metric"]: row for row in rows}

    assert by_metric["acceptance_rate"]["value"] == ""
    assert by_metric["acceptance_rate"]["note"] == "no real decisions exist"


def test_no_mappings_yields_null_coverage() -> None:
    summary = summarize_teacher_reviews([], [])

    assert summary["reviewed_fraction"] is None


# --------------------------------------------------------------------------
# Counting real decisions
# --------------------------------------------------------------------------


def test_counts_each_decision_type(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:1", "GI_C1", "reject"),
        review("page:2", "GI_C2_3", "modify"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["status"] == "COMPLETE"
    assert summary["accepted"] == 1
    assert summary["rejected"] == 1
    assert summary["modified"] == 1
    assert summary["reviewed"] == 3
    assert summary["pending"] == 1


def test_rates_use_reviewed_suggestions_as_denominator(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:1", "GI_C1", "reject"),
        review("page:2", "GI_C2_3", "accept"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["rate_denominator"] == 3
    assert summary["acceptance_rate"] == pytest.approx(2 / 3)
    assert summary["rejection_rate"] == pytest.approx(1 / 3)
    assert summary["edit_rate"] == 0.0


def test_added_mappings_are_outside_the_reviewed_denominator(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:9", "GI_C3_3", "add"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["added"] == 1
    assert summary["reviewed"] == 1
    assert summary["rate_denominator"] == 1
    assert summary["acceptance_rate"] == 1.0


def test_unknown_decision_values_are_ignored(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:1", "GI_C1", ""),
        review("page:2", "GI_C2_3", "maybe"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["reviewed"] == 1
    assert summary["rate_denominator"] == 1


def test_reviewed_decisions_exclude_add() -> None:
    assert "add" not in REVIEWED_DECISIONS
    assert set(REVIEWED_DECISIONS) == {"accept", "reject", "modify"}


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def test_researcher_only_is_not_teacher_validation(mappings) -> None:
    reviews = [
        review(
            "page:1",
            "GI_C1_1",
            "accept",
            reviewer="Wail Ouaret",
            reviewer_role="researcher",
        )
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["reviewer_roles"] == {"researcher": 1}
    assert summary["teacher_or_supervisor_validation_performed"] is False


@pytest.mark.parametrize("role", sorted(TEACHER_ROLES))
def test_a_real_teacher_or_supervisor_counts(mappings, role: str) -> None:
    reviews = [review("page:1", "GI_C1_1", "accept", reviewer_role=role)]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["teacher_or_supervisor_validation_performed"] is True


def test_reviewers_are_counted_by_name(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept", reviewer="Ana"),
        review("page:1", "GI_C1", "reject", reviewer="Ana"),
        review("page:2", "GI_C2_3", "accept", reviewer="Bo"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["reviewers"] == {"Ana": 2, "Bo": 1}


def test_missing_reviewer_name_is_marked_unrecorded(mappings) -> None:
    row = review("page:1", "GI_C1_1", "accept")
    row["reviewer"] = ""

    summary = summarize_teacher_reviews([row], mappings)

    assert summary["reviewers"] == {"unrecorded": 1}


def test_runtime_reviews_are_reported_but_kept_separate(mappings) -> None:
    runtime = [
        {"decision": "ACCEPT", "reviewer_role": "researcher"},
        {"decision": "REJECT", "reviewer_role": "researcher"},
    ]

    summary = summarize_teacher_reviews([], mappings, runtime_reviews=runtime)

    assert summary["runtime_review_count"] == 2
    assert summary["runtime_reviewer_roles"] == {"researcher": 2}
    assert summary["status"] == "WAITING_FOR_HUMAN"
    assert summary["teacher_or_supervisor_validation_performed"] is False


def test_runtime_teacher_counts_as_validation(mappings) -> None:
    runtime = [{"decision": "ACCEPT", "reviewer_role": "teacher"}]

    summary = summarize_teacher_reviews([], mappings, runtime_reviews=runtime)

    assert summary["teacher_or_supervisor_validation_performed"] is True


def test_no_significance_tests_are_claimed(mappings) -> None:
    summary = summarize_teacher_reviews(
        [review("page:1", "GI_C1_1", "accept")], mappings
    )

    assert summary["significance_tests"] == "not_run"


# --------------------------------------------------------------------------
# Evidence relevance
# --------------------------------------------------------------------------


def test_evidence_relevance_distribution_is_counted(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept", evidence_relevance="2"),
        review("page:1", "GI_C1", "reject", evidence_relevance="0"),
        review("page:2", "GI_C2_3", "accept", evidence_relevance="2"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["evidence_relevance_distribution"] == {"0": 1, "1": 0, "2": 2}
    assert summary["evidence_relevance_unanswered"] == 0


def test_blank_evidence_relevance_is_unanswered_not_zero(mappings) -> None:
    reviews = [review("page:1", "GI_C1_1", "accept", evidence_relevance="")]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["evidence_relevance_distribution"]["0"] == 0
    assert summary["evidence_relevance_unanswered"] == 1


# --------------------------------------------------------------------------
# Breakdowns
# --------------------------------------------------------------------------


def test_per_course_and_per_type_breakdowns(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:1", "GI_C1", "reject"),
        review("quiz_question:1:1", "GI_C3_2", "accept"),
    ]

    summary = summarize_teacher_reviews(reviews, mappings)

    assert summary["per_course"]["MVP-SW"]["reviewed"] == 2
    assert summary["per_course"]["MVP-SW"]["accept"] == 1
    assert summary["per_course"]["MVP-SW"]["reject"] == 1
    assert summary["per_course"]["MVP-DATA"]["reviewed"] == 1
    assert summary["per_resource_type"]["page"]["reviewed"] == 2
    assert summary["per_resource_type"]["quiz_question"]["accept"] == 1


def test_breakdowns_are_empty_without_reviews(mappings) -> None:
    summary = summarize_teacher_reviews([], mappings)

    assert summary["per_course"] == {}
    assert summary["per_resource_type"] == {}


# --------------------------------------------------------------------------
# Table rendering
# --------------------------------------------------------------------------


def test_table_rows_cover_every_scope(mappings) -> None:
    reviews = [review("page:1", "GI_C1_1", "accept", evidence_relevance="2")]
    rows = summary_table_rows(
        summarize_teacher_reviews(reviews, mappings, runtime_reviews=[{"decision": "ACCEPT"}])
    )

    scopes = {row["scope"] for row in rows}

    assert "overall" in scopes
    assert "evidence_relevance" in scopes
    assert "course:MVP-SW" in scopes
    assert "resource_type:page" in scopes
    assert "reviewer_role" in scopes
    assert "runtime" in scopes


def test_table_marks_researcher_role_as_not_validation(mappings) -> None:
    reviews = [review("page:1", "GI_C1_1", "accept", reviewer_role="researcher")]
    rows = summary_table_rows(summarize_teacher_reviews(reviews, mappings))

    role_row = next(
        row for row in rows if row["scope"] == "reviewer_role" and row["metric"] == "researcher"
    )

    assert "does NOT count" in role_row["note"]


def test_table_formats_real_rates(mappings) -> None:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:1", "GI_C1", "reject"),
    ]
    rows = summary_table_rows(summarize_teacher_reviews(reviews, mappings))
    by_metric = {row["metric"]: row for row in rows}

    assert by_metric["acceptance_rate"]["value"] == "0.5000000000"
    assert by_metric["acceptance_rate"]["note"] == "denominator = reviewed suggestions"
