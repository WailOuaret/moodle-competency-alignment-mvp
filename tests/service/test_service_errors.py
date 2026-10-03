"""Failure handling: every failure is serialised safely and none leaks internals."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from moodle_competency.runtime_analysis import (
    NoUsableFragmentsError,
    RuntimeAnalysisError,
    analyze_runtime_resource as real_analyze,
)

from service_support import AUTH, build_payload


def post(client, payload=None, headers=AUTH):
    return client.post("/v1/analyses", json=payload or build_payload(), headers=headers)


def patch_engine(monkeypatch: pytest.MonkeyPatch, replacement) -> None:
    monkeypatch.setattr(
        "service.alignment_adapter.analyze_runtime_resource",
        replacement,
    )


class UnavailableBackend:
    """A backend whose provider cannot be reached (no key, offline, quota)."""

    backend_name = "gemini"
    model = "unavailable-model"
    temperature = 0.0
    prompt_version = "1.0"

    def is_available(self) -> tuple[bool, str]:
        return False, "Gemini backend unavailable. key=SECRET-PROVIDER-DETAIL"

    def align(self, task: Mapping[str, Any]):  # pragma: no cover - never reached
        raise AssertionError("align must not be called when unavailable")


def test_unavailable_backend_is_a_retryable_503(make_client) -> None:
    result = post(make_client(backend=UnavailableBackend()))
    error = result.json()["error"]

    assert result.status_code == 503
    assert error["code"] == "backend_unavailable"
    assert error["retryable"] is True
    assert "SECRET-PROVIDER-DETAIL" not in result.text
    assert "Gemini" not in result.text


def test_unexpected_failure_is_serialised_without_internals(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    def explode(*args, **kwargs):
        raise RuntimeError("boom /home/someone/secret/path.py INTERNAL-MARKER")

    patch_engine(monkeypatch, explode)

    result = post(client)
    error = result.json()["error"]

    assert result.status_code == 500
    assert error["code"] == "internal_error"
    assert error["request_id"] == result.headers["x-request-id"]

    for forbidden in ("boom", "/home/", "INTERNAL-MARKER", "Traceback", "RuntimeError"):
        assert forbidden not in result.text


def test_engine_runtime_error_is_reported_as_analysis_failed(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    def fail(*args, **kwargs):
        raise RuntimeAnalysisError("internal engine detail")

    patch_engine(monkeypatch, fail)

    result = post(client)

    assert result.status_code == 500
    assert result.json()["error"]["code"] == "analysis_failed"
    assert "internal engine detail" not in result.text


def test_engine_rejection_of_the_input_is_a_422(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    def reject(*args, **kwargs):
        raise ValueError("Fragment has no usable BM25 query tokens: x#f001")

    patch_engine(monkeypatch, reject)

    result = post(client)

    assert result.status_code == 422
    assert result.json()["error"]["code"] == "engine_input_rejected"
    assert "BM25" not in result.text


def test_resource_without_fragments_is_a_422(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    def nothing(*args, **kwargs):
        raise NoUsableFragmentsError("Fragmentation returned no usable fragments.")

    patch_engine(monkeypatch, nothing)

    result = post(client)

    assert result.status_code == 422
    assert result.json()["error"]["code"] == "no_usable_fragments"


def test_a_result_that_breaks_the_evidence_rule_is_withheld(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    """The boundary re-checks evidence, so a faulty engine cannot leak a quote."""

    def corrupted(*args, **kwargs):
        analysis = real_analyze(*args, **kwargs)
        selected = analysis["validated_predictions"][0]["selected"]
        selected[0]["evidence"] = ["a quotation that is not in the fragment"]
        return analysis

    patch_engine(monkeypatch, corrupted)

    result = post(client)

    assert result.status_code == 500
    assert result.json()["error"]["code"] == "response_validation_failed"
    assert "a quotation that is not in the fragment" not in result.text


def test_a_result_naming_an_unknown_competency_is_withheld(
    monkeypatch: pytest.MonkeyPatch,
    client,
) -> None:
    def corrupted(*args, **kwargs):
        analysis = real_analyze(*args, **kwargs)
        predicted = analysis["original_aggregation"][0]["predicted_competencies"]
        predicted[0]["competency_id"] = "NOT-IN-THE-CATALOGUE"
        return analysis

    patch_engine(monkeypatch, corrupted)

    result = post(client)

    assert result.status_code == 500
    assert result.json()["error"]["code"] == "response_validation_failed"


def test_error_envelope_has_a_stable_shape(client) -> None:
    result = client.post("/v1/analyses", json=build_payload())
    body = result.json()

    assert set(body) == {"schema_version", "error"}
    assert body["schema_version"] == "1.0"
    assert set(body["error"]) == {
        "code",
        "message",
        "retryable",
        "request_id",
        "details",
    }
