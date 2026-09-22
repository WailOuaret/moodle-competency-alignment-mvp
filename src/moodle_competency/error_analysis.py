"""Classify alignment errors from gold, BM25, constrained LLM and evidence review.

Prediction-correctness flags and evidence-quality flags are separate.
They may overlap. Do not invent gold, ratings, or teacher decisions.

Join key for evidence review: fragment_id + competency_id.
Do not join only by evidence quote text.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import stripped_text
from moodle_competency.evidence_review import (
    ALLOWED_PEDAGOGICAL_RATINGS,
    pedagogical_ratings_complete,
)


PREDICTION_CATEGORIES = (
    "retrieval_failure",
    "incorrect_abstention",
    "llm_missed_gold_label",
    "llm_wrong_selection",
    "overprediction",
    "underprediction",
    "parent_child_redundancy",
    "ambiguous_gold",
    "correct_prediction",
    "correct_abstention",
)

EVIDENCE_QUALITY_FLAGS = (
    "evidence_clear",
    "evidence_partial",
    "evidence_unsupported",
    "exact_but_weak_evidence",
)

ERROR_CATEGORIES = PREDICTION_CATEGORIES + EVIDENCE_QUALITY_FLAGS

PRIMARY_CATEGORY_PRIORITY = (
    "retrieval_failure",
    "incorrect_abstention",
    "llm_missed_gold_label",
    "llm_wrong_selection",
    "overprediction",
    "underprediction",
    "parent_child_redundancy",
    "ambiguous_gold",
    "correct_prediction",
    "correct_abstention",
)

PRIMARY_CATEGORY_NOTE = (
    "Primary category counts partition fragments for presentation; "
    "flag counts may overlap."
)

ERROR_TABLE_COLUMNS = (
    "fragment_id",
    "resource_id",
    "resource_type",
    "course_shortname",
    "gold_competency_ids",
    "predicted_competency_ids",
    "bm25_top5_ids",
    "retrieval_failure",
    "llm_wrong_selection",
    "llm_missed_gold_label",
    "overprediction",
    "underprediction",
    "incorrect_abstention",
    "correct_abstention",
    "parent_child_redundancy",
    "ambiguous_gold",
    "correct_prediction",
    "evidence_clear",
    "evidence_partial",
    "evidence_unsupported",
    "exact_but_weak_evidence",
    "primary_error_category",
    "categories",
    "evidence_quote_count",
    "evidence_rating_2_count",
    "evidence_rating_1_count",
    "evidence_rating_0_count",
    "evidence_rating_min",
    "evidence_rating_max",
    "evidence_rating_mean",
    "mechanically_valid_count",
    "mechanically_invalid_count",
    "pedagogical_evidence_available",
)

EXAMPLE_COLUMNS = (
    "example_type",
    "fragment_id",
    "resource_id",
    "resource_type",
    "fragment_text",
    "reference_competencies",
    "bm25_top5",
    "predicted_competencies",
    "evidence_quotes",
    "evidence_ratings",
    "primary_error_category",
    "all_error_flags",
    "short_factual_explanation",
)


def _set(values: Iterable[str] | None) -> set[str]:
    return {
        str(value).strip()
        for value in (values or [])
        if str(value).strip()
    }


def _copy_row(row: Mapping[str, Any]) -> dict[str, str]:
    return {str(key): str(row.get(key, "") or "") for key in row}


def parent_of(competency_id: str) -> str | None:
    """Return parent idnumber for GI child IDs such as GI_C1_2 -> GI_C1."""

    parts = competency_id.split("_")

    if len(parts) >= 3:
        return "_".join(parts[:2])

    return None


def group_evidence_reviews(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], list[dict[str, str]]]:
    """Group evidence rows by (fragment_id, competency_id). Copies only."""

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        copied = _copy_row(row)
        fragment_id = stripped_text(copied.get("fragment_id"))
        competency_id = stripped_text(copied.get("competency_id"))

        if not fragment_id or not competency_id:
            continue

        grouped[(fragment_id, competency_id)].append(copied)

    return dict(grouped)


def evidence_by_competency_for_fragment(
    grouped: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    fragment_id: str,
) -> dict[str, list[dict[str, str]]]:
    """Return reviews for one fragment, keyed by competency_id."""

    by_competency: dict[str, list[dict[str, str]]] = defaultdict(list)

    for (row_fragment, competency_id), reviews in grouped.items():
        if row_fragment != fragment_id:
            continue

        by_competency[competency_id].extend(
            _copy_row(review) for review in reviews
        )

    return dict(by_competency)


def aggregate_evidence_reviews(
    reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count quotes and ratings. Blank ratings are not treated as 0 or 2."""

    quote_count = 0
    rating_counts = {0: 0, 1: 0, 2: 0}
    rated_values: list[int] = []
    mechanically_valid = 0
    mechanically_invalid = 0

    for review in reviews:
        quote_count += 1
        mechanical = stripped_text(review.get("mechanically_valid")).lower()

        if mechanical == "true":
            mechanically_valid += 1
        else:
            mechanically_invalid += 1

        rating_text = stripped_text(review.get("pedagogical_rating"))

        if rating_text in ALLOWED_PEDAGOGICAL_RATINGS:
            rating = int(rating_text)
            rating_counts[rating] += 1
            rated_values.append(rating)

    return {
        "evidence_quote_count": quote_count,
        "evidence_rating_2_count": rating_counts[2],
        "evidence_rating_1_count": rating_counts[1],
        "evidence_rating_0_count": rating_counts[0],
        "evidence_rating_min": min(rated_values) if rated_values else None,
        "evidence_rating_max": max(rated_values) if rated_values else None,
        "evidence_rating_mean": (
            sum(rated_values) / len(rated_values) if rated_values else None
        ),
        "mechanically_valid_count": mechanically_valid,
        "mechanically_invalid_count": mechanically_invalid,
        "rated_count": len(rated_values),
    }


def pair_evidence_quality_flags(
    reviews: Sequence[Mapping[str, Any]],
    *,
    pedagogical_complete: bool,
) -> dict[str, bool]:
    """Flags for one fragment_id + competency_id pair."""

    flags = {name: False for name in EVIDENCE_QUALITY_FLAGS}

    if not pedagogical_complete or not reviews:
        return flags

    ratings: list[int] = []
    exact_but_weak = False

    for review in reviews:
        rating_text = stripped_text(review.get("pedagogical_rating"))
        mechanical = stripped_text(review.get("mechanically_valid")).lower()

        if rating_text not in ALLOWED_PEDAGOGICAL_RATINGS:
            continue

        rating = int(rating_text)
        ratings.append(rating)

        if mechanical == "true" and rating < 2:
            exact_but_weak = True

    if not ratings:
        return flags

    if any(rating == 0 for rating in ratings):
        flags["evidence_unsupported"] = True
    elif any(rating == 1 for rating in ratings):
        flags["evidence_partial"] = True
    elif all(rating == 2 for rating in ratings):
        flags["evidence_clear"] = True

    flags["exact_but_weak_evidence"] = exact_but_weak
    return flags


def fragment_evidence_quality_flags(
    predicted_ids: Iterable[str],
    evidence_by_competency: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    *,
    pedagogical_complete: bool,
) -> tuple[dict[str, bool], dict[str, Any]]:
    """OR pair flags across predicted competencies; sum quote stats."""

    flags = {name: False for name in EVIDENCE_QUALITY_FLAGS}
    empty_stats = aggregate_evidence_reviews([])

    if not pedagogical_complete or not evidence_by_competency:
        return flags, empty_stats

    predicted = _set(predicted_ids)
    combined_reviews: list[Mapping[str, Any]] = []

    for competency_id in predicted:
        reviews = evidence_by_competency.get(competency_id) or []
        combined_reviews.extend(reviews)
        pair_flags = pair_evidence_quality_flags(
            reviews,
            pedagogical_complete=True,
        )

        for name, value in pair_flags.items():
            if value:
                flags[name] = True

    if flags["evidence_unsupported"]:
        flags["evidence_clear"] = False

    if flags["evidence_unsupported"] or flags["evidence_partial"]:
        flags["evidence_clear"] = False

    return flags, aggregate_evidence_reviews(combined_reviews)


def unique_preserve(values: Sequence[str]) -> list[str]:
    unique: list[str] = []

    for value in values:
        if value not in unique:
            unique.append(value)

    return unique


def primary_error_category(flags: Sequence[str]) -> str:
    """Deterministic presentation category. Flag overlap is preserved."""

    flag_set = set(flags)

    for category in PRIMARY_CATEGORY_PRIORITY:
        if category in flag_set:
            return category

    return "unclassified"


def classify_fragment(
    *,
    fragment_id: str,
    gold_ids: Iterable[str],
    no_competency: bool,
    ambiguous_gold: bool,
    ranked_candidates: Sequence[str],
    predicted_ids: Iterable[str],
    abstain: bool,
    evidence_by_competency: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    pedagogical_complete: bool = False,
) -> dict[str, Any]:
    """Assign overlapping prediction flags plus optional evidence flags."""

    gold = _set(gold_ids)
    predicted = _set(predicted_ids)
    top5 = list(ranked_candidates[:5])
    top5_set = set(top5)
    flags: list[str] = []

    if no_competency or not gold:
        if not predicted and abstain:
            flags.append("correct_abstention")
        elif predicted:
            flags.append("overprediction")
            if abstain:
                flags.append("incorrect_abstention")
        else:
            flags.append("incorrect_abstention")
    else:
        missing_from_retrieval = sorted(gold - top5_set)
        present_in_retrieval = gold & top5_set
        missed_by_llm = sorted(present_in_retrieval - predicted)
        extra = predicted - gold

        if missing_from_retrieval:
            flags.append("retrieval_failure")

        if missed_by_llm:
            flags.append("llm_missed_gold_label")

        if extra:
            flags.append("llm_wrong_selection")
            flags.append("overprediction")

        if gold - predicted:
            flags.append("underprediction")

        if abstain and gold:
            flags.append("incorrect_abstention")

        if predicted == gold:
            flags.append("correct_prediction")

    if predicted:
        for competency_id in predicted:
            parent = parent_of(competency_id)

            if parent and parent in predicted:
                flags.append("parent_child_redundancy")
                break

    if ambiguous_gold:
        flags.append("ambiguous_gold")

    evidence_flags, evidence_stats = fragment_evidence_quality_flags(
        predicted,
        evidence_by_competency,
        pedagogical_complete=pedagogical_complete,
    )

    for name, value in evidence_flags.items():
        if value:
            flags.append(name)

    unique_flags = unique_preserve(flags)
    return {
        "fragment_id": fragment_id,
        "gold_competency_ids": sorted(gold),
        "predicted_competency_ids": sorted(predicted),
        "bm25_top5": top5,
        "categories": unique_flags,
        "primary_category": primary_error_category(unique_flags),
        "primary_error_category": primary_error_category(unique_flags),
        "pedagogical_evidence_available": pedagogical_complete,
        "evidence_stats": evidence_stats,
        "evidence_flags": evidence_flags,
    }


def flag_as_csv(flags: Sequence[str], name: str) -> str:
    return "true" if name in flags else "false"


def format_optional_number(value: Any, *, digits: int | None = None) -> str:
    if value is None:
        return ""

    if digits is None:
        return str(value)

    return f"{float(value):.{digits}f}"


def build_error_table_row(
    classified: Mapping[str, Any],
    *,
    resource_id: str = "",
    resource_type: str = "",
    course_shortname: str = "",
) -> dict[str, str]:
    flags = list(classified.get("categories") or [])
    stats = classified.get("evidence_stats") or aggregate_evidence_reviews([])
    return {
        "fragment_id": stripped_text(classified.get("fragment_id")),
        "resource_id": resource_id,
        "resource_type": resource_type,
        "course_shortname": course_shortname,
        "gold_competency_ids": ";".join(
            classified.get("gold_competency_ids") or []
        ),
        "predicted_competency_ids": ";".join(
            classified.get("predicted_competency_ids") or []
        ),
        "bm25_top5_ids": ";".join(classified.get("bm25_top5") or []),
        "retrieval_failure": flag_as_csv(flags, "retrieval_failure"),
        "llm_wrong_selection": flag_as_csv(flags, "llm_wrong_selection"),
        "llm_missed_gold_label": flag_as_csv(flags, "llm_missed_gold_label"),
        "overprediction": flag_as_csv(flags, "overprediction"),
        "underprediction": flag_as_csv(flags, "underprediction"),
        "incorrect_abstention": flag_as_csv(flags, "incorrect_abstention"),
        "correct_abstention": flag_as_csv(flags, "correct_abstention"),
        "parent_child_redundancy": flag_as_csv(
            flags, "parent_child_redundancy"
        ),
        "ambiguous_gold": flag_as_csv(flags, "ambiguous_gold"),
        "correct_prediction": flag_as_csv(flags, "correct_prediction"),
        "evidence_clear": flag_as_csv(flags, "evidence_clear"),
        "evidence_partial": flag_as_csv(flags, "evidence_partial"),
        "evidence_unsupported": flag_as_csv(flags, "evidence_unsupported"),
        "exact_but_weak_evidence": flag_as_csv(
            flags, "exact_but_weak_evidence"
        ),
        "primary_error_category": stripped_text(
            classified.get("primary_error_category")
        ),
        "categories": ";".join(flags),
        "evidence_quote_count": str(stats.get("evidence_quote_count") or 0),
        "evidence_rating_2_count": str(
            stats.get("evidence_rating_2_count") or 0
        ),
        "evidence_rating_1_count": str(
            stats.get("evidence_rating_1_count") or 0
        ),
        "evidence_rating_0_count": str(
            stats.get("evidence_rating_0_count") or 0
        ),
        "evidence_rating_min": format_optional_number(
            stats.get("evidence_rating_min")
        ),
        "evidence_rating_max": format_optional_number(
            stats.get("evidence_rating_max")
        ),
        "evidence_rating_mean": format_optional_number(
            stats.get("evidence_rating_mean"),
            digits=4,
        ),
        "mechanically_valid_count": str(
            stats.get("mechanically_valid_count") or 0
        ),
        "mechanically_invalid_count": str(
            stats.get("mechanically_invalid_count") or 0
        ),
        "pedagogical_evidence_available": (
            "true"
            if classified.get("pedagogical_evidence_available")
            else "false"
        ),
    }


def summarize_error_rows(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count overlapping flags. Does not create fake examples."""

    counts = {category: 0 for category in ERROR_CATEGORIES}
    primary_counts = {category: 0 for category in PRIMARY_CATEGORY_PRIORITY}
    primary_counts["unclassified"] = 0

    for row in rows:
        categories = row.get("categories") or []

        if isinstance(categories, str):
            categories = [
                item for item in categories.split(";") if item
            ]

        for category in categories:
            if category in counts:
                counts[category] += 1

        primary = stripped_text(
            row.get("primary_error_category") or row.get("primary_category")
        ) or primary_error_category(list(categories))

        if primary not in primary_counts:
            primary_counts[primary] = 0

        primary_counts[primary] += 1

    return {
        "fragments": len(rows),
        "category_counts": counts,
        "overlapping_flag_counts": counts,
        "primary_category_counts": primary_counts,
        "primary_category_note": PRIMARY_CATEGORY_NOTE,
    }


def summarize_evidence_quality(
    *,
    evidence_rows: Sequence[Mapping[str, Any]],
    analysis_rows: Sequence[Mapping[str, Any]],
    grouped: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    pedagogical_complete: bool,
) -> dict[str, Any]:
    """Quote-level and prediction-pair evidence quality. Not 83 predictions."""

    ratings = [
        stripped_text(row.get("pedagogical_rating"))
        for row in evidence_rows
    ]
    clear_quotes = sum(1 for rating in ratings if rating == "2")
    partial_quotes = sum(1 for rating in ratings if rating == "1")
    unsupported_quotes = sum(1 for rating in ratings if rating == "0")
    total = len(evidence_rows)
    pair_clear = pair_partial = pair_unsupported = 0

    if pedagogical_complete:
        for reviews in grouped.values():
            flags = pair_evidence_quality_flags(
                reviews,
                pedagogical_complete=True,
            )

            if flags["evidence_unsupported"]:
                pair_unsupported += 1
            elif flags["evidence_partial"]:
                pair_partial += 1
            elif flags["evidence_clear"]:
                pair_clear += 1

    weak_fragments = sum(
        1
        for row in analysis_rows
        if (
            "exact_but_weak_evidence"
            in (
                row.get("categories")
                if not isinstance(row.get("categories"), str)
                else row.get("categories", "").split(";")
            )
        )
        or stripped_text(row.get("exact_but_weak_evidence")).lower()
        == "true"
    )

    return {
        "status": "COMPLETE" if pedagogical_complete else "WAITING_FOR_HUMAN",
        "evidence_rows": total,
        "clear_quote_count": clear_quotes,
        "partial_quote_count": partial_quotes,
        "unsupported_quote_count": unsupported_quotes,
        "clear_rate": clear_quotes / total if total else 0.0,
        "partial_rate": partial_quotes / total if total else 0.0,
        "unsupported_rate": unsupported_quotes / total if total else 0.0,
        "prediction_pairs_with_clear_evidence": pair_clear,
        "prediction_pairs_with_partial_evidence": pair_partial,
        "prediction_pairs_with_unsupported_evidence": pair_unsupported,
        "fragments_with_weak_evidence": weak_fragments,
        "note": (
            "evidence_rows are quotes, not predictions. "
            "Mechanical exactness is not pedagogical relevance."
        ),
    }


def _has_flag(row: Mapping[str, Any], name: str) -> bool:
    categories = row.get("categories") or []

    if isinstance(categories, str):
        categories = [item for item in categories.split(";") if item]

    if name in categories:
        return True

    return stripped_text(row.get(name)).lower() == "true"


def _example_row(
    *,
    example_type: str,
    analysis_row: Mapping[str, Any],
    fragment_text: str,
    evidence_quotes: Sequence[str],
    evidence_ratings: Sequence[str],
    explanation: str,
) -> dict[str, str]:
    return {
        "example_type": example_type,
        "fragment_id": stripped_text(analysis_row.get("fragment_id")),
        "resource_id": stripped_text(analysis_row.get("resource_id")),
        "resource_type": stripped_text(analysis_row.get("resource_type")),
        "fragment_text": fragment_text,
        "reference_competencies": stripped_text(
            analysis_row.get("gold_competency_ids")
        ),
        "bm25_top5": stripped_text(analysis_row.get("bm25_top5_ids")),
        "predicted_competencies": stripped_text(
            analysis_row.get("predicted_competency_ids")
        ),
        "evidence_quotes": " || ".join(evidence_quotes),
        "evidence_ratings": ";".join(evidence_ratings),
        "primary_error_category": stripped_text(
            analysis_row.get("primary_error_category")
        ),
        "all_error_flags": stripped_text(analysis_row.get("categories")),
        "short_factual_explanation": explanation,
    }


def build_error_examples(
    analysis_rows: Sequence[Mapping[str, Any]],
    *,
    fragments_by_id: Mapping[str, Mapping[str, Any]],
    grouped_reviews: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
) -> list[dict[str, str]]:
    """Select real classified rows. Does not invent fragment IDs."""

    by_id = {
        stripped_text(row.get("fragment_id")): row for row in analysis_rows
    }
    examples: list[dict[str, str]] = []
    used: set[tuple[str, str]] = set()

    def quotes_for(fragment_id: str) -> tuple[list[str], list[str]]:
        quotes: list[str] = []
        ratings: list[str] = []

        for (row_fragment, _competency), reviews in grouped_reviews.items():
            if row_fragment != fragment_id:
                continue

            for review in reviews:
                quotes.append(str(review.get("evidence_quote") or ""))
                ratings.append(
                    stripped_text(review.get("pedagogical_rating"))
                )

        return quotes, ratings

    def add(
        example_type: str,
        fragment_id: str,
        explanation: str,
    ) -> None:
        row = by_id.get(fragment_id)

        if row is None or (example_type, fragment_id) in used:
            return

        fragment = fragments_by_id.get(fragment_id) or {}
        quotes, ratings = quotes_for(fragment_id)
        examples.append(
            _example_row(
                example_type=example_type,
                analysis_row=row,
                fragment_text=str(
                    fragment.get("fragment_text")
                    or fragment.get("text")
                    or ""
                ),
                evidence_quotes=quotes,
                evidence_ratings=ratings,
                explanation=explanation,
            )
        )
        used.add((example_type, fragment_id))

    correct_ids = [
        stripped_text(row.get("fragment_id"))
        for row in analysis_rows
        if _has_flag(row, "correct_prediction")
    ][:3]
    explanations = {
        "correct_prediction": (
            "Predicted set equals the human-reviewed reference set."
        ),
        "retrieval_failure": (
            "Reference GI_C1_3 is absent from BM25 Top-5, so constrained "
            "Gemini could not select it. Predicted GI_C1_1 is outside the "
            "reference set."
        ),
        "overprediction": (
            "Gemini selected at least one competency that is not in the "
            "human-reviewed reference set."
        ),
        "parent_child_redundancy": (
            "Gemini predicted both a parent competency and one of its "
            "direct children for the same fragment."
        ),
        "ambiguous_gold": (
            "The researcher marked this reference annotation ambiguous."
        ),
        "unsupported_evidence": (
            "Both evidence quotes for predicted GI_C1_1 were rated 0. "
            "The human-reviewed reference is GI_C1_3."
        ),
        "partial_evidence": (
            "At least one mechanically exact quote was rated 1 "
            "(partial / ambiguous pedagogical support)."
        ),
    }

    for fragment_id in correct_ids:
        add("correct_prediction", fragment_id, explanations["correct_prediction"])

    add(
        "retrieval_failure",
        "quiz_question:1:4#f001",
        explanations["retrieval_failure"],
    )
    add(
        "unsupported_evidence",
        "quiz_question:1:4#f001",
        explanations["unsupported_evidence"],
    )

    over_ids = [
        stripped_text(row.get("fragment_id"))
        for row in analysis_rows
        if _has_flag(row, "overprediction")
        and stripped_text(row.get("fragment_id")) != "quiz_question:1:4#f001"
    ][:3]

    for fragment_id in over_ids:
        add("overprediction", fragment_id, explanations["overprediction"])

    parent_ids = [
        stripped_text(row.get("fragment_id"))
        for row in analysis_rows
        if _has_flag(row, "parent_child_redundancy")
    ][:3]

    for fragment_id in parent_ids:
        add(
            "parent_child_redundancy",
            fragment_id,
            explanations["parent_child_redundancy"],
        )

    ambiguous_ids = [
        stripped_text(row.get("fragment_id"))
        for row in analysis_rows
        if _has_flag(row, "ambiguous_gold")
    ]

    for fragment_id in ambiguous_ids:
        add("ambiguous_gold", fragment_id, explanations["ambiguous_gold"])

    partial_ids = [
        stripped_text(row.get("fragment_id"))
        for row in analysis_rows
        if _has_flag(row, "evidence_partial")
    ][:3]

    for fragment_id in partial_ids:
        add("partial_evidence", fragment_id, explanations["partial_evidence"])

    return examples
