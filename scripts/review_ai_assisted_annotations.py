"""Human review of assisted annotation drafts.

Confirmed rows are marked human_confirmed_ai_assisted.
They are not independent gold and are never written to the gold CSV.
"""

from __future__ import annotations

import sys
from pathlib import Path

from moodle_competency.ai_assisted_annotation import (
    DRAFT_COLUMNS,
    STATUS_PENDING,
    apply_accept_suggestion,
    apply_modified_decision,
    atomic_write_drafts,
    create_review_backup,
    is_review_complete,
    parse_evidence_json,
    parse_review_competency_choice,
    parse_accept_choice,
    validate_suggestion,
)
from moodle_competency.annotation import (
    parse_annotation_date,
    read_csv,
    stripped_text,
)
from moodle_competency.annotation_session import (
    HELP_TEXT,
    AnnotationCommand,
    catalogue_id_set,
    format_catalogue,
    parse_yes_no,
    raise_if_command,
    validate_evidence_quotes,
    validate_session_identity,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFTS = (
    PROJECT_ROOT / "data" / "reviews" / "ai_assisted_annotation_drafts.csv"
)
CATALOGUE = (
    PROJECT_ROOT / "data" / "gold" / "annotation_competency_catalogue.csv"
)
BACKUP_DIR = PROJECT_ROOT / "data" / "reviews" / "ai_assisted_review_backups"
GOLD = PROJECT_ROOT / "data" / "gold" / "manual_fragment_annotations.csv"


def prompt(message: str) -> str:
    try:
        return input(message)
    except EOFError as error:
        raise AnnotationCommand("quit") from error
    except KeyboardInterrupt as error:
        print()
        raise AnnotationCommand("quit") from error


def ask(message: str) -> str:
    return raise_if_command(prompt(message))


def print_progress(rows: list[dict[str, str]]) -> None:
    completed = sum(1 for row in rows if is_review_complete(row))
    print(
        f"Reviewed: {completed}\n"
        f"Remaining: {len(rows) - completed}\n"
        f"Total: {len(rows)}"
    )


def first_pending(rows: list[dict[str, str]]) -> int | None:
    for index, row in enumerate(rows):
        if not is_review_complete(row):
            return index

    return None


def format_draft(row: dict[str, str], position: int, total: int) -> str:
    return (
        f"Fragment {position} / {total}\n"
        f"fragment_id: {row.get('fragment_id', '')}\n"
        f"resource_id: {row.get('resource_id', '')}\n"
        f"course_shortname: {row.get('course_shortname', '')}\n"
        f"resource_type: {row.get('resource_type', '')}\n"
        f"activity_name: {row.get('activity_name', '')}\n"
        f"resource_title: {row.get('resource_title', '')}\n"
        "\nFRAGMENT\n--------\n"
        f"{row.get('fragment_text', '')}\n"
        "\nDRAFT SUGGESTION\n----------------\n"
        f"Suggested competency: "
        f"{row.get('suggested_competency_ids', '') or 'NONE'}\n"
        f"Suggested no_competency: {row.get('suggested_no_competency', '')}\n"
        f"Reason:\n{row.get('short_reasoning', '')}\n"
        f"Evidence:\n{row.get('suggested_exact_evidence', '')}\n"
        f"Ambiguous: {row.get('suggested_ambiguous', '')}\n"
        f"Ambiguity reason: "
        f"{row.get('suggested_ambiguity_reason', '') or '(none)'}\n"
        "\nThis is an AI-assisted draft. It is not independent gold.\n"
    )


def save(rows: list[dict[str, str]]) -> None:
    gold_before = GOLD.read_bytes() if GOLD.exists() else None
    atomic_write_drafts(rows, DRAFTS)
    gold_after = GOLD.read_bytes() if GOLD.exists() else None

    if gold_before != gold_after:
        raise RuntimeError("Independent gold CSV was modified.")


def review_one(
    row: dict[str, str],
    *,
    allowed_ids: set[str],
    reviewer: str,
    review_date: str,
) -> dict[str, str] | None:
    while True:
        answer = ask("Accept draft suggestion? [y/n]: ")
        accepted, errors = parse_accept_choice(answer)

        if errors:
            print(errors[0])
            continue

        if accepted:
            return apply_accept_suggestion(
                row,
                reviewer=reviewer,
                review_date=review_date,
            )

        choice = ask("Competency IDs or NONE: ")
        ids, no_competency, choice_errors = parse_review_competency_choice(
            choice,
            allowed_ids,
        )

        if choice_errors:
            print(choice_errors[0])
            continue

        ambiguous_raw = ask("Ambiguous? [y/n]: ")
        ambiguous, amb_errors = parse_yes_no(ambiguous_raw)

        if amb_errors or ambiguous is None:
            print("Please answer y or n.")
            continue

        reason = ""

        if ambiguous:
            reason = ask("Ambiguity reason: ")

            if not stripped_text(reason):
                print("Ambiguous decisions need a reason.")
                continue

        quotes: list[str] = []

        if not no_competency:
            evidence_raw = ask(
                "Evidence JSON array, or a single exact quote: "
            )

            if stripped_text(evidence_raw).startswith("["):
                quotes, evidence_errors = parse_evidence_json(evidence_raw)
            elif stripped_text(evidence_raw):
                quotes = [evidence_raw]
                evidence_errors = []
            else:
                evidence_errors = ["Evidence is required unless NONE."]

            if not evidence_errors:
                evidence_errors = validate_evidence_quotes(
                    quotes,
                    str(row.get("fragment_text") or ""),
                )

            if evidence_errors:
                print(evidence_errors[0])
                continue

        comment = ask("Comment (optional): ")
        suggestion_errors = validate_suggestion(
            fragment_text=str(row.get("fragment_text") or ""),
            competency_ids=ids,
            no_competency=no_competency,
            ambiguous=ambiguous,
            ambiguity_reason=reason,
            evidence_quotes=quotes,
            allowed_ids=allowed_ids,
        )

        if suggestion_errors:
            print(suggestion_errors[0])
            continue

        return apply_modified_decision(
            row,
            reviewer=reviewer,
            review_date=review_date,
            competency_ids=ids,
            no_competency=no_competency,
            ambiguous=ambiguous,
            ambiguity_reason=reason,
            evidence_quotes=quotes,
            comment=comment,
        )


def main() -> int:
    if not DRAFTS.exists():
        print(
            f"ERROR: {DRAFTS} does not exist. "
            "Run scripts/21_build_ai_assisted_annotation_drafts.py first.",
            file=sys.stderr,
        )
        return 1

    rows = read_csv(DRAFTS)
    catalogue = read_csv(CATALOGUE)
    allowed_ids = catalogue_id_set(catalogue)

    if [column for column in DRAFT_COLUMNS if column not in (rows[0] if rows else {})]:
        missing = [
            column
            for column in DRAFT_COLUMNS
            if rows and column not in rows[0]
        ]

        if missing:
            print(f"ERROR: draft CSV missing columns: {missing}", file=sys.stderr)
            return 1

    create_review_backup(DRAFTS, BACKUP_DIR)
    print("=== AI-ASSISTED ANNOTATION REVIEW ===")
    print("Confirmed drafts are AI-assisted, not independent gold.")
    print_progress(rows)
    reviewer = ask("Reviewer: ")
    review_date = ask("Review date (YYYY-MM-DD): ")
    identity_errors = validate_session_identity(
        annotator=reviewer,
        annotation_date=review_date,
    )

    if identity_errors:
        print(identity_errors[0], file=sys.stderr)
        return 1

    parsed_date, date_errors = parse_annotation_date(review_date)

    if date_errors or parsed_date is None:
        print(
            (date_errors or ["Review date must use YYYY-MM-DD."])[0],
            file=sys.stderr,
        )
        return 1

    review_date = parsed_date

    index = first_pending(rows)

    if index is None:
        print("All drafts already have a human review.")
        return 0

    while index is not None:
        row = rows[index]
        print()
        print(
            format_draft(
                row,
                position=index + 1,
                total=len(rows),
            )
        )
        print(format_catalogue(catalogue))

        try:
            updated = review_one(
                row,
                allowed_ids=allowed_ids,
                reviewer=reviewer,
                review_date=review_date,
            )
        except AnnotationCommand as command:
            if command.action == "quit":
                save(rows)
                print("Saved. Resume later with the same command.")
                return 0

            if command.action == "skip":
                nxt = None

                for later in range(index + 1, len(rows)):
                    if not is_review_complete(rows[later]):
                        nxt = later
                        break

                if nxt is None:
                    for earlier in range(0, index + 1):
                        if not is_review_complete(rows[earlier]):
                            nxt = earlier
                            break

                index = nxt
                continue

            if command.action == "help":
                print(HELP_TEXT)
                continue

            if command.action == "catalogue":
                print(format_catalogue(catalogue))
                continue

            if command.action == "progress":
                print_progress(rows)
                continue

            if command.action == "back":
                index = max(index - 1, 0)
                continue

            continue

        if updated is None:
            continue

        rows[index] = updated
        save(rows)
        print(f"Saved as {updated['review_status']}")
        index = first_pending(rows)

    print("All 35 drafts have a human review.")
    print("Independent gold was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
