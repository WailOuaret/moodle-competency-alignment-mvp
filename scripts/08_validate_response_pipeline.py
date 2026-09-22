"""Exercise the LLM response validator with an abstention baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.llm_validation import (
    load_jsonl,
    validate_response_collection,
    write_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

TASKS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "llm_tasks.jsonl"
)

RESPONSES_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "abstention_baseline_responses.jsonl"
)

VALIDATED_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "abstention_baseline_validated.jsonl"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "abstention_baseline_manifest.json"
)


def main() -> int:
    try:
        tasks = load_jsonl(TASKS_PATH)

        responses = [
            {
                "fragment_id": task["fragment_id"],
                "selected": [],
                "abstain": True,
                "overall_reason": (
                    "Deterministic baseline: no automatic "
                    "competency decision was attempted."
                ),
                "model_provider": "deterministic_baseline",
                "model_name": "always_abstain_v1",
            }
            for task in tasks
        ]

        responses_path = write_jsonl(
            responses,
            RESPONSES_PATH,
        )

        (
            validated_records,
            validation,
        ) = validate_response_collection(
            tasks=tasks,
            responses=responses,
        )

        validated_path = write_jsonl(
            validated_records,
            VALIDATED_PATH,
        )

        MANIFEST_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest = {
            "purpose": (
                "Validate the response schema before "
                "connecting a real language model."
            ),
            "baseline": "always_abstain",
            "input_tasks": str(
                TASKS_PATH.relative_to(PROJECT_ROOT)
            ),
            "responses_file": str(
                responses_path.relative_to(PROJECT_ROOT)
            ),
            "validated_file": str(
                validated_path.relative_to(PROJECT_ROOT)
            ),
            "validation": validation,
        }

        MANIFEST_PATH.write_text(
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
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print("=== LLM RESPONSE PIPELINE VALIDATION ===")
    print(
        f"Source tasks: "
        f"{validation['source_tasks']}"
    )
    print(
        f"Source responses: "
        f"{validation['source_responses']}"
    )
    print(
        f"Validated responses: "
        f"{validation['validated_responses']}"
    )
    print(
        f"Valid responses: "
        f"{validation['valid_responses']}"
    )
    print(
        f"Invalid responses: "
        f"{validation['invalid_responses']}"
    )
    print(
        f"Selected alignments: "
        f"{validation['selected_alignments']}"
    )
    print(
        f"Abstentions: "
        f"{validation['abstentions']}"
    )

    print(
        "\nMissing responses: "
        f"{len(validation['missing_responses'])}"
    )
    print(
        "Unknown responses: "
        f"{len(validation['unknown_responses'])}"
    )
    print(
        "Duplicate response fragments: "
        f"{len(validation['duplicate_response_fragments'])}"
    )

    print(f"\nResponses: {responses_path}")
    print(f"Validated: {validated_path}")
    print(f"Manifest: {MANIFEST_PATH}")

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
