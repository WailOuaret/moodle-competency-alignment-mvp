"""Tests for the pedagogical evidence-rating helper.

Uses temporary fixtures only. Never mutates the live evidence-review CSV
and never invents a recommended rating.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from moodle_competency.annotation import read_csv, write_csv
from moodle_competency.evidence_review import (
    EVIDENCE_REVIEW_COLUMNS,
    LEGACY_EVIDENCE_REVIEW_COLUMNS,
    evidence_offsets,
    migrate_evidence_review_row,
    write_evidence_review,
)
from moodle_competency.evidence_review_session import (
    HELP_TEXT,
    apply_pedagogical_rating,
    atomic_write_evidence_review,
    create_timestamped_backup,
    first_unrated_index,
    format_evidence_row,
    is_rating_complete,
    load_evidence_review_workspace,
    next_unrated_index,
    parse_evidence_command,
    parse_pedagogical_rating,
    progress_counts,
)


def legacy_row(
    *,
    fragment_id: str = "page:1#f001",
    quote: str = "Design software.",
    text: str = "Design software. Deploy it.",
    rating: str = "",
    mechanically_valid: str = "true",
) -> dict[str, str]:
    return {
        "fragment_id": fragment_id,
        "resource_id": "page:1",
        "competency_id": "GI_C1_1",
        "competency_shortname": "Dev",
        "fragment_text": text,
        "evidence_quote": quote,
        "mechanically_valid": mechanically_valid,
        "pedagogical_rating": rating,
        "reviewer": "",
        "comment": "",
    }


def test_valid_and_invalid_ratings() -> None:
    assert parse_pedagogical_rating("0") == ("0", [])
    assert parse_pedagogical_rating("1") == ("1", [])
    assert parse_pedagogical_rating("2") == ("2", [])
    rating, errors = parse_pedagogical_rating("3")
    assert rating is None
    assert errors
    assert parse_pedagogical_rating("")[0] is None
    assert parse_pedagogical_rating("yes")[0] is None


def test_apply_rating_does_not_change_mechanical_or_quote() -> None:
    row = migrate_evidence_review_row(legacy_row())
    updated = apply_pedagogical_rating(
        row,
        rating="2",
        reviewer="Wail Ouaret",
        review_date="2026-09-18",
        comment="human judgement",
    )

    assert updated["pedagogical_rating"] == "2"
    assert updated["evidence_quote"] == row["evidence_quote"]
    assert updated["mechanically_valid"] == "true"
    assert updated["reviewer"] == "Wail Ouaret"
    assert updated["review_date"] == "2026-09-18"
    assert is_rating_complete(updated) is True


def test_invalid_rating_cannot_be_applied() -> None:
    row = migrate_evidence_review_row(legacy_row())

    with pytest.raises(ValueError):
        apply_pedagogical_rating(
            row,
            rating="9",
            reviewer="Wail Ouaret",
            review_date="2026-09-18",
            comment="",
        )


def test_resume_skips_already_rated_rows() -> None:
    rated = apply_pedagogical_rating(
        migrate_evidence_review_row(legacy_row(fragment_id="page:1#f001")),
        rating="0",
        reviewer="Wail Ouaret",
        review_date="2026-09-18",
        comment="",
    )
    unrated = migrate_evidence_review_row(
        legacy_row(fragment_id="page:1#f002")
    )
    later = migrate_evidence_review_row(
        legacy_row(fragment_id="page:1#f003")
    )
    rows = [rated, unrated, later]

    assert first_unrated_index(rows) == 1
    assert next_unrated_index(rows, 1) == 2
    assert progress_counts(rows)["completed"] == 1
    assert progress_counts(rows)["remaining"] == 2


def test_atomic_write_and_backup(tmp_path: Path) -> None:
    source = tmp_path / "evidence_review.csv"
    backup_dir = tmp_path / "evidence_review_backups"
    rows = [
        migrate_evidence_review_row(legacy_row(fragment_id="page:1#f001")),
        migrate_evidence_review_row(legacy_row(fragment_id="page:1#f002")),
    ]
    write_csv(rows, source, LEGACY_EVIDENCE_REVIEW_COLUMNS)
    backup = create_timestamped_backup(
        source,
        backup_dir,
        moment=datetime(2026, 9, 18, 6, 0, tzinfo=timezone.utc),
    )
    rows[0] = apply_pedagogical_rating(
        rows[0],
        rating="1",
        reviewer="Wail Ouaret",
        review_date="2026-09-18",
        comment="",
    )
    atomic_write_evidence_review(rows, source)
    saved = read_csv(source)
    original_backup = read_csv(backup)

    assert backup.name == "evidence_review_20260918T060000Z.csv"
    assert original_backup[0]["pedagogical_rating"] == ""
    assert saved[0]["pedagogical_rating"] == "1"
    assert saved[1]["pedagogical_rating"] == ""
    assert saved[0]["mechanically_valid"] == "true"


def test_legacy_csv_migrates_review_date_and_offsets(
    tmp_path: Path,
) -> None:
    source = tmp_path / "evidence_review.csv"
    write_csv(
        [legacy_row()],
        source,
        LEGACY_EVIDENCE_REVIEW_COLUMNS,
    )
    rows = load_evidence_review_workspace(source)

    assert rows[0]["review_date"] == ""
    assert rows[0]["pedagogical_rating"] == ""
    assert rows[0]["evidence_start"] == "0"
    assert rows[0]["evidence_end"] == str(len("Design software."))
    assert rows[0]["offset_valid"] == "true"
    assert rows[0]["evidence_quote"] == "Design software."


def test_exact_substring_offsets_and_duplicate_quote() -> None:
    text = "alpha beta alpha"
    first = evidence_offsets("alpha", text)
    missing = evidence_offsets("gamma", text)
    empty = evidence_offsets("", text)

    assert first["evidence_start"] == "0"
    assert first["evidence_end"] == "5"
    assert first["offset_valid"] == "true"
    assert text[int(first["evidence_start"]) : int(first["evidence_end"])] == (
        "alpha"
    )
    # Duplicate quotes use the first occurrence (str.find).
    assert text.find("alpha") == 0
    assert text.find("alpha", 1) == 11
    assert missing["offset_valid"] == "false"
    assert missing["evidence_start"] == ""
    assert empty["offset_valid"] == "false"


def test_migration_does_not_invent_a_rating() -> None:
    migrated = migrate_evidence_review_row(legacy_row())

    assert migrated["pedagogical_rating"] == ""
    assert "recommend" not in HELP_TEXT.lower() or "does not recommend" in HELP_TEXT
    rendered = format_evidence_row(
        migrated,
        position=1,
        total=83,
        completed=0,
        remaining=83,
    )
    lowered = rendered.lower()
    assert "suggest" not in lowered
    assert "likely" not in lowered
    assert "recommended rating" not in lowered


def test_commands_and_no_rating_recommendation() -> None:
    assert parse_evidence_command(":q") == "quit"
    assert parse_evidence_command(":s") == "skip"
    assert parse_evidence_command(":b") == "back"
    assert parse_evidence_command(":p") == "progress"
    assert parse_evidence_command(":h") == "help"
    assert parse_evidence_command("2") is None
    source = Path(
        "src/moodle_competency/evidence_review_session.py"
    ).read_text(encoding="utf-8")
    script = Path(
        "scripts/review_evidence_pedagogically.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "recommended rating",
        "suggest rating",
        "likely rating",
    ):
        assert forbidden not in source.lower()
        assert forbidden not in script.lower()


def test_write_helper_leaves_blank_ratings(tmp_path: Path) -> None:
    path = tmp_path / "evidence_review.csv"
    write_evidence_review([legacy_row()], path)
    saved = read_csv(path)

    assert saved[0]["pedagogical_rating"] == ""
    assert set(EVIDENCE_REVIEW_COLUMNS).issubset(saved[0])
