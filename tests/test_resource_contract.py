"""Connector contract and assignment adapter. No frozen files."""

from moodle_competency.assignment_adapter import normalize_assignment
from moodle_competency.fragmentation import create_fragments
from moodle_competency.resource_contract import (
    validate_competency_record,
    validate_resource_record,
)


def test_resource_contract_requires_identity_and_text() -> None:
    errors = validate_resource_record({"title": "Only a title"})
    assert any("resource_id" in error for error in errors)
    assert any("text" in error for error in errors)
    assert validate_resource_record(
        {
            "resource_id": "page:1",
            "resource_type": "page",
            "title": "HCI",
            "text": "User-centred design.",
        }
    ) == []


def test_competency_contract_rejects_self_parent() -> None:
    errors = validate_competency_record(
        {
            "idnumber": "X1",
            "shortname": "Design",
            "description_text": "Design software.",
            "parent_idnumber": "X1",
        }
    )
    assert errors


def test_assignment_adapter_enters_existing_fragmenter() -> None:
    record = normalize_assignment(
        {
            "id": 44,
            "course": 3,
            "course_shortname": "MVP-DATA",
            "name": "Ontology exercise",
            "intro": "<p>Represent courses and competencies as an ontology.</p>",
            "section_name": "Knowledge",
        }
    )
    assert record["resource_type"] == "assignment"
    assert record["resource_id"] == "assignment:44"
    assert "ontology" in record["text"].casefold()
    fragments = create_fragments([record])
    assert len(fragments) == 1
    assert fragments[0]["fragment_type"] == "resource_chunk"
    assert fragments[0]["resource_id"] == "assignment:44"
