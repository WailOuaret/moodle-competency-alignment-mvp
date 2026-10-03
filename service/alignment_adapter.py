"""Adapter between the service contract and the research alignment engine.

The engine is called the way the teacher application calls it
(``analyze_runtime_resource``). This module only

1. validates and normalises what Moodle sends,
2. guards the places where the engine would silently fall back to frozen
   experiment data, and
3. maps the engine result onto the public response contract.

Nothing here decides which competency fits a resource.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from moodle_competency.graph_checks import validate_hierarchy
from moodle_competency.html_clean import combine_text, normalize_whitespace
from moodle_competency.resource_contract import (
    validate_competency_record,
    validate_resource_record,
)
from moodle_competency.resource_ingestion import sha256_text
from moodle_competency.retrieval import build_competency_document, tokenize
from moodle_competency.runtime_analysis import (
    RETRIEVAL_TOP_K,
    AlignmentBackend,
    BackendUnavailableError,
    NoUsableFragmentsError,
    RuntimeAnalysisError,
    analyze_runtime_resource,
    create_runtime_backend,
)
from moodle_competency.runtime_storage import runtime_paths

from service.config import Settings
from service.errors import ErrorCode, ServiceError
from service.mock_backend import create_mock_backend
from service.schemas import (
    SCHEMA_VERSION,
    SUPPORTED_RESOURCE_TYPES,
    AnalysisConfigIn,
    AnalysisRequest,
    AnalysisResponse,
    CompetencyIn,
    DiagnosticOut,
    EvidenceOut,
    FieldError,
    ManifestOut,
    ResourceIn,
    SuggestionOut,
    WarningOut,
)


logger = logging.getLogger("service.adapter")

BackendFactory = Callable[[Settings], AlignmentBackend]

PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")
HASH_PREFIX = "sha256:"
MAX_DIAGNOSTIC_DETAILS = 5
MAX_DIAGNOSTIC_DETAIL_CHARS = 300
SOURCE_EXTRACTION = "moodle_plugin"

# Warning texts are factual. They describe the hierarchy relation and do not
# recommend a decision. The Moodle plugin localises them from ``code`` and
# ``role``.
_WARNING_MESSAGES = {
    ("parent_child_redundancy", "parent"): (
        "A more specific child competency ({related}) is also suggested "
        "for this resource."
    ),
    ("parent_child_redundancy", "child"): (
        "Its parent competency ({related}) is also suggested for this resource."
    ),
    ("granularity_conflict", "parent"): (
        "A more specific child competency ({related}) is suggested with "
        "overlapping evidence."
    ),
    ("granularity_conflict", "child"): (
        "Its parent competency ({related}) is suggested with overlapping "
        "evidence."
    ),
}
_GENERIC_WARNING_MESSAGE = "A hierarchy check flagged this competency."

_CATALOGUE_HASH_FIELDS = (
    "idnumber",
    "shortname",
    "description_text",
    "parent_idnumber",
    "framework_idnumber",
    "framework_shortname",
)


@dataclass(frozen=True, slots=True)
class PreparedCatalogue:
    """A validated catalogue in the shape the engine expects."""

    records: list[dict[str, Any]]
    idnumbers: frozenset[str]
    content_hash: str


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #


def _flat_record(competency: CompetencyIn) -> dict[str, str]:
    return {
        "idnumber": normalize_whitespace(competency.idnumber),
        "shortname": normalize_whitespace(competency.shortname),
        "description_text": normalize_whitespace(competency.description_text),
        "parent_idnumber": normalize_whitespace(competency.parent_idnumber),
        "framework_idnumber": normalize_whitespace(
            competency.framework_idnumber
        ),
        "framework_shortname": normalize_whitespace(
            competency.framework_shortname
        ),
    }


def catalogue_hash(records: Sequence[Mapping[str, str]]) -> str:
    """Return a stable digest of the catalogue content.

    The digest covers the normalised content of every competency in idnumber
    order. It does not depend on the order Moodle listed them in.
    """

    canonical = json.dumps(
        [
            {field: record[field] for field in _CATALOGUE_HASH_FIELDS}
            for record in sorted(records, key=lambda item: item["idnumber"])
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return HASH_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _enrich_catalogue(
    records: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    """Derive the hierarchy fields the engine reads (depth, labels, search text).

    The derivation follows ``competency_normalization.normalize_competencies``
    so that an equivalent catalogue yields identical BM25 documents and model
    prompts. A parity test compares the result with the frozen catalogue.
    """

    by_idnumber = {record["idnumber"]: record for record in records}
    enriched: list[dict[str, Any]] = []

    for record in sorted(records, key=lambda item: item["idnumber"]):
        ancestors: list[Mapping[str, str]] = []
        visited = {record["idnumber"]}
        parent_id = record["parent_idnumber"]

        while parent_id and parent_id not in visited:
            visited.add(parent_id)
            parent = by_idnumber.get(parent_id)

            if parent is None:
                break

            ancestors.append(parent)
            parent_id = parent["parent_idnumber"]

        ancestors.reverse()
        hierarchy_idnumbers = [item["idnumber"] for item in ancestors] + [
            record["idnumber"]
        ]
        hierarchy_labels = [
            item["shortname"] for item in ancestors if item["shortname"]
        ] + [record["shortname"]]
        full_text = combine_text(
            record["idnumber"],
            record["shortname"],
            record["description_text"],
        )
        direct_parent = by_idnumber.get(record["parent_idnumber"])

        enriched.append(
            {
                "competency_id": None,
                "idnumber": record["idnumber"],
                "shortname": record["shortname"],
                "description_text": record["description_text"],
                "full_text": full_text,
                "search_text": combine_text(
                    record["framework_shortname"],
                    " > ".join(hierarchy_labels[:-1]),
                    full_text,
                ),
                "framework_id": None,
                "framework_idnumber": record["framework_idnumber"],
                "framework_shortname": record["framework_shortname"],
                "parent_competency_id": None,
                "parent_idnumber": record["parent_idnumber"],
                "parent_shortname": (
                    direct_parent["shortname"] if direct_parent else ""
                ),
                "depth": len(ancestors),
                "hierarchy_idnumbers": hierarchy_idnumbers,
                "hierarchy_labels": hierarchy_labels,
                "source_extraction": SOURCE_EXTRACTION,
            }
        )

    return enriched


def _join_ids(values: Sequence[str], limit: int = 10) -> str:
    shown = ", ".join(values[:limit])
    extra = len(values) - limit
    return f"{shown} (+{extra} more)" if extra > 0 else shown


def prepare_catalogue(
    competencies: Sequence[CompetencyIn],
) -> PreparedCatalogue:
    """Validate the supplied catalogue and return it in engine form.

    The catalogue is never completed from the frozen experiment files: the
    engine would do that silently for an empty list, so an empty or invalid
    catalogue is rejected here instead.
    """

    records = [_flat_record(item) for item in competencies]
    problems: list[FieldError] = []
    counts = Counter(record["idnumber"] for record in records)
    duplicates = sorted(key for key, count in counts.items() if count > 1)

    if duplicates:
        problems.append(
            FieldError(
                loc="competencies",
                message="Duplicate idnumber values: " + _join_ids(duplicates),
            )
        )

    for index, record in enumerate(records):
        for message in validate_competency_record(record):
            problems.append(
                FieldError(
                    loc=f"competencies.{index}",
                    message=f"{record['idnumber']}: {message}",
                )
            )

    frameworks = sorted({record["framework_idnumber"] for record in records})

    if len(frameworks) > 1:
        problems.append(
            FieldError(
                loc="competencies",
                message=(
                    "Competencies from more than one framework were sent: "
                    + _join_ids(frameworks)
                ),
            )
        )

    hierarchy = validate_hierarchy(records)

    for reference in hierarchy["missing_parent_references"]:
        problems.append(
            FieldError(
                loc="competencies",
                message=f"Parent is not in the catalogue: {reference}",
            )
        )

    for cycle in hierarchy["cycles"]:
        problems.append(
            FieldError(
                loc="competencies",
                message=f"Hierarchy cycle: {cycle}",
            )
        )

    enriched = _enrich_catalogue(records)

    for record in enriched:
        if not tokenize(build_competency_document(record)):
            problems.append(
                FieldError(
                    loc="competencies",
                    message=(
                        f"{record['idnumber']}: contains no searchable words."
                    ),
                )
            )

    if problems:
        raise ServiceError(
            ErrorCode.INVALID_COMPETENCY_CATALOGUE,
            "The competency catalogue is not valid.",
            status_code=422,
            details=problems,
        )

    return PreparedCatalogue(
        records=enriched,
        idnumbers=frozenset(record["idnumber"] for record in records),
        content_hash=catalogue_hash(records),
    )


# --------------------------------------------------------------------------- #
# Resource
# --------------------------------------------------------------------------- #


def normalize_paragraphs(text: str) -> str:
    """Normalise every paragraph but keep the blank-line breaks.

    The fragmenter splits Page text on blank lines, so they must survive. The
    same pattern is used by ``fragmentation.chunk_text``.
    """

    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = (
        normalize_whitespace(paragraph)
        for paragraph in PARAGRAPH_BREAK.split(unified)
    )
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def prepare_resource(resource: ResourceIn) -> dict[str, Any]:
    """Build the engine resource record for one supported resource."""

    if resource.resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise ServiceError(
            ErrorCode.UNSUPPORTED_RESOURCE_TYPE,
            "This resource type is not supported by this release. "
            "Supported types: " + ", ".join(SUPPORTED_RESOURCE_TYPES) + ".",
            status_code=422,
            details=[
                FieldError(
                    loc="resource.resource_type",
                    message="Unsupported resource type.",
                )
            ],
        )

    title = normalize_whitespace(resource.title)
    text = normalize_paragraphs(resource.text)

    if not title or not text or not tokenize(f"{title} {text}"):
        raise ServiceError(
            ErrorCode.INVALID_RESOURCE,
            "The resource contains no searchable text.",
            status_code=422,
            details=[
                FieldError(
                    loc="resource.text",
                    message="No searchable text remains after normalisation.",
                )
            ],
        )

    search_text = (
        normalize_whitespace(resource.search_text)
        if resource.search_text
        else combine_text(title, text)
    )
    resource_id = resource.resource_id

    record: dict[str, Any] = {
        "runtime_resource_id": resource_id,
        "resource_id": resource_id,
        "resource_type": resource.resource_type,
        "title": title,
        "text": text,
        "search_text": search_text,
        "raw_text_hash": sha256_text(resource.text),
        "normalized_text_hash": sha256_text(text),
        "course_id": resource.course_id,
        "course_module_id": resource.course_module_id,
        # Never None: the engine would print the word "None" into the prompt.
        "course_shortname": normalize_whitespace(resource.course_shortname),
        "course_fullname": normalize_whitespace(resource.course_fullname),
        "section_name": normalize_whitespace(resource.section_name),
        "activity_name": normalize_whitespace(resource.activity_name) or title,
        "source_type": "moodle",
        "source_reference": resource_id,
        "source_structure": "heading_paragraph",
        "source_extraction": SOURCE_EXTRACTION,
        "research_status": "RUNTIME_DEMO",
        "metadata": {},
    }
    contract_errors = validate_resource_record(record)

    if contract_errors:
        raise ServiceError(
            ErrorCode.INVALID_RESOURCE,
            "The resource does not satisfy the connector contract.",
            status_code=422,
            details=[
                FieldError(loc="resource", message=message)
                for message in contract_errors
            ],
        )

    return record


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def validate_config(config: AnalysisConfigIn) -> None:
    """Refuse options the engine cannot honour without being changed.

    ``top_k`` is a constant inside the engine, and the evaluated configuration
    is Top-5. Accepting another value would report a setting that was not used.
    """

    if config.top_k not in (None, RETRIEVAL_TOP_K):
        raise ServiceError(
            ErrorCode.UNSUPPORTED_CONFIG,
            f"top_k must be {RETRIEVAL_TOP_K}, the evaluated configuration.",
            status_code=422,
            details=[
                FieldError(
                    loc="config.top_k",
                    message=f"Only {RETRIEVAL_TOP_K} is supported.",
                )
            ],
        )


# --------------------------------------------------------------------------- #
# Result mapping
# --------------------------------------------------------------------------- #


def _truncate(value: object) -> str:
    text = str(value)

    if len(text) <= MAX_DIAGNOSTIC_DETAIL_CHARS:
        return text

    return text[: MAX_DIAGNOSTIC_DETAIL_CHARS - 3] + "..."


def _best_ranks(
    candidate_sets: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], int]:
    ranks: dict[tuple[str, str], int] = {}

    for candidate_set in candidate_sets:
        fragment_id = str(candidate_set.get("fragment_id", "")).strip()

        for candidate in candidate_set.get("candidates") or []:
            idnumber = str(candidate.get("idnumber", "")).strip()
            ranks[(fragment_id, idnumber)] = int(candidate.get("rank", 0))

    return ranks


def _evidence_for(
    idnumber: str,
    fragment_ids: Sequence[str],
    valid_by_fragment: Mapping[str, Mapping[str, Any]],
) -> list[EvidenceOut]:
    evidence: list[EvidenceOut] = []
    seen: set[tuple[str, str]] = set()

    for fragment_id in fragment_ids:
        record = valid_by_fragment.get(fragment_id, {})

        for selection in record.get("selected") or []:
            if str(selection.get("idnumber", "")).strip() != idnumber:
                continue

            for quote in selection.get("evidence") or []:
                key = (fragment_id, str(quote))

                if key in seen:
                    continue

                seen.add(key)
                evidence.append(
                    EvidenceOut(fragment_id=fragment_id, quote=str(quote))
                )

    return evidence


def _warnings_by_competency(
    resource_warnings: Sequence[Mapping[str, Any]],
) -> dict[str, list[WarningOut]]:
    """Turn the engine's resource-level hierarchy warnings into structured ones.

    The engine card text is not reused: it states that a parent was removed,
    which is untrue for the original view returned here, where no suggestion is
    altered or dropped.
    """

    collected: dict[str, dict[tuple[str, str | None], WarningOut]] = defaultdict(
        dict
    )

    for warning in resource_warnings:
        code = str(warning.get("warning_type") or "")
        parent_id = str(warning.get("parent_id") or "").strip()
        child_id = str(warning.get("child_id") or "").strip()

        for idnumber, role, related in (
            (parent_id, "parent", child_id),
            (child_id, "child", parent_id),
        ):
            if not idnumber:
                continue

            related_id = related or None
            template = _WARNING_MESSAGES.get((code, role))
            message = (
                template.format(related=related_id)
                if template and related_id
                else _GENERIC_WARNING_MESSAGE
            )
            collected[idnumber][(code, related_id)] = WarningOut(
                code=code,
                role=role if related_id else None,
                related_idnumber=related_id,
                message=message,
            )

    return {
        idnumber: [
            warnings[key]
            for key in sorted(warnings, key=lambda item: (item[0], item[1] or ""))
        ]
        for idnumber, warnings in collected.items()
    }


def _diagnostics(
    invalid_records: Sequence[Mapping[str, Any]],
    candidate_sets: Sequence[Mapping[str, Any]],
) -> list[DiagnosticOut]:
    diagnostics: list[DiagnosticOut] = []

    for record in invalid_records:
        errors = record.get("validation_errors") or record.get("errors") or []
        diagnostics.append(
            DiagnosticOut(
                code="fragment_response_invalid",
                fragment_id=str(record.get("fragment_id", "")) or None,
                message=(
                    "The model response for this fragment failed validation "
                    "and was discarded."
                ),
                details=[
                    _truncate(error) for error in errors[:MAX_DIAGNOSTIC_DETAILS]
                ],
            )
        )

    for candidate_set in candidate_sets:
        if candidate_set.get("all_scores_zero") is True:
            diagnostics.append(
                DiagnosticOut(
                    code="retrieval_no_signal",
                    fragment_id=str(candidate_set.get("fragment_id", "")) or None,
                    message=(
                        "No competency shares vocabulary with this fragment "
                        "(all BM25 scores are zero)."
                    ),
                )
            )

    return diagnostics


def _suggestion_sort_key(suggestion: SuggestionOut) -> tuple[Any, ...]:
    return (
        -suggestion.support_count,
        -(suggestion.confidence if suggestion.confidence is not None else 0.0),
        suggestion.bm25_rank if suggestion.bm25_rank is not None else 10**6,
        suggestion.competency_idnumber,
    )


def _assert_response_invariants(
    suggestions: Sequence[SuggestionOut],
    catalogue: PreparedCatalogue,
    fragment_texts: Mapping[str, str],
) -> None:
    """Re-check, at the service boundary, what the engine already validated.

    Every suggestion must name a competency from the supplied catalogue, carry
    evidence, and quote it exactly from its own fragment. A violation is a bug
    or a changed engine, so nothing is returned to Moodle.
    """

    for suggestion in suggestions:
        valid = (
            suggestion.competency_idnumber in catalogue.idnumbers
            and bool(suggestion.evidence)
            and all(
                item.quote in fragment_texts.get(item.fragment_id, "")
                for item in suggestion.evidence
            )
        )

        if not valid:
            raise ServiceError(
                ErrorCode.RESPONSE_VALIDATION_FAILED,
                "The analysis result failed validation and was withheld.",
                status_code=500,
            )


def build_response(
    analysis: Mapping[str, Any],
    *,
    resource_id: str,
    resource_hash: str,
    catalogue: PreparedCatalogue,
    max_suggestions: int,
    duration_ms: int,
) -> AnalysisResponse:
    """Map one engine analysis onto the public response contract."""

    fragment_texts = {
        str(fragment["fragment_id"]): str(fragment.get("text") or "")
        for fragment in analysis["fragments"]
    }
    predictions = list(analysis["validated_predictions"])
    valid_records = [item for item in predictions if item.get("valid") is True]
    invalid_records = [item for item in predictions if item.get("valid") is not True]

    if not valid_records:
        raise ServiceError(
            ErrorCode.MODEL_OUTPUT_INVALID,
            "The model returned no response that passed validation.",
            status_code=502,
            retryable=True,
        )

    valid_by_fragment = {
        str(item["fragment_id"]): item for item in valid_records
    }
    ranks = _best_ranks(analysis["retrieval"])
    warnings = _warnings_by_competency(analysis["resource_warnings"])
    aggregated = next(iter(analysis["original_aggregation"]), {})
    suggestions: list[SuggestionOut] = []

    for entry in aggregated.get("predicted_competencies") or []:
        idnumber = str(entry["competency_id"]).strip()
        fragment_ids = [str(value) for value in entry.get("fragment_ids") or []]
        fragment_ranks = [
            ranks[(fragment_id, idnumber)]
            for fragment_id in fragment_ids
            if (fragment_id, idnumber) in ranks
        ]
        suggestions.append(
            SuggestionOut(
                competency_idnumber=idnumber,
                confidence=entry.get("max_confidence"),
                bm25_rank=min(fragment_ranks) if fragment_ranks else None,
                support_count=int(entry.get("support_count", len(fragment_ids))),
                evidence=_evidence_for(idnumber, fragment_ids, valid_by_fragment),
                warnings=warnings.get(idnumber, []),
            )
        )

    suggestions.sort(key=_suggestion_sort_key)
    diagnostics = _diagnostics(invalid_records, analysis["retrieval"])
    omitted = max(len(suggestions) - max_suggestions, 0)

    if omitted:
        diagnostics.append(
            DiagnosticOut(
                code="suggestions_truncated",
                message=(
                    f"{omitted} further suggestion(s) were omitted because "
                    f"max_suggestions is {max_suggestions}."
                ),
            )
        )

    returned = suggestions[:max_suggestions]
    _assert_response_invariants(returned, catalogue, fragment_texts)

    return AnalysisResponse(
        schema_version=SCHEMA_VERSION,
        analysis_id=str(analysis["analysis_id"]),
        status="completed",
        resource_id=resource_id,
        manifest=ManifestOut(
            backend=str(analysis["backend"]),
            model=str(analysis["model"]),
            prompt_version=str(analysis["prompt_version"]),
            top_k=int(analysis["candidate_count"]),
            max_selections_per_fragment=int(analysis["max_selections"]),
            competency_catalogue_hash=catalogue.content_hash,
            resource_hash=resource_hash,
            fragment_count=len(fragment_texts),
            completeness=(
                "complete"
                if analysis.get("aggregation_status") == "complete"
                else "partial"
            ),
            analysed_at=str(analysis["analysis_timestamp"]),
            duration_ms=duration_ms,
        ),
        suggestions=returned,
        abstained=not suggestions,
        diagnostics=diagnostics,
    )


# --------------------------------------------------------------------------- #
# Adapter
# --------------------------------------------------------------------------- #


def default_backend_factory(settings: Settings) -> AlignmentBackend:
    """Create the configured backend. ``mock`` is explicit and never default."""

    if settings.backend == "mock":
        return create_mock_backend()

    return create_runtime_backend(settings.backend, model=settings.model)


class AlignmentAdapter:
    """Run the research engine for one request and return the public result."""

    def __init__(
        self,
        settings: Settings,
        *,
        backend_factory: BackendFactory | None = None,
    ) -> None:
        self._settings = settings
        self._backend_factory = backend_factory or default_backend_factory

    def analyse(
        self,
        request: AnalysisRequest,
        *,
        request_id: str,
    ) -> AnalysisResponse:
        if request.schema_version != SCHEMA_VERSION:
            raise ServiceError(
                ErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                f"Only schema_version {SCHEMA_VERSION} is supported.",
                status_code=422,
                details=[
                    FieldError(
                        loc="schema_version",
                        message=f"Expected {SCHEMA_VERSION}.",
                    )
                ],
            )

        validate_config(request.config)
        catalogue = prepare_catalogue(request.competencies)
        resource = prepare_resource(request.resource)
        backend = self._backend_factory(self._settings)
        started = time.perf_counter()

        try:
            # A throwaway root keeps the engine from creating directories in the
            # repository, and keeps its manifest away from the frozen files.
            with tempfile.TemporaryDirectory(prefix="compalign-") as workdir:
                root = Path(workdir)
                analysis = analyze_runtime_resource(
                    resource,
                    backend=backend,
                    competencies=catalogue.records,
                    persist=False,
                    paths=runtime_paths(root),
                    project_root=root,
                )
        except BackendUnavailableError as exc:
            logger.warning(
                "backend unavailable request_id=%s backend=%s",
                request_id,
                self._settings.backend,
            )
            raise ServiceError(
                ErrorCode.BACKEND_UNAVAILABLE,
                "The configured model backend is not available.",
                status_code=503,
                retryable=True,
            ) from exc
        except NoUsableFragmentsError as exc:
            raise ServiceError(
                ErrorCode.NO_USABLE_FRAGMENTS,
                "The resource produced no usable fragments.",
                status_code=422,
            ) from exc
        except RuntimeAnalysisError as exc:
            logger.error(
                "analysis failed request_id=%s error=%s",
                request_id,
                type(exc).__name__,
            )
            raise ServiceError(
                ErrorCode.ANALYSIS_FAILED,
                "The analysis could not be completed.",
                status_code=500,
            ) from exc
        except ValueError as exc:
            logger.warning(
                "engine rejected input request_id=%s error=%s",
                request_id,
                exc,
            )
            raise ServiceError(
                ErrorCode.ENGINE_INPUT_REJECTED,
                "The alignment engine could not process the supplied "
                "resource or catalogue.",
                status_code=422,
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        response = build_response(
            analysis,
            resource_id=request.resource.resource_id,
            resource_hash=HASH_PREFIX + str(resource["normalized_text_hash"]),
            catalogue=catalogue,
            max_suggestions=request.config.max_suggestions,
            duration_ms=duration_ms,
        )
        logger.info(
            "analysis completed request_id=%s resource_id=%s backend=%s "
            "fragments=%d suggestions=%d completeness=%s duration_ms=%d",
            request_id,
            response.resource_id,
            response.manifest.backend,
            response.manifest.fragment_count,
            len(response.suggestions),
            response.manifest.completeness,
            duration_ms,
        )
        return response
