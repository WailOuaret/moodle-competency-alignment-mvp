"""Tests for constrained LLM-task generation."""

from moodle_competency.llm_tasks import (
    build_alignment_tasks,
    validate_alignment_tasks,
)


COMPETENCIES = [
    {
        "competency_id": index,
        "idnumber": f"C{index}",
        "shortname": f"Competency {index}",
        "description_text": (
            f"Description for competency {index}."
        ),
        "parent_idnumber": "",
        "parent_shortname": "",
        "hierarchy_idnumbers": [f"C{index}"],
        "hierarchy_labels": [
            f"Competency {index}"
        ],
        "depth": 0,
    }
    for index in range(1, 6)
]


CANDIDATE_SETS = [
    {
        "fragment_id": "page:1#f001",
        "resource_id": "page:1",
        "resource_type": "page",
        "fragment_type": "page_chunk",
        "course_id": 2,
        "course_shortname": "MVP-SW",
        "course_module_id": 5,
        "activity_id": 1,
        "activity_name": "Software Design",
        "title": "Architecture",
        "fragment_text": (
            "Students design a modular "
            "software architecture."
        ),
        "candidates": [
            {
                "rank": index,
                "idnumber": f"C{index}",
                "bm25_score": float(
                    10 - index
                ),
            }
            for index in range(1, 6)
        ],
    }
]


def test_build_alignment_task() -> None:
    tasks = build_alignment_tasks(
        candidate_sets=CANDIDATE_SETS,
        competencies=COMPETENCIES,
    )

    assert len(tasks) == 1

    task = tasks[0]

    assert task["fragment_id"] == (
        "page:1#f001"
    )

    assert task["allowed_idnumbers"] == [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
    ]

    assert len(task["candidates"]) == 5
    assert "exact, contiguous substring" in (
        task["prompt"]
    )
    assert "C1" in task["prompt"]


def test_alignment_task_validation() -> None:
    tasks = build_alignment_tasks(
        candidate_sets=CANDIDATE_SETS,
        competencies=COMPETENCIES,
    )

    validation = validate_alignment_tasks(
        candidate_sets=CANDIDATE_SETS,
        competencies=COMPETENCIES,
        tasks=tasks,
        expected_candidate_count=5,
    )

    assert validation["passed"] is True
    assert validation["alignment_tasks"] == 1
    assert (
        validation[
            "expected_candidates_per_task"
        ]
        == 5
    )


def test_task_allows_abstention() -> None:
    tasks = build_alignment_tasks(
        candidate_sets=CANDIDATE_SETS,
        competencies=COMPETENCIES,
    )

    instructions = tasks[0]["instructions"]

    assert (
        instructions["abstention_allowed"]
        is True
    )

    assert (
        instructions[
            "evidence_must_be_exact_substring"
        ]
        is True
    )
