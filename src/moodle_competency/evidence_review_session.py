"""Interactive helper for HUMAN pedagogical evidence ratings.

This module never recommends a 0/1/2 rating, never changes
``mechanically_valid``, and never rewrites the evidence quote.
Ratings must be typed by the reviewer.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import (
    parse_annotation_date,
    read_csv,
    stripped_text,
    write_csv,
)
from moodle_competency.annotation_session import (
    AnnotationCommand,
    parse_session_command,
    validate_session_identity,
)
from moodle_competency.evidence_review import (
    ALLOWED_PEDAGOGICAL_RATINGS,
    EVIDENCE_REVIEW_COLUMNS,
    migrate_evidence_review_rows,
)


COMMANDS = {
    ":q": "quit",
    ":s": "skip",
    ":b": "back",
    ":p": "progress",
    ":h": "help",
}

HELP_TEXT = """Commands:
  :q  quit without saving the current unsaved row
  :s  skip this row and resume it later
  :b  go to the previous row
  :p  show progress
  :h  show this help

Pedagogical relevance [0/1/2]:
  0 = evidence does not justify the competency
  1 = partially relevant / ambiguous
  2 = clearly supports the competency

This helper does not recommend a rating.
"""

RATING_PROMPT = (
    "Pedagogical relevance [0/1/2] "
    "(0=does not justify, 1=partial/ambiguous, 2=clearly supports): "
)


def parse_evidence_command(raw: Any) -> str | None:
    """Return a Gate-2 command, ignoring annotation-only commands."""

    action = parse_session_command(raw)

    if action in {"quit", "skip", "back", "progress", "help"}:
        return action

    text = stripped_text(raw).lower()
    return COMMANDS.get(text)


def raise_if_evidence_command(raw: Any) -> str:
    action = parse_evidence_command(raw)

    if action is not None:
        raise AnnotationCommand(action)

    return stripped_text(raw)


def is_rating_complete(row: Mapping[str, Any]) -> bool:
    return stripped_text(row.get("pedagogical_rating")) in (
        ALLOWED_PEDAGOGICAL_RATINGS
    )


def parse_pedagogical_rating(raw: Any) -> tuple[str | None, list[str]]:
    """Accept only 0, 1, or 2. Do not default to a recommended value."""

    text = stripped_text(raw)

    if text in ALLOWED_PEDAGOGICAL_RATINGS:
        return text, []

    return None, [
        "Pedagogical rating must be 0, 1, or 2. "
        "This helper does not recommend a value."
    ]


def first_unrated_index(
    rows: Sequence[Mapping[str, Any]],
) -> int | None:
    for index, row in enumerate(rows):
        if not is_rating_complete(row):
            return index

    return None


def next_unrated_index(
    rows: Sequence[Mapping[str, Any]],
    current_index: int,
) -> int | None:
    if not rows:
        return None

    count = len(rows)

    for step in range(1, count + 1):
        index = (current_index + step) % count

        if not is_rating_complete(rows[index]):
            return index

    return None


def progress_counts(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    completed = sum(1 for row in rows if is_rating_complete(row))
    total = len(rows)
    return {
        "total": total,
        "completed": completed,
        "remaining": total - completed,
    }


def format_evidence_row(
    row: Mapping[str, Any],
    *,
    position: int,
    total: int,
    completed: int,
    remaining: int,
) -> str:
    """Show one evidence row. Does not suggest a rating."""

    return (
        f"Evidence {position} / {total}\n"
        f"Completed: {completed}\n"
        f"Remaining: {remaining}\n"
        "\n"
        f"fragment_id: {stripped_text(row.get('fragment_id'))}\n"
        f"resource_id: {stripped_text(row.get('resource_id'))}\n"
        f"competency_id: {stripped_text(row.get('competency_id'))}\n"
        f"competency_shortname: "
        f"{stripped_text(row.get('competency_shortname'))}\n"
        f"mechanically_valid: "
        f"{stripped_text(row.get('mechanically_valid'))}\n"
        f"evidence_start: {stripped_text(row.get('evidence_start'))}\n"
        f"evidence_end: {stripped_text(row.get('evidence_end'))}\n"
        f"offset_valid: {stripped_text(row.get('offset_valid'))}\n"
        "\n"
        "Fragment text\n"
        "--------------------------------------------------------------------\n"
        f"{row.get('fragment_text') or ''}\n"
        "--------------------------------------------------------------------\n"
        "\n"
        "Exact evidence quote\n"
        "--------------------------------------------------------------------\n"
        f"{row.get('evidence_quote') or ''}\n"
        "--------------------------------------------------------------------\n"
    )


def apply_pedagogical_rating(
    row: Mapping[str, Any],
    *,
    rating: str,
    reviewer: str,
    review_date: str,
    comment: str,
) -> dict[str, str]:
    """Copy a row and attach the human rating only."""

    if rating not in ALLOWED_PEDAGOGICAL_RATINGS:
        raise ValueError(
            "Pedagogical rating must be 0, 1, or 2."
        )

    updated = {
        column: str(row.get(column, "") or "")
        for column in EVIDENCE_REVIEW_COLUMNS
    }
    updated["pedagogical_rating"] = rating
    updated["reviewer"] = stripped_text(reviewer)
    updated["review_date"] = stripped_text(review_date)
    updated["comment"] = stripped_text(comment)
    return updated


def atomic_write_evidence_review(
    rows: Sequence[Mapping[str, Any]],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)

    try:
        write_csv(
            migrate_evidence_review_rows(rows),
            temp_path,
            EVIDENCE_REVIEW_COLUMNS,
        )
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return path.resolve()


def create_timestamped_backup(
    source_path: Path,
    backup_dir: Path,
    *,
    moment: datetime | None = None,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(
            f"Cannot backup missing file: {source_path}"
        )

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = (moment or datetime.now(timezone.utc)).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    backup_path = backup_dir / f"evidence_review_{stamp}.csv"
    shutil.copy2(source_path, backup_path)
    return backup_path.resolve()


def load_evidence_review_workspace(
    path: Path,
) -> list[dict[str, str]]:
    """Load and migrate the review CSV. Ratings stay as stored."""

    return migrate_evidence_review_rows(read_csv(path))


def validate_reviewer_identity(
    *,
    reviewer: str,
    review_date: str,
) -> list[str]:
    return validate_session_identity(
        annotator=reviewer,
        annotation_date=review_date,
    )


def parse_review_date(raw: Any) -> tuple[str | None, list[str]]:
    parsed, errors = parse_annotation_date(raw)

    if parsed is None:
        return None, errors or ["review_date must use YYYY-MM-DD."]

    return parsed, []
