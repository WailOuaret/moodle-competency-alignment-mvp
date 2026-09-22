"""Interactive HUMAN pedagogical evidence rating helper.

Does not recommend 0/1/2 ratings and does not change mechanical validity
or evidence quotes. Save after each accepted row. Resume unrated rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

from moodle_competency.annotation_session import AnnotationCommand
from moodle_competency.evidence_review import pedagogical_ratings_complete
from moodle_competency.evidence_review_session import (
    HELP_TEXT,
    RATING_PROMPT,
    apply_pedagogical_rating,
    atomic_write_evidence_review,
    create_timestamped_backup,
    first_unrated_index,
    format_evidence_row,
    is_rating_complete,
    load_evidence_review_workspace,
    next_unrated_index,
    parse_pedagogical_rating,
    progress_counts,
    raise_if_evidence_command,
    validate_reviewer_identity,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = PROJECT_ROOT / "data" / "reviews" / "evidence_review.csv"
BACKUP_DIR = PROJECT_ROOT / "data" / "reviews" / "evidence_review_backups"


def prompt(message: str) -> str:
    try:
        return input(message)
    except EOFError as error:
        raise AnnotationCommand("quit") from error
    except KeyboardInterrupt as error:
        print()
        raise AnnotationCommand("quit") from error


def ask(message: str) -> str:
    return raise_if_evidence_command(prompt(message))


def print_progress(rows: list[dict[str, str]]) -> None:
    counts = progress_counts(rows)
    print(
        f"Completed: {counts['completed']}\n"
        f"Remaining: {counts['remaining']}\n"
        f"Total: {counts['total']}"
    )


def collect_rating() -> str:
    while True:
        raw = ask(RATING_PROMPT)
        rating, errors = parse_pedagogical_rating(raw)

        if rating is not None:
            return rating

        for error in errors:
            print(error)


def rate_one_row(
    row: dict[str, str],
    *,
    reviewer: str,
    review_date: str,
) -> dict[str, str]:
    rating = collect_rating()
    comment = ask("Optional comment: ")
    updated = apply_pedagogical_rating(
        row,
        rating=rating,
        reviewer=reviewer,
        review_date=review_date,
        comment=comment,
    )
    print()
    print(
        "Saved rating will be "
        f"{updated['pedagogical_rating']} "
        f"for {updated['fragment_id']} / {updated['competency_id']}"
    )
    return updated


def main() -> int:
    try:
        rows = load_evidence_review_workspace(REVIEW_PATH)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Pedagogical evidence review")
    print("This helper does not recommend a rating.")
    print("Mechanical validity and evidence quotes are not edited.")
    print("Commands: :h :p :s :b :q")
    print()

    while True:
        try:
            reviewer = ask("Reviewer name: ")
            review_date = ask("Review date [YYYY-MM-DD]: ")
        except AnnotationCommand as command:
            if command.action == "quit":
                print("Quitting. No ratings were changed.")
                return 0
            print(HELP_TEXT)
            continue

        identity_errors = validate_reviewer_identity(
            reviewer=reviewer,
            review_date=review_date,
        )

        if not identity_errors:
            break

        for error in identity_errors:
            print(error)

    backup_made = False
    index = first_unrated_index(rows)

    if index is None:
        counts = progress_counts(rows)
        print()
        print("Pedagogical evidence review complete.")
        print(f"Total rows: {counts['total']}")
        print(f"Completed: {counts['completed']}")
        print()
        print("Then run:")
        print("python scripts/18_summarize_evidence_review.py")
        return 0

    while True:
        counts = progress_counts(rows)

        if counts["remaining"] == 0 or pedagogical_ratings_complete(rows):
            print()
            print("Pedagogical evidence review complete.")
            print(f"Total rows: {counts['total']}")
            print(f"Completed: {counts['completed']}")
            print("Remaining: 0")
            print()
            print("Then run:")
            print("python scripts/18_summarize_evidence_review.py")
            return 0

        if index is None or is_rating_complete(rows[index]):
            index = first_unrated_index(rows)

            if index is None:
                continue

        row = rows[index]

        try:
            print()
            print("=" * 72)
            print(
                format_evidence_row(
                    row,
                    position=index + 1,
                    total=counts["total"],
                    completed=counts["completed"],
                    remaining=counts["remaining"],
                )
            )
            updated = rate_one_row(
                row,
                reviewer=reviewer,
                review_date=review_date,
            )
        except AnnotationCommand as command:
            if command.action == "quit":
                print("Quitting. Progress already saved is kept.")
                return 0

            if command.action == "help":
                print(HELP_TEXT)
                continue

            if command.action == "progress":
                print_progress(rows)
                continue

            if command.action == "skip":
                nxt = next_unrated_index(rows, index)
                index = index if nxt is None else nxt
                continue

            if command.action == "back":
                index = max(index - 1, 0)
                continue

            continue

        if not backup_made:
            backup_path = create_timestamped_backup(
                REVIEW_PATH,
                BACKUP_DIR,
            )
            print(f"Backup written: {backup_path}")
            backup_made = True

        rows[index] = updated
        atomic_write_evidence_review(rows, REVIEW_PATH)
        print("Saved.")
        nxt = next_unrated_index(rows, index)
        index = 0 if nxt is None else nxt


if __name__ == "__main__":
    raise SystemExit(main())
