"""Section O — a minimal view of teacher-validated coverage.

Deliberately small. This is *not* a curriculum analytics product: there are no
recommendations, no learning paths, no taught-versus-assessed classification
and no dashboard. Those are deferred unless the supervisors reopen them.

What "validated" means
----------------------
A resource-competency pair is validated only when a human decision says so:

``accept``  the predicted pair is validated as-is;
``modify``  the predicted pair is *not* validated; each replacement competency
            the reviewer named is validated for that resource instead;
``add``     a pair the model never predicted is validated;
``reject``  the pair is not validated.

An unreviewed prediction is **not** coverage. Until a human decides, the pair
is pending, and this module reports it as such rather than counting it.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from moodle_competency.annotation import stripped_text


COVERAGE_VERSION = "1.0"

VALIDATING_DECISIONS = frozenset({"accept", "add"})

COVERAGE_TABLE_COLUMNS = (
    "scope",
    "key",
    "validated_count",
    "detail",
)


def _split_ids(value: Any) -> list[str]:
    return [part.strip() for part in stripped_text(value).split(";") if part.strip()]


def validated_pairs(
    reviews: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Every (resource, competency) pair a human decision validates.

    Results are deduplicated and sorted, so the output is stable regardless of
    the order decisions were recorded in.
    """

    pairs: dict[tuple[str, str], dict[str, str]] = {}

    for review in reviews:
        decision = stripped_text(review.get("decision")).lower()
        resource_id = stripped_text(review.get("resource_id"))
        competency_id = stripped_text(review.get("competency_id"))

        if not resource_id:
            continue

        if decision in VALIDATING_DECISIONS and competency_id:
            pairs[(resource_id, competency_id)] = {
                "resource_id": resource_id,
                "competency_id": competency_id,
                "via": decision,
                "reviewer": stripped_text(review.get("reviewer")),
            }
            continue

        if decision == "modify":
            for replacement in _split_ids(review.get("modified_competency_ids")):
                pairs[(resource_id, replacement)] = {
                    "resource_id": resource_id,
                    "competency_id": replacement,
                    "via": "modify",
                    "reviewer": stripped_text(review.get("reviewer")),
                }

    return [pairs[key] for key in sorted(pairs)]


def competency_to_resources(
    pairs: Sequence[Mapping[str, Any]],
    competency_ids: Sequence[str],
) -> dict[str, list[str]]:
    """Validated resources per competency, including competencies with none."""

    result: dict[str, list[str]] = {
        stripped_text(value): [] for value in competency_ids
    }

    for pair in pairs:
        competency_id = stripped_text(pair.get("competency_id"))
        resource_id = stripped_text(pair.get("resource_id"))
        result.setdefault(competency_id, [])

        if resource_id not in result[competency_id]:
            result[competency_id].append(resource_id)

    return {key: sorted(result[key]) for key in sorted(result)}


def resource_to_competencies(
    pairs: Sequence[Mapping[str, Any]],
    resource_ids: Sequence[str],
) -> dict[str, list[str]]:
    """Validated competencies per resource, including resources with none."""

    result: dict[str, list[str]] = {stripped_text(value): [] for value in resource_ids}

    for pair in pairs:
        resource_id = stripped_text(pair.get("resource_id"))
        competency_id = stripped_text(pair.get("competency_id"))
        result.setdefault(resource_id, [])

        if competency_id not in result[resource_id]:
            result[resource_id].append(competency_id)

    return {key: sorted(result[key]) for key in sorted(result)}


def build_coverage(
    reviews: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
    competency_ids: Sequence[str],
) -> dict[str, Any]:
    """The full minimal coverage payload.

    With no validated pair, this reports zero coverage explicitly and marks
    every resource unmapped — it does not fall back to predictions.
    """

    pairs = validated_pairs(reviews)

    resource_ids = [stripped_text(r.get("resource_id")) for r in resources]
    resource_index = {
        stripped_text(r.get("resource_id")): dict(r) for r in resources
    }

    by_competency = competency_to_resources(pairs, competency_ids)
    by_resource = resource_to_competencies(pairs, resource_ids)

    unmapped = [
        resource_id
        for resource_id in sorted(resource_ids)
        if not by_resource.get(resource_id)
    ]
    uncovered = [
        competency_id
        for competency_id in sorted(competency_ids)
        if not by_competency.get(competency_id)
    ]

    per_course: dict[str, int] = {}
    per_section: dict[str, int] = {}

    for pair in pairs:
        resource = resource_index.get(stripped_text(pair.get("resource_id")), {})
        course = stripped_text(resource.get("course_shortname")) or "unknown"
        section = stripped_text(resource.get("section_name")) or "unknown"
        section_key = f"{course} · {section}"

        per_course[course] = per_course.get(course, 0) + 1
        per_section[section_key] = per_section.get(section_key, 0) + 1

    per_competency = {
        competency_id: len(by_competency.get(competency_id, []))
        for competency_id in sorted(competency_ids)
    }

    return {
        "coverage_version": COVERAGE_VERSION,
        "status": "COMPLETE" if pairs else "WAITING_FOR_HUMAN",
        "message": (
            None
            if pairs
            else "NO VALIDATED MAPPING EXISTS. Coverage requires a human decision."
        ),
        "validated_mapping_count": len(pairs),
        "validated_pairs": pairs,
        "resource_count": len(resource_ids),
        "competency_count": len(competency_ids),
        "mapped_resource_count": len(resource_ids) - len(unmapped),
        "covered_competency_count": len(competency_ids) - len(uncovered),
        "unmapped_resources": unmapped,
        "competencies_without_validated_resources": uncovered,
        "competency_to_resources": by_competency,
        "resource_to_competencies": by_resource,
        "validated_by_course": {key: per_course[key] for key in sorted(per_course)},
        "validated_by_section": {key: per_section[key] for key in sorted(per_section)},
        "validated_by_competency": per_competency,
        "scope_note": (
            "Minimal validated-mapping view only. No recommendation engine, "
            "learning paths, taught-versus-assessed analytics or dashboard."
        ),
        "definition_note": (
            "Validated means a human decision said so: accept, add, or the "
            "replacement side of a modify. An unreviewed prediction is not "
            "coverage."
        ),
    }


def coverage_table_rows(coverage: Mapping[str, Any]) -> list[dict[str, str]]:
    """Flatten the coverage payload into reportable CSV rows."""

    rows: list[dict[str, str]] = [
        {
            "scope": "overall",
            "key": "status",
            "validated_count": str(coverage.get("validated_mapping_count", 0)),
            "detail": stripped_text(coverage.get("status")),
        }
    ]

    for competency_id, resource_ids in (
        coverage.get("competency_to_resources") or {}
    ).items():
        rows.append(
            {
                "scope": "competency",
                "key": competency_id,
                "validated_count": str(len(resource_ids)),
                "detail": ";".join(resource_ids),
            }
        )

    for resource_id, competency_ids in (
        coverage.get("resource_to_competencies") or {}
    ).items():
        rows.append(
            {
                "scope": "resource",
                "key": resource_id,
                "validated_count": str(len(competency_ids)),
                "detail": ";".join(competency_ids),
            }
        )

    for course, count in (coverage.get("validated_by_course") or {}).items():
        rows.append(
            {
                "scope": "course",
                "key": course,
                "validated_count": str(count),
                "detail": "",
            }
        )

    for section, count in (coverage.get("validated_by_section") or {}).items():
        rows.append(
            {
                "scope": "section",
                "key": section,
                "validated_count": str(count),
                "detail": "",
            }
        )

    return rows
