"""POST /v1/analyses with the mock backend. No live model is ever called."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from moodle_competency.runtime_storage import frozen_file_hashes
from moodle_competency.settings import PROJECT_ROOT

from service.alignment_adapter import prepare_catalogue
from service.schemas import AnalysisResponse, CompetencyIn
from service_support import (
    AUTH,
    CATALOGUE,
    FRAMEWORK,
    PAGE_TEXT,
    TWO_FRAGMENT_TEXT,
    abstaining,
    build_payload,
    quote_of,
    response as model_response,
    selecting,
    selection,
    with_resource,
)


CATALOGUE_IDS = {item["idnumber"] for item in CATALOGUE}
FLATTENED_PAGE_TEXT = " ".join(PAGE_TEXT.split())


def post(client, payload, headers=AUTH):
    return client.post("/v1/analyses", json=payload, headers=headers)


def parsed(http_response) -> AnalysisResponse:
    assert http_response.status_code == 200, http_response.text
    return AnalysisResponse.model_validate(http_response.json())


# --------------------------------------------------------------------------- #
# The successful contract
# --------------------------------------------------------------------------- #


def test_page_analysis_returns_validated_suggestions(client) -> None:
    body = parsed(post(client, build_payload()))

    assert body.schema_version == "1.0"
    assert body.status == "completed"
    assert body.resource_id == "moodle:page:42"
    assert body.analysis_id.startswith("an_")
    assert 1 <= len(body.suggestions) <= 3
    assert body.abstained is False
    assert body.diagnostics == []

    for suggestion in body.suggestions:
        assert suggestion.competency_idnumber in CATALOGUE_IDS
        assert suggestion.evidence
        assert 1 <= suggestion.bm25_rank <= 5
        assert 0.0 <= suggestion.confidence <= 1.0
        assert suggestion.support_count >= 1

        for evidence in suggestion.evidence:
            assert evidence.fragment_id.startswith("moodle:page:42#f")
            assert evidence.quote in FLATTENED_PAGE_TEXT


def test_manifest_describes_how_the_result_was_produced(client) -> None:
    manifest = parsed(post(client, build_payload())).manifest
    expected_hash = prepare_catalogue(
        [CompetencyIn(**item) for item in CATALOGUE]
    ).content_hash

    assert manifest.backend == "mock"
    assert manifest.model == "mock-deterministic-1"
    assert manifest.prompt_version
    assert manifest.top_k == 5
    assert manifest.max_selections_per_fragment == 3
    assert manifest.competency_catalogue_hash == expected_hash
    assert manifest.resource_hash.startswith("sha256:")
    assert len(manifest.resource_hash) == len("sha256:") + 64
    assert manifest.fragment_count == 1
    assert manifest.completeness == "complete"
    assert manifest.duration_ms >= 0


def test_catalogue_comes_from_the_request_not_the_frozen_experiment(
    make_client,
) -> None:
    catalogue = [
        {
            "idnumber": "ZZ-9",
            "shortname": "Quantum widgets",
            "description_text": "Assemble quantum widgets safely and repeatably.",
            **FRAMEWORK,
        },
        {
            "idnumber": "ZZ-9.1",
            "shortname": "Widget safety",
            "description_text": "Follow safety procedures when assembling widgets.",
            "parent_idnumber": "ZZ-9",
            **FRAMEWORK,
        },
    ]
    body = parsed(
        post(make_client(), build_payload(competencies=catalogue))
    )

    assert body.suggestions
    assert {item.competency_idnumber for item in body.suggestions} <= {
        "ZZ-9",
        "ZZ-9.1",
    }


def test_empty_catalogue_never_falls_back_to_the_frozen_one(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        "service.alignment_adapter.analyze_runtime_resource",
        lambda *args, **kwargs: calls.append(1),
    )

    result = post(client, build_payload(competencies=[]))

    assert result.status_code == 422
    assert result.json()["error"]["code"] == "invalid_request"
    assert calls == []


def test_response_never_carries_prompts_or_model_reasoning(client) -> None:
    text = post(client, build_payload()).text

    for forbidden in (
        "STRICT RULES",
        "FRAGMENT_TEXT",
        "ALLOWED CANDIDATES",
        '"prompt"',
        "raw_response",
        "overall_reason",
        '"reason"',
        "Deterministic mock selection",
        "api_key",
    ):
        assert forbidden not in text


def test_request_id_is_returned_and_reused_when_well_formed(client) -> None:
    echoed = post(
        client,
        build_payload(),
        headers={**AUTH, "X-Request-ID": "moodle-task-123"},
    )
    replaced = post(
        client,
        build_payload(),
        headers={**AUTH, "X-Request-ID": "not valid!"},
    )

    assert echoed.headers["x-request-id"] == "moodle-task-123"
    assert replaced.headers["x-request-id"] != "not valid!"
    assert len(replaced.headers["x-request-id"]) == 32


# --------------------------------------------------------------------------- #
# Model output that must not be accepted
# --------------------------------------------------------------------------- #


def test_model_may_not_select_a_competency_that_does_not_exist(make_client) -> None:
    client = make_client(selecting("NOT-IN-THE-CATALOGUE"))

    result = post(client, build_payload())

    assert result.status_code == 502
    assert result.json()["error"]["code"] == "model_output_invalid"
    assert result.json()["error"]["retryable"] is True
    assert "NOT-IN-THE-CATALOGUE" not in result.text


def test_model_may_not_select_outside_the_bm25_candidates(make_client) -> None:
    extra = [
        {
            "idnumber": f"XX-{index}",
            "shortname": f"Unrelated topic {index}",
            "description_text": f"Unrelated subject number {index}.",
            **FRAMEWORK,
        }
        for index in (1, 2)
    ]
    catalogue = copy.deepcopy(CATALOGUE) + extra

    def outsider(task):
        allowed = set(task["allowed_idnumbers"])
        missing = next(
            item["idnumber"] for item in catalogue if item["idnumber"] not in allowed
        )
        return model_response(task, [selection(missing, quote_of(task))])

    result = post(
        make_client(outsider),
        build_payload(competencies=catalogue),
    )

    assert result.status_code == 502
    assert result.json()["error"]["code"] == "model_output_invalid"


def test_evidence_must_be_an_exact_quotation(make_client) -> None:
    def invented(task):
        allowed = list(task["allowed_idnumbers"])
        return model_response(
            task,
            [selection(allowed[0], "this sentence appears nowhere in the page")],
        )

    result = post(make_client(invented), build_payload())

    assert result.status_code == 502
    assert result.json()["error"]["code"] == "model_output_invalid"


def test_output_that_is_not_json_is_not_accepted(make_client) -> None:
    result = post(make_client(lambda task: "this is not json{"), build_payload())

    assert result.status_code == 502
    assert result.json()["error"]["code"] == "model_output_invalid"


def test_selection_without_evidence_is_not_accepted(make_client) -> None:
    def no_evidence(task):
        allowed = list(task["allowed_idnumbers"])
        return model_response(
            task,
            [{"idnumber": allowed[0], "evidence": [], "reason": "x", "confidence": 0.9}],
        )

    assert post(make_client(no_evidence), build_payload()).status_code == 502


# --------------------------------------------------------------------------- #
# Abstention, partial results and diagnostics
# --------------------------------------------------------------------------- #


def test_abstention_is_reported_without_suggestions(make_client) -> None:
    body = parsed(post(make_client(abstaining()), build_payload()))

    assert body.abstained is True
    assert body.suggestions == []
    assert body.manifest.completeness == "complete"


def test_partial_result_is_marked_and_explained(make_client) -> None:
    def second_fragment_invalid(task):
        allowed = list(task["allowed_idnumbers"])
        quote = quote_of(task)

        if task["fragment_id"].endswith("#f002"):
            return model_response(task, [selection("INVENTED-ID", quote)])

        return model_response(task, [selection(allowed[0], quote)])

    body = parsed(
        post(
            make_client(second_fragment_invalid),
            with_resource(text=TWO_FRAGMENT_TEXT),
        )
    )

    assert body.manifest.fragment_count == 2
    assert body.manifest.completeness == "partial"
    assert body.suggestions
    assert all(
        item.fragment_id.endswith("#f001")
        for suggestion in body.suggestions
        for item in suggestion.evidence
    )
    invalid = [d for d in body.diagnostics if d.code == "fragment_response_invalid"]
    assert len(invalid) == 1
    assert invalid[0].fragment_id.endswith("#f002")
    assert invalid[0].details


def test_hierarchy_warnings_are_structured_and_nothing_is_removed(
    make_client,
) -> None:
    body = parsed(post(make_client(selecting("SE-1", "SE-1.1")), build_payload()))
    by_id = {item.competency_idnumber: item for item in body.suggestions}

    # Neither the parent nor the child is dropped or rewritten.
    assert set(by_id) == {"SE-1", "SE-1.1"}

    parent_codes = {w.code: w for w in by_id["SE-1"].warnings}
    child_codes = {w.code: w for w in by_id["SE-1.1"].warnings}

    assert parent_codes["parent_child_redundancy"].role == "parent"
    assert parent_codes["parent_child_redundancy"].related_idnumber == "SE-1.1"
    assert child_codes["parent_child_redundancy"].role == "child"
    assert child_codes["parent_child_redundancy"].related_idnumber == "SE-1"
    # Same quotation for both, so the engine also flags overlapping evidence.
    assert "granularity_conflict" in parent_codes

    for warning in by_id["SE-1"].warnings + by_id["SE-1.1"].warnings:
        assert "removed" not in warning.message.lower()


def test_unrelated_competencies_carry_no_warning(make_client) -> None:
    body = parsed(post(make_client(selecting("SE-1.1", "DB-1")), build_payload()))

    assert all(item.warnings == [] for item in body.suggestions)


def test_max_suggestions_caps_the_list_and_says_so(make_client) -> None:
    payload = build_payload()
    payload["config"]["max_suggestions"] = 1
    body = parsed(
        post(make_client(selecting("SE-1.1", "SE-1.2", "DB-1")), payload)
    )

    assert len(body.suggestions) == 1
    assert body.abstained is False
    assert [d.code for d in body.diagnostics] == ["suggestions_truncated"]


def test_suggestions_are_ordered_by_support_then_confidence(make_client) -> None:
    confidences = {"SE-1.1": 0.6, "SE-1.2": 0.9, "DB-1": 0.7}

    def varied(task):
        quote = quote_of(task)
        return model_response(
            task,
            [selection(key, quote, value) for key, value in confidences.items()],
        )

    body = parsed(post(make_client(varied), build_payload()))

    assert [item.competency_idnumber for item in body.suggestions] == [
        "SE-1.2",
        "DB-1",
        "SE-1.1",
    ]


def test_retrieval_without_signal_is_reported_and_not_hidden(make_client) -> None:
    payload = with_resource(title="Qqqq zzzz", text="Zzzz qqqq xxxx yyyy.")
    body = parsed(post(make_client(abstaining()), payload))

    assert body.abstained is True
    assert body.suggestions == []
    assert [d.code for d in body.diagnostics] == ["retrieval_no_signal"]


# --------------------------------------------------------------------------- #
# The engine must not touch the frozen experiment or the repository
# --------------------------------------------------------------------------- #


def _runtime_listing() -> set[str]:
    root = Path(PROJECT_ROOT) / "data" / "runtime"
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if "__pycache__" not in path.parts
    }


def test_frozen_experiment_files_and_runtime_data_are_untouched(client) -> None:
    frozen_before = frozen_file_hashes(PROJECT_ROOT)
    runtime_before = _runtime_listing()

    parsed(post(client, build_payload()))

    assert frozen_file_hashes(PROJECT_ROOT) == frozen_before
    assert _runtime_listing() == runtime_before
