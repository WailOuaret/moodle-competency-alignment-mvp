"""Tests for normalized Moodle resources."""

from moodle_competency.normalization import (
    normalize_pages,
    normalize_quiz_questions,
)


COURSES = {
    2: {
        "id": 2,
        "shortname": "MVP-SW",
        "fullname": "Software Engineering",
    }
}


MODULES_BY_CMID = {
    11: {
        "course_module_id": 11,
        "section_id": 5,
        "section_number": 4,
        "section_name": "Assessment",
        "completion": 2,
    }
}


MODULES_BY_INSTANCE = {
    (2, "page", 4): {
        "course_module_id": 10,
        "section_id": 4,
        "section_number": 3,
        "section_name": "Architecture",
        "completion": 2,
    },
    (2, "quiz", 1): {
        "course_module_id": 11,
        "section_id": 5,
        "section_number": 4,
        "section_name": "Assessment",
        "completion": 2,
    },
}


def test_normalize_page() -> None:
    resources = normalize_pages(
        pages_response={
            "pages": [
                {
                    "id": 4,
                    "course": 2,
                    "name": "Distributed Systems",
                    "intro": "<p>Introduction</p>",
                    "content": (
                        "<p>Nodes communicate over a network.</p>"
                    ),
                }
            ]
        },
        courses=COURSES,
        modules_by_cmid=MODULES_BY_CMID,
        modules_by_instance=MODULES_BY_INSTANCE,
    )

    assert len(resources) == 1
    assert resources[0]["resource_id"] == "page:4"
    assert resources[0]["course_module_id"] == 10
    assert "Nodes communicate" in resources[0]["text"]


def test_normalize_quiz_question() -> None:
    rows = [
        {
            "course_id": "2",
            "quiz_id": "1",
            "quiz_name": "Software Quiz",
            "question_id": "20",
            "question_name": "Architecture question",
            "question_type": "multichoice",
            "question_text": (
                "<p>Which pattern separates concerns?</p>"
            ),
            "answer_id": "101",
            "answer_text": "MVC",
            "answer_fraction": "1.0",
            "slot": "1",
        },
        {
            "course_id": "2",
            "quiz_id": "1",
            "quiz_name": "Software Quiz",
            "question_id": "20",
            "question_name": "Architecture question",
            "question_type": "multichoice",
            "question_text": (
                "<p>Which pattern separates concerns?</p>"
            ),
            "answer_id": "102",
            "answer_text": "Random duplication",
            "answer_fraction": "0.0",
            "slot": "1",
        },
    ]

    resources = normalize_quiz_questions(
        rows=rows,
        courses=COURSES,
        modules_by_cmid=MODULES_BY_CMID,
        modules_by_instance=MODULES_BY_INSTANCE,
    )

    question = resources[0]

    assert question["resource_type"] == "quiz_question"
    assert question["course_module_id"] == 11
    assert question["metadata"]["answer_count"] == 2
    assert question["metadata"]["correct_answer_count"] == 1
    assert "MVC" in question["search_text"]
