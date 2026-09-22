"""Build competency -> resource inverse index from Function A outputs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from moodle_competency.annotation import stripped_text
from moodle_competency.llm_validation import write_jsonl


INVERSE_INDEX_VERSION = "1.0"


def build_competency_resource_index(
    *,
    competencies: Sequence[Mapping[str, Any]],
    resource_predictions: Sequence[Mapping[str, Any]],
    teacher_reviews: Sequence[Mapping[str, Any]] | None = None,
    upstream_completeness: str = "unknown",
) -> list[dict[str, Any]]:
    """Invert resource predictions. Include competencies with zero resources.

    Teacher decisions stay pending unless a real review record exists.
    Do not invent accept/reject/modify values.
    """

    reviews_by_pair: dict[tuple[str, str], str] = {}

    for review in teacher_reviews or []:
        resource_id = stripped_text(review.get("resource_id"))
        competency_id = stripped_text(
            review.get("competency_id")
        )
        status = stripped_text(
            review.get("decision")
            or review.get("teacher_decision_status")
        )

        if resource_id and competency_id and status:
            reviews_by_pair[(resource_id, competency_id)] = status

    resources_by_competency: dict[str, list[dict[str, Any]]] = {
        stripped_text(item.get("idnumber")): []
        for item in competencies
        if stripped_text(item.get("idnumber"))
    }

    for resource in resource_predictions:
        resource_id = stripped_text(resource.get("resource_id"))

        for predicted in resource.get("predicted_competencies") or []:
            competency_id = stripped_text(
                predicted.get("competency_id")
            )

            if competency_id not in resources_by_competency:
                continue

            resources_by_competency[competency_id].append(
                {
                    "resource_id": resource_id,
                    "course_id": resource.get("course_id"),
                    "course_shortname": stripped_text(
                        resource.get("course_shortname")
                    ),
                    "resource_type": stripped_text(
                        resource.get("resource_type")
                    ),
                    "resource_title": stripped_text(
                        resource.get("title")
                        or resource.get("resource_title")
                    ),
                    "fragment_ids": list(
                        predicted.get("fragment_ids") or []
                    ),
                    "evidence": list(predicted.get("evidence") or []),
                    "max_confidence": predicted.get("max_confidence"),
                    "mean_confidence": predicted.get(
                        "mean_confidence"
                    ),
                    "support_count": predicted.get(
                        "support_count",
                        0,
                    ),
                    "teacher_decision_status": reviews_by_pair.get(
                        (resource_id, competency_id),
                        "pending",
                    ),
                }
            )

    index: list[dict[str, Any]] = []

    for competency in competencies:
        competency_id = stripped_text(competency.get("idnumber"))

        if not competency_id:
            continue

        matches = sorted(
            resources_by_competency.get(competency_id, []),
            key=lambda item: (
                str(item.get("course_shortname") or ""),
                str(item.get("resource_id") or ""),
            ),
        )
        index.append(
            {
                "competency_id": competency_id,
                "shortname": stripped_text(
                    competency.get("shortname")
                ),
                "description": stripped_text(
                    competency.get("description_text")
                    or competency.get("description")
                ),
                "parent_idnumber": stripped_text(
                    competency.get("parent_idnumber")
                ),
                "depth": competency.get("depth"),
                "match_count": len(matches),
                "resources": matches,
                "upstream_completeness": upstream_completeness,
                "inverse_index_version": INVERSE_INDEX_VERSION,
            }
        )

    return index


def write_competency_resource_index(
    records: Sequence[Mapping[str, Any]],
    output_path,
) -> None:
    write_jsonl(records, output_path)
