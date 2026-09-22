"""Derived resource-level evaluation against fragment-union reference.

Resource gold is DERIVED from human-reviewed fragment labels.
It is not a second independent annotation exercise.

Page gold = union of fragment labels on that Page.
Quiz-question gold = that question's fragment labels.

Do not read activity-level Moodle competency links.
Do not generate new Gemini or Ollama predictions.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import (
    parse_competency_ids,
    stripped_text,
)
from moodle_competency.error_analysis import parent_of
from moodle_competency.metrics import (
    abstention_rate,
    average_predicted_labels,
    coverage_rate,
    exact_set_match,
    instance_prf,
    macro_prf_views,
    micro_prf,
    per_label_prf,
)


RESOURCE_EVALUATION_VERSION = "1.0"

PAGE_DERIVATION = "union_of_human_reviewed_fragment_labels"
QUIZ_DERIVATION = "human_reviewed_question_fragment_label"

RESOURCE_TABLE_COLUMNS = (
    "resource_id",
    "course_shortname",
    "resource_type",
    "title",
    "fragment_count",
    "reference_competency_ids",
    "predicted_competency_ids",
    "reference_label_count",
    "predicted_label_count",
    "label_count_error",
    "true_positive_ids",
    "false_positive_ids",
    "false_negative_ids",
    "precision",
    "recall",
    "f1",
    "exact_set_match",
    "parent_child_redundancy",
)

EXAMPLE_COLUMNS = (
    "example_type",
    "resource_id",
    "resource_type",
    "title",
    "fragment_ids",
    "reference_competency_ids",
    "predicted_competency_ids",
    "true_positive_ids",
    "false_positive_ids",
    "false_negative_ids",
    "exact_set_match",
    "parent_child_redundancy",
    "short_factual_explanation",
)

PER_COMPETENCY_COLUMNS = (
    "competency_id",
    "support",
    "predicted_count",
    "true_positives",
    "false_positives",
    "false_negatives",
    "precision",
    "recall",
    "f1",
    "gold_supported",
)

KNOWN_RETRIEVAL_FAILURE_RESOURCE = "quiz_question:1:4"


class ResourceReferenceValidationError(ValueError):
    """Raised when derived resource reference construction is invalid."""


def competency_catalogue_ids(
    competencies: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Return competency idnumbers in catalogue order."""

    ids: list[str] = []
    seen: set[str] = set()

    for item in competencies:
        competency_id = stripped_text(item.get("idnumber"))

        if not competency_id or competency_id in seen:
            continue

        seen.add(competency_id)
        ids.append(competency_id)

    return ids


def ordered_competency_ids(
    values: Iterable[str],
    catalogue: Sequence[str],
) -> list[str]:
    """Deduplicate IDs and sort by catalogue order, then by id."""

    unique = {
        stripped_text(value)
        for value in values
        if stripped_text(value)
    }
    rank = {label: index for index, label in enumerate(catalogue)}
    return sorted(
        unique,
        key=lambda label: (rank.get(label, 10**6), label),
    )


def predicted_competency_ids(
    record: Mapping[str, Any],
    catalogue: Sequence[str],
) -> list[str]:
    """Extract predicted competency IDs from a resource_predictions record."""

    selected: list[str] = []

    for item in record.get("predicted_competencies") or []:
        if isinstance(item, Mapping):
            competency_id = stripped_text(item.get("competency_id"))
        else:
            competency_id = stripped_text(item)

        if competency_id:
            selected.append(competency_id)

    return ordered_competency_ids(selected, catalogue)


def has_parent_child_redundancy(predicted_ids: Iterable[str]) -> bool:
    """True when a parent and one of its direct children are both predicted."""

    predicted = {
        stripped_text(value)
        for value in predicted_ids
        if stripped_text(value)
    }

    for competency_id in predicted:
        parent = parent_of(competency_id)

        if parent and parent in predicted:
            return True

    return False


def _join_ids(values: Sequence[str]) -> str:
    return ";".join(values)


def _as_bool_text(value: bool) -> str:
    return "true" if value else "false"


def _format_float(value: float) -> str:
    return f"{value:.10f}"


def gold_fragments_by_resource(
    gold_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Group gold rows by resource_id. Preserve gold-file order."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    seen_fragments: set[str] = set()

    for row in gold_rows:
        fragment_id = stripped_text(row.get("fragment_id"))
        resource_id = stripped_text(row.get("resource_id"))

        if not fragment_id:
            errors.append("Gold row is missing fragment_id.")
            continue

        if fragment_id in seen_fragments:
            errors.append(f"Duplicate gold fragment: {fragment_id}")
            continue

        if not resource_id:
            errors.append(
                f"Gold fragment {fragment_id} is missing resource_id."
            )
            continue

        seen_fragments.add(fragment_id)
        grouped.setdefault(resource_id, []).append(dict(row))

    return grouped, errors


def _derivation_for_type(resource_type: str) -> str:
    if resource_type == "page":
        return PAGE_DERIVATION

    if resource_type == "quiz_question":
        return QUIZ_DERIVATION

    return ""


def build_resource_reference(
    *,
    gold_rows: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Derive resource gold from human-reviewed fragment labels."""

    catalogue = competency_catalogue_ids(competencies)
    allowed = set(catalogue)
    grouped, grouping_errors = gold_fragments_by_resource(gold_rows)
    errors = list(grouping_errors)

    unique_resources: list[Mapping[str, Any]] = []
    resource_ids: list[str] = []
    seen_resources: set[str] = set()
    duplicate_resource_ids: list[str] = []

    for resource in resources:
        resource_id = stripped_text(resource.get("resource_id"))

        if not resource_id:
            errors.append("Resource record is missing resource_id.")
            continue

        if resource_id in seen_resources:
            duplicate_resource_ids.append(resource_id)
            errors.append(f"Duplicate resource record: {resource_id}")
            continue

        seen_resources.add(resource_id)
        resource_ids.append(resource_id)
        unique_resources.append(resource)

    unknown_gold_resources = sorted(set(grouped) - seen_resources)

    for resource_id in unknown_gold_resources:
        errors.append(
            "Gold fragments refer to unknown resource: "
            f"{resource_id}"
        )

    missing_resource_ids = [
        resource_id
        for resource_id in resource_ids
        if resource_id not in grouped
    ]

    for resource_id in missing_resource_ids:
        errors.append(
            "Resource has no human-reviewed fragments: "
            f"{resource_id}"
        )

    used_fragment_ids: list[str] = []
    unknown_competency_ids: list[str] = []
    records: list[dict[str, Any]] = []
    page_count = 0
    quiz_count = 0

    for resource in unique_resources:
        resource_id = stripped_text(resource.get("resource_id"))
        resource_type = stripped_text(resource.get("resource_type"))
        fragment_rows = grouped.get(resource_id, [])
        fragment_ids = [
            stripped_text(row.get("fragment_id"))
            for row in fragment_rows
            if stripped_text(row.get("fragment_id"))
        ]
        used_fragment_ids.extend(fragment_ids)

        label_values: list[str] = []

        for row in fragment_rows:
            ids, parse_errors = parse_competency_ids(
                row.get("gold_competency_ids")
            )
            errors.extend(
                f"{stripped_text(row.get('fragment_id'))}: {error}"
                for error in parse_errors
            )

            for competency_id in ids:
                if competency_id not in allowed:
                    unknown_competency_ids.append(competency_id)
                    errors.append(
                        "Unknown competency "
                        f"{competency_id} on "
                        f"{stripped_text(row.get('fragment_id'))}"
                    )
                    continue

                label_values.append(competency_id)

        reference_ids = ordered_competency_ids(label_values, catalogue)
        derivation = _derivation_for_type(resource_type)

        if not derivation:
            errors.append(
                f"Unsupported resource_type for {resource_id}: "
                f"{resource_type}"
            )

        if resource_type == "page":
            page_count += 1
        elif resource_type == "quiz_question":
            quiz_count += 1

        records.append(
            {
                "resource_id": resource_id,
                "course_id": resource.get("course_id"),
                "course_shortname": stripped_text(
                    resource.get("course_shortname")
                ),
                "resource_type": resource_type,
                "title": stripped_text(resource.get("title")),
                "fragment_ids": fragment_ids,
                "reference_competency_ids": reference_ids,
                "reference_label_count": len(reference_ids),
                "reference_derivation": derivation,
            }
        )

    fragment_counts = Counter(used_fragment_ids)
    reused = sorted(
        fragment_id
        for fragment_id, count in fragment_counts.items()
        if count != 1
    )

    for fragment_id in reused:
        errors.append(
            f"Fragment used {fragment_counts[fragment_id]} times: "
            f"{fragment_id}"
        )

    gold_fragment_ids = [
        stripped_text(row.get("fragment_id"))
        for row in gold_rows
        if stripped_text(row.get("fragment_id"))
    ]
    unused_gold = sorted(set(gold_fragment_ids) - set(used_fragment_ids))

    for fragment_id in unused_gold:
        errors.append(
            f"Gold fragment not used in resource reference: {fragment_id}"
        )

    unique_errors: list[str] = []

    for error in errors:
        if error not in unique_errors:
            unique_errors.append(error)

    validation = {
        "passed": not unique_errors,
        "errors": unique_errors,
        "resource_count": len(records),
        "page_count": page_count,
        "quiz_question_count": quiz_count,
        "fragment_count": len(used_fragment_ids),
        "gold_fragment_count": len(gold_fragment_ids),
        "fragments_used_exactly_once": not reused and not unused_gold,
        "duplicate_resource_ids": list(dict.fromkeys(duplicate_resource_ids)),
        "missing_resource_ids": missing_resource_ids,
        "unknown_gold_resource_ids": unknown_gold_resources,
        "unknown_competency_ids": list(dict.fromkeys(unknown_competency_ids)),
        "used_manual_moodle_links": False,
        "reference_derivation": {
            "page": PAGE_DERIVATION,
            "quiz_question": QUIZ_DERIVATION,
        },
        "notes": (
            "Resource-level labels are DERIVED from the "
            "human-reviewed fragment reference. Native Moodle "
            "activity mappings are not used as question-level gold."
        ),
    }
    return records, validation


def require_valid_resource_reference(
    validation: Mapping[str, Any],
) -> None:
    """Refuse metric writes when derived reference construction failed."""

    if validation.get("passed") is True:
        return

    errors = validation.get("errors") or ["unknown validation error"]
    raise ResourceReferenceValidationError(
        "Resource-reference construction failed. "
        "Final metric files were not written. "
        + " | ".join(str(item) for item in errors)
    )


def predictions_by_resource(
    predictions: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    """Index resource predictions. Report duplicate resource IDs."""

    by_id: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []

    for record in predictions:
        resource_id = stripped_text(record.get("resource_id"))

        if not resource_id:
            errors.append("Prediction record is missing resource_id.")
            continue

        if resource_id in by_id:
            errors.append(
                f"Duplicate resource prediction: {resource_id}"
            )
            continue

        by_id[resource_id] = record

    return by_id, errors


def evaluate_resource_level(
    *,
    reference_records: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare resource predictions with the derived resource reference."""

    catalogue = competency_catalogue_ids(competencies)
    predicted_by_id, prediction_errors = predictions_by_resource(predictions)

    if prediction_errors:
        raise ResourceReferenceValidationError(
            "Resource predictions are invalid. "
            + " | ".join(prediction_errors)
        )

    missing_predictions = [
        stripped_text(record.get("resource_id"))
        for record in reference_records
        if stripped_text(record.get("resource_id")) not in predicted_by_id
    ]

    if missing_predictions:
        raise ResourceReferenceValidationError(
            "Missing resource predictions: "
            + ", ".join(missing_predictions)
        )

    gold_sets: list[list[str]] = []
    predicted_sets: list[list[str]] = []
    per_resource: list[dict[str, Any]] = []
    label_count_errors: list[int] = []

    for record in reference_records:
        resource_id = stripped_text(record.get("resource_id"))
        gold = list(record.get("reference_competency_ids") or [])
        predicted_record = predicted_by_id[resource_id]
        predicted = predicted_competency_ids(predicted_record, catalogue)
        gold_sets.append(gold)
        predicted_sets.append(predicted)
        gold_set = set(gold)
        predicted_set = set(predicted)
        true_positive = ordered_competency_ids(
            gold_set & predicted_set,
            catalogue,
        )
        false_positive = ordered_competency_ids(
            predicted_set - gold_set,
            catalogue,
        )
        false_negative = ordered_competency_ids(
            gold_set - predicted_set,
            catalogue,
        )
        scores = instance_prf(gold, predicted)
        label_count_error = abs(len(predicted) - len(gold))
        label_count_errors.append(label_count_error)
        parent_child = has_parent_child_redundancy(predicted)
        per_resource.append(
            {
                "resource_id": resource_id,
                "course_shortname": stripped_text(
                    record.get("course_shortname")
                ),
                "resource_type": stripped_text(record.get("resource_type")),
                "title": stripped_text(record.get("title")),
                "fragment_ids": list(record.get("fragment_ids") or []),
                "fragment_count": len(record.get("fragment_ids") or []),
                "reference_competency_ids": gold,
                "predicted_competency_ids": predicted,
                "reference_label_count": len(gold),
                "predicted_label_count": len(predicted),
                "label_count_error": label_count_error,
                "true_positive_ids": true_positive,
                "false_positive_ids": false_positive,
                "false_negative_ids": false_negative,
                "precision": scores["precision"],
                "recall": scores["recall"],
                "f1": scores["f1"],
                "exact_set_match": gold_set == predicted_set,
                "parent_child_redundancy": parent_child,
                "reference_derivation": stripped_text(
                    record.get("reference_derivation")
                ),
            }
        )

    micro = micro_prf(gold_sets, predicted_sets)
    macro_views = macro_prf_views(gold_sets, predicted_sets, catalogue)
    exact = exact_set_match(gold_sets, predicted_sets)
    per_label = per_label_prf(gold_sets, predicted_sets, catalogue)
    overpredicted = sum(
        1 for row in per_resource if row["false_positive_ids"]
    )
    underpredicted = sum(
        1 for row in per_resource if row["false_negative_ids"]
    )
    parent_child_count = sum(
        1 for row in per_resource if row["parent_child_redundancy"]
    )
    exact_count = sum(1 for row in per_resource if row["exact_set_match"])
    average_reference = (
        sum(len(gold) for gold in gold_sets) / len(gold_sets)
        if gold_sets
        else 0.0
    )
    average_error = (
        sum(label_count_errors) / len(label_count_errors)
        if label_count_errors
        else 0.0
    )
    macro_all = macro_views["macro_all_13"]
    macro_supported = macro_views["macro_gold_supported_labels"]

    return {
        "status": "COMPLETE",
        "final": True,
        "evaluation_version": RESOURCE_EVALUATION_VERSION,
        "resource_count": len(per_resource),
        "page_count": sum(
            1 for row in per_resource if row["resource_type"] == "page"
        ),
        "quiz_question_count": sum(
            1
            for row in per_resource
            if row["resource_type"] == "quiz_question"
        ),
        "micro_precision": micro["precision"],
        "micro_recall": micro["recall"],
        "micro_f1": micro["f1"],
        "micro_true_positives": int(micro["true_positives"]),
        "micro_false_positives": int(micro["false_positives"]),
        "micro_false_negatives": int(micro["false_negatives"]),
        "macro_precision": macro_all["precision"],
        "macro_recall": macro_all["recall"],
        "macro_f1": macro_all["f1"],
        "macro_all_13": dict(macro_all),
        "macro_gold_supported_labels": dict(macro_supported),
        "gold_supported_label_count": macro_views[
            "gold_supported_label_count"
        ],
        "gold_supported_label_ids": list(
            macro_views["gold_supported_label_ids"]
        ),
        "zero_gold_support_label_ids": list(
            macro_views["zero_gold_support_label_ids"]
        ),
        "exact_set_match": exact,
        "subset_accuracy": exact,
        "exact_set_match_count": exact_count,
        "average_reference_label_count": average_reference,
        "average_predicted_label_count": average_predicted_labels(
            predicted_sets
        ),
        "average_absolute_label_count_error": average_error,
        "resource_coverage": coverage_rate(predicted_sets),
        "resource_abstention_rate": abstention_rate(predicted_sets),
        "overpredicted_resource_count": overpredicted,
        "underpredicted_resource_count": underpredicted,
        "parent_child_redundant_resource_count": parent_child_count,
        "used_manual_moodle_links": False,
        "includes_ollama": False,
        "reference_derivation_note": (
            "Resource-level labels are DERIVED from the "
            "human-reviewed fragment reference. This is not a "
            "second independent annotation exercise."
        ),
        "per_resource": per_resource,
        "per_competency": per_label,
    }


def resource_table_rows(
    evaluation: Mapping[str, Any],
) -> list[dict[str, str]]:
    """CSV rows for reports/tables/resource_level_evaluation.csv."""

    rows: list[dict[str, str]] = []

    for item in evaluation.get("per_resource") or []:
        rows.append(
            {
                "resource_id": item["resource_id"],
                "course_shortname": item["course_shortname"],
                "resource_type": item["resource_type"],
                "title": item["title"],
                "fragment_count": str(item["fragment_count"]),
                "reference_competency_ids": _join_ids(
                    item["reference_competency_ids"]
                ),
                "predicted_competency_ids": _join_ids(
                    item["predicted_competency_ids"]
                ),
                "reference_label_count": str(item["reference_label_count"]),
                "predicted_label_count": str(item["predicted_label_count"]),
                "label_count_error": str(item["label_count_error"]),
                "true_positive_ids": _join_ids(item["true_positive_ids"]),
                "false_positive_ids": _join_ids(item["false_positive_ids"]),
                "false_negative_ids": _join_ids(item["false_negative_ids"]),
                "precision": _format_float(float(item["precision"])),
                "recall": _format_float(float(item["recall"])),
                "f1": _format_float(float(item["f1"])),
                "exact_set_match": _as_bool_text(
                    bool(item["exact_set_match"])
                ),
                "parent_child_redundancy": _as_bool_text(
                    bool(item["parent_child_redundancy"])
                ),
            }
        )

    return rows


def per_competency_table_rows(
    evaluation: Mapping[str, Any],
) -> list[dict[str, str]]:
    """CSV rows for reports/tables/resource_level_per_competency.csv."""

    rows: list[dict[str, str]] = []

    for item in evaluation.get("per_competency") or []:
        rows.append(
            {
                "competency_id": str(item["competency_id"]),
                "support": str(item["support"]),
                "predicted_count": str(item["predicted_count"]),
                "true_positives": str(item["true_positives"]),
                "false_positives": str(item["false_positives"]),
                "false_negatives": str(item["false_negatives"]),
                "precision": _format_float(float(item["precision"])),
                "recall": _format_float(float(item["recall"])),
                "f1": _format_float(float(item["f1"])),
                "gold_supported": _as_bool_text(
                    bool(item["gold_supported"])
                ),
            }
        )

    return rows


def _example_row(
    *,
    example_type: str,
    item: Mapping[str, Any],
    explanation: str,
) -> dict[str, str]:
    return {
        "example_type": example_type,
        "resource_id": str(item.get("resource_id") or ""),
        "resource_type": str(item.get("resource_type") or ""),
        "title": str(item.get("title") or ""),
        "fragment_ids": _join_ids(list(item.get("fragment_ids") or [])),
        "reference_competency_ids": _join_ids(
            list(item.get("reference_competency_ids") or [])
        ),
        "predicted_competency_ids": _join_ids(
            list(item.get("predicted_competency_ids") or [])
        ),
        "true_positive_ids": _join_ids(
            list(item.get("true_positive_ids") or [])
        ),
        "false_positive_ids": _join_ids(
            list(item.get("false_positive_ids") or [])
        ),
        "false_negative_ids": _join_ids(
            list(item.get("false_negative_ids") or [])
        ),
        "exact_set_match": _as_bool_text(bool(item.get("exact_set_match"))),
        "parent_child_redundancy": _as_bool_text(
            bool(item.get("parent_child_redundancy"))
        ),
        "short_factual_explanation": explanation,
    }


def build_resource_error_examples(
    evaluation: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Select real resource-level examples. Does not invent IDs."""

    items = list(evaluation.get("per_resource") or [])
    by_id = {
        stripped_text(item.get("resource_id")): item for item in items
    }
    examples: list[dict[str, str]] = []
    used: set[tuple[str, str]] = set()

    def add(
        example_type: str,
        resource_id: str,
        explanation: str,
    ) -> None:
        item = by_id.get(resource_id)

        if item is None or (example_type, resource_id) in used:
            return

        examples.append(
            _example_row(
                example_type=example_type,
                item=item,
                explanation=explanation,
            )
        )
        used.add((example_type, resource_id))

    exact_ids = [
        stripped_text(item.get("resource_id"))
        for item in items
        if item.get("exact_set_match")
    ]
    over_page_ids = [
        stripped_text(item.get("resource_id"))
        for item in items
        if item.get("resource_type") == "page"
        and item.get("false_positive_ids")
    ]
    parent_child_ids = [
        stripped_text(item.get("resource_id"))
        for item in items
        if item.get("parent_child_redundancy")
    ]
    false_negative_ids = [
        stripped_text(item.get("resource_id"))
        for item in items
        if item.get("false_negative_ids")
    ]
    quiz_ids = [
        stripped_text(item.get("resource_id"))
        for item in items
        if item.get("resource_type") == "quiz_question"
    ]

    if exact_ids:
        first = by_id[exact_ids[0]]
        add(
            "exact_correct_resource",
            exact_ids[0],
            "Predicted competency set equals the derived resource "
            "reference set "
            f"({_join_ids(first['reference_competency_ids'])}).",
        )

    if over_page_ids:
        page = by_id[over_page_ids[0]]
        add(
            "overpredicted_page",
            over_page_ids[0],
            "Page reference is "
            f"{_join_ids(page['reference_competency_ids'])}; "
            "predicted extra labels "
            f"{_join_ids(page['false_positive_ids'])}.",
        )

    if parent_child_ids:
        parent_item = by_id[parent_child_ids[0]]
        add(
            "parent_child_redundant_resource",
            parent_child_ids[0],
            "Predicted set includes a GI parent and at least one of "
            "its direct children: "
            f"{_join_ids(parent_item['predicted_competency_ids'])}.",
        )

    retrieval_item = by_id.get(KNOWN_RETRIEVAL_FAILURE_RESOURCE)

    if retrieval_item is not None:
        add(
            "retrieval_failure_resource",
            KNOWN_RETRIEVAL_FAILURE_RESOURCE,
            "Quiz-question resource containing fragment-level retrieval "
            "failure quiz_question:1:4#f001. Derived reference is "
            f"{_join_ids(retrieval_item['reference_competency_ids'])}; "
            "predicted "
            f"{_join_ids(retrieval_item['predicted_competency_ids'])}.",
        )

    if false_negative_ids:
        fn_item = by_id[false_negative_ids[0]]
        add(
            "resource_false_negative",
            false_negative_ids[0],
            "Derived reference labels absent from the resource "
            "prediction: "
            f"{_join_ids(fn_item['false_negative_ids'])}.",
        )

    quiz_example_id = next(
        (
            resource_id
            for resource_id in quiz_ids
            if resource_id != KNOWN_RETRIEVAL_FAILURE_RESOURCE
        ),
        quiz_ids[0] if quiz_ids else "",
    )

    if quiz_example_id:
        quiz_item = by_id[quiz_example_id]
        add(
            "quiz_question_resource",
            quiz_example_id,
            "Quiz questions remain independent research resources. "
            "Derived gold is the question fragment reference "
            f"{_join_ids(quiz_item['reference_competency_ids'])}, "
            "not a Quiz-activity Moodle competency mapping.",
        )

    return examples


def metrics_payload(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    """JSON-serializable metrics without per-resource row objects."""

    payload = {
        key: value
        for key, value in evaluation.items()
        if key not in {"per_resource", "per_competency"}
    }
    payload["per_competency"] = list(evaluation.get("per_competency") or [])
    return payload


def _fmt4(value: float) -> str:
    return f"{float(value):.4f}"


def _fmt10(value: float) -> str:
    return f"{float(value):.10f}"


def render_resource_level_report(
    *,
    evaluation: Mapping[str, Any],
    validation: Mapping[str, Any],
    fragment_metrics: Mapping[str, Any] | None = None,
) -> str:
    """Human-readable resource-level evaluation report."""

    fragment = fragment_metrics or {}
    fragment_p = float(fragment.get("micro_precision", 0.7254901960784313))
    fragment_r = float(fragment.get("micro_recall", 0.9736842105263158))
    fragment_f1 = float(fragment.get("micro_f1", 0.8314606741573034))
    macro_all = evaluation["macro_all_13"]
    macro_supported = evaluation["macro_gold_supported_labels"]
    per_resource = list(evaluation.get("per_resource") or [])
    per_label = list(evaluation.get("per_competency") or [])
    examples = build_resource_error_examples(evaluation)
    by_type = {row["example_type"]: row for row in examples}

    resource_lines = [
        "| resource_id | type | reference | predicted | P | R | F1 | exact |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]

    for item in per_resource:
        resource_lines.append(
            "| `{id}` | {typ} | `{ref}` | `{pred}` | {p} | {r} | {f1} | {ex} |".format(
                id=item["resource_id"],
                typ=item["resource_type"],
                ref=_join_ids(item["reference_competency_ids"]) or "∅",
                pred=_join_ids(item["predicted_competency_ids"]) or "∅",
                p=_fmt4(item["precision"]),
                r=_fmt4(item["recall"]),
                f1=_fmt4(item["f1"]),
                ex="yes" if item["exact_set_match"] else "no",
            )
        )

    label_lines = [
        "| competency_id | support | predicted | TP | FP | FN | P | R | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for item in per_label:
        label_lines.append(
            "| `{cid}` | {sup} | {pred} | {tp} | {fp} | {fn} | {p} | {r} | {f1} |".format(
                cid=item["competency_id"],
                sup=item["support"],
                pred=item["predicted_count"],
                tp=item["true_positives"],
                fp=item["false_positives"],
                fn=item["false_negatives"],
                p=_fmt4(float(item["precision"])),
                r=_fmt4(float(item["recall"])),
                f1=_fmt4(float(item["f1"])),
            )
        )

    retrieval = by_type.get("retrieval_failure_resource") or {}
    fn_example = by_type.get("resource_false_negative") or {}
    over_page = by_type.get("overpredicted_page") or {}
    parent_ex = by_type.get("parent_child_redundant_resource") or {}
    exact_ex = by_type.get("exact_correct_resource") or {}
    quiz_ex = by_type.get("quiz_question_resource") or {}

    return "\n".join(
        [
            "# Resource-level evaluation",
            "",
            "**Project:** Moodle Learning Resource-to-Competency Alignment MVP  ",
            "**Researcher:** Wail Ouaret  ",
            "**Date:** 2026-09-18",
            "",
            "Predictions are the already-generated constrained Gemini "
            "resource aggregations. No new model calls were made.",
            "",
            "## 1. Purpose",
            "",
            "This phase measures how accurately fragment-level competency "
            "predictions aggregate into competency mappings for complete "
            "Moodle research resources (Pages and independent Quiz questions).",
            "",
            "## 2. Derived resource reference",
            "",
            "Resource-level labels are **DERIVED** from the human-reviewed "
            "fragment reference in `data/gold/manual_fragment_annotations.csv`. "
            "This is not a second independent annotation exercise.",
            "",
            f"- Resources: {validation.get('resource_count')}",
            f"- Pages: {validation.get('page_count')}",
            f"- Quiz-question resources: {validation.get('quiz_question_count')}",
            f"- Fragments accounted for: {validation.get('fragment_count')} / "
            f"{validation.get('gold_fragment_count')}",
            "- Fragments used exactly once: "
            f"{validation.get('fragments_used_exactly_once')}",
            "- Native Moodle activity mappings used: no "
            "(`used_manual_moodle_links=false`)",
            "",
            "Derivation strings:",
            "",
            f"- Page: `{PAGE_DERIVATION}`",
            f"- Quiz question: `{QUIZ_DERIVATION}`",
            "",
            "File: `data/processed/resource_reference.jsonl`",
            "",
            "## 3. Why Pages use union of fragment labels",
            "",
            "A Page is one Moodle learning resource that may be split into "
            "several `page_chunk` fragments for retrieval and LLM scoring. "
            "The resource-level mapping for that Page is the union of the "
            "human-reviewed fragment labels belonging to it. Duplicate labels "
            "across fragments are kept once.",
            "",
            "Example: fragment labels `GI_C1_1;GI_C1_2` and `GI_C1_1` become "
            "resource gold `GI_C1_1;GI_C1_2`.",
            "",
            "## 4. Why Quiz questions remain independent",
            "",
            "Each Quiz question is already treated as an independent research "
            "resource. Question gold is that question's human-reviewed fragment "
            "labels. Quiz activity-level Moodle competency associations are "
            "not propagated to individual questions. "
            "`data/gold/manual_moodle_links.csv` is not used here.",
            "",
            "## 5. Resource-level metrics",
            "",
            "Source: `reports/metrics/resource_level_metrics.json`  ",
            "System: existing `data/processed/resource_predictions.jsonl` "
            "(constrained Gemini, no new calls).",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Resources | {evaluation['resource_count']} |",
            f"| Micro precision | {_fmt10(evaluation['micro_precision'])} |",
            f"| Micro recall | {_fmt10(evaluation['micro_recall'])} |",
            f"| Micro F1 | {_fmt10(evaluation['micro_f1'])} |",
            f"| Macro precision (all 13) | {_fmt10(macro_all['precision'])} |",
            f"| Macro recall (all 13) | {_fmt10(macro_all['recall'])} |",
            f"| Macro F1 (all 13) | {_fmt10(macro_all['f1'])} |",
            f"| Macro precision (gold-supported) | {_fmt10(macro_supported['precision'])} |",
            f"| Macro recall (gold-supported) | {_fmt10(macro_supported['recall'])} |",
            f"| Macro F1 (gold-supported) | {_fmt10(macro_supported['f1'])} |",
            f"| Exact-set / subset accuracy | {_fmt10(evaluation['exact_set_match'])} |",
            f"| Exact-set matches | {evaluation['exact_set_match_count']} / {evaluation['resource_count']} |",
            f"| Average reference labels | {_fmt10(evaluation['average_reference_label_count'])} |",
            f"| Average predicted labels | {_fmt10(evaluation['average_predicted_label_count'])} |",
            f"| Average |predicted − reference| label count | {_fmt10(evaluation['average_absolute_label_count_error'])} |",
            f"| Resource coverage | {_fmt10(evaluation['resource_coverage'])} |",
            f"| Resource abstention | {_fmt10(evaluation['resource_abstention_rate'])} |",
            "",
            "`macro_all_13` is the unweighted mean over all 13 UTC GI "
            "competencies. `macro_gold_supported_labels` is a second view over "
            "competencies with positive derived-reference support. Neither "
            "replaces the other.",
            "",
            "Exact-set match is the multi-label subset-accuracy rate: the "
            "fraction of resources whose predicted set equals the derived "
            "reference set.",
            "",
            "Ollama is not included in this file.",
            "",
            "## 6. Per-resource results",
            "",
            *resource_lines,
            "",
            f"Overpredicted resources (any false positive): "
            f"{evaluation['overpredicted_resource_count']}",
            f"Resources with a false negative: "
            f"{evaluation['underpredicted_resource_count']}",
            f"Resources with parent-child redundancy: "
            f"{evaluation['parent_child_redundant_resource_count']}",
            "",
            "## 7. Per-competency results",
            "",
            *label_lines,
            "",
            "## 8. Main errors",
            "",
            "Measured error pattern at resource level is overprediction, "
            "often a GI parent predicted together with a child that is already "
            "in the derived reference. Exact-set accuracy is therefore lower "
            "than fragment-level exact-set match even when the child labels "
            "are correct.",
            "",
            (
                f"- Overpredicted Page example: `{over_page.get('resource_id', '')}` "
                f"reference `{over_page.get('reference_competency_ids', '')}`; "
                f"extra `{over_page.get('false_positive_ids', '')}`."
                if over_page
                else "- No overpredicted Page in this evaluation."
            ),
            (
                f"- Parent-child example: `{parent_ex.get('resource_id', '')}` "
                f"predicted `{parent_ex.get('predicted_competency_ids', '')}`."
                if parent_ex
                else "- No parent-child redundant resource in this evaluation."
            ),
            (
                f"- False-negative example: `{fn_example.get('resource_id', '')}` "
                f"missing `{fn_example.get('false_negative_ids', '')}`."
                if fn_example
                else "- No false-negative resources in this evaluation."
            ),
            (
                f"- Retrieval-failure resource: `{retrieval.get('resource_id', '')}` "
                f"reference `{retrieval.get('reference_competency_ids', '')}`; "
                f"predicted `{retrieval.get('predicted_competency_ids', '')}`."
                if retrieval
                else "- The known fragment retrieval-failure resource is not in this table."
            ),
            (
                f"- Exact correct example: `{exact_ex.get('resource_id', '')}` "
                f"(`{exact_ex.get('reference_competency_ids', '')}`)."
                if exact_ex
                else "- No exact-set resource in this evaluation."
            ),
            (
                f"- Independent Quiz-question example: `{quiz_ex.get('resource_id', '')}`."
                if quiz_ex
                else "- No Quiz-question resource in this evaluation."
            ),
            "",
            "The only resource-level false negative on the current frozen "
            "data is `quiz_question:1:4` (`GI_C1_3` missing; `GI_C1_1` "
            "predicted). That is the same retrieval failure already measured "
            "at fragment level.",
            "",
            "## 9. Relationship to fragment-level results",
            "",
            "| Level | Micro P | Micro R | Micro F1 |",
            "|---|---:|---:|---:|",
            f"| Fragment-level Gemini | {_fmt4(fragment_p)} | {_fmt4(fragment_r)} | {_fmt4(fragment_f1)} |",
            f"| Resource-level Gemini | {_fmt4(evaluation['micro_precision'])} | {_fmt4(evaluation['micro_recall'])} | {_fmt4(evaluation['micro_f1'])} |",
            "",
            "Fragment-level micro recall and resource-level micro recall are "
            "both limited by the same missed reference label "
            "`GI_C1_3` on `quiz_question:1:4`. Resource-level micro precision "
            "is lower than fragment-level micro precision on this corpus. "
            "Page aggregation may accumulate false-positive labels from "
            "several fragments (for example a parent predicted on one chunk "
            "remains on the Page after union). This is a measured difference, "
            "not a causal proof.",
            "",
            "## 10. Limitations",
            "",
            "- Resource gold is derived from fragment gold; it is not a new "
            "human annotation of whole resources.",
            "- Native Moodle activity competency links are not question gold.",
            "- Parent and child IDs remain distinct labels.",
            "- Small corpus: 20 resources, 35 fragments, 13 competencies.",
            "- Constrained Gemini still cannot select a label absent from "
            "BM25 Top-5.",
            "- Teacher validation has not started.",
            "- Optional unconstrained Gemini and Ollama resource-level "
            "evaluation were not run in this phase.",
            "",
            "Next phase: minimal hierarchy / graph analysis. "
            "Teacher UI is not started.",
            "",
        ]
    )


def inspect_sanity_mismatches(
    evaluation: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    abs_tol: float = 1e-4,
) -> list[str]:
    """Compare measured metrics with approximate expected values.

    Expected values are not used to compute metrics. They only detect
    accidental implementation errors on the frozen live corpus.
    """

    mismatches: list[str] = []

    def close(actual: float, target: float, name: str) -> None:
        if abs(float(actual) - float(target)) > abs_tol:
            mismatches.append(
                f"{name}: measured {actual} vs expected {target}"
            )

    if "resource_count" in expected:
        actual_count = int(evaluation["resource_count"])
        expected_count = int(expected["resource_count"])

        if actual_count != expected_count:
            mismatches.append(
                "resource_count: measured "
                f"{actual_count} vs expected {expected_count}"
            )

    for key in (
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "exact_set_match",
        "average_absolute_label_count_error",
    ):
        if key in expected:
            close(evaluation[key], expected[key], key)

    for view_name in ("macro_all_13", "macro_gold_supported_labels"):
        expected_view = expected.get(view_name)

        if not isinstance(expected_view, Mapping):
            continue

        actual_view = evaluation.get(view_name) or {}

        for metric_name in ("precision", "recall", "f1"):
            if metric_name in expected_view:
                close(
                    actual_view[metric_name],
                    expected_view[metric_name],
                    f"{view_name}.{metric_name}",
                )

    return mismatches
