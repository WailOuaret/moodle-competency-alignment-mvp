"""Run all constrained Gemini competency-alignment tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from moodle_competency.gemini_alignment import (
    GeminiAlignmentClient,
    GeminiAlignmentError,
    GeminiQuotaExhaustedError,
)
from moodle_competency.llm_validation import (
    load_jsonl,
    validate_alignment_response,
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
    / "gemini_responses.jsonl"
)

VALIDATED_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_validated.jsonl"
)

RAW_ATTEMPTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_raw_attempts.jsonl"
)

ERRORS_PATH = (
    PROJECT_ROOT
    / "reports"
    / "logs"
    / "gemini_alignment_errors.jsonl"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "gemini_run_manifest.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run constrained Gemini alignment for all Moodle fragments "
            "with checkpointing and strict response validation."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help=(
            "Process only the first N tasks. "
            "Use 0 to process all tasks."
        ),
    )

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=2.0,
        help="Delay between live Gemini requests.",
    )

    parser.add_argument(
        "--validation-attempts",
        type=int,
        default=3,
        help=(
            "Maximum model attempts when a response fails "
            "the strict local validator."
        ),
    )

    parser.add_argument(
        "--restart",
        action="store_true",
        help="Forbidden for this experiment. Kept only to fail loudly.",
    )

    return parser.parse_args()


def append_jsonl(
    path: Path,
    record: Mapping[str, Any],
) -> None:
    """Append one JSON object to a JSON Lines file."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                dict(record),
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )


def remove_previous_outputs() -> None:
    """Remove batch outputs while preserving the pilot files."""

    for path in (
        RESPONSES_PATH,
        VALIDATED_PATH,
        RAW_ATTEMPTS_PATH,
        ERRORS_PATH,
        MANIFEST_PATH,
    ):
        if path.exists():
            path.unlink()


def ordered_records(
    tasks: list[dict[str, Any]],
    records_by_fragment: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> list[dict[str, Any]]:
    """Return records in the original task order."""

    records: list[dict[str, Any]] = []

    for task in tasks:
        fragment_id = str(
            task.get("fragment_id", "")
        ).strip()

        record = records_by_fragment.get(
            fragment_id
        )

        if record is not None:
            records.append(dict(record))

    return records


def build_repair_task(
    *,
    original_task: Mapping[str, Any],
    previous_response: Mapping[str, Any],
    validation_errors: list[str],
) -> dict[str, Any]:
    """Create a retry prompt explaining the exact validator failures."""

    repair_task = dict(original_task)

    numbered_errors = "\n".join(
        f"{index}. {error}"
        for index, error in enumerate(
            validation_errors,
            start=1,
        )
    )

    previous_json = json.dumps(
        dict(previous_response),
        ensure_ascii=False,
        indent=2,
    )

    repair_task["prompt"] = (
        str(original_task.get("prompt", "")).strip()
        + "\n\n"
        + "CORRECTION REQUIRED\n"
        + "Your previous response failed the deterministic validator.\n"
        + "Return a completely corrected JSON object.\n\n"
        + "VALIDATION ERRORS:\n"
        + numbered_errors
        + "\n\n"
        + "PREVIOUS INVALID RESPONSE:\n"
        + previous_json
        + "\n\n"
        + "Copy every evidence quote exactly from FRAGMENT_TEXT. "
        + "Use only allowed competency IDs. "
        + "Prefer abstention when evidence is insufficient."
    )

    return repair_task


def load_valid_existing_responses(
    tasks: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Load valid checkpoints from an earlier interrupted run."""

    if not RESPONSES_PATH.exists():
        return {}, {}

    existing_responses = load_jsonl(
        RESPONSES_PATH
    )

    tasks_by_fragment = {
        str(task["fragment_id"]): task
        for task in tasks
    }

    responses_by_fragment: dict[
        str,
        dict[str, Any],
    ] = {}

    validated_by_fragment: dict[
        str,
        dict[str, Any],
    ] = {}

    for response in existing_responses:
        fragment_id = str(
            response.get("fragment_id", "")
        ).strip()

        task = tasks_by_fragment.get(
            fragment_id
        )

        if task is None:
            continue

        validated = validate_alignment_response(
            task=task,
            response=response,
        )

        if validated["valid"]:
            responses_by_fragment[
                fragment_id
            ] = response

            validated_by_fragment[
                fragment_id
            ] = validated

    return (
        responses_by_fragment,
        validated_by_fragment,
    )


def main() -> int:
    arguments = parse_arguments()

    if arguments.delay_seconds < 0:
        print(
            "ERROR: --delay-seconds cannot be negative.",
            file=sys.stderr,
        )
        return 1

    if arguments.validation_attempts <= 0:
        print(
            "ERROR: --validation-attempts must be positive.",
            file=sys.stderr,
        )
        return 1

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
        all_tasks = load_jsonl(TASKS_PATH)
    except (FileNotFoundError, ValueError) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    if arguments.limit > 0:
        tasks = all_tasks[:arguments.limit]
    else:
        tasks = all_tasks

    if not tasks:
        print(
            "ERROR: No alignment tasks were found.",
            file=sys.stderr,
        )
        return 1

    if arguments.restart:
        print(
            "ERROR: --restart is forbidden. "
            "Existing valid Gemini checkpoints must be kept.",
            file=sys.stderr,
        )
        return 1

    try:
        (
            responses_by_fragment,
            validated_by_fragment,
        ) = load_valid_existing_responses(
            tasks
        )
    except (FileNotFoundError, ValueError) as error:
        print(
            f"ERROR: Could not load checkpoints: {error}",
            file=sys.stderr,
        )
        return 1

    resumed_count = len(
        responses_by_fragment
    )
    missing_fragment_ids = [
        str(task["fragment_id"]).strip()
        for task in tasks
        if str(task["fragment_id"]).strip()
        not in responses_by_fragment
    ]

    new_completed = 0
    failed_fragment_ids: list[str] = []
    live_attempt_count = 0
    http_retry_count = 0
    quota_exhausted = False
    start_timestamp = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )

    prompt_tokens = 0
    candidate_tokens = 0
    total_tokens = 0

    print("=== GEMINI FULL ALIGNMENT RUN ===")
    print(f"Model: {model}")
    print("Temperature: 0")
    print(f"Selected tasks: {len(tasks)}")
    print(
        f"Valid responses resumed: "
        f"{resumed_count}"
    )
    print(f"Missing after checkpoint scan: {len(missing_fragment_ids)}")
    if missing_fragment_ids:
        print("Missing fragment IDs:")
        for fragment_id in missing_fragment_ids:
            print(f"- {fragment_id}")
    print(
        f"Delay between requests: "
        f"{arguments.delay_seconds} seconds"
    )
    print()

    try:
        with GeminiAlignmentClient(
            api_key=api_key,
            model=model,
        ) as client:

            for task_index, task in enumerate(
                tasks,
                start=1,
            ):
                fragment_id = str(
                    task["fragment_id"]
                )

                if fragment_id in responses_by_fragment:
                    print(
                        f"[{task_index}/{len(tasks)}] "
                        f"SKIP {fragment_id} "
                        "(valid checkpoint exists)"
                    )
                    continue

                current_task: Mapping[str, Any] = task
                last_response: dict[str, Any] = {}
                last_validation_errors: list[str] = []
                task_completed = False
                live_request_made = False

                for validation_attempt in range(
                    1,
                    arguments.validation_attempts + 1,
                ):
                    live_attempt_count += 1
                    live_request_made = True

                    try:
                        (
                            model_response,
                            raw_response,
                            usage,
                        ) = client.align(
                            current_task
                        )
                        http_retry_count += client.last_http_retries

                    except GeminiQuotaExhaustedError as error:
                        error_record = {
                            "fragment_id": fragment_id,
                            "task_index": task_index,
                            "validation_attempt":
                                validation_attempt,
                            "error_type":
                                type(error).__name__,
                            "error": str(error),
                        }
                        append_jsonl(
                            ERRORS_PATH,
                            error_record,
                        )
                        print(
                            f"[{task_index}/{len(tasks)}] "
                            f"QUOTA STOP {fragment_id}"
                        )
                        print(
                            "Daily/free-tier quota is exhausted. "
                            "Stopping without further API calls. "
                            "Checkpoints are preserved."
                        )
                        quota_exhausted = True
                        break

                    except GeminiAlignmentError as error:
                        error_record = {
                            "fragment_id": fragment_id,
                            "task_index": task_index,
                            "validation_attempt":
                                validation_attempt,
                            "error_type":
                                type(error).__name__,
                            "error": str(error),
                        }

                        append_jsonl(
                            ERRORS_PATH,
                            error_record,
                        )

                        print(
                            f"[{task_index}/{len(tasks)}] "
                            f"API ERROR {fragment_id} "
                            f"(attempt "
                            f"{validation_attempt}/"
                            f"{arguments.validation_attempts})"
                        )

                        if (
                            validation_attempt
                            < arguments.validation_attempts
                        ):
                            time.sleep(2.0)
                            continue

                        break

                    if usage.prompt_tokens is not None:
                        prompt_tokens += (
                            usage.prompt_tokens
                        )

                    if usage.candidate_tokens is not None:
                        candidate_tokens += (
                            usage.candidate_tokens
                        )

                    if usage.total_tokens is not None:
                        total_tokens += (
                            usage.total_tokens
                        )

                    validated = (
                        validate_alignment_response(
                            task=task,
                            response=model_response,
                        )
                    )

                    append_jsonl(
                        RAW_ATTEMPTS_PATH,
                        {
                            "fragment_id": fragment_id,
                            "task_index": task_index,
                            "validation_attempt":
                                validation_attempt,
                            "valid":
                                validated["valid"],
                            "validation_errors":
                                validated[
                                    "validation_errors"
                                ],
                            "usage":
                                usage.to_dict(),
                            "model_response":
                                model_response,
                            "raw_api_response":
                                raw_response,
                        },
                    )

                    if validated["valid"]:
                        responses_by_fragment[
                            fragment_id
                        ] = model_response

                        validated_by_fragment[
                            fragment_id
                        ] = validated

                        write_jsonl(
                            ordered_records(
                                tasks,
                                responses_by_fragment,
                            ),
                            RESPONSES_PATH,
                        )

                        write_jsonl(
                            ordered_records(
                                tasks,
                                validated_by_fragment,
                            ),
                            VALIDATED_PATH,
                        )

                        print(
                            f"[{task_index}/{len(tasks)}] "
                            f"PASS {fragment_id} "
                            "(validated, checkpoint saved)"
                        )

                        new_completed += 1
                        task_completed = True
                        break

                    last_response = model_response
                    last_validation_errors = list(
                        validated[
                            "validation_errors"
                        ]
                    )

                    print(
                        f"[{task_index}/{len(tasks)}] "
                        f"INVALID {fragment_id} "
                        f"(attempt "
                        f"{validation_attempt}/"
                        f"{arguments.validation_attempts}, "
                        f"errors="
                        f"{len(last_validation_errors)})"
                    )

                    if (
                        validation_attempt
                        < arguments.validation_attempts
                    ):
                        current_task = build_repair_task(
                            original_task=task,
                            previous_response=
                                last_response,
                            validation_errors=
                                last_validation_errors,
                        )

                        time.sleep(1.0)

                if quota_exhausted:
                    break

                if not task_completed:
                    failed_fragment_ids.append(
                        fragment_id
                    )

                    append_jsonl(
                        ERRORS_PATH,
                        {
                            "fragment_id":
                                fragment_id,
                            "task_index":
                                task_index,
                            "error_type":
                                "task_validation_failure",
                            "validation_errors":
                                last_validation_errors,
                            "last_response":
                                last_response,
                        },
                    )

                    print(
                        f"[{task_index}/{len(tasks)}] "
                        f"FAILED {fragment_id}"
                    )

                if (
                    live_request_made
                    and arguments.delay_seconds > 0
                    and task_index < len(tasks)
                ):
                    time.sleep(
                        arguments.delay_seconds
                    )

    except KeyboardInterrupt:
        print()
        print(
            "Run interrupted. Valid responses were "
            "checkpointed and will be resumed next time."
        )
        return 130

    final_responses = ordered_records(
        tasks,
        responses_by_fragment,
    )

    (
        final_validated,
        final_validation,
    ) = validate_response_collection(
        tasks=tasks,
        responses=final_responses,
    )

    write_jsonl(
        final_validated,
        VALIDATED_PATH,
    )

    selected_alignments = sum(
        len(record["selected"])
        for record in final_validated
    )

    abstentions = sum(
        record["abstain"] is True
        for record in final_validated
    )

    remaining_ids = [
        str(task["fragment_id"]).strip()
        for task in tasks
        if str(task["fragment_id"]).strip()
        not in responses_by_fragment
    ]
    end_timestamp = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )

    manifest = {
        "model_provider": "google_gemini",
        "model_id": model,
        "model_name": model,
        "temperature": 0,
        "prompt_version": "1.0",
        "schema_version": "1.0",
        "candidate_count": 5,
        "max_selections": 3,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "source_tasks": len(tasks),
        "preserved_valid_responses": resumed_count,
        "resumed_valid_responses": resumed_count,
        "newly_completed_responses": new_completed,
        "total_valid_now": len(responses_by_fragment),
        "remaining_responses": len(remaining_ids),
        "remaining_fragment_ids": remaining_ids,
        "live_attempts": live_attempt_count,
        "retry_count": http_retry_count,
        "quota_exhausted": quota_exhausted,
        "failed_fragment_ids": failed_fragment_ids,
        "current_session_usage": {
            "prompt_tokens": prompt_tokens,
            "candidate_tokens": candidate_tokens,
            "total_tokens": total_tokens,
        },
        "results": {
            "validated_responses": len(final_validated),
            "selected_alignments": selected_alignments,
            "abstentions": abstentions,
        },
        "output_files": {
            "responses": str(
                RESPONSES_PATH.relative_to(PROJECT_ROOT)
            ),
            "validated": str(
                VALIDATED_PATH.relative_to(PROJECT_ROOT)
            ),
            "raw_attempts": str(
                RAW_ATTEMPTS_PATH.relative_to(PROJECT_ROOT)
            ),
            "errors": str(
                ERRORS_PATH.relative_to(PROJECT_ROOT)
            ),
        },
        "validation": final_validation,
        "restart_used": False,
    }

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    print()
    print("=== GEMINI RUN SUMMARY ===")
    print(f"Tasks: {final_validation['source_tasks']}")
    print(f"Preserved valid before run: {resumed_count}")
    print(f"Newly completed valid: {new_completed}")
    print(f"Total valid now: {len(responses_by_fragment)} / {len(tasks)}")
    print(f"Remaining: {len(remaining_ids)}")
    if remaining_ids:
        print("Remaining fragment IDs:")
        for fragment_id in remaining_ids:
            print(f"- {fragment_id}")
    print(f"Invalid accepted: {final_validation['invalid_responses']}")
    print(f"HTTP retries this session: {http_retry_count}")
    print(f"Quota exhausted: {quota_exhausted}")
    print(f"Failed fragments: {len(failed_fragment_ids)}")

    print("\nCurrent-session token usage:")
    print(f"- Prompt: {prompt_tokens}")
    print(f"- Candidate: {candidate_tokens}")
    print(f"- Total: {total_tokens}")

    print(f"\nResponses: {RESPONSES_PATH}")
    print(f"Validated: {VALIDATED_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")

    if quota_exhausted:
        print("Status: STOPPED_ON_QUOTA")
        return 2

    print(
        "Status: PASSED"
        if final_validation["passed"]
        else "Status: REVIEW REQUIRED"
    )

    return (
        0
        if final_validation["passed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
