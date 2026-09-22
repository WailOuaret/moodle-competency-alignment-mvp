"""Tests for blinded fragment-level manual annotation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moodle_competency.annotation import (
    ANNOTATION_COLUMNS,
    HUMAN_FIELDS,
    build_blank_annotation_records,
    build_competency_catalogue,
    generate_manual_annotation_outputs,
    load_jsonl,
    parse_competency_ids,
    parse_evidence,
    read_csv,
    validate_annotation_dataset,
    write_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_FRAGMENTS = (
    PROJECT_ROOT / "data" / "processed" / "fragments.jsonl"
)
REAL_RESOURCES = (
    PROJECT_ROOT / "data" / "processed" / "resources.jsonl"
)
REAL_COMPETENCIES = (
    PROJECT_ROOT / "data" / "processed" / "competencies.jsonl"
)


def sample_competencies() -> list[dict[str, object]]:
    return [
        {
            "idnumber": "GI_C1",
            "shortname": "Design software",
            "description_text": "Design and develop software.",
            "parent_idnumber": "",
            "hierarchy_idnumbers": ["GI_C1"],
            "depth": 0,
        },
        {
            "idnumber": "GI_C1_1",
            "shortname": "Software development",
            "description_text": "Design, paradigms, deployment.",
            "parent_idnumber": "GI_C1",
            "hierarchy_idnumbers": ["GI_C1", "GI_C1_1"],
            "depth": 1,
        },
        {
            "idnumber": "GI_C1_3",
            "shortname": "HCI and UX",
            "description_text": "Interfaces and accessibility.",
            "parent_idnumber": "GI_C1",
            "hierarchy_idnumbers": ["GI_C1", "GI_C1_3"],
            "depth": 1,
        },
    ]


def sample_resources() -> list[dict[str, object]]:
    return [
        {
            "resource_id": "page:1",
            "resource_type": "page",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "activity_name": "Software Page",
            "title": "Software Development",
        },
        {
            "resource_id": "quiz_question:1:1",
            "resource_type": "quiz_question",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "activity_name": "Software Quiz",
            "title": "SW_Q1_User_Requirements",
        },
    ]


def sample_fragments() -> list[dict[str, object]]:
    return [
        {
            "fragment_id": "page:1#f001",
            "resource_id": "page:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "page",
            "activity_name": "Software Page",
            "title": "Software Development",
            "text": (
                "Students design software and consider "
                "user requirements during deployment."
            ),
        },
        {
            "fragment_id": "quiz_question:1:1#f001",
            "resource_id": "quiz_question:1:1",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "resource_type": "quiz_question",
            "activity_name": "Software Quiz",
            "title": "SW_Q1_User_Requirements",
            "text": (
                "Which activity captures user requirements "
                "before implementation?"
            ),
        },
    ]


def write_jsonl(records: list[dict[str, object]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    return path


def write_fixture_sources(directory: Path) -> dict[str, Path]:
    paths = {
        "fragments": directory / "fragments.jsonl",
        "resources": directory / "resources.jsonl",
        "competencies": directory / "competencies.jsonl",
        "annotations": directory / "manual_fragment_annotations.csv",
        "catalogue": directory / "annotation_competency_catalogue.csv",
        "manifest": directory / "manual_annotation_manifest.json",
    }
    write_jsonl(sample_fragments(), paths["fragments"])
    write_jsonl(sample_resources(), paths["resources"])
    write_jsonl(sample_competencies(), paths["competencies"])
    return paths


def generate_from_fixtures(directory: Path) -> dict:
    paths = write_fixture_sources(directory)
    return generate_manual_annotation_outputs(
        fragments_path=paths["fragments"],
        resources_path=paths["resources"],
        competencies_path=paths["competencies"],
        annotations_path=paths["annotations"],
        catalogue_path=paths["catalogue"],
        manifest_path=paths["manifest"],
    )


def blank_rows() -> list[dict[str, str]]:
    return build_blank_annotation_records(
        sample_fragments(),
        sample_resources(),
    )


def catalogue_rows() -> list[dict[str, str]]:
    return build_competency_catalogue(sample_competencies())


def filled_row(
    row: dict[str, str],
    **updates: str,
) -> dict[str, str]:
    completed = dict(row)
    completed.update(
        {
            "no_competency": "false",
            "ambiguous": "false",
            "annotator": "Wail Ouaret",
            "annotation_date": "2026-09-18",
        }
    )
    completed.update(updates)
    return completed


def validate_rows(
    rows: list[dict[str, str]],
    mode: str,
    catalogue: list[dict[str, str]] | None = None,
) -> dict:
    return validate_annotation_dataset(
        mode=mode,
        annotation_rows=rows,
        catalogue_rows=catalogue or catalogue_rows(),
        fragments=sample_fragments(),
        resources=sample_resources(),
        competencies=sample_competencies(),
    )


def test_successful_blank_template_generation(
    tmp_path: Path,
) -> None:
    generated = generate_from_fixtures(tmp_path)
    rows = generated["annotations"]

    assert len(rows) == 2
    assert all(
        not rows[0][field]
        for field in HUMAN_FIELDS
    )
    assert rows[0]["fragment_id"] == "page:1#f001"
    assert rows[0]["resource_title"] == "Software Development"
    assert "user requirements" in rows[0]["fragment_text"]


def test_exactly_one_row_per_source_fragment() -> None:
    rows = blank_rows()
    fragment_ids = [row["fragment_id"] for row in rows]
    source_ids = [
        str(fragment["fragment_id"])
        for fragment in sample_fragments()
    ]

    assert fragment_ids == source_ids
    assert len(set(fragment_ids)) == len(fragment_ids)


def test_real_dataset_has_35_blank_fragment_rows(
    tmp_path: Path,
) -> None:
    generated = generate_manual_annotation_outputs(
        fragments_path=REAL_FRAGMENTS,
        resources_path=REAL_RESOURCES,
        competencies_path=REAL_COMPETENCIES,
        annotations_path=tmp_path / "annotations.csv",
        catalogue_path=tmp_path / "catalogue.csv",
        manifest_path=tmp_path / "manifest.json",
    )
    rows = generated["annotations"]

    assert len(rows) == 35
    assert len({row["fragment_id"] for row in rows}) == 35
    assert all(
        not row[field]
        for row in rows
        for field in HUMAN_FIELDS
    )


def test_real_catalogue_has_13_competencies(
    tmp_path: Path,
) -> None:
    generated = generate_manual_annotation_outputs(
        fragments_path=REAL_FRAGMENTS,
        resources_path=REAL_RESOURCES,
        competencies_path=REAL_COMPETENCIES,
        annotations_path=tmp_path / "annotations.csv",
        catalogue_path=tmp_path / "catalogue.csv",
        manifest_path=tmp_path / "manifest.json",
    )
    catalogue = generated["catalogue"]
    idnumbers = [row["idnumber"] for row in catalogue]

    assert len(catalogue) == 13
    assert "GI_C1" in idnumbers
    assert "GI_C3_3" in idnumbers
    assert catalogue[1]["parent_idnumber"] == "GI_C1"
    assert "GI_C1 > GI_C1_1" in catalogue[1]["hierarchy_path"]


def test_no_annotation_label_automatically_filled() -> None:
    for row in blank_rows():
        assert row["gold_competency_ids"] == ""
        assert row["gold_evidence"] == ""
        assert row["no_competency"] == ""
        assert row["ambiguous"] == ""


def test_duplicate_fragment_rejected() -> None:
    rows = blank_rows()
    rows.append(dict(rows[0]))

    summary = validate_rows(rows, "template")

    assert summary["passed"] is False
    assert summary["duplicate_fragments"] == [
        "page:1#f001"
    ]


def test_unknown_fragment_rejected() -> None:
    rows = blank_rows()
    rows[0]["fragment_id"] = "page:999#f001"

    summary = validate_rows(rows, "template")

    assert summary["passed"] is False
    assert "page:999#f001" in summary["unknown_fragments"]


def test_missing_fragment_rejected() -> None:
    rows = blank_rows()[:1]

    summary = validate_rows(rows, "template")

    assert summary["passed"] is False
    assert summary["missing_fragments"] == [
        "quiz_question:1:1#f001"
    ]


def test_fragment_text_mismatch_rejected() -> None:
    rows = blank_rows()
    rows[0]["fragment_text"] = "Paraphrased fragment."

    summary = validate_rows(rows, "template")

    assert summary["passed"] is False
    assert summary["source_text_mismatches"] == [
        "page:1#f001"
    ]


def test_unknown_competency_id_rejected() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="INVENTED",
    )
    rows[1] = filled_row(
        rows[1],
        gold_competency_ids="GI_C1_1",
    )

    summary = validate_rows(rows, "final")

    assert summary["passed"] is False
    assert any(
        "unknown competency IDs: INVENTED" in error
        for error in summary["errors"]
    )


def test_one_valid_competency_accepted() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1",
    )
    rows[1] = filled_row(
        rows[1],
        no_competency="true",
        gold_competency_ids="",
    )

    summary = validate_rows(rows, "final")

    assert summary["passed"] is True


def test_multiple_valid_competencies_accepted() -> None:
    ids, errors = parse_competency_ids("GI_C1_1; GI_C1_3")
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1;GI_C1_3",
    )
    rows[1] = filled_row(
        rows[1],
        no_competency="true",
    )

    summary = validate_rows(rows, "final")

    assert errors == []
    assert ids == ["GI_C1_1", "GI_C1_3"]
    assert summary["passed"] is True


def test_duplicate_competency_id_rejected() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1;GI_C1_1",
    )
    rows[1] = filled_row(
        rows[1],
        no_competency="true",
    )

    summary = validate_rows(rows, "final")

    assert summary["passed"] is False
    assert any(
        "Duplicate competency IDs: GI_C1_1" in error
        for error in summary["errors"]
    )


def test_no_competency_with_selected_id_rejected() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        no_competency="true",
        gold_competency_ids="GI_C1_1",
    )
    rows[1] = filled_row(
        rows[1],
        no_competency="true",
    )

    summary = validate_rows(rows, "final")

    assert summary["passed"] is False
    assert any(
        "cannot coexist with gold_competency_ids" in error
        for error in summary["errors"]
    )


def test_valid_no_competency_decision_accepted() -> None:
    rows = [
        filled_row(row, no_competency="true")
        for row in blank_rows()
    ]

    summary = validate_rows(rows, "final")

    assert summary["passed"] is True
    assert summary["incomplete_rows"] == []


def test_incomplete_row_rejected_in_final_mode() -> None:
    summary = validate_rows(blank_rows(), "final")

    assert summary["passed"] is False
    assert "page:1#f001" in summary["incomplete_rows"]
    assert any(
        "incomplete decision" in error
        for error in summary["errors"]
    )


def test_exact_evidence_accepted() -> None:
    rows = blank_rows()
    quote = "design software"
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1",
        gold_evidence=json.dumps([quote]),
    )
    rows[1] = filled_row(rows[1], no_competency="true")

    summary = validate_rows(rows, "final")

    assert quote in rows[0]["fragment_text"]
    assert summary["passed"] is True


def test_non_exact_evidence_rejected() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1",
        gold_evidence=json.dumps(
            ["Learners create an architecture."]
        ),
    )
    rows[1] = filled_row(rows[1], no_competency="true")

    summary = validate_rows(rows, "final")

    assert summary["passed"] is False
    assert any(
        "not an exact contiguous substring" in error
        for error in summary["errors"]
    )


def test_malformed_evidence_json_rejected() -> None:
    quotes, errors = parse_evidence("{not-an-array}")
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1",
        gold_evidence="not-json",
    )
    rows[1] = filled_row(rows[1], no_competency="true")

    summary = validate_rows(rows, "final")

    assert quotes == []
    assert errors
    assert summary["passed"] is False
    assert any(
        "JSON array" in error
        for error in summary["errors"]
    )


def test_ambiguous_true_with_reason_accepted() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1;GI_C1_3",
        ambiguous="true",
        ambiguity_reason=(
            "The fragment could reasonably correspond "
            "to both GI_C1_1 and GI_C1_3."
        ),
    )
    rows[1] = filled_row(rows[1], no_competency="true")

    summary = validate_rows(rows, "final")

    assert summary["passed"] is True


def test_ambiguous_true_without_reason_rejected() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1",
        ambiguous="true",
        ambiguity_reason="",
    )
    rows[1] = filled_row(rows[1], no_competency="true")

    summary = validate_rows(rows, "final")

    assert summary["passed"] is False
    assert any(
        "requires ambiguity_reason" in error
        for error in summary["errors"]
    )


def test_invalid_annotation_date_rejected() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1",
        annotation_date="18/09/2026",
    )
    rows[1] = filled_row(rows[1], no_competency="true")

    summary = validate_rows(rows, "final")

    assert summary["passed"] is False
    assert any(
        "YYYY-MM-DD" in error
        for error in summary["errors"]
    )


def test_complete_valid_final_annotation_accepted() -> None:
    rows = blank_rows()
    rows[0] = filled_row(
        rows[0],
        gold_competency_ids="GI_C1_1;GI_C1_3",
        gold_evidence=json.dumps(
            [
                "design software",
                "user requirements",
            ]
        ),
        comment="Clear software-development evidence.",
    )
    rows[1] = filled_row(
        rows[1],
        no_competency="true",
        comment="Question stem is too generic.",
    )

    summary = validate_rows(rows, "final")

    assert summary["passed"] is True
    assert summary["incomplete_rows"] == []


def test_template_mode_allows_blank_human_fields() -> None:
    summary = validate_rows(blank_rows(), "template")

    assert summary["passed"] is True
    assert summary["source_fragments"] == 2
    assert summary["annotation_rows"] == 2


def test_generator_works_without_bm25_or_gemini_files(
    tmp_path: Path,
) -> None:
    assert not (tmp_path / "bm25_candidates.jsonl").exists()
    assert not (tmp_path / "llm_tasks.jsonl").exists()
    assert not (tmp_path / "gemini_responses.jsonl").exists()
    assert not (tmp_path / "gemini_validated.jsonl").exists()

    generated = generate_from_fixtures(tmp_path)

    assert generated["manifest"]["blinding_policy"][
        "reads_bm25_candidates"
    ] is False
    assert generated["manifest"]["blinding_policy"][
        "reads_gemini_predictions"
    ] is False
    assert generated["manifest"]["blinding_policy"][
        "reads_llm_tasks"
    ] is False
    assert len(generated["annotations"]) == 2


def test_generator_ignores_moodle_activity_links(
    tmp_path: Path,
) -> None:
    write_csv(
        [
            {
                "course": "MVP-SW",
                "activity_or_question": "Software Page",
                "competency_ids": "GI_C1_1;GI_C1_3",
            }
        ],
        tmp_path / "manual_moodle_links.csv",
        [
            "course",
            "activity_or_question",
            "competency_ids",
        ],
    )

    generated = generate_from_fixtures(tmp_path)

    assert all(
        row["gold_competency_ids"] == ""
        for row in generated["annotations"]
    )
    assert generated["manifest"]["blinding_policy"][
        "uses_moodle_activity_links_as_fragment_gold"
    ] is False


def test_generator_rejects_forbidden_source_filename(
    tmp_path: Path,
) -> None:
    paths = write_fixture_sources(tmp_path)
    forbidden = tmp_path / "bm25_candidates.jsonl"
    forbidden.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="cannot read bm25_candidates.jsonl",
    ):
        generate_manual_annotation_outputs(
            fragments_path=forbidden,
            resources_path=paths["resources"],
            competencies_path=paths["competencies"],
            annotations_path=paths["annotations"],
            catalogue_path=paths["catalogue"],
            manifest_path=paths["manifest"],
        )


def test_blank_template_csv_uses_expected_columns(
    tmp_path: Path,
) -> None:
    generate_from_fixtures(tmp_path)
    rows = read_csv(
        tmp_path / "manual_fragment_annotations.csv"
    )

    assert list(rows[0].keys())[:8] == list(
        ANNOTATION_COLUMNS[:8]
    )
    assert set(HUMAN_FIELDS).issubset(rows[0].keys())


def test_refuses_to_overwrite_filled_annotations(
    tmp_path: Path,
) -> None:
    generated = generate_from_fixtures(tmp_path)
    filled = generated["annotations"]
    filled[0]["gold_competency_ids"] = "GI_C1_1"
    write_csv(
        filled,
        tmp_path / "manual_fragment_annotations.csv",
        ANNOTATION_COLUMNS,
    )

    with pytest.raises(
        ValueError,
        match="Refusing to overwrite filled annotations",
    ):
        generate_from_fixtures(tmp_path)
