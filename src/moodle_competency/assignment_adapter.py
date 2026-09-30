"""Moodle Assignment → normalized resource record.

Isolated adapter. Not called by the frozen extraction scripts. A live Moodle
Assignment experiment has not been run.
"""

from __future__ import annotations

from typing import Any, Mapping

from moodle_competency.html_clean import combine_text, html_to_text, normalize_whitespace
from moodle_competency.resource_contract import assert_resource_record


def normalize_assignment(source: Mapping[str, Any]) -> dict[str, Any]:
    """Map one Assignment payload into the connector contract.

    Expected keys (Moodle ``mod_assign_get_assignments`` shape, or a test
    fixture with the same names):

    - ``id`` or ``assignment_id``
    - ``name``
    - ``intro`` (HTML) and optional ``activity`` (HTML)
    - ``course`` or ``course_id``
    - optional course and section provenance
    """

    assignment_id = source.get("assignment_id", source.get("id"))
    if assignment_id is None or str(assignment_id).strip() == "":
        raise ValueError("assignment id is required")

    title = normalize_whitespace(source.get("name") or source.get("title"))
    intro = html_to_text(source.get("intro"))
    activity = html_to_text(source.get("activity"))
    text = combine_text(intro, activity)
    course_id = source.get("course_id", source.get("course"))

    record = {
        "resource_id": f"assignment:{assignment_id}",
        "resource_type": "assignment",
        "source_extraction": "moodle_assignment_adapter",
        "course_id": course_id,
        "course_shortname": normalize_whitespace(
            source.get("course_shortname")
        ),
        "course_fullname": normalize_whitespace(
            source.get("course_fullname")
        ),
        "course_module_id": source.get("coursemodule", source.get("cmid")),
        "section_id": source.get("section_id"),
        "section_number": source.get("section_number"),
        "section_name": normalize_whitespace(source.get("section_name")),
        "activity_id": assignment_id,
        "activity_name": title,
        "source_item_id": assignment_id,
        "title": title or f"Assignment {assignment_id}",
        "text": text,
        "search_text": combine_text(title, text),
        "metadata": {
            "adapter": "assignment",
            "implemented": True,
            "evaluated_on_frozen_corpus": False,
            "intro_format": source.get("introformat"),
        },
    }
    assert_resource_record(record)
    return record
