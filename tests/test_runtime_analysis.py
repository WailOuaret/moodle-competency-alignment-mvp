"""Runtime analysis tests with injectable mock backends. No live models."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from moodle_competency.resource_ingestion import ingest_pasted_text
from moodle_competency.runtime_analysis import (
    InvalidModelJsonError,
    MockAlignmentBackend,
    analyze_runtime_resource,
    fragment_runtime_resource,
    load_competencies,
)
from moodle_competency.runtime_storage import (
    frozen_file_hashes,
    runtime_paths,
)
from moodle_competency.retrieval import retrieve_candidates
from moodle_competency.settings import PROJECT_ROOT


PASTE_TEXT = (
    "Software verification includes testing software against specified "
    "requirements. User testing can also evaluate interface usability."
)


def _quote(text: str, size: int = 32) -> str:
    return text[: min(size, len(text))]


def _selection(idnumber: str, quote: str, confidence: float = 0.9) -> dict:
    return {
        "idnumber": idnumber,
        "evidence": [quote],
        "reason": "Exact quote from the fragment.",
        "confidence": confidence,
    }


def _response(task, selected, *, abstain: bool = False) -> dict:
    return {
        "fragment_id": task["fragment_id"],
        "selected": selected,
        "abstain": abstain,
        "overall_reason": "Mock constrained alignment response.",
    }


def _first_allowed_backend(quote_from_task: bool = True) -> MockAlignmentBackend:
    def handler(task):
        allowed = list(task["allowed_idnumbers"])
        quote = _quote(str(task["fragment_text"]))
        return _response(task, [_selection(allowed[0], quote)])

    return MockAlignmentBackend(handler)


def test_fragment_provenance() -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")
    fragments = fragment_runtime_resource(resource)

    assert fragments
    fragment = fragments[0]
    assert fragment["fragment_id"]
    assert fragment["runtime_resource_id"] == resource["runtime_resource_id"]
    assert fragment["fragment_index"] == 1
    assert fragment["text"]
    assert fragment["source_structure"] == "paragraph"
    assert fragment["content_hash"]
    assert fragment["start_offset"] is not None
    assert fragment["end_offset"] is not None


def test_bm25_top5_retrieval() -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")
    fragments = fragment_runtime_resource(resource)
    competencies = load_competencies()
    candidate_sets = retrieve_candidates(
        fragments=fragments,
        competencies=competencies,
        top_k=5,
    )

    assert len(candidate_sets) == len(fragments)
    candidates = candidate_sets[0]["candidates"]
    assert len(candidates) == 5
    assert [item["rank"] for item in candidates] == [1, 2, 3, 4, 5]
    assert all(item["idnumber"] for item in candidates)


def test_mock_constrained_llm_and_e2e(tmp_path: Path) -> None:
    before = frozen_file_hashes(PROJECT_ROOT)
    resource = ingest_pasted_text(PASTE_TEXT, title="Verification notes")
    stages: list[str] = []

    def progress(index: int, label: str) -> None:
        stages.append(label)

    analysis = analyze_runtime_resource(
        resource,
        backend=_first_allowed_backend(),
        persist=True,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
        progress=progress,
    )

    assert stages[0] == "Extracting text"
    assert "Fragmenting resource" in stages
    assert "Retrieving competency candidates" in stages
    assert "Running competency alignment" in stages
    assert "Validating evidence" in stages
    assert "Checking hierarchy" in stages
    assert "Aggregating resource competencies" in stages
    assert analysis["backend"] == "mock"
    assert analysis["temperature"] == 0
    assert analysis["candidate_count"] == 5
    assert analysis["max_selections"] == 3
    assert analysis["fragments"]
    assert analysis["retrieval"][0]["candidates"]
    assert analysis["validated_predictions"][0]["valid"] is True
    assert analysis["original_aggregation"]
    assert analysis["suggestion_cards"]
    assert analysis["manifest"]["analysis_id"] == analysis["analysis_id"]
    manifest_path = (
        tmp_path / "data" / "runtime" / "manifests" / f"{analysis['analysis_id']}.json"
    )
    assert manifest_path.exists()
    after = frozen_file_hashes(PROJECT_ROOT)
    assert after == before


def test_invalid_json_handling(tmp_path: Path) -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")
    backend = MockAlignmentBackend(lambda task: "not-json{")
    analysis = analyze_runtime_resource(
        resource,
        backend=backend,
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    record = analysis["validated_predictions"][0]
    assert record["valid"] is False
    assert any("JSON" in error for error in record["errors"])


def test_competency_outside_top5_rejected(tmp_path: Path) -> None:
    competencies = load_competencies()
    catalogue = [str(item["idnumber"]) for item in competencies]
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")

    def handler(task):
        allowed = set(task["allowed_idnumbers"])
        outsider = next(item for item in catalogue if item not in allowed)
        quote = _quote(str(task["fragment_text"]))
        return _response(task, [_selection(outsider, quote)])

    analysis = analyze_runtime_resource(
        resource,
        backend=MockAlignmentBackend(handler),
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    record = analysis["validated_predictions"][0]
    assert record["valid"] is False
    assert any("outside" in error for error in record["validation_errors"])


def test_non_exact_evidence_rejected(tmp_path: Path) -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")

    def handler(task):
        allowed = list(task["allowed_idnumbers"])
        return _response(
            task,
            [_selection(allowed[0], "this quote is not in the fragment xyz")],
        )

    analysis = analyze_runtime_resource(
        resource,
        backend=MockAlignmentBackend(handler),
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    record = analysis["validated_predictions"][0]
    assert record["valid"] is False
    assert any("substring" in error for error in record["validation_errors"])


def test_abstention(tmp_path: Path) -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")

    def handler(task):
        return _response(task, [], abstain=True)

    analysis = analyze_runtime_resource(
        resource,
        backend=MockAlignmentBackend(handler),
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    record = analysis["validated_predictions"][0]
    assert record["valid"] is True
    assert record["abstain"] is True
    assert record["selected"] == []
    assert analysis["suggestion_cards"] == []


def test_multi_label_response(tmp_path: Path) -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")

    def handler(task):
        allowed = list(task["allowed_idnumbers"])
        quote = _quote(str(task["fragment_text"]))
        return _response(
            task,
            [
                _selection(allowed[0], quote, 0.91),
                _selection(allowed[1], quote, 0.82),
            ],
        )

    analysis = analyze_runtime_resource(
        resource,
        backend=MockAlignmentBackend(handler),
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    record = analysis["validated_predictions"][0]
    assert record["valid"] is True
    assert len(record["selected"]) == 2


def test_hierarchy_warning_and_child_preference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    competencies = load_competencies()

    def stub_retrieve(*, fragments, competencies, top_k=5):
        fragment = fragments[0]
        ids = ["GI_C1", "GI_C1_2", "GI_C1_3", "GI_C1_1", "GI_C2"]
        candidates = []

        for rank, idnumber in enumerate(ids, start=1):
            competency = next(
                item for item in competencies if item["idnumber"] == idnumber
            )
            candidates.append(
                {
                    "rank": rank,
                    "competency_id": competency.get("competency_id"),
                    "idnumber": idnumber,
                    "shortname": competency.get("shortname"),
                    "parent_competency_id": competency.get("parent_competency_id"),
                    "parent_idnumber": competency.get("parent_idnumber"),
                    "depth": competency.get("depth"),
                    "bm25_score": 2.0 - rank * 0.1,
                }
            )

        return [
            {
                "fragment_id": fragment["fragment_id"],
                "resource_id": fragment["resource_id"],
                "resource_type": fragment.get("resource_type"),
                "fragment_type": fragment.get("fragment_type"),
                "course_id": fragment.get("course_id"),
                "course_shortname": fragment.get("course_shortname"),
                "course_module_id": fragment.get("course_module_id"),
                "activity_id": fragment.get("activity_id"),
                "activity_name": fragment.get("activity_name"),
                "title": fragment.get("title"),
                "fragment_text": fragment.get("text"),
                "candidates": candidates,
            }
        ]

    monkeypatch.setattr(
        "moodle_competency.runtime_analysis.retrieve_candidates",
        stub_retrieve,
    )
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")

    def handler(task):
        quote = _quote(str(task["fragment_text"]))
        return _response(
            task,
            [
                _selection("GI_C1", quote, 0.7),
                _selection("GI_C1_2", quote, 0.91),
            ],
        )

    original_resource = copy.deepcopy(resource)
    analysis = analyze_runtime_resource(
        resource,
        backend=MockAlignmentBackend(handler),
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    original_ids = [
        item["idnumber"]
        for item in analysis["validated_predictions"][0]["selected"]
    ]
    reconciled_ids = [
        item["idnumber"]
        for item in analysis["reconciled_predictions"][0]["selected"]
    ]

    assert original_ids == ["GI_C1", "GI_C1_2"]
    assert reconciled_ids == ["GI_C1_2"]
    assert analysis["fragment_warnings"]
    assert any(
        warning["warning_type"] in {
            "parent_child_redundancy",
            "granularity_mismatch",
        }
        for warning in analysis["fragment_warnings"]
    )
    assert analysis["validated_predictions"][0]["selected"][0]["idnumber"] == "GI_C1"
    assert original_resource["text"] == resource["text"]
    original_card = next(
        card
        for card in analysis["suggestion_cards"]
        if card["competency_id"] == "GI_C1"
    )
    assert original_card["original_prediction"] is True
    assert original_card["reconciled_prediction"] is False


def test_resource_aggregation(tmp_path: Path) -> None:
    resource = ingest_pasted_text(PASTE_TEXT, title="Notes")
    analysis = analyze_runtime_resource(
        resource,
        backend=_first_allowed_backend(),
        persist=False,
        paths=runtime_paths(tmp_path),
        project_root=tmp_path,
    )
    aggregated = analysis["original_aggregation"][0]
    predicted = aggregated["predicted_competencies"]
    assert predicted
    first = predicted[0]
    assert first["competency_id"]
    assert first["fragment_ids"]
    assert first["support_count"] >= 1
    assert first["evidence"]


def test_mock_align_raises_for_string() -> None:
    backend = MockAlignmentBackend(lambda task: "nope")

    with pytest.raises(InvalidModelJsonError):
        backend.align({"fragment_id": "x"})
