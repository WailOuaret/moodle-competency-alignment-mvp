"""Tests for the interactive human annotation helper."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from moodle_competency.annotation import (
    ANNOTATION_COLUMNS,
    read_csv,
    write_csv,
)
from moodle_competency.annotation_session import (
    apply_human_decision,
    atomic_write_annotations,
    catalogue_id_set,
    create_timestamped_backup,
    decision_guide,
    first_incomplete_index,
    format_catalogue,
    is_row_complete,
    load_annotation_workspace,
    next_incomplete_index,
    parse_competency_choice,
    parse_session_command,
    parse_yes_no,
    progress_counts,
    validate_evidence_quotes,
    validate_session_identity,
)


def sample_catalogue() -> list[dict[str, str]]:
    return [
        {
            "idnumber": "GI_C1",
            "shortname": "Design software",
            "description": "Parent software competency.",
            "parent_idnumber": "",
            "hierarchy_path": "GI_C1",
            "depth": "0",
        },
        {
            "idnumber": "GI_C1_1",
            "shortname": "Software development",
            "description": "Child software competency.",
            "parent_idnumber": "GI_C1",
            "hierarchy_path": "GI_C1 > GI_C1_1",
            "depth": "1",
        },
        {
            "idnumber": "GI_C1_3",
            "shortname": "HCI and UX",
            "description": "Child interface competency.",
            "parent_idnumber": "GI_C1",
            "hierarchy_path": "GI_C1 > GI_C1_3",
            "depth": "1",
        },
    ]


def blank_row(
    fragment_id: str,
    resource_type: str = "page",
    text: str = "Students design software.",
) -> dict[str, str]:
    return {
        "fragment_id": fragment_id,
        "resource_id": "page:1",
        "course_id": "2",
        "course_shortname": "MVP-SW",
        "resource_type": resource_type,
        "activity_name": "Software Page",
        "resource_title": "Software Development",
        "fragment_text": text,
        "gold_competency_ids": "",
        "gold_evidence": "",
        "no_competency": "",
        "ambiguous": "",
        "ambiguity_reason": "",
        "comment": "",
        "annotator": "",
        "annotation_date": "",
    }


def test_blank_row_is_incomplete() -> None:
    assert is_row_complete(blank_row("page:1#f001")) is False


def test_resume_from_first_incomplete() -> None:
    complete = apply_human_decision(
        blank_row("page:1#f001"),
        annotator="Wail Ouaret",
        annotation_date="2026-09-18",
        competency_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous=False,
        ambiguity_reason="",
        evidence_quotes=[],
        comment="",
    )
    incomplete = blank_row("page:1#f002")
    later = blank_row("page:1#f003")
    rows = [complete, incomplete, later]

    assert first_incomplete_index(rows) == 1
    assert progress_counts(rows)["completed"] == 1
    assert progress_counts(rows)["remaining"] == 2


def test_none_choice_sets_no_competency() -> None:
    allowed = catalogue_id_set(sample_catalogue())
    ids, no_competency, errors = parse_competency_choice(
        "NONE",
        allowed,
    )
    row = apply_human_decision(
        blank_row("page:1#f001"),
        annotator="Wail Ouaret",
        annotation_date="2026-09-18",
        competency_ids=ids,
        no_competency=no_competency,
        ambiguous=False,
        ambiguity_reason="",
        evidence_quotes=[],
        comment="",
    )

    assert errors == []
    assert no_competency is True
    assert row["gold_competency_ids"] == ""
    assert row["no_competency"] == "true"
    assert is_row_complete(row) is True


def test_valid_and_multiple_ids_accepted() -> None:
    allowed = catalogue_id_set(sample_catalogue())
    ids, no_competency, errors = parse_competency_choice(
        "GI_C1_1; GI_C1_3",
        allowed,
    )

    assert errors == []
    assert no_competency is False
    assert ids == ["GI_C1_1", "GI_C1_3"]


def test_unknown_competency_rejected() -> None:
    allowed = catalogue_id_set(sample_catalogue())
    _ids, _no_competency, errors = parse_competency_choice(
        "INVENTED",
        allowed,
    )

    assert errors
    assert "Unknown competency IDs: INVENTED" in errors[0]


def test_duplicate_competency_rejected() -> None:
    allowed = catalogue_id_set(sample_catalogue())
    _ids, _no_competency, errors = parse_competency_choice(
        "GI_C1_1;GI_C1_1",
        allowed,
    )

    assert any("Duplicate competency IDs" in error for error in errors)


def test_exact_evidence_accepted() -> None:
    text = "Students design software."
    errors = validate_evidence_quotes(
        ["design software"],
        text,
    )

    assert errors == []


def test_non_exact_evidence_rejected() -> None:
    errors = validate_evidence_quotes(
        ["Learners create an architecture."],
        "Students design software.",
    )

    assert errors
    assert "exact contiguous substring" in errors[0]


def test_catalogue_is_hierarchical_and_unranked() -> None:
    rendered = format_catalogue(sample_catalogue())

    assert rendered.index("GI_C1") < rendered.index("GI_C1_1")
    assert "top-level" in rendered
    assert "child of GI_C1" in rendered
    assert "catalogue / hierarchy order" in rendered
    assert "likely" not in rendered.lower()
    assert "recommend" not in rendered.lower()


def test_page_and_quiz_guides_differ() -> None:
    page_guide = decision_guide("page")
    quiz_guide = decision_guide("quiz_question")

    assert "teaching or explaining" in page_guide
    assert "answer this question" in quiz_guide


def test_commands_are_recognized() -> None:
    assert parse_session_command(":q") == "quit"
    assert parse_session_command(" :S ") == "skip"
    assert parse_session_command("GI_C1_1") is None


def test_yes_no_parser() -> None:
    assert parse_yes_no("y") == (True, [])
    assert parse_yes_no("n") == (False, [])
    assert parse_yes_no("maybe")[0] is None


def test_invalid_date_rejected() -> None:
    errors = validate_session_identity(
        annotator="Wail Ouaret",
        annotation_date="18/09/2026",
    )

    assert any("YYYY-MM-DD" in error for error in errors)


def test_atomic_write_and_backup_use_temporary_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "manual_fragment_annotations.csv"
    backup_dir = tmp_path / "annotation_backups"
    rows = [
        blank_row("page:1#f001"),
        blank_row("page:1#f002"),
    ]
    write_csv(rows, source, ANNOTATION_COLUMNS)

    backup = create_timestamped_backup(
        source,
        backup_dir,
        moment=datetime(2026, 9, 18, 3, 0, tzinfo=timezone.utc),
    )
    updated = apply_human_decision(
        rows[0],
        annotator="Wail Ouaret",
        annotation_date="2026-09-18",
        competency_ids=["GI_C1_1"],
        no_competency=False,
        ambiguous=True,
        ambiguity_reason="Close child competencies.",
        evidence_quotes=["design software"],
        comment="Human decision only.",
    )
    rows[0] = updated
    atomic_write_annotations(rows, source)

    saved = read_csv(source)
    original_backup = read_csv(backup)

    assert backup.name.endswith("20260918T030000Z.csv")
    assert original_backup[0]["gold_competency_ids"] == ""
    assert saved[0]["gold_competency_ids"] == "GI_C1_1"
    assert saved[0]["no_competency"] == "false"
    assert saved[1]["gold_competency_ids"] == ""


def test_next_incomplete_skips_completed_rows() -> None:
    rows = [
        apply_human_decision(
            blank_row("page:1#f001"),
            annotator="Wail Ouaret",
            annotation_date="2026-09-18",
            competency_ids=["GI_C1_1"],
            no_competency=False,
            ambiguous=False,
            ambiguity_reason="",
            evidence_quotes=[],
            comment="",
        ),
        blank_row("page:1#f002"),
        apply_human_decision(
            blank_row("page:1#f003"),
            annotator="Wail Ouaret",
            annotation_date="2026-09-18",
            competency_ids=[],
            no_competency=True,
            ambiguous=False,
            ambiguity_reason="",
            evidence_quotes=[],
            comment="",
        ),
    ]

    assert next_incomplete_index(rows, 0) == 1
    assert next_incomplete_index(rows, 1) == 1


def test_helper_module_does_not_load_prediction_files() -> None:
    source = Path(
        "src/moodle_competency/annotation_session.py"
    ).read_text(encoding="utf-8")
    script = Path(
        "scripts/manual_annotate_fragments.py"
    ).read_text(encoding="utf-8")

    for name in (
        "bm25_candidates.jsonl",
        "llm_tasks.jsonl",
        "gemini_responses.jsonl",
        "gemini_validated.jsonl",
        "manual_moodle_links.csv",
    ):
        assert name not in source
        assert name not in script


def test_load_workspace_from_temporary_files_only(
    tmp_path: Path,
) -> None:
    annotations = tmp_path / "manual_fragment_annotations.csv"
    catalogue = tmp_path / "annotation_competency_catalogue.csv"
    write_csv(
        [blank_row("page:1#f001")],
        annotations,
        ANNOTATION_COLUMNS,
    )
    write_csv(
        sample_catalogue(),
        catalogue,
        [
            "idnumber",
            "shortname",
            "description",
            "parent_idnumber",
            "hierarchy_path",
            "depth",
        ],
    )

    rows, loaded_catalogue = load_annotation_workspace(
        annotations,
        catalogue,
    )

    assert len(rows) == 1
    assert len(loaded_catalogue) == 3
    assert rows[0]["gold_competency_ids"] == ""
