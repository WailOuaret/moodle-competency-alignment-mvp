"""Storage layer for later teacher accept/reject/modify reviews.

This is not a UI. Decisions stay pending unless a real review file exists.
Do not invent teacher decisions. Wail's own tests are researcher reviews,
not teacher validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import read_csv, stripped_text, write_csv


TEACHER_REVIEW_COLUMNS = (
    "review_id",
    "resource_id",
    "competency_id",
    "fragment_ids",
    "decision",
    "modified_competency_ids",
    "comment",
    "evidence_relevance",
    "reviewer",
    "review_date",
)

ALLOWED_DECISIONS = {"accept", "reject", "modify"}
ALLOWED_EVIDENCE_RELEVANCE = {"0", "1", "2"}


def empty_review_row(
    *,
    resource_id: str,
    competency_id: str,
    fragment_ids: Sequence[str] | None = None,
) -> dict[str, str]:
    """Blank pending review. Never pre-fills accept/reject/modify."""

    return {
        "review_id": f"{resource_id}|{competency_id}",
        "resource_id": resource_id,
        "competency_id": competency_id,
        "fragment_ids": ";".join(fragment_ids or []),
        "decision": "",
        "modified_competency_ids": "",
        "comment": "",
        "evidence_relevance": "",
        "reviewer": "",
        "review_date": "",
    }


def load_teacher_reviews(path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    return read_csv(path)


def decision_status(
    reviews: Sequence[Mapping[str, Any]],
    resource_id: str,
    competency_id: str,
) -> str:
    """Return a stored teacher decision or pending."""

    for review in reviews:
        if (
            stripped_text(review.get("resource_id")) == resource_id
            and stripped_text(review.get("competency_id")) == competency_id
        ):
            decision = stripped_text(review.get("decision")).lower()

            if decision in ALLOWED_DECISIONS:
                return decision

    return "pending"


def write_teacher_reviews(
    rows: Sequence[Mapping[str, Any]],
    output_path,
) -> None:
    write_csv(rows, output_path, TEACHER_REVIEW_COLUMNS)


RUNTIME_REVIEW_COLUMNS = (
    "review_id",
    "analysis_id",
    "runtime_resource_id",
    "fragment_id",
    "competency_id",
    "suggested_by_model",
    "original_prediction",
    "reconciled_prediction",
    "decision",
    "replacement_competency_id",
    "comment",
    "reviewer_name",
    "reviewer_role",
    "review_date",
    "backend",
    "model",
)

ALLOWED_RUNTIME_DECISIONS = {"ACCEPT", "REJECT", "MODIFY"}
ALLOWED_REVIEWER_ROLES = {"researcher", "teacher", "supervisor"}


class InvalidReviewError(ValueError):
    """Raised when a runtime review cannot be stored."""


def utc_review_date(moment: datetime | None = None) -> str:
    value = moment or datetime.now(timezone.utc)
    return value.date().isoformat()


def review_kind_label(role: str) -> str:
    normalized = stripped_text(role).casefold()

    if normalized == "teacher":
        return "teacher review"

    if normalized == "supervisor":
        return "supervisor review"

    return "researcher review"


def normalize_runtime_decision(decision: str) -> str:
    value = stripped_text(decision).upper()

    if value not in ALLOWED_RUNTIME_DECISIONS:
        raise InvalidReviewError(
            f"Decision must be ACCEPT, REJECT, or MODIFY, not {decision!r}."
        )

    return value


def load_runtime_reviews(path: Path) -> list[dict[str, str]]:
    if not Path(path).exists():
        return []

    return read_csv(path)


def catalogue_id_set(competency_ids: Sequence[str]) -> set[str]:
    return {
        stripped_text(value)
        for value in competency_ids
        if stripped_text(value)
    }


def persist_runtime_review(
    *,
    analysis_id: str,
    runtime_resource_id: str,
    competency_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    catalogue_ids: Sequence[str],
    fragment_id: str | None = None,
    suggested_by_model: bool = True,
    original_prediction: bool = True,
    reconciled_prediction: bool | None = None,
    replacement_competency_id: str | None = None,
    comment: str = "",
    backend: str = "",
    model: str = "",
    path: Path,
) -> dict[str, str]:
    """Store one human decision. Does not invent reviewer identity."""

    name = stripped_text(reviewer_name)
    role = stripped_text(reviewer_role).casefold()
    normalized_decision = normalize_runtime_decision(decision)
    allowed = catalogue_id_set(catalogue_ids)
    competency = stripped_text(competency_id)
    replacement = stripped_text(replacement_competency_id)

    if not stripped_text(analysis_id):
        raise InvalidReviewError("analysis_id is required.")

    if not stripped_text(runtime_resource_id):
        raise InvalidReviewError("runtime_resource_id is required.")

    if competency not in allowed:
        raise InvalidReviewError(
            f"Unknown competency {competency_id!r}."
        )

    if not name:
        raise InvalidReviewError(
            "reviewer_name is required. Do not fabricate reviewer information."
        )

    if role not in ALLOWED_REVIEWER_ROLES:
        raise InvalidReviewError(
            "reviewer_role must be researcher, teacher, or supervisor."
        )

    if normalized_decision == "MODIFY":
        if not replacement:
            raise InvalidReviewError(
                "MODIFY requires a replacement competency from the catalogue."
            )

        if replacement not in allowed:
            raise InvalidReviewError(
                "Invalid MODIFY competency: replacement must be one of "
                "the 13 catalogue identifiers."
            )
    elif replacement:
        raise InvalidReviewError(
            "replacement_competency_id is only allowed for MODIFY."
        )

    review_date = utc_review_date()
    review_id = "|".join(
        [
            stripped_text(analysis_id),
            stripped_text(runtime_resource_id),
            stripped_text(fragment_id),
            competency,
            review_date,
            name,
        ]
    )
    row = {
        "review_id": review_id,
        "analysis_id": stripped_text(analysis_id),
        "runtime_resource_id": stripped_text(runtime_resource_id),
        "fragment_id": stripped_text(fragment_id),
        "competency_id": competency,
        "suggested_by_model": "true" if suggested_by_model else "false",
        "original_prediction": "true" if original_prediction else "false",
        "reconciled_prediction": (
            ""
            if reconciled_prediction is None
            else ("true" if reconciled_prediction else "false")
        ),
        "decision": normalized_decision,
        "replacement_competency_id": replacement,
        "comment": str(comment or ""),
        "reviewer_name": name,
        "reviewer_role": role,
        "review_date": review_date,
        "backend": stripped_text(backend),
        "model": stripped_text(model),
    }
    existing = load_runtime_reviews(path)
    existing.append(row)
    write_csv(existing, path, RUNTIME_REVIEW_COLUMNS)
    return row


def runtime_decision_status(
    reviews: Sequence[Mapping[str, Any]],
    *,
    analysis_id: str,
    runtime_resource_id: str,
    competency_id: str,
    fragment_id: str | None = None,
) -> str:
    for review in reviews:
        if stripped_text(review.get("analysis_id")) != stripped_text(analysis_id):
            continue

        if stripped_text(review.get("runtime_resource_id")) != stripped_text(
            runtime_resource_id
        ):
            continue

        if stripped_text(review.get("competency_id")) != stripped_text(
            competency_id
        ):
            continue

        stored_fragment = stripped_text(review.get("fragment_id"))

        if fragment_id is not None and stored_fragment != stripped_text(
            fragment_id
        ):
            continue

        decision = stripped_text(review.get("decision")).upper()

        if decision in ALLOWED_RUNTIME_DECISIONS:
            return decision.casefold()

    return "pending"


def review_progress(
    reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    counts = {
        "total": len(reviews),
        "pending": 0,
        "accepted": 0,
        "rejected": 0,
        "modified": 0,
        "by_role": {
            "researcher": 0,
            "teacher": 0,
            "supervisor": 0,
            "other": 0,
        },
        "teacher_review_count": 0,
        "researcher_review_count": 0,
        "supervisor_review_count": 0,
    }

    for review in reviews:
        decision = stripped_text(review.get("decision")).upper()
        role = stripped_text(review.get("reviewer_role")).casefold()

        if decision == "ACCEPT":
            counts["accepted"] += 1
        elif decision == "REJECT":
            counts["rejected"] += 1
        elif decision == "MODIFY":
            counts["modified"] += 1
        else:
            counts["pending"] += 1

        if role in counts["by_role"]:
            counts["by_role"][role] += 1
        else:
            counts["by_role"]["other"] += 1

        if role == "teacher":
            counts["teacher_review_count"] += 1
        elif role == "supervisor":
            counts["supervisor_review_count"] += 1
        elif role == "researcher":
            counts["researcher_review_count"] += 1

    return counts
