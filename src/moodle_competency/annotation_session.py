"""Interactive human annotation session helpers.

This module never ranks competencies, never reads BM25/Gemini files,
and never invents gold labels. It only stores decisions entered by the
human annotator.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import (
    ANNOTATION_COLUMNS,
    parse_annotation_date,
    parse_boolean,
    parse_competency_ids,
    read_csv,
    stripped_text,
    write_csv,
)


COMMANDS = {
    ":q": "quit",
    ":s": "skip",
    ":c": "catalogue",
    ":p": "progress",
    ":b": "back",
    ":h": "help",
}

HELP_TEXT = """Commands:
  :q  quit without saving the current unsaved fragment
  :s  skip this fragment and resume it later
  :c  show the competency catalogue
  :p  show progress
  :b  go to the previous fragment
  :h  show this help

Competency input examples (format only, not recommendations):
  GI_C1_2
  GI_C1_2;GI_C1_3
  NONE
"""


class AnnotationCommand(Exception):
    """Raised when the annotator enters a session command."""

    def __init__(self, action: str) -> None:
        super().__init__(action)
        self.action = action


def parse_session_command(raw: Any) -> str | None:
    """Return a command action, or None if the text is ordinary input."""

    text = stripped_text(raw).lower()
    return COMMANDS.get(text)


def raise_if_command(raw: Any) -> str:
    """Return stripped input, or raise AnnotationCommand."""

    action = parse_session_command(raw)

    if action is not None:
        raise AnnotationCommand(action)

    return stripped_text(raw)


def is_row_complete(row: Mapping[str, Any]) -> bool:
    """Return True when a row already contains a saveable human decision."""

    competency_ids, competency_errors = parse_competency_ids(
        row.get("gold_competency_ids")
    )
    no_competency, no_competency_errors = parse_boolean(
        row.get("no_competency"),
        "no_competency",
    )
    ambiguous, ambiguous_errors = parse_boolean(
        row.get("ambiguous"),
        "ambiguous",
    )
    annotator = stripped_text(row.get("annotator"))
    annotation_date, date_errors = parse_annotation_date(
        row.get("annotation_date")
    )

    if competency_errors or no_competency_errors:
        return False

    if ambiguous_errors or date_errors:
        return False

    if not annotator or annotation_date is None:
        return False

    if ambiguous is None:
        return False

    if ambiguous is True and not stripped_text(
        row.get("ambiguity_reason")
    ):
        return False

    if no_competency is True:
        return not competency_ids

    if no_competency is False:
        return bool(competency_ids)

    return False


def first_incomplete_index(
    rows: Sequence[Mapping[str, Any]],
) -> int | None:
    """Return the first incomplete row index, or None if all are complete."""

    for index, row in enumerate(rows):
        if not is_row_complete(row):
            return index

    return None


def next_incomplete_index(
    rows: Sequence[Mapping[str, Any]],
    current_index: int,
) -> int | None:
    """Return the next incomplete index after current, wrapping once."""

    if not rows:
        return None

    count = len(rows)

    for step in range(1, count + 1):
        index = (current_index + step) % count

        if not is_row_complete(rows[index]):
            return index

    return None


def progress_counts(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Count completed and remaining annotations."""

    completed = sum(1 for row in rows if is_row_complete(row))
    total = len(rows)
    return {
        "total": total,
        "completed": completed,
        "remaining": total - completed,
    }


def catalogue_id_set(
    catalogue: Sequence[Mapping[str, Any]],
) -> set[str]:
    """Return the allowed competency IDs from the catalogue."""

    return {
        stripped_text(row.get("idnumber"))
        for row in catalogue
        if stripped_text(row.get("idnumber"))
    }


def format_catalogue(
    catalogue: Sequence[Mapping[str, Any]],
) -> str:
    """Render competencies in catalogue/hierarchy order, unranked."""

    lines = ["UTC GI competencies (catalogue / hierarchy order)", ""]

    for row in catalogue:
        depth_raw = stripped_text(row.get("depth"))

        try:
            depth = int(depth_raw) if depth_raw else 0
        except ValueError:
            depth = 0

        indent = "  " * max(depth, 0)
        idnumber = stripped_text(row.get("idnumber"))
        shortname = stripped_text(row.get("shortname"))
        parent = stripped_text(row.get("parent_idnumber"))
        relation = (
            f"child of {parent}"
            if parent
            else "top-level"
        )
        description = stripped_text(row.get("description"))
        lines.append(
            f"{indent}{idnumber}  [{relation}]  {shortname}"
        )

        if description:
            lines.append(f"{indent}  {description}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_fragment_header(
    row: Mapping[str, Any],
    *,
    position: int,
    total: int,
    completed: int,
    remaining: int,
) -> str:
    """Render progress and source metadata for one fragment."""

    return (
        f"Fragment {position} / {total}\n"
        f"Completed: {completed}\n"
        f"Remaining: {remaining}\n"
        "\n"
        f"fragment_id: {stripped_text(row.get('fragment_id'))}\n"
        f"resource_id: {stripped_text(row.get('resource_id'))}\n"
        f"course_shortname: {stripped_text(row.get('course_shortname'))}\n"
        f"resource_type: {stripped_text(row.get('resource_type'))}\n"
        f"activity_name: {stripped_text(row.get('activity_name'))}\n"
        f"resource_title: {stripped_text(row.get('resource_title'))}\n"
    )


def decision_guide(resource_type: str) -> str:
    """Return the human decision prompt for this resource type."""

    if stripped_text(resource_type) == "quiz_question":
        question = (
            "What competency must a student use to answer "
            "this question?"
        )
    else:
        question = (
            "What competency is this paragraph actually "
            "teaching or explaining?"
        )

    return (
        "Human decision guide\n"
        f"- {question}\n"
        "- Prefer a specific child competency when it clearly matches.\n"
        "- Choose multiple competencies only when the fragment "
        "genuinely supports each one.\n"
        "- Choose NONE when no competency fits.\n"
        "- Mark ambiguous when you are genuinely uncertain.\n"
    )


def parse_competency_choice(
    raw: Any,
    allowed_ids: set[str],
) -> tuple[list[str], bool, list[str]]:
    """Parse NONE or semicolon-separated catalogue IDs."""

    text = stripped_text(raw)

    if not text:
        return [], False, [
            "Enter at least one competency ID, or NONE."
        ]

    if text.upper() == "NONE":
        return [], True, []

    competency_ids, errors = parse_competency_ids(text)

    if errors:
        return competency_ids, False, errors

    unknown = [
        competency_id
        for competency_id in competency_ids
        if competency_id not in allowed_ids
    ]

    if unknown:
        errors.append(
            "Unknown competency IDs: " + ", ".join(unknown)
        )

    return competency_ids, False, errors


def parse_yes_no(raw: Any) -> tuple[bool | None, list[str]]:
    """Parse y/n answers."""

    text = stripped_text(raw).lower()

    if text in {"y", "yes", "true", "1"}:
        return True, []

    if text in {"n", "no", "false", "0"}:
        return False, []

    return None, ["Please answer y or n."]


def validate_evidence_quotes(
    quotes: Sequence[str],
    fragment_text: str,
) -> list[str]:
    """Require every quote to be an exact contiguous substring."""

    errors: list[str] = []

    for index, quote in enumerate(quotes, start=1):
        if not stripped_text(quote):
            errors.append(f"Evidence quote {index} is empty.")
            continue

        if quote not in fragment_text:
            errors.append(
                f"Evidence quote {index} is not an exact "
                "contiguous substring of the fragment text."
            )

    return errors


def encode_evidence(quotes: Sequence[str]) -> str:
    """Store evidence as a JSON array, or blank when omitted."""

    cleaned = [quote for quote in quotes if stripped_text(quote)]

    if not cleaned:
        return ""

    return json.dumps(cleaned, ensure_ascii=False)


def apply_human_decision(
    row: Mapping[str, Any],
    *,
    annotator: str,
    annotation_date: str,
    competency_ids: Sequence[str],
    no_competency: bool,
    ambiguous: bool,
    ambiguity_reason: str,
    evidence_quotes: Sequence[str],
    comment: str,
) -> dict[str, str]:
    """Copy a source row and attach the human decision only."""

    updated = {
        column: str(row.get(column, "") or "")
        for column in ANNOTATION_COLUMNS
    }

    if no_competency:
        updated["gold_competency_ids"] = ""
        updated["no_competency"] = "true"
    else:
        updated["gold_competency_ids"] = ";".join(competency_ids)
        updated["no_competency"] = "false"

    updated["ambiguous"] = "true" if ambiguous else "false"
    updated["ambiguity_reason"] = (
        stripped_text(ambiguity_reason) if ambiguous else ""
    )
    updated["gold_evidence"] = encode_evidence(evidence_quotes)
    updated["comment"] = stripped_text(comment)
    updated["annotator"] = stripped_text(annotator)
    updated["annotation_date"] = stripped_text(annotation_date)
    return updated


def format_decision_summary(row: Mapping[str, Any]) -> str:
    """Show the annotator's decision before they confirm save."""

    return (
        "Decision summary\n"
        f"  fragment_id: {stripped_text(row.get('fragment_id'))}\n"
        f"  gold_competency_ids: "
        f"{stripped_text(row.get('gold_competency_ids')) or '(none)'}\n"
        f"  no_competency: {stripped_text(row.get('no_competency'))}\n"
        f"  ambiguous: {stripped_text(row.get('ambiguous'))}\n"
        f"  ambiguity_reason: "
        f"{stripped_text(row.get('ambiguity_reason')) or '(blank)'}\n"
        f"  gold_evidence: "
        f"{stripped_text(row.get('gold_evidence')) or '(blank)'}\n"
        f"  comment: {stripped_text(row.get('comment')) or '(blank)'}\n"
        f"  annotator: {stripped_text(row.get('annotator'))}\n"
        f"  annotation_date: {stripped_text(row.get('annotation_date'))}\n"
    )


def atomic_write_annotations(
    rows: Sequence[Mapping[str, Any]],
    path: Path,
) -> Path:
    """Write the annotation CSV using a same-directory replace."""

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
        write_csv(rows, temp_path, ANNOTATION_COLUMNS)
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
    """Copy the annotation CSV before the first write of a session."""

    if not source_path.exists():
        raise FileNotFoundError(
            f"Cannot backup missing file: {source_path}"
        )

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = (moment or datetime.now(timezone.utc)).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    backup_path = (
        backup_dir
        / f"manual_fragment_annotations_{stamp}.csv"
    )
    shutil.copy2(source_path, backup_path)
    return backup_path.resolve()


def load_annotation_workspace(
    annotations_path: Path,
    catalogue_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Load only the gold annotation CSV and competency catalogue."""

    return read_csv(annotations_path), read_csv(catalogue_path)


def validate_session_identity(
    *,
    annotator: str,
    annotation_date: str,
) -> list[str]:
    """Validate annotator name and YYYY-MM-DD date."""

    errors: list[str] = []

    if not stripped_text(annotator):
        errors.append("Annotator name is required.")

    parsed_date, date_errors = parse_annotation_date(
        annotation_date
    )

    if parsed_date is None:
        errors.extend(
            date_errors
            or ["annotation_date must use YYYY-MM-DD."]
        )

    return errors
