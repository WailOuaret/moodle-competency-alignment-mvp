"""Interactive helper for HUMAN fragment-level gold annotation.

This program does not recommend competencies, does not rank them,
and does not read BM25, Gemini, LLM-task or Moodle activity-link files.
"""

from __future__ import annotations

import sys
from pathlib import Path

from moodle_competency.annotation_session import (
    HELP_TEXT,
    AnnotationCommand,
    apply_human_decision,
    atomic_write_annotations,
    catalogue_id_set,
    create_timestamped_backup,
    decision_guide,
    first_incomplete_index,
    format_catalogue,
    format_decision_summary,
    format_fragment_header,
    is_row_complete,
    load_annotation_workspace,
    next_incomplete_index,
    parse_competency_choice,
    parse_yes_no,
    progress_counts,
    raise_if_command,
    validate_evidence_quotes,
    validate_session_identity,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ANNOTATIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "manual_fragment_annotations.csv"
)

CATALOGUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "annotation_competency_catalogue.csv"
)

BACKUP_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "annotation_backups"
)


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
    counts = progress_counts(rows)
    print(
        f"Completed: {counts['completed']}\n"
        f"Remaining: {counts['remaining']}\n"
        f"Total: {counts['total']}"
    )


def show_fragment(
    row: dict[str, str],
    rows: list[dict[str, str]],
    index: int,
) -> None:
    counts = progress_counts(rows)
    print()
    print("=" * 72)
    print(
        format_fragment_header(
            row,
            position=index + 1,
            total=counts["total"],
            completed=counts["completed"],
            remaining=counts["remaining"],
        )
    )
    print("Fragment text")
    print("-" * 72)
    print(row.get("fragment_text", ""))
    print("-" * 72)


def collect_competency_choice(
    allowed_ids: set[str],
) -> tuple[list[str], bool]:
    while True:
        raw = ask(
            "Enter competency ID(s) separated by semicolons, "
            "or NONE: "
        )
        competency_ids, no_competency, errors = (
            parse_competency_choice(raw, allowed_ids)
        )

        if not errors:
            return competency_ids, no_competency

        print("Invalid competency choice:")

        for error in errors:
            print(f"- {error}")


def collect_yes_no(message: str) -> bool:
    while True:
        answer, errors = parse_yes_no(ask(message))

        if answer is not None:
            return answer

        for error in errors:
            print(error)


def collect_evidence(fragment_text: str) -> list[str]:
    quotes: list[str] = []
    print(
        "Paste one exact quote from the fragment, then Enter. "
        "Empty line finishes. Do not paraphrase."
    )

    while True:
        quote = prompt("Evidence quote: ")
        action = None

        try:
            text = raise_if_command(quote)
        except AnnotationCommand as command:
            if command.action in {"catalogue", "progress", "help"}:
                raise
            action = command.action
            text = ""

        if action in {"quit", "skip", "back"}:
            raise AnnotationCommand(action)

        if not text:
            break

        errors = validate_evidence_quotes(
            [text],
            fragment_text,
        )

        if errors:
            for error in errors:
                print(error)
            continue

        quotes.append(text)
        print("Quote accepted.")

    return quotes


def annotate_one_row(
    row: dict[str, str],
    *,
    annotator: str,
    annotation_date: str,
    allowed_ids: set[str],
) -> dict[str, str]:
    competency_ids, no_competency = collect_competency_choice(
        allowed_ids
    )
    ambiguous = collect_yes_no("Ambiguous? [y/n] ")
    ambiguity_reason = ""

    if ambiguous:
        while True:
            ambiguity_reason = ask("Ambiguity reason: ")

            if ambiguity_reason:
                break

            print("An ambiguity reason is required.")

    evidence_quotes: list[str] = []

    if collect_yes_no("Add exact textual evidence? [y/n] "):
        evidence_quotes = collect_evidence(
            str(row.get("fragment_text", ""))
        )

    comment = ask("Optional comment: ")
    updated = apply_human_decision(
        row,
        annotator=annotator,
        annotation_date=annotation_date,
        competency_ids=competency_ids,
        no_competency=no_competency,
        ambiguous=ambiguous,
        ambiguity_reason=ambiguity_reason,
        evidence_quotes=evidence_quotes,
        comment=comment,
    )
    print()
    print(format_decision_summary(updated))

    if not collect_yes_no("Save this annotation? [y/n] "):
        print("Not saved.")
        raise AnnotationCommand("skip")

    return updated


def main() -> int:
    try:
        rows, catalogue = load_annotation_workspace(
            ANNOTATIONS_PATH,
            CATALOGUE_PATH,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    allowed_ids = catalogue_id_set(catalogue)

    print("Blinded manual fragment annotation")
    print("This helper does not recommend competencies.")
    print("Commands: :h :c :p :s :b :q")
    print()

    while True:
        try:
            annotator = ask("Annotator name: ")
            annotation_date = ask(
                "Annotation date [YYYY-MM-DD]: "
            )
        except AnnotationCommand as command:
            if command.action == "quit":
                print("Quitting. No annotations were changed.")
                return 0
            print(HELP_TEXT)
            continue
        identity_errors = validate_session_identity(
            annotator=annotator,
            annotation_date=annotation_date,
        )

        if not identity_errors:
            break

        for error in identity_errors:
            print(error)

    backup_made = False
    index = first_incomplete_index(rows)

    if index is None:
        counts = progress_counts(rows)
        print()
        print("Manual annotation complete.")
        print(f"Total fragments: {counts['total']}")
        print(f"Completed: {counts['completed']}")
        print(f"Remaining: {counts['remaining']}")
        print()
        print("Then run:")
        print(
            "python scripts/12_validate_manual_annotations.py "
            "--mode final"
        )
        return 0

    while True:
        counts = progress_counts(rows)

        if counts["remaining"] == 0:
            print()
            print("Manual annotation complete.")
            print(f"Total fragments: {counts['total']}")
            print(f"Completed: {counts['completed']}")
            print("Remaining: 0")
            print()
            print("Then run:")
            print(
                "python scripts/12_validate_manual_annotations.py "
                "--mode final"
            )
            return 0

        if index is None or is_row_complete(rows[index]):
            index = first_incomplete_index(rows)

            if index is None:
                continue

        row = rows[index]

        try:
            show_fragment(row, rows, index)
            print()
            print(format_catalogue(catalogue))
            print()
            print(
                decision_guide(
                    str(row.get("resource_type", ""))
                )
            )
            updated = annotate_one_row(
                row,
                annotator=annotator,
                annotation_date=annotation_date,
                allowed_ids=allowed_ids,
            )
        except AnnotationCommand as command:
            if command.action == "quit":
                print("Quitting. Progress already saved is kept.")
                return 0

            if command.action == "help":
                print(HELP_TEXT)
                continue

            if command.action == "catalogue":
                print(format_catalogue(catalogue))
                continue

            if command.action == "progress":
                print_progress(rows)
                continue

            if command.action == "skip":
                nxt = next_incomplete_index(rows, index)
                index = index if nxt is None else nxt
                continue

            if command.action == "back":
                index = max(index - 1, 0)
                continue

            continue

        if not backup_made:
            backup_path = create_timestamped_backup(
                ANNOTATIONS_PATH,
                BACKUP_DIR,
            )
            print(f"Backup written: {backup_path}")
            backup_made = True

        rows[index] = updated
        atomic_write_annotations(rows, ANNOTATIONS_PATH)
        print("Saved.")
        nxt = next_incomplete_index(rows, index)
        index = 0 if nxt is None else nxt


if __name__ == "__main__":
    raise SystemExit(main())
