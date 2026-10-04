"""Service errors and their serialisation into the public error envelope.

Errors never carry stack traces, file paths, environment values or the content
of the request. The technical cause is logged on the server instead.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from service.schemas import ErrorDetail, ErrorResponse, FieldError


class ErrorCode:
    AUTH_MISSING = "auth_missing"
    AUTH_INVALID = "auth_invalid"
    SERVICE_NOT_CONFIGURED = "service_not_configured"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    UNSUPPORTED_RESOURCE_TYPE = "unsupported_resource_type"
    UNSUPPORTED_CONFIG = "unsupported_config"
    INVALID_COMPETENCY_CATALOGUE = "invalid_competency_catalogue"
    INVALID_RESOURCE = "invalid_resource"
    NO_USABLE_FRAGMENTS = "no_usable_fragments"
    ENGINE_INPUT_REJECTED = "engine_input_rejected"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    HTTP_ERROR = "http_error"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    MODEL_OUTPUT_INVALID = "model_output_invalid"
    ANALYSIS_FAILED = "analysis_failed"
    RESPONSE_VALIDATION_FAILED = "response_validation_failed"
    INTERNAL_ERROR = "internal_error"
    DOCUMENT_UNSUPPORTED = "document_unsupported"
    DOCUMENT_NO_TEXT = "document_no_text"
    DOCUMENT_ENCRYPTED = "document_encrypted"
    DOCUMENT_MALFORMED = "document_malformed"
    DOCUMENT_TOO_LARGE = "document_too_large"


# Bound the number of located problems returned for one request.
MAX_ERROR_DETAILS = 25


class ServiceError(Exception):
    """An error that maps to one HTTP status and one stable error code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        retryable: bool = False,
        details: Sequence[FieldError] = (),
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = list(details)[:MAX_ERROR_DETAILS]
        self.headers = dict(headers or {})


def error_payload(
    error: ServiceError,
    *,
    request_id: str | None,
) -> dict[str, Any]:
    """Return the JSON body for an error response."""

    return ErrorResponse(
        error=ErrorDetail(
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            request_id=request_id,
            details=error.details,
        )
    ).model_dump(mode="json")
