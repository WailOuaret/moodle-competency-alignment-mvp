"""Tests for AI-assisted annotation drafts and review."""

from __future__ import annotations

from pathlib import Path

import pytest

from moodle_competency.ai_assisted_annotation import (
    DraftValidationError,
    FORBIDDEN_SOURCE_NAMES,
    GOLD_FILENAME,
    STATUS_CONFIRMED,
    STATUS_MODIFIED,
    STATUS_PENDING,
    apply_accept_suggestion,
    apply_modified_decision,
    assert_allowed_source_paths,
    build_draft_rows,
    create_review_backup,
    draft_summary,
    export_reviewed_rows,
    is_review_complete,
    write_drafts,
)
from moodle_competency.annotation import read_csv


CATALOGUE = [
    {
        "idnumber": "GI_C1",
        "shortname": "Software parent",
        "parent_idnumber": "",
        "depth": "0",
    },
    {
        "idnumber": "GI_C1_1",
        "shortname": "Software development",
        "parent_idnumber": "GI_C1",
        "depth": "1",
    },
    {
        "idnumber": "GI_C1_3",
        "shortname": "HCI",
        "parent_idnumber": "GI_C1",
        "depth": "1",
    },
]


def fragments() -> list[dict]:
    return [
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "page",
            "activity_name": "Software",
            "title": "Software",
            "text": "Design software systems. Testing verifies requirements.",
        },
        {
            "fragment_id": "page:2#f001",
            "resource_id": "page:2",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "page",
            "activity_name": "HCI",
            "title": "HCI",
            "text": "User-centered prototypes and accessibility.",
        },
        {
            "fragment_id": "page:9#f001",
            "resource_id": "page:9",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "page",
            "activity_name": "History",
            "title": "History",
            "text": "The campus cafeteria opening hours are posted weekly.",
        },
    ]


def suggestions() -> dict[str, dict]:
    return {
        "page:1#f001": {
            "competency_ids": ["GI_C1_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": ["Design software systems."],
            "reasoning": "The fragment teaches software design, the child GI_C1_1 rather than the parent GI_C1.",
        },
        "page:2#f001": {
            "competency_ids": ["GI_C1_3"],
            "no_competency": False,
            "ambiguous": True,
            "ambiguity_reason": "Usability vs accessibility emphasis is unclear.",
            "evidence": ["User-centered prototypes and accessibility."],
            "reasoning": "HCI/UX child competency.",
        },
        "page:9#f001": {
            "competency_ids": [],
            "no_competency": True,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [],
            "reasoning": "Cafeteria hours are not a GI competency.",
        },
    }


def test_build_drafts_unique_valid_and_none(tmp_path: Path) -> None:
    gold = tmp_path / GOLD_FILENAME
    gold.write_text("untouched\n", encoding="utf-8")
    rows = build_draft_rows(
        fragments=fragments(),
        catalogue=CATALOGUE,
        suggestions_by_id=suggestions(),
    )
    path = tmp_path / "drafts.csv"
    write_drafts(rows, path)
    loaded = read_csv(path)
    ids = [row["fragment_id"] for row in loaded]
    summary = draft_summary(loaded)

    assert len(loaded) == 3
    assert len(set(ids)) == 3
    assert loaded[0]["suggested_competency_ids"] == "GI_C1_1"
    assert "GI_C1;" not in loaded[0]["suggested_competency_ids"]
    assert loaded[0]["review_status"] == STATUS_PENDING
    assert loaded[0]["human_competency_ids"] == ""
    assert loaded[2]["suggested_no_competency"] == "true"
    assert loaded[2]["suggested_competency_ids"] == ""
    assert loaded[1]["suggested_ambiguous"] == "true"
    assert "Design software systems." in loaded[0]["fragment_text"]
    assert "Design software systems." in loaded[0]["suggested_exact_evidence"]
    assert summary["none"] == 1
    assert summary["single"] == 2
    assert summary["multi"] == 0
    assert summary["ambiguous"] == 1
    assert gold.read_text(encoding="utf-8") == "untouched\n"


def test_evidence_must_be_exact_substring() -> None:
    bad = suggestions()
    bad["page:1#f001"]["evidence"] = ["paraphrased design content"]

    with pytest.raises(DraftValidationError, match="exact"):
        build_draft_rows(
            fragments=fragments(),
            catalogue=CATALOGUE,
            suggestions_by_id=bad,
        )


def test_unknown_competency_rejected() -> None:
    bad = suggestions()
    bad["page:1#f001"]["competency_ids"] = ["GI_C9_9"]

    with pytest.raises(DraftValidationError, match="Unknown"):
        build_draft_rows(
            fragments=fragments(),
            catalogue=CATALOGUE,
            suggestions_by_id=bad,
        )


def test_none_cannot_also_have_ids() -> None:
    bad = suggestions()
    bad["page:9#f001"]["competency_ids"] = ["GI_C1_1"]

    with pytest.raises(DraftValidationError, match="NONE"):
        build_draft_rows(
            fragments=fragments(),
            catalogue=CATALOGUE,
            suggestions_by_id=bad,
        )


def test_accept_and_modify_and_backup(tmp_path: Path) -> None:
    rows = build_draft_rows(
        fragments=fragments(),
        catalogue=CATALOGUE,
        suggestions_by_id=suggestions(),
    )
    path = tmp_path / "drafts.csv"
    write_drafts(rows, path)
    backup = create_review_backup(path, tmp_path / "backups")
    accepted = apply_accept_suggestion(
        rows[0],
        reviewer="Wail Ouaret",
        review_date="2026-09-18",
    )
    modified = apply_modified_decision(
        rows[1],
        reviewer="Wail Ouaret",
        review_date="2026-09-18",
        competency_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous=False,
        ambiguity_reason="",
        evidence_quotes=["User-centered prototypes and accessibility."],
        comment="Changed to software development after review.",
    )

    assert backup is not None
    assert backup.exists()
    assert accepted["review_status"] == STATUS_CONFIRMED
    assert accepted["human_competency_ids"] == "GI_C1_1"
    assert is_review_complete(accepted)
    assert modified["review_status"] == STATUS_MODIFIED
    assert modified["human_competency_ids"] == "GI_C1_1"
    assert not is_review_complete(rows[0])


def test_resume_skips_complete_rows() -> None:
    rows = build_draft_rows(
        fragments=fragments(),
        catalogue=CATALOGUE,
        suggestions_by_id=suggestions(),
    )
    rows[0] = apply_accept_suggestion(
        rows[0],
        reviewer="Wail Ouaret",
        review_date="2026-09-18",
    )
    pending = [
        index
        for index, row in enumerate(rows)
        if not is_review_complete(row)
    ]

    assert pending == [1, 2]


def test_export_requires_complete_reviews() -> None:
    rows = build_draft_rows(
        fragments=fragments(),
        catalogue=CATALOGUE,
        suggestions_by_id=suggestions(),
    )

    with pytest.raises(DraftValidationError, match="incomplete"):
        export_reviewed_rows(rows)

    reviewed = [
        apply_accept_suggestion(
            row,
            reviewer="Wail Ouaret",
            review_date="2026-09-18",
        )
        for row in rows
    ]
    exported = export_reviewed_rows(reviewed)

    assert len(exported) == 3
    assert "Not independent manual gold" in exported[0]["provenance"]


def test_forbidden_sources_are_rejected(tmp_path: Path) -> None:
    forbidden = tmp_path / "gemini_validated.jsonl"
    forbidden.write_text("{}\n", encoding="utf-8")

    with pytest.raises(DraftValidationError, match="Forbidden"):
        assert_allowed_source_paths([forbidden])

    assert GOLD_FILENAME in FORBIDDEN_SOURCE_NAMES
    assert "bm25_candidates.jsonl" in FORBIDDEN_SOURCE_NAMES
    assert "llm_tasks.jsonl" in FORBIDDEN_SOURCE_NAMES


def test_project_drafts_cover_all_fragments() -> None:
    root = Path(__file__).resolve().parent.parent
    drafts_path = (
        root / "data" / "reviews" / "ai_assisted_annotation_drafts.csv"
    )
    fragments_path = root / "data" / "processed" / "fragments.jsonl"
    gold_path = root / "data" / "gold" / "manual_fragment_annotations.csv"

    if not drafts_path.exists():
        pytest.skip("Project drafts have not been generated yet.")

    from moodle_competency.annotation import load_jsonl, parse_competency_ids
    from moodle_competency.ai_assisted_annotation import parse_evidence_json

    gold_before = gold_path.read_bytes()
    fragments = load_jsonl(fragments_path)
    drafts = read_csv(drafts_path)
    fragment_ids = [item["fragment_id"] for item in fragments]
    draft_ids = [row["fragment_id"] for row in drafts]

    assert len(drafts) == 35
    assert draft_ids == fragment_ids
    assert len(set(draft_ids)) == 35

    by_id = {item["fragment_id"]: item for item in fragments}

    for row in drafts:
        assert row["review_status"] == STATUS_PENDING
        assert row["human_competency_ids"] == ""
        ids, errors = parse_competency_ids(row["suggested_competency_ids"])
        assert not errors
        quotes, quote_errors = parse_evidence_json(
            row["suggested_exact_evidence"]
        )
        assert not quote_errors
        text = by_id[row["fragment_id"]]["text"]

        for quote in quotes:
            assert quote in text

        if row["suggested_no_competency"] == "true":
            assert ids == []
            assert quotes == []

    assert gold_path.read_bytes() == gold_before
