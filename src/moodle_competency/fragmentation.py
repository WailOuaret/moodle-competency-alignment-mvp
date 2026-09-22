"""Create pedagogical fragments from normalized Moodle resources."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

from moodle_competency.html_clean import (
    combine_text,
    normalize_whitespace,
)


SENTENCE_BOUNDARY = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z0-9])"
)


def load_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    """Load UTF-8 JSON Lines records."""

    if not path.exists():
        raise FileNotFoundError(
            f"JSONL file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} "
                    f"of {path}."
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} of {path} "
                    "is not a JSON object."
                )

            records.append(record)

    return records


def split_sentences(text: str) -> list[str]:
    """Split normalized text using simple sentence boundaries."""

    normalized = normalize_whitespace(text)

    if not normalized:
        return []

    sentences = [
        sentence.strip()
        for sentence in SENTENCE_BOUNDARY.split(
            normalized
        )
        if sentence.strip()
    ]

    return sentences or [normalized]


def split_words_to_limit(
    text: str,
    *,
    max_chars: int,
) -> list[str]:
    """Split an unusually long sentence without losing words."""

    words = normalize_whitespace(text).split()

    if not words:
        return []

    chunks: list[str] = []
    current_words: list[str] = []

    for word in words:
        candidate = " ".join(
            current_words + [word]
        )

        if (
            current_words
            and len(candidate) > max_chars
        ):
            chunks.append(" ".join(current_words))
            current_words = [word]
        else:
            current_words.append(word)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def chunk_text(
    text: str,
    *,
    max_chars: int = 900,
) -> list[str]:
    """Split Page text into paragraph and sentence-based chunks."""

    if max_chars < 100:
        raise ValueError(
            "max_chars must be at least 100."
        )

    raw_paragraphs = re.split(
        r"\n\s*\n+",
        str(text or ""),
    )

    paragraphs = [
        normalize_whitespace(paragraph)
        for paragraph in raw_paragraphs
        if normalize_whitespace(paragraph)
    ]

    if not paragraphs:
        normalized = normalize_whitespace(text)
        paragraphs = [normalized] if normalized else []

    units: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue

        for sentence in split_sentences(paragraph):
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(
                    split_words_to_limit(
                        sentence,
                        max_chars=max_chars,
                    )
                )

    chunks: list[str] = []
    current_parts: list[str] = []

    for unit in units:
        candidate = " ".join(
            current_parts + [unit]
        ).strip()

        if (
            current_parts
            and len(candidate) > max_chars
        ):
            chunks.append(
                " ".join(current_parts).strip()
            )
            current_parts = [unit]
        else:
            current_parts.append(unit)

    if current_parts:
        chunks.append(
            " ".join(current_parts).strip()
        )

    return [
        chunk
        for chunk in chunks
        if chunk
    ]


def create_fragments(
    resources: Iterable[Mapping[str, Any]],
    *,
    max_page_chars: int = 900,
) -> list[dict[str, Any]]:
    """Create Page chunks and one fragment per Quiz question."""

    fragments: list[dict[str, Any]] = []

    for resource in resources:
        resource_id = normalize_whitespace(
            resource.get("resource_id")
        )

        resource_type = normalize_whitespace(
            resource.get("resource_type")
        )

        title = normalize_whitespace(
            resource.get("title")
        )

        if not resource_id:
            continue

        if resource_type == "quiz_question":
            fragment_text = normalize_whitespace(
                resource.get("search_text")
                or resource.get("text")
            )

            fragment_texts = (
                [fragment_text]
                if fragment_text
                else []
            )

            fragment_type = "quiz_question"

        elif resource_type == "page":
            fragment_texts = chunk_text(
                str(resource.get("text", "")),
                max_chars=max_page_chars,
            )

            fragment_type = "page_chunk"

        else:
            fragment_texts = chunk_text(
                str(resource.get("text", "")),
                max_chars=max_page_chars,
            )

            fragment_type = "resource_chunk"

        total_for_resource = len(fragment_texts)

        for index, fragment_text in enumerate(
            fragment_texts,
            start=1,
        ):
            fragment_id = (
                f"{resource_id}#f{index:03d}"
            )

            fragments.append(
                {
                    "fragment_id": fragment_id,
                    "resource_id": resource_id,
                    "resource_type": resource_type,
                    "fragment_type": fragment_type,
                    "fragment_index": index,
                    "fragments_in_resource":
                        total_for_resource,
                    "course_id": resource.get(
                        "course_id"
                    ),
                    "course_shortname":
                        resource.get(
                            "course_shortname",
                            "",
                        ),
                    "course_fullname":
                        resource.get(
                            "course_fullname",
                            "",
                        ),
                    "course_module_id":
                        resource.get(
                            "course_module_id"
                        ),
                    "section_id": resource.get(
                        "section_id"
                    ),
                    "section_number": resource.get(
                        "section_number"
                    ),
                    "section_name": resource.get(
                        "section_name",
                        "",
                    ),
                    "activity_id": resource.get(
                        "activity_id"
                    ),
                    "activity_name": resource.get(
                        "activity_name",
                        "",
                    ),
                    "source_item_id": resource.get(
                        "source_item_id"
                    ),
                    "title": title,
                    "text": fragment_text,
                    "search_text": combine_text(
                        title,
                        fragment_text,
                    ),
                    "character_count": len(
                        fragment_text
                    ),
                    "word_count": len(
                        fragment_text.split()
                    ),
                    "fragmentation_version": "1.0",
                    "metadata": {
                        "source_extraction":
                            resource.get(
                                "source_extraction"
                            ),
                        "source_resource_metadata":
                            resource.get(
                                "metadata",
                                {},
                            ),
                    },
                }
            )

    return fragments


def validate_fragments(
    *,
    resources: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    max_page_chars: int,
) -> dict[str, Any]:
    """Validate coverage, ordering and fragment contents."""

    resource_ids = {
        str(resource.get("resource_id", "")).strip()
        for resource in resources
        if str(
            resource.get("resource_id", "")
        ).strip()
    }

    fragment_ids = [
        str(fragment.get("fragment_id", "")).strip()
        for fragment in fragments
    ]

    represented_resource_ids = {
        str(fragment.get("resource_id", "")).strip()
        for fragment in fragments
        if str(
            fragment.get("resource_id", "")
        ).strip()
    }

    missing_resources = sorted(
        resource_ids - represented_resource_ids
    )

    unknown_resources = sorted(
        represented_resource_ids - resource_ids
    )

    duplicate_fragment_ids = sorted(
        fragment_id
        for fragment_id, count in Counter(
            fragment_ids
        ).items()
        if fragment_id and count > 1
    )

    empty_fragment_ids = [
        fragment.get("fragment_id")
        for fragment in fragments
        if not str(
            fragment.get("text", "")
        ).strip()
    ]

    empty_search_text_ids = [
        fragment.get("fragment_id")
        for fragment in fragments
        if not str(
            fragment.get("search_text", "")
        ).strip()
    ]

    oversized_page_fragments = [
        fragment.get("fragment_id")
        for fragment in fragments
        if (
            fragment.get("fragment_type")
            == "page_chunk"
            and int(
                fragment.get(
                    "character_count",
                    0,
                )
            )
            > max_page_chars
        )
    ]

    fragments_by_resource: defaultdict[
        str,
        list[Mapping[str, Any]],
    ] = defaultdict(list)

    for fragment in fragments:
        fragments_by_resource[
            str(fragment.get("resource_id", ""))
        ].append(fragment)

    invalid_fragment_order: list[str] = []

    for resource_id, resource_fragments in (
        fragments_by_resource.items()
    ):
        indexes = sorted(
            int(
                fragment.get(
                    "fragment_index",
                    0,
                )
            )
            for fragment in resource_fragments
        )

        expected_indexes = list(
            range(1, len(indexes) + 1)
        )

        if indexes != expected_indexes:
            invalid_fragment_order.append(
                resource_id
            )

    quiz_resource_ids = {
        str(resource.get("resource_id", "")).strip()
        for resource in resources
        if resource.get("resource_type")
        == "quiz_question"
    }

    invalid_quiz_fragment_counts = sorted(
        resource_id
        for resource_id in quiz_resource_ids
        if len(
            fragments_by_resource.get(
                resource_id,
                [],
            )
        )
        != 1
    )

    type_counts = Counter(
        str(fragment.get("fragment_type", ""))
        for fragment in fragments
    )

    course_counts = Counter(
        str(
            fragment.get(
                "course_shortname",
                "",
            )
        )
        for fragment in fragments
    )

    fragment_counts = [
        len(resource_fragments)
        for resource_fragments
        in fragments_by_resource.values()
    ]

    character_counts = [
        int(
            fragment.get(
                "character_count",
                0,
            )
        )
        for fragment in fragments
    ]

    passed = (
        len(resources) == 20
        and len(quiz_resource_ids) == 12
        and len(fragments) >= 20
        and type_counts["quiz_question"] == 12
        and not missing_resources
        and not unknown_resources
        and not duplicate_fragment_ids
        and not empty_fragment_ids
        and not empty_search_text_ids
        and not oversized_page_fragments
        and not invalid_fragment_order
        and not invalid_quiz_fragment_counts
    )

    return {
        "source_resources": len(resources),
        "total_fragments": len(fragments),
        "represented_resources":
            len(represented_resource_ids),
        "fragments_by_type":
            dict(type_counts),
        "fragments_by_course":
            dict(course_counts),
        "fragments_per_resource": {
            "minimum": (
                min(fragment_counts)
                if fragment_counts
                else 0
            ),
            "maximum": (
                max(fragment_counts)
                if fragment_counts
                else 0
            ),
            "average": (
                round(
                    mean(fragment_counts),
                    3,
                )
                if fragment_counts
                else 0
            ),
        },
        "fragment_characters": {
            "minimum": (
                min(character_counts)
                if character_counts
                else 0
            ),
            "maximum": (
                max(character_counts)
                if character_counts
                else 0
            ),
            "average": (
                round(
                    mean(character_counts),
                    3,
                )
                if character_counts
                else 0
            ),
        },
        "max_page_characters":
            max_page_chars,
        "missing_resources":
            missing_resources,
        "unknown_resources":
            unknown_resources,
        "duplicate_fragment_ids":
            duplicate_fragment_ids,
        "empty_fragment_ids":
            empty_fragment_ids,
        "empty_search_text_ids":
            empty_search_text_ids,
        "oversized_page_fragments":
            oversized_page_fragments,
        "invalid_fragment_order":
            invalid_fragment_order,
        "invalid_quiz_fragment_counts":
            invalid_quiz_fragment_counts,
        "passed": passed,
    }


def write_jsonl(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> Path:
    """Write fragment records as UTF-8 JSON Lines."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(
                    dict(record),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    return output_path.resolve()
