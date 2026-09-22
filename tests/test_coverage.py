"""Tests for the Section O minimal validated-coverage view.

The property that matters most: an unreviewed prediction is never counted as
coverage. Coverage exists only where a human decision put it.
"""

from __future__ import annotations

import pytest

from moodle_competency.coverage import (
    VALIDATING_DECISIONS,
    build_coverage,
    competency_to_resources,
    coverage_table_rows,
    resource_to_competencies,
    validated_pairs,
)


COMPETENCY_IDS = ["GI_C1", "GI_C1_1", "GI_C1_2", "GI_C2_3"]

RESOURCES = [
    {
        "resource_id": "page:1",
        "course_shortname": "MVP-SW",
        "section_name": "Week 1",
        "resource_type": "page",
        "title": "Page one",
    },
    {
        "resource_id": "page:2",
        "course_shortname": "MVP-SW",
        "section_name": "Week 2",
        "resource_type": "page",
        "title": "Page two",
    },
    {
        "resource_id": "quiz_question:1:1",
        "course_shortname": "MVP-DATA",
        "section_name": "Week 1",
        "resource_type": "quiz_question",
        "title": "Question one",
    },
]


def review(
    resource_id: str,
    competency_id: str,
    decision: str,
    *,
    modified: str = "",
    reviewer: str = "Test Teacher",
) -> dict[str, str]:
    return {
        "review_id": f"{resource_id}|{competency_id}",
        "resource_id": resource_id,
        "competency_id": competency_id,
        "decision": decision,
        "modified_competency_ids": modified,
        "reviewer": reviewer,
    }


# --------------------------------------------------------------------------
# What counts as validated
# --------------------------------------------------------------------------


def test_accept_validates_the_pair() -> None:
    pairs = validated_pairs([review("page:1", "GI_C1_1", "accept")])

    assert pairs == [
        {
            "resource_id": "page:1",
            "competency_id": "GI_C1_1",
            "via": "accept",
            "reviewer": "Test Teacher",
        }
    ]


def test_reject_validates_nothing() -> None:
    assert validated_pairs([review("page:1", "GI_C1_1", "reject")]) == []


def test_modify_validates_the_replacement_not_the_original() -> None:
    pairs = validated_pairs(
        [review("page:1", "GI_C1", "modify", modified="GI_C1_1;GI_C1_2")]
    )

    ids = {pair["competency_id"] for pair in pairs}

    assert ids == {"GI_C1_1", "GI_C1_2"}
    assert "GI_C1" not in ids
    assert all(pair["via"] == "modify" for pair in pairs)


def test_add_validates_a_pair_the_model_never_predicted() -> None:
    pairs = validated_pairs([review("page:2", "GI_C2_3", "add")])

    assert pairs[0]["via"] == "add"


def test_unreviewed_and_blank_decisions_validate_nothing() -> None:
    assert validated_pairs([]) == []
    assert validated_pairs([review("page:1", "GI_C1_1", "")]) == []
    assert validated_pairs([review("page:1", "GI_C1_1", "pending")]) == []


def test_validating_decisions_are_accept_and_add_only() -> None:
    assert VALIDATING_DECISIONS == {"accept", "add"}


def test_duplicate_decisions_are_deduplicated() -> None:
    pairs = validated_pairs(
        [
            review("page:1", "GI_C1_1", "accept"),
            review("page:1", "GI_C1_1", "accept", reviewer="Someone Else"),
        ]
    )

    assert len(pairs) == 1


def test_pairs_are_sorted_regardless_of_input_order() -> None:
    forward = validated_pairs(
        [
            review("page:2", "GI_C1_2", "accept"),
            review("page:1", "GI_C1_1", "accept"),
        ]
    )
    backward = validated_pairs(
        [
            review("page:1", "GI_C1_1", "accept"),
            review("page:2", "GI_C1_2", "accept"),
        ]
    )

    assert forward == backward


def test_review_without_resource_id_is_ignored() -> None:
    assert validated_pairs([review("", "GI_C1_1", "accept")]) == []


# --------------------------------------------------------------------------
# Both directions
# --------------------------------------------------------------------------


def test_competency_to_resources_includes_empty_competencies() -> None:
    pairs = validated_pairs([review("page:1", "GI_C1_1", "accept")])
    result = competency_to_resources(pairs, COMPETENCY_IDS)

    assert result["GI_C1_1"] == ["page:1"]
    assert result["GI_C2_3"] == []
    assert set(result) == set(COMPETENCY_IDS)


def test_resource_to_competencies_includes_empty_resources() -> None:
    pairs = validated_pairs([review("page:1", "GI_C1_1", "accept")])
    result = resource_to_competencies(pairs, [r["resource_id"] for r in RESOURCES])

    assert result["page:1"] == ["GI_C1_1"]
    assert result["page:2"] == []


# --------------------------------------------------------------------------
# The empty case
# --------------------------------------------------------------------------


def test_no_decisions_means_zero_coverage_not_predictions() -> None:
    coverage = build_coverage([], RESOURCES, COMPETENCY_IDS)

    assert coverage["status"] == "WAITING_FOR_HUMAN"
    assert coverage["validated_mapping_count"] == 0
    assert coverage["mapped_resource_count"] == 0
    assert coverage["covered_competency_count"] == 0
    assert coverage["unmapped_resources"] == [
        "page:1",
        "page:2",
        "quiz_question:1:1",
    ]
    assert coverage["competencies_without_validated_resources"] == sorted(
        COMPETENCY_IDS
    )
    assert coverage["message"]


def test_no_decisions_means_empty_breakdowns() -> None:
    coverage = build_coverage([], RESOURCES, COMPETENCY_IDS)

    assert coverage["validated_by_course"] == {}
    assert coverage["validated_by_section"] == {}
    assert all(count == 0 for count in coverage["validated_by_competency"].values())


# --------------------------------------------------------------------------
# A populated case
# --------------------------------------------------------------------------


@pytest.fixture()
def coverage() -> dict:
    reviews = [
        review("page:1", "GI_C1_1", "accept"),
        review("page:1", "GI_C1", "reject"),
        review("page:2", "GI_C1", "modify", modified="GI_C1_2"),
        review("quiz_question:1:1", "GI_C2_3", "add"),
    ]
    return build_coverage(reviews, RESOURCES, COMPETENCY_IDS)


def test_coverage_counts_only_validated_mappings(coverage) -> None:
    assert coverage["status"] == "COMPLETE"
    assert coverage["validated_mapping_count"] == 3


def test_coverage_reports_both_directions(coverage) -> None:
    assert coverage["competency_to_resources"]["GI_C1_1"] == ["page:1"]
    assert coverage["competency_to_resources"]["GI_C1_2"] == ["page:2"]
    assert coverage["competency_to_resources"]["GI_C1"] == []
    assert coverage["resource_to_competencies"]["quiz_question:1:1"] == ["GI_C2_3"]


def test_coverage_identifies_uncovered_competencies(coverage) -> None:
    assert coverage["competencies_without_validated_resources"] == ["GI_C1"]
    assert coverage["covered_competency_count"] == 3


def test_coverage_identifies_unmapped_resources(coverage) -> None:
    assert coverage["unmapped_resources"] == []
    assert coverage["mapped_resource_count"] == 3


def test_unmapped_resource_is_listed_when_nothing_validated() -> None:
    reviews = [review("page:1", "GI_C1_1", "accept")]
    coverage = build_coverage(reviews, RESOURCES, COMPETENCY_IDS)

    assert coverage["unmapped_resources"] == ["page:2", "quiz_question:1:1"]
    assert coverage["mapped_resource_count"] == 1


def test_coverage_counts_by_course_and_section(coverage) -> None:
    assert coverage["validated_by_course"] == {"MVP-SW": 2, "MVP-DATA": 1}
    assert coverage["validated_by_section"] == {
        "MVP-SW · Week 1": 1,
        "MVP-SW · Week 2": 1,
        "MVP-DATA · Week 1": 1,
    }


def test_coverage_counts_by_competency(coverage) -> None:
    assert coverage["validated_by_competency"] == {
        "GI_C1": 0,
        "GI_C1_1": 1,
        "GI_C1_2": 1,
        "GI_C2_3": 1,
    }


def test_coverage_states_its_narrow_scope(coverage) -> None:
    assert "No recommendation engine" in coverage["scope_note"]
    assert "not coverage" in coverage["definition_note"]


def test_resource_missing_from_the_catalogue_is_tolerated() -> None:
    reviews = [review("page:999", "GI_C1_1", "accept")]
    coverage = build_coverage(reviews, RESOURCES, COMPETENCY_IDS)

    assert coverage["validated_by_course"]["unknown"] == 1
    assert coverage["resource_to_competencies"]["page:999"] == ["GI_C1_1"]


# --------------------------------------------------------------------------
# Table
# --------------------------------------------------------------------------


def test_table_rows_cover_each_scope(coverage) -> None:
    rows = coverage_table_rows(coverage)
    scopes = {row["scope"] for row in rows}

    assert scopes == {"overall", "competency", "resource", "course", "section"}


def test_table_row_lists_validated_ids(coverage) -> None:
    rows = coverage_table_rows(coverage)
    row = next(
        r for r in rows if r["scope"] == "competency" and r["key"] == "GI_C1_1"
    )

    assert row["validated_count"] == "1"
    assert row["detail"] == "page:1"


def test_table_for_empty_coverage_reports_zero() -> None:
    rows = coverage_table_rows(build_coverage([], RESOURCES, COMPETENCY_IDS))
    overall = next(row for row in rows if row["scope"] == "overall")

    assert overall["validated_count"] == "0"
    assert overall["detail"] == "WAITING_FOR_HUMAN"
