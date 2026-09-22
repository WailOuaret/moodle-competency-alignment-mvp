"""Fixture tests for post-hoc hierarchy warnings and child-preference ablation.

Temporary files only. No Gemini or Ollama calls.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from moodle_competency.aggregation import aggregate_fragment_predictions
from moodle_competency.graph_checks import (
    HierarchyValidationError,
    apply_child_preference,
    build_hierarchy_index,
    collect_fragment_warnings,
    count_removed_true_reference_labels,
    detect_fragment_warnings,
    evaluate_fragment_predictions,
    get_children,
    get_parent,
    is_ancestor,
    is_direct_parent,
    parent_child_pairs,
    require_valid_hierarchy,
    simulate_child_preference,
    validate_hierarchy,
)
from moodle_competency.llm_validation import write_jsonl


def competencies() -> list[dict]:
    return [
        {"idnumber": "GI_C1", "parent_idnumber": ""},
        {"idnumber": "GI_C1_1", "parent_idnumber": "GI_C1"},
        {"idnumber": "GI_C1_2", "parent_idnumber": "GI_C1"},
        {"idnumber": "GI_C2", "parent_idnumber": ""},
        {"idnumber": "GI_C2_3", "parent_idnumber": "GI_C2"},
        {"idnumber": "GI_C3", "parent_idnumber": ""},
        {"idnumber": "GI_C3_1", "parent_idnumber": "GI_C3"},
    ]


def index():
    return build_hierarchy_index(competencies())


def prediction(fragment_id: str, selected: list[dict]) -> dict:
    return {
        "fragment_id": fragment_id,
        "valid": True,
        "abstain": False,
        "selected": selected,
    }


def sel(idnumber: str, evidence: list[str], confidence: float = 0.9) -> dict:
    return {
        "idnumber": idnumber,
        "evidence": evidence,
        "confidence": confidence,
    }


def test_direct_parent_child_detected() -> None:
    record = prediction(
        "page:1#f001",
        [
            sel("GI_C1", ["same quote"]),
            sel("GI_C1_1", ["same quote"]),
        ],
    )
    warnings = detect_fragment_warnings(record, index())
    types = {item["warning_type"] for item in warnings}

    assert "parent_child_redundancy" in types
    assert "granularity_conflict" in types
    assert parent_child_pairs(["GI_C1", "GI_C1_1"], index()) == [
        ("GI_C1", "GI_C1_1")
    ]


def test_parent_alone_not_redundant() -> None:
    record = prediction("page:1#f001", [sel("GI_C1", ["text"])])
    warnings = detect_fragment_warnings(record, index())

    assert warnings == []


def test_child_alone_not_redundant() -> None:
    record = prediction("page:1#f001", [sel("GI_C1_1", ["text"])])
    warnings = detect_fragment_warnings(record, index())

    assert warnings == []


def test_two_unrelated_children_not_redundant() -> None:
    record = prediction(
        "page:1#f001",
        [
            sel("GI_C1_1", ["a"]),
            sel("GI_C2_3", ["b"]),
        ],
    )
    warnings = detect_fragment_warnings(record, index())

    assert warnings == []


def test_one_parent_two_children() -> None:
    record = prediction(
        "page:1#f001",
        [
            sel("GI_C1", ["q1"]),
            sel("GI_C1_1", ["q2"]),
            sel("GI_C1_2", ["q3"]),
        ],
    )
    pairs = [
        (item["parent_id"], item["child_id"])
        for item in detect_fragment_warnings(record, index())
        if item["warning_type"] == "parent_child_redundancy"
    ]

    assert ("GI_C1", "GI_C1_1") in pairs
    assert ("GI_C1", "GI_C1_2") in pairs


def test_invalid_id_detection() -> None:
    record = prediction("page:1#f001", [sel("GI_UNKNOWN", ["x"])])
    warnings = detect_fragment_warnings(record, index())

    assert warnings[0]["warning_type"] == "invalid_hierarchy_reference"
    assert warnings[0]["child_id"] == "GI_UNKNOWN"


def test_missing_parent_reference() -> None:
    broken = competencies() + [
        {"idnumber": "GI_ORPHAN", "parent_idnumber": "GI_MISSING"}
    ]
    validation = validate_hierarchy(broken)

    assert validation["passed"] is False
    assert validation["missing_parent_references"]

    with pytest.raises(HierarchyValidationError):
        require_valid_hierarchy(validation)


def test_cycle_detection() -> None:
    cyclic = [
        {"idnumber": "A", "parent_idnumber": "B"},
        {"idnumber": "B", "parent_idnumber": "A"},
    ]
    validation = validate_hierarchy(cyclic)

    assert validation["passed"] is False
    assert validation["cycles"]


def test_deterministic_output() -> None:
    records = [
        prediction(
            "page:2#f001",
            [sel("GI_C1", ["z"]), sel("GI_C1_1", ["z"])],
        ),
        prediction(
            "page:1#f001",
            [sel("GI_C3", ["y"]), sel("GI_C3_1", ["y"])],
        ),
    ]
    first = collect_fragment_warnings(records, index())
    second = collect_fragment_warnings(list(reversed(records)), index())

    assert [item["fragment_id"] for item in first] == [
        item["fragment_id"] for item in second
    ]
    assert first[0]["fragment_id"] <= first[-1]["fragment_id"]


def test_child_preference_removes_parent() -> None:
    record = prediction(
        "page:1#f001",
        [
            sel("GI_C1", ["a"]),
            sel("GI_C1_1", ["b"]),
            sel("GI_C1_2", ["c"]),
        ],
    )
    copied, removed = apply_child_preference(record, index())
    ids = [item["idnumber"] for item in copied["selected"]]

    assert removed == ["GI_C1"]
    assert ids == ["GI_C1_1", "GI_C1_2"]
    assert record["selected"][0]["idnumber"] == "GI_C1"


def test_child_preference_preserves_parent_when_alone() -> None:
    record = prediction("page:1#f001", [sel("GI_C1", ["alone"])])
    copied, removed = apply_child_preference(record, index())

    assert removed == []
    assert copied["selected"][0]["idnumber"] == "GI_C1"


def test_child_preference_preserves_unrelated_labels() -> None:
    record = prediction(
        "page:1#f001",
        [
            sel("GI_C1", ["p"]),
            sel("GI_C1_1", ["c"]),
            sel("GI_C2_3", ["other"]),
        ],
    )
    copied, _removed = apply_child_preference(record, index())
    ids = [item["idnumber"] for item in copied["selected"]]

    assert "GI_C1" not in ids
    assert "GI_C1_1" in ids
    assert "GI_C2_3" in ids


def test_input_prediction_object_not_mutated() -> None:
    record = prediction(
        "page:1#f001",
        [sel("GI_C1", ["p"]), sel("GI_C1_1", ["c"])],
    )
    original = copy.deepcopy(record)
    apply_child_preference(record, index())

    assert record == original


def test_original_files_not_modified(tmp_path: Path) -> None:
    path = tmp_path / "gemini_validated.jsonl"
    records = [
        prediction("page:1#f001", [sel("GI_C1", ["p"]), sel("GI_C1_1", ["c"])])
    ]
    write_jsonl(records, path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    loaded = [
        {
            "fragment_id": "page:1#f001",
            "valid": True,
            "abstain": False,
            "selected": [
                sel("GI_C1", ["p"]),
                sel("GI_C1_1", ["c"]),
            ],
        }
    ]
    simulate_child_preference(loaded, index())

    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_simulated_evaluation_correctness() -> None:
    gold_rows = [
        {
            "fragment_id": "page:1#f001",
            "gold_competency_ids": "GI_C1_1",
            "no_competency": "false",
            "ambiguous": "false",
            "annotator": "Wail Ouaret",
            "annotation_date": "2026-09-18",
        }
    ]
    original = [
        prediction(
            "page:1#f001",
            [sel("GI_C1", ["p"]), sel("GI_C1_1", ["c"])],
        )
    ]
    simulated, _stats = simulate_child_preference(original, index())
    metrics = evaluate_fragment_predictions(
        gold_rows,
        simulated,
        competencies(),
        parent_child_redundancy_count=0,
    )

    assert metrics["micro_precision"] == 1.0
    assert metrics["micro_recall"] == 1.0
    assert metrics["exact_set_match"] == 1.0


def test_resource_aggregation_from_simulated_predictions() -> None:
    fragments = [
        {"fragment_id": "page:1#f001", "resource_id": "page:1"},
        {"fragment_id": "page:1#f002", "resource_id": "page:1"},
    ]
    resources = [
        {
            "resource_id": "page:1",
            "resource_type": "page",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "title": "Page",
            "activity_name": "Page",
        }
    ]
    original = [
        prediction(
            "page:1#f001",
            [sel("GI_C1", ["p"]), sel("GI_C1_1", ["c"])],
        ),
        prediction("page:1#f002", [sel("GI_C1_1", ["c2"])]),
    ]
    simulated, _stats = simulate_child_preference(original, index())
    records, manifest = aggregate_fragment_predictions(
        fragments=fragments,
        resources=resources,
        competencies=competencies(),
        predictions=simulated,
    )
    predicted = [
        item["competency_id"]
        for item in records[0]["predicted_competencies"]
    ]

    assert manifest["final"] is True
    assert "GI_C1" not in predicted
    assert "GI_C1_1" in predicted


def test_correct_label_removal_count() -> None:
    gold_rows = [
        {
            "fragment_id": "a",
            "gold_competency_ids": "GI_C1",
            "no_competency": "false",
            "ambiguous": "false",
            "annotator": "Wail Ouaret",
            "annotation_date": "2026-09-18",
        },
        {
            "fragment_id": "b",
            "gold_competency_ids": "GI_C1_1",
            "no_competency": "false",
            "ambiguous": "false",
            "annotator": "Wail Ouaret",
            "annotation_date": "2026-09-18",
        },
    ]
    original = [
        prediction("a", [sel("GI_C1", ["p"]), sel("GI_C1_1", ["c"])]),
        prediction("b", [sel("GI_C1", ["p"]), sel("GI_C1_1", ["c"])]),
    ]
    simulated, _stats = simulate_child_preference(original, index())
    result = count_removed_true_reference_labels(
        gold_rows,
        original,
        simulated,
    )

    assert result["removed_true_reference_labels"] == 1
    assert result["details"][0]["fragment_id"] == "a"


def test_hierarchy_helpers() -> None:
    tree = index()

    assert get_parent("GI_C1_1", tree) == "GI_C1"
    assert get_parent("GI_C1", tree) is None
    assert "GI_C1_1" in get_children("GI_C1", tree)
    assert is_direct_parent("GI_C1", "GI_C1_1", tree) is True
    assert is_ancestor("GI_C1", "GI_C1_1", tree) is True
    assert is_ancestor("GI_C1_1", "GI_C1", tree) is False
    assert is_direct_parent("GI_C1", "GI_C2_3", tree) is False
