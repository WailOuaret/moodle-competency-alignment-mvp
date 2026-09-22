"""Aggregate fragment-level constrained LLM predictions to resources."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import load_jsonl, stripped_text, write_json
from moodle_competency.llm_validation import write_jsonl


AGGREGATION_VERSION = "1.0"


class IncompletePredictionsError(ValueError):
    """Raised when Gemini coverage is incomplete and final write is refused."""


def utc_timestamp(moment: datetime | None = None) -> str:
    value = moment or datetime.now(timezone.utc)
    return value.replace(microsecond=0).isoformat()


def valid_predictions(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only locally validated non-duplicate fragment predictions."""

    seen: set[str] = set()
    selected: list[dict[str, Any]] = []

    for record in records:
        fragment_id = stripped_text(record.get("fragment_id"))

        if not fragment_id or fragment_id in seen:
            continue

        if record.get("valid") is not True:
            continue

        seen.add(fragment_id)
        selected.append(dict(record))

    return selected


def completeness_report(
    *,
    fragments: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare expected fragments with available valid predictions."""

    expected_ids = [
        stripped_text(fragment.get("fragment_id"))
        for fragment in fragments
        if stripped_text(fragment.get("fragment_id"))
    ]
    predicted_ids = {
        stripped_text(record.get("fragment_id"))
        for record in valid_predictions(predictions)
    }
    missing = [
        fragment_id
        for fragment_id in expected_ids
        if fragment_id not in predicted_ids
    ]
    unknown = sorted(
        predicted_ids - set(expected_ids)
    )

    return {
        "expected_fragments": len(expected_ids),
        "available_predicted_fragments": len(
            predicted_ids & set(expected_ids)
        ),
        "missing_fragment_ids": missing,
        "unknown_fragment_ids": unknown,
        "complete": not missing and not unknown,
    }


def _resource_lookup(
    resources: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {
        stripped_text(resource.get("resource_id")): resource
        for resource in resources
        if stripped_text(resource.get("resource_id"))
    }


def _competency_ids(
    competencies: Sequence[Mapping[str, Any]],
) -> set[str]:
    return {
        stripped_text(item.get("idnumber"))
        for item in competencies
        if stripped_text(item.get("idnumber"))
    }


def aggregate_fragment_predictions(
    *,
    fragments: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    allow_partial: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build resource-level predictions from fragment Gemini outputs.

    Page fragments aggregate onto their Page. Quiz questions remain
    independent resources. Missing fragment predictions make the result
    PARTIAL. Final writes require complete coverage unless allow_partial.
    """

    coverage = completeness_report(
        fragments=fragments,
        predictions=predictions,
    )
    resources_by_id = _resource_lookup(resources)
    allowed_ids = _competency_ids(competencies)
    fragments_by_id = {
        stripped_text(fragment.get("fragment_id")): fragment
        for fragment in fragments
        if stripped_text(fragment.get("fragment_id"))
    }
    predictions_by_id = {
        stripped_text(record.get("fragment_id")): record
        for record in valid_predictions(predictions)
    }

    errors: list[str] = []

    for fragment_id in coverage["unknown_fragment_ids"]:
        errors.append(f"Unknown predicted fragment: {fragment_id}")

    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for fragment in fragments:
        fragment_id = stripped_text(fragment.get("fragment_id"))
        resource_id = stripped_text(fragment.get("resource_id"))

        if resource_id not in resources_by_id:
            errors.append(
                f"Unknown resource for fragment {fragment_id}: "
                f"{resource_id}"
            )
            continue

        prediction = predictions_by_id.get(fragment_id)

        if prediction is None:
            continue

        if prediction.get("abstain") is True:
            continue

        for selection in prediction.get("selected") or []:
            competency_id = stripped_text(
                selection.get("idnumber")
            )

            if not competency_id:
                continue

            if competency_id not in allowed_ids:
                errors.append(
                    f"Unknown competency {competency_id} on "
                    f"{fragment_id}"
                )
                continue

            bucket = grouped[resource_id].setdefault(
                competency_id,
                {
                    "fragment_ids": [],
                    "evidence": [],
                    "confidences": [],
                },
            )

            if fragment_id not in bucket["fragment_ids"]:
                bucket["fragment_ids"].append(fragment_id)

            for quote in selection.get("evidence") or []:
                text = str(quote)

                if text and text not in bucket["evidence"]:
                    bucket["evidence"].append(text)

            confidence = selection.get("confidence")

            if isinstance(confidence, (int, float)):
                bucket["confidences"].append(float(confidence))

    resource_records: list[dict[str, Any]] = []

    for resource in resources:
        resource_id = stripped_text(resource.get("resource_id"))
        alignments = grouped.get(resource_id, {})
        predicted = []

        for competency_id in sorted(alignments):
            bucket = alignments[competency_id]
            confidences = bucket["confidences"]
            predicted.append(
                {
                    "competency_id": competency_id,
                    "fragment_ids": list(bucket["fragment_ids"]),
                    "evidence": list(bucket["evidence"]),
                    "confidences": confidences,
                    "support_count": len(bucket["fragment_ids"]),
                    "max_confidence": (
                        max(confidences) if confidences else None
                    ),
                    "mean_confidence": (
                        round(mean(confidences), 6)
                        if confidences
                        else None
                    ),
                }
            )

        resource_records.append(
            {
                "resource_id": resource_id,
                "course_id": resource.get("course_id"),
                "course_shortname": stripped_text(
                    resource.get("course_shortname")
                ),
                "resource_type": stripped_text(
                    resource.get("resource_type")
                ),
                "title": stripped_text(resource.get("title")),
                "activity_name": stripped_text(
                    resource.get("activity_name")
                ),
                "predicted_competencies": predicted,
                "fragment_ids": [
                    stripped_text(fragment.get("fragment_id"))
                    for fragment in fragments
                    if stripped_text(fragment.get("resource_id"))
                    == resource_id
                ],
            }
        )

    complete = coverage["complete"] and not errors
    status = "complete" if complete else "partial"

    if not allow_partial and not complete:
        raise IncompletePredictionsError(
            "Refusing to write a FINAL resource_predictions "
            "dataset because constrained Gemini is incomplete "
            f"({coverage['available_predicted_fragments']}/"
            f"{coverage['expected_fragments']} fragments). "
            "Missing: "
            + ", ".join(coverage["missing_fragment_ids"])
        )

    manifest = {
        "aggregation_version": AGGREGATION_VERSION,
        "prediction_completeness": status,
        "final": complete,
        "passed": complete,
        "allow_partial": allow_partial,
        "total_expected_fragments": coverage["expected_fragments"],
        "available_predicted_fragments": coverage[
            "available_predicted_fragments"
        ],
        "missing_fragment_ids": coverage["missing_fragment_ids"],
        "unknown_fragment_ids": coverage["unknown_fragment_ids"],
        "resource_count": len(resource_records),
        "competency_count": len(allowed_ids),
        "errors": errors,
        "timestamp": utc_timestamp(),
        "source_files": {
            "fragments": "data/processed/fragments.jsonl",
            "resources": "data/processed/resources.jsonl",
            "competencies": "data/processed/competencies.jsonl",
            "predictions": "data/interim/gemini_validated.jsonl",
        },
        "notes": (
            "PARTIAL outputs are development artefacts and must "
            "not be treated as final research results."
            if not complete
            else "All expected fragments have valid predictions."
        ),
        "represented_fragments": sorted(fragments_by_id),
    }

    return resource_records, manifest


def write_resource_predictions(
    records: Sequence[Mapping[str, Any]],
    output_path,
    manifest: Mapping[str, Any],
    manifest_path,
) -> None:
    """Write JSONL predictions and a companion manifest."""

    write_jsonl(records, output_path)
    write_json(manifest, manifest_path)
