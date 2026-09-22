"""Prepare and summarize human pedagogical evidence review."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import stripped_text, write_csv


EVIDENCE_REVIEW_COLUMNS = (
    "fragment_id",
    "resource_id",
    "competency_id",
    "competency_shortname",
    "fragment_text",
    "evidence_quote",
    "mechanically_valid",
    "evidence_start",
    "evidence_end",
    "offset_valid",
    "pedagogical_rating",
    "reviewer",
    "comment",
    "review_date",
)

ALLOWED_PEDAGOGICAL_RATINGS = {"0", "1", "2"}
LEGACY_EVIDENCE_REVIEW_COLUMNS = (
    "fragment_id",
    "resource_id",
    "competency_id",
    "competency_shortname",
    "fragment_text",
    "evidence_quote",
    "mechanically_valid",
    "pedagogical_rating",
    "reviewer",
    "comment",
)


def is_mechanically_valid(quote: str, fragment_text: str) -> bool:
    """True when quote is an exact contiguous substring of fragment_text."""

    return bool(quote) and quote in fragment_text


def evidence_offsets(quote: str, fragment_text: str) -> dict[str, str]:
    """First-occurrence character offsets. Does not change the quote.

    ``evidence_end`` is exclusive. If the quote occurs more than once,
    ``str.find`` returns the first index. Empty or non-substring quotes
    are marked ``offset_valid=false`` with blank start/end.
    """

    if not quote:
        return {
            "evidence_start": "",
            "evidence_end": "",
            "offset_valid": "false",
        }

    start = fragment_text.find(quote)

    if start < 0:
        return {
            "evidence_start": "",
            "evidence_end": "",
            "offset_valid": "false",
        }

    return {
        "evidence_start": str(start),
        "evidence_end": str(start + len(quote)),
        "offset_valid": "true",
    }


def build_evidence_review_rows(
    *,
    predictions: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """One blank pedagogical-review row per predicted evidence quote."""

    fragments_by_id = {
        stripped_text(fragment.get("fragment_id")): fragment
        for fragment in fragments
        if stripped_text(fragment.get("fragment_id"))
    }
    names = {
        stripped_text(item.get("idnumber")): stripped_text(
            item.get("shortname")
        )
        for item in competencies
        if stripped_text(item.get("idnumber"))
    }
    rows: list[dict[str, str]] = []

    for prediction in predictions:
        if prediction.get("valid") is False:
            continue

        fragment_id = stripped_text(prediction.get("fragment_id"))
        fragment = fragments_by_id.get(fragment_id, {})
        fragment_text = str(fragment.get("text") or "")
        resource_id = stripped_text(fragment.get("resource_id"))

        for selection in prediction.get("selected") or []:
            competency_id = stripped_text(selection.get("idnumber"))
            quotes = selection.get("evidence") or []

            if not quotes:
                quotes = [""]

            for quote in quotes:
                text = str(quote)
                offsets = evidence_offsets(text, fragment_text)
                rows.append(
                    {
                        "fragment_id": fragment_id,
                        "resource_id": resource_id,
                        "competency_id": competency_id,
                        "competency_shortname": names.get(
                            competency_id,
                            "",
                        ),
                        "fragment_text": fragment_text,
                        "evidence_quote": text,
                        "mechanically_valid": (
                            "true"
                            if is_mechanically_valid(
                                text,
                                fragment_text,
                            )
                            else "false"
                        ),
                        "evidence_start": offsets["evidence_start"],
                        "evidence_end": offsets["evidence_end"],
                        "offset_valid": offsets["offset_valid"],
                        "pedagogical_rating": "",
                        "reviewer": "",
                        "comment": "",
                        "review_date": "",
                    }
                )

    return rows


def pedagogical_ratings_complete(
    rows: Sequence[Mapping[str, Any]],
) -> bool:
    """True when every row has an allowed 0/1/2 rating."""

    if not rows:
        return False

    for row in rows:
        rating = stripped_text(row.get("pedagogical_rating"))

        if rating not in ALLOWED_PEDAGOGICAL_RATINGS:
            return False

    return True


def summarize_evidence_review(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize mechanical validity always; pedagogical stats only if complete."""

    total = len(rows)
    mechanical_true = sum(
        1
        for row in rows
        if stripped_text(row.get("mechanically_valid")).lower()
        == "true"
    )
    summary: dict[str, Any] = {
        "rows": total,
        "mechanically_valid": mechanical_true,
        "mechanical_validity_rate": (
            mechanical_true / total if total else 0.0
        ),
        "pedagogical_complete": pedagogical_ratings_complete(rows),
        "pedagogical_rating_counts": {},
        "pedagogical_clear_rate": None,
        "pedagogical_partial_rate": None,
        "pedagogical_unsupported_rate": None,
    }

    if not summary["pedagogical_complete"]:
        summary["status"] = "WAITING_FOR_HUMAN"
        summary["note"] = (
            "Pedagogical ratings are incomplete. Mechanical "
            "validity is reported; pedagogical percentages are "
            "not final."
        )
        return summary

    counts = Counter(
        stripped_text(row.get("pedagogical_rating"))
        for row in rows
    )
    summary["pedagogical_rating_counts"] = dict(counts)
    summary["pedagogical_unsupported_rate"] = counts.get("0", 0) / total
    summary["pedagogical_partial_rate"] = counts.get("1", 0) / total
    summary["pedagogical_clear_rate"] = counts.get("2", 0) / total
    summary["status"] = "COMPLETE"
    return summary


def migrate_evidence_review_row(
    row: Mapping[str, Any],
) -> dict[str, str]:
    """Add new audit columns without changing quotes or human ratings."""

    migrated = {
        column: str(row.get(column, "") or "")
        for column in EVIDENCE_REVIEW_COLUMNS
    }
    quote = migrated["evidence_quote"]
    fragment_text = migrated["fragment_text"]
    migrated.update(evidence_offsets(quote, fragment_text))
    migrated["mechanically_valid"] = str(
        row.get("mechanically_valid", "") or ""
    )
    migrated["pedagogical_rating"] = str(
        row.get("pedagogical_rating", "") or ""
    )
    migrated["reviewer"] = str(row.get("reviewer", "") or "")
    migrated["comment"] = str(row.get("comment", "") or "")
    migrated["review_date"] = str(row.get("review_date", "") or "")
    return migrated


def migrate_evidence_review_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    return [migrate_evidence_review_row(row) for row in rows]


def write_evidence_review(
    rows: Sequence[Mapping[str, Any]],
    output_path,
) -> None:
    write_csv(
        migrate_evidence_review_rows(rows),
        output_path,
        EVIDENCE_REVIEW_COLUMNS,
    )
