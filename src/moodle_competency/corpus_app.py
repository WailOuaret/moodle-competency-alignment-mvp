"""Data layer for the frozen-corpus teacher validation interface (Section L).

This module contains no Streamlit import on purpose. Every function here is a
pure read over the frozen research corpus, or an explicit, validated write to
the teacher review file. The Streamlit pages under ``app/`` are thin renderers
on top of these functions so the logic stays testable.

Two review files coexist in this project and must not be confused:

``data/reviews/teacher_reviews.csv``
    The *runtime* review log written by the separate runtime app
    (``app.py`` + ``pages/``). It uses ``RUNTIME_REVIEW_COLUMNS`` and already
    holds real researcher decisions. This module never writes it.

``data/reviews/corpus_teacher_reviews.csv``
    The *frozen-corpus* review file written by this module, using
    ``TEACHER_REVIEW_COLUMNS``. The review unit is one
    (resource_id, competency_id) pair.

Nothing here writes to Moodle, to the human-reviewed reference, to the Gemini
output, to the evidence review, or to any metric file.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.annotation import read_csv, stripped_text, write_csv
from moodle_competency.teacher_reviews import (
    ALLOWED_DECISIONS,
    ALLOWED_EVIDENCE_RELEVANCE,
    TEACHER_REVIEW_COLUMNS,
)


CORPUS_REVIEW_FILENAME = "corpus_teacher_reviews.csv"
CORPUS_REVIEW_BACKUP_DIRNAME = "corpus_teacher_review_backups"

PENDING = "pending"

#: Decisions a teacher may record against an existing predicted mapping.
#: ``add`` is stored for a mapping the model never predicted.
ADD_DECISION = "add"
ALL_DECISIONS = set(ALLOWED_DECISIONS) | {ADD_DECISION}


class CorpusReviewError(ValueError):
    """Raised when a teacher review would be invalid or would lose data."""


# --------------------------------------------------------------------------
# Loading the frozen corpus
# --------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts. Blank lines are skipped."""

    if not Path(path).exists():
        raise FileNotFoundError(f"JSONL file does not exist: {path}")

    records: list[dict[str, Any]] = []

    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()

            if not line:
                continue

            records.append(json.loads(line))

    return records


def _index_by(records: Iterable[Mapping[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {stripped_text(record.get(key)): dict(record) for record in records}


class CorpusPaths:
    """Resolved locations of the frozen corpus files."""

    def __init__(self, project_root: Path) -> None:
        root = Path(project_root)
        self.project_root = root
        self.resources = root / "data" / "processed" / "resources.jsonl"
        self.fragments = root / "data" / "processed" / "fragments.jsonl"
        self.competencies = root / "data" / "processed" / "competencies.jsonl"
        self.bm25_candidates = root / "data" / "interim" / "bm25_candidates.jsonl"
        self.gemini_validated = root / "data" / "interim" / "gemini_validated.jsonl"
        self.resource_predictions = (
            root / "data" / "processed" / "resource_predictions.jsonl"
        )
        self.competency_index = (
            root / "data" / "processed" / "competency_resource_index.jsonl"
        )
        self.resource_reference = (
            root / "data" / "processed" / "resource_reference.jsonl"
        )
        self.graph_warnings = root / "data" / "processed" / "graph_warnings.jsonl"
        self.evidence_review = root / "data" / "reviews" / "evidence_review.csv"
        self.gold_annotations = (
            root / "data" / "gold" / "manual_fragment_annotations.csv"
        )
        self.reviews_dir = root / "data" / "reviews"
        self.corpus_reviews = self.reviews_dir / CORPUS_REVIEW_FILENAME
        self.corpus_review_backups = self.reviews_dir / CORPUS_REVIEW_BACKUP_DIRNAME
        self.metrics_dir = root / "reports" / "metrics"


class CorpusData:
    """An immutable in-memory view of the frozen research corpus.

    Construct with :meth:`load`. Nothing on this object writes to disk.
    """

    def __init__(
        self,
        *,
        resources: Sequence[Mapping[str, Any]],
        fragments: Sequence[Mapping[str, Any]],
        competencies: Sequence[Mapping[str, Any]],
        bm25_candidates: Sequence[Mapping[str, Any]],
        gemini_validated: Sequence[Mapping[str, Any]],
        resource_predictions: Sequence[Mapping[str, Any]],
        competency_index: Sequence[Mapping[str, Any]],
        resource_reference: Sequence[Mapping[str, Any]] = (),
        graph_warnings: Sequence[Mapping[str, Any]] = (),
        evidence_reviews: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self.resources = [dict(r) for r in resources]
        self.fragments = [dict(f) for f in fragments]
        self.competencies = [dict(c) for c in competencies]
        self.bm25_candidates = [dict(b) for b in bm25_candidates]
        self.gemini_validated = [dict(g) for g in gemini_validated]
        self.resource_predictions = [dict(p) for p in resource_predictions]
        self.competency_index = [dict(c) for c in competency_index]
        self.resource_reference = [dict(r) for r in resource_reference]
        self.graph_warnings = [dict(w) for w in graph_warnings]
        self.evidence_reviews = [dict(e) for e in evidence_reviews]

        self.resources_by_id = _index_by(self.resources, "resource_id")
        self.fragments_by_id = _index_by(self.fragments, "fragment_id")
        self.competencies_by_id = _index_by(self.competencies, "idnumber")
        self.bm25_by_fragment = _index_by(self.bm25_candidates, "fragment_id")
        self.gemini_by_fragment = _index_by(self.gemini_validated, "fragment_id")
        self.predictions_by_resource = _index_by(
            self.resource_predictions, "resource_id"
        )
        self.reference_by_resource = _index_by(self.resource_reference, "resource_id")

    # -- construction ------------------------------------------------------

    @classmethod
    def load(cls, project_root: Path) -> "CorpusData":
        paths = CorpusPaths(project_root)

        def optional_jsonl(path: Path) -> list[dict[str, Any]]:
            return read_jsonl(path) if path.exists() else []

        def optional_csv(path: Path) -> list[dict[str, str]]:
            return read_csv(path) if path.exists() else []

        return cls(
            resources=read_jsonl(paths.resources),
            fragments=read_jsonl(paths.fragments),
            competencies=read_jsonl(paths.competencies),
            bm25_candidates=read_jsonl(paths.bm25_candidates),
            gemini_validated=read_jsonl(paths.gemini_validated),
            resource_predictions=read_jsonl(paths.resource_predictions),
            competency_index=read_jsonl(paths.competency_index),
            resource_reference=optional_jsonl(paths.resource_reference),
            graph_warnings=optional_jsonl(paths.graph_warnings),
            evidence_reviews=optional_csv(paths.evidence_review),
        )

    # -- competency helpers ------------------------------------------------

    def competency(self, competency_id: str) -> dict[str, Any]:
        return self.competencies_by_id.get(stripped_text(competency_id), {})

    def competency_shortname(self, competency_id: str) -> str:
        return stripped_text(self.competency(competency_id).get("shortname"))

    def competency_description(self, competency_id: str) -> str:
        return stripped_text(self.competency(competency_id).get("description_text"))

    def competency_ids(self) -> list[str]:
        """All framework competency IDs, in framework sort order."""

        ordered = sorted(
            self.competencies,
            key=lambda c: (int(c.get("sortorder", 0) or 0), stripped_text(c.get("idnumber"))),
        )
        return [stripped_text(c.get("idnumber")) for c in ordered]

    def competency_ids_hierarchical(self) -> list[str]:
        """Competency IDs as a reader expects them: each parent then its children.

        The framework's own ``sortorder`` interleaves depths, which reads badly
        in a picker. Ordering is by ID so it is stable and reproducible.
        """

        parents = sorted(
            stripped_text(c.get("idnumber"))
            for c in self.competencies
            if not stripped_text(c.get("parent_idnumber"))
        )

        ordered: list[str] = []

        for parent_id in parents:
            ordered.append(parent_id)
            ordered.extend(
                sorted(
                    stripped_text(c.get("idnumber"))
                    for c in self.competencies
                    if stripped_text(c.get("parent_idnumber")) == parent_id
                )
            )

        # Any competency whose parent is not itself a root still belongs here.
        for competency in sorted(
            self.competencies, key=lambda c: stripped_text(c.get("idnumber"))
        ):
            competency_id = stripped_text(competency.get("idnumber"))

            if competency_id not in ordered:
                ordered.append(competency_id)

        return ordered

    def competency_label(self, competency_id: str) -> str:
        """``GI_C1_1 — Short name`` for pickers and tables."""

        shortname = self.competency_shortname(competency_id)
        competency_id = stripped_text(competency_id)

        return f"{competency_id} — {shortname}" if shortname else competency_id

    def hierarchy_context(self, competency_id: str) -> dict[str, Any]:
        """Parent / children context for a competency, from the framework only."""

        competency_id = stripped_text(competency_id)
        record = self.competency(competency_id)
        parent_id = stripped_text(record.get("parent_idnumber"))

        children = [
            stripped_text(c.get("idnumber"))
            for c in self.competencies
            if stripped_text(c.get("parent_idnumber")) == competency_id
        ]

        return {
            "competency_id": competency_id,
            "depth": record.get("depth"),
            "is_parent": bool(children),
            "parent_id": parent_id,
            "parent_shortname": (
                self.competency_shortname(parent_id) if parent_id else ""
            ),
            "child_ids": sorted(children),
        }

    # -- course / resource browsing ---------------------------------------

    def courses(self) -> list[dict[str, Any]]:
        """Course rows with resource and fragment counts, sorted by shortname."""

        summary: dict[str, dict[str, Any]] = {}

        for resource in self.resources:
            shortname = stripped_text(resource.get("course_shortname"))
            entry = summary.setdefault(
                shortname,
                {
                    "course_shortname": shortname,
                    "course_fullname": stripped_text(resource.get("course_fullname")),
                    "course_id": resource.get("course_id"),
                    "resource_count": 0,
                    "page_count": 0,
                    "quiz_question_count": 0,
                    "fragment_count": 0,
                },
            )
            entry["resource_count"] += 1

            if stripped_text(resource.get("resource_type")) == "page":
                entry["page_count"] += 1
            else:
                entry["quiz_question_count"] += 1

        for fragment in self.fragments:
            shortname = stripped_text(fragment.get("course_shortname"))

            if shortname in summary:
                summary[shortname]["fragment_count"] += 1

        return [summary[key] for key in sorted(summary)]

    def resources_for_course(self, course_shortname: str) -> list[dict[str, Any]]:
        """Resources in one course, page resources first, then quiz questions."""

        course_shortname = stripped_text(course_shortname)
        selected = [
            resource
            for resource in self.resources
            if stripped_text(resource.get("course_shortname")) == course_shortname
        ]

        def sort_key(resource: Mapping[str, Any]) -> tuple[int, str]:
            is_page = stripped_text(resource.get("resource_type")) == "page"
            return (0 if is_page else 1, stripped_text(resource.get("resource_id")))

        return sorted(selected, key=sort_key)

    def fragments_for_resource(self, resource_id: str) -> list[dict[str, Any]]:
        resource_id = stripped_text(resource_id)
        selected = [
            fragment
            for fragment in self.fragments
            if stripped_text(fragment.get("resource_id")) == resource_id
        ]
        return sorted(selected, key=lambda f: int(f.get("fragment_index", 0) or 0))

    # -- retrieval / prediction lookups ------------------------------------

    def bm25_rank(self, fragment_id: str, competency_id: str) -> int | None:
        """BM25 Top-5 rank of a competency for a fragment, or None if absent."""

        record = self.bm25_by_fragment.get(stripped_text(fragment_id), {})

        for candidate in record.get("candidates", []) or []:
            if stripped_text(candidate.get("idnumber")) == stripped_text(competency_id):
                rank = candidate.get("rank")
                return int(rank) if rank is not None else None

        return None

    def bm25_candidates_for_fragment(self, fragment_id: str) -> list[dict[str, Any]]:
        record = self.bm25_by_fragment.get(stripped_text(fragment_id), {})
        candidates = [dict(c) for c in (record.get("candidates", []) or [])]
        return sorted(candidates, key=lambda c: int(c.get("rank", 0) or 0))

    def fragment_predictions(self, fragment_id: str) -> list[dict[str, Any]]:
        """Validated Gemini selections for one fragment, with retrieval context."""

        fragment_id = stripped_text(fragment_id)
        record = self.gemini_by_fragment.get(fragment_id, {})
        rows: list[dict[str, Any]] = []

        for selection in record.get("selected", []) or []:
            competency_id = stripped_text(selection.get("idnumber"))
            rows.append(
                {
                    "fragment_id": fragment_id,
                    "competency_id": competency_id,
                    "competency_shortname": self.competency_shortname(competency_id),
                    "competency_description": self.competency_description(competency_id),
                    "confidence": selection.get("confidence"),
                    "reason": stripped_text(selection.get("reason")),
                    "evidence": list(selection.get("evidence", []) or []),
                    "bm25_rank": self.bm25_rank(fragment_id, competency_id),
                    "hierarchy": self.hierarchy_context(competency_id),
                }
            )

        return rows

    def fragment_abstained(self, fragment_id: str) -> bool:
        record = self.gemini_by_fragment.get(stripped_text(fragment_id), {})
        return bool(record.get("abstain"))

    # -- graph warnings ----------------------------------------------------

    def graph_warnings_for_fragment(self, fragment_id: str) -> list[dict[str, Any]]:
        fragment_id = stripped_text(fragment_id)
        return [
            dict(warning)
            for warning in self.graph_warnings
            if stripped_text(warning.get("fragment_id")) == fragment_id
        ]

    def graph_warning_labels(self, fragment_id: str, competency_id: str) -> list[str]:
        """Human-readable warnings touching one (fragment, competency) pair."""

        competency_id = stripped_text(competency_id)
        labels: list[str] = []

        for warning in self.graph_warnings_for_fragment(fragment_id):
            parent_id = stripped_text(warning.get("parent_id"))
            child_id = stripped_text(warning.get("child_id"))

            if competency_id not in {parent_id, child_id}:
                continue

            warning_type = stripped_text(warning.get("warning_type"))

            if competency_id == parent_id and child_id:
                labels.append(f"{warning_type}: parent of predicted {child_id}")
            elif competency_id == child_id and parent_id:
                labels.append(f"{warning_type}: parent {parent_id} also predicted")
            else:
                labels.append(warning_type)

        return labels

    # -- evidence review ---------------------------------------------------

    def evidence_ratings(self, fragment_id: str, competency_id: str) -> list[str]:
        """Human pedagogical ratings recorded for one (fragment, competency)."""

        fragment_id = stripped_text(fragment_id)
        competency_id = stripped_text(competency_id)
        ratings: list[str] = []

        for row in self.evidence_reviews:
            if (
                stripped_text(row.get("fragment_id")) == fragment_id
                and stripped_text(row.get("competency_id")) == competency_id
            ):
                rating = stripped_text(row.get("pedagogical_rating"))

                if rating:
                    ratings.append(rating)

        return ratings

    def evidence_rows(self, fragment_id: str, competency_id: str) -> list[dict[str, Any]]:
        fragment_id = stripped_text(fragment_id)
        competency_id = stripped_text(competency_id)
        return [
            dict(row)
            for row in self.evidence_reviews
            if stripped_text(row.get("fragment_id")) == fragment_id
            and stripped_text(row.get("competency_id")) == competency_id
        ]

    # -- reviewable mappings ----------------------------------------------

    def reviewable_mappings(self) -> list[dict[str, Any]]:
        """One row per predicted (resource, competency) alignment.

        This is the review unit for Section L. The count equals the number of
        predicted resource-competency alignments in
        ``resource_predictions.jsonl``.
        """

        rows: list[dict[str, Any]] = []

        for prediction in self.resource_predictions:
            resource_id = stripped_text(prediction.get("resource_id"))
            resource = self.resources_by_id.get(resource_id, {})

            for entry in prediction.get("predicted_competencies", []) or []:
                competency_id = stripped_text(entry.get("competency_id"))
                fragment_ids = [
                    stripped_text(f) for f in (entry.get("fragment_ids", []) or [])
                ]

                warnings: list[str] = []

                for fragment_id in fragment_ids:
                    warnings.extend(
                        self.graph_warning_labels(fragment_id, competency_id)
                    )

                ratings: list[str] = []

                for fragment_id in fragment_ids:
                    ratings.extend(self.evidence_ratings(fragment_id, competency_id))

                rows.append(
                    {
                        "review_id": f"{resource_id}|{competency_id}",
                        "resource_id": resource_id,
                        "resource_title": stripped_text(prediction.get("title")),
                        "resource_type": stripped_text(prediction.get("resource_type")),
                        "course_shortname": stripped_text(
                            prediction.get("course_shortname")
                        ),
                        "activity_name": stripped_text(
                            prediction.get("activity_name")
                            or resource.get("activity_name")
                        ),
                        "competency_id": competency_id,
                        "competency_shortname": self.competency_shortname(competency_id),
                        "competency_description": self.competency_description(
                            competency_id
                        ),
                        "fragment_ids": fragment_ids,
                        "support_count": entry.get("support_count"),
                        "max_confidence": entry.get("max_confidence"),
                        "mean_confidence": entry.get("mean_confidence"),
                        "evidence": list(entry.get("evidence", []) or []),
                        "bm25_ranks": [
                            self.bm25_rank(fragment_id, competency_id)
                            for fragment_id in fragment_ids
                        ],
                        "hierarchy": self.hierarchy_context(competency_id),
                        "graph_warnings": sorted(set(warnings)),
                        "evidence_ratings": ratings,
                    }
                )

        return sorted(rows, key=lambda r: (r["resource_id"], r["competency_id"]))

    # -- inverse direction -------------------------------------------------

    def competency_resources(self, competency_id: str) -> dict[str, Any]:
        """Function B: one competency to its predicted resources."""

        competency_id = stripped_text(competency_id)

        for entry in self.competency_index:
            if stripped_text(entry.get("competency_id")) == competency_id:
                return dict(entry)

        return {
            "competency_id": competency_id,
            "shortname": self.competency_shortname(competency_id),
            "description": self.competency_description(competency_id),
            "match_count": 0,
            "resources": [],
        }


# --------------------------------------------------------------------------
# Teacher review persistence
# --------------------------------------------------------------------------


def utc_today(moment: datetime | None = None) -> str:
    return (moment or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def load_corpus_reviews(path: Path) -> list[dict[str, str]]:
    """Load stored frozen-corpus teacher reviews, or an empty list."""

    path = Path(path)

    if not path.exists():
        return []

    return read_csv(path)


def review_key(resource_id: str, competency_id: str) -> str:
    return f"{stripped_text(resource_id)}|{stripped_text(competency_id)}"


def decision_for(
    reviews: Sequence[Mapping[str, Any]],
    resource_id: str,
    competency_id: str,
) -> str:
    """Stored decision for one mapping, or ``pending``."""

    key = review_key(resource_id, competency_id)

    for review in reviews:
        if review_key(
            review.get("resource_id"), review.get("competency_id")
        ) == key:
            decision = stripped_text(review.get("decision")).lower()

            if decision in ALL_DECISIONS:
                return decision

    return PENDING


def validate_review(
    *,
    resource_id: str,
    competency_id: str,
    decision: str,
    reviewer: str,
    review_date: str,
    modified_competency_ids: Sequence[str] = (),
    evidence_relevance: str = "",
    valid_competency_ids: Sequence[str],
    valid_resource_ids: Sequence[str],
) -> dict[str, str]:
    """Validate one teacher decision and return a normalized review row.

    Raises :class:`CorpusReviewError` with an explicit message on any problem.
    Nothing is written here; the caller decides when to persist.
    """

    resource_id = stripped_text(resource_id)
    competency_id = stripped_text(competency_id)
    decision = stripped_text(decision).lower()
    reviewer = stripped_text(reviewer)
    review_date = stripped_text(review_date)
    evidence_relevance = stripped_text(evidence_relevance)

    if not resource_id:
        raise CorpusReviewError("resource_id is required.")

    if resource_id not in set(valid_resource_ids):
        raise CorpusReviewError(f"Unknown resource_id: {resource_id}")

    if not competency_id:
        raise CorpusReviewError("competency_id is required.")

    if competency_id not in set(valid_competency_ids):
        raise CorpusReviewError(f"Unknown competency_id: {competency_id}")

    if decision not in ALL_DECISIONS:
        allowed = ", ".join(sorted(ALL_DECISIONS))
        raise CorpusReviewError(
            f"decision must be one of {allowed}; got {decision!r}"
        )

    if not reviewer:
        raise CorpusReviewError("reviewer is required. Reviews are never anonymous.")

    if not review_date:
        raise CorpusReviewError("review_date is required.")

    try:
        datetime.strptime(review_date, "%Y-%m-%d")
    except ValueError as error:
        raise CorpusReviewError(
            f"review_date must be YYYY-MM-DD; got {review_date!r}"
        ) from error

    normalized_modified = [
        stripped_text(value) for value in modified_competency_ids if stripped_text(value)
    ]

    for value in normalized_modified:
        if value not in set(valid_competency_ids):
            raise CorpusReviewError(f"Unknown modified competency_id: {value}")

    if decision == "modify" and not normalized_modified:
        raise CorpusReviewError(
            "A MODIFY decision requires at least one replacement competency ID."
        )

    if decision != "modify" and normalized_modified:
        raise CorpusReviewError(
            "modified_competency_ids is only allowed with a MODIFY decision."
        )

    if evidence_relevance and evidence_relevance not in ALLOWED_EVIDENCE_RELEVANCE:
        allowed = ", ".join(sorted(ALLOWED_EVIDENCE_RELEVANCE))
        raise CorpusReviewError(
            f"evidence_relevance must be blank or one of {allowed}; "
            f"got {evidence_relevance!r}"
        )

    return {
        "review_id": review_key(resource_id, competency_id),
        "resource_id": resource_id,
        "competency_id": competency_id,
        "fragment_ids": "",
        "decision": decision,
        "modified_competency_ids": ";".join(normalized_modified),
        "comment": "",
        "evidence_relevance": evidence_relevance,
        "reviewer": reviewer,
        "review_date": review_date,
    }


def upsert_review(
    reviews: Sequence[Mapping[str, Any]],
    new_review: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Insert or replace one review, keeping review IDs unique.

    The input sequence is never mutated.
    """

    key = review_key(new_review.get("resource_id"), new_review.get("competency_id"))
    updated: list[dict[str, str]] = []
    replaced = False

    for review in reviews:
        if review_key(review.get("resource_id"), review.get("competency_id")) == key:
            if replaced:
                # A duplicate already existed; drop it rather than carry it on.
                continue

            updated.append({str(k): stripped_text(v) for k, v in new_review.items()})
            replaced = True
            continue

        updated.append({str(k): stripped_text(v) for k, v in review.items()})

    if not replaced:
        updated.append({str(k): stripped_text(v) for k, v in new_review.items()})

    return updated


def assert_unique_review_ids(reviews: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()

    for review in reviews:
        key = review_key(review.get("resource_id"), review.get("competency_id"))

        if key in seen:
            raise CorpusReviewError(f"Duplicate review_id: {key}")

        seen.add(key)


def create_review_backup(
    source_path: Path,
    backup_dir: Path,
    *,
    moment: datetime | None = None,
) -> Path | None:
    """Copy the current review file aside. Returns None on a first write."""

    source_path = Path(source_path)

    if not source_path.exists():
        return None

    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = (moment or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"corpus_teacher_reviews_{stamp}.csv"
    shutil.copy2(source_path, backup_path)
    return backup_path.resolve()


def atomic_write_reviews(
    reviews: Sequence[Mapping[str, Any]],
    path: Path,
) -> Path:
    """Write the review file atomically via a temporary file in the same dir."""

    assert_unique_review_ids(reviews)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)

    try:
        write_csv(reviews, temp_path, TEACHER_REVIEW_COLUMNS)
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return path.resolve()


def save_review(
    *,
    path: Path,
    backup_dir: Path,
    new_review: Mapping[str, Any],
    moment: datetime | None = None,
) -> dict[str, Any]:
    """Back up, upsert and atomically persist one teacher decision."""

    path = Path(path)
    existing = load_corpus_reviews(path)
    backup_path = create_review_backup(path, backup_dir, moment=moment)
    updated = upsert_review(existing, new_review)
    written = atomic_write_reviews(updated, path)

    return {
        "path": written,
        "backup_path": backup_path,
        "review_count": len(updated),
        "review_id": stripped_text(new_review.get("review_id")),
    }


# --------------------------------------------------------------------------
# Progress (View 5)
# --------------------------------------------------------------------------


def review_progress(
    mappings: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Counts for the progress view. Never invents a decision.

    ``added`` counts stored reviews whose mapping the model did not predict,
    so it is reported outside the reviewed-percentage denominator.
    """

    predicted_keys = {
        review_key(m.get("resource_id"), m.get("competency_id")) for m in mappings
    }

    counts = {decision: 0 for decision in sorted(ALL_DECISIONS)}
    added = 0
    reviewed_keys: set[str] = set()

    for review in reviews:
        decision = stripped_text(review.get("decision")).lower()

        if decision not in ALL_DECISIONS:
            continue

        key = review_key(review.get("resource_id"), review.get("competency_id"))

        if key in predicted_keys:
            counts[decision] += 1
            reviewed_keys.add(key)
        else:
            added += 1

    total = len(predicted_keys)
    reviewed = len(reviewed_keys)

    per_course: dict[str, dict[str, int]] = {}
    per_type: dict[str, dict[str, int]] = {}

    for mapping in mappings:
        key = review_key(mapping.get("resource_id"), mapping.get("competency_id"))
        course = stripped_text(mapping.get("course_shortname"))
        resource_type = stripped_text(mapping.get("resource_type"))

        for bucket, name in ((per_course, course), (per_type, resource_type)):
            entry = bucket.setdefault(name, {"total": 0, "reviewed": 0, "pending": 0})
            entry["total"] += 1

            if key in reviewed_keys:
                entry["reviewed"] += 1
            else:
                entry["pending"] += 1

    return {
        "total_mappings": total,
        "reviewed": reviewed,
        "pending": total - reviewed,
        "accepted": counts.get("accept", 0),
        "rejected": counts.get("reject", 0),
        "modified": counts.get("modify", 0),
        "added": added,
        "reviewed_fraction": (reviewed / total) if total else None,
        "per_course": {name: per_course[name] for name in sorted(per_course)},
        "per_resource_type": {name: per_type[name] for name in sorted(per_type)},
    }


# --------------------------------------------------------------------------
# Read-only measured results (View 6)
# --------------------------------------------------------------------------


def load_metric_file(path: Path) -> dict[str, Any] | None:
    """Read one metric JSON read-only. Returns None when absent."""

    path = Path(path)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_measured_results(project_root: Path) -> dict[str, Any]:
    """Collect the frozen measured results for the read-only results view."""

    metrics_dir = Path(project_root) / "reports" / "metrics"

    return {
        "bm25": load_metric_file(metrics_dir / "bm25_metrics.json"),
        "constrained_llm": load_metric_file(metrics_dir / "constrained_llm_metrics.json"),
        "macro_views": load_metric_file(metrics_dir / "macro_label_views.json"),
        "evidence_review": load_metric_file(
            metrics_dir / "evidence_review_summary.json"
        ),
        "error_summary": load_metric_file(metrics_dir / "error_summary.json"),
        "graph_check": load_metric_file(metrics_dir / "graph_check_summary.json"),
        "resource_level": load_metric_file(metrics_dir / "resource_level_metrics.json"),
    }
