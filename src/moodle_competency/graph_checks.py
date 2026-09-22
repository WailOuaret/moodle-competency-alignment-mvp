"""Post-hoc hierarchy warnings and a separate child-preference ablation.

Inspect frozen predictions. Never overwrite Gemini outputs or gold.
Uses only parent-child edges present in competencies.jsonl.
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import parse_competency_ids, stripped_text
from moodle_competency.evaluation import (
    gold_sets_from_rows,
    predicted_sets_from_gemini,
)
from moodle_competency.metrics import (
    abstention_rate,
    average_predicted_labels,
    coverage_rate,
    exact_set_match,
    instance_prf,
    macro_prf_views,
    micro_prf,
)


GRAPH_RULE_VERSION = "1.0"
EXPERIMENT_NAME = "post_hoc_child_preference_ablation"
WARNING_ACTION = "warning_only"

WARNING_TYPES = (
    "parent_child_redundancy",
    "granularity_conflict",
    "invalid_hierarchy_reference",
)

WARNING_COLUMNS = (
    "fragment_id",
    "resource_id",
    "warning_type",
    "parent_id",
    "child_id",
    "parent_confidence",
    "child_confidence",
    "parent_evidence",
    "child_evidence",
    "same_or_overlapping_evidence",
    "action",
)

RESOURCE_WARNING_COLUMNS = (
    "resource_id",
    "course_shortname",
    "resource_type",
    "warning_type",
    "parent_id",
    "child_id",
    "parent_confidence",
    "child_confidence",
    "parent_evidence",
    "child_evidence",
    "same_or_overlapping_evidence",
    "action",
)

FRAGMENT_EVAL_COLUMNS = (
    "fragment_id",
    "gold_competency_ids",
    "predicted_competency_ids",
    "removed_parent_ids",
    "exact_set_match",
    "precision",
    "recall",
    "f1",
)

EXAMPLE_COLUMNS = (
    "fragment_id",
    "fragment_text",
    "original_predictions",
    "reference_labels",
    "parent",
    "child",
    "evidence",
    "original_correct",
    "simulated_predictions",
    "simulated_correct",
    "explanation",
)

ABLATION_COMPARISON_COLUMNS = (
    "system",
    "micro_precision",
    "micro_recall",
    "micro_f1",
    "macro_all_13_f1",
    "macro_gold_supported_f1",
    "exact_set_match",
    "coverage",
    "abstention_rate",
    "average_predicted_labels",
    "parent_child_redundancy_count",
    "delta_micro_precision",
    "delta_micro_recall",
    "delta_micro_f1",
    "delta_exact_set_match",
)

RESOURCE_ABLATION_COLUMNS = (
    "system",
    "micro_precision",
    "micro_recall",
    "micro_f1",
    "macro_all_13_f1",
    "macro_gold_supported_f1",
    "exact_set_match",
    "average_predicted_labels",
    "average_absolute_label_count_error",
    "parent_child_redundancy_count",
    "delta_micro_precision",
    "delta_micro_recall",
    "delta_micro_f1",
    "delta_exact_set_match",
)


class HierarchyValidationError(ValueError):
    """Raised when the competency hierarchy is inconsistent."""


def utc_timestamp(moment: datetime | None = None) -> str:
    value = moment or datetime.now(timezone.utc)
    return value.replace(microsecond=0).isoformat()


def _ids(values: Iterable[str] | None) -> list[str]:
    return [
        stripped_text(value)
        for value in (values or [])
        if stripped_text(value)
    ]


def _join(values: Sequence[str]) -> str:
    return ";".join(values)


def _fmt(value: float) -> str:
    return f"{float(value):.10f}"


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _evidence_list(raw: Any) -> list[str]:
    if raw is None:
        return []

    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []

    return [
        str(item).strip()
        for item in raw
        if str(item).strip()
    ]


def evidence_overlap(
    left: Sequence[str],
    right: Sequence[str],
) -> bool:
    """True when quote sets intersect or one quote contains the other."""

    left_set = {item for item in _evidence_list(left)}
    right_set = {item for item in _evidence_list(right)}

    if not left_set or not right_set:
        return False

    if left_set & right_set:
        return True

    for quote_left in left_set:
        for quote_right in right_set:
            if quote_left in quote_right or quote_right in quote_left:
                return True

    return False


def _confidence(raw: Any) -> float | None:
    if isinstance(raw, bool):
        return None

    if isinstance(raw, (int, float)):
        return float(raw)

    return None


def build_hierarchy_index(
    competencies: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Index parent/child edges from competencies.jsonl. No invented edges."""

    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for item in competencies:
        competency_id = stripped_text(item.get("idnumber"))

        if not competency_id or competency_id in by_id:
            continue

        parent_id = stripped_text(item.get("parent_idnumber"))
        by_id[competency_id] = {
            "idnumber": competency_id,
            "parent_idnumber": parent_id,
            "shortname": stripped_text(item.get("shortname")),
            "children": [],
        }
        order.append(competency_id)

    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = {key: [] for key in by_id}

    for competency_id in order:
        parent_id = by_id[competency_id]["parent_idnumber"]

        if not parent_id:
            continue

        parent_of[competency_id] = parent_id

        if parent_id in children_of:
            children_of[parent_id].append(competency_id)
            by_id[parent_id]["children"].append(competency_id)

    roots = [
        competency_id
        for competency_id in order
        if not by_id[competency_id]["parent_idnumber"]
    ]
    children = [
        competency_id
        for competency_id in order
        if by_id[competency_id]["parent_idnumber"]
    ]
    return {
        "ids": order,
        "by_id": by_id,
        "parent_of": parent_of,
        "children_of": children_of,
        "roots": roots,
        "children": children,
    }


def get_parent(
    competency_id: str,
    index: Mapping[str, Any],
) -> str | None:
    parent = index.get("parent_of", {}).get(stripped_text(competency_id))
    return parent or None


def get_children(
    competency_id: str,
    index: Mapping[str, Any],
) -> list[str]:
    return list(
        index.get("children_of", {}).get(stripped_text(competency_id), [])
    )


def is_direct_parent(
    parent_id: str,
    child_id: str,
    index: Mapping[str, Any],
) -> bool:
    return get_parent(child_id, index) == stripped_text(parent_id)


def is_ancestor(
    ancestor_id: str,
    node_id: str,
    index: Mapping[str, Any],
) -> bool:
    ancestor = stripped_text(ancestor_id)
    current = stripped_text(node_id)
    seen: set[str] = set()

    while current:
        if current in seen:
            return False

        seen.add(current)
        parent = get_parent(current, index)

        if parent is None:
            return False

        if parent == ancestor:
            return True

        current = parent

    return False


def _cycle_ids(index: Mapping[str, Any]) -> list[str]:
    cycles: list[str] = []

    for start in index.get("ids") or []:
        seen: list[str] = []
        current = start
        visited: set[str] = set()

        while current:
            if current in visited:
                loop = " -> ".join(seen[seen.index(current) :] + [current])

                if loop not in cycles:
                    cycles.append(loop)

                break

            visited.add(current)
            seen.append(current)
            current = get_parent(current, index)

    return cycles


def validate_hierarchy(
    competencies: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check IDs, missing parents, and cycles. Does not alter data."""

    built = index or build_hierarchy_index(competencies)
    missing_parents: list[str] = []

    for competency_id in built["ids"]:
        parent_id = built["by_id"][competency_id]["parent_idnumber"]

        if parent_id and parent_id not in built["by_id"]:
            missing_parents.append(
                f"{competency_id} -> {parent_id}"
            )

    cycles = _cycle_ids(built)
    errors: list[str] = []

    if missing_parents:
        errors.append(
            "Missing parent references: " + ", ".join(missing_parents)
        )

    if cycles:
        errors.append("Hierarchy cycles: " + "; ".join(cycles))

    return {
        "passed": not errors,
        "errors": errors,
        "competency_count": len(built["ids"]),
        "root_count": len(built["roots"]),
        "child_count": len(built["children"]),
        "root_ids": list(built["roots"]),
        "child_ids": list(built["children"]),
        "missing_parent_references": missing_parents,
        "cycles": cycles,
    }


def require_valid_hierarchy(validation: Mapping[str, Any]) -> None:
    if validation.get("passed") is True:
        return

    raise HierarchyValidationError(
        "Competency hierarchy is invalid. "
        + " | ".join(str(item) for item in validation.get("errors") or [])
    )


def fragment_context_from_rows(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    """Lookup resource/course/text/gold from annotation or fragment rows."""

    context: dict[str, dict[str, str]] = {}

    for row in rows:
        fragment_id = stripped_text(row.get("fragment_id"))

        if not fragment_id:
            continue

        gold_ids, _errors = parse_competency_ids(
            row.get("gold_competency_ids")
        )
        context[fragment_id] = {
            "resource_id": stripped_text(row.get("resource_id")),
            "course_shortname": stripped_text(row.get("course_shortname")),
            "resource_type": stripped_text(row.get("resource_type")),
            "fragment_text": stripped_text(
                row.get("fragment_text") or row.get("text")
            ),
            "gold_competency_ids": _join(gold_ids),
        }

    return context


def selections_from_fragment(
    record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for item in record.get("selected") or []:
        competency_id = stripped_text(item.get("idnumber"))

        if not competency_id:
            continue

        selected.append(
            {
                "idnumber": competency_id,
                "confidence": _confidence(item.get("confidence")),
                "evidence": _evidence_list(item.get("evidence")),
            }
        )

    return selected


def selections_from_resource(
    record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for item in record.get("predicted_competencies") or []:
        if isinstance(item, Mapping):
            competency_id = stripped_text(item.get("competency_id"))
            evidence = _evidence_list(item.get("evidence"))
            confidence = _confidence(
                item.get("max_confidence")
                if item.get("max_confidence") is not None
                else item.get("mean_confidence")
            )
        else:
            competency_id = stripped_text(item)
            evidence = []
            confidence = None

        if not competency_id:
            continue

        selected.append(
            {
                "idnumber": competency_id,
                "confidence": confidence,
                "evidence": evidence,
            }
        )

    return selected


def _selection_map(
    selections: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}

    for item in selections:
        competency_id = stripped_text(item.get("idnumber"))

        if competency_id and competency_id not in mapped:
            mapped[competency_id] = dict(item)

    return mapped


def parent_child_pairs(
    predicted_ids: Sequence[str],
    index: Mapping[str, Any],
) -> list[tuple[str, str]]:
    ids = _ids(predicted_ids)
    pairs: list[tuple[str, str]] = []

    for child_id in ids:
        parent_id = get_parent(child_id, index)

        if parent_id and parent_id in set(ids):
            pairs.append((parent_id, child_id))

    return pairs


def detect_fragment_warnings(
    record: Mapping[str, Any],
    index: Mapping[str, Any],
    *,
    context: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return warnings for one fragment prediction. Does not mutate record."""

    fragment_id = stripped_text(record.get("fragment_id"))
    info = dict(context or {})
    selections = selections_from_fragment(record)
    by_id = _selection_map(selections)
    predicted_ids = [item["idnumber"] for item in selections]
    warnings: list[dict[str, Any]] = []
    known = set(index.get("ids") or [])

    for competency_id in predicted_ids:
        recorded_parent = ""

        if competency_id in known:
            recorded_parent = stripped_text(
                index["by_id"][competency_id]["parent_idnumber"]
            )

        unknown = competency_id not in known
        missing_parent = bool(recorded_parent) and recorded_parent not in known

        if not unknown and not missing_parent:
            continue

        warnings.append(
            _warning_record(
                fragment_id=fragment_id,
                resource_id=info.get("resource_id", ""),
                warning_type="invalid_hierarchy_reference",
                parent_id=recorded_parent if missing_parent else "",
                child_id=competency_id,
                parent_confidence=None,
                child_confidence=by_id[competency_id]["confidence"],
                parent_evidence=[],
                child_evidence=by_id[competency_id]["evidence"],
                overlapping=False,
            )
        )

    for parent_id, child_id in parent_child_pairs(predicted_ids, index):
        parent_sel = by_id[parent_id]
        child_sel = by_id[child_id]
        overlapping = evidence_overlap(
            parent_sel["evidence"],
            child_sel["evidence"],
        )
        warnings.append(
            _warning_record(
                fragment_id=fragment_id,
                resource_id=info.get("resource_id", ""),
                warning_type="parent_child_redundancy",
                parent_id=parent_id,
                child_id=child_id,
                parent_confidence=parent_sel["confidence"],
                child_confidence=child_sel["confidence"],
                parent_evidence=parent_sel["evidence"],
                child_evidence=child_sel["evidence"],
                overlapping=overlapping,
            )
        )

        if overlapping:
            warnings.append(
                _warning_record(
                    fragment_id=fragment_id,
                    resource_id=info.get("resource_id", ""),
                    warning_type="granularity_conflict",
                    parent_id=parent_id,
                    child_id=child_id,
                    parent_confidence=parent_sel["confidence"],
                    child_confidence=child_sel["confidence"],
                    parent_evidence=parent_sel["evidence"],
                    child_evidence=child_sel["evidence"],
                    overlapping=True,
                )
            )

    return _sort_warnings(warnings)


def detect_resource_warnings(
    record: Mapping[str, Any],
    index: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return warnings for one resource prediction. Does not mutate record."""

    resource_id = stripped_text(record.get("resource_id"))
    selections = selections_from_resource(record)
    by_id = _selection_map(selections)
    predicted_ids = [item["idnumber"] for item in selections]
    warnings: list[dict[str, Any]] = []
    known = set(index.get("ids") or [])

    for competency_id in predicted_ids:
        if competency_id in known:
            continue

        warnings.append(
            {
                "resource_id": resource_id,
                "course_shortname": stripped_text(
                    record.get("course_shortname")
                ),
                "resource_type": stripped_text(record.get("resource_type")),
                "warning_type": "invalid_hierarchy_reference",
                "parent_id": "",
                "child_id": competency_id,
                "parent_confidence": None,
                "child_confidence": by_id[competency_id]["confidence"],
                "parent_evidence": [],
                "child_evidence": by_id[competency_id]["evidence"],
                "same_or_overlapping_evidence": False,
                "action": WARNING_ACTION,
            }
        )

    for parent_id, child_id in parent_child_pairs(predicted_ids, index):
        parent_sel = by_id[parent_id]
        child_sel = by_id[child_id]
        overlapping = evidence_overlap(
            parent_sel["evidence"],
            child_sel["evidence"],
        )
        base = {
            "resource_id": resource_id,
            "course_shortname": stripped_text(
                record.get("course_shortname")
            ),
            "resource_type": stripped_text(record.get("resource_type")),
            "parent_id": parent_id,
            "child_id": child_id,
            "parent_confidence": parent_sel["confidence"],
            "child_confidence": child_sel["confidence"],
            "parent_evidence": list(parent_sel["evidence"]),
            "child_evidence": list(child_sel["evidence"]),
            "same_or_overlapping_evidence": overlapping,
            "action": WARNING_ACTION,
        }
        warnings.append(
            {**base, "warning_type": "parent_child_redundancy"}
        )

        if overlapping:
            warnings.append(
                {**base, "warning_type": "granularity_conflict"}
            )

    return sorted(
        warnings,
        key=lambda item: (
            item["resource_id"],
            item["warning_type"],
            item["parent_id"],
            item["child_id"],
        ),
    )


def _warning_record(
    *,
    fragment_id: str,
    resource_id: str,
    warning_type: str,
    parent_id: str,
    child_id: str,
    parent_confidence: float | None,
    child_confidence: float | None,
    parent_evidence: Sequence[str],
    child_evidence: Sequence[str],
    overlapping: bool,
) -> dict[str, Any]:
    return {
        "fragment_id": fragment_id,
        "resource_id": resource_id,
        "warning_type": warning_type,
        "parent_id": parent_id,
        "child_id": child_id,
        "parent_confidence": parent_confidence,
        "child_confidence": child_confidence,
        "parent_evidence": list(parent_evidence),
        "child_evidence": list(child_evidence),
        "same_or_overlapping_evidence": overlapping,
        "action": WARNING_ACTION,
    }


def _sort_warnings(warnings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(item) for item in warnings),
        key=lambda item: (
            item.get("fragment_id", ""),
            item.get("warning_type", ""),
            item.get("parent_id", ""),
            item.get("child_id", ""),
        ),
    )


def collect_fragment_warnings(
    predictions: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
    *,
    context_by_fragment: Mapping[str, Mapping[str, str]] | None = None,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    context_by_fragment = context_by_fragment or {}

    for record in predictions:
        fragment_id = stripped_text(record.get("fragment_id"))
        warnings.extend(
            detect_fragment_warnings(
                record,
                index,
                context=context_by_fragment.get(fragment_id),
            )
        )

    return _sort_warnings(warnings)


def collect_resource_warnings(
    predictions: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    for record in predictions:
        warnings.extend(detect_resource_warnings(record, index))

    return warnings


def summarize_fragment_warnings(
    warnings: Sequence[Mapping[str, Any]],
    *,
    fragments_checked: int,
    context_by_fragment: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    context_by_fragment = context_by_fragment or {}
    redundancy = [
        item
        for item in warnings
        if item.get("warning_type") == "parent_child_redundancy"
    ]
    granularity = [
        item
        for item in warnings
        if item.get("warning_type") == "granularity_conflict"
    ]
    invalid = [
        item
        for item in warnings
        if item.get("warning_type") == "invalid_hierarchy_reference"
    ]
    redundant_fragments = {
        stripped_text(item.get("fragment_id")) for item in redundancy
    }
    parent_freq = Counter(
        stripped_text(item.get("parent_id")) for item in redundancy
    )
    course_counts: dict[str, int] = defaultdict(int)

    for fragment_id in sorted(redundant_fragments):
        course = stripped_text(
            (context_by_fragment.get(fragment_id) or {}).get(
                "course_shortname"
            )
        ) or "unknown"
        course_counts[course] += 1

    return {
        "status": "COMPLETE",
        "experiment_kind": "post-hoc hierarchy / graph ablation",
        "original_predictions_modified": False,
        "fragments_checked": fragments_checked,
        "fragments_with_parent_child_redundancy": len(redundant_fragments),
        "redundant_parent_child_pairs": len(redundancy),
        "fragments_with_granularity_conflict": len(
            {
                stripped_text(item.get("fragment_id"))
                for item in granularity
            }
        ),
        "granularity_conflict_pairs": len(granularity),
        "invalid_hierarchy_references": len(invalid),
        "warning_rate": (
            len(redundant_fragments) / fragments_checked
            if fragments_checked
            else 0.0
        ),
        "parent_frequencies": {
            "GI_C1": int(parent_freq.get("GI_C1", 0)),
            "GI_C2": int(parent_freq.get("GI_C2", 0)),
            "GI_C3": int(parent_freq.get("GI_C3", 0)),
        },
        "parent_frequencies_all": dict(parent_freq),
        "per_course_redundant_fragments": dict(course_counts),
        "most_frequent_redundant_parent": (
            parent_freq.most_common(1)[0][0] if parent_freq else ""
        ),
    }


def summarize_resource_warnings(
    warnings: Sequence[Mapping[str, Any]],
    *,
    resources_checked: int,
    predictions: Sequence[Mapping[str, Any]] | None = None,
    index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    redundancy = [
        item
        for item in warnings
        if item.get("warning_type") == "parent_child_redundancy"
    ]
    redundant_resources = {
        stripped_text(item.get("resource_id")) for item in redundancy
    }
    parent_freq_pairs = Counter(
        stripped_text(item.get("parent_id")) for item in redundancy
    )
    parent_by_resource = {"GI_C1": 0, "GI_C2": 0, "GI_C3": 0}

    if predictions is not None and index is not None:
        for record in predictions:
            predicted = [
                item["idnumber"]
                for item in selections_from_resource(record)
            ]
            predicted_set = set(predicted)

            for parent_id in ("GI_C1", "GI_C2", "GI_C3"):
                if parent_id in predicted_set and any(
                    is_direct_parent(parent_id, child_id, index)
                    for child_id in predicted_set
                ):
                    parent_by_resource[parent_id] += 1

    return {
        "status": "COMPLETE",
        "experiment_kind": "post-hoc hierarchy / graph ablation",
        "original_predictions_modified": False,
        "resources_checked": resources_checked,
        "resources_with_parent_child_redundancy": len(redundant_resources),
        "redundant_resource_parent_child_pairs": len(redundancy),
        "invalid_hierarchy_references": sum(
            1
            for item in warnings
            if item.get("warning_type") == "invalid_hierarchy_reference"
        ),
        "parent_frequencies": {
            "GI_C1": int(parent_freq_pairs.get("GI_C1", 0)),
            "GI_C2": int(parent_freq_pairs.get("GI_C2", 0)),
            "GI_C3": int(parent_freq_pairs.get("GI_C3", 0)),
        },
        "parent_frequency_by_resource": parent_by_resource,
        "most_frequent_redundant_parent": (
            parent_freq_pairs.most_common(1)[0][0]
            if parent_freq_pairs
            else ""
        ),
    }


def redundant_parents_to_remove(
    predicted_ids: Sequence[str],
    index: Mapping[str, Any],
) -> list[str]:
    """Parents that have at least one direct child also predicted."""

    predicted = _ids(predicted_ids)
    predicted_set = set(predicted)
    removed: list[str] = []

    for competency_id in predicted:
        children = get_children(competency_id, index)

        if any(child_id in predicted_set for child_id in children):
            if competency_id not in removed:
                removed.append(competency_id)

    return removed


def apply_child_preference(
    record: Mapping[str, Any],
    index: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Return a copied prediction with redundant parents removed.

    The input mapping is not mutated.
    """

    copied = copy.deepcopy(dict(record))
    selections = list(copied.get("selected") or [])
    predicted_ids = [
        stripped_text(item.get("idnumber"))
        for item in selections
        if stripped_text(item.get("idnumber"))
    ]
    removed = redundant_parents_to_remove(predicted_ids, index)

    if removed:
        copied["selected"] = [
            item
            for item in selections
            if stripped_text(item.get("idnumber")) not in set(removed)
        ]

    copied["graph_ablation"] = EXPERIMENT_NAME
    copied["removed_parent_ids"] = list(removed)
    copied["rule_version"] = GRAPH_RULE_VERSION
    return copied, removed


def simulate_child_preference(
    predictions: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build a separate simulated prediction set. Originals stay intact."""

    simulated: list[dict[str, Any]] = []
    removed_parent_count = 0
    affected_fragment_ids: list[str] = []
    removed_by_parent: Counter[str] = Counter()

    for record in predictions:
        copied, removed = apply_child_preference(record, index)
        simulated.append(copied)
        removed_parent_count += len(removed)

        if removed:
            affected_fragment_ids.append(
                stripped_text(record.get("fragment_id"))
            )
            removed_by_parent.update(removed)

    return simulated, {
        "experiment_name": EXPERIMENT_NAME,
        "rule_version": GRAPH_RULE_VERSION,
        "removed_parent_count": removed_parent_count,
        "affected_fragment_count": len(affected_fragment_ids),
        "affected_fragment_ids": affected_fragment_ids,
        "removed_parent_frequencies": dict(removed_by_parent),
        "original_predictions_modified": False,
    }


def count_removed_true_reference_labels(
    gold_rows: Sequence[Mapping[str, Any]],
    original: Sequence[Mapping[str, Any]],
    simulated: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count gold labels present originally and absent after ablation."""

    gold_sets = gold_sets_from_rows(gold_rows)
    original_sets = predicted_sets_from_gemini(gold_rows, original)
    simulated_sets = predicted_sets_from_gemini(gold_rows, simulated)
    details: list[dict[str, Any]] = []
    total = 0

    for row, gold, orig, sim in zip(
        gold_rows,
        gold_sets,
        original_sets,
        simulated_sets,
        strict=True,
    ):
        removed = sorted(set(orig) & set(gold) - set(sim))

        if not removed:
            continue

        total += len(removed)
        details.append(
            {
                "fragment_id": stripped_text(row.get("fragment_id")),
                "removed_true_reference_labels": removed,
            }
        )

    return {
        "removed_true_reference_labels": total,
        "fragments_with_removed_true_reference_labels": len(details),
        "details": details,
    }


def evaluate_fragment_predictions(
    gold_rows: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
    *,
    parent_child_redundancy_count: int,
) -> dict[str, Any]:
    """Same fragment metric definitions as the frozen Gemini evaluation."""

    gold_sets = gold_sets_from_rows(gold_rows)
    predicted_sets = predicted_sets_from_gemini(gold_rows, predictions)
    labels = [
        stripped_text(item.get("idnumber"))
        for item in competencies
        if stripped_text(item.get("idnumber"))
    ]
    micro = micro_prf(gold_sets, predicted_sets)
    views = macro_prf_views(gold_sets, predicted_sets, labels)
    rows: list[dict[str, Any]] = []

    for row, gold, predicted in zip(
        gold_rows,
        gold_sets,
        predicted_sets,
        strict=True,
    ):
        scores = instance_prf(gold, predicted)
        fragment_id = stripped_text(row.get("fragment_id"))
        source = next(
            (
                item
                for item in predictions
                if stripped_text(item.get("fragment_id")) == fragment_id
            ),
            {},
        )
        rows.append(
            {
                "fragment_id": fragment_id,
                "gold_competency_ids": gold,
                "predicted_competency_ids": predicted,
                "removed_parent_ids": list(
                    source.get("removed_parent_ids") or []
                ),
                "exact_set_match": set(gold) == set(predicted),
                "precision": scores["precision"],
                "recall": scores["recall"],
                "f1": scores["f1"],
            }
        )

    return {
        "status": "COMPLETE",
        "final": False,
        "experiment_kind": "post-hoc hierarchy / graph ablation",
        "original_predictions_modified": False,
        "micro_precision": micro["precision"],
        "micro_recall": micro["recall"],
        "micro_f1": micro["f1"],
        "macro_all_13": dict(views["macro_all_13"]),
        "macro_gold_supported_labels": dict(
            views["macro_gold_supported_labels"]
        ),
        "macro_precision": views["macro_all_13"]["precision"],
        "macro_recall": views["macro_all_13"]["recall"],
        "macro_f1": views["macro_all_13"]["f1"],
        "exact_set_match": exact_set_match(gold_sets, predicted_sets),
        "coverage": coverage_rate(predicted_sets),
        "abstention_rate": abstention_rate(predicted_sets),
        "average_predicted_labels": average_predicted_labels(predicted_sets),
        "parent_child_redundancy_count": parent_child_redundancy_count,
        "per_fragment": rows,
    }


def warning_table_rows(
    warnings: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for item in warnings:
        rows.append(
            {
                "fragment_id": str(item.get("fragment_id") or ""),
                "resource_id": str(item.get("resource_id") or ""),
                "warning_type": str(item.get("warning_type") or ""),
                "parent_id": str(item.get("parent_id") or ""),
                "child_id": str(item.get("child_id") or ""),
                "parent_confidence": (
                    ""
                    if item.get("parent_confidence") is None
                    else _fmt(float(item["parent_confidence"]))
                ),
                "child_confidence": (
                    ""
                    if item.get("child_confidence") is None
                    else _fmt(float(item["child_confidence"]))
                ),
                "parent_evidence": " | ".join(
                    _evidence_list(item.get("parent_evidence"))
                ),
                "child_evidence": " | ".join(
                    _evidence_list(item.get("child_evidence"))
                ),
                "same_or_overlapping_evidence": _bool_text(
                    bool(item.get("same_or_overlapping_evidence"))
                ),
                "action": WARNING_ACTION,
            }
        )

    return rows


def resource_warning_table_rows(
    warnings: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for item in warnings:
        rows.append(
            {
                "resource_id": str(item.get("resource_id") or ""),
                "course_shortname": str(item.get("course_shortname") or ""),
                "resource_type": str(item.get("resource_type") or ""),
                "warning_type": str(item.get("warning_type") or ""),
                "parent_id": str(item.get("parent_id") or ""),
                "child_id": str(item.get("child_id") or ""),
                "parent_confidence": (
                    ""
                    if item.get("parent_confidence") is None
                    else _fmt(float(item["parent_confidence"]))
                ),
                "child_confidence": (
                    ""
                    if item.get("child_confidence") is None
                    else _fmt(float(item["child_confidence"]))
                ),
                "parent_evidence": " | ".join(
                    _evidence_list(item.get("parent_evidence"))
                ),
                "child_evidence": " | ".join(
                    _evidence_list(item.get("child_evidence"))
                ),
                "same_or_overlapping_evidence": _bool_text(
                    bool(item.get("same_or_overlapping_evidence"))
                ),
                "action": WARNING_ACTION,
            }
        )

    return rows


def fragment_eval_table_rows(
    evaluation: Mapping[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for item in evaluation.get("per_fragment") or []:
        rows.append(
            {
                "fragment_id": item["fragment_id"],
                "gold_competency_ids": _join(item["gold_competency_ids"]),
                "predicted_competency_ids": _join(
                    item["predicted_competency_ids"]
                ),
                "removed_parent_ids": _join(item["removed_parent_ids"]),
                "exact_set_match": _bool_text(bool(item["exact_set_match"])),
                "precision": _fmt(float(item["precision"])),
                "recall": _fmt(float(item["recall"])),
                "f1": _fmt(float(item["f1"])),
            }
        )

    return rows


def fragment_ablation_comparison_rows(
    original: Mapping[str, Any],
    simulated: Mapping[str, Any],
) -> list[dict[str, str]]:
    def row(name: str, metrics: Mapping[str, Any], deltas: Mapping[str, float]) -> dict[str, str]:
        return {
            "system": name,
            "micro_precision": _fmt(metrics["micro_precision"]),
            "micro_recall": _fmt(metrics["micro_recall"]),
            "micro_f1": _fmt(metrics["micro_f1"]),
            "macro_all_13_f1": _fmt(metrics["macro_all_13"]["f1"]),
            "macro_gold_supported_f1": _fmt(
                metrics["macro_gold_supported_labels"]["f1"]
            ),
            "exact_set_match": _fmt(metrics["exact_set_match"]),
            "coverage": _fmt(metrics["coverage"]),
            "abstention_rate": _fmt(metrics["abstention_rate"]),
            "average_predicted_labels": _fmt(
                metrics["average_predicted_labels"]
            ),
            "parent_child_redundancy_count": str(
                metrics["parent_child_redundancy_count"]
            ),
            "delta_micro_precision": _fmt(deltas["micro_precision"]),
            "delta_micro_recall": _fmt(deltas["micro_recall"]),
            "delta_micro_f1": _fmt(deltas["micro_f1"]),
            "delta_exact_set_match": _fmt(deltas["exact_set_match"]),
        }

    zeros = {
        "micro_precision": 0.0,
        "micro_recall": 0.0,
        "micro_f1": 0.0,
        "exact_set_match": 0.0,
    }
    deltas = {
        key: float(simulated[key]) - float(original[key])
        for key in zeros
    }
    return [
        row("Original BM25 Top-5 + Gemini", original, zeros),
        row("Post-hoc child-preference reconciliation", simulated, deltas),
    ]


def resource_ablation_comparison_rows(
    original: Mapping[str, Any],
    simulated: Mapping[str, Any],
) -> list[dict[str, str]]:
    def row(name: str, metrics: Mapping[str, Any], deltas: Mapping[str, float]) -> dict[str, str]:
        return {
            "system": name,
            "micro_precision": _fmt(metrics["micro_precision"]),
            "micro_recall": _fmt(metrics["micro_recall"]),
            "micro_f1": _fmt(metrics["micro_f1"]),
            "macro_all_13_f1": _fmt(metrics["macro_all_13"]["f1"]),
            "macro_gold_supported_f1": _fmt(
                metrics["macro_gold_supported_labels"]["f1"]
            ),
            "exact_set_match": _fmt(metrics["exact_set_match"]),
            "average_predicted_labels": _fmt(
                metrics["average_predicted_label_count"]
            ),
            "average_absolute_label_count_error": _fmt(
                metrics["average_absolute_label_count_error"]
            ),
            "parent_child_redundancy_count": str(
                metrics["parent_child_redundant_resource_count"]
            ),
            "delta_micro_precision": _fmt(deltas["micro_precision"]),
            "delta_micro_recall": _fmt(deltas["micro_recall"]),
            "delta_micro_f1": _fmt(deltas["micro_f1"]),
            "delta_exact_set_match": _fmt(deltas["exact_set_match"]),
        }

    zeros = {
        "micro_precision": 0.0,
        "micro_recall": 0.0,
        "micro_f1": 0.0,
        "exact_set_match": 0.0,
    }
    deltas = {
        key: float(simulated[key]) - float(original[key])
        for key in zeros
    }
    return [
        row("Original resource-level Gemini", original, zeros),
        row("Post-hoc child-preference resource predictions", simulated, deltas),
    ]


def build_graph_examples(
    *,
    gold_rows: Sequence[Mapping[str, Any]],
    original: Sequence[Mapping[str, Any]],
    simulated: Sequence[Mapping[str, Any]],
    warnings: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Real frozen-run examples only. Does not invent fragment IDs."""

    context = fragment_context_from_rows(gold_rows)
    original_by_id = {
        stripped_text(item.get("fragment_id")): item for item in original
    }
    simulated_by_id = {
        stripped_text(item.get("fragment_id")): item for item in simulated
    }
    gold_by_id = {
        stripped_text(row.get("fragment_id")): row for row in gold_rows
    }
    examples: list[dict[str, str]] = []
    used_kinds: set[tuple[str, str]] = set()

    def predicted_ids(record: Mapping[str, Any] | None) -> list[str]:
        if not record:
            return []

        return [
            item["idnumber"] for item in selections_from_fragment(record)
        ]

    def add(
        fragment_id: str,
        parent_id: str,
        child_id: str,
        explanation: str,
        kind: str,
    ) -> None:
        key = (kind, fragment_id)

        if key in used_kinds or fragment_id not in original_by_id:
            return

        orig = original_by_id[fragment_id]
        sim = simulated_by_id.get(fragment_id) or orig
        gold_ids, _errors = parse_competency_ids(
            (gold_by_id.get(fragment_id) or {}).get("gold_competency_ids")
        )
        orig_ids = predicted_ids(orig)
        sim_ids = predicted_ids(sim)
        parent_sel = _selection_map(selections_from_fragment(orig)).get(
            parent_id,
            {},
        )
        child_sel = _selection_map(selections_from_fragment(orig)).get(
            child_id,
            {},
        )
        evidence = list(parent_sel.get("evidence") or [])
        evidence.extend(
            quote
            for quote in child_sel.get("evidence") or []
            if quote not in evidence
        )
        examples.append(
            {
                "fragment_id": fragment_id,
                "fragment_text": context.get(fragment_id, {}).get(
                    "fragment_text",
                    "",
                ),
                "original_predictions": _join(orig_ids),
                "reference_labels": _join(gold_ids),
                "parent": parent_id,
                "child": child_id,
                "evidence": " | ".join(evidence),
                "original_correct": _bool_text(
                    set(orig_ids) == set(gold_ids)
                ),
                "simulated_predictions": _join(sim_ids),
                "simulated_correct": _bool_text(
                    set(sim_ids) == set(gold_ids)
                ),
                "explanation": explanation,
            }
        )
        used_kinds.add(key)

    redundancy = [
        item
        for item in warnings
        if item.get("warning_type") == "parent_child_redundancy"
    ]

    for parent_id in ("GI_C1", "GI_C2", "GI_C3"):
        match = next(
            (
                item
                for item in redundancy
                if item.get("parent_id") == parent_id
            ),
            None,
        )

        if match is None:
            continue

        add(
            stripped_text(match.get("fragment_id")),
            parent_id,
            stripped_text(match.get("child_id")),
            f"Frozen Gemini predicted parent {parent_id} together with "
            f"direct child {match.get('child_id')}.",
            kind=f"parent_{parent_id}",
        )

    for item in redundancy:
        fragment_id = stripped_text(item.get("fragment_id"))
        orig_ids = predicted_ids(original_by_id.get(fragment_id))
        sim_ids = predicted_ids(simulated_by_id.get(fragment_id))
        gold_ids, _errors = parse_competency_ids(
            (gold_by_id.get(fragment_id) or {}).get("gold_competency_ids")
        )

        if set(orig_ids) != set(gold_ids) and set(sim_ids) == set(gold_ids):
            add(
                fragment_id,
                stripped_text(item.get("parent_id")),
                stripped_text(item.get("child_id")),
                "Removing the redundant parent makes the predicted set "
                "equal the human-reviewed reference set.",
                kind="improved_by_removing_parent",
            )
            break

    for record in original:
        orig_ids = predicted_ids(record)
        removed = redundant_parents_to_remove(orig_ids, index)
        preserved = [
            competency_id
            for competency_id in orig_ids
            if competency_id in set(index.get("roots") or [])
            and competency_id not in set(removed)
        ]

        if preserved:
            fragment_id = stripped_text(record.get("fragment_id"))
            parent_id = preserved[0]
            add(
                fragment_id,
                parent_id,
                "",
                f"Parent {parent_id} appears without a direct child and "
                "is preserved by the child-preference rule.",
                kind="parent_alone_preserved",
            )
            break

    return examples


def metrics_without_rows(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in evaluation.items()
        if key != "per_fragment"
    }


def render_graph_report(
    *,
    hierarchy: Mapping[str, Any],
    fragment_summary: Mapping[str, Any],
    resource_summary: Mapping[str, Any],
    original_fragment: Mapping[str, Any],
    simulated_fragment: Mapping[str, Any],
    original_resource: Mapping[str, Any],
    simulated_resource: Mapping[str, Any],
    simulation_stats: Mapping[str, Any],
    removed_gold: Mapping[str, Any],
    examples: Sequence[Mapping[str, str]],
) -> str:
    """Human-readable post-hoc hierarchy ablation report."""

    def sign_text(delta: float, noun: str) -> str:
        if abs(delta) < 1e-12:
            return f"{noun} did not change."

        direction = "increased" if delta > 0 else "decreased"
        return f"{noun} {direction} by {abs(delta):.4f}."

    p_delta = (
        float(simulated_fragment["micro_precision"])
        - float(original_fragment["micro_precision"])
    )
    r_delta = (
        float(simulated_fragment["micro_recall"])
        - float(original_fragment["micro_recall"])
    )
    f_delta = (
        float(simulated_fragment["micro_f1"])
        - float(original_fragment["micro_f1"])
    )
    e_delta = (
        float(simulated_fragment["exact_set_match"])
        - float(original_fragment["exact_set_match"])
    )
    rp_delta = (
        float(simulated_resource["micro_precision"])
        - float(original_resource["micro_precision"])
    )
    re_delta = (
        float(simulated_resource["exact_set_match"])
        - float(original_resource["exact_set_match"])
    )
    example_lines = [
        "| fragment_id | parent | child | original | simulated | orig exact | sim exact |",
        "|---|---|---|---|---|---|---|",
    ]

    for item in examples:
        example_lines.append(
            "| `{fid}` | `{p}` | `{c}` | `{o}` | `{s}` | {oe} | {se} |".format(
                fid=item.get("fragment_id", ""),
                p=item.get("parent", "") or "—",
                c=item.get("child", "") or "—",
                o=item.get("original_predictions", ""),
                s=item.get("simulated_predictions", ""),
                oe=item.get("original_correct", ""),
                se=item.get("simulated_correct", ""),
            )
        )

    parent_freq = fragment_summary.get("parent_frequencies") or {}
    most_parent = fragment_summary.get("most_frequent_redundant_parent") or ""

    return "\n".join(
        [
            "# Minimal hierarchy / graph analysis",
            "",
            "**Project:** Moodle Learning Resource-to-Competency Alignment MVP  ",
            "**Researcher:** Wail Ouaret  ",
            "**Date:** 2026-09-18",
            "",
            "This document reports a **post-hoc hierarchy ablation**. "
            "A deterministic hierarchy rule was applied after the frozen "
            "Gemini predictions to assess the effect of removing redundant "
            "parent labels.",
            "",
            "Do not read this as “Gemini used graph reasoning.” The original "
            "Gemini run did not use a graph layer.",
            "",
            "## 1. Motivation",
            "",
            "Fragment-level error analysis found frequent parent-child "
            "redundancy. The human-reviewed reference has no positive support "
            "for the three UTC GI top-level parents `GI_C1`, `GI_C2`, and "
            "`GI_C3`. This experiment tests whether a minimal hierarchy "
            "consistency rule can reduce unnecessary parent predictions.",
            "",
            "## 2. Graph used",
            "",
            "Only the verified UTC GI parent-child hierarchy from "
            "`data/processed/competencies.jsonl` was used. No prerequisite, "
            "related-to, part-of, or similarity edges were invented.",
            "",
            f"- Competency IDs: {hierarchy.get('competency_count')}",
            f"- Root / parent competencies: {hierarchy.get('root_count')} "
            f"({', '.join(hierarchy.get('root_ids') or [])})",
            f"- Child competencies: {hierarchy.get('child_count')}",
            f"- Missing parent references: {len(hierarchy.get('missing_parent_references') or [])}",
            f"- Cycles: {len(hierarchy.get('cycles') or [])}",
            "",
            "## 3. Warning rules",
            "",
            "- `parent_child_redundancy`: a parent and one of its **direct** "
            "children are both predicted for the same fragment or resource.",
            "- `granularity_conflict`: the same parent/child pair is supported "
            "by identical or overlapping evidence quotes.",
            "- `invalid_hierarchy_reference`: unknown competency, missing "
            "parent reference, or malformed hierarchy relation.",
            "",
            "Warnings are non-destructive (`action = warning_only`). Original "
            "predictions are not changed.",
            "",
            "## 4. Original hierarchy inconsistencies",
            "",
            "### Fragments",
            "",
            f"- Fragments checked: {fragment_summary.get('fragments_checked')}",
            f"- Fragments with parent-child redundancy: "
            f"{fragment_summary.get('fragments_with_parent_child_redundancy')}",
            f"- Redundant parent-child pairs: "
            f"{fragment_summary.get('redundant_parent_child_pairs')}",
            f"- Fragments with granularity conflict: "
            f"{fragment_summary.get('fragments_with_granularity_conflict')}",
            f"- Invalid hierarchy references: "
            f"{fragment_summary.get('invalid_hierarchy_references')}",
            f"- Warning rate: {float(fragment_summary.get('warning_rate') or 0):.4f}",
            "",
            "Parent pair frequencies:",
            "",
            f"- GI_C1: {parent_freq.get('GI_C1', 0)}",
            f"- GI_C2: {parent_freq.get('GI_C2', 0)}",
            f"- GI_C3: {parent_freq.get('GI_C3', 0)}",
            "",
            f"Most frequent redundant parent: `{most_parent}`.",
            "",
            "Per-course redundant fragments: "
            + json.dumps(
                fragment_summary.get("per_course_redundant_fragments") or {},
                ensure_ascii=False,
            ),
            "",
            "### Resources",
            "",
            f"- Resources checked: {resource_summary.get('resources_checked')}",
            f"- Resources with parent-child redundancy: "
            f"{resource_summary.get('resources_with_parent_child_redundancy')}",
            f"- Redundant resource parent-child pairs: "
            f"{resource_summary.get('redundant_resource_parent_child_pairs')}",
            "",
            "## 5. Child-preference simulation",
            "",
            "Rule: if a parent and one or more **direct** children are both "
            "predicted, remove the parent from the **simulated** set only. "
            "Keep all children. A parent predicted alone is kept. Unrelated "
            "labels are kept. Confidence is not used to drop labels.",
            "",
            f"- Labels removed (parent instances): "
            f"{simulation_stats.get('removed_parent_count')}",
            f"- Affected fragments: "
            f"{simulation_stats.get('affected_fragment_count')}",
            f"- Removed true human-reference labels: "
            f"{removed_gold.get('removed_true_reference_labels')}",
            "",
            "Simulated outputs are stored under `data/experiments/`. "
            "`data/interim/gemini_validated.jsonl` was not overwritten.",
            "",
            "## 6. Fragment-level before/after metrics",
            "",
            "| Metric | Original Gemini | Post-hoc child-preference |",
            "|---|---:|---:|",
            f"| Micro precision | {float(original_fragment['micro_precision']):.10f} | {float(simulated_fragment['micro_precision']):.10f} |",
            f"| Micro recall | {float(original_fragment['micro_recall']):.10f} | {float(simulated_fragment['micro_recall']):.10f} |",
            f"| Micro F1 | {float(original_fragment['micro_f1']):.10f} | {float(simulated_fragment['micro_f1']):.10f} |",
            f"| Macro all-13 F1 | {float(original_fragment['macro_all_13']['f1']):.10f} | {float(simulated_fragment['macro_all_13']['f1']):.10f} |",
            f"| Macro gold-supported F1 | {float(original_fragment['macro_gold_supported_labels']['f1']):.10f} | {float(simulated_fragment['macro_gold_supported_labels']['f1']):.10f} |",
            f"| Exact-set match | {float(original_fragment['exact_set_match']):.10f} | {float(simulated_fragment['exact_set_match']):.10f} |",
            f"| Coverage | {float(original_fragment['coverage']):.10f} | {float(simulated_fragment['coverage']):.10f} |",
            f"| Abstention | {float(original_fragment['abstention_rate']):.10f} | {float(simulated_fragment['abstention_rate']):.10f} |",
            f"| Average predicted labels | {float(original_fragment['average_predicted_labels']):.10f} | {float(simulated_fragment['average_predicted_labels']):.10f} |",
            f"| Parent-child redundancy fragments | {original_fragment['parent_child_redundancy_count']} | {simulated_fragment['parent_child_redundancy_count']} |",
            "",
            "## 7. Resource-level before/after metrics",
            "",
            "| Metric | Original resource Gemini | Post-hoc child-preference |",
            "|---|---:|---:|",
            f"| Micro precision | {float(original_resource['micro_precision']):.10f} | {float(simulated_resource['micro_precision']):.10f} |",
            f"| Micro recall | {float(original_resource['micro_recall']):.10f} | {float(simulated_resource['micro_recall']):.10f} |",
            f"| Micro F1 | {float(original_resource['micro_f1']):.10f} | {float(simulated_resource['micro_f1']):.10f} |",
            f"| Macro all-13 F1 | {float(original_resource['macro_all_13']['f1']):.10f} | {float(simulated_resource['macro_all_13']['f1']):.10f} |",
            f"| Macro gold-supported F1 | {float(original_resource['macro_gold_supported_labels']['f1']):.10f} | {float(simulated_resource['macro_gold_supported_labels']['f1']):.10f} |",
            f"| Exact-set accuracy | {float(original_resource['exact_set_match']):.10f} | {float(simulated_resource['exact_set_match']):.10f} |",
            f"| Average predicted labels | {float(original_resource['average_predicted_label_count']):.10f} | {float(simulated_resource['average_predicted_label_count']):.10f} |",
            f"| Average label-count error | {float(original_resource['average_absolute_label_count_error']):.10f} | {float(simulated_resource['average_absolute_label_count_error']):.10f} |",
            f"| Parent-child redundant resources | {original_resource['parent_child_redundant_resource_count']} | {simulated_resource['parent_child_redundant_resource_count']} |",
            "",
            "## 8. Example cases",
            "",
            *example_lines,
            "",
            "No invented examples. If a parent-alone row is missing, no frozen "
            "Gemini fragment predicted a parent without a direct child.",
            "",
            "## 9. Effect on precision",
            "",
            sign_text(p_delta, "Fragment-level micro precision"),
            sign_text(rp_delta, "Resource-level micro precision"),
            "",
            "## 10. Effect on recall",
            "",
            sign_text(r_delta, "Fragment-level micro recall"),
            "",
            "Recall is expected to stay the same if no human-reference labels "
            "are removed. Measured removed true reference labels: "
            f"{removed_gold.get('removed_true_reference_labels')}.",
            "",
            "## 11. Effect on F1",
            "",
            sign_text(f_delta, "Fragment-level micro F1"),
            "",
            "## 12. Effect on exact-set accuracy",
            "",
            sign_text(e_delta, "Fragment-level exact-set match"),
            sign_text(re_delta, "Resource-level exact-set accuracy"),
            "",
            "## 13. Limitations",
            "",
            "- This is a post-hoc ablation, not part of the historical Gemini run.",
            "- Only direct parent-child edges are used.",
            "- A two-level UTC GI subset cannot test deeper ancestry rules.",
            "- Teacher validation has not started.",
            "- Small corpus: 35 fragments, 20 resources, 13 competencies.",
            "",
            "## 14. Conclusion",
            "",
            "A deterministic child-preference rule can be applied after frozen "
            "Gemini predictions to drop redundant parents. Original Gemini "
            "metrics remain the system-of-record for the constrained LLM run. "
            "The ablation is stored separately under `data/experiments/`.",
            "",
            "Next phase: teacher-facing runtime analysis + validation interface. "
            "Teacher UI is not started. Teacher decisions remain 0.",
            "",
        ]
    )
