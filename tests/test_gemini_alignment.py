"""Tests for Gemini retry-delay parsing and 429 handling."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from moodle_competency.gemini_alignment import (
    GeminiAlignmentClient,
    GeminiQuotaExhaustedError,
    apply_safety_margin,
    exponential_backoff_seconds,
    is_daily_quota_exhausted,
    parse_retry_delay_seconds,
)


SAMPLE_TASK = {
    "fragment_id": "page:1#f001",
    "allowed_idnumbers": ["GI_C1_1"],
    "prompt": "Align this fragment.",
}


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300
        self.text = json.dumps(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.closed = False

    def post(self, *args: Any, **kwargs: Any) -> FakeResponse:
        if not self.responses:
            raise AssertionError("No fake Gemini response remains.")

        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


def test_parse_retry_from_message() -> None:
    delay = parse_retry_delay_seconds(
        message=(
            "You exceeded your current quota. "
            "Please retry in 32.735228683s."
        )
    )

    assert delay == pytest.approx(32.735228683)


def test_parse_retry_from_header_and_retryinfo() -> None:
    assert parse_retry_delay_seconds(
        headers={"Retry-After": "12"}
    ) == 12.0
    assert parse_retry_delay_seconds(
        error_object={
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": "5s",
                }
            ]
        }
    ) == 5.0


def test_safety_margin_and_backoff() -> None:
    assert apply_safety_margin(10.0) == 12.0
    assert exponential_backoff_seconds(1) == 1.0
    assert exponential_backoff_seconds(3) == 4.0


def test_daily_quota_uses_long_delay_or_per_day_metric() -> None:
    assert is_daily_quota_exhausted(
        message="Please retry later",
        retry_seconds=400.0,
    )
    assert is_daily_quota_exhausted(
        message="Quota exceeded for metric generate_content_free_tier_requests_per_day",
        retry_seconds=None,
    )
    assert not is_daily_quota_exhausted(
        message=(
            "You exceeded your current quota. "
            "Please retry in 32s."
        ),
        retry_seconds=32.0,
    )


def test_429_waits_provider_delay_then_succeeds() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "fragment_id": "page:1#f001",
                                    "selected": [],
                                    "abstain": True,
                                    "overall_reason": "none",
                                }
                            )
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 4,
            "totalTokenCount": 14,
        },
    }
    session = FakeSession(
        [
            FakeResponse(
                429,
                {
                    "error": {
                        "message": "Please retry in 3s.",
                        "status": "RESOURCE_EXHAUSTED",
                    }
                },
            ),
            FakeResponse(200, payload),
        ]
    )
    sleeps: list[float] = []

    with patch(
        "moodle_competency.gemini_alignment.time.sleep",
        side_effect=lambda seconds: sleeps.append(seconds),
    ):
        client = GeminiAlignmentClient(
            api_key="test-key",
            session=session,
        )
        parsed, _raw, usage = client.align(SAMPLE_TASK)

    assert parsed["abstain"] is True
    assert client.last_http_retries == 1
    assert sleeps == [apply_safety_margin(3.0)]
    assert usage.total_tokens == 14


def test_daily_quota_stops_without_retry_loop() -> None:
    session = FakeSession(
        [
            FakeResponse(
                429,
                {
                    "error": {
                        "message": (
                            "Quota exceeded for metric "
                            "generate_content_free_tier_requests_per_day"
                        )
                    }
                },
            )
        ]
    )

    with patch("moodle_competency.gemini_alignment.time.sleep") as sleep:
        client = GeminiAlignmentClient(
            api_key="test-key",
            session=session,
        )

        with pytest.raises(GeminiQuotaExhaustedError):
            client.align(SAMPLE_TASK)

    sleep.assert_not_called()
