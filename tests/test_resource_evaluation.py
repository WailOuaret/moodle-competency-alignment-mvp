"""Fixture tests for derived resource-level evaluation.

Temporary files only. No live Gemini or Ollama calls.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from moodle_competency.llm_validation import write_jsonl
from moodle_competency.resource_evaluation import (
    ResourceReferenceValidationError,
    build_resource_error_examples,
    build_resource_reference,
    evaluate_resource_level,
    has_parent_child_redundancy,
    inspect_sanity_mismatches,
    metrics_payload,
    require_valid_resource_reference,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def competencies() -> list[dict]:
    return [
        {"idnumber": "GI_C1"},
        {"idnumber": "GI_C1_1"},
        {"idnumber": "GI_C1_2"},
        {"idnumber": "GI_C1_3"},
        {"idnumber": "GI_C2"},
        {"idnumber": "GI_C2_3"},
        {"idnumber": "GI_C3"},
        {"idnumber": "GI_C3_1"},
        {"idnumber": "GI_C3_2"},
        {"idnumber": "GI_C3_3"},
        {"idnumber": "GI_X"},
        {"idnumber": "GI_Y"},
        {"idnumber": "GI_Z"},
    ]


def resources() -> list[dict]:
    return [
        {
            "resource_id": "page:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "page",
            "title": "Software Page",
        },
        {
            "resource_id": "quiz_question:1:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "quiz_question",
            "title": "Q1",
        },
        {
            "resource_id": "quiz_question:1:2",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "quiz_question",
            "title": "Q2",
        },
    ]


def gold_rows() -> list[dict]:
    return [
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "gold_competency_ids": "GI_C1_1;GI_C1_2",
        },
        {
            "fragment_id": "page:1#f002",
            "resource_id": "page:1",
            "gold_competency_ids": "GI_C1_1",
        },
        {
            "fragment_id": "quiz_question:1:1#f001",
            "resource_id": "quiz_question:1:1",
            "gold_competency_ids": "GI_C1_1",
        },
        {
            "fragment_id": "quiz_question:1:2#f001",
            "resource_id": "quiz_question:1:2",
            "gold_competency_ids": "GI_C1_3",
        },
    ]


def predictions() -> list[dict]:
    return [
        {
            "resource_id": "page:1",
            "predicted_competencies": [
                {"competency_id": "GI_C1"},
                {"competency_id": "GI_C1_1"},
                {"competency_id": "GI_C1_2"},
            ],
        },
        {
            "resource_id": "quiz_question:1:1",
            "predicted_competencies": [
                {"competency_id": "GI_C1_1"},
            ],
        },
        {
            "resource_id": "quiz_question:1:2",
            "predicted_competencies": [
                {"competency_id": "GI_C1_1"},
            ],
        },
    ]


def test_page_fragment_label_union_deduplicates() -> None:
    records, validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    page = next(item for item in records if item["resource_id"] == "page:1")

    assert validation["passed"] is True
    assert page["reference_competency_ids"] == ["GI_C1_1", "GI_C1_2"]
    assert page["reference_label_count"] == 2
    assert page["reference_derivation"] == (
        "union_of_human_reviewed_fragment_labels"
    )
    assert page["fragment_ids"] == ["page:1#f001", "page:1#f002"]


def test_quiz_question_remains_independent() -> None:
    records, validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    quiz = next(
        item
        for item in records
        if item["resource_id"] == "quiz_question:1:1"
    )
    other = next(
        item
        for item in records
        if item["resource_id"] == "quiz_question:1:2"
    )

    assert validation["passed"] is True
    assert quiz["reference_competency_ids"] == ["GI_C1_1"]
    assert other["reference_competency_ids"] == ["GI_C1_3"]
    assert quiz["reference_derivation"] == (
        "human_reviewed_question_fragment_label"
    )
    assert "GI_C1_3" not in quiz["reference_competency_ids"]


def test_multi_label_fragment_kept_in_union() -> None:
    records, _validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    page = next(item for item in records if item["resource_id"] == "page:1")

    assert "GI_C1_1" in page["reference_competency_ids"]
    assert "GI_C1_2" in page["reference_competency_ids"]


def test_multiple_fragments_same_resource() -> None:
    records, validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    page = next(item for item in records if item["resource_id"] == "page:1")

    assert validation["fragment_count"] == 4
    assert validation["fragments_used_exactly_once"] is True
    assert len(page["fragment_ids"]) == 2


def test_missing_fragment_detection() -> None:
    incomplete = gold_rows()[:-1]
    _records, validation = build_resource_reference(
        gold_rows=incomplete,
        resources=resources(),
        competencies=competencies(),
    )

    assert validation["passed"] is False
    assert "quiz_question:1:2" in validation["missing_resource_ids"]

    with pytest.raises(ResourceReferenceValidationError):
        require_valid_resource_reference(validation)


def test_duplicate_resource_detection() -> None:
    duplicated = resources() + [resources()[0]]
    _records, validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=duplicated,
        competencies=competencies(),
    )

    assert validation["passed"] is False
    assert "page:1" in validation["duplicate_resource_ids"]


def test_unknown_competency_rejection() -> None:
    broken = gold_rows()
    broken[0] = dict(broken[0])
    broken[0]["gold_competency_ids"] = "GI_UNKNOWN"
    _records, validation = build_resource_reference(
        gold_rows=broken,
        resources=resources(),
        competencies=competencies(),
    )

    assert validation["passed"] is False
    assert "GI_UNKNOWN" in validation["unknown_competency_ids"]


def test_per_resource_prf_exact_set_and_label_count_error() -> None:
    records, validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    require_valid_resource_reference(validation)
    evaluation = evaluate_resource_level(
        reference_records=records,
        predictions=predictions(),
        competencies=competencies(),
    )
    by_id = {
        item["resource_id"]: item for item in evaluation["per_resource"]
    }
    page = by_id["page:1"]
    exact_quiz = by_id["quiz_question:1:1"]
    wrong_quiz = by_id["quiz_question:1:2"]

    assert page["precision"] == pytest.approx(2 / 3)
    assert page["recall"] == 1.0
    assert page["exact_set_match"] is False
    assert page["label_count_error"] == 1
    assert page["false_positive_ids"] == ["GI_C1"]
    assert exact_quiz["exact_set_match"] is True
    assert exact_quiz["precision"] == 1.0
    assert exact_quiz["recall"] == 1.0
    assert exact_quiz["label_count_error"] == 0
    assert wrong_quiz["false_negative_ids"] == ["GI_C1_3"]
    assert wrong_quiz["false_positive_ids"] == ["GI_C1_1"]
    assert wrong_quiz["label_count_error"] == 0


def test_macro_all_13_and_gold_supported() -> None:
    records, _validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    evaluation = evaluate_resource_level(
        reference_records=records,
        predictions=predictions(),
        competencies=competencies(),
    )
    all_13 = evaluation["macro_all_13"]
    supported = evaluation["macro_gold_supported_labels"]

    assert evaluation["gold_supported_label_count"] == 3
    assert set(evaluation["gold_supported_label_ids"]) == {
        "GI_C1_1",
        "GI_C1_2",
        "GI_C1_3",
    }
    assert all_13 != supported
    assert supported["precision"] > all_13["precision"]
    assert "GI_C1" in evaluation["zero_gold_support_label_ids"]
    payload = metrics_payload(evaluation)
    assert "macro_all_13" in payload
    assert "macro_gold_supported_labels" in payload
    assert payload["includes_ollama"] is False


def test_micro_prf_on_fixture() -> None:
    records, _validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    evaluation = evaluate_resource_level(
        reference_records=records,
        predictions=predictions(),
        competencies=competencies(),
    )

    # Gold labels: page {C1_1,C1_2}, q1 {C1_1}, q2 {C1_3} = 4
    # Predicted: page {C1,C1_1,C1_2}, q1 {C1_1}, q2 {C1_1}
    # TP=3, FP=2, FN=1
    assert evaluation["micro_true_positives"] == 3
    assert evaluation["micro_false_positives"] == 2
    assert evaluation["micro_false_negatives"] == 1
    assert evaluation["micro_precision"] == pytest.approx(3 / 5)
    assert evaluation["micro_recall"] == pytest.approx(3 / 4)


def test_parent_child_redundancy_and_examples() -> None:
    assert has_parent_child_redundancy(["GI_C1", "GI_C1_1"]) is True
    assert has_parent_child_redundancy(["GI_C1_1", "GI_C1_2"]) is False

    records, _validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )
    evaluation = evaluate_resource_level(
        reference_records=records,
        predictions=predictions(),
        competencies=competencies(),
    )
    examples = build_resource_error_examples(evaluation)
    types = {row["example_type"] for row in examples}

    assert "exact_correct_resource" in types
    assert "overpredicted_page" in types
    assert "parent_child_redundant_resource" in types
    assert "resource_false_negative" in types
    assert "quiz_question_resource" in types
    assert all(row["resource_id"] for row in examples)


def test_no_use_of_manual_moodle_links_in_source() -> None:
    module_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "moodle_competency"
        / "resource_evaluation.py"
    )
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "22_evaluate_resource_level.py"
    )
    combined = (
        module_path.read_text(encoding="utf-8")
        + "\n"
        + script_path.read_text(encoding="utf-8")
    )

    assert ' / "manual_moodle_links.csv"' not in combined
    assert "read_csv(MOODLE_LINKS" not in combined
    records, validation = build_resource_reference(
        gold_rows=gold_rows(),
        resources=resources(),
        competencies=competencies(),
    )

    assert validation["used_manual_moodle_links"] is False
    assert all("moodle_link" not in item for item in records)


def test_no_mutation_of_input_files(tmp_path: Path) -> None:
    gold = gold_rows()
    resource_rows = resources()
    competency_rows = competencies()
    prediction_rows = predictions()
    gold_path = tmp_path / "gold.csv"
    resource_path = tmp_path / "resources.jsonl"
    competency_path = tmp_path / "competencies.jsonl"
    prediction_path = tmp_path / "predictions.jsonl"
    gold_path.write_text("placeholder", encoding="utf-8")
    write_jsonl(resource_rows, resource_path)
    write_jsonl(competency_rows, competency_path)
    write_jsonl(prediction_rows, prediction_path)
    before = {
        resource_path: _hash(resource_path),
        competency_path: _hash(competency_path),
        prediction_path: _hash(prediction_path),
        gold_path: _hash(gold_path),
    }

    records, validation = build_resource_reference(
        gold_rows=gold,
        resources=resource_rows,
        competencies=competency_rows,
    )
    evaluate_resource_level(
        reference_records=records,
        predictions=prediction_rows,
        competencies=competency_rows,
    )
    require_valid_resource_reference(validation)

    assert _hash(resource_path) == before[resource_path]
    assert _hash(competency_path) == before[competency_path]
    assert _hash(prediction_path) == before[prediction_path]
    assert _hash(gold_path) == before[gold_path]
    assert validation["used_manual_moodle_links"] is False


def test_sanity_helper_detects_mismatch() -> None:
    mismatches = inspect_sanity_mismatches(
        {
            "resource_count": 20,
            "micro_precision": 0.1,
            "micro_recall": 0.9583333333,
            "micro_f1": 0.7931034483,
            "exact_set_match": 0.45,
            "average_absolute_label_count_error": 0.50,
            "macro_all_13": {
                "precision": 0.7051,
                "recall": 0.7308,
                "f1": 0.7026,
            },
            "macro_gold_supported_labels": {
                "precision": 0.9167,
                "recall": 0.9500,
                "f1": 0.9133,
            },
        },
        {
            "resource_count": 20,
            "micro_precision": 0.6764705882,
            "micro_recall": 0.9583333333,
            "micro_f1": 0.7931034483,
            "exact_set_match": 0.45,
            "average_absolute_label_count_error": 0.50,
            "macro_all_13": {
                "precision": 0.7051,
                "recall": 0.7308,
                "f1": 0.7026,
            },
            "macro_gold_supported_labels": {
                "precision": 0.9167,
                "recall": 0.9500,
                "f1": 0.9133,
            },
        },
    )

    assert mismatches
    assert mismatches[0].startswith("micro_precision")
