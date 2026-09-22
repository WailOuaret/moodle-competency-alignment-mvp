"""Read-only PostgreSQL extraction through the Moodle Docker stack."""

from __future__ import annotations

import csv
import json
import shlex
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DatabaseExportSummary:
    """Summary of the exported Quiz-question dataset."""

    answer_rows: int
    unique_quizzes: int
    unique_questions: int
    questions_per_quiz: dict[str, int]
    question_types: dict[str, int]
    questions_with_empty_text: int
    questions_without_answers: int
    questions_without_correct_answer: int

    @property
    def passed(self) -> bool:
        return (
            self.answer_rows == 48
            and self.unique_quizzes == 2
            and self.unique_questions == 12
            and all(
                count == 6
                for count in self.questions_per_quiz.values()
            )
            and self.questions_with_empty_text == 0
            and self.questions_without_answers == 0
            and self.questions_without_correct_answer == 0
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["passed"] = self.passed
        return result


class DatabaseExportError(RuntimeError):
    """Raised when the PostgreSQL export cannot be completed."""


def run_sql_export(
    *,
    sql_path: Path,
    output_path: Path,
    error_log_path: Path,
    moodle_docker_dir: Path,
    moodle_env_script: Path,
) -> None:
    """Execute one read-only SQL export inside the Moodle DB container."""

    for required_path in (
        sql_path,
        moodle_docker_dir,
        moodle_env_script,
    ):
        if not required_path.exists():
            raise DatabaseExportError(
                f"Required path does not exist: {required_path}"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    error_log_path.parent.mkdir(parents=True, exist_ok=True)

    command = (
        f"source {shlex.quote(str(moodle_env_script))} && "
        f"cd {shlex.quote(str(moodle_docker_dir))} && "
        "./bin/moodle-docker-compose exec -T db sh -lc "
        "'psql -q -v ON_ERROR_STOP=1 "
        "-U \"${POSTGRES_USER:-moodle}\" "
        "-d \"${POSTGRES_DB:-moodle}\"'"
    )

    with (
        sql_path.open("r", encoding="utf-8") as sql_handle,
        output_path.open("w", encoding="utf-8", newline="") as output_handle,
        error_log_path.open("w", encoding="utf-8") as error_handle,
    ):
        result = subprocess.run(
            ["bash", "-lc", command],
            stdin=sql_handle,
            stdout=output_handle,
            stderr=error_handle,
            text=True,
            check=False,
        )

    if result.returncode != 0:
        error_text = error_log_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        raise DatabaseExportError(
            "PostgreSQL export failed with exit code "
            f"{result.returncode}. Error: "
            f"{error_text or 'No error message was returned.'}"
        )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise DatabaseExportError(
            f"The export produced no output: {output_path}"
        )


def validate_quiz_question_export(
    csv_path: Path,
) -> DatabaseExportSummary:
    """Validate Quiz questions, answers and correct-answer fractions."""

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Quiz-question CSV does not exist: {csv_path}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    questions: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    answers_per_question: defaultdict[
        tuple[str, str],
        int,
    ] = defaultdict(int)

    correct_answers_per_question: defaultdict[
        tuple[str, str],
        int,
    ] = defaultdict(int)

    for row in rows:
        key = (
            row["quiz_id"],
            row["question_id"],
        )

        questions.setdefault(key, row)

        if row.get("answer_id", "").strip():
            answers_per_question[key] += 1

            try:
                fraction = float(
                    row.get("answer_fraction", "0") or 0
                )
            except ValueError:
                fraction = 0.0

            if fraction > 0:
                correct_answers_per_question[key] += 1

    questions_per_quiz = Counter(
        row["quiz_name"]
        for row in questions.values()
    )

    question_types = Counter(
        row["question_type"]
        for row in questions.values()
    )

    empty_text = sum(
        not row.get("question_text", "").strip()
        for row in questions.values()
    )

    without_answers = sum(
        answers_per_question[key] == 0
        for key in questions
    )

    without_correct_answer = sum(
        correct_answers_per_question[key] == 0
        for key in questions
    )

    return DatabaseExportSummary(
        answer_rows=len(rows),
        unique_quizzes=len(questions_per_quiz),
        unique_questions=len(questions),
        questions_per_quiz=dict(questions_per_quiz),
        question_types=dict(question_types),
        questions_with_empty_text=empty_text,
        questions_without_answers=without_answers,
        questions_without_correct_answer=without_correct_answer,
    )


def write_summary(
    summary: DatabaseExportSummary,
    output_path: Path,
) -> Path:
    """Save a formatted extraction summary."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            summary.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path.resolve()
