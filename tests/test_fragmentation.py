"""Tests for pedagogical resource fragmentation."""

from moodle_competency.fragmentation import (
    chunk_text,
    create_fragments,
    validate_fragments,
)


def test_long_text_is_split_under_limit() -> None:
    text = " ".join(
        [
            (
                "This sentence explains software "
                "architecture and system design."
            )
            for _ in range(20)
        ]
    )

    chunks = chunk_text(
        text,
        max_chars=220,
    )

    assert len(chunks) > 1
    assert all(
        len(chunk) <= 220
        for chunk in chunks
    )


def test_quiz_question_remains_one_fragment() -> None:
    resources = [
        {
            "resource_id": "quiz_question:1:20",
            "resource_type": "quiz_question",
            "course_id": 2,
            "course_shortname": "MVP-SW",
            "course_fullname": "Software Engineering",
            "course_module_id": 11,
            "activity_id": 1,
            "activity_name": "Software Quiz",
            "source_item_id": 20,
            "title": "Architecture question",
            "text": "Which pattern separates concerns?",
            "search_text": (
                "Architecture question\n\n"
                "Which pattern separates concerns?\n\n"
                "Answer options: MVC | Duplication"
            ),
            "metadata": {},
        }
    ]

    fragments = create_fragments(resources)

    assert len(fragments) == 1
    assert (
        fragments[0]["fragment_type"]
        == "quiz_question"
    )
    assert (
        fragments[0]["fragment_id"]
        == "quiz_question:1:20#f001"
    )
    assert "MVC" in fragments[0]["text"]


def test_fragment_validation_detects_full_coverage() -> None:
    resources = []

    for index in range(1, 9):
        resources.append(
            {
                "resource_id": f"page:{index}",
                "resource_type": "page",
                "course_shortname": (
                    "MVP-SW"
                    if index <= 4
                    else "MVP-DATA"
                ),
                "title": f"Page {index}",
                "text": (
                    "This is a complete Page description "
                    "used for competency alignment."
                ),
                "metadata": {},
            }
        )

    for index in range(1, 13):
        resources.append(
            {
                "resource_id": (
                    f"quiz_question:1:{index}"
                ),
                "resource_type": "quiz_question",
                "course_shortname": (
                    "MVP-SW"
                    if index <= 6
                    else "MVP-DATA"
                ),
                "title": f"Question {index}",
                "text": (
                    "Which concept correctly answers "
                    "this question?"
                ),
                "search_text": (
                    "Which concept correctly answers "
                    "this question? Answer options: "
                    "A | B | C | D"
                ),
                "metadata": {},
            }
        )

    fragments = create_fragments(
        resources,
        max_page_chars=900,
    )

    validation = validate_fragments(
        resources=resources,
        fragments=fragments,
        max_page_chars=900,
    )

    assert validation["passed"] is True
    assert validation["source_resources"] == 20
    assert validation["represented_resources"] == 20
    assert validation["fragments_by_type"][
        "quiz_question"
    ] == 12
