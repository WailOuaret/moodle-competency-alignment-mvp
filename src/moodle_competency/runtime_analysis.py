"""Teacher-facing runtime analysis using the evaluated research pipeline.

Runtime analyses are stored under data/runtime/. Frozen Gemini/Ollama
experiment files are never rewritten.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from moodle_competency.aggregation import aggregate_fragment_predictions
from moodle_competency.annotation import load_jsonl
from moodle_competency.fragmentation import create_fragments
from moodle_competency.graph_checks import (
    apply_child_preference,
    build_hierarchy_index,
    collect_fragment_warnings,
    collect_resource_warnings,
)
from moodle_competency.html_clean import normalize_whitespace
from moodle_competency.llm_tasks import (
    build_alignment_task,
    build_competency_lookup,
)
from moodle_competency.llm_validation import validate_alignment_response
from moodle_competency.resource_ingestion import (
    EXTRACTOR_VERSION,
    NORMALIZATION_VERSION,
    sha256_text,
)
from moodle_competency.retrieval import retrieve_candidates
from moodle_competency.reproducibility import file_sha256
from moodle_competency.runtime_storage import (
    RuntimePaths,
    ensure_runtime_dirs,
    redact_secrets,
    runtime_paths,
    save_analysis_artefacts,
)
from moodle_competency.settings import PROJECT_ROOT


FRAGMENTER_VERSION = "1.0"
PROMPT_VERSION = "1.0"
RETRIEVAL_TOP_K = 5
MAX_SELECTIONS = 3
TEMPERATURE = 0.0
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
DEFAULT_OLLAMA_MODEL = "mistral:latest"

ANALYSIS_STAGES = (
    "Extracting text",
    "Fragmenting resource",
    "Retrieving competency candidates",
    "Running competency alignment",
    "Validating evidence",
    "Checking hierarchy",
    "Aggregating resource competencies",
)

ProgressCallback = Callable[[int, str], None]


class RuntimeAnalysisError(RuntimeError):
    """Raised when a runtime analysis cannot complete."""


class BackendUnavailableError(RuntimeAnalysisError):
    """Raised when the chosen model backend cannot be used."""


class InvalidModelJsonError(RuntimeAnalysisError):
    """Raised when the model does not return a JSON object."""


class NoUsableFragmentsError(RuntimeAnalysisError):
    """Raised when fragmentation produces no usable fragments."""


class AlignmentBackend(Protocol):
    backend_name: str
    model: str
    temperature: float
    prompt_version: str

    def is_available(self) -> tuple[bool, str]:
        ...

    def align(
        self,
        task: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
        ...


class MockAlignmentBackend:
    """Injectable backend for tests. Never calls Gemini or Ollama."""

    backend_name = "mock"
    temperature = TEMPERATURE
    prompt_version = PROMPT_VERSION

    def __init__(
        self,
        handler: Callable[[Mapping[str, Any]], Any],
        *,
        model: str = "mock-model",
    ) -> None:
        self.handler = handler
        self.model = model

    def is_available(self) -> tuple[bool, str]:
        return True, ""

    def align(
        self,
        task: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
        result = self.handler(task)

        if isinstance(result, str):
            raise InvalidModelJsonError(
                "LLM invalid JSON: response was not a JSON object."
            )

        if not isinstance(result, dict):
            raise InvalidModelJsonError(
                "LLM invalid JSON: response was not a JSON object."
            )

        return result, {"mock_raw": copy.deepcopy(result)}, {}


class GeminiRuntimeBackend:
    backend_name = "gemini"
    temperature = TEMPERATURE
    prompt_version = PROMPT_VERSION

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = (
            model
            or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        ).strip() or DEFAULT_GEMINI_MODEL
        self._api_key = api_key
        self._client = client

    def is_available(self) -> tuple[bool, str]:
        if self._client is not None:
            return True, ""

        key = (
            self._api_key
            or os.getenv("GEMINI_API_KEY", "")
        ).strip()

        if not key:
            return False, "Gemini backend unavailable."

        return True, ""

    def align(
        self,
        task: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
        available, message = self.is_available()

        if not available:
            raise BackendUnavailableError(message)

        from moodle_competency.gemini_alignment import (
            GeminiAlignmentClient,
            GeminiAlignmentError,
        )

        client = self._client
        owns_client = False

        if client is None:
            client = GeminiAlignmentClient(
                api_key=(
                    self._api_key
                    or os.getenv("GEMINI_API_KEY", "")
                ).strip(),
                model=self.model,
            )
            owns_client = True

        try:
            parsed, raw, usage = client.align(task)
            usage_payload = (
                usage.to_dict() if hasattr(usage, "to_dict") else dict(usage)
            )
            return parsed, raw if isinstance(raw, dict) else {"raw": raw}, usage_payload
        except GeminiAlignmentError as exc:
            raise BackendUnavailableError(
                "Gemini API unavailable."
            ) from exc
        finally:
            if owns_client and hasattr(client, "close"):
                client.close()


class OllamaRuntimeBackend:
    backend_name = "ollama"
    temperature = TEMPERATURE
    prompt_version = PROMPT_VERSION

    def __init__(
        self,
        *,
        model: str | None = None,
        client: Any | None = None,
        probe: Callable[[], list[str]] | None = None,
    ) -> None:
        self.model = (
            model
            or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        ).strip() or DEFAULT_OLLAMA_MODEL
        self._client = client
        self._probe = probe

    def is_available(self) -> tuple[bool, str]:
        if self._client is not None:
            return True, ""

        try:
            if self._probe is not None:
                names = self._probe()
            else:
                from moodle_competency.ollama_alignment import (
                    OllamaAlignmentClient,
                )

                with OllamaAlignmentClient(model=self.model) as client:
                    names = client.list_model_names()
        except Exception:
            return False, "Ollama backend unavailable."

        allowed = set(names)
        allowed.update(name.split(":", 1)[0] for name in names)

        if self.model not in allowed and self.model.split(":", 1)[0] not in allowed:
            return False, "Ollama backend unavailable."

        return True, ""

    def align(
        self,
        task: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
        available, message = self.is_available()

        if not available:
            raise BackendUnavailableError(message)

        from moodle_competency.ollama_alignment import (
            OllamaAlignmentClient,
            OllamaAlignmentError,
        )

        client = self._client
        owns_client = False

        if client is None:
            client = OllamaAlignmentClient(model=self.model)
            owns_client = True

        try:
            parsed, raw, usage = client.align(task)
            usage_payload = (
                usage.to_dict() if hasattr(usage, "to_dict") else dict(usage)
            )
            return parsed, raw if isinstance(raw, dict) else {"raw": raw}, usage_payload
        except OllamaAlignmentError as exc:
            raise BackendUnavailableError(
                "Ollama backend unavailable."
            ) from exc
        finally:
            if owns_client and hasattr(client, "close"):
                client.close()


def utc_timestamp(moment: datetime | None = None) -> str:
    value = moment or datetime.now(timezone.utc)
    return value.replace(microsecond=0).isoformat()


def load_competencies(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    competency_path = path or (
        PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
    )
    return load_jsonl(competency_path)


def catalogue_ids(competencies: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(item.get("idnumber", "")).strip()
        for item in competencies
        if str(item.get("idnumber", "")).strip()
    ]


def create_runtime_backend(
    backend: str,
    *,
    model: str | None = None,
    client: Any | None = None,
) -> AlignmentBackend:
    name = str(backend or "").strip().casefold()

    if name == "gemini":
        return GeminiRuntimeBackend(model=model, client=client)

    if name == "ollama":
        return OllamaRuntimeBackend(model=model, client=client)

    if name == "mock":
        raise RuntimeAnalysisError(
            "Mock backend must be constructed explicitly for tests."
        )

    raise RuntimeAnalysisError(f"Unknown runtime backend: {backend!r}.")


def gemini_backend_status() -> dict[str, Any]:
    configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or (
        DEFAULT_GEMINI_MODEL
    )
    return {
        "backend": "gemini",
        "available": configured,
        "model": model if configured else None,
        "message": "" if configured else "Gemini backend unavailable.",
    }


def ollama_backend_status(
    probe: Callable[[], list[str]] | None = None,
) -> dict[str, Any]:
    backend = OllamaRuntimeBackend(probe=probe)
    available, message = backend.is_available()
    return {
        "backend": "ollama",
        "available": available,
        "model": backend.model if available else None,
        "message": message,
    }


def available_runtime_backends(
    *,
    ollama_probe: Callable[[], list[str]] | None = None,
    include_ollama_probe: bool = True,
) -> list[dict[str, Any]]:
    backends = [gemini_backend_status()]

    if include_ollama_probe:
        backends.append(ollama_backend_status(probe=ollama_probe))
    else:
        backends.append(
            {
                "backend": "ollama",
                "available": False,
                "model": DEFAULT_OLLAMA_MODEL,
                "message": "Ollama backend unavailable.",
            }
        )

    return backends


def fragment_runtime_resource(
    resource: Mapping[str, Any],
) -> list[dict[str, Any]]:
    fragments = create_fragments([resource])

    if not fragments:
        raise NoUsableFragmentsError(
            "Fragmentation returned no usable fragments."
        )

    normalized = str(resource.get("text") or "")
    search_offset = 0
    enriched: list[dict[str, Any]] = []

    for fragment in fragments:
        text = str(fragment.get("text") or "")
        start = normalized.find(text, search_offset)

        if start < 0:
            start = normalized.find(text)

        end = start + len(text) if start >= 0 else 0

        if start >= 0:
            search_offset = end

        record = dict(fragment)
        record["runtime_resource_id"] = resource["runtime_resource_id"]
        record["source_structure"] = resource.get(
            "source_structure",
            "paragraph",
        )
        record["start_offset"] = start if start >= 0 else None
        record["end_offset"] = end if start >= 0 else None
        record["content_hash"] = sha256_text(text)
        enriched.append(record)

    return enriched


def _notify(progress: ProgressCallback | None, index: int) -> None:
    if progress is not None:
        progress(index, ANALYSIS_STAGES[index - 1])


def _make_analysis_id(
    *,
    resource_id: str,
    backend: str,
    model: str,
    timestamp: str,
) -> str:
    digest = hashlib.sha256(
        f"{resource_id}|{backend}|{model}|{timestamp}".encode("utf-8")
    ).hexdigest()[:16]
    return f"an_{digest}"


def _parse_model_json(parsed: Any) -> dict[str, Any]:
    if isinstance(parsed, dict):
        return parsed

    if isinstance(parsed, str):
        try:
            loaded = json.loads(parsed)
        except json.JSONDecodeError as exc:
            raise InvalidModelJsonError(
                "LLM invalid JSON: response was not a JSON object."
            ) from exc

        if isinstance(loaded, dict):
            return loaded

    raise InvalidModelJsonError(
        "LLM invalid JSON: response was not a JSON object."
    )


def _english_label(competency: Mapping[str, Any]) -> str:
    description = str(competency.get("description_text") or "")
    marker = "English label:"

    if marker in description:
        remainder = description.split(marker, 1)[1]
        label = remainder.split("UTC competency")[0].strip()

        if label:
            return label

    return str(competency.get("shortname") or competency.get("idnumber") or "")


def _bm25_ranks_for_competency(
    competency_id: str,
    candidate_sets: Sequence[Mapping[str, Any]],
    fragment_ids: Sequence[str],
) -> list[int]:
    ranks: list[int] = []
    wanted = set(fragment_ids)

    for candidate_set in candidate_sets:
        if str(candidate_set.get("fragment_id", "")).strip() not in wanted:
            continue

        for candidate in candidate_set.get("candidates") or []:
            if str(candidate.get("idnumber", "")).strip() == competency_id:
                ranks.append(int(candidate.get("rank", 0)))

    return sorted(set(ranks))


def _label_set(record: Mapping[str, Any]) -> list[str]:
    return [
        str(item.get("idnumber", "")).strip()
        for item in record.get("selected") or []
        if str(item.get("idnumber", "")).strip()
    ]


def build_suggestion_cards(
    *,
    resource: Mapping[str, Any],
    fragments: Sequence[Mapping[str, Any]],
    candidate_sets: Sequence[Mapping[str, Any]],
    original_predictions: Sequence[Mapping[str, Any]],
    reconciled_predictions: Sequence[Mapping[str, Any]],
    original_aggregation: Sequence[Mapping[str, Any]],
    reconciled_aggregation: Sequence[Mapping[str, Any]],
    fragment_warnings: Sequence[Mapping[str, Any]],
    resource_warnings: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    competency_lookup = {
        str(item.get("idnumber", "")).strip(): item
        for item in competencies
    }
    fragments_by_id = {
        str(item.get("fragment_id", "")).strip(): item
        for item in fragments
    }
    original_by_fragment = {
        str(item.get("fragment_id", "")).strip(): item
        for item in original_predictions
    }
    reconciled_by_fragment = {
        str(item.get("fragment_id", "")).strip(): item
        for item in reconciled_predictions
    }
    original_resource = next(iter(original_aggregation), {})
    reconciled_resource = next(iter(reconciled_aggregation), {})
    reconciled_ids = {
        str(item.get("competency_id", "")).strip()
        for item in reconciled_resource.get("predicted_competencies") or []
    }
    warning_text_by_competency: dict[str, list[str]] = {}

    for warning in list(fragment_warnings) + list(resource_warnings):
        warning_type = str(warning.get("warning_type", "")).strip()
        parent_id = str(warning.get("parent_id", "")).strip()
        child_id = str(warning.get("child_id", "")).strip()

        if warning_type in {
            "parent_child_redundancy",
            "granularity_mismatch",
        }:
            message = (
                "Broad parent removed because a directly related child "
                "competency was also predicted."
                if warning_type == "parent_child_redundancy"
                else "Granularity warning: parent and child competencies "
                "were both predicted."
            )
            for competency_id in (parent_id, child_id):
                if competency_id:
                    warning_text_by_competency.setdefault(
                        competency_id,
                        [],
                    ).append(message)

    cards: list[dict[str, Any]] = []

    for predicted in original_resource.get("predicted_competencies") or []:
        competency_id = str(predicted.get("competency_id", "")).strip()
        competency = competency_lookup.get(competency_id, {})
        supporting_ids = [
            str(value).strip()
            for value in predicted.get("fragment_ids") or []
        ]
        supports: list[dict[str, Any]] = []

        for fragment_id in supporting_ids:
            fragment = fragments_by_id.get(fragment_id, {})
            original = original_by_fragment.get(fragment_id, {})
            quotes: list[str] = []

            for selection in original.get("selected") or []:
                if str(selection.get("idnumber", "")).strip() == competency_id:
                    quotes.extend(
                        str(quote)
                        for quote in selection.get("evidence") or []
                        if str(quote).strip()
                    )

            supports.append(
                {
                    "fragment_id": fragment_id,
                    "fragment_text": fragment.get("text", ""),
                    "quotes": quotes,
                }
            )

        original_labels: list[str] = []
        reconciled_labels: list[str] = []

        for fragment_id in supporting_ids:
            original_labels.extend(
                _label_set(original_by_fragment.get(fragment_id, {}))
            )
            reconciled_labels.extend(
                _label_set(reconciled_by_fragment.get(fragment_id, {}))
            )

        warnings = list(
            dict.fromkeys(warning_text_by_competency.get(competency_id, []))
        )

        cards.append(
            {
                "competency_id": competency_id,
                "competency_name": competency.get("shortname", competency_id),
                "english_label": _english_label(competency),
                "competency_description": competency.get(
                    "description_text",
                    "",
                ),
                "suggested_confidence": predicted.get("max_confidence"),
                "mean_confidence": predicted.get("mean_confidence"),
                "confidences": list(predicted.get("confidences") or []),
                "support_count": predicted.get("support_count", 0),
                "supporting_fragment_ids": supporting_ids,
                "supporting_fragments": supports,
                "evidence_quotes": list(predicted.get("evidence") or []),
                "bm25_ranks": _bm25_ranks_for_competency(
                    competency_id,
                    candidate_sets,
                    supporting_ids,
                ),
                "hierarchy_warnings": warnings,
                "hierarchy_label": (
                    "; ".join(warnings) if warnings else "No warning"
                ),
                "original_prediction": True,
                "reconciled_prediction": competency_id in reconciled_ids,
                "original_labels": sorted(set(original_labels)),
                "reconciled_labels": sorted(set(reconciled_labels)),
                "course_id": resource.get("course_id"),
                "course_shortname": resource.get("course_shortname"),
                "runtime_resource_id": resource.get("runtime_resource_id"),
                "title": resource.get("title"),
            }
        )

    return cards


def analyze_runtime_resource(
    resource: Mapping[str, Any],
    *,
    backend: str | AlignmentBackend = "gemini",
    model: str | None = None,
    competencies: Sequence[Mapping[str, Any]] | None = None,
    persist: bool = True,
    paths: RuntimePaths | None = None,
    project_root: Path | None = None,
    progress: ProgressCallback | None = None,
    reconciled_view: bool = True,
) -> dict[str, Any]:
    """Run the evaluated pipeline on one runtime resource.

    `backend` may be \"gemini\", \"ollama\", or an injectable AlignmentBackend.
    Live Gemini/Ollama are not invoked when a mock backend is supplied.
    """

    root = Path(project_root or PROJECT_ROOT)
    resolved_paths = ensure_runtime_dirs(paths or runtime_paths(root))
    catalogue = list(competencies or load_competencies())

    if isinstance(backend, str):
        adapter: AlignmentBackend = create_runtime_backend(
            backend,
            model=model,
        )
    else:
        adapter = backend

    available, message = adapter.is_available()

    if not available:
        raise BackendUnavailableError(message)

    timestamp = utc_timestamp()
    analysis_id = _make_analysis_id(
        resource_id=str(resource["runtime_resource_id"]),
        backend=adapter.backend_name,
        model=adapter.model,
        timestamp=timestamp,
    )

    _notify(progress, 1)
    extracted = dict(resource)

    _notify(progress, 2)
    fragments = fragment_runtime_resource(extracted)

    _notify(progress, 3)
    candidate_sets = retrieve_candidates(
        fragments=fragments,
        competencies=catalogue,
        top_k=RETRIEVAL_TOP_K,
    )
    lookup = build_competency_lookup(catalogue)
    tasks = [
        build_alignment_task(
            candidate_set=candidate_set,
            competency_lookup=lookup,
        )
        for candidate_set in candidate_sets
    ]

    _notify(progress, 4)
    raw_responses: list[dict[str, Any]] = []
    validated_responses: list[dict[str, Any]] = []

    for task in tasks:
        raw_record: dict[str, Any] = {
            "fragment_id": task["fragment_id"],
            "analysis_id": analysis_id,
            "backend": adapter.backend_name,
            "model": adapter.model,
            "temperature": adapter.temperature,
            "prompt_version": adapter.prompt_version,
        }

        try:
            parsed, raw, usage = adapter.align(task)
            parsed_json = _parse_model_json(parsed)
            raw_record["raw_response"] = redact_secrets(raw)
            raw_record["usage"] = redact_secrets(dict(usage))
            raw_record["parsed_response"] = parsed_json
        except InvalidModelJsonError as exc:
            raw_record["error"] = str(exc)
            raw_record["valid"] = False
            raw_responses.append(raw_record)
            validated_responses.append(
                {
                    "fragment_id": task["fragment_id"],
                    "analysis_id": analysis_id,
                    "valid": False,
                    "errors": [str(exc)],
                    "abstain": False,
                    "selected": [],
                    "backend": adapter.backend_name,
                    "model": adapter.model,
                }
            )
            continue
        except BackendUnavailableError:
            raise

        raw_responses.append(raw_record)

        _notify(progress, 5)
        validated = validate_alignment_response(
            task=task,
            response=parsed_json,
        )
        validated["analysis_id"] = analysis_id
        validated["backend"] = adapter.backend_name
        validated["model"] = adapter.model
        validated["temperature"] = adapter.temperature
        validated["prompt_version"] = adapter.prompt_version
        validated_responses.append(validated)

    original_predictions = copy.deepcopy(validated_responses)

    _notify(progress, 6)
    hierarchy_index = build_hierarchy_index(catalogue)
    fragment_warnings = collect_fragment_warnings(
        original_predictions,
        hierarchy_index,
    )
    reconciled_predictions: list[dict[str, Any]] = []
    removed_by_fragment: dict[str, list[str]] = {}

    for record in original_predictions:
        copied, removed = apply_child_preference(record, hierarchy_index)
        reconciled_predictions.append(copied)
        fragment_id = str(record.get("fragment_id", "")).strip()

        if removed:
            removed_by_fragment[fragment_id] = list(removed)

    _notify(progress, 7)
    original_aggregation, aggregation_manifest = aggregate_fragment_predictions(
        fragments=fragments,
        resources=[extracted],
        competencies=catalogue,
        predictions=original_predictions,
        allow_partial=True,
    )
    reconciled_aggregation, _reconciled_manifest = aggregate_fragment_predictions(
        fragments=fragments,
        resources=[extracted],
        competencies=catalogue,
        predictions=reconciled_predictions,
        allow_partial=True,
    )
    resource_warnings = collect_resource_warnings(
        original_aggregation,
        hierarchy_index,
    )
    suggestion_cards = build_suggestion_cards(
        resource=extracted,
        fragments=fragments,
        candidate_sets=candidate_sets,
        original_predictions=original_predictions,
        reconciled_predictions=reconciled_predictions,
        original_aggregation=original_aggregation,
        reconciled_aggregation=reconciled_aggregation,
        fragment_warnings=fragment_warnings,
        resource_warnings=resource_warnings,
        competencies=catalogue,
    )

    analysis = {
        "analysis_id": analysis_id,
        "runtime_resource_id": extracted["runtime_resource_id"],
        "title": extracted.get("title"),
        "source_type": extracted.get("source_type"),
        "source_reference": extracted.get("source_reference"),
        "course_id": extracted.get("course_id"),
        "course_shortname": extracted.get("course_shortname"),
        "resource_type": extracted.get("resource_type"),
        "backend": adapter.backend_name,
        "model": adapter.model,
        "temperature": adapter.temperature,
        "prompt_version": adapter.prompt_version,
        "candidate_count": RETRIEVAL_TOP_K,
        "max_selections": MAX_SELECTIONS,
        "analysis_timestamp": timestamp,
        "fragment_count": len(fragments),
        "suggestion_count": len(suggestion_cards),
        "research_status": extracted.get("research_status"),
        "resource": extracted,
        "fragments": fragments,
        "retrieval": candidate_sets,
        "raw_responses": raw_responses,
        "validated_predictions": original_predictions,
        "reconciled_predictions": reconciled_predictions,
        "original_aggregation": original_aggregation,
        "reconciled_aggregation": reconciled_aggregation,
        "fragment_warnings": fragment_warnings,
        "resource_warnings": resource_warnings,
        "removed_parents_by_fragment": removed_by_fragment,
        "suggestion_cards": suggestion_cards,
        "reconciled_view_requested": reconciled_view,
        "hierarchy_check_label": "Post-processing hierarchy check",
        "aggregation_method": aggregation_manifest.get(
            "aggregation_version"
        ),
        "aggregation_status": aggregation_manifest.get(
            "prediction_completeness"
        ),
    }

    top5_lists = [
        {
            "fragment_id": item.get("fragment_id"),
            "candidates": [
                {
                    "competency_id": candidate.get("idnumber"),
                    "rank": candidate.get("rank"),
                    "bm25_score": candidate.get("bm25_score"),
                }
                for candidate in item.get("candidates") or []
            ],
        }
        for item in candidate_sets
    ]

    manifest = {
        "analysis_id": analysis_id,
        "runtime_resource_id": extracted["runtime_resource_id"],
        "resource_hash": extracted.get("normalized_text_hash"),
        "raw_text_hash": extracted.get("raw_text_hash"),
        "source": extracted.get("source_type"),
        "source_reference": extracted.get("source_reference"),
        "extractor_version": EXTRACTOR_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "fragmenter_version": FRAGMENTER_VERSION,
        "competency_catalogue_hash": file_sha256(
            root / "data" / "processed" / "competencies.jsonl"
        ),
        "retrieval_configuration": {
            "method": "bm25",
            "top_k": RETRIEVAL_TOP_K,
        },
        "top5_candidate_lists": top5_lists,
        "backend": adapter.backend_name,
        "model": adapter.model,
        "temperature": adapter.temperature,
        "prompt_version": adapter.prompt_version,
        "candidate_count": RETRIEVAL_TOP_K,
        "max_selections": MAX_SELECTIONS,
        "raw_response_references": [
            f"data/runtime/model_responses/{analysis_id}_raw.jsonl"
        ],
        "validated_predictions": [
            {
                "fragment_id": item.get("fragment_id"),
                "valid": item.get("valid"),
                "abstain": item.get("abstain"),
                "selected": _label_set(item),
                "errors": item.get("validation_errors")
                or item.get("errors")
                or [],
            }
            for item in original_predictions
        ],
        "hierarchy_warnings": fragment_warnings + resource_warnings,
        "reconciled_view_requested": reconciled_view,
        "aggregation_method": aggregation_manifest.get(
            "aggregation_version"
        ),
        "timestamp": timestamp,
        "research_status": "RUNTIME_DEMO",
    }

    if persist:
        save_analysis_artefacts(
            analysis_id=analysis_id,
            resource=extracted,
            fragments=fragments,
            retrieval=candidate_sets,
            raw_responses=raw_responses,
            validated_responses=original_predictions,
            analysis=analysis,
            manifest=manifest,
            paths=resolved_paths,
        )

    analysis["manifest"] = manifest
    return analysis
