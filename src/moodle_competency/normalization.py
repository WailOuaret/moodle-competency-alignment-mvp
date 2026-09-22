"""Normalize Moodle Pages and Quiz questions into one resource schema."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from moodle_competency.html_clean import (
    combine_text,
    html_to_text,
    normalize_whitespace,
)


def load_json(path: Path) -> Any:
    """Load a UTF-8 JSON file."""

    return json.loads(path.read_text(encoding="utf-8"))


def optional_integer(value: Any) -> int | None:
    """Convert a value to an integer when possible."""

    if value is None or str(value).strip() == "":
        return None

    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def optional_float(value: Any) -> float | None:
    """Convert a value to a float when possible."""

    if value is None or str(value).strip() == "":
        return None

    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def build_course_lookup(
    courses_response: dict[str, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Index Moodle courses by course ID."""

    courses: dict[int, dict[str, Any]] = {}

    for fallback_shortname, course in courses_response.items():
        course_id = optional_integer(course.get("id"))

        if course_id is None:
            continue

        courses[course_id] = {
            "id": course_id,
            "shortname": normalize_whitespace(
                course.get("shortname") or fallback_shortname
            ),
            "fullname": normalize_whitespace(
                course.get("fullname") or fallback_shortname
            ),
        }

    return courses


def build_module_indexes(
    course_contents: dict[int, list[dict[str, Any]]],
) -> tuple[
    dict[int, dict[str, Any]],
    dict[tuple[int, str, int], dict[str, Any]],
]:
    """Index course modules by CMID and activity instance."""

    by_cmid: dict[int, dict[str, Any]] = {}
    by_instance: dict[
        tuple[int, str, int],
        dict[str, Any],
    ] = {}

    for raw_course_id, sections in course_contents.items():
        course_id = int(raw_course_id)

        for section in sections:
            section_id = optional_integer(section.get("id"))
            section_number = optional_integer(
                section.get("section")
            )
            section_name = normalize_whitespace(
                section.get("name")
            )

            for module in section.get("modules", []):
                cmid = optional_integer(module.get("id"))
                instance_id = optional_integer(
                    module.get("instance")
                )
                module_type = normalize_whitespace(
                    module.get("modname")
                )

                record = {
                    "course_module_id": cmid,
                    "course_id": course_id,
                    "instance_id": instance_id,
                    "module_type": module_type,
                    "module_name": normalize_whitespace(
                        module.get("name")
                    ),
                    "section_id": section_id,
                    "section_number": section_number,
                    "section_name": section_name,
                    "visible": module.get("visible"),
                    "completion": module.get("completion"),
                    "completion_data": module.get(
                        "completiondata"
                    ),
                }

                if cmid is not None:
                    by_cmid[cmid] = record

                if instance_id is not None and module_type:
                    key = (
                        course_id,
                        module_type,
                        instance_id,
                    )
                    by_instance[key] = record

    return by_cmid, by_instance


def find_module(
    *,
    course_id: int,
    module_type: str,
    instance_id: int,
    possible_cmid: int | None,
    modules_by_cmid: dict[int, dict[str, Any]],
    modules_by_instance: dict[
        tuple[int, str, int],
        dict[str, Any],
    ],
) -> dict[str, Any]:
    """Locate module metadata using CMID or activity instance."""

    if (
        possible_cmid is not None
        and possible_cmid in modules_by_cmid
    ):
        return modules_by_cmid[possible_cmid]

    return modules_by_instance.get(
        (course_id, module_type, instance_id),
        {},
    )


def normalize_pages(
    *,
    pages_response: dict[str, Any],
    courses: dict[int, dict[str, Any]],
    modules_by_cmid: dict[int, dict[str, Any]],
    modules_by_instance: dict[
        tuple[int, str, int],
        dict[str, Any],
    ],
) -> list[dict[str, Any]]:
    """Normalize Moodle Page records."""

    resources: list[dict[str, Any]] = []

    for page in pages_response.get("pages", []):
        page_id = optional_integer(page.get("id"))
        course_id = optional_integer(page.get("course"))

        if page_id is None or course_id is None:
            continue

        possible_cmid = optional_integer(
            page.get("coursemodule")
            or page.get("cmid")
            or page.get("coursemoduleid")
        )

        module = find_module(
            course_id=course_id,
            module_type="page",
            instance_id=page_id,
            possible_cmid=possible_cmid,
            modules_by_cmid=modules_by_cmid,
            modules_by_instance=modules_by_instance,
        )

        course = courses.get(
            course_id,
            {
                "shortname": "",
                "fullname": "",
            },
        )

        title = normalize_whitespace(page.get("name"))
        intro_text = html_to_text(page.get("intro"))
        content_text = html_to_text(page.get("content"))
        clean_text = combine_text(intro_text, content_text)

        resources.append(
            {
                "resource_id": f"page:{page_id}",
                "resource_type": "page",
                "source_extraction": "moodle_rest",
                "course_id": course_id,
                "course_shortname": course["shortname"],
                "course_fullname": course["fullname"],
                "course_module_id": module.get(
                    "course_module_id",
                    possible_cmid,
                ),
                "section_id": module.get("section_id"),
                "section_number": module.get(
                    "section_number"
                ),
                "section_name": module.get(
                    "section_name",
                    "",
                ),
                "activity_id": page_id,
                "activity_name": title,
                "source_item_id": page_id,
                "title": title,
                "text": clean_text,
                "search_text": combine_text(
                    title,
                    clean_text,
                ),
                "metadata": {
                    "intro_text": intro_text,
                    "content_format": page.get(
                        "contentformat"
                    ),
                    "intro_format": page.get(
                        "introformat"
                    ),
                    "visible": page.get(
                        "visible",
                        module.get("visible"),
                    ),
                    "time_modified": page.get(
                        "timemodified"
                    ),
                    "completion": module.get(
                        "completion"
                    ),
                    "completion_data": module.get(
                        "completion_data"
                    ),
                },
            }
        )

    return resources


def read_quiz_rows(
    csv_path: Path,
) -> list[dict[str, str]]:
    """Read the SQL Quiz-question CSV."""

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def normalize_quiz_questions(
    *,
    rows: Iterable[dict[str, str]],
    courses: dict[int, dict[str, Any]],
    modules_by_cmid: dict[int, dict[str, Any]],
    modules_by_instance: dict[
        tuple[int, str, int],
        dict[str, Any],
    ],
) -> list[dict[str, Any]]:
    """Group SQL rows and normalize individual Quiz questions."""

    grouped: defaultdict[
        tuple[int, int, int],
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        course_id = optional_integer(row.get("course_id"))
        quiz_id = optional_integer(row.get("quiz_id"))
        question_id = optional_integer(
            row.get("question_id")
        )

        if (
            course_id is None
            or quiz_id is None
            or question_id is None
        ):
            continue

        grouped[
            (course_id, quiz_id, question_id)
        ].append(row)

    resources: list[dict[str, Any]] = []

    def group_sort_key(
        item: tuple[
            tuple[int, int, int],
            list[dict[str, str]],
        ],
    ) -> tuple[int, int, int, int]:
        key, question_rows = item
        first = question_rows[0]

        return (
            key[0],
            key[1],
            optional_integer(first.get("slot")) or 0,
            key[2],
        )

    for (
        (course_id, quiz_id, question_id),
        question_rows,
    ) in sorted(grouped.items(), key=group_sort_key):
        first = question_rows[0]

        course = courses.get(
            course_id,
            {
                "shortname": normalize_whitespace(
                    first.get("course_shortname")
                ),
                "fullname": normalize_whitespace(
                    first.get("course_fullname")
                ),
            },
        )

        module = find_module(
            course_id=course_id,
            module_type="quiz",
            instance_id=quiz_id,
            possible_cmid=None,
            modules_by_cmid=modules_by_cmid,
            modules_by_instance=modules_by_instance,
        )

        answers: list[dict[str, Any]] = []
        seen_answer_ids: set[int] = set()

        for row in question_rows:
            answer_id = optional_integer(
                row.get("answer_id")
            )

            if (
                answer_id is None
                or answer_id in seen_answer_ids
            ):
                continue

            seen_answer_ids.add(answer_id)

            fraction = optional_float(
                row.get("answer_fraction")
            )

            answers.append(
                {
                    "answer_id": answer_id,
                    "text": html_to_text(
                        row.get("answer_text")
                    ),
                    "fraction": fraction,
                    "is_correct": (
                        fraction is not None
                        and fraction > 0
                    ),
                    "feedback": html_to_text(
                        row.get("answer_feedback")
                    ),
                }
            )

        question_text = html_to_text(
            first.get("question_text")
        )
        question_name = normalize_whitespace(
            first.get("question_name")
        )
        display_number = normalize_whitespace(
            first.get("displaynumber")
        )

        title = (
            question_name
            or (
                f"Question {display_number}"
                if display_number
                else f"Question {question_id}"
            )
        )

        answer_option_text = " | ".join(
            answer["text"]
            for answer in answers
            if answer["text"]
        )

        options_text = (
            f"Answer options: {answer_option_text}"
            if answer_option_text
            else ""
        )

        resources.append(
            {
                "resource_id": (
                    f"quiz_question:{quiz_id}:{question_id}"
                ),
                "resource_type": "quiz_question",
                "source_extraction": (
                    "postgresql_read_only"
                ),
                "course_id": course_id,
                "course_shortname": course["shortname"],
                "course_fullname": course["fullname"],
                "course_module_id": module.get(
                    "course_module_id"
                ),
                "section_id": module.get("section_id"),
                "section_number": module.get(
                    "section_number"
                ),
                "section_name": module.get(
                    "section_name",
                    "",
                ),
                "activity_id": quiz_id,
                "activity_name": normalize_whitespace(
                    first.get("quiz_name")
                ),
                "source_item_id": question_id,
                "title": title,
                "text": question_text,
                "search_text": combine_text(
                    title,
                    question_text,
                    options_text,
                ),
                "metadata": {
                    "quiz_slot_id": optional_integer(
                        first.get("quiz_slot_id")
                    ),
                    "slot": optional_integer(
                        first.get("slot")
                    ),
                    "display_number": display_number,
                    "question_type":
                        normalize_whitespace(
                            first.get("question_type")
                        ),
                    "question_bank_entry_id":
                        optional_integer(
                            first.get(
                                "question_bank_entry_id"
                            )
                        ),
                    "question_version_id":
                        optional_integer(
                            first.get(
                                "question_version_id"
                            )
                        ),
                    "question_version":
                        optional_integer(
                            first.get(
                                "question_version"
                            )
                        ),
                    "question_version_status":
                        normalize_whitespace(
                            first.get(
                                "question_version_status"
                            )
                        ),
                    "default_mark": optional_float(
                        first.get("default_mark")
                    ),
                    "maximum_mark": optional_float(
                        first.get("maxmark")
                    ),
                    "general_feedback": html_to_text(
                        first.get("general_feedback")
                    ),
                    "answers": answers,
                    "answer_count": len(answers),
                    "correct_answer_count": sum(
                        answer["is_correct"]
                        for answer in answers
                    ),
                    "completion": module.get(
                        "completion"
                    ),
                    "completion_data": module.get(
                        "completion_data"
                    ),
                },
            }
        )

    return resources


def validate_resources(
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the normalized MVP dataset."""

    resource_ids = [
        resource["resource_id"]
        for resource in resources
    ]

    type_counts = Counter(
        resource["resource_type"]
        for resource in resources
    )

    course_counts = Counter(
        resource["course_shortname"]
        for resource in resources
    )

    empty_text = [
        resource["resource_id"]
        for resource in resources
        if not resource.get("text", "").strip()
    ]

    missing_course_modules = [
        resource["resource_id"]
        for resource in resources
        if resource.get("course_module_id") is None
    ]

    duplicate_ids = (
        len(resource_ids) - len(set(resource_ids))
    )

    invalid_quiz_answers: list[str] = []

    for resource in resources:
        if resource["resource_type"] != "quiz_question":
            continue

        metadata = resource["metadata"]

        if (
            metadata["answer_count"] != 4
            or metadata["correct_answer_count"] != 1
        ):
            invalid_quiz_answers.append(
                resource["resource_id"]
            )

    passed = (
        len(resources) == 20
        and type_counts["page"] == 8
        and type_counts["quiz_question"] == 12
        and course_counts["MVP-SW"] == 10
        and course_counts["MVP-DATA"] == 10
        and not empty_text
        and not missing_course_modules
        and duplicate_ids == 0
        and not invalid_quiz_answers
    )

    return {
        "total_resources": len(resources),
        "resource_types": dict(type_counts),
        "resources_per_course": dict(course_counts),
        "empty_text_resources": empty_text,
        "missing_course_module_resources":
            missing_course_modules,
        "duplicate_resource_ids": duplicate_ids,
        "invalid_quiz_answer_resources":
            invalid_quiz_answers,
        "passed": passed,
    }


def write_jsonl(
    resources: Iterable[dict[str, Any]],
    output_path: Path,
) -> Path:
    """Write resources as UTF-8 JSON Lines."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for resource in resources:
            handle.write(
                json.dumps(
                    resource,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    return output_path.resolve()
