"""Validate constrained LLM competency-alignment responses."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSON objects from a UTF-8 JSON Lines file."""

    if not path.exists():
        raise FileNotFoundError(
            f"JSONL file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} "
                    f"of {path}."
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} of {path} "
                    "is not a JSON object."
                )

            records.append(record)

    return records


def validate_alignment_response(
    *,
    task: Mapping[str, Any],
    response: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one response against its original constrained task."""

    errors: list[str] = []

    expected_fragment_id = str(
        task.get("fragment_id", "")
    ).strip()

    response_fragment_id = str(
        response.get("fragment_id", "")
    ).strip()

    allowed_idnumbers = {
        str(value).strip()
        for value in task.get(
            "allowed_idnumbers",
            [],
        )
        if str(value).strip()
    }

    fragment_text = str(
        task.get("fragment_text", "")
    )

    if not response_fragment_id:
        errors.append("Response fragment_id is empty.")
    elif response_fragment_id != expected_fragment_id:
        errors.append(
            "Response fragment_id does not match its task."
        )

    abstain = response.get("abstain")

    if not isinstance(abstain, bool):
        errors.append(
            "abstain must be a JSON boolean."
        )
        abstain = False

    selected_value = response.get("selected")

    if not isinstance(selected_value, list):
        errors.append(
            "selected must be a JSON list."
        )
        selected_items: list[Any] = []
    else:
        selected_items = selected_value

    if len(selected_items) > 3:
        errors.append(
            "No more than three competencies may be selected."
        )

    if abstain and selected_items:
        errors.append(
            "selected must be empty when abstain is true."
        )

    if not abstain and not selected_items:
        errors.append(
            "At least one competency is required when "
            "abstain is false."
        )

    selected_idnumbers: list[str] = []
    validated_selected: list[dict[str, Any]] = []

    for index, item in enumerate(
        selected_items,
        start=1,
    ):
        prefix = f"Selection {index}"

        if not isinstance(item, dict):
            errors.append(
                f"{prefix} must be a JSON object."
            )
            continue

        idnumber = str(
            item.get("idnumber", "")
        ).strip()

        if not idnumber:
            errors.append(
                f"{prefix} has an empty idnumber."
            )
        elif idnumber not in allowed_idnumbers:
            errors.append(
                f"{prefix} uses a competency outside "
                f"the allowed candidate set: {idnumber}"
            )

        selected_idnumbers.append(idnumber)

        evidence_value = item.get("evidence")

        if not isinstance(evidence_value, list):
            errors.append(
                f"{prefix} evidence must be a list."
            )
            evidence_items: list[Any] = []
        else:
            evidence_items = evidence_value

        if not evidence_items:
            errors.append(
                f"{prefix} requires at least one evidence quote."
            )

        validated_evidence: list[str] = []

        for evidence_index, raw_quote in enumerate(
            evidence_items,
            start=1,
        ):
            quote = str(raw_quote).strip()

            if not quote:
                errors.append(
                    f"{prefix} evidence {evidence_index} "
                    "is empty."
                )
                continue

            if quote not in fragment_text:
                errors.append(
                    f"{prefix} evidence {evidence_index} "
                    "is not an exact contiguous substring "
                    "of fragment_text."
                )

            validated_evidence.append(quote)

        reason = str(
            item.get("reason", "")
        ).strip()

        if not reason:
            errors.append(
                f"{prefix} reason is empty."
            )

        raw_confidence = item.get("confidence")

        if isinstance(raw_confidence, bool):
            confidence = None
        else:
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                confidence = None

        if (
            confidence is None
            or not math.isfinite(confidence)
            or confidence < 0.0
            or confidence > 1.0
        ):
            errors.append(
                f"{prefix} confidence must be a finite "
                "number from 0.0 to 1.0."
            )

        validated_selected.append(
            {
                "idnumber": idnumber,
                "evidence": validated_evidence,
                "reason": reason,
                "confidence": confidence,
            }
        )

    duplicate_selected_ids = sorted(
        idnumber
        for idnumber, count in Counter(
            selected_idnumbers
        ).items()
        if idnumber and count > 1
    )

    if duplicate_selected_ids:
        errors.append(
            "Duplicate selected competency IDs: "
            + ", ".join(duplicate_selected_ids)
        )

    overall_reason = str(
        response.get("overall_reason", "")
    ).strip()

    if not overall_reason:
        errors.append(
            "overall_reason is empty."
        )

    return {
        "task_id": task.get("task_id"),
        "fragment_id": expected_fragment_id,
        "selected": validated_selected,
        "abstain": abstain,
        "overall_reason": overall_reason,
        "model_provider": response.get(
            "model_provider"
        ),
        "model_name": response.get(
            "model_name"
        ),
        "validation_errors": errors,
        "valid": not errors,
    }


def validate_response_collection(
    *,
    tasks: Sequence[Mapping[str, Any]],
    responses: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    """Validate coverage and individual response constraints."""

    tasks_by_fragment: dict[
        str,
        Mapping[str, Any],
    ] = {}

    for task in tasks:
        fragment_id = str(
            task.get("fragment_id", "")
        ).strip()

        if fragment_id:
            tasks_by_fragment[fragment_id] = task

    response_fragment_ids = [
        str(
            response.get(
                "fragment_id",
                "",
            )
        ).strip()
        for response in responses
    ]

    duplicate_response_fragments = sorted(
        fragment_id
        for fragment_id, count in Counter(
            response_fragment_ids
        ).items()
        if fragment_id and count > 1
    )

    responses_by_fragment: dict[
        str,
        Mapping[str, Any],
    ] = {}

    for response in responses:
        fragment_id = str(
            response.get("fragment_id", "")
        ).strip()

        if (
            fragment_id
            and fragment_id not in responses_by_fragment
        ):
            responses_by_fragment[fragment_id] = response

    expected_fragment_ids = set(
        tasks_by_fragment
    )

    actual_fragment_ids = set(
        responses_by_fragment
    )

    missing_responses = sorted(
        expected_fragment_ids - actual_fragment_ids
    )

    unknown_responses = sorted(
        actual_fragment_ids - expected_fragment_ids
    )

    validated_records: list[dict[str, Any]] = []

    for fragment_id, task in tasks_by_fragment.items():
        response = responses_by_fragment.get(fragment_id)

        if response is None:
            continue

        validated_records.append(
            validate_alignment_response(
                task=task,
                response=response,
            )
        )

    invalid_records = [
        record
        for record in validated_records
        if not record["valid"]
    ]

    selected_alignment_count = sum(
        len(record["selected"])
        for record in validated_records
    )

    abstention_count = sum(
        record["abstain"] is True
        for record in validated_records
    )

    passed = (
        len(responses) == len(tasks)
        and not duplicate_response_fragments
        and not missing_responses
        and not unknown_responses
        and not invalid_records
    )

    summary = {
        "source_tasks": len(tasks),
        "source_responses": len(responses),
        "validated_responses":
            len(validated_records),
        "valid_responses": (
            len(validated_records)
            - len(invalid_records)
        ),
        "invalid_responses":
            len(invalid_records),
        "selected_alignments":
            selected_alignment_count,
        "abstentions": abstention_count,
        "duplicate_response_fragments":
            duplicate_response_fragments,
        "missing_responses":
            missing_responses,
        "unknown_responses":
            unknown_responses,
        "invalid_fragment_ids": [
            record["fragment_id"]
            for record in invalid_records
        ],
        "passed": passed,
    }

    return validated_records, summary


def write_jsonl(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> Path:
    """Write records as UTF-8 JSON Lines."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(
                    dict(record),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    return output_path.resolve()
