"""AI-assisted annotation drafts. Not independent human gold.

Suggestions are researcher-reviewable drafts. They must never be written
into data/gold/manual_fragment_annotations.csv automatically.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import (
    parse_boolean,
    parse_competency_ids,
    stripped_text,
    write_csv,
)
from moodle_competency.annotation_session import (
    encode_evidence,
    parse_competency_choice,
    parse_yes_no,
    validate_evidence_quotes,
)


DRAFT_COLUMNS = (
    "fragment_id",
    "resource_id",
    "course_id",
    "course_shortname",
    "resource_type",
    "activity_name",
    "resource_title",
    "fragment_text",
    "suggested_competency_ids",
    "suggested_no_competency",
    "suggested_ambiguous",
    "suggested_ambiguity_reason",
    "suggested_exact_evidence",
    "short_reasoning",
    "review_status",
    "human_competency_ids",
    "human_no_competency",
    "human_ambiguous",
    "human_ambiguity_reason",
    "human_evidence",
    "human_comment",
    "reviewer",
    "review_date",
)

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "human_confirmed_ai_assisted"
STATUS_MODIFIED = "human_modified_ai_assisted"
REVIEWED_STATUSES = {STATUS_CONFIRMED, STATUS_MODIFIED}

ALLOWED_SOURCE_NAMES = {
    "fragments.jsonl",
    "resources.jsonl",
    "competencies.jsonl",
    "annotation_competency_catalogue.csv",
}

FORBIDDEN_SOURCE_NAMES = (
    "bm25_candidates.jsonl",
    "llm_tasks.jsonl",
    "gemini_responses.jsonl",
    "gemini_validated.jsonl",
    "manual_moodle_links.csv",
    "manual_fragment_annotations.csv",
)

GOLD_FILENAME = "manual_fragment_annotations.csv"


class DraftValidationError(ValueError):
    """Raised when a draft suggestion is internally inconsistent."""


def assert_allowed_source_paths(paths: Sequence[Path]) -> None:
    """Refuse BM25, Gemini, gold, and activity-link files."""

    for path in paths:
        name = path.name

        if name in FORBIDDEN_SOURCE_NAMES:
            raise DraftValidationError(
                f"Forbidden source file: {path}"
            )


def empty_human_fields() -> dict[str, str]:
    return {
        "human_competency_ids": "",
        "human_no_competency": "",
        "human_ambiguous": "",
        "human_ambiguity_reason": "",
        "human_evidence": "",
        "human_comment": "",
        "reviewer": "",
        "review_date": "",
    }


def encode_id_list(competency_ids: Sequence[str]) -> str:
    return ";".join(competency_ids)


def parse_evidence_json(raw: Any) -> tuple[list[str], list[str]]:
    text = stripped_text(raw)

    if not text:
        return [], []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [], ["Evidence must be a JSON array of strings."]

    if not isinstance(parsed, list):
        return [], ["Evidence must be a JSON array of strings."]

    quotes: list[str] = []

    for item in parsed:
        if not isinstance(item, str) or not item:
            return [], ["Every evidence item must be a non-empty string."]

        quotes.append(item)

    return quotes, []


def validate_suggestion(
    *,
    fragment_text: str,
    competency_ids: Sequence[str],
    no_competency: bool,
    ambiguous: bool,
    ambiguity_reason: str,
    evidence_quotes: Sequence[str],
    allowed_ids: set[str],
) -> list[str]:
    errors: list[str] = []

    if no_competency and competency_ids:
        errors.append(
            "NONE suggestions cannot also list competency IDs."
        )

    if not no_competency and not competency_ids:
        errors.append(
            "A non-NONE suggestion must list at least one competency."
        )

    unknown = [
        competency_id
        for competency_id in competency_ids
        if competency_id not in allowed_ids
    ]

    if unknown:
        errors.append(
            "Unknown competency IDs: " + ", ".join(unknown)
        )

    if ambiguous and not stripped_text(ambiguity_reason):
        errors.append("Ambiguous suggestions need an ambiguity reason.")

    if not no_competency:
        if not evidence_quotes:
            errors.append(
                "Each competency suggestion needs exact evidence."
            )

        errors.extend(
            validate_evidence_quotes(evidence_quotes, fragment_text)
        )
    elif evidence_quotes:
        errors.append("NONE suggestions should not include evidence.")

    return errors


def build_draft_row(
    fragment: Mapping[str, Any],
    suggestion: Mapping[str, Any],
    allowed_ids: set[str],
) -> dict[str, str]:
    fragment_id = stripped_text(fragment.get("fragment_id"))
    fragment_text = str(fragment.get("text") or "")
    competency_ids = list(suggestion.get("competency_ids") or [])
    no_competency = bool(suggestion.get("no_competency"))
    ambiguous = bool(suggestion.get("ambiguous"))
    ambiguity_reason = stripped_text(
        suggestion.get("ambiguity_reason")
    )
    evidence_quotes = list(suggestion.get("evidence") or [])
    errors = validate_suggestion(
        fragment_text=fragment_text,
        competency_ids=competency_ids,
        no_competency=no_competency,
        ambiguous=ambiguous,
        ambiguity_reason=ambiguity_reason,
        evidence_quotes=evidence_quotes,
        allowed_ids=allowed_ids,
    )

    if errors:
        raise DraftValidationError(
            f"{fragment_id}: " + " ".join(errors)
        )

    row = {
        "fragment_id": fragment_id,
        "resource_id": stripped_text(fragment.get("resource_id")),
        "course_id": str(fragment.get("course_id") or ""),
        "course_shortname": stripped_text(
            fragment.get("course_shortname")
        ),
        "resource_type": stripped_text(fragment.get("resource_type")),
        "activity_name": stripped_text(fragment.get("activity_name")),
        "resource_title": stripped_text(
            fragment.get("title") or fragment.get("resource_title")
        ),
        "fragment_text": fragment_text,
        "suggested_competency_ids": encode_id_list(competency_ids),
        "suggested_no_competency": (
            "true" if no_competency else "false"
        ),
        "suggested_ambiguous": "true" if ambiguous else "false",
        "suggested_ambiguity_reason": (
            ambiguity_reason if ambiguous else ""
        ),
        "suggested_exact_evidence": encode_evidence(evidence_quotes),
        "short_reasoning": stripped_text(
            suggestion.get("reasoning")
        ),
        "review_status": STATUS_PENDING,
    }
    row.update(empty_human_fields())
    return row


def build_draft_rows(
    *,
    fragments: Sequence[Mapping[str, Any]],
    catalogue: Sequence[Mapping[str, Any]],
    suggestions_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    allowed_ids = {
        stripped_text(item.get("idnumber"))
        for item in catalogue
        if stripped_text(item.get("idnumber"))
    }
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for fragment in fragments:
        fragment_id = stripped_text(fragment.get("fragment_id"))

        if not fragment_id:
            raise DraftValidationError("Fragment is missing fragment_id.")

        if fragment_id in seen:
            raise DraftValidationError(
                f"Duplicate fragment_id: {fragment_id}"
            )

        seen.add(fragment_id)
        suggestion = suggestions_by_id.get(fragment_id)

        if suggestion is None:
            raise DraftValidationError(
                f"No draft suggestion for {fragment_id}."
            )

        rows.append(
            build_draft_row(fragment, suggestion, allowed_ids)
        )

    missing = sorted(set(suggestions_by_id) - seen)

    if missing:
        raise DraftValidationError(
            "Suggestions for unknown fragments: " + ", ".join(missing)
        )

    return rows


def draft_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    none_count = 0
    single = 0
    multi = 0
    ambiguous = 0

    for row in rows:
        ids, _errors = parse_competency_ids(
            row.get("suggested_competency_ids")
        )
        no_competency, _ = parse_boolean(
            row.get("suggested_no_competency"),
            "suggested_no_competency",
        )
        is_ambiguous, _ = parse_boolean(
            row.get("suggested_ambiguous"),
            "suggested_ambiguous",
        )

        if no_competency:
            none_count += 1
        elif len(ids) == 1:
            single += 1
        elif len(ids) > 1:
            multi += 1

        if is_ambiguous:
            ambiguous += 1

    return {
        "total": len(rows),
        "none": none_count,
        "single": single,
        "multi": multi,
        "ambiguous": ambiguous,
        "pending": sum(
            1
            for row in rows
            if stripped_text(row.get("review_status"))
            == STATUS_PENDING
        ),
    }


def is_review_complete(row: Mapping[str, Any]) -> bool:
    status = stripped_text(row.get("review_status"))

    if status not in REVIEWED_STATUSES:
        return False

    no_competency, errors = parse_boolean(
        row.get("human_no_competency"),
        "human_no_competency",
    )
    ambiguous, amb_errors = parse_boolean(
        row.get("human_ambiguous"),
        "human_ambiguous",
    )
    ids, id_errors = parse_competency_ids(
        row.get("human_competency_ids")
    )

    if errors or amb_errors or id_errors:
        return False

    if not stripped_text(row.get("reviewer")):
        return False

    if no_competency is True:
        return not ids and ambiguous is not None

    if no_competency is False:
        return bool(ids) and ambiguous is not None

    return False


def apply_accept_suggestion(
    row: Mapping[str, Any],
    *,
    reviewer: str,
    review_date: str,
) -> dict[str, str]:
    updated = {column: str(row.get(column, "") or "") for column in DRAFT_COLUMNS}
    updated["human_competency_ids"] = stripped_text(
        row.get("suggested_competency_ids")
    )
    updated["human_no_competency"] = stripped_text(
        row.get("suggested_no_competency")
    )
    updated["human_ambiguous"] = stripped_text(
        row.get("suggested_ambiguous")
    )
    updated["human_ambiguity_reason"] = stripped_text(
        row.get("suggested_ambiguity_reason")
    )
    updated["human_evidence"] = stripped_text(
        row.get("suggested_exact_evidence")
    )
    updated["human_comment"] = ""
    updated["reviewer"] = stripped_text(reviewer)
    updated["review_date"] = stripped_text(review_date)
    updated["review_status"] = STATUS_CONFIRMED
    return updated


def apply_modified_decision(
    row: Mapping[str, Any],
    *,
    reviewer: str,
    review_date: str,
    competency_ids: Sequence[str],
    no_competency: bool,
    ambiguous: bool,
    ambiguity_reason: str,
    evidence_quotes: Sequence[str],
    comment: str,
) -> dict[str, str]:
    updated = {column: str(row.get(column, "") or "") for column in DRAFT_COLUMNS}

    if no_competency:
        updated["human_competency_ids"] = ""
        updated["human_no_competency"] = "true"
        updated["human_evidence"] = ""
    else:
        updated["human_competency_ids"] = encode_id_list(competency_ids)
        updated["human_no_competency"] = "false"
        updated["human_evidence"] = encode_evidence(evidence_quotes)

    updated["human_ambiguous"] = "true" if ambiguous else "false"
    updated["human_ambiguity_reason"] = (
        stripped_text(ambiguity_reason) if ambiguous else ""
    )
    updated["human_comment"] = stripped_text(comment)
    updated["reviewer"] = stripped_text(reviewer)
    updated["review_date"] = stripped_text(review_date)
    updated["review_status"] = STATUS_MODIFIED
    return updated


def write_drafts(
    rows: Sequence[Mapping[str, Any]],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_csv(rows, path, DRAFT_COLUMNS)


def atomic_write_drafts(
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
        write_csv(rows, temp_path, DRAFT_COLUMNS)
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return path


def create_review_backup(path: Path, backup_dir: Path) -> Path | None:
    if not path.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, destination)
    return destination


def export_reviewed_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    incomplete = [
        stripped_text(row.get("fragment_id"))
        for row in rows
        if not is_review_complete(row)
    ]

    if incomplete:
        raise DraftValidationError(
            "Human review is incomplete. Remaining: "
            + ", ".join(incomplete)
        )

    exported: list[dict[str, str]] = []

    for row in rows:
        exported.append(
            {
                "fragment_id": stripped_text(row.get("fragment_id")),
                "resource_id": stripped_text(row.get("resource_id")),
                "course_id": stripped_text(row.get("course_id")),
                "course_shortname": stripped_text(
                    row.get("course_shortname")
                ),
                "resource_type": stripped_text(row.get("resource_type")),
                "activity_name": stripped_text(row.get("activity_name")),
                "resource_title": stripped_text(
                    row.get("resource_title")
                ),
                "fragment_text": str(row.get("fragment_text") or ""),
                "human_competency_ids": stripped_text(
                    row.get("human_competency_ids")
                ),
                "human_no_competency": stripped_text(
                    row.get("human_no_competency")
                ),
                "human_ambiguous": stripped_text(
                    row.get("human_ambiguous")
                ),
                "human_ambiguity_reason": stripped_text(
                    row.get("human_ambiguity_reason")
                ),
                "human_evidence": stripped_text(row.get("human_evidence")),
                "human_comment": stripped_text(row.get("human_comment")),
                "review_status": stripped_text(row.get("review_status")),
                "reviewer": stripped_text(row.get("reviewer")),
                "review_date": stripped_text(row.get("review_date")),
                "provenance": (
                    "AI-assisted human review. "
                    "Not independent manual gold."
                ),
            }
        )

    return exported


EXPORT_COLUMNS = (
    "fragment_id",
    "resource_id",
    "course_id",
    "course_shortname",
    "resource_type",
    "activity_name",
    "resource_title",
    "fragment_text",
    "human_competency_ids",
    "human_no_competency",
    "human_ambiguous",
    "human_ambiguity_reason",
    "human_evidence",
    "human_comment",
    "review_status",
    "reviewer",
    "review_date",
    "provenance",
)


def parse_accept_choice(raw: Any) -> tuple[bool | None, list[str]]:
    return parse_yes_no(raw)


def parse_review_competency_choice(
    raw: Any,
    allowed_ids: set[str],
) -> tuple[list[str], bool, list[str]]:
    return parse_competency_choice(raw, allowed_ids)
