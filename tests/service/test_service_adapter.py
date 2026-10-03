"""Unit tests for the adapter's normalisation and catalogue handling."""

from __future__ import annotations

import copy

from moodle_competency.resource_contract import validate_resource_record
from moodle_competency.retrieval import build_competency_document, tokenize

from service.alignment_adapter import (
    catalogue_hash,
    normalize_paragraphs,
    prepare_catalogue,
    prepare_resource,
)
from service.schemas import CompetencyIn, ResourceIn
from service_support import CATALOGUE, PAGE_TEXT


def competencies(items=CATALOGUE) -> list[CompetencyIn]:
    return [CompetencyIn(**copy.deepcopy(item)) for item in items]


def resource(**changes) -> ResourceIn:
    values = {
        "resource_id": "moodle:page:7",
        "resource_type": "page",
        "title": "A Page",
        "text": PAGE_TEXT,
    }
    values.update(changes)
    return ResourceIn(**values)


# --------------------------------------------------------------------------- #
# Text normalisation
# --------------------------------------------------------------------------- #


def test_paragraph_breaks_survive_normalisation() -> None:
    assert normalize_paragraphs("First.\n\nSecond.\n  \n\nThird.") == (
        "First.\n\nSecond.\n\nThird."
    )


def test_whitespace_inside_a_paragraph_is_collapsed() -> None:
    assert normalize_paragraphs("One   two\nthree\t four.") == "One two three four."


def test_windows_line_endings_keep_their_paragraphs() -> None:
    assert normalize_paragraphs("First.\r\n\r\nSecond.") == "First.\n\nSecond."


def test_empty_paragraphs_are_dropped() -> None:
    assert normalize_paragraphs("\n\n  \n\nOnly.\n\n") == "Only."


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #


def test_catalogue_enrichment_derives_the_hierarchy_fields() -> None:
    records = {item["idnumber"]: item for item in prepare_catalogue(competencies()).records}

    root = records["SE-1"]
    child = records["SE-1.1"]

    assert root["depth"] == 0
    assert root["parent_idnumber"] == ""
    assert root["parent_shortname"] == ""
    assert root["hierarchy_idnumbers"] == ["SE-1"]
    assert child["depth"] == 1
    assert child["parent_idnumber"] == "SE-1"
    assert child["parent_shortname"] == "Software engineering"
    assert child["hierarchy_idnumbers"] == ["SE-1", "SE-1.1"]
    assert child["hierarchy_labels"] == ["Software engineering", "Software testing"]
    assert "Software engineering" in child["search_text"]
    assert child["framework_shortname"] == "Demo framework"


def test_every_prepared_competency_can_be_retrieved() -> None:
    for record in prepare_catalogue(competencies()).records:
        assert tokenize(build_competency_document(record))


def test_catalogue_hash_ignores_the_order_moodle_listed_competencies() -> None:
    forward = prepare_catalogue(competencies())
    backward = prepare_catalogue(competencies(list(reversed(CATALOGUE))))

    assert forward.content_hash == backward.content_hash
    assert forward.content_hash.startswith("sha256:")


def test_catalogue_hash_changes_when_any_field_changes() -> None:
    baseline = prepare_catalogue(competencies()).content_hash

    for field, value in (
        ("shortname", "Renamed"),
        ("description_text", "A different description."),
        ("parent_idnumber", "SE-1.2"),
    ):
        changed = copy.deepcopy(CATALOGUE)
        changed[1][field] = value
        assert prepare_catalogue(competencies(changed)).content_hash != baseline


def test_catalogue_hash_is_computed_over_normalised_text() -> None:
    padded = copy.deepcopy(CATALOGUE)
    padded[0]["shortname"] = "  Software   engineering "

    assert (
        prepare_catalogue(competencies(padded)).content_hash
        == prepare_catalogue(competencies()).content_hash
    )


def test_hash_function_depends_only_on_the_listed_fields() -> None:
    record = {
        "idnumber": "A",
        "shortname": "a",
        "description_text": "d",
        "parent_idnumber": "",
        "framework_idnumber": "F",
        "framework_shortname": "",
    }

    assert catalogue_hash([record]) == catalogue_hash([{**record, "ignored": "x"}])


# --------------------------------------------------------------------------- #
# Resource
# --------------------------------------------------------------------------- #


def test_resource_record_satisfies_the_connector_contract() -> None:
    record = prepare_resource(resource())

    assert validate_resource_record(record) == []
    assert record["resource_id"] == "moodle:page:7"
    assert record["runtime_resource_id"] == "moodle:page:7"
    assert record["resource_type"] == "page"


def test_resource_context_fields_are_never_none() -> None:
    record = prepare_resource(resource())

    for field in ("course_shortname", "course_fullname", "section_name", "activity_name"):
        assert isinstance(record[field], str)

    # The engine would print the word "None" into the model prompt otherwise.
    assert "None" not in {record[field] for field in ("course_shortname", "section_name")}


def test_activity_name_defaults_to_the_title() -> None:
    assert prepare_resource(resource())["activity_name"] == "A Page"
    assert prepare_resource(resource(activity_name="Lesson 3"))["activity_name"] == "Lesson 3"


def test_search_text_defaults_to_title_then_text() -> None:
    record = prepare_resource(resource())

    assert record["search_text"].startswith("A Page")
    assert "Software testing verifies requirements." in record["search_text"]


def test_supplied_search_text_is_normalised_and_kept() -> None:
    record = prepare_resource(resource(search_text="  Custom   query\ntext "))

    assert record["search_text"] == "Custom query text"


def test_resource_hashes_describe_raw_and_normalised_text() -> None:
    first = prepare_resource(resource(text="Same words.\n\nSecond paragraph."))
    second = prepare_resource(resource(text="Same   words.\n\n\nSecond paragraph."))

    assert first["normalized_text_hash"] == second["normalized_text_hash"]
    assert first["raw_text_hash"] != second["raw_text_hash"]
