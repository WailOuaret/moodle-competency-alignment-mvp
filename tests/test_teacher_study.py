"""Tests for the Section M evidence-usefulness pilot.

Every test builds its own fixture. No test reads or writes real experimental
data and no test fabricates a human response: responses used here are explicit
test inputs, never values the code invented.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moodle_competency.teacher_study import (
    CONDITIONS,
    DEFAULT_SEED,
    STRATA,
    TeacherStudyError,
    assign_conditions,
    build_candidate_cases,
    build_study_design,
    classify_stratum,
    design_manifest,
    load_study_cases,
    load_study_responses,
    parse_timestamp,
    select_stratified_sample,
    study_label,
    summarize_responses,
    upsert_response,
    validate_response,
    write_study_cases,
    write_study_manifest,
    write_study_responses,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def error_row(
    fragment_id: str,
    *,
    gold: str,
    predicted: str,
    correct: bool = False,
    redundancy: bool = False,
    resource_type: str = "page",
    course: str = "MVP-SW",
) -> dict[str, str]:
    return {
        "fragment_id": fragment_id,
        "resource_id": fragment_id.split("#")[0],
        "resource_type": resource_type,
        "course_shortname": course,
        "gold_competency_ids": gold,
        "predicted_competency_ids": predicted,
        "correct_prediction": str(correct).lower(),
        "parent_child_redundancy": str(redundancy).lower(),
    }


def evidence_row(fragment_id: str, competency_id: str, quote: str) -> dict[str, str]:
    return {
        "fragment_id": fragment_id,
        "competency_id": competency_id,
        "competency_shortname": f"Name of {competency_id}",
        "fragment_text": f"Full text of {fragment_id}.",
        "evidence_quote": quote,
        "mechanically_valid": "true",
        "pedagogical_rating": "2",
    }


@pytest.fixture()
def error_rows() -> list[dict[str, str]]:
    return [
        error_row("page:1#f001", gold="GI_C1_1", predicted="GI_C1_1", correct=True),
        error_row(
            "page:1#f002",
            gold="GI_C1_1",
            predicted="GI_C1;GI_C1_1",
            redundancy=True,
        ),
        error_row("page:2#f001", gold="GI_C2_1", predicted="GI_C2_3"),
        error_row(
            "quiz_question:1:1#f001",
            gold="GI_C3_2",
            predicted="GI_C3_2",
            correct=True,
            resource_type="quiz_question",
            course="MVP-DATA",
        ),
        error_row(
            "quiz_question:1:2#f001",
            gold="GI_C3_3",
            predicted="GI_C3;GI_C3_3",
            redundancy=True,
            resource_type="quiz_question",
            course="MVP-DATA",
        ),
        error_row(
            "quiz_question:1:3#f001",
            gold="GI_C3_1",
            predicted="GI_C3_2",
            resource_type="quiz_question",
            course="MVP-DATA",
        ),
    ]


@pytest.fixture()
def evidence_rows() -> list[dict[str, str]]:
    return [
        evidence_row("page:1#f001", "GI_C1_1", "quote one"),
        evidence_row("page:1#f002", "GI_C1", "quote two"),
        evidence_row("page:1#f002", "GI_C1_1", "quote three"),
        evidence_row("page:2#f001", "GI_C2_3", "quote four"),
        evidence_row("quiz_question:1:1#f001", "GI_C3_2", "quote five"),
        evidence_row("quiz_question:1:2#f001", "GI_C3", "quote six"),
        evidence_row("quiz_question:1:2#f001", "GI_C3_3", "quote seven"),
        evidence_row("quiz_question:1:3#f001", "GI_C3_2", "quote eight"),
    ]


# --------------------------------------------------------------------------
# Stratification
# --------------------------------------------------------------------------


def test_classify_stratum_prefers_redundancy_then_correct() -> None:
    assert (
        classify_stratum({"parent_child_redundancy": "true", "correct_prediction": "true"})
        == "parent_child_redundancy"
    )
    assert (
        classify_stratum({"parent_child_redundancy": "false", "correct_prediction": "true"})
        == "correct_prediction"
    )
    assert (
        classify_stratum({"parent_child_redundancy": "false", "correct_prediction": "false"})
        == "incorrect_prediction"
    )


def test_strata_are_the_documented_three() -> None:
    assert set(STRATA) == {
        "parent_child_redundancy",
        "incorrect_prediction",
        "correct_prediction",
    }


# --------------------------------------------------------------------------
# Candidate cases
# --------------------------------------------------------------------------


def test_candidates_are_one_per_fragment_competency_pair(
    error_rows, evidence_rows
) -> None:
    cases = build_candidate_cases(error_rows, evidence_rows)

    assert len(cases) == len(evidence_rows)
    assert cases[0]["case_id"] == "page:1#f001|GI_C1_1"


def test_candidate_without_evidence_is_skipped(error_rows, evidence_rows) -> None:
    trimmed = [row for row in evidence_rows if row["competency_id"] != "GI_C1"]
    cases = build_candidate_cases(error_rows, trimmed)

    assert all(case["case_id"] != "page:1#f002|GI_C1" for case in cases)


def test_candidate_records_correctness_against_the_reference(
    error_rows, evidence_rows
) -> None:
    cases = {c["case_id"]: c for c in build_candidate_cases(error_rows, evidence_rows)}

    assert cases["page:1#f001|GI_C1_1"]["model_is_correct"] == "true"
    assert cases["page:1#f002|GI_C1"]["model_is_correct"] == "false"
    assert cases["page:1#f002|GI_C1"]["parent_child_redundancy"] == "true"


def test_candidate_uses_supplied_shortnames(error_rows, evidence_rows) -> None:
    cases = build_candidate_cases(
        error_rows, evidence_rows, {"GI_C1_1": "Overridden name"}
    )
    first = next(c for c in cases if c["competency_id"] == "GI_C1_1")

    assert first["competency_shortname"] == "Overridden name"


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------


def test_sample_is_reproducible_for_a_fixed_seed(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)

    first = select_stratified_sample(candidates, sample_size=6, seed=DEFAULT_SEED)
    second = select_stratified_sample(candidates, sample_size=6, seed=DEFAULT_SEED)

    assert [c["case_id"] for c in first] == [c["case_id"] for c in second]


def test_different_seeds_may_select_differently(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)

    first = select_stratified_sample(candidates, sample_size=3, seed=1)
    second = select_stratified_sample(candidates, sample_size=3, seed=999)

    assert len(first) == len(second) == 3


def test_sample_spans_every_available_stratum(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    sample = select_stratified_sample(candidates, sample_size=3, seed=DEFAULT_SEED)

    assert {case["stratum"] for case in sample} == set(STRATA)


def test_sample_spans_both_courses_and_both_types(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    sample = select_stratified_sample(candidates, sample_size=6, seed=DEFAULT_SEED)

    assert {case["course_shortname"] for case in sample} == {"MVP-SW", "MVP-DATA"}
    assert {case["resource_type"] for case in sample} == {"page", "quiz_question"}


def test_sample_larger_than_population_returns_everything(
    error_rows, evidence_rows
) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    sample = select_stratified_sample(candidates, sample_size=999, seed=DEFAULT_SEED)

    assert len(sample) == len(candidates)


def test_sample_size_must_be_positive(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)

    with pytest.raises(TeacherStudyError, match="positive"):
        select_stratified_sample(candidates, sample_size=0)


def test_sampling_does_not_mutate_the_input(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    snapshot = [dict(case) for case in candidates]

    select_stratified_sample(candidates, sample_size=4, seed=DEFAULT_SEED)

    assert candidates == snapshot


# --------------------------------------------------------------------------
# Condition assignment
# --------------------------------------------------------------------------


def test_conditions_are_assigned_to_every_case(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    assigned = assign_conditions(candidates, seed=DEFAULT_SEED)

    assert len(assigned) == len(candidates)
    assert all(case["condition"] in CONDITIONS for case in assigned)


def test_condition_assignment_is_reproducible(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)

    first = assign_conditions(candidates, seed=DEFAULT_SEED)
    second = assign_conditions(candidates, seed=DEFAULT_SEED)

    assert [(c["case_id"], c["condition"]) for c in first] == [
        (c["case_id"], c["condition"]) for c in second
    ]


def test_conditions_are_balanced_within_each_stratum(
    error_rows, evidence_rows
) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    assigned = assign_conditions(candidates, seed=DEFAULT_SEED)

    for stratum in STRATA:
        rows = [c for c in assigned if c["stratum"] == stratum]

        if not rows:
            continue

        counts = {
            condition: sum(1 for c in rows if c["condition"] == condition)
            for condition in CONDITIONS
        }
        assert abs(counts["A"] - counts["B"]) <= 1


def test_assignment_does_not_mutate_the_input(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    snapshot = [dict(case) for case in candidates]

    assign_conditions(candidates, seed=DEFAULT_SEED)

    assert candidates == snapshot


# --------------------------------------------------------------------------
# Design and manifest
# --------------------------------------------------------------------------


def test_build_study_design_returns_cases_and_manifest(
    error_rows, evidence_rows
) -> None:
    design = build_study_design(
        error_rows, evidence_rows, sample_size=6, seed=DEFAULT_SEED
    )

    assert len(design["cases"]) == 6
    manifest = design["manifest"]
    assert manifest["seed"] == DEFAULT_SEED
    assert manifest["sampled_case_count"] == 6
    assert manifest["candidate_case_count"] == len(evidence_rows)
    assert set(manifest["condition_counts"]) <= set(CONDITIONS)
    assert manifest["case_ids"] == [c["case_id"] for c in design["cases"]]


def test_manifest_records_strata_and_coverage(error_rows, evidence_rows) -> None:
    candidates = build_candidate_cases(error_rows, evidence_rows)
    sample = assign_conditions(
        select_stratified_sample(candidates, sample_size=6, seed=DEFAULT_SEED),
        seed=DEFAULT_SEED,
    )
    manifest = design_manifest(sample, candidates, seed=DEFAULT_SEED, sample_size=6)

    assert set(manifest["course_counts"]) == {"MVP-SW", "MVP-DATA"}
    assert set(manifest["resource_type_counts"]) == {"page", "quiz_question"}
    assert "Not a controlled study" in manifest["interpretation_note"]


def test_design_is_reproducible_end_to_end(error_rows, evidence_rows) -> None:
    first = build_study_design(error_rows, evidence_rows, sample_size=5, seed=7)
    second = build_study_design(error_rows, evidence_rows, sample_size=5, seed=7)

    assert [(c["case_id"], c["condition"]) for c in first["cases"]] == [
        (c["case_id"], c["condition"]) for c in second["cases"]
    ]


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def test_cases_and_manifest_round_trip(tmp_path: Path, error_rows, evidence_rows) -> None:
    design = build_study_design(error_rows, evidence_rows, sample_size=4, seed=3)

    cases_path = write_study_cases(design["cases"], tmp_path / "cases.csv")
    manifest_path = write_study_manifest(design["manifest"], tmp_path / "manifest.json")

    reloaded = load_study_cases(cases_path)
    assert [c["case_id"] for c in reloaded] == [
        c["case_id"] for c in design["cases"]
    ]

    stored = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert stored["seed"] == 3


def test_loading_absent_files_is_empty(tmp_path: Path) -> None:
    assert load_study_cases(tmp_path / "absent.csv") == []
    assert load_study_responses(tmp_path / "absent.csv") == []


def test_responses_round_trip(tmp_path: Path) -> None:
    response = validate_response(**_response_kwargs())
    path = write_study_responses([response], tmp_path / "responses.csv")

    reloaded = load_study_responses(path)
    assert reloaded[0]["case_id"] == response["case_id"]
    assert reloaded[0]["elapsed_seconds"] == response["elapsed_seconds"]


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------


def _response_kwargs(**overrides):
    kwargs = {
        "case_id": "page:1#f001|GI_C1_1",
        "condition": "B",
        "reviewer": "Test Reviewer",
        "reviewer_role": "teacher",
        "decision": "accept",
        "confidence": 4,
        "evidence_shown": True,
        "evidence_opened": True,
        "start_timestamp": "2026-09-22T10:00:00+00:00",
        "end_timestamp": "2026-09-22T10:00:42+00:00",
        "comment": "Clear enough.",
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_response_computes_elapsed_seconds() -> None:
    response = validate_response(**_response_kwargs())

    assert response["elapsed_seconds"] == "42.000"
    assert response["condition"] == "B"
    assert response["confidence"] == "4"


def test_response_rejects_unknown_case_id() -> None:
    with pytest.raises(TeacherStudyError, match="Unknown case_id"):
        validate_response(**_response_kwargs(valid_case_ids=["other|GI_C1"]))


def test_response_rejects_bad_condition() -> None:
    with pytest.raises(TeacherStudyError, match="condition must be one of"):
        validate_response(**_response_kwargs(condition="C"))


def test_response_requires_reviewer_and_role() -> None:
    with pytest.raises(TeacherStudyError, match="reviewer is required"):
        validate_response(**_response_kwargs(reviewer="  "))

    with pytest.raises(TeacherStudyError, match="reviewer_role must be"):
        validate_response(**_response_kwargs(reviewer_role="student"))


def test_response_rejects_bad_decision() -> None:
    with pytest.raises(TeacherStudyError, match="decision must be one of"):
        validate_response(**_response_kwargs(decision="maybe"))


@pytest.mark.parametrize("value", [0, 6, "high", None])
def test_response_rejects_confidence_outside_1_to_5(value) -> None:
    with pytest.raises(TeacherStudyError, match="confidence"):
        validate_response(**_response_kwargs(confidence=value))


@pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
def test_response_accepts_confidence_1_to_5(value) -> None:
    assert validate_response(**_response_kwargs(confidence=value))["confidence"] == str(
        value
    )


def test_response_rejects_reversed_timestamps() -> None:
    with pytest.raises(TeacherStudyError, match="before start_timestamp"):
        validate_response(
            **_response_kwargs(
                start_timestamp="2026-09-22T10:01:00+00:00",
                end_timestamp="2026-09-22T10:00:00+00:00",
            )
        )


def test_response_rejects_malformed_timestamp() -> None:
    with pytest.raises(TeacherStudyError, match="ISO-8601"):
        validate_response(**_response_kwargs(start_timestamp="yesterday"))


def test_parse_timestamp_assumes_utc_when_naive() -> None:
    parsed = parse_timestamp("2026-09-22T10:00:00", "start_timestamp")

    assert parsed.tzinfo is not None


def test_evidence_flags_are_recorded_not_inferred() -> None:
    hidden = validate_response(
        **_response_kwargs(condition="A", evidence_shown=False, evidence_opened=False)
    )

    assert hidden["evidence_shown"] == "false"
    assert hidden["evidence_opened"] == "false"


def test_upsert_replaces_same_case_and_reviewer() -> None:
    first = validate_response(**_response_kwargs(decision="accept"))
    second = validate_response(**_response_kwargs(decision="reject"))

    updated = upsert_response([first], second)

    assert len(updated) == 1
    assert updated[0]["decision"] == "reject"


def test_upsert_keeps_a_second_reviewer_separate() -> None:
    first = validate_response(**_response_kwargs(reviewer="Reviewer One"))
    second = validate_response(**_response_kwargs(reviewer="Reviewer Two"))

    assert len(upsert_response([first], second)) == 2


def test_upsert_does_not_mutate_input() -> None:
    first = validate_response(**_response_kwargs())
    snapshot = [dict(first)]

    upsert_response([first], validate_response(**_response_kwargs(decision="reject")))

    assert [first] == snapshot


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------


def test_summary_without_responses_reports_waiting_and_no_rates() -> None:
    summary = summarize_responses([], cases=[{"case_id": "x"}])

    assert summary["status"] == "WAITING_FOR_HUMAN"
    assert summary["response_count"] == 0
    assert summary["study_label"] is None

    for condition in CONDITIONS:
        block = summary["by_condition"][condition]
        assert block["n"] == 0
        assert block["acceptance_rate"] is None
        assert block["median_elapsed_seconds"] is None


def test_summary_computes_descriptives_by_condition() -> None:
    responses = [
        validate_response(
            **_response_kwargs(
                case_id="c1",
                condition="A",
                decision="accept",
                confidence=3,
                end_timestamp="2026-09-22T10:01:00+00:00",
            )
        ),
        validate_response(
            **_response_kwargs(
                case_id="c2",
                condition="A",
                decision="reject",
                confidence=5,
                end_timestamp="2026-09-22T10:00:30+00:00",
            )
        ),
        validate_response(
            **_response_kwargs(
                case_id="c3",
                condition="B",
                decision="accept",
                confidence=4,
                end_timestamp="2026-09-22T10:00:20+00:00",
            )
        ),
    ]

    summary = summarize_responses(responses)

    assert summary["status"] == "COMPLETE"
    assert summary["response_count"] == 3

    condition_a = summary["by_condition"]["A"]
    assert condition_a["n"] == 2
    assert condition_a["acceptance_rate"] == 0.5
    assert condition_a["median_elapsed_seconds"] == 45.0
    assert condition_a["median_confidence"] == 4.0

    condition_b = summary["by_condition"]["B"]
    assert condition_b["n"] == 1
    assert condition_b["acceptance_rate"] == 1.0
    assert condition_b["median_elapsed_seconds"] == 20.0


def test_summary_never_runs_significance_tests() -> None:
    summary = summarize_responses(
        [validate_response(**_response_kwargs())]
    )

    assert summary["significance_tests"] == "not_run"
    assert "do not support" in summary["significance_tests_note"]


def test_study_label_is_researcher_pilot_without_a_teacher() -> None:
    researcher_only = [
        validate_response(**_response_kwargs(reviewer_role="researcher"))
    ]

    assert study_label(researcher_only) == "researcher pilot"
    assert summarize_responses(researcher_only)["study_label"] == "researcher pilot"


@pytest.mark.parametrize("role", ["teacher", "supervisor"])
def test_study_label_upgrades_when_a_real_teacher_takes_part(role: str) -> None:
    responses = [
        validate_response(**_response_kwargs(reviewer_role="researcher")),
        validate_response(
            **_response_kwargs(case_id="c2", reviewer="Other", reviewer_role=role)
        ),
    ]

    assert study_label(responses) == "teacher/supervisor pilot"


def test_summary_counts_reviewer_roles_honestly() -> None:
    responses = [
        validate_response(**_response_kwargs(reviewer_role="researcher")),
        validate_response(
            **_response_kwargs(case_id="c2", reviewer="Teach", reviewer_role="teacher")
        ),
    ]

    summary = summarize_responses(responses)

    assert summary["reviewer_roles"] == {"researcher": 1, "teacher": 1}
    assert summary["reviewers"] == ["Teach", "Test Reviewer"]


def test_summary_counts_evidence_opened() -> None:
    responses = [
        validate_response(
            **_response_kwargs(condition="A", evidence_shown=False, evidence_opened=True)
        ),
        validate_response(
            **_response_kwargs(
                case_id="c2",
                condition="A",
                evidence_shown=False,
                evidence_opened=False,
            )
        ),
    ]

    assert summarize_responses(responses)["by_condition"]["A"]["evidence_opened_count"] == 1


def test_sampling_rotates_across_courses_within_a_stratum() -> None:
    """One course must not crowd out another inside the same stratum."""

    rows = []
    evidence = []

    # Nine MVP-SW incorrect cases against three MVP-DATA ones.
    for index in range(9):
        fragment_id = f"page:{index}#f001"
        rows.append(
            error_row(fragment_id, gold="GI_C2_1", predicted="GI_C2_3", course="MVP-SW")
        )
        evidence.append(evidence_row(fragment_id, "GI_C2_3", f"quote sw {index}"))

    for index in range(3):
        fragment_id = f"quiz_question:9:{index}#f001"
        rows.append(
            error_row(
                fragment_id,
                gold="GI_C3_1",
                predicted="GI_C3_2",
                course="MVP-DATA",
                resource_type="quiz_question",
            )
        )
        evidence.append(evidence_row(fragment_id, "GI_C3_2", f"quote data {index}"))

    candidates = build_candidate_cases(rows, evidence)
    sample = select_stratified_sample(candidates, sample_size=6, seed=DEFAULT_SEED)

    counts = {
        course: sum(1 for c in sample if c["course_shortname"] == course)
        for course in ("MVP-SW", "MVP-DATA")
    }

    # Strict alternation is possible here, so expect an even split.
    assert counts == {"MVP-SW": 3, "MVP-DATA": 3}


def test_sampling_does_not_stall_when_one_course_runs_out() -> None:
    rows = []
    evidence = []

    for index in range(5):
        fragment_id = f"page:{index}#f001"
        rows.append(
            error_row(fragment_id, gold="GI_C2_1", predicted="GI_C2_3", course="MVP-SW")
        )
        evidence.append(evidence_row(fragment_id, "GI_C2_3", f"quote {index}"))

    fragment_id = "quiz_question:9:1#f001"
    rows.append(
        error_row(
            fragment_id,
            gold="GI_C3_1",
            predicted="GI_C3_2",
            course="MVP-DATA",
            resource_type="quiz_question",
        )
    )
    evidence.append(evidence_row(fragment_id, "GI_C3_2", "only data quote"))

    candidates = build_candidate_cases(rows, evidence)
    sample = select_stratified_sample(candidates, sample_size=6, seed=DEFAULT_SEED)

    assert len(sample) == 6
