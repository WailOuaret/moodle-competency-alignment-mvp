"""Summarize real teacher/supervisor validation. Never invent decisions."""

from __future__ import annotations

from moodle_competency.human_validation_summary import (
    WAITING_MESSAGE,
    summarize_human_validation,
    write_human_validation_outputs,
)
from moodle_competency.settings import PROJECT_ROOT
from moodle_competency.teacher_reviews import load_runtime_reviews


def main() -> int:
    review_path = PROJECT_ROOT / "data" / "reviews" / "teacher_reviews.csv"
    reviews = load_runtime_reviews(review_path)
    summary = summarize_human_validation(reviews)
    write_human_validation_outputs(project_root=PROJECT_ROOT, reviews=reviews)

    if summary.get("status") == "WAITING_FOR_HUMAN":
        print(WAITING_MESSAGE)
        print(
            "Researcher reviews recorded: "
            f"{summary.get('researcher_review_count')}. "
            "These are not teacher-study results."
        )
        return 0

    print("Human validation summary written.")
    print(f"Teacher reviews: {summary.get('teacher_review_count')}")
    print(f"Supervisor reviews: {summary.get('supervisor_review_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
