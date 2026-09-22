"""Create pedagogical fragments for retrieval and alignment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from moodle_competency.fragmentation import (
    create_fragments,
    load_jsonl,
    validate_fragments,
    write_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "resources.jsonl"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fragments.jsonl"
)

DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fragments_manifest.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Split Moodle Pages into pedagogical chunks while "
            "keeping every Quiz question as one fragment."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Normalized resources JSONL file.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output fragments JSONL file.",
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Output validation-manifest file.",
    )

    parser.add_argument(
        "--max-page-chars",
        type=int,
        default=900,
        help="Maximum number of characters in one Page fragment.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        resources = load_jsonl(
            arguments.input.resolve()
        )

        fragments = create_fragments(
            resources,
            max_page_chars=arguments.max_page_chars,
        )

        validation = validate_fragments(
            resources=resources,
            fragments=fragments,
            max_page_chars=arguments.max_page_chars,
        )

        output_path = write_jsonl(
            fragments,
            arguments.output.resolve(),
        )

        manifest_path = arguments.manifest.resolve()
        manifest_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest = {
            "input_file": str(
                arguments.input.resolve()
            ),
            "output_file": str(output_path),
            "fragmentation_version": "1.0",
            "configuration": {
                "max_page_characters":
                    arguments.max_page_chars,
                "quiz_question_strategy":
                    "one_question_one_fragment",
                "page_strategy":
                    "paragraph_sentence_greedy_chunking",
            },
            "validation": validation,
        }

        manifest_path.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print("=== PEDAGOGICAL FRAGMENTATION ===")
    print(
        f"Source resources: "
        f"{validation['source_resources']}"
    )
    print(
        f"Represented resources: "
        f"{validation['represented_resources']}"
    )
    print(
        f"Total fragments: "
        f"{validation['total_fragments']}"
    )

    print("\nFragments by type:")
    for fragment_type, count in sorted(
        validation["fragments_by_type"].items()
    ):
        print(f"- {fragment_type}: {count}")

    print("\nFragments by course:")
    for course, count in sorted(
        validation["fragments_by_course"].items()
    ):
        print(f"- {course}: {count}")

    statistics = validation[
        "fragments_per_resource"
    ]

    print("\nFragments per resource:")
    print(f"- Minimum: {statistics['minimum']}")
    print(f"- Maximum: {statistics['maximum']}")
    print(f"- Average: {statistics['average']}")

    print(
        "\nMissing resources: "
        f"{len(validation['missing_resources'])}"
    )
    print(
        "Unknown resources: "
        f"{len(validation['unknown_resources'])}"
    )
    print(
        "Duplicate fragment IDs: "
        f"{len(validation['duplicate_fragment_ids'])}"
    )
    print(
        "Empty fragments: "
        f"{len(validation['empty_fragment_ids'])}"
    )
    print(
        "Oversized Page fragments: "
        f"{len(validation['oversized_page_fragments'])}"
    )
    print(
        "Invalid Quiz fragment counts: "
        f"{len(validation['invalid_quiz_fragment_counts'])}"
    )

    print(f"\nDataset: {output_path}")
    print(f"Manifest: {manifest_path}")

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
