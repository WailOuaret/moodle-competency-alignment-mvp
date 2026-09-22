"""Summarize real teacher/supervisor validation. Never invent decisions."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import read_csv, stripped_text, write_csv, write_json
from moodle_competency.settings import PROJECT_ROOT
from moodle_competency.teacher_reviews import (
    ALLOWED_RUNTIME_DECISIONS,
    load_runtime_reviews,
)


WAITING_MESSAGE = "HUMAN VALIDATION NOT YET PERFORMED"
REAL_VALIDATION_ROLES = {"teacher", "supervisor"}
FORM_COLUMNS = (
    "validation_id",
    "analysis_id",
    "resource_id",
    "resource_title",
    "resource_type",
    "competency_id",
    "reviewer_name",
    "reviewer_role",
    "condition",
    "decision",
    "replacement_competency_id",
    "evidence_usefulness_rating",
    "confidence_in_decision",
    "decision_time_seconds",
    "comment",
    "date",
)
REVIEW_TABLE_COLUMNS = (
    "review_id",
    "analysis_id",
    "runtime_resource_id",
    "competency_id",
    "decision",
    "replacement_competency_id",
    "reviewer_name",
    "reviewer_role",
    "review_date",
    "backend",
    "model",
    "comment",
    "counts_as_teacher_or_supervisor_validation",
)


def _role(review: Mapping[str, Any]) -> str:
    return stripped_text(review.get("reviewer_role")).casefold()


def _decision(review: Mapping[str, Any]) -> str:
    return stripped_text(review.get("decision")).upper()


def is_completed_review(review: Mapping[str, Any]) -> bool:
    return _decision(review) in ALLOWED_RUNTIME_DECISIONS


def is_real_teacher_or_supervisor_review(
    review: Mapping[str, Any],
) -> bool:
    return _role(review) in REAL_VALIDATION_ROLES and is_completed_review(
        review
    )


def _finite_numbers(values: Sequence[Any]) -> list[float]:
    numbers: list[float] = []

    for value in values:
        text = stripped_text(value)

        if not text:
            continue

        try:
            number = float(text)
        except ValueError:
            continue

        numbers.append(number)

    return numbers


def _mean_median(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "n": 0}

    return {
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "n": len(values),
    }


def load_validation_form(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    rows = read_csv(path)
    return [
        row
        for row in rows
        if any(stripped_text(value) for key, value in row.items() if key)
    ]


def summarize_human_validation(
    reviews: Sequence[Mapping[str, Any]],
    form_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a descriptive summary. Researcher reviews are reported separately."""

    completed = [row for row in reviews if is_completed_review(row)]
    real = [
        row for row in completed if is_real_teacher_or_supervisor_review(row)
    ]
    researcher = [
        row for row in completed if _role(row) == "researcher"
    ]
    teacher = [row for row in real if _role(row) == "teacher"]
    supervisor = [row for row in real if _role(row) == "supervisor"]
    form = list(form_rows or [])
    filled_form = [
        row
        for row in form
        if stripped_text(row.get("decision"))
        or stripped_text(row.get("evidence_usefulness_rating"))
    ]

    accept = sum(1 for row in real if _decision(row) == "ACCEPT")
    reject = sum(1 for row in real if _decision(row) == "REJECT")
    modify = sum(1 for row in real if _decision(row) == "MODIFY")
    real_count = len(real)
    waiting = real_count == 0

    resources = {
        stripped_text(row.get("runtime_resource_id")) or stripped_text(
            row.get("resource_id")
        )
        for row in real
        if stripped_text(row.get("runtime_resource_id"))
        or stripped_text(row.get("resource_id"))
    }
    reviewers = {
        stripped_text(row.get("reviewer_name"))
        for row in real
        if stripped_text(row.get("reviewer_name"))
    }

    summary: dict[str, Any] = {
        "status": "WAITING_FOR_HUMAN" if waiting else "COMPLETE",
        "message": WAITING_MESSAGE if waiting else "Human validation recorded.",
        "teacher_or_supervisor_validation_performed": not waiting,
        "reviewer_count": len(reviewers),
        "reviewer_names": sorted(reviewers),
        "reviewer_roles": {
            "teacher": len(teacher),
            "supervisor": len(supervisor),
            "researcher": len(researcher),
        },
        "teacher_review_count": len(teacher),
        "supervisor_review_count": len(supervisor),
        "researcher_review_count": len(researcher),
        "resources_reviewed": len(resources),
        "suggestions_reviewed": real_count,
        "accept_count": accept,
        "reject_count": reject,
        "modify_count": modify,
        "acceptance_rate": (
            round(accept / real_count, 4) if real_count else None
        ),
        "modification_rate": (
            round(modify / real_count, 4) if real_count else None
        ),
        "rejection_rate": (
            round(reject / real_count, 4) if real_count else None
        ),
        "evidence_usefulness": _mean_median(
            _finite_numbers(
                row.get("evidence_usefulness_rating") for row in filled_form
            )
        ),
        "confidence": _mean_median(
            _finite_numbers(
                row.get("confidence_in_decision") for row in filled_form
            )
        ),
        "decision_time_seconds": _mean_median(
            _finite_numbers(
                row.get("decision_time_seconds") for row in filled_form
            )
        ),
        "with_evidence_vs_without_evidence": _condition_comparison(filled_form),
        "significance_tests": "not_run",
        "significance_tests_note": (
            "No significance tests. Sample size and design do not support "
            "inferential claims."
        ),
        "note": (
            "Researcher reviews are not teacher-study results. "
            "Only reviewer_role=teacher or reviewer_role=supervisor counts "
            "as real teacher/supervisor validation."
        ),
        "form_rows_with_answers": len(filled_form),
    }
    return summary


def _condition_comparison(
    form_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "with_evidence": [],
        "without_evidence": [],
    }

    for row in form_rows:
        condition = stripped_text(row.get("condition")).casefold()

        if condition in grouped:
            grouped[condition].append(dict(row))

    comparison: dict[str, Any] = {}

    for condition, rows in grouped.items():
        decisions = [_decision(row) for row in rows if _decision(row)]
        comparison[condition] = {
            "n": len(rows),
            "accept_count": sum(1 for item in decisions if item == "ACCEPT"),
            "reject_count": sum(1 for item in decisions if item == "REJECT"),
            "modify_count": sum(1 for item in decisions if item == "MODIFY"),
            "evidence_usefulness": _mean_median(
                _finite_numbers(
                    row.get("evidence_usefulness_rating") for row in rows
                )
            ),
            "confidence": _mean_median(
                _finite_numbers(row.get("confidence_in_decision") for row in rows)
            ),
            "decision_time_seconds": _mean_median(
                _finite_numbers(row.get("decision_time_seconds") for row in rows)
            ),
        }

    comparison["note"] = (
        "Descriptive only. A tiny within-reviewer sample is an exploratory "
        "usability exercise, not a controlled teacher study."
    )
    return comparison


def render_human_validation_report(summary: Mapping[str, Any]) -> str:
    waiting = summary.get("status") == "WAITING_FOR_HUMAN"
    lines = [
        "# Human validation summary",
        "",
        f"**Status:** {summary.get('status')}",
        "",
    ]

    if waiting:
        lines.extend(
            [
                WAITING_MESSAGE,
                "",
                "No `teacher` or `supervisor` ACCEPT/REJECT/MODIFY records "
                "were found. Researcher reviews, if any, are recorded below "
                "for provenance and are **not** teacher-study results.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The counts below use only reviews with "
                "`reviewer_role` = teacher or supervisor.",
                "",
            ]
        )

    lines.extend(
        [
            "| Item | Count |",
            "|---|---:|",
            f"| Teacher reviews | {summary.get('teacher_review_count')} |",
            f"| Supervisor reviews | {summary.get('supervisor_review_count')} |",
            f"| Researcher reviews | {summary.get('researcher_review_count')} |",
            f"| Distinct reviewers (teacher/supervisor) | {summary.get('reviewer_count')} |",
            f"| Resources reviewed (teacher/supervisor) | {summary.get('resources_reviewed')} |",
            f"| Suggestions reviewed (teacher/supervisor) | {summary.get('suggestions_reviewed')} |",
            f"| ACCEPT | {summary.get('accept_count')} |",
            f"| REJECT | {summary.get('reject_count')} |",
            f"| MODIFY | {summary.get('modify_count')} |",
            "",
            f"**Acceptance rate:** {summary.get('acceptance_rate')}",
            f"**Modification rate:** {summary.get('modification_rate')}",
            "",
            summary.get("note", ""),
            "",
            "No inferential statistical tests were run.",
            "",
        ]
    )
    return "\n".join(lines)


def write_human_validation_outputs(
    *,
    project_root: Path | None = None,
    reviews: Sequence[Mapping[str, Any]] | None = None,
    form_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Path]:
    root = Path(project_root or PROJECT_ROOT)
    review_path = root / "data" / "reviews" / "teacher_reviews.csv"
    form_path = root / "data" / "templates" / "human_validation_form.csv"
    loaded_reviews = (
        list(reviews)
        if reviews is not None
        else load_runtime_reviews(review_path)
    )
    loaded_form = (
        list(form_rows)
        if form_rows is not None
        else load_validation_form(form_path)
    )
    summary = summarize_human_validation(loaded_reviews, loaded_form)
    table_rows = [
        {
            "review_id": row.get("review_id", ""),
            "analysis_id": row.get("analysis_id", ""),
            "runtime_resource_id": row.get("runtime_resource_id", ""),
            "competency_id": row.get("competency_id", ""),
            "decision": _decision(row),
            "replacement_competency_id": row.get(
                "replacement_competency_id",
                "",
            ),
            "reviewer_name": row.get("reviewer_name", ""),
            "reviewer_role": _role(row),
            "review_date": row.get("review_date", ""),
            "backend": row.get("backend", ""),
            "model": row.get("model", ""),
            "comment": row.get("comment", ""),
            "counts_as_teacher_or_supervisor_validation": (
                "true" if is_real_teacher_or_supervisor_review(row) else "false"
            ),
        }
        for row in loaded_reviews
        if is_completed_review(row)
    ]
    metrics_path = root / "reports" / "metrics" / "human_validation_summary.json"
    table_path = root / "reports" / "tables" / "human_validation_reviews.csv"
    report_path = root / "reports" / "HUMAN_VALIDATION_SUMMARY.md"
    write_json(summary, metrics_path)
    write_csv(table_rows, table_path, REVIEW_TABLE_COLUMNS)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_human_validation_report(summary) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": metrics_path,
        "table": table_path,
        "report": report_path,
    }


def write_empty_validation_form(path: Path) -> Path:
    """Write the header-only RQ2 form. Do not invent answers."""

    return write_csv([], path, FORM_COLUMNS)
