"""Fixture-based tests for error-analysis flags."""

from __future__ import annotations

from moodle_competency.error_analysis import (
    classify_fragment,
    summarize_error_rows,
)


def test_retrieval_failure_and_llm_miss() -> None:
    result = classify_fragment(
        fragment_id="page:1#f001",
        gold_ids=["GI_C1_1", "GI_C2_3"],
        no_competency=False,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_1", "GI_C1_2", "GI_C1", "GI_C1_3", "GI_C1_4"],
        predicted_ids=["GI_C1_2"],
        abstain=False,
    )

    assert "retrieval_failure" in result["categories"]
    assert "llm_missed_gold_label" in result["categories"]
    assert "llm_wrong_selection" in result["categories"]


def test_correct_prediction_and_abstention() -> None:
    correct = classify_fragment(
        fragment_id="page:1#f001",
        gold_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_1", "GI_C1_2", "GI_C1", "GI_C1_3", "GI_C1_4"],
        predicted_ids=["GI_C1_1"],
        abstain=False,
    )
    abstain = classify_fragment(
        fragment_id="page:1#f002",
        gold_ids=[],
        no_competency=True,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_1", "GI_C1_2", "GI_C1", "GI_C1_3", "GI_C1_4"],
        predicted_ids=[],
        abstain=True,
    )

    assert "correct_prediction" in correct["categories"]
    assert "correct_abstention" in abstain["categories"]


def test_parent_child_and_weak_evidence() -> None:
    result = classify_fragment(
        fragment_id="page:1#f001",
        gold_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous_gold=True,
        ranked_candidates=["GI_C1_1", "GI_C1", "GI_C1_2", "GI_C1_3", "GI_C1_4"],
        predicted_ids=["GI_C1_1", "GI_C1"],
        abstain=False,
        evidence_by_competency={
            "GI_C1_1": [
                {
                    "mechanically_valid": "true",
                    "pedagogical_rating": "1",
                }
            ]
        },
        pedagogical_complete=True,
    )

    assert "parent_child_redundancy" in result["categories"]
    assert "ambiguous_gold" in result["categories"]
    assert "exact_but_weak_evidence" in result["categories"]
    assert "overprediction" in result["categories"]


def test_summary_counts() -> None:
    rows = [
        classify_fragment(
            fragment_id="a",
            gold_ids=["GI_C1_1"],
            no_competency=False,
            ambiguous_gold=False,
            ranked_candidates=["GI_C1_1", "X", "Y", "Z", "W"],
            predicted_ids=["GI_C1_1"],
            abstain=False,
        )
    ]
    summary = summarize_error_rows(rows)

    assert summary["fragments"] == 1
    assert summary["category_counts"]["correct_prediction"] == 1
    assert summary["primary_category_counts"]["correct_prediction"] == 1


def test_evidence_join_is_fragment_and_competency() -> None:
    from moodle_competency.error_analysis import group_evidence_reviews

    grouped = group_evidence_reviews(
        [
            {
                "fragment_id": "page:1#f001",
                "competency_id": "GI_C1_1",
                "evidence_quote": "first",
                "pedagogical_rating": "2",
            },
            {
                "fragment_id": "page:1#f001",
                "competency_id": "GI_C1_1",
                "evidence_quote": "second",
                "pedagogical_rating": "0",
            },
            {
                "fragment_id": "page:1#f001",
                "competency_id": "GI_C1_2",
                "evidence_quote": "other",
                "pedagogical_rating": "2",
            },
        ]
    )

    assert len(grouped[("page:1#f001", "GI_C1_1")]) == 2
    assert len(grouped[("page:1#f001", "GI_C1_2")]) == 1


def test_multiple_quotes_keep_rating_zero() -> None:
    from moodle_competency.error_analysis import (
        aggregate_evidence_reviews,
        pair_evidence_quality_flags,
    )

    reviews = [
        {
            "evidence_quote": "User_Centred_Design",
            "mechanically_valid": "true",
            "pedagogical_rating": "0",
        },
        {
            "evidence_quote": "Testing a prototype with representative users",
            "mechanically_valid": "true",
            "pedagogical_rating": "0",
        },
    ]
    stats = aggregate_evidence_reviews(reviews)
    flags = pair_evidence_quality_flags(
        reviews,
        pedagogical_complete=True,
    )

    assert stats["evidence_quote_count"] == 2
    assert stats["evidence_rating_0_count"] == 2
    assert stats["evidence_rating_mean"] == 0.0
    assert flags["evidence_unsupported"] is True
    assert flags["evidence_clear"] is False
    assert flags["exact_but_weak_evidence"] is True


def test_rating_two_only_is_clear() -> None:
    from moodle_competency.error_analysis import pair_evidence_quality_flags

    flags = pair_evidence_quality_flags(
        [
            {
                "mechanically_valid": "true",
                "pedagogical_rating": "2",
            }
        ],
        pedagogical_complete=True,
    )

    assert flags["evidence_clear"] is True
    assert flags["evidence_partial"] is False
    assert flags["evidence_unsupported"] is False
    assert flags["exact_but_weak_evidence"] is False


def test_rating_one_is_partial() -> None:
    from moodle_competency.error_analysis import pair_evidence_quality_flags

    flags = pair_evidence_quality_flags(
        [
            {
                "mechanically_valid": "true",
                "pedagogical_rating": "2",
            },
            {
                "mechanically_valid": "true",
                "pedagogical_rating": "1",
            },
        ],
        pedagogical_complete=True,
    )

    assert flags["evidence_partial"] is True
    assert flags["evidence_clear"] is False
    assert flags["evidence_unsupported"] is False
    assert flags["exact_but_weak_evidence"] is True


def test_rating_zero_is_unsupported_and_weak_when_exact() -> None:
    from moodle_competency.error_analysis import pair_evidence_quality_flags

    flags = pair_evidence_quality_flags(
        [
            {
                "mechanically_valid": "true",
                "pedagogical_rating": "0",
            }
        ],
        pedagogical_complete=True,
    )

    assert flags["evidence_unsupported"] is True
    assert flags["exact_but_weak_evidence"] is True


def test_invalid_quote_is_not_exact_but_weak() -> None:
    from moodle_competency.error_analysis import pair_evidence_quality_flags

    flags = pair_evidence_quality_flags(
        [
            {
                "mechanically_valid": "false",
                "pedagogical_rating": "1",
            }
        ],
        pedagogical_complete=True,
    )

    assert flags["evidence_partial"] is True
    assert flags["exact_but_weak_evidence"] is False


def test_incomplete_review_does_not_treat_blanks_as_ratings() -> None:
    result = classify_fragment(
        fragment_id="page:1#f001",
        gold_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_1", "GI_C1_2", "GI_C1", "GI_C1_3", "GI_C1_4"],
        predicted_ids=["GI_C1_1"],
        abstain=False,
        evidence_by_competency={
            "GI_C1_1": [
                {
                    "mechanically_valid": "true",
                    "pedagogical_rating": "",
                }
            ]
        },
        pedagogical_complete=False,
    )

    assert "exact_but_weak_evidence" not in result["categories"]
    assert "evidence_unsupported" not in result["categories"]
    assert "evidence_clear" not in result["categories"]
    assert result["pedagogical_evidence_available"] is False


def test_missing_and_empty_evidence_rows() -> None:
    missing = classify_fragment(
        fragment_id="page:1#f001",
        gold_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_1", "GI_C1_2", "GI_C1", "GI_C1_3", "GI_C1_4"],
        predicted_ids=["GI_C1_1"],
        abstain=False,
        evidence_by_competency=None,
        pedagogical_complete=True,
    )
    empty = classify_fragment(
        fragment_id="page:1#f001",
        gold_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_1", "GI_C1_2", "GI_C1", "GI_C1_3", "GI_C1_4"],
        predicted_ids=["GI_C1_1"],
        abstain=False,
        evidence_by_competency={"GI_C1_1": []},
        pedagogical_complete=True,
    )

    assert "evidence_clear" not in missing["categories"]
    assert "evidence_clear" not in empty["categories"]
    assert empty["evidence_stats"]["evidence_quote_count"] == 0


def test_primary_category_priority_and_overlap() -> None:
    result = classify_fragment(
        fragment_id="quiz_question:1:4#f001",
        gold_ids=["GI_C1_3"],
        no_competency=False,
        ambiguous_gold=False,
        ranked_candidates=["GI_C1_2", "GI_C3_2", "GI_C3", "GI_C1_1", "GI_C1_4"],
        predicted_ids=["GI_C1_1"],
        abstain=False,
        evidence_by_competency={
            "GI_C1_1": [
                {
                    "mechanically_valid": "true",
                    "pedagogical_rating": "0",
                    "evidence_quote": "User_Centred_Design",
                },
                {
                    "mechanically_valid": "true",
                    "pedagogical_rating": "0",
                    "evidence_quote": "Testing a prototype with representative users",
                },
            ]
        },
        pedagogical_complete=True,
    )

    assert result["primary_error_category"] == "retrieval_failure"
    assert "underprediction" in result["categories"]
    assert "llm_wrong_selection" in result["categories"]
    assert "overprediction" in result["categories"]
    assert "evidence_unsupported" in result["categories"]
    assert "correct_prediction" not in result["categories"]


def test_group_evidence_does_not_mutate_input() -> None:
    from moodle_competency.error_analysis import group_evidence_reviews

    original = [
        {
            "fragment_id": "page:1#f001",
            "competency_id": "GI_C1_1",
            "pedagogical_rating": "2",
            "evidence_quote": "keep",
        }
    ]
    grouped = group_evidence_reviews(original)
    grouped[("page:1#f001", "GI_C1_1")][0]["pedagogical_rating"] = "0"

    assert original[0]["pedagogical_rating"] == "2"
    assert original[0]["evidence_quote"] == "keep"
