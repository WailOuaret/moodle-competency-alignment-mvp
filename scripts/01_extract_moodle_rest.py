"""Extract the Moodle MVP data through the configured REST service."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from moodle_competency.moodle_client import (
    MoodleAPIError,
    MoodleClient,
    write_json,
)
from moodle_competency.settings import load_settings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "api"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract site, course, section, Page and Quiz information "
            "from the local Moodle REST service."
        )
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where raw JSON responses will be stored.",
    )

    return parser.parse_args()


def count_modules(
    course_contents: dict[str, list[dict[str, Any]]],
) -> int:
    return sum(
        len(section.get("modules", []))
        for sections in course_contents.values()
        for section in sections
    )


def build_manifest(
    *,
    site_info: dict[str, Any],
    courses: dict[str, dict[str, Any]],
    course_contents: dict[str, list[dict[str, Any]]],
    pages_response: dict[str, Any],
    quizzes_response: dict[str, Any],
    output_files: dict[str, str],
) -> dict[str, Any]:
    page_records = pages_response.get("pages", [])
    quiz_records = quizzes_response.get("quizzes", [])

    return {
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "site": {
            "sitename": site_info.get("sitename"),
            "username": site_info.get("username"),
            "userid": site_info.get("userid"),
            "functions_available": len(site_info.get("functions", [])),
        },
        "counts": {
            "courses": len(courses),
            "sections": sum(
                len(sections)
                for sections in course_contents.values()
            ),
            "modules": count_modules(course_contents),
            "pages": len(page_records),
            "quizzes": len(quiz_records),
            "page_warnings": len(
                pages_response.get("warnings", [])
            ),
            "quiz_warnings": len(
                quizzes_response.get("warnings", [])
            ),
        },
        "courses": {
            shortname: {
                "id": course.get("id"),
                "shortname": course.get("shortname"),
                "fullname": course.get("fullname"),
            }
            for shortname, course in courses.items()
        },
        "output_files": output_files,
    }


def main() -> int:
    arguments = parse_arguments()
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings(override=True)

    try:
        with MoodleClient(settings) as client:
            site_info = client.get_site_info()

            courses = {
                settings.moodle_sw_shortname:
                    client.get_course_by_shortname(
                        settings.moodle_sw_shortname
                    ),
                settings.moodle_data_shortname:
                    client.get_course_by_shortname(
                        settings.moodle_data_shortname
                    ),
            }

            expected_ids = {
                settings.moodle_sw_shortname:
                    settings.moodle_sw_course_id,
                settings.moodle_data_shortname:
                    settings.moodle_data_course_id,
            }

            for shortname, expected_id in expected_ids.items():
                actual_id = int(courses[shortname]["id"])

                if actual_id != expected_id:
                    raise MoodleAPIError(
                        f"Course {shortname} has ID {actual_id}, "
                        f"but configuration expects {expected_id}."
                    )

            course_contents = {
                shortname: client.get_course_contents(
                    int(course["id"])
                )
                for shortname, course in courses.items()
            }

            pages_response = client.get_pages_by_courses(
                settings.course_ids
            )

            quizzes_response = client.get_quizzes_by_courses(
                settings.course_ids
            )

    except (MoodleAPIError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output_paths = {
        "site_info": output_dir / "site_info.json",
        "courses": output_dir / "courses.json",
        "course_contents_sw":
            output_dir / "course_contents_MVP-SW.json",
        "course_contents_data":
            output_dir / "course_contents_MVP-DATA.json",
        "pages": output_dir / "pages_by_courses.json",
        "quizzes": output_dir / "quizzes_by_courses.json",
        "manifest": output_dir / "extraction_manifest.json",
    }

    write_json(site_info, output_paths["site_info"])
    write_json(courses, output_paths["courses"])

    write_json(
        course_contents[settings.moodle_sw_shortname],
        output_paths["course_contents_sw"],
    )

    write_json(
        course_contents[settings.moodle_data_shortname],
        output_paths["course_contents_data"],
    )

    write_json(pages_response, output_paths["pages"])
    write_json(quizzes_response, output_paths["quizzes"])

    manifest = build_manifest(
        site_info=site_info,
        courses=courses,
        course_contents=course_contents,
        pages_response=pages_response,
        quizzes_response=quizzes_response,
        output_files={
            name: str(path.relative_to(PROJECT_ROOT))
            for name, path in output_paths.items()
            if name != "manifest"
        },
    )

    write_json(manifest, output_paths["manifest"])

    counts = manifest["counts"]

    print("=== MOODLE REST EXTRACTION ===")
    print(f"Site: {manifest['site']['sitename']}")
    print(f"API user: {manifest['site']['username']}")
    print(f"Courses: {counts['courses']}")
    print(f"Sections: {counts['sections']}")
    print(f"Modules: {counts['modules']}")
    print(f"Pages: {counts['pages']}")
    print(f"Quizzes: {counts['quizzes']}")
    print(f"Page warnings: {counts['page_warnings']}")
    print(f"Quiz warnings: {counts['quiz_warnings']}")
    print(f"Output directory: {output_dir}")
    print("Status: PASSED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
