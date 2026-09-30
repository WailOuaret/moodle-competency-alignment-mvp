"""Section N — summarize real teacher / researcher review decisions.

Two review files can exist in this project and both are read here:

``data/reviews/corpus_teacher_reviews.csv``
    Decisions on the frozen research corpus, recorded through
    ``app/pages/2_Teacher_Review.py``. This is the file Section N is about.

``data/reviews/teacher_reviews.csv``
    The separate runtime app's review log. It is counted and reported, but
    kept distinct, because it is not a decision about the research corpus.

The guiding rule is that **rates are only reported when there is something real
to compute them from**. With no decisions, every rate is ``None`` and the
status is ``WAITING_FOR_HUMAN``. Nothing is ever inferred, defaulted or
back-filled, and a researcher decision is never counted as teacher validation.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from moodle_competency.annotation import stripped_text


SUMMARY_VERSION = "1.0"

DECISIONS = ("accept", "reject", "modify", "add")
REVIEWED_DECISIONS = ("accept", "reject", "modify")
EVIDENCE_RELEVANCE_VALUES = ("0", "1", "2")

TEACHER_ROLES = frozenset({"teacher", "supervisor"})

DEMO_STATUS_FIELDS = (
    "record_status",
    "review_status",
    "research_status",
    "provenance",
    "reviewer_role",
)
DEMO_STATUS_VALUES = frozenset(
    {
        "demo",
        "test",
        "fixture",
        "test/demo",
        "demo/test",
    }
)

SUMMARY_TABLE_COLUMNS = (
    "scope",
    "metric",
    "value",
    "note",
)


def is_demo_or_test_review(review: Mapping[str, Any]) -> bool:
    """True when a row is an explicit demo or test, not a genuine decision.

    A reviewer name is never enough. The row must carry a demo/test marker in
    ``record_status``, ``review_status``, ``research_status``, ``provenance``,
    or ``reviewer_role``.
    """

    for field in DEMO_STATUS_FIELDS:
        value = stripped_text(review.get(field)).casefold()

        if value in DEMO_STATUS_VALUES:
            return True

    return False


def genuine_corpus_reviews(
    reviews: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Drop demo and test rows before any corpus-review summary is computed."""

    return [review for review in reviews if not is_demo_or_test_review(review)]


def _decision_of(review: Mapping[str, Any]) -> str:
    return stripped_text(review.get("decision")).lower()


def _key(review: Mapping[str, Any]) -> tuple[str, str]:
    return (
        stripped_text(review.get("resource_id")),
        stripped_text(review.get("competency_id")),
    )


def _rate(numerator: int, denominator: int) -> float | None:
    """A rate, or None when there is no real denominator.

    Returning None rather than 0.0 is deliberate: 0.0 would read as "nobody
    accepted anything", which is a finding. None reads as "nothing was
    reviewed", which is the truth.
    """

    return (numerator / denominator) if denominator else None


def summarize_teacher_reviews(
    reviews: Sequence[Mapping[str, Any]],
    mappings: Sequence[Mapping[str, Any]],
    *,
    runtime_reviews: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build the teacher-review summary payload.

    ``mappings`` are the predicted resource-competency alignments that were
    offered for review; they set the denominator for coverage, but never for
    acceptance, edit or rejection rates.
    """

    reviews = genuine_corpus_reviews(reviews)
    predicted_keys = {_key(mapping) for mapping in mappings}

    counts = {decision: 0 for decision in DECISIONS}
    reviewed_keys: set[str] = set()
    added_rows: list[Mapping[str, Any]] = []
    relevance_counts = {value: 0 for value in EVIDENCE_RELEVANCE_VALUES}
    relevance_blank = 0
    reviewers: dict[str, int] = {}

    per_course: dict[str, dict[str, int]] = {}
    per_type: dict[str, dict[str, int]] = {}

    mapping_by_key = {_key(mapping): mapping for mapping in mappings}

    for review in reviews:
        decision = _decision_of(review)

        if decision not in DECISIONS:
            continue

        counts[decision] += 1

        name = stripped_text(review.get("reviewer")) or "unrecorded"
        reviewers[name] = reviewers.get(name, 0) + 1

        relevance = stripped_text(review.get("evidence_relevance"))

        if relevance in relevance_counts:
            relevance_counts[relevance] += 1
        else:
            relevance_blank += 1

        key = _key(review)

        if key not in predicted_keys:
            added_rows.append(review)
            continue

        reviewed_keys.add(f"{key[0]}|{key[1]}")

        mapping = mapping_by_key.get(key, {})
        course = stripped_text(mapping.get("course_shortname")) or "unknown"
        resource_type = stripped_text(mapping.get("resource_type")) or "unknown"

        for bucket, bucket_key in ((per_course, course), (per_type, resource_type)):
            entry = bucket.setdefault(
                bucket_key,
                {decision_name: 0 for decision_name in REVIEWED_DECISIONS}
                | {"reviewed": 0},
            )
            entry["reviewed"] += 1

            if decision in entry:
                entry[decision] += 1

    reviewed = len(reviewed_keys)
    total = len(predicted_keys)

    # Denominator for rates is reviewed suggestions, not every predicted one.
    rate_denominator = sum(counts[decision] for decision in REVIEWED_DECISIONS)

    has_decisions = rate_denominator > 0 or counts["add"] > 0

    roles = _role_counts(reviews)
    runtime_roles = _role_counts(runtime_reviews, role_field="reviewer_role")

    teacher_validation = bool(
        (set(roles) | set(runtime_roles)) & TEACHER_ROLES
        and any(
            roles.get(role, 0) + runtime_roles.get(role, 0) > 0
            for role in TEACHER_ROLES
        )
    )

    return {
        "summary_version": SUMMARY_VERSION,
        "status": "COMPLETE" if has_decisions else "WAITING_FOR_HUMAN",
        "message": (
            None
            if has_decisions
            else "NO TEACHER REVIEW DECISIONS EXIST FOR THE RESEARCH CORPUS"
        ),
        "reviewable_mappings": total,
        "reviewed": reviewed,
        "pending": total - reviewed,
        "reviewed_fraction": _rate(reviewed, total),
        "accepted": counts["accept"],
        "rejected": counts["reject"],
        "modified": counts["modify"],
        "added": counts["add"],
        "rate_denominator": rate_denominator,
        "acceptance_rate": _rate(counts["accept"], rate_denominator),
        "edit_rate": _rate(counts["modify"], rate_denominator),
        "rejection_rate": _rate(counts["reject"], rate_denominator),
        "rate_note": (
            "Rates are computed over reviewed suggestions only. They are null "
            "when nothing has been reviewed, rather than 0.0, because 0.0 "
            "would read as a finding."
        ),
        "evidence_relevance_distribution": dict(relevance_counts),
        "evidence_relevance_unanswered": relevance_blank,
        "per_course": {name: per_course[name] for name in sorted(per_course)},
        "per_resource_type": {name: per_type[name] for name in sorted(per_type)},
        "reviewers": {name: reviewers[name] for name in sorted(reviewers)},
        "reviewer_roles": roles,
        "teacher_or_supervisor_validation_performed": teacher_validation,
        "runtime_review_count": len(list(runtime_reviews)),
        "runtime_reviewer_roles": runtime_roles,
        "runtime_note": (
            "Runtime reviews come from the separate runtime analysis app and "
            "are not decisions about the frozen research corpus. They are "
            "reported here only so no real human decision goes unrecorded."
        ),
        "provenance_note": (
            "A researcher decision is never reported as teacher validation. "
            "Only reviewer roles teacher or supervisor count as such."
        ),
        "significance_tests": "not_run",
        "significance_tests_note": (
            "No significance tests. Sample size and design do not support "
            "inferential claims."
        ),
    }


def _role_counts(
    reviews: Sequence[Mapping[str, Any]],
    *,
    role_field: str = "reviewer_role",
) -> dict[str, int]:
    """Count reviewer roles, tolerating a file that records no role."""

    counts: dict[str, int] = {}

    for review in reviews:
        role = stripped_text(review.get(role_field)).lower()

        if not role:
            continue

        counts[role] = counts.get(role, 0) + 1

    return {key: counts[key] for key in sorted(counts)}


def summary_table_rows(summary: Mapping[str, Any]) -> list[dict[str, str]]:
    """Flatten the summary into reportable CSV rows.

    A null rate is written as an empty cell with an explicit note, never as 0.
    """

    def value(raw: Any) -> str:
        if raw is None:
            return ""

        if isinstance(raw, float):
            return f"{raw:.10f}"

        return str(raw)

    waiting_note = (
        "" if summary.get("status") == "COMPLETE" else "no real decisions exist"
    )

    rows: list[dict[str, str]] = [
        {
            "scope": "overall",
            "metric": "status",
            "value": value(summary.get("status")),
            "note": value(summary.get("message")),
        },
        {
            "scope": "overall",
            "metric": "reviewable_mappings",
            "value": value(summary.get("reviewable_mappings")),
            "note": "predicted resource-competency alignments offered for review",
        },
    ]

    for metric in ("reviewed", "pending", "accepted", "rejected", "modified", "added"):
        rows.append(
            {
                "scope": "overall",
                "metric": metric,
                "value": value(summary.get(metric)),
                "note": "",
            }
        )

    for metric in ("acceptance_rate", "edit_rate", "rejection_rate"):
        rows.append(
            {
                "scope": "overall",
                "metric": metric,
                "value": value(summary.get(metric)),
                "note": waiting_note or "denominator = reviewed suggestions",
            }
        )

    for rating, count in (summary.get("evidence_relevance_distribution") or {}).items():
        rows.append(
            {
                "scope": "evidence_relevance",
                "metric": f"rating_{rating}",
                "value": value(count),
                "note": "teacher judgement of the evidence quote",
            }
        )

    rows.append(
        {
            "scope": "evidence_relevance",
            "metric": "unanswered",
            "value": value(summary.get("evidence_relevance_unanswered")),
            "note": "reviews that left the evidence question blank",
        }
    )

    for course, entry in (summary.get("per_course") or {}).items():
        for metric, count in entry.items():
            rows.append(
                {
                    "scope": f"course:{course}",
                    "metric": metric,
                    "value": value(count),
                    "note": "",
                }
            )

    for resource_type, entry in (summary.get("per_resource_type") or {}).items():
        for metric, count in entry.items():
            rows.append(
                {
                    "scope": f"resource_type:{resource_type}",
                    "metric": metric,
                    "value": value(count),
                    "note": "",
                }
            )

    for role, count in (summary.get("reviewer_roles") or {}).items():
        rows.append(
            {
                "scope": "reviewer_role",
                "metric": role,
                "value": value(count),
                "note": (
                    "counts as teacher validation"
                    if role in TEACHER_ROLES
                    else "does NOT count as teacher validation"
                ),
            }
        )

    rows.append(
        {
            "scope": "runtime",
            "metric": "runtime_review_count",
            "value": value(summary.get("runtime_review_count")),
            "note": value(summary.get("runtime_note")),
        }
    )

    return rows
