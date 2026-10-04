"""FastAPI application: an HTTP adapter over the competency-alignment engine.

Run from the repository root::

    uvicorn service.main:app --host 0.0.0.0 --port 8001

``app`` is created on first access, not on import, so importing this module (for
example from the tests) never reads ``.env`` or the process environment.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from service.alignment_adapter import AlignmentAdapter, BackendFactory
from service.auth import authenticate
from service.config import Settings, load_settings
from service.errors import ErrorCode, ServiceError, error_payload
from service.extraction.errors import DocumentError
from service.extraction.extract import extract_document
from service.schemas import (
    API_VERSION,
    SERVICE_NAME,
    AnalysisRequest,
    AnalysisResponse,
    FieldError,
    HealthResponse,
)


logger = logging.getLogger("service")

REQUEST_ID_HEADER = "X-Request-ID"
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
PROTECTED_PREFIX = "/v1/"


def _request_id(candidate: str | None) -> str:
    """Reuse a well-formed caller id so Moodle logs can be matched to ours."""

    if candidate and VALID_REQUEST_ID.match(candidate):
        return candidate

    return uuid.uuid4().hex


def _state_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(error: ServiceError, request_id: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=error_payload(error, request_id=request_id),
        headers=error.headers or None,
    )


def _location(parts: tuple[Any, ...]) -> str:
    visible = parts[1:] if parts and parts[0] == "body" else parts
    return ".".join(str(part) for part in visible) or "body"


def _configure_logging(level: str) -> None:
    """Make the service's own log lines visible under uvicorn.

    uvicorn configures only its own loggers, so without a handler the INFO
    lines written by this package would be dropped. Log lines carry request ids
    and counts only, never request content or credentials.
    """

    package_logger = logging.getLogger("service")
    package_logger.setLevel(level)

    if not package_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s:     %(name)s - %(message)s")
        )
        package_logger.addHandler(handler)


def create_app(
    settings: Settings | None = None,
    *,
    backend_factory: BackendFactory | None = None,
) -> FastAPI:
    """Build the application.

    ``backend_factory`` lets tests inject a model backend. Production leaves it
    unset and the backend named in the settings is used.
    """

    settings = settings or load_settings()
    _configure_logging(settings.log_level)
    adapter = AlignmentAdapter(settings, backend_factory=backend_factory)

    app = FastAPI(
        title="Moodle competency alignment service",
        version=API_VERSION,
        # The interactive documentation is off unless explicitly enabled.
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    if settings.backend == "mock":
        logger.warning(
            "ALIGNMENT_BACKEND=mock: responses are deterministic test output, "
            "not model output."
        )

    if not settings.token_configured:
        logger.warning(
            "ALIGNMENT_SERVICE_TOKEN is not set: protected endpoints refuse "
            "every request."
        )

    # Middleware added later wraps middleware added earlier, so the request id
    # is set first, then the body size is checked, then the caller is
    # authenticated, all before the body is parsed.
    @app.middleware("http")
    async def authentication(request: Request, call_next: Any) -> Response:
        if request.url.path.startswith(PROTECTED_PREFIX):
            try:
                authenticate(settings, request.headers.get("authorization"))
            except ServiceError as error:
                return _error_response(error, _state_request_id(request))

        return await call_next(request)

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Response:
        request_id = _request_id(request.headers.get(REQUEST_ID_HEADER.lower()))
        request.state.request_id = request_id
        declared = request.headers.get("content-length", "")

        if declared.isdigit() and int(declared) > settings.max_body_bytes:
            response: Response = _error_response(
                ServiceError(
                    ErrorCode.PAYLOAD_TOO_LARGE,
                    "The request body is too large.",
                    status_code=413,
                ),
                request_id,
            )
        else:
            response = await call_next(request)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @app.exception_handler(ServiceError)
    async def handle_service_error(
        request: Request,
        error: ServiceError,
    ) -> JSONResponse:
        return _error_response(error, _state_request_id(request))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        # Only the location and the rule are reported. The submitted value is
        # never echoed back, because it may be resource content.
        return _error_response(
            ServiceError(
                ErrorCode.INVALID_REQUEST,
                "The request does not match the expected schema.",
                status_code=422,
                details=[
                    FieldError(
                        loc=_location(tuple(item.get("loc", ()))),
                        message=str(item.get("msg", "Invalid value.")),
                    )
                    for item in error.errors()
                ],
            ),
            _state_request_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        code = {
            404: ErrorCode.NOT_FOUND,
            405: ErrorCode.METHOD_NOT_ALLOWED,
        }.get(error.status_code, ErrorCode.HTTP_ERROR)
        return _error_response(
            ServiceError(
                code,
                "The request could not be routed.",
                status_code=error.status_code,
            ),
            _state_request_id(request),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        request_id = _state_request_id(request)
        logger.error(
            "unhandled error request_id=%s type=%s",
            request_id,
            type(error).__name__,
            exc_info=error,
        )
        response = _error_response(
            ServiceError(
                ErrorCode.INTERNAL_ERROR,
                "The service could not complete the request.",
                status_code=500,
            ),
            request_id,
        )

        if request_id:
            response.headers[REQUEST_ID_HEADER] = request_id

        return response

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=SERVICE_NAME,
            api_version=API_VERSION,
        )

    # A plain ``def`` handler runs in the thread pool, so a long model call does
    # not block the event loop.
    @app.post("/v1/analyses", response_model=AnalysisResponse)
    def create_analysis(
        payload: AnalysisRequest,
        request: Request,
    ) -> AnalysisResponse:
        return adapter.analyse(
            payload,
            request_id=_state_request_id(request) or "",
        )

    @app.post("/v1/extractions")
    async def create_extraction(
        request: Request,
        declared_format: str = Form(...),
        upload: UploadFile = File(...),
    ) -> dict[str, Any]:
        """Extract plain text from one teacher file. The bytes are not stored."""

        data = await upload.read()
        try:
            result = extract_document(data, declared_format)
        except DocumentError as error:
            code = {
                "document_unsupported": ErrorCode.DOCUMENT_UNSUPPORTED,
                "document_no_text": ErrorCode.DOCUMENT_NO_TEXT,
                "document_encrypted": ErrorCode.DOCUMENT_ENCRYPTED,
                "document_malformed": ErrorCode.DOCUMENT_MALFORMED,
                "document_too_large": ErrorCode.DOCUMENT_TOO_LARGE,
            }.get(error.code, ErrorCode.DOCUMENT_MALFORMED)
            status = 413 if code == ErrorCode.DOCUMENT_TOO_LARGE else 422
            raise ServiceError(code, error.message, status_code=status) from None

        logger.info(
            "extraction completed request_id=%s format=%s chars=%s",
            _state_request_id(request),
            declared_format,
            len(result["text"]),
        )
        return result

    return app


_application: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """Create ``app`` lazily so ``uvicorn service.main:app`` works."""

    global _application

    if name == "app":
        if _application is None:
            _application = create_app()

        return _application

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
