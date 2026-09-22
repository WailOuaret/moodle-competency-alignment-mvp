"""Export Moodle Quiz questions through read-only PostgreSQL access."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from moodle_competency.db_export import (
    DatabaseExportError,
    run_sql_export,
    validate_quiz_question_export,
    write_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export Quiz questions and answers from the local "
            "Moodle PostgreSQL database."
        )
    )

    parser.add_argument(
        "--moodle-docker-dir",
        type=Path,
        default=Path.home() / "moodle-dev" / "moodle-docker",
    )

    parser.add_argument(
        "--moodle-env-script",
        type=Path,
        default=Path.home() / "moodle-dev" / "moodle-env.sh",
    )

    parser.add_argument(
        "--sql-file",
        type=Path,
        default=PROJECT_ROOT / "sql" / "export_quiz_questions.sql",
    )

    parser.add_argument(
        "--output-file",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "raw"
            / "sql"
            / "quiz_questions_answers.csv"
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    error_log = (
        PROJECT_ROOT
        / "reports"
        / "logs"
        / "quiz_question_export_error.log"
    )

    summary_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "sql"
        / "extraction_manifest.json"
    )

    try:
        run_sql_export(
            sql_path=arguments.sql_file.resolve(),
            output_path=arguments.output_file.resolve(),
            error_log_path=error_log.resolve(),
            moodle_docker_dir=arguments.moodle_docker_dir.resolve(),
            moodle_env_script=arguments.moodle_env_script.resolve(),
        )

        summary = validate_quiz_question_export(
            arguments.output_file.resolve()
        )

        write_summary(
            summary,
            summary_path,
        )

    except (
        DatabaseExportError,
        FileNotFoundError,
        KeyError,
        ValueError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("=== MOODLE SQL EXTRACTION ===")
    print(f"Answer rows: {summary.answer_rows}")
    print(f"Unique quizzes: {summary.unique_quizzes}")
    print(f"Unique questions: {summary.unique_questions}")

    print("\nQuestions per quiz:")
    for quiz_name, count in sorted(
        summary.questions_per_quiz.items()
    ):
        print(f"- {quiz_name}: {count}")

    print("\nQuestion types:")
    for question_type, count in sorted(
        summary.question_types.items()
    ):
        print(f"- {question_type}: {count}")

    print(
        "Questions with empty text: "
        f"{summary.questions_with_empty_text}"
    )
    print(
        "Questions without answers: "
        f"{summary.questions_without_answers}"
    )
    print(
        "Questions without a correct answer: "
        f"{summary.questions_without_correct_answer}"
    )

    print(f"\nCSV: {arguments.output_file.resolve()}")
    print(f"Manifest: {summary_path.resolve()}")
    print(
        f"Status: "
        f"{'PASSED' if summary.passed else 'REVIEW REQUIRED'}"
    )

    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
