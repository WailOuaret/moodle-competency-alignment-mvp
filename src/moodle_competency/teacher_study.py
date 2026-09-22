"""Section M — a small, exploratory evidence-usefulness pilot.

The research question this addresses is narrow: *does showing the exact
evidence quote change how a reviewer judges a suggested competency, and how
long they take?* Exact-substring validity alone cannot answer it.

Design
------
Each sampled case is shown in one of two conditions:

``A`` (without evidence)
    The suggested competency is shown; the evidence quote is hidden behind an
    explicit "show the evidence" action. Whether the reviewer opened it is
    recorded.

``B`` (with evidence)
    The suggested competency and its evidence quote are shown together.

Assignment is a deterministic function of a fixed seed, so a rerun of
``scripts/27_prepare_teacher_study.py`` with the same seed produces exactly the
same design. The seed and the resulting assignment are saved in a manifest.

What this is not
----------------
This is an exploratory usability exercise on a small stratified sample, with
one or a few reviewers. It is not a controlled study of Moodle teachers, it
does not support inferential statistics, and it must never be reported as
either. When the only reviewer is the researcher, the correct label is
``researcher pilot``; :func:`study_label` enforces that from the recorded roles
rather than from an assumption.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import read_csv, stripped_text, write_csv


STUDY_VERSION = "1.0"
DEFAULT_SEED = 20260918
DEFAULT_SAMPLE_SIZE = 12

CONDITION_WITHOUT_EVIDENCE = "A"
CONDITION_WITH_EVIDENCE = "B"
CONDITIONS = (CONDITION_WITHOUT_EVIDENCE, CONDITION_WITH_EVIDENCE)

ALLOWED_DECISIONS = {"accept", "reject", "modify"}
MIN_CONFIDENCE = 1
MAX_CONFIDENCE = 5

#: Strata the sample tries to cover, in priority order. Each case is assigned
#: to the first stratum it matches, so the labels are mutually exclusive.
STRATA = (
    "parent_child_redundancy",
    "incorrect_prediction",
    "correct_prediction",
)

STUDY_CASE_COLUMNS = (
    "case_id",
    "condition",
    "stratum",
    "fragment_id",
    "resource_id",
    "resource_type",
    "course_shortname",
    "competency_id",
    "competency_shortname",
    "fragment_text",
    "evidence_quote",
    "reference_competency_ids",
    "predicted_competency_ids",
    "model_is_correct",
    "parent_child_redundancy",
)

STUDY_RESPONSE_COLUMNS = (
    "case_id",
    "condition",
    "reviewer",
    "reviewer_role",
    "decision",
    "confidence",
    "evidence_shown",
    "evidence_opened",
    "start_timestamp",
    "end_timestamp",
    "elapsed_seconds",
    "comment",
)


class TeacherStudyError(ValueError):
    """Raised when a study design or a recorded response would be invalid."""


# --------------------------------------------------------------------------
# Case construction
# --------------------------------------------------------------------------


def _as_bool(value: Any) -> bool:
    return stripped_text(value).lower() in {"true", "1", "yes"}


def _split_ids(value: Any) -> list[str]:
    return [part.strip() for part in stripped_text(value).split(";") if part.strip()]


def classify_stratum(error_row: Mapping[str, Any]) -> str:
    """Assign one error-analysis row to exactly one stratum."""

    if _as_bool(error_row.get("parent_child_redundancy")):
        return "parent_child_redundancy"

    if _as_bool(error_row.get("correct_prediction")):
        return "correct_prediction"

    return "incorrect_prediction"


def build_candidate_cases(
    error_rows: Sequence[Mapping[str, Any]],
    evidence_rows: Sequence[Mapping[str, Any]],
    competency_shortnames: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build one candidate case per (fragment, predicted competency) pair.

    A case needs an evidence quote, because the whole point is to compare a
    judgement made with it against one made without it. Pairs with no quote are
    skipped rather than shown with an empty quote.
    """

    shortnames = dict(competency_shortnames or {})

    evidence_by_pair: dict[tuple[str, str], list[dict[str, str]]] = {}

    for row in evidence_rows:
        key = (
            stripped_text(row.get("fragment_id")),
            stripped_text(row.get("competency_id")),
        )
        evidence_by_pair.setdefault(key, []).append(dict(row))

    cases: list[dict[str, Any]] = []

    for error_row in error_rows:
        fragment_id = stripped_text(error_row.get("fragment_id"))
        stratum = classify_stratum(error_row)
        reference_ids = _split_ids(error_row.get("gold_competency_ids"))
        predicted_ids = _split_ids(error_row.get("predicted_competency_ids"))

        for competency_id in predicted_ids:
            quotes = evidence_by_pair.get((fragment_id, competency_id), [])

            if not quotes:
                continue

            first = quotes[0]

            cases.append(
                {
                    "case_id": f"{fragment_id}|{competency_id}",
                    "stratum": stratum,
                    "fragment_id": fragment_id,
                    "resource_id": stripped_text(error_row.get("resource_id")),
                    "resource_type": stripped_text(error_row.get("resource_type")),
                    "course_shortname": stripped_text(
                        error_row.get("course_shortname")
                    ),
                    "competency_id": competency_id,
                    "competency_shortname": shortnames.get(
                        competency_id,
                        stripped_text(first.get("competency_shortname")),
                    ),
                    "fragment_text": stripped_text(first.get("fragment_text")),
                    "evidence_quote": stripped_text(first.get("evidence_quote")),
                    "reference_competency_ids": ";".join(reference_ids),
                    "predicted_competency_ids": ";".join(predicted_ids),
                    "model_is_correct": str(competency_id in reference_ids).lower(),
                    "parent_child_redundancy": str(
                        _as_bool(error_row.get("parent_child_redundancy"))
                    ).lower(),
                }
            )

    return sorted(cases, key=lambda case: case["case_id"])


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------


def _stratify(cases: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in STRATA}

    for case in cases:
        buckets.setdefault(stripped_text(case.get("stratum")), []).append(dict(case))

    return buckets


def select_stratified_sample(
    cases: Sequence[Mapping[str, Any]],
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """Pick a reproducible stratified sample spanning courses and types.

    Selection round-robins across strata so no stratum is crowded out, and
    within a stratum it round-robins across courses so one course cannot
    dominate. Within a (stratum, course) cell the order is a seeded shuffle,
    applied to a sorted list so the result depends only on the seed.

    Asking for more cases than exist returns all of them rather than raising.
    """

    if sample_size <= 0:
        raise TeacherStudyError("sample_size must be a positive integer.")

    rng = random.Random(seed)

    # cells[stratum][course] -> shuffled cases
    cells: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for case in cases:
        stratum = stripped_text(case.get("stratum"))
        course = stripped_text(case.get("course_shortname"))
        cells.setdefault(stratum, {}).setdefault(course, []).append(dict(case))

    for stratum in sorted(cells):
        for course in sorted(cells[stratum]):
            bucket = cells[stratum][course]
            bucket.sort(key=lambda case: case["case_id"])
            rng.shuffle(bucket)

    stratum_order = [name for name in STRATA if cells.get(name)]
    stratum_order.extend(
        name for name in sorted(cells) if name not in STRATA
    )

    # Independent course rotation per stratum, so a stratum missing a course
    # does not push the others out of step.
    course_cursor = {stratum: 0 for stratum in stratum_order}

    def take_from(stratum: str) -> dict[str, Any] | None:
        courses = sorted(cells.get(stratum, {}))

        if not courses:
            return None

        for offset in range(len(courses)):
            index = (course_cursor[stratum] + offset) % len(courses)
            bucket = cells[stratum][courses[index]]

            if bucket:
                course_cursor[stratum] = (index + 1) % len(courses)
                return bucket.pop(0)

        return None

    selected: list[dict[str, Any]] = []

    while len(selected) < sample_size:
        progressed = False

        for stratum in stratum_order:
            if len(selected) >= sample_size:
                break

            case = take_from(stratum)

            if case is not None:
                selected.append(case)
                progressed = True

        if not progressed:
            break

    return sorted(selected, key=lambda case: case["case_id"])


def assign_conditions(
    cases: Sequence[Mapping[str, Any]],
    *,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """Assign conditions A and B in a balanced, seeded way.

    Balancing happens *within* each stratum, so a stratum cannot end up
    entirely in one condition. The input sequence is not mutated.
    """

    rng = random.Random(seed + 1)
    assigned: list[dict[str, Any]] = []

    buckets = _stratify(cases)

    for name in sorted(buckets):
        bucket = sorted(buckets[name], key=lambda case: case["case_id"])
        labels = [
            CONDITIONS[index % len(CONDITIONS)] for index in range(len(bucket))
        ]
        rng.shuffle(labels)

        for case, condition in zip(bucket, labels):
            row = dict(case)
            row["condition"] = condition
            assigned.append(row)

    return sorted(assigned, key=lambda case: case["case_id"])


def build_study_design(
    error_rows: Sequence[Mapping[str, Any]],
    evidence_rows: Sequence[Mapping[str, Any]],
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    competency_shortnames: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build the full reproducible design: cases, conditions and a manifest."""

    candidates = build_candidate_cases(
        error_rows, evidence_rows, competency_shortnames
    )
    sample = select_stratified_sample(
        candidates, sample_size=sample_size, seed=seed
    )
    cases = assign_conditions(sample, seed=seed)

    return {
        "cases": cases,
        "manifest": design_manifest(cases, candidates, seed=seed, sample_size=sample_size),
    }


def design_manifest(
    cases: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    sample_size: int,
) -> dict[str, Any]:
    """A manifest sufficient to reproduce and audit the design."""

    def tally(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, int]:
        counts: dict[str, int] = {}

        for row in rows:
            key = stripped_text(row.get(field))
            counts[key] = counts.get(key, 0) + 1

        return {key: counts[key] for key in sorted(counts)}

    return {
        "study_version": STUDY_VERSION,
        "seed": seed,
        "requested_sample_size": sample_size,
        "candidate_case_count": len(candidates),
        "sampled_case_count": len(cases),
        "conditions": list(CONDITIONS),
        "condition_counts": tally(cases, "condition"),
        "stratum_counts": tally(cases, "stratum"),
        "course_counts": tally(cases, "course_shortname"),
        "resource_type_counts": tally(cases, "resource_type"),
        "case_ids": [stripped_text(case.get("case_id")) for case in cases],
        "design_note": (
            "Conditions are balanced within each stratum using a fixed seed. "
            "Rerunning with the same seed reproduces this design exactly."
        ),
        "interpretation_note": (
            "Exploratory usability exercise on a small stratified sample. "
            "Not a controlled study of Moodle teachers. No inferential claim "
            "is supported."
        ),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def write_study_cases(cases: Sequence[Mapping[str, Any]], path: Path) -> Path:
    return write_csv(cases, Path(path), STUDY_CASE_COLUMNS)


def load_study_cases(path: Path) -> list[dict[str, str]]:
    path = Path(path)
    return read_csv(path) if path.exists() else []


def write_study_manifest(manifest: Mapping[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(dict(manifest), handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    return path.resolve()


def load_study_responses(path: Path) -> list[dict[str, str]]:
    path = Path(path)
    return read_csv(path) if path.exists() else []


def write_study_responses(
    responses: Sequence[Mapping[str, Any]], path: Path
) -> Path:
    return write_csv(responses, Path(path), STUDY_RESPONSE_COLUMNS)


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------


def validate_response(
    *,
    case_id: str,
    condition: str,
    reviewer: str,
    reviewer_role: str,
    decision: str,
    confidence: Any,
    evidence_shown: bool,
    evidence_opened: bool,
    start_timestamp: str,
    end_timestamp: str,
    comment: str = "",
    valid_case_ids: Sequence[str] | None = None,
) -> dict[str, str]:
    """Validate one recorded response and compute its elapsed time."""

    case_id = stripped_text(case_id)
    condition = stripped_text(condition).upper()
    reviewer = stripped_text(reviewer)
    reviewer_role = stripped_text(reviewer_role).lower()
    decision = stripped_text(decision).lower()

    if not case_id:
        raise TeacherStudyError("case_id is required.")

    if valid_case_ids is not None and case_id not in set(valid_case_ids):
        raise TeacherStudyError(f"Unknown case_id: {case_id}")

    if condition not in CONDITIONS:
        raise TeacherStudyError(
            f"condition must be one of {', '.join(CONDITIONS)}; got {condition!r}"
        )

    if not reviewer:
        raise TeacherStudyError("reviewer is required. Responses are never anonymous.")

    if reviewer_role not in {"teacher", "supervisor", "researcher"}:
        raise TeacherStudyError(
            "reviewer_role must be teacher, supervisor or researcher; "
            f"got {reviewer_role!r}"
        )

    if decision not in ALLOWED_DECISIONS:
        raise TeacherStudyError(
            f"decision must be one of {', '.join(sorted(ALLOWED_DECISIONS))}; "
            f"got {decision!r}"
        )

    try:
        confidence_value = int(confidence)
    except (TypeError, ValueError) as error:
        raise TeacherStudyError(
            f"confidence must be an integer {MIN_CONFIDENCE}-{MAX_CONFIDENCE}; "
            f"got {confidence!r}"
        ) from error

    if not MIN_CONFIDENCE <= confidence_value <= MAX_CONFIDENCE:
        raise TeacherStudyError(
            f"confidence must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}; "
            f"got {confidence_value}"
        )

    started = parse_timestamp(start_timestamp, "start_timestamp")
    ended = parse_timestamp(end_timestamp, "end_timestamp")

    if ended < started:
        raise TeacherStudyError("end_timestamp is before start_timestamp.")

    elapsed = (ended - started).total_seconds()

    return {
        "case_id": case_id,
        "condition": condition,
        "reviewer": reviewer,
        "reviewer_role": reviewer_role,
        "decision": decision,
        "confidence": str(confidence_value),
        "evidence_shown": str(bool(evidence_shown)).lower(),
        "evidence_opened": str(bool(evidence_opened)).lower(),
        "start_timestamp": started.isoformat(),
        "end_timestamp": ended.isoformat(),
        "elapsed_seconds": f"{elapsed:.3f}",
        "comment": stripped_text(comment),
    }


def parse_timestamp(value: Any, field: str) -> datetime:
    text = stripped_text(value)

    if not text:
        raise TeacherStudyError(f"{field} is required.")

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise TeacherStudyError(
            f"{field} must be an ISO-8601 timestamp; got {text!r}"
        ) from error

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def upsert_response(
    responses: Sequence[Mapping[str, Any]],
    new_response: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Replace any earlier response for the same case and reviewer."""

    key = (
        stripped_text(new_response.get("case_id")),
        stripped_text(new_response.get("reviewer")),
    )

    updated: list[dict[str, str]] = []
    replaced = False

    for response in responses:
        existing = (
            stripped_text(response.get("case_id")),
            stripped_text(response.get("reviewer")),
        )

        if existing == key:
            if replaced:
                continue

            updated.append({str(k): stripped_text(v) for k, v in new_response.items()})
            replaced = True
            continue

        updated.append({str(k): stripped_text(v) for k, v in response.items()})

    if not replaced:
        updated.append({str(k): stripped_text(v) for k, v in new_response.items()})

    return updated


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    middle = len(ordered) // 2

    if len(ordered) % 2:
        return ordered[middle]

    return (ordered[middle - 1] + ordered[middle]) / 2


def _mean(values: Sequence[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def study_label(responses: Sequence[Mapping[str, Any]]) -> str:
    """``researcher pilot`` unless a teacher or supervisor actually took part."""

    roles = {stripped_text(r.get("reviewer_role")).lower() for r in responses}

    if roles & {"teacher", "supervisor"}:
        return "teacher/supervisor pilot"

    return "researcher pilot"


def summarize_responses(
    responses: Sequence[Mapping[str, Any]],
    cases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Descriptive summary by condition. Returns nulls when there is no data.

    No significance test is computed: the sample size and single-reviewer
    design do not support one, and reporting one would overstate the result.
    """

    responses = [dict(r) for r in responses]

    if not responses:
        return {
            "status": "WAITING_FOR_HUMAN",
            "message": "EVIDENCE USEFULNESS PILOT NOT YET PERFORMED",
            "study_label": None,
            "response_count": 0,
            "case_count": len(cases),
            "reviewers": [],
            "reviewer_roles": {},
            "by_condition": {
                condition: _empty_condition_summary() for condition in CONDITIONS
            },
            "significance_tests": "not_run",
            "significance_tests_note": (
                "No significance tests. Sample size and design do not support "
                "inferential claims."
            ),
            "interpretation_note": (
                "Exploratory usability exercise. Not a controlled study of "
                "Moodle teachers."
            ),
        }

    roles: dict[str, int] = {}

    for response in responses:
        role = stripped_text(response.get("reviewer_role")).lower() or "unrecorded"
        roles[role] = roles.get(role, 0) + 1

    by_condition = {
        condition: _summarize_condition(
            [
                r
                for r in responses
                if stripped_text(r.get("condition")).upper() == condition
            ]
        )
        for condition in CONDITIONS
    }

    return {
        "status": "COMPLETE",
        "message": None,
        "study_label": study_label(responses),
        "response_count": len(responses),
        "case_count": len(cases),
        "reviewers": sorted(
            {stripped_text(r.get("reviewer")) for r in responses if r.get("reviewer")}
        ),
        "reviewer_roles": {key: roles[key] for key in sorted(roles)},
        "by_condition": by_condition,
        "significance_tests": "not_run",
        "significance_tests_note": (
            "No significance tests. Sample size and design do not support "
            "inferential claims."
        ),
        "interpretation_note": (
            "Exploratory usability exercise on a small stratified sample. "
            "Descriptive only."
        ),
    }


def _empty_condition_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "accept_count": 0,
        "reject_count": 0,
        "modify_count": 0,
        "acceptance_rate": None,
        "rejection_rate": None,
        "edit_rate": None,
        "median_elapsed_seconds": None,
        "mean_elapsed_seconds": None,
        "median_confidence": None,
        "mean_confidence": None,
        "evidence_opened_count": 0,
    }


def _summarize_condition(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return _empty_condition_summary()

    decisions = [stripped_text(r.get("decision")).lower() for r in rows]
    elapsed = [
        float(r["elapsed_seconds"])
        for r in rows
        if stripped_text(r.get("elapsed_seconds"))
    ]
    confidence = [
        float(r["confidence"]) for r in rows if stripped_text(r.get("confidence"))
    ]
    total = len(rows)

    accept = decisions.count("accept")
    reject = decisions.count("reject")
    modify = decisions.count("modify")

    return {
        "n": total,
        "accept_count": accept,
        "reject_count": reject,
        "modify_count": modify,
        "acceptance_rate": accept / total,
        "rejection_rate": reject / total,
        "edit_rate": modify / total,
        "median_elapsed_seconds": _median(elapsed),
        "mean_elapsed_seconds": _mean(elapsed),
        "median_confidence": _median(confidence),
        "mean_confidence": _mean(confidence),
        "evidence_opened_count": sum(
            1 for r in rows if stripped_text(r.get("evidence_opened")).lower() == "true"
        ),
    }
