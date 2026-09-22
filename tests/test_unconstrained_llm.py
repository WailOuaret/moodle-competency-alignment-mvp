"""Tests for the optional all-13 unconstrained condition (Section K).

**No test here calls Gemini.** Responses are hand-written fixtures, and the
only validator exercised is the shared one from ``llm_validation``, which is
reused unchanged so both conditions are judged identically.
"""

from __future__ import annotations

import pytest

from moodle_competency.llm_tasks import build_output_contract
from moodle_competency.llm_validation import (
    validate_alignment_response,
    validate_response_collection,
)
from moodle_competency.unconstrained_llm import (
    CANDIDATE_SPACE,
    EXPECTED_CANDIDATE_COUNT,
    HELD_CONSTANT,
    MAXIMUM_SELECTIONS,
    UnconstrainedTaskError,
    build_full_candidate_list,
    build_unconstrained_prompt,
    build_unconstrained_task,
    build_unconstrained_tasks,
    compare_conditions,
    experiment_manifest,
    prompt_rule_block,
    validate_unconstrained_tasks,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


COMPETENCIES = [
    {
        "competency_id": 2,
        "idnumber": "GI_P1",
        "shortname": "Parent one",
        "description_text": "Parent one description",
        "parent_idnumber": "",
        "parent_shortname": "",
        "hierarchy_idnumbers": ["GI_P1"],
        "hierarchy_labels": ["Parent one"],
        "depth": 0,
        "sortorder": 0,
    },
    {
        "competency_id": 3,
        "idnumber": "GI_P1_1",
        "shortname": "Child one",
        "description_text": "Child one description",
        "parent_idnumber": "GI_P1",
        "parent_shortname": "Parent one",
        "hierarchy_idnumbers": ["GI_P1", "GI_P1_1"],
        "hierarchy_labels": ["Parent one", "Child one"],
        "depth": 1,
        "sortorder": 1,
    },
    {
        "competency_id": 4,
        "idnumber": "GI_P1_2",
        "shortname": "Child two",
        "description_text": "Child two description",
        "parent_idnumber": "GI_P1",
        "parent_shortname": "Parent one",
        "hierarchy_idnumbers": ["GI_P1", "GI_P1_2"],
        "hierarchy_labels": ["Parent one", "Child two"],
        "depth": 1,
        "sortorder": 2,
    },
]

FRAGMENT_TEXT = "This fragment explains software design and testing clearly."

FRAGMENTS = [
    {
        "fragment_id": "page:1#f001",
        "resource_id": "page:1",
        "resource_type": "page",
        "fragment_type": "page_chunk",
        "course_id": 2,
        "course_shortname": "MVP-SW",
        "course_module_id": 3,
        "activity_id": 1,
        "activity_name": "Activity one",
        "title": "Page one",
        "text": FRAGMENT_TEXT,
    },
    {
        "fragment_id": "page:1#f002",
        "resource_id": "page:1",
        "resource_type": "page",
        "fragment_type": "page_chunk",
        "course_id": 2,
        "course_shortname": "MVP-SW",
        "course_module_id": 3,
        "activity_id": 1,
        "activity_name": "Activity one",
        "title": "Page one",
        "text": "A second fragment about distributed systems.",
    },
]


@pytest.fixture()
def tasks() -> list[dict]:
    return build_unconstrained_tasks(
        fragments=FRAGMENTS, competencies=COMPETENCIES
    )


@pytest.fixture()
def task(tasks) -> dict:
    return tasks[0]


# --------------------------------------------------------------------------
# Candidate space — the one intended difference
# --------------------------------------------------------------------------


def test_candidate_list_contains_every_competency() -> None:
    candidates = build_full_candidate_list(COMPETENCIES)

    assert len(candidates) == len(COMPETENCIES)
    assert [c["idnumber"] for c in candidates] == ["GI_P1", "GI_P1_1", "GI_P1_2"]


def test_candidate_list_is_ordered_by_framework_sort_order() -> None:
    shuffled = [COMPETENCIES[2], COMPETENCIES[0], COMPETENCIES[1]]

    assert [c["idnumber"] for c in build_full_candidate_list(shuffled)] == [
        "GI_P1",
        "GI_P1_1",
        "GI_P1_2",
    ]


def test_candidate_list_carries_no_bm25_score() -> None:
    for candidate in build_full_candidate_list(COMPETENCIES):
        assert "bm25_score" not in candidate


def test_candidate_rank_is_a_presentation_index() -> None:
    ranks = [c["rank"] for c in build_full_candidate_list(COMPETENCIES)]

    assert ranks == [1, 2, 3]


def test_competency_without_idnumber_is_refused() -> None:
    with pytest.raises(UnconstrainedTaskError, match="no idnumber"):
        build_full_candidate_list([{"shortname": "Nameless", "sortorder": 0}])


def test_allowed_idnumbers_is_the_whole_framework(task) -> None:
    assert task["allowed_idnumbers"] == ["GI_P1", "GI_P1_1", "GI_P1_2"]


def test_candidate_restriction_is_recorded_as_disabled(task) -> None:
    assert task["instructions"]["candidate_restriction_enforced"] is False
    assert task["candidate_space"] == CANDIDATE_SPACE


# --------------------------------------------------------------------------
# Everything else held identical
# --------------------------------------------------------------------------


def test_max_selections_matches_the_constrained_run(task) -> None:
    assert task["instructions"]["maximum_selections"] == MAXIMUM_SELECTIONS == 3


def test_evidence_requirement_matches_the_constrained_run(task) -> None:
    assert task["instructions"]["evidence_must_be_exact_substring"] is True


def test_abstention_is_still_allowed(task) -> None:
    assert task["instructions"]["abstention_allowed"] is True
    assert task["instructions"]["minimum_selections"] == 0


def test_output_contract_is_the_shared_one(task) -> None:
    assert task["output_contract"] == build_output_contract("page:1#f001")


def test_prompt_rules_are_shared_with_the_constrained_prompt() -> None:
    rules = prompt_rule_block(["GI_P1", "GI_P1_1"])

    assert "1. Select only from these allowed competency IDs: GI_P1, GI_P1_1." in rules
    assert "3. Select between zero and three competencies." in rules
    assert "6. Every evidence quote must be an exact, contiguous substring" in rules
    assert "12. Return valid JSON only." in rules


def test_prompt_lists_every_competency_and_omits_bm25(task) -> None:
    prompt = task["prompt"]

    for competency_id in ("GI_P1", "GI_P1_1", "GI_P1_2"):
        assert competency_id in prompt

    assert "BM25 score" not in prompt


def test_prompt_contains_the_fragment_text(task) -> None:
    assert FRAGMENT_TEXT in task["prompt"]


def test_prompt_builder_needs_at_least_one_candidate() -> None:
    with pytest.raises(IndexError):
        build_unconstrained_prompt(
            fragment_id="f",
            fragment_text="t",
            title="",
            activity_name="",
            course_shortname="",
            candidates=[],
        )


# --------------------------------------------------------------------------
# Task construction
# --------------------------------------------------------------------------


def test_one_task_per_fragment(tasks) -> None:
    assert len(tasks) == len(FRAGMENTS)
    assert [t["fragment_id"] for t in tasks] == [
        "page:1#f001",
        "page:1#f002",
    ]


def test_task_id_is_distinct_from_the_constrained_one(task) -> None:
    assert task["task_id"] == "unconstrained_alignment:page:1#f001"
    assert task["experiment"] == "unconstrained_all_competencies"


def test_task_requires_a_fragment_id() -> None:
    candidates = build_full_candidate_list(COMPETENCIES)

    with pytest.raises(UnconstrainedTaskError, match="missing fragment_id"):
        build_unconstrained_task(fragment={"text": "x"}, candidates=candidates)


def test_task_requires_non_empty_text() -> None:
    candidates = build_full_candidate_list(COMPETENCIES)

    with pytest.raises(UnconstrainedTaskError, match="empty text"):
        build_unconstrained_task(
            fragment={"fragment_id": "f1", "text": "   "}, candidates=candidates
        )


def test_task_requires_candidates() -> None:
    with pytest.raises(UnconstrainedTaskError, match="no candidate"):
        build_unconstrained_task(
            fragment={"fragment_id": "f1", "text": "x"}, candidates=[]
        )


def test_duplicate_candidate_ids_are_refused() -> None:
    candidates = build_full_candidate_list(COMPETENCIES)
    duplicated = [*candidates, dict(candidates[0])]

    with pytest.raises(UnconstrainedTaskError, match="Duplicate competency ID"):
        build_unconstrained_task(
            fragment={"fragment_id": "f1", "text": "x"}, candidates=duplicated
        )


# --------------------------------------------------------------------------
# Task-set validation
# --------------------------------------------------------------------------


def test_task_validation_passes_for_a_well_formed_set(tasks) -> None:
    report = validate_unconstrained_tasks(
        tasks,
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )

    assert report["status"] == "PASSED"
    assert report["errors"] == []
    assert report["task_count"] == 2


def test_task_validation_detects_a_missing_fragment(tasks) -> None:
    report = validate_unconstrained_tasks(
        tasks[:1],
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )

    assert report["status"] == "FAILED"
    assert report["missing_fragment_ids"] == ["page:1#f002"]


def test_task_validation_detects_a_duplicate(tasks) -> None:
    report = validate_unconstrained_tasks(
        [*tasks, dict(tasks[0])],
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )

    assert report["duplicate_fragment_ids"] == ["page:1#f001"]
    assert report["status"] == "FAILED"


def test_task_validation_detects_a_shrunken_candidate_space(tasks) -> None:
    broken = dict(tasks[0])
    broken["allowed_idnumbers"] = ["GI_P1"]

    report = validate_unconstrained_tasks(
        [broken, tasks[1]],
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )

    assert report["status"] == "FAILED"
    assert any("expected 3 candidates" in error for error in report["errors"])


def test_task_validation_rejects_a_restriction_left_enabled(tasks) -> None:
    broken = dict(tasks[0])
    broken["instructions"] = dict(broken["instructions"])
    broken["instructions"]["candidate_restriction_enforced"] = True

    report = validate_unconstrained_tasks(
        [broken, tasks[1]],
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )

    assert any(
        "candidate_restriction_enforced must be false" in error
        for error in report["errors"]
    )


def test_task_validation_rejects_a_changed_selection_limit(tasks) -> None:
    broken = dict(tasks[0])
    broken["instructions"] = dict(broken["instructions"])
    broken["instructions"]["maximum_selections"] = 5

    report = validate_unconstrained_tasks(
        [broken, tasks[1]],
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )

    assert any("maximum_selections must be 3" in error for error in report["errors"])


def test_expected_candidate_count_default_is_thirteen() -> None:
    assert EXPECTED_CANDIDATE_COUNT == 13


# --------------------------------------------------------------------------
# Condition comparison — what makes the experiment interpretable
# --------------------------------------------------------------------------


def constrained_task(fragment: dict, allowed: list[str]) -> dict:
    return {
        "fragment_id": fragment["fragment_id"],
        "fragment_text": fragment["text"],
        "allowed_idnumbers": allowed,
        "instructions": {
            "minimum_selections": 0,
            "maximum_selections": 3,
            "abstention_allowed": True,
            "evidence_must_be_exact_substring": True,
            "candidate_restriction_enforced": True,
            "response_format": "json_only",
        },
    }


def test_comparison_passes_when_only_the_candidate_space_differs(tasks) -> None:
    constrained = [
        constrained_task(FRAGMENTS[0], ["GI_P1_1"]),
        constrained_task(FRAGMENTS[1], ["GI_P1_2"]),
    ]

    report = compare_conditions(
        constrained_tasks=constrained, unconstrained_tasks=tasks
    )

    assert report["status"] == "PASSED"
    assert report["shared_fragment_count"] == 2
    assert report["fragment_text_mismatches"] == []
    assert report["instruction_mismatches"] == []
    assert report["fragments_with_identical_candidate_space"] == []


def test_comparison_flags_drifted_fragment_text(tasks) -> None:
    constrained = [
        constrained_task(
            {**FRAGMENTS[0], "text": "Different text entirely."}, ["GI_P1_1"]
        ),
        constrained_task(FRAGMENTS[1], ["GI_P1_2"]),
    ]

    report = compare_conditions(
        constrained_tasks=constrained, unconstrained_tasks=tasks
    )

    assert report["status"] == "FAILED"
    assert report["fragment_text_mismatches"] == ["page:1#f001"]


def test_comparison_flags_drifted_instructions(tasks) -> None:
    constrained = [constrained_task(FRAGMENTS[0], ["GI_P1_1"])]
    constrained[0]["instructions"]["maximum_selections"] = 2

    report = compare_conditions(
        constrained_tasks=constrained, unconstrained_tasks=tasks
    )

    assert report["status"] == "FAILED"
    assert "page:1#f001:maximum_selections" in report["instruction_mismatches"]


def test_comparison_flags_a_fragment_missing_from_the_new_condition(tasks) -> None:
    constrained = [
        constrained_task(FRAGMENTS[0], ["GI_P1_1"]),
        constrained_task(FRAGMENTS[1], ["GI_P1_2"]),
        constrained_task(
            {"fragment_id": "page:2#f001", "text": "Extra"}, ["GI_P1"]
        ),
    ]

    report = compare_conditions(
        constrained_tasks=constrained, unconstrained_tasks=tasks
    )

    assert report["status"] == "FAILED"
    assert any("page:2#f001" in error for error in report["errors"])


def test_comparison_notes_where_candidate_space_did_not_widen(tasks) -> None:
    constrained = [
        constrained_task(FRAGMENTS[0], ["GI_P1", "GI_P1_1", "GI_P1_2"]),
        constrained_task(FRAGMENTS[1], ["GI_P1_2"]),
    ]

    report = compare_conditions(
        constrained_tasks=constrained, unconstrained_tasks=tasks
    )

    assert report["fragments_with_identical_candidate_space"] == ["page:1#f001"]
    assert report["status"] == "PASSED"


# --------------------------------------------------------------------------
# The shared validator judges both conditions identically
# --------------------------------------------------------------------------


def mock_response(**overrides) -> dict:
    """A hand-written model response. Never produced by a live call."""

    response = {
        "fragment_id": "page:1#f001",
        "abstain": False,
        "selected": [
            {
                "idnumber": "GI_P1_1",
                "evidence": ["software design and testing"],
                "reason": "The fragment covers design and testing.",
                "confidence": 0.9,
            }
        ],
        "overall_reason": "Direct evidence for the child competency.",
    }
    response.update(overrides)
    return response


def test_valid_mock_response_passes_the_shared_validator(task) -> None:
    result = validate_alignment_response(task=task, response=mock_response())

    assert result["valid"] is True
    assert result["validation_errors"] == []


def test_paraphrased_evidence_is_rejected(task) -> None:
    response = mock_response(
        selected=[
            {
                "idnumber": "GI_P1_1",
                "evidence": ["the fragment discusses designing software"],
                "reason": "Paraphrase.",
                "confidence": 0.9,
            }
        ]
    )

    result = validate_alignment_response(task=task, response=response)

    assert result["valid"] is False


def test_a_competency_outside_the_framework_is_still_rejected(task) -> None:
    response = mock_response(
        selected=[
            {
                "idnumber": "GI_NOT_REAL",
                "evidence": ["software design and testing"],
                "reason": "Invented ID.",
                "confidence": 0.9,
            }
        ]
    )

    result = validate_alignment_response(task=task, response=response)

    assert result["valid"] is False


def test_a_competency_outside_bm25_top5_is_now_accepted(task) -> None:
    """The whole point: a label BM25 would not have offered is now legal."""

    response = mock_response(
        selected=[
            {
                "idnumber": "GI_P1_2",
                "evidence": ["software design and testing"],
                "reason": "Allowed because the candidate space is the framework.",
                "confidence": 0.7,
            }
        ]
    )

    result = validate_alignment_response(task=task, response=response)

    assert result["valid"] is True


def test_more_than_three_selections_is_still_rejected(task) -> None:
    response = mock_response(
        selected=[
            {
                "idnumber": competency_id,
                "evidence": ["software design and testing"],
                "reason": "r",
                "confidence": 0.5,
            }
            for competency_id in ("GI_P1", "GI_P1_1", "GI_P1_2", "GI_P1")
        ]
    )

    result = validate_alignment_response(task=task, response=response)

    assert result["valid"] is False


def test_abstention_with_selections_is_rejected(task) -> None:
    result = validate_alignment_response(
        task=task, response=mock_response(abstain=True)
    )

    assert result["valid"] is False


def test_clean_abstention_is_accepted(task) -> None:
    result = validate_alignment_response(
        task=task, response=mock_response(abstain=True, selected=[])
    )

    assert result["valid"] is True


def test_collection_validation_reports_a_missing_response(tasks) -> None:
    validated, summary = validate_response_collection(
        tasks=tasks, responses=[mock_response()]
    )

    assert len(validated) == 1
    assert "page:1#f002" in str(summary)


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


def test_manifest_records_the_design(tasks) -> None:
    manifest = experiment_manifest(
        tasks=tasks, model_name="gemini-3.5-flash", temperature=0.0
    )

    assert manifest["experiment"] == "unconstrained_all_competencies"
    assert manifest["candidate_counts_observed"] == [3]
    assert manifest["task_count"] == 2
    assert manifest["temperature"] == 0.0
    assert manifest["maximum_selections"] == 3
    assert manifest["constrained_outputs_overwritten"] is False
    assert manifest["output_location"] == "data/experiments/"


def test_manifest_lists_what_was_held_constant(tasks) -> None:
    manifest = experiment_manifest(
        tasks=tasks, model_name="m", temperature=0.0
    )

    assert set(manifest["held_constant"]) == set(HELD_CONSTANT)
    assert "validator_semantics" in manifest["held_constant"]
    assert "candidate space" in manifest["intended_difference"]
    assert "BM25 score line" in manifest["presentation_difference"]


def test_manifest_carries_validation_and_comparison(tasks) -> None:
    validation = validate_unconstrained_tasks(
        tasks,
        expected_fragment_ids=[f["fragment_id"] for f in FRAGMENTS],
        expected_candidate_count=len(COMPETENCIES),
    )
    comparison = compare_conditions(
        constrained_tasks=[constrained_task(FRAGMENTS[0], ["GI_P1_1"])],
        unconstrained_tasks=tasks,
    )

    manifest = experiment_manifest(
        tasks=tasks,
        model_name="m",
        temperature=0.0,
        validation=validation,
        comparison=comparison,
    )

    assert manifest["validation"]["status"] == "PASSED"
    assert manifest["condition_comparison"]["status"] == "PASSED"
