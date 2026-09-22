"""Helpers for the teacher-facing Streamlit interface.

These functions are unit-tested without launching Streamlit or calling
live models. They never display API keys or Moodle tokens.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import stripped_text
from moodle_competency.resource_ingestion import (
    list_moodle_courses,
    list_moodle_resources_for_course,
    load_moodle_resource_catalogue,
)
from moodle_competency.runtime_analysis import (
    available_runtime_backends,
    catalogue_ids,
    load_competencies,
)
from moodle_competency.runtime_storage import (
    RuntimePaths,
    load_all_analyses,
    runtime_paths,
)
from moodle_competency.settings import PROJECT_ROOT
from moodle_competency.teacher_reviews import (
    load_runtime_reviews,
    review_kind_label,
    review_progress,
    runtime_decision_status,
)


PAGE_TITLES = (
    "Analyze Resource",
    "Review Suggestions",
    "Competency → Resources",
    "Review History / Progress",
    "Research Results",
)

ANALYZE_EXPLANATION = (
    "Select an existing Moodle resource or upload/paste a learning "
    "resource. The system suggests relevant competencies and shows the "
    "textual evidence supporting each suggestion."
)


def highlight_quote(fragment_text: str, quote: str) -> str:
    """Return HTML with the exact quote marked. Input is escaped first."""

    text = str(fragment_text or "")
    needle = str(quote or "")
    escaped = html.escape(text)

    if not needle or needle not in text:
        return escaped

    start = text.find(needle)
    end = start + len(needle)
    return (
        html.escape(text[:start])
        + "<mark>"
        + html.escape(needle)
        + "</mark>"
        + html.escape(text[end:])
    )


def format_bm25_ranks(ranks: Sequence[int]) -> str:
    if not ranks:
        return "n/a"

    return ", ".join(f"#{rank}" for rank in ranks)


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def round4(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def load_research_results(
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Read frozen metric files. Does not recalculate them."""

    root = Path(project_root or PROJECT_ROOT)
    metrics = root / "reports" / "metrics"
    fragment = load_json_if_exists(metrics / "constrained_llm_metrics.json")
    resource = load_json_if_exists(metrics / "resource_level_metrics.json")
    evidence = load_json_if_exists(metrics / "evidence_review_summary.json")
    hierarchy_fragment = load_json_if_exists(
        metrics / "graph_child_preference_fragment_metrics.json"
    )
    hierarchy_resource = load_json_if_exists(
        metrics / "graph_child_preference_resource_metrics.json"
    )

    return {
        "fragment_original": {
            "precision": round4(fragment.get("micro_precision")),
            "recall": round4(fragment.get("micro_recall")),
            "f1": round4(fragment.get("micro_f1")),
        },
        "resource_original": {
            "precision": round4(resource.get("micro_precision")),
            "recall": round4(resource.get("micro_recall")),
            "f1": round4(resource.get("micro_f1")),
        },
        "evidence": {
            "mechanically_exact": evidence.get("mechanically_valid"),
            "total": evidence.get("rows")
            or evidence.get("total_rows")
            or evidence.get("row_count"),
            "clear_rate": round4(evidence.get("pedagogical_clear_rate")),
            "partial_rate": round4(evidence.get("pedagogical_partial_rate")),
            "unsupported_rate": round4(
                evidence.get("pedagogical_unsupported_rate")
            ),
            "rating_counts": evidence.get("pedagogical_rating_counts") or {},
        },
        "hierarchy_ablation": {
            "label": "POST-HOC ABLATION",
            "fragment_f1_original": round4(fragment.get("micro_f1")),
            "fragment_f1_reconciled": round4(
                hierarchy_fragment.get("micro_f1")
            ),
            "resource_f1_original": round4(resource.get("micro_f1")),
            "resource_f1_reconciled": round4(
                hierarchy_resource.get("micro_f1")
            ),
            "note": (
                "Hierarchy metrics are a post-hoc ablation. "
                "They are not the original Gemini metrics."
            ),
        },
    }


def configured_backend_choices(
    *,
    include_ollama_probe: bool = False,
    ollama_probe=None,
) -> list[dict[str, Any]]:
    """Return backends that can be shown in the UI.

    Tests pass include_ollama_probe=False so Ollama is never contacted.
    """

    return available_runtime_backends(
        ollama_probe=ollama_probe,
        include_ollama_probe=include_ollama_probe,
    )


def moodle_course_options(
    resources: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    return [
        str(item["course_shortname"])
        for item in list_moodle_courses(resources)
    ]


def moodle_resource_options(
    course_shortname: str,
    resources: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, str]]:
    return [
        {
            "resource_id": str(item.get("resource_id", "")),
            "title": str(item.get("title") or item.get("resource_id")),
            "resource_type": str(item.get("resource_type", "")),
        }
        for item in list_moodle_resources_for_course(
            course_shortname,
            resources,
        )
    ]


def suggestion_status(
    card: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    *,
    analysis_id: str,
) -> str:
    return runtime_decision_status(
        reviews,
        analysis_id=analysis_id,
        runtime_resource_id=str(card.get("runtime_resource_id", "")),
        competency_id=str(card.get("competency_id", "")),
    )


def filter_suggestion_rows(
    analyses: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    *,
    course: str | None = None,
    resource_id: str | None = None,
    status: str | None = None,
    competency_id: str | None = None,
    backend: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    wanted_course = stripped_text(course)
    wanted_resource = stripped_text(resource_id)
    wanted_status = stripped_text(status).casefold()
    wanted_competency = stripped_text(competency_id)
    wanted_backend = stripped_text(backend).casefold()

    for analysis in analyses:
        if wanted_backend and stripped_text(
            analysis.get("backend")
        ).casefold() != wanted_backend:
            continue

        analysis_id = str(analysis.get("analysis_id", ""))

        for card in analysis.get("suggestion_cards") or []:
            if wanted_course and stripped_text(
                card.get("course_shortname")
            ) != wanted_course:
                continue

            if wanted_resource and stripped_text(
                card.get("runtime_resource_id")
            ) != wanted_resource:
                continue

            if wanted_competency and stripped_text(
                card.get("competency_id")
            ) != wanted_competency:
                continue

            decision = suggestion_status(
                card,
                reviews,
                analysis_id=analysis_id,
            )

            if wanted_status and wanted_status != "all":
                expected = (
                    "pending"
                    if wanted_status == "pending"
                    else wanted_status
                )

                if expected == "accepted":
                    expected = "accept"
                elif expected == "rejected":
                    expected = "reject"
                elif expected == "modified":
                    expected = "modify"

                if decision != expected:
                    continue

            row = dict(card)
            row["analysis_id"] = analysis_id
            row["backend"] = analysis.get("backend")
            row["model"] = analysis.get("model")
            row["review_status"] = decision
            rows.append(row)

    return rows


def competency_resource_index(
    analyses: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    *,
    competency_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Split model suggestions from human-validated mappings."""

    wanted = stripped_text(competency_id)
    suggestions: list[dict[str, Any]] = []
    validated: list[dict[str, Any]] = []

    for analysis in analyses:
        analysis_id = str(analysis.get("analysis_id", ""))

        for card in analysis.get("suggestion_cards") or []:
            if stripped_text(card.get("competency_id")) != wanted:
                continue

            status = suggestion_status(
                card,
                reviews,
                analysis_id=analysis_id,
            )
            backend = analysis.get("backend")
            model = analysis.get("model")
            row = {
                "analysis_id": analysis_id,
                "runtime_resource_id": card.get("runtime_resource_id"),
                "title": card.get("title"),
                "course_shortname": card.get("course_shortname"),
                "support_count": card.get("support_count"),
                "evidence_quotes": card.get("evidence_quotes") or [],
                "suggested_confidence": card.get("suggested_confidence"),
                "review_status": status,
                "backend": backend,
                "model": model,
                "backend_label": format_backend_model(backend, model),
            }
            suggestions.append(row)

            if status in {"accept", "modify"}:
                review = latest_matching_review(
                    reviews,
                    analysis_id=analysis_id,
                    runtime_resource_id=str(
                        card.get("runtime_resource_id") or ""
                    ),
                    competency_id=wanted,
                )
                validated_row = dict(row)

                if review is not None:
                    review_backend = review.get("backend") or backend
                    review_model = review.get("model") or model
                    validated_row.update(
                        {
                            "decision": stripped_text(
                                review.get("decision")
                            ).upper(),
                            "reviewer_name": review.get("reviewer_name"),
                            "reviewer_role": review.get("reviewer_role"),
                            "review_kind": review_kind_label(
                                str(review.get("reviewer_role") or "")
                            ),
                            "backend": review_backend,
                            "model": review_model,
                            "backend_label": format_backend_model(
                                review_backend,
                                review_model,
                            ),
                        }
                    )
                else:
                    validated_row["decision"] = status.upper()
                    validated_row["reviewer_name"] = ""
                    validated_row["reviewer_role"] = ""
                    validated_row["review_kind"] = ""

                validated.append(validated_row)

    return {
        "model_suggestions": suggestions,
        "human_validated": validated,
    }


def history_summary(
    analyses: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    resource_ids = {
        str(item.get("runtime_resource_id", ""))
        for item in analyses
        if item.get("runtime_resource_id")
    }
    suggestion_count = sum(
        len(item.get("suggestion_cards") or [])
        for item in analyses
    )
    progress = review_progress(reviews)
    pending = max(suggestion_count - progress["total"], 0)
    return {
        "analyses_run": len(analyses),
        "resources_analyzed": len(resource_ids),
        "suggestions_generated": suggestion_count,
        "pending": pending,
        "accepted": progress["accepted"],
        "rejected": progress["rejected"],
        "modified": progress["modified"],
        "reviewer_breakdown": progress["by_role"],
        "teacher_review_count": progress["teacher_review_count"],
        "researcher_review_count": progress["researcher_review_count"],
        "supervisor_review_count": progress["supervisor_review_count"],
        "note": (
            "Researcher and supervisor reviews are not teacher-study results."
        ),
    }


def load_ui_state(
    paths: RuntimePaths | None = None,
) -> dict[str, Any]:
    resolved = paths or runtime_paths()
    analyses = load_all_analyses(resolved)
    reviews = load_runtime_reviews(resolved.reviews)
    competencies = load_competencies()
    catalogue = []

    try:
        catalogue = load_moodle_resource_catalogue()
    except Exception:
        catalogue = []

    return {
        "analyses": analyses,
        "reviews": reviews,
        "competencies": competencies,
        "catalogue_ids": catalogue_ids(competencies),
        "moodle_resources": catalogue,
        "paths": resolved,
    }


def review_label_for_role(role: str) -> str:
    return review_kind_label(role)


def format_backend_model(
    backend: str | None,
    model: str | None = None,
) -> str:
    """Human-readable backend/model label, e.g. Gemini — gemini-3.5-flash."""

    raw = stripped_text(backend).casefold()
    pretty = {
        "gemini": "Gemini",
        "ollama": "Ollama",
        "mock": "Mock",
    }.get(raw, stripped_text(backend) or "Unknown backend")
    model_name = stripped_text(model)

    if model_name:
        return f"{pretty} — {model_name}"

    return pretty


def latest_matching_review(
    reviews: Sequence[Mapping[str, Any]],
    *,
    analysis_id: str,
    runtime_resource_id: str,
    competency_id: str,
) -> dict[str, Any] | None:
    matched: list[dict[str, Any]] = []

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

        matched.append(dict(review))

    if not matched:
        return None

    return matched[-1]


def review_history_table_rows(
    reviews: Sequence[Mapping[str, Any]],
    analyses: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, str]]:
    titles: dict[str, str] = {}

    for analysis in analyses or []:
        analysis_id = stripped_text(analysis.get("analysis_id"))

        if not analysis_id:
            continue

        titles[analysis_id] = stripped_text(
            analysis.get("title")
        ) or stripped_text(analysis.get("runtime_resource_id"))

    rows: list[dict[str, str]] = []

    for review in reviews:
        analysis_id = stripped_text(review.get("analysis_id"))
        resource_id = stripped_text(review.get("runtime_resource_id"))
        rows.append(
            {
                "analysis ID": analysis_id,
                "resource": titles.get(analysis_id) or resource_id,
                "competency": stripped_text(review.get("competency_id")),
                "decision": stripped_text(review.get("decision")).upper(),
                "reviewer": stripped_text(review.get("reviewer_name")),
                "role": stripped_text(review.get("reviewer_role")),
                "backend": stripped_text(review.get("backend")),
                "model": stripped_text(review.get("model")),
                "date": stripped_text(review.get("review_date")),
            }
        )

    return rows
