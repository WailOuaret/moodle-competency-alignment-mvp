"""Tests for Moodle Quiz-question SQL export validation."""

from __future__ import annotations

import csv
from pathlib import Path

from moodle_competency.db_export import (
    validate_quiz_question_export,
)


def create_test_csv(path: Path) -> None:
    fieldnames = [
        "quiz_id",
        "quiz_name",
        "question_id",
        "question_name",
        "question_type",
        "question_text",
        "answer_id",
        "answer_fraction",
    ]

    rows = []

    for quiz_id in (1, 2):
        for question_number in range(1, 7):
            question_id = (
                quiz_id * 100 + question_number
            )

            for answer_number in range(1, 5):
                rows.append({
                    "quiz_id": str(quiz_id),
                    "quiz_name": f"Quiz {quiz_id}",
                    "question_id": str(question_id),
                    "question_name": (
                        f"Q{quiz_id}_{question_number}"
                    ),
                    "question_type": "multichoice",
                    "question_text": (
                        f"Question {question_number}"
                    ),
                    "answer_id": str(
                        question_id * 10 + answer_number
                    ),
                    "answer_fraction": (
                        "1.0"
                        if answer_number == 1
                        else "0.0"
                    ),
                })

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def test_valid_quiz_question_export(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "questions.csv"
    create_test_csv(csv_path)

    summary = validate_quiz_question_export(
        csv_path
    )

    assert summary.answer_rows == 48
    assert summary.unique_quizzes == 2
    assert summary.unique_questions == 12
    assert summary.question_types == {
        "multichoice": 12
    }
    assert summary.passed is True
