"""GET /health and the unauthenticated surface of the service."""

from __future__ import annotations

import pytest

from service_support import TOKEN


def test_health_reports_status_only(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "moodle-competency-alignment",
        "api_version": "1",
    }


def test_health_needs_no_credentials(client) -> None:
    assert "authorization" not in client.headers
    assert client.get("/health").status_code == 200


def test_health_exposes_no_secret_environment_or_path(
    monkeypatch: pytest.MonkeyPatch,
    make_client,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret-marker")
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama-secret-marker:11434")
    text = make_client().get("/health").text

    for forbidden in (
        TOKEN,
        "gemini-secret-marker",
        "ollama-secret-marker",
        "/home/",
        "Traceback",
        "model",
        "mock",
    ):
        assert forbidden not in text


def test_interactive_documentation_is_disabled_by_default(client) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_interactive_documentation_can_be_enabled(make_client) -> None:
    assert make_client(enable_docs=True).get("/openapi.json").status_code == 200


def test_unknown_route_uses_the_error_envelope(client) -> None:
    response = client.get("/v1/nothing-here", headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unknown_route_is_still_protected(client) -> None:
    assert client.get("/v1/nothing-here").status_code == 401


def test_wrong_method_uses_the_error_envelope(client) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
