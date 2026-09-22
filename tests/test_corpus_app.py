"""Tests for the frozen-corpus teacher interface data layer.

Every test builds its own fixture under ``tmp_path``. No test reads or writes
real experimental data, and no test calls a live API.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from moodle_competency.corpus_app import (
    CorpusData,
    CorpusReviewError,
    assert_unique_review_ids,
    atomic_write_reviews,
    create_review_backup,
    decision_for,
    load_corpus_reviews,
    load_measured_results,
    load_metric_file,
    read_jsonl,
    review_key,
    review_progress,
    save_review,
    upsert_review,
    validate_review,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


COMPETENCIES = [
    {
        "idnumber": "GI_P1",
        "shortname": "Parent one",
        "description_text": "Parent one description",
        "depth": 0,
        "parent_idnumber": "",
        "sortorder": 0,
    },
    {
        "idnumber": "GI_P1_1",
        "shortname": "Child one",
        "description_text": "Child one description",
        "depth": 1,
        "parent_idnumber": "GI_P1",
        "sortorder": 1,
    },
    {
        "idnumber": "GI_P1_2",
        "shortname": "Child two",
        "description_text": "Child two description",
        "depth": 1,
        "parent_idnumber": "GI_P1",
        "sortorder": 2,
    },
]

RESOURCES = [
    {
        "resource_id": "page:1",
        "course_shortname": "MVP-SW",
        "course_fullname": "Software course",
        "course_id": 2,
        "resource_type": "page",
        "title": "Page one",
        "activity_name": "Page one activity",
        "text": "Page one body text",
    },
    {
        "resource_id": "quiz_question:1:1",
        "course_shortname": "MVP-DATA",
        "course_fullname": "Data course",
        "course_id": 3,
        "resource_type": "quiz_question",
        "title": "Question one",
        "activity_name": "Quiz one",
        "text": "Question one body",
    },
]

FRAGMENTS = [
    {
        "fragment_id": "page:1#f001",
        "resource_id": "page:1",
        "course_shortname": "MVP-SW",
        "resource_type": "page",
        "fragment_type": "page_chunk",
        "fragment_index": 1,
        "title": "Page one",
        "text": "Fragment one text about design.",
    },
    {
        "fragment_id": "page:1#f002",
        "resource_id": "page:1",
        "course_shortname": "MVP-SW",
        "resource_type": "page",
        "fragment_type": "page_chunk",
        "fragment_index": 2,
        "title": "Page one",
        "text": "Fragment two text about testing.",
    },
    {
        "fragment_id": "quiz_question:1:1#f001",
        "resource_id": "quiz_question:1:1",
        "course_shortname": "MVP-DATA",
        "resource_type": "quiz_question",
        "fragment_type": "quiz_question",
        "fragment_index": 1,
        "title": "Question one",
        "text": "Question one fragment text.",
    },
]

BM25 = [
    {
        "fragment_id": "page:1#f001",
        "candidates": [
            {"idnumber": "GI_P1_1", "rank": 1, "bm25_score": 10.0},
            {"idnumber": "GI_P1", "rank": 2, "bm25_score": 5.0},
        ],
    },
    {
        "fragment_id": "page:1#f002",
        "candidates": [{"idnumber": "GI_P1_2", "rank": 1, "bm25_score": 8.0}],
    },
    {
        "fragment_id": "quiz_question:1:1#f001",
        "candidates": [{"idnumber": "GI_P1_1", "rank": 1, "bm25_score": 7.0}],
    },
]

GEMINI = [
    {
        "fragment_id": "page:1#f001",
        "abstain": False,
        "valid": True,
        "selected": [
            {
                "idnumber": "GI_P1_1",
                "confidence": 0.95,
                "evidence": ["Fragment one text about design."],
                "reason": "Design is covered.",
            },
            {
                "idnumber": "GI_P1",
                "confidence": 0.80,
                "evidence": ["Fragment one text about design."],
                "reason": "Parent also matches.",
            },
        ],
    },
    {
        "fragment_id": "page:1#f002",
        "abstain": False,
        "valid": True,
        "selected": [
            {
                "idnumber": "GI_P1_2",
                "confidence": 0.90,
                "evidence": ["Fragment two text about testing."],
                "reason": "Testing is covered.",
            }
        ],
    },
    {
        "fragment_id": "quiz_question:1:1#f001",
        "abstain": True,
        "valid": True,
        "selected": [],
    },
]

RESOURCE_PREDICTIONS = [
    {
        "resource_id": "page:1",
        "course_shortname": "MVP-SW",
        "resource_type": "page",
        "title": "Page one",
        "activity_name": "Page one activity",
        "fragment_ids": ["page:1#f001", "page:1#f002"],
        "predicted_competencies": [
            {
                "competency_id": "GI_P1_1",
                "fragment_ids": ["page:1#f001"],
                "support_count": 1,
                "max_confidence": 0.95,
                "mean_confidence": 0.95,
                "evidence": ["Fragment one text about design."],
            },
            {
                "competency_id": "GI_P1",
                "fragment_ids": ["page:1#f001"],
                "support_count": 1,
                "max_confidence": 0.80,
                "mean_confidence": 0.80,
                "evidence": ["Fragment one text about design."],
            },
            {
                "competency_id": "GI_P1_2",
                "fragment_ids": ["page:1#f002"],
                "support_count": 1,
                "max_confidence": 0.90,
                "mean_confidence": 0.90,
                "evidence": ["Fragment two text about testing."],
            },
        ],
    },
    {
        "resource_id": "quiz_question:1:1",
        "course_shortname": "MVP-DATA",
        "resource_type": "quiz_question",
        "title": "Question one",
        "activity_name": "Quiz one",
        "fragment_ids": ["quiz_question:1:1#f001"],
        "predicted_competencies": [],
    },
]

COMPETENCY_INDEX = [
    {
        "competency_id": "GI_P1_1",
        "shortname": "Child one",
        "description": "Child one description",
        "depth": 1,
        "parent_idnumber": "GI_P1",
        "match_count": 1,
        "resources": [
            {
                "resource_id": "page:1",
                "course_shortname": "MVP-SW",
                "resource_type": "page",
                "title": "Page one",
                "support_count": 1,
                "max_confidence": 0.95,
                "evidence": ["Fragment one text about design."],
            }
        ],
    }
]

GRAPH_WARNINGS = [
    {
        "fragment_id": "page:1#f001",
        "resource_id": "page:1",
        "warning_type": "parent_child_redundancy",
        "parent_id": "GI_P1",
        "child_id": "GI_P1_1",
        "action": "warning_only",
    }
]

EVIDENCE_REVIEW_COLUMNS = [
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
]

EVIDENCE_REVIEW_ROWS = [
    {
        "fragment_id": "page:1#f001",
        "resource_id": "page:1",
        "competency_id": "GI_P1_1",
        "competency_shortname": "Child one",
        "fragment_text": "Fragment one text about design.",
        "evidence_quote": "Fragment one text about design.",
        "mechanically_valid": "true",
        "evidence_start": "0",
        "evidence_end": "31",
        "offset_valid": "true",
        "pedagogical_rating": "2",
        "reviewer": "Test Reviewer",
        "comment": "",
        "review_date": "2026-09-18",
    },
    {
        "fragment_id": "page:1#f001",
        "resource_id": "page:1",
        "competency_id": "GI_P1",
        "competency_shortname": "Parent one",
        "fragment_text": "Fragment one text about design.",
        "evidence_quote": "Fragment one text about design.",
        "mechanically_valid": "true",
        "evidence_start": "0",
        "evidence_end": "31",
        "offset_valid": "true",
        "pedagogical_rating": "1",
        "reviewer": "Test Reviewer",
        "comment": "Parent only by hierarchy.",
        "review_date": "2026-09-18",
    },
]


def _write_jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A miniature project tree with the frozen corpus files."""

    _write_jsonl(tmp_path / "data/processed/resources.jsonl", RESOURCES)
    _write_jsonl(tmp_path / "data/processed/fragments.jsonl", FRAGMENTS)
    _write_jsonl(tmp_path / "data/processed/competencies.jsonl", COMPETENCIES)
    _write_jsonl(tmp_path / "data/interim/bm25_candidates.jsonl", BM25)
    _write_jsonl(tmp_path / "data/interim/gemini_validated.jsonl", GEMINI)
    _write_jsonl(
        tmp_path / "data/processed/resource_predictions.jsonl", RESOURCE_PREDICTIONS
    )
    _write_jsonl(
        tmp_path / "data/processed/competency_resource_index.jsonl", COMPETENCY_INDEX
    )
    _write_jsonl(tmp_path / "data/processed/graph_warnings.jsonl", GRAPH_WARNINGS)

    review_path = tmp_path / "data/reviews/evidence_review.csv"
    review_path.parent.mkdir(parents=True, exist_ok=True)

    with review_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVIDENCE_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(EVIDENCE_REVIEW_ROWS)

    return tmp_path


@pytest.fixture()
def corpus(project: Path) -> CorpusData:
    return CorpusData.load(project)


VALID_COMPETENCIES = [c["idnumber"] for c in COMPETENCIES]
VALID_RESOURCES = [r["resource_id"] for r in RESOURCES]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def test_read_jsonl_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "sample.jsonl"
    path.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")

    assert read_jsonl(path) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_jsonl(tmp_path / "absent.jsonl")


def test_load_reads_every_corpus_file(corpus: CorpusData) -> None:
    assert len(corpus.resources) == 2
    assert len(corpus.fragments) == 3
    assert len(corpus.competencies) == 3
    assert len(corpus.resource_predictions) == 2
    assert len(corpus.graph_warnings) == 1
    assert len(corpus.evidence_reviews) == 2


def test_optional_files_may_be_absent(project: Path) -> None:
    (project / "data/processed/graph_warnings.jsonl").unlink()
    (project / "data/reviews/evidence_review.csv").unlink()

    corpus = CorpusData.load(project)

    assert corpus.graph_warnings == []
    assert corpus.evidence_reviews == []


# --------------------------------------------------------------------------
# Browsing (View 1)
# --------------------------------------------------------------------------


def test_courses_counts_resources_and_fragments(corpus: CorpusData) -> None:
    courses = corpus.courses()

    assert [c["course_shortname"] for c in courses] == ["MVP-DATA", "MVP-SW"]

    by_name = {c["course_shortname"]: c for c in courses}
    assert by_name["MVP-SW"]["resource_count"] == 1
    assert by_name["MVP-SW"]["page_count"] == 1
    assert by_name["MVP-SW"]["fragment_count"] == 2
    assert by_name["MVP-DATA"]["quiz_question_count"] == 1
    assert by_name["MVP-DATA"]["fragment_count"] == 1


def test_resources_for_course_orders_pages_first(corpus: CorpusData) -> None:
    assert [r["resource_id"] for r in corpus.resources_for_course("MVP-SW")] == [
        "page:1"
    ]
    assert corpus.resources_for_course("UNKNOWN") == []


def test_fragments_for_resource_sorted_by_index(corpus: CorpusData) -> None:
    ids = [f["fragment_id"] for f in corpus.fragments_for_resource("page:1")]

    assert ids == ["page:1#f001", "page:1#f002"]


# --------------------------------------------------------------------------
# Hierarchy and retrieval context (View 2)
# --------------------------------------------------------------------------


def test_hierarchy_context_for_parent_and_child(corpus: CorpusData) -> None:
    parent = corpus.hierarchy_context("GI_P1")

    assert parent["is_parent"] is True
    assert parent["parent_id"] == ""
    assert parent["child_ids"] == ["GI_P1_1", "GI_P1_2"]

    child = corpus.hierarchy_context("GI_P1_1")

    assert child["is_parent"] is False
    assert child["parent_id"] == "GI_P1"
    assert child["parent_shortname"] == "Parent one"


def test_bm25_rank_found_and_missing(corpus: CorpusData) -> None:
    assert corpus.bm25_rank("page:1#f001", "GI_P1_1") == 1
    assert corpus.bm25_rank("page:1#f001", "GI_P1") == 2
    assert corpus.bm25_rank("page:1#f001", "GI_P1_2") is None
    assert corpus.bm25_rank("absent#f001", "GI_P1_1") is None


def test_fragment_predictions_carry_full_context(corpus: CorpusData) -> None:
    rows = corpus.fragment_predictions("page:1#f001")

    assert [r["competency_id"] for r in rows] == ["GI_P1_1", "GI_P1"]

    first = rows[0]
    assert first["competency_shortname"] == "Child one"
    assert first["competency_description"] == "Child one description"
    assert first["confidence"] == 0.95
    assert first["bm25_rank"] == 1
    assert first["evidence"] == ["Fragment one text about design."]
    assert first["hierarchy"]["parent_id"] == "GI_P1"


def test_fragment_abstention_is_reported(corpus: CorpusData) -> None:
    assert corpus.fragment_abstained("quiz_question:1:1#f001") is True
    assert corpus.fragment_abstained("page:1#f001") is False


def test_graph_warning_labels_describe_both_sides(corpus: CorpusData) -> None:
    parent_labels = corpus.graph_warning_labels("page:1#f001", "GI_P1")
    child_labels = corpus.graph_warning_labels("page:1#f001", "GI_P1_1")

    assert parent_labels == ["parent_child_redundancy: parent of predicted GI_P1_1"]
    assert child_labels == [
        "parent_child_redundancy: parent GI_P1 also predicted"
    ]
    assert corpus.graph_warning_labels("page:1#f002", "GI_P1_2") == []


def test_evidence_ratings_are_read_not_derived(corpus: CorpusData) -> None:
    assert corpus.evidence_ratings("page:1#f001", "GI_P1_1") == ["2"]
    assert corpus.evidence_ratings("page:1#f001", "GI_P1") == ["1"]
    assert corpus.evidence_ratings("page:1#f002", "GI_P1_2") == []


# --------------------------------------------------------------------------
# Reviewable mappings
# --------------------------------------------------------------------------


def test_reviewable_mappings_one_row_per_alignment(corpus: CorpusData) -> None:
    mappings = corpus.reviewable_mappings()

    assert len(mappings) == 3
    assert [m["competency_id"] for m in mappings] == ["GI_P1", "GI_P1_1", "GI_P1_2"]

    parent_row = next(m for m in mappings if m["competency_id"] == "GI_P1")
    assert parent_row["resource_id"] == "page:1"
    assert parent_row["course_shortname"] == "MVP-SW"
    assert parent_row["bm25_ranks"] == [2]
    assert parent_row["graph_warnings"] == [
        "parent_child_redundancy: parent of predicted GI_P1_1"
    ]
    assert parent_row["evidence_ratings"] == ["1"]


def test_resource_without_predictions_contributes_no_mapping(
    corpus: CorpusData,
) -> None:
    mappings = corpus.reviewable_mappings()

    assert all(m["resource_id"] != "quiz_question:1:1" for m in mappings)


def test_competency_resources_inverse_direction(corpus: CorpusData) -> None:
    entry = corpus.competency_resources("GI_P1_1")

    assert entry["match_count"] == 1
    assert entry["resources"][0]["resource_id"] == "page:1"


def test_competency_resources_unknown_returns_empty_shell(corpus: CorpusData) -> None:
    entry = corpus.competency_resources("GI_P1_2")

    assert entry["match_count"] == 0
    assert entry["resources"] == []
    assert entry["shortname"] == "Child two"


# --------------------------------------------------------------------------
# Review validation (View 3)
# --------------------------------------------------------------------------


def _valid_kwargs(**overrides):
    kwargs = {
        "resource_id": "page:1",
        "competency_id": "GI_P1_1",
        "decision": "accept",
        "reviewer": "Test Reviewer",
        "review_date": "2026-09-22",
        "valid_competency_ids": VALID_COMPETENCIES,
        "valid_resource_ids": VALID_RESOURCES,
    }
    kwargs.update(overrides)
    return kwargs


def test_validate_review_accepts_a_well_formed_decision() -> None:
    row = validate_review(**_valid_kwargs())

    assert row["review_id"] == "page:1|GI_P1_1"
    assert row["decision"] == "accept"
    assert row["reviewer"] == "Test Reviewer"
    assert row["review_date"] == "2026-09-22"


def test_validate_review_normalizes_decision_case() -> None:
    row = validate_review(**_valid_kwargs(decision="REJECT"))

    assert row["decision"] == "reject"


def test_validate_review_rejects_unknown_ids() -> None:
    with pytest.raises(CorpusReviewError, match="Unknown resource_id"):
        validate_review(**_valid_kwargs(resource_id="page:999"))

    with pytest.raises(CorpusReviewError, match="Unknown competency_id"):
        validate_review(**_valid_kwargs(competency_id="GI_NOPE"))


def test_validate_review_requires_reviewer_and_date() -> None:
    with pytest.raises(CorpusReviewError, match="reviewer is required"):
        validate_review(**_valid_kwargs(reviewer="  "))

    with pytest.raises(CorpusReviewError, match="review_date is required"):
        validate_review(**_valid_kwargs(review_date=""))


def test_validate_review_rejects_malformed_date() -> None:
    with pytest.raises(CorpusReviewError, match="YYYY-MM-DD"):
        validate_review(**_valid_kwargs(review_date="22/09/2026"))


def test_validate_review_rejects_unknown_decision() -> None:
    with pytest.raises(CorpusReviewError, match="decision must be one of"):
        validate_review(**_valid_kwargs(decision="maybe"))


def test_modify_requires_valid_replacement_ids() -> None:
    with pytest.raises(CorpusReviewError, match="requires at least one replacement"):
        validate_review(**_valid_kwargs(decision="modify"))

    with pytest.raises(CorpusReviewError, match="Unknown modified competency_id"):
        validate_review(
            **_valid_kwargs(decision="modify", modified_competency_ids=["GI_NOPE"])
        )

    row = validate_review(
        **_valid_kwargs(decision="modify", modified_competency_ids=["GI_P1_2"])
    )
    assert row["modified_competency_ids"] == "GI_P1_2"


def test_replacements_not_allowed_without_modify() -> None:
    with pytest.raises(CorpusReviewError, match="only allowed with a MODIFY"):
        validate_review(
            **_valid_kwargs(decision="accept", modified_competency_ids=["GI_P1_2"])
        )


def test_evidence_relevance_must_be_blank_or_0_1_2() -> None:
    assert validate_review(**_valid_kwargs(evidence_relevance=""))["evidence_relevance"] == ""
    assert (
        validate_review(**_valid_kwargs(evidence_relevance="2"))["evidence_relevance"]
        == "2"
    )

    with pytest.raises(CorpusReviewError, match="evidence_relevance"):
        validate_review(**_valid_kwargs(evidence_relevance="5"))


def test_add_decision_is_allowed_for_a_missing_competency() -> None:
    row = validate_review(**_valid_kwargs(decision="add", competency_id="GI_P1_2"))

    assert row["decision"] == "add"


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def test_upsert_does_not_mutate_the_input(tmp_path: Path) -> None:
    existing = [validate_review(**_valid_kwargs())]
    snapshot = [dict(row) for row in existing]

    upsert_review(existing, validate_review(**_valid_kwargs(decision="reject")))

    assert existing == snapshot


def test_upsert_replaces_rather_than_duplicating() -> None:
    first = validate_review(**_valid_kwargs(decision="accept"))
    second = validate_review(**_valid_kwargs(decision="reject"))

    updated = upsert_review([first], second)

    assert len(updated) == 1
    assert updated[0]["decision"] == "reject"


def test_upsert_appends_a_distinct_mapping() -> None:
    first = validate_review(**_valid_kwargs())
    other = validate_review(**_valid_kwargs(competency_id="GI_P1_2"))

    updated = upsert_review([first], other)

    assert len(updated) == 2


def test_assert_unique_review_ids_detects_duplicates() -> None:
    row = validate_review(**_valid_kwargs())

    with pytest.raises(CorpusReviewError, match="Duplicate review_id"):
        assert_unique_review_ids([row, dict(row)])


def test_atomic_write_leaves_no_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "reviews.csv"
    atomic_write_reviews([validate_review(**_valid_kwargs())], path)

    assert path.exists()
    assert list(tmp_path.glob("*.tmp")) == []

    reloaded = load_corpus_reviews(path)
    assert reloaded[0]["decision"] == "accept"


def test_atomic_write_refuses_duplicate_ids(tmp_path: Path) -> None:
    row = validate_review(**_valid_kwargs())
    path = tmp_path / "reviews.csv"

    with pytest.raises(CorpusReviewError):
        atomic_write_reviews([row, dict(row)], path)

    assert not path.exists()


def test_backup_is_none_on_first_write_then_created(tmp_path: Path) -> None:
    path = tmp_path / "reviews.csv"
    backup_dir = tmp_path / "backups"

    assert create_review_backup(path, backup_dir) is None

    atomic_write_reviews([validate_review(**_valid_kwargs())], path)
    moment = datetime(2026, 9, 22, 10, 30, 0, tzinfo=timezone.utc)
    backup = create_review_backup(path, backup_dir, moment=moment)

    assert backup is not None
    assert backup.name == "corpus_teacher_reviews_20260922T103000Z.csv"
    assert backup.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")


def test_save_review_backs_up_the_previous_version(tmp_path: Path) -> None:
    path = tmp_path / "reviews.csv"
    backup_dir = tmp_path / "backups"

    first = save_review(
        path=path,
        backup_dir=backup_dir,
        new_review=validate_review(**_valid_kwargs(decision="accept")),
    )
    assert first["backup_path"] is None
    assert first["review_count"] == 1

    second = save_review(
        path=path,
        backup_dir=backup_dir,
        new_review=validate_review(**_valid_kwargs(decision="reject")),
        moment=datetime(2026, 9, 22, 11, 0, 0, tzinfo=timezone.utc),
    )

    assert second["backup_path"] is not None
    assert second["review_count"] == 1
    assert load_corpus_reviews(path)[0]["decision"] == "reject"

    backed_up = load_corpus_reviews(second["backup_path"])
    assert backed_up[0]["decision"] == "accept"


def test_load_corpus_reviews_missing_file_is_empty(tmp_path: Path) -> None:
    assert load_corpus_reviews(tmp_path / "absent.csv") == []


def test_decision_for_defaults_to_pending() -> None:
    reviews = [validate_review(**_valid_kwargs(decision="accept"))]

    assert decision_for(reviews, "page:1", "GI_P1_1") == "accept"
    assert decision_for(reviews, "page:1", "GI_P1_2") == "pending"
    assert decision_for([], "page:1", "GI_P1_1") == "pending"


def test_decision_for_ignores_blank_decisions() -> None:
    row = validate_review(**_valid_kwargs())
    row["decision"] = ""

    assert decision_for([row], "page:1", "GI_P1_1") == "pending"


# --------------------------------------------------------------------------
# Progress (View 5)
# --------------------------------------------------------------------------


def test_progress_with_no_reviews_is_all_pending(corpus: CorpusData) -> None:
    progress = review_progress(corpus.reviewable_mappings(), [])

    assert progress["total_mappings"] == 3
    assert progress["reviewed"] == 0
    assert progress["pending"] == 3
    assert progress["accepted"] == 0
    assert progress["added"] == 0
    assert progress["reviewed_fraction"] == 0.0


def test_progress_counts_decisions_and_breakdowns(corpus: CorpusData) -> None:
    mappings = corpus.reviewable_mappings()
    reviews = [
        validate_review(**_valid_kwargs(decision="accept")),
        validate_review(**_valid_kwargs(competency_id="GI_P1", decision="reject")),
    ]

    progress = review_progress(mappings, reviews)

    assert progress["reviewed"] == 2
    assert progress["pending"] == 1
    assert progress["accepted"] == 1
    assert progress["rejected"] == 1
    assert progress["reviewed_fraction"] == pytest.approx(2 / 3)
    assert progress["per_course"]["MVP-SW"] == {
        "total": 3,
        "reviewed": 2,
        "pending": 1,
    }
    assert progress["per_resource_type"]["page"]["total"] == 3


def test_added_mappings_are_counted_separately(corpus: CorpusData) -> None:
    mappings = corpus.reviewable_mappings()
    added = validate_review(
        **_valid_kwargs(
            resource_id="quiz_question:1:1",
            competency_id="GI_P1_2",
            decision="add",
        )
    )

    progress = review_progress(mappings, [added])

    assert progress["added"] == 1
    assert progress["reviewed"] == 0
    assert progress["total_mappings"] == 3


def test_progress_fraction_is_none_without_mappings() -> None:
    assert review_progress([], [])["reviewed_fraction"] is None


# --------------------------------------------------------------------------
# Read-only results (View 6)
# --------------------------------------------------------------------------


def test_load_metric_file_missing_returns_none(tmp_path: Path) -> None:
    assert load_metric_file(tmp_path / "absent.json") is None


def test_load_measured_results_tolerates_missing_metrics(project: Path) -> None:
    results = load_measured_results(project)

    assert set(results) == {
        "bm25",
        "constrained_llm",
        "macro_views",
        "evidence_review",
        "error_summary",
        "graph_check",
        "resource_level",
    }
    assert all(value is None for value in results.values())


def test_load_measured_results_reads_present_metrics(project: Path) -> None:
    metrics_dir = project / "reports" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    (metrics_dir / "bm25_metrics.json").write_text(
        json.dumps({"recall_at_5": 0.97}), encoding="utf-8"
    )

    results = load_measured_results(project)

    assert results["bm25"] == {"recall_at_5": 0.97}
    assert results["constrained_llm"] is None


def test_review_key_is_stable_and_trimmed() -> None:
    assert review_key(" page:1 ", " GI_P1_1 ") == "page:1|GI_P1_1"


def test_competency_ids_hierarchical_puts_children_under_parent(
    corpus: CorpusData,
) -> None:
    assert corpus.competency_ids_hierarchical() == ["GI_P1", "GI_P1_1", "GI_P1_2"]


def test_competency_ids_uses_framework_sort_order(corpus: CorpusData) -> None:
    assert corpus.competency_ids() == ["GI_P1", "GI_P1_1", "GI_P1_2"]


def test_competency_ids_hierarchical_includes_orphans(project: Path) -> None:
    extra = dict(COMPETENCIES[0])
    extra.update(
        {"idnumber": "GI_X", "parent_idnumber": "GI_MISSING", "sortorder": 9}
    )
    _write_jsonl(
        project / "data/processed/competencies.jsonl", [*COMPETENCIES, extra]
    )

    ordered = CorpusData.load(project).competency_ids_hierarchical()

    assert ordered == ["GI_P1", "GI_P1_1", "GI_P1_2", "GI_X"]


def test_competency_label_formats_id_and_shortname(corpus: CorpusData) -> None:
    assert corpus.competency_label("GI_P1_1") == "GI_P1_1 — Child one"
    assert corpus.competency_label("GI_UNKNOWN") == "GI_UNKNOWN"
