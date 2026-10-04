"""Versioned request and response models for the alignment service.

Schema version 1.0. The Moodle plugin and this service must agree on these
models; a change to any field is a new schema version.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEMA_VERSION = "1.0"
API_VERSION = "1"
SERVICE_NAME = "moodle-competency-alignment"

# A resource type is listed here only after it has been exercised end to end
# through this service. The engine can chunk other types, but the contract does
# not claim support for them until they are tested.
# Every type is the same alignment input: plain text plus a stable id.
# Adapters in the Moodle plugin produce these values. The engine does not
# branch on them.
SUPPORTED_RESOURCE_TYPES: tuple[str, ...] = (
    "page",
    "quiz_question",
    "pdf",
    "docx",
    "pptx",
    "text",
    "markdown",
    "transcript",
    "book_chapter",
    "assignment",
    "lesson_page",
    "label",
    "forum_intro",
    "url",
)

MAX_ID_CHARS = 255
MAX_TITLE_CHARS = 500
MAX_CONTEXT_CHARS = 500
MAX_TEXT_CHARS = 200_000
MAX_COMPETENCIES = 2_000
# Moodle stores competency idnumber and shortname as char(100).
MAX_COMPETENCY_CODE_CHARS = 100
MAX_COMPETENCY_DESCRIPTION_CHARS = 20_000
DEFAULT_MAX_SUGGESTIONS = 3
MAX_SUGGESTIONS_LIMIT = 10


class _StrictModel(BaseModel):
    """Reject unknown fields so a contract mismatch is visible, not silent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #


class ResourceIn(_StrictModel):
    """One teacher-authored learning resource, already converted to plain text."""

    resource_id: str = Field(min_length=1, max_length=MAX_ID_CHARS)
    resource_type: str = Field(min_length=1, max_length=40)
    course_id: str | None = Field(default=None, max_length=40)
    course_module_id: str | None = Field(default=None, max_length=40)
    title: str = Field(min_length=1, max_length=MAX_TITLE_CHARS)
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    search_text: str | None = Field(
        default=None,
        max_length=MAX_TEXT_CHARS + MAX_TITLE_CHARS,
    )
    # Optional structural context. The frozen pipeline put these into the BM25
    # query and the model prompt, so a connector may send them to keep parity.
    course_shortname: str | None = Field(default=None, max_length=MAX_CONTEXT_CHARS)
    course_fullname: str | None = Field(default=None, max_length=MAX_CONTEXT_CHARS)
    section_name: str | None = Field(default=None, max_length=MAX_CONTEXT_CHARS)
    activity_name: str | None = Field(default=None, max_length=MAX_CONTEXT_CHARS)

    @field_validator("resource_id")
    @classmethod
    def _resource_id_has_no_whitespace(cls, value: str) -> str:
        if any(character.isspace() for character in value):
            raise ValueError("must not contain whitespace")

        return value

    @field_validator("course_id", "course_module_id", mode="before")
    @classmethod
    def _identifier_as_text(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("must be a string or an integer")

        if isinstance(value, int):
            return str(value)

        return value


class CompetencyIn(_StrictModel):
    """One competency of the framework the resource is aligned against."""

    idnumber: str = Field(min_length=1, max_length=MAX_COMPETENCY_CODE_CHARS)
    shortname: str = Field(min_length=1, max_length=MAX_COMPETENCY_CODE_CHARS)
    description_text: str = Field(
        min_length=1,
        max_length=MAX_COMPETENCY_DESCRIPTION_CHARS,
    )
    parent_idnumber: str | None = Field(
        default=None,
        max_length=MAX_COMPETENCY_CODE_CHARS,
    )
    framework_idnumber: str = Field(
        min_length=1,
        max_length=MAX_COMPETENCY_CODE_CHARS,
    )
    framework_shortname: str | None = Field(
        default=None,
        max_length=MAX_COMPETENCY_CODE_CHARS,
    )


class AnalysisConfigIn(_StrictModel):
    """Run-time options. ``top_k`` is validated against the engine, not here."""

    top_k: int | None = Field(default=None, ge=1, le=50)
    max_suggestions: int = Field(
        default=DEFAULT_MAX_SUGGESTIONS,
        ge=1,
        le=MAX_SUGGESTIONS_LIMIT,
    )


class AnalysisRequest(_StrictModel):
    schema_version: str = Field(min_length=1, max_length=20)
    resource: ResourceIn
    competencies: list[CompetencyIn] = Field(
        min_length=1,
        max_length=MAX_COMPETENCIES,
    )
    config: AnalysisConfigIn = Field(default_factory=AnalysisConfigIn)


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    api_version: str


class EvidenceOut(BaseModel):
    """An exact quotation from the fragment, validated by the engine."""

    fragment_id: str
    quote: str


class WarningOut(BaseModel):
    """A hierarchy diagnostic. It is informational and never alters a suggestion."""

    code: str
    role: Literal["parent", "child"] | None = None
    related_idnumber: str | None = None
    message: str


class SuggestionOut(BaseModel):
    """One proposed competency for the resource.

    ``confidence`` is the highest confidence the model reported over the
    supporting fragments. It is model metadata, not a calibrated probability.
    ``bm25_rank`` is the best retrieval rank over the supporting fragments.
    """

    competency_idnumber: str
    confidence: float | None
    bm25_rank: int | None
    support_count: int
    evidence: list[EvidenceOut]
    warnings: list[WarningOut]


class DiagnosticOut(BaseModel):
    code: str
    message: str
    fragment_id: str | None = None
    details: list[str] = Field(default_factory=list)


class ManifestOut(BaseModel):
    backend: str
    model: str
    prompt_version: str
    top_k: int
    max_selections_per_fragment: int
    competency_catalogue_hash: str
    resource_hash: str
    fragment_count: int
    completeness: Literal["complete", "partial"]
    analysed_at: str
    duration_ms: int


class AnalysisResponse(BaseModel):
    schema_version: str
    analysis_id: str
    status: Literal["completed"]
    resource_id: str
    manifest: ManifestOut
    suggestions: list[SuggestionOut]
    abstained: bool
    diagnostics: list[DiagnosticOut]


class FieldError(BaseModel):
    """A problem located in the request. It never repeats the offending value."""

    loc: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    request_id: str | None = None
    details: list[FieldError] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    error: ErrorDetail
