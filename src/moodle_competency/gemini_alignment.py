"""Run constrained Moodle competency-alignment tasks with Gemini."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import requests


RETRY_IN_SECONDS_RE = re.compile(
    r"Please retry in (?P<seconds>\d+(?:\.\d+)?)s",
    re.IGNORECASE,
)
PROTO_DELAY_RE = re.compile(
    r"^(?P<seconds>\d+(?:\.\d+)?)s$",
    re.IGNORECASE,
)

SAFETY_MARGIN_SECONDS = 2.0
MAX_RATE_LIMIT_WAIT_SECONDS = 120.0
DAILY_QUOTA_WAIT_SECONDS = 300.0

DAILY_QUOTA_MARKERS = (
    "per_day",
    "perday",
    "requests_per_day",
    "free_tier_requests_per_day",
    "daily quota",
    "quota metric: generate_content_free_tier_requests, limit: 0",
)


class GeminiAlignmentError(RuntimeError):
    """Raised when a Gemini alignment request cannot be completed."""


class GeminiQuotaExhaustedError(GeminiAlignmentError):
    """Raised when daily or free-tier quota is exhausted."""


@dataclass(frozen=True, slots=True)
class GeminiUsage:
    """Token-usage metadata returned by Gemini."""

    prompt_tokens: int | None
    candidate_tokens: int | None
    total_tokens: int | None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "candidate_tokens": self.candidate_tokens,
            "total_tokens": self.total_tokens,
        }


def build_response_schema(
    task: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a task-specific JSON schema for Gemini."""

    fragment_id = str(
        task.get("fragment_id", "")
    ).strip()

    allowed_idnumbers = [
        str(value).strip()
        for value in task.get(
            "allowed_idnumbers",
            [],
        )
        if str(value).strip()
    ]

    if not fragment_id:
        raise ValueError(
            "The alignment task has no fragment_id."
        )

    if not allowed_idnumbers:
        raise ValueError(
            f"Task {fragment_id} has no allowed competency IDs."
        )

    return {
        "type": "object",
        "properties": {
            "fragment_id": {
                "type": "string",
                "enum": [fragment_id],
            },
            "selected": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "idnumber": {
                            "type": "string",
                            "enum": allowed_idnumbers,
                        },
                        "evidence": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "string",
                            },
                        },
                        "reason": {
                            "type": "string",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": [
                        "idnumber",
                        "evidence",
                        "reason",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "abstain": {
                "type": "boolean",
            },
            "overall_reason": {
                "type": "string",
            },
        },
        "required": [
            "fragment_id",
            "selected",
            "abstain",
            "overall_reason",
        ],
        "additionalProperties": False,
    }


def build_request_prompt(
    task: Mapping[str, Any],
) -> str:
    """Add final safeguards to the previously generated prompt."""

    original_prompt = str(
        task.get("prompt", "")
    ).strip()

    if not original_prompt:
        raise ValueError(
            "The alignment task contains an empty prompt."
        )

    return (
        original_prompt
        + "\n\nFINAL DECISION REMINDERS:\n"
        + "- The example JSON above illustrates formatting only.\n"
        + "- It is not a recommendation to select Candidate 1.\n"
        + "- Judge every candidate independently from the fragment text.\n"
        + "- Prefer abstention over a weak or unsupported alignment.\n"
        + "- Copy evidence exactly, including capitalization and punctuation.\n"
    )


def extract_response_text(
    response_data: Mapping[str, Any],
) -> str:
    """Extract the generated JSON text from a Gemini response."""

    candidates = response_data.get("candidates")

    if not isinstance(candidates, list) or not candidates:
        prompt_feedback = response_data.get(
            "promptFeedback",
            {},
        )

        raise GeminiAlignmentError(
            "Gemini returned no response candidate. "
            f"Prompt feedback: {prompt_feedback}"
        )

    first_candidate = candidates[0]

    if not isinstance(first_candidate, dict):
        raise GeminiAlignmentError(
            "Gemini returned an invalid candidate structure."
        )

    finish_reason = first_candidate.get(
        "finishReason"
    )

    content = first_candidate.get("content", {})

    if not isinstance(content, dict):
        raise GeminiAlignmentError(
            "Gemini returned no response content."
        )

    parts = content.get("parts", [])

    if not isinstance(parts, list):
        raise GeminiAlignmentError(
            "Gemini response parts have an invalid structure."
        )

    text_parts = [
        str(part.get("text", ""))
        for part in parts
        if (
            isinstance(part, dict)
            and str(part.get("text", "")).strip()
        )
    ]

    response_text = "".join(text_parts).strip()

    if not response_text:
        raise GeminiAlignmentError(
            "Gemini returned empty text. "
            f"Finish reason: {finish_reason}"
        )

    return response_text


def parse_usage(
    response_data: Mapping[str, Any],
) -> GeminiUsage:
    """Read optional Gemini token-usage metadata."""

    metadata = response_data.get(
        "usageMetadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    def optional_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return GeminiUsage(
        prompt_tokens=optional_int(
            metadata.get("promptTokenCount")
        ),
        candidate_tokens=optional_int(
            metadata.get("candidatesTokenCount")
        ),
        total_tokens=optional_int(
            metadata.get("totalTokenCount")
        ),
    )


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number < 0:
        return None

    return number


def parse_retry_delay_seconds(
    *,
    headers: Mapping[str, Any] | None = None,
    error_object: Mapping[str, Any] | None = None,
    message: str = "",
) -> float | None:
    """Read provider retry delay from headers, RetryInfo, or error text."""

    headers = headers or {}
    retry_after = headers.get("Retry-After") or headers.get("retry-after")

    if retry_after is not None:
        as_seconds = _positive_float(retry_after)

        if as_seconds is not None:
            return as_seconds

        try:
            retry_at = parsedate_to_datetime(str(retry_after))
        except (TypeError, ValueError, IndexError):
            retry_at = None

        if retry_at is not None:
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)

            remaining = (
                retry_at - datetime.now(timezone.utc)
            ).total_seconds()

            if remaining > 0:
                return remaining

    if isinstance(error_object, Mapping):
        details = error_object.get("details") or []

        if isinstance(details, list):
            for item in details:
                if not isinstance(item, Mapping):
                    continue

                delay = item.get("retryDelay") or item.get("retry_delay")

                if delay is None:
                    continue

                if isinstance(delay, Mapping):
                    seconds = _positive_float(delay.get("seconds") or 0) or 0.0
                    nanos = _positive_float(delay.get("nanos") or 0) or 0.0
                    return seconds + nanos / 1_000_000_000

                match = PROTO_DELAY_RE.match(str(delay).strip())

                if match:
                    return float(match.group("seconds"))

                as_seconds = _positive_float(delay)

                if as_seconds is not None:
                    return as_seconds

    match = RETRY_IN_SECONDS_RE.search(message)

    if match:
        return float(match.group("seconds"))

    return None


def apply_safety_margin(seconds: float) -> float:
    """Add a small extra wait so the quota window has actually reset."""

    extra = max(SAFETY_MARGIN_SECONDS, seconds * 0.1)
    extra = min(extra, 5.0)
    return seconds + extra


def exponential_backoff_seconds(attempt: int) -> float:
    """Fallback wait when the provider does not publish a retry delay."""

    return float(2 ** max(attempt - 1, 0))


def is_daily_quota_exhausted(
    *,
    message: str,
    retry_seconds: float | None,
) -> bool:
    """True when waiting would not recover the quota in this session."""

    lowered = message.lower()

    if retry_seconds is not None and retry_seconds >= DAILY_QUOTA_WAIT_SECONDS:
        return True

    return any(marker in lowered for marker in DAILY_QUOTA_MARKERS)


class GeminiAlignmentClient:
    """REST client for constrained Gemini alignment requests."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.5-flash",
        timeout: float = 120.0,
        maximum_attempts: int = 8,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "Gemini API key cannot be empty."
            )

        if maximum_attempts <= 0:
            raise ValueError(
                "maximum_attempts must be positive."
            )

        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = timeout
        self.maximum_attempts = maximum_attempts
        self.session = session or requests.Session()
        self._owns_session = session is None
        self.last_http_retries = 0

    @property
    def endpoint(self) -> str:
        return (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self.model}:generateContent"
        )

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "GeminiAlignmentClient":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def align(
        self,
        task: Mapping[str, Any],
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        GeminiUsage,
    ]:
        """Run one task and return parsed, raw and usage data."""

        fragment_id = str(
            task.get("fragment_id", "")
        ).strip()

        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": build_request_prompt(
                                task
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
                "responseJsonSchema":
                    build_response_schema(task),
            },
        }

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        retryable_statuses = {
            429,
            500,
            502,
            503,
            504,
        }

        last_error = ""
        self.last_http_retries = 0

        for attempt in range(
            1,
            self.maximum_attempts + 1,
        ):
            try:
                response = self.session.post(
                    self.endpoint,
                    headers=headers,
                    json=request_body,
                    timeout=self.timeout,
                )
            except requests.RequestException as error:
                last_error = str(error)

                if attempt < self.maximum_attempts:
                    self.last_http_retries += 1
                    time.sleep(exponential_backoff_seconds(attempt))
                    continue

                raise GeminiAlignmentError(
                    f"Gemini request failed for "
                    f"{fragment_id}: {error}"
                ) from error

            try:
                response_data = response.json()
            except ValueError as error:
                response_preview = response.text[:1000]

                raise GeminiAlignmentError(
                    "Gemini returned invalid JSON at the "
                    "HTTP-response level. Preview: "
                    f"{response_preview!r}"
                ) from error

            if response.ok:
                response_text = extract_response_text(
                    response_data
                )

                try:
                    parsed_response = json.loads(
                        response_text
                    )
                except json.JSONDecodeError as error:
                    raise GeminiAlignmentError(
                        "Gemini structured output could not "
                        f"be decoded for {fragment_id}: "
                        f"{response_text[:1000]!r}"
                    ) from error

                if not isinstance(
                    parsed_response,
                    dict,
                ):
                    raise GeminiAlignmentError(
                        "Gemini output is not a JSON object."
                    )

                parsed_response[
                    "model_provider"
                ] = "google_gemini"

                parsed_response[
                    "model_name"
                ] = self.model

                return (
                    parsed_response,
                    response_data,
                    parse_usage(response_data),
                )

            error_object = response_data.get(
                "error",
                {},
            )

            if isinstance(error_object, dict):
                last_error = str(
                    error_object.get(
                        "message",
                        response_data,
                    )
                )
            else:
                error_object = {}
                last_error = str(response_data)

            retry_seconds = parse_retry_delay_seconds(
                headers=getattr(response, "headers", {}) or {},
                error_object=error_object,
                message=last_error,
            )

            if response.status_code == 429 and is_daily_quota_exhausted(
                message=last_error,
                retry_seconds=retry_seconds,
            ):
                raise GeminiQuotaExhaustedError(
                    f"Gemini daily/free-tier quota exhausted for "
                    f"{fragment_id}: {last_error}"
                )

            if (
                response.status_code in retryable_statuses
                and attempt < self.maximum_attempts
            ):
                if retry_seconds is None:
                    wait_seconds = exponential_backoff_seconds(attempt)
                else:
                    wait_seconds = apply_safety_margin(retry_seconds)
                    wait_seconds = min(
                        wait_seconds,
                        MAX_RATE_LIMIT_WAIT_SECONDS,
                    )

                self.last_http_retries += 1
                time.sleep(wait_seconds)
                continue

            raise GeminiAlignmentError(
                f"Gemini returned HTTP "
                f"{response.status_code} for "
                f"{fragment_id}: {last_error}"
            )

        raise GeminiAlignmentError(
            f"Gemini failed after "
            f"{self.maximum_attempts} attempts: "
            f"{last_error}"
        )
