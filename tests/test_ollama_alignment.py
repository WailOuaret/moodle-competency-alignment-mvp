"""Tests for the optional local Ollama experiment client.

Uses mocked HTTP only. Never calls Gemini and never mutates live
experimental Gemini files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from moodle_competency.ollama_alignment import (
    OllamaAlignmentClient,
    OllamaAlignmentError,
    extract_json_object,
)


SAMPLE_TASK = {
    "fragment_id": "page:1#f001",
    "allowed_idnumbers": ["GI_C1_1"],
    "prompt": "Align this fragment.",
    "fragment_text": "Students design software.",
}


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.ok = 200 <= status_code < 300
        self.text = json.dumps(payload)
        self.headers = {}

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []
        self.last_json: dict[str, Any] | None = None

    def request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> FakeResponse:
        self.calls.append((method, url))
        self.last_json = json

        if not self.responses:
            raise AssertionError("No fake Ollama response remains.")

        return self.responses.pop(0)


def sample_model_payload() -> dict[str, Any]:
    content = {
        "fragment_id": "page:1#f001",
        "selected": [
            {
                "idnumber": "GI_C1_1",
                "evidence": ["Students design software."],
                "reason": "The fragment teaches software design.",
                "confidence": 0.9,
            }
        ],
        "abstain": False,
        "overall_reason": "One matching child competency.",
    }
    return {
        "message": {"content": json.dumps(content)},
        "prompt_eval_count": 11,
        "eval_count": 7,
    }


def test_extract_json_from_fenced_text() -> None:
    parsed = extract_json_object(
        '```json\n{"fragment_id": "page:1#f001", "abstain": true}\n```'
    )

    assert parsed["fragment_id"] == "page:1#f001"
    assert parsed["abstain"] is True


def test_align_uses_temperature_zero_and_same_schema() -> None:
    session = FakeSession([FakeResponse(200, sample_model_payload())])

    with OllamaAlignmentClient(
        host="http://127.0.0.1:11434",
        model="mistral:latest",
        session=session,
        allow_windows_curl_fallback=False,
    ) as client:
        parsed, raw, usage = client.align(SAMPLE_TASK)

    method, url = session.calls[0]
    assert method == "POST"
    assert url.endswith("/api/chat")
    assert session.last_json is not None
    assert session.last_json["options"]["temperature"] == 0
    assert session.last_json["stream"] is False
    assert parsed["model_provider"] == "ollama"
    assert parsed["model_name"] == "mistral:latest"
    assert parsed["fragment_id"] == "page:1#f001"
    assert usage.prompt_tokens == 11
    assert raw["eval_count"] == 7


def test_missing_model_is_rejected() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"models": [{"name": "llama3.1:latest"}]},
            )
        ]
    )

    with OllamaAlignmentClient(
        host="http://127.0.0.1:11434",
        model="mistral:latest",
        session=session,
        allow_windows_curl_fallback=False,
    ) as client:
        with pytest.raises(OllamaAlignmentError, match="not installed"):
            client.require_model()


def test_experiment_paths_are_not_gemini_paths() -> None:
    runner = Path("scripts/29_run_ollama_constrained.py").read_text(
        encoding="utf-8"
    )
    evaluator = Path("scripts/30_evaluate_ollama_constrained.py").read_text(
        encoding="utf-8"
    )

    assert 'EXPERIMENT_DIR / "ollama_constrained_validated.jsonl"' in runner
    assert "Does not modify Gemini outputs." in runner
    assert "ollama_constrained_metrics.json" in evaluator
    assert "model_comparison_with_ollama.csv" in evaluator
    assert 'COMPARISON = PROJECT_ROOT / "reports" / "tables" / "model_comparison.csv"' not in evaluator
