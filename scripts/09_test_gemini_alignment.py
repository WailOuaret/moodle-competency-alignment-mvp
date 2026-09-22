"""Run and validate one real Gemini competency-alignment task."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from moodle_competency.gemini_alignment import (
    GeminiAlignmentClient,
    GeminiAlignmentError,
)
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

PILOT_RESPONSE_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_pilot_response.jsonl"
)

PILOT_VALIDATED_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_pilot_validated.jsonl"
)

PILOT_RAW_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_pilot_raw.json"
)

PILOT_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_pilot_manifest.json"
)


def main() -> int:
    load_dotenv(
        dotenv_path=PROJECT_ROOT / ".env",
        override=True,
    )

    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash",
    ).strip()

    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY is empty.",
            file=sys.stderr,
        )
        return 1

    try:
        tasks = load_jsonl(TASKS_PATH)

        if not tasks:
            raise ValueError(
                "No LLM tasks were found."
            )

        pilot_task = tasks[0]

        with GeminiAlignmentClient(
            api_key=api_key,
            model=model,
        ) as client:
            (
                model_response,
                raw_response,
                usage,
            ) = client.align(pilot_task)

        write_jsonl(
            [model_response],
            PILOT_RESPONSE_PATH,
        )

        (
            validated_records,
            validation,
        ) = validate_response_collection(
            tasks=[pilot_task],
            responses=[model_response],
        )

        write_jsonl(
            validated_records,
            PILOT_VALIDATED_PATH,
        )

        PILOT_RAW_PATH.write_text(
            json.dumps(
                raw_response,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        manifest = {
            "purpose": (
                "Validate one real Gemini alignment "
                "before processing all 35 tasks."
            ),
            "model_provider": "google_gemini",
            "model_name": model,
            "fragment_id":
                pilot_task["fragment_id"],
            "allowed_idnumbers":
                pilot_task["allowed_idnumbers"],
            "usage": usage.to_dict(),
            "validation": validation,
        }

        PILOT_MANIFEST_PATH.write_text(
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
        GeminiAlignmentError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    validated = validated_records[0]

    print("=== GEMINI ALIGNMENT PILOT ===")
    print(f"Model: {model}")
    print(
        f"Fragment: "
        f"{pilot_task['fragment_id']}"
    )
    print(
        "Allowed candidates: "
        + ", ".join(
            pilot_task["allowed_idnumbers"]
        )
    )
    print(
        f"Abstained: "
        f"{validated['abstain']}"
    )
    print(
        f"Selected competencies: "
        f"{len(validated['selected'])}"
    )

    for selection in validated["selected"]:
        print(
            f"- {selection['idnumber']} "
            f"(confidence "
            f"{selection['confidence']})"
        )

        for evidence in selection["evidence"]:
            print(f"  Evidence: {evidence}")

    print(
        f"\nValidation errors: "
        f"{len(validated['validation_errors'])}"
    )

    print("\nToken usage:")
    print(
        f"- Prompt: "
        f"{usage.prompt_tokens}"
    )
    print(
        f"- Candidate: "
        f"{usage.candidate_tokens}"
    )
    print(
        f"- Total: "
        f"{usage.total_tokens}"
    )

    print(
        f"\nResponse: "
        f"{PILOT_RESPONSE_PATH}"
    )
    print(
        f"Validated: "
        f"{PILOT_VALIDATED_PATH}"
    )
    print(
        f"Raw API output: "
        f"{PILOT_RAW_PATH}"
    )
    print(
        f"Manifest: "
        f"{PILOT_MANIFEST_PATH}"
    )

    print(
        "Status: PASSED"
        if validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
