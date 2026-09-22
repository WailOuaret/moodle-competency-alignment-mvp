"""Run constrained Ollama alignment as a separate optional experiment.

Reads the same BM25 Top-5 tasks as Gemini. Writes only under
data/experiments/. Never overwrites Gemini checkpoints.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from moodle_competency.llm_validation import (
    load_jsonl,
    validate_alignment_response,
    write_jsonl,
)
from moodle_competency.ollama_alignment import (
    OllamaAlignmentClient,
    OllamaAlignmentError,
    default_ollama_host,
    default_ollama_model,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = PROJECT_ROOT / "data" / "interim" / "llm_tasks.jsonl"
EXPERIMENT_DIR = PROJECT_ROOT / "data" / "experiments"
RESPONSES_PATH = EXPERIMENT_DIR / "ollama_constrained_responses.jsonl"
VALIDATED_PATH = EXPERIMENT_DIR / "ollama_constrained_validated.jsonl"
RAW_ATTEMPTS_PATH = EXPERIMENT_DIR / "ollama_constrained_raw_attempts.jsonl"
MANIFEST_PATH = EXPERIMENT_DIR / "ollama_constrained_manifest.json"
ERRORS_PATH = (
    PROJECT_ROOT / "reports" / "logs" / "ollama_alignment_errors.jsonl"
)
GEMINI_FORBIDDEN = (
    PROJECT_ROOT / "data" / "interim" / "gemini_responses.jsonl",
    PROJECT_ROOT / "data" / "interim" / "gemini_validated.jsonl",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run BM25 Top-5 + constrained Ollama. "
            "Does not modify Gemini outputs."
        )
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--validation-attempts", type=int, default=3)
    parser.add_argument(
        "--model",
        default="",
        help="Override OLLAMA_MODEL (default: env or mistral:latest).",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Rebuild this Ollama experiment only. Gemini files stay untouched.",
    )
    return parser.parse_args()


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(dict(record), ensure_ascii=False, sort_keys=True)
            + "\n"
        )


def ordered_records(
    tasks: list[dict[str, Any]],
    records_by_fragment: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for task in tasks:
        fragment_id = str(task.get("fragment_id", "")).strip()
        record = records_by_fragment.get(fragment_id)

        if record is not None:
            records.append(dict(record))

    return records


def build_repair_task(
    *,
    original_task: Mapping[str, Any],
    previous_response: Mapping[str, Any],
    validation_errors: list[str],
) -> dict[str, Any]:
    repair_task = dict(original_task)
    numbered_errors = "\n".join(
        f"{index}. {error}"
        for index, error in enumerate(validation_errors, start=1)
    )
    previous_json = json.dumps(
        dict(previous_response),
        ensure_ascii=False,
        indent=2,
    )
    repair_task["prompt"] = (
        str(original_task.get("prompt", "")).strip()
        + "\n\nCORRECTION REQUIRED\n"
        + "Your previous response failed the deterministic validator.\n"
        + "Return a completely corrected JSON object.\n\n"
        + "VALIDATION ERRORS:\n"
        + numbered_errors
        + "\n\nPREVIOUS INVALID RESPONSE:\n"
        + previous_json
        + "\n\nCopy every evidence quote exactly from FRAGMENT_TEXT. "
        + "Use only allowed competency IDs. "
        + "Prefer abstention when evidence is insufficient."
    )
    return repair_task


def load_valid_existing_responses(
    tasks: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not RESPONSES_PATH.exists():
        return {}, {}

    existing_responses = load_jsonl(RESPONSES_PATH)
    tasks_by_fragment = {
        str(task["fragment_id"]): task for task in tasks
    }
    responses_by_fragment: dict[str, dict[str, Any]] = {}
    validated_by_fragment: dict[str, dict[str, Any]] = {}

    for response in existing_responses:
        fragment_id = str(response.get("fragment_id", "")).strip()
        task = tasks_by_fragment.get(fragment_id)

        if task is None:
            continue

        validated = validate_alignment_response(task=task, response=response)

        if validated["valid"]:
            responses_by_fragment[fragment_id] = response
            validated_by_fragment[fragment_id] = validated

    return responses_by_fragment, validated_by_fragment


def assert_gemini_untouched(before: dict[Path, tuple[int, str]]) -> None:
    for path, (mtime_ns, digest_head) in before.items():
        if not path.exists():
            raise RuntimeError(f"Protected Gemini file disappeared: {path}")

        current = (path.stat().st_mtime_ns, path.read_text(encoding="utf-8")[:80])

        if current != (mtime_ns, digest_head):
            raise RuntimeError(
                f"Refusing to continue: {path} changed during the Ollama run."
            )


def snapshot_gemini() -> dict[Path, tuple[int, str]]:
    snapshot: dict[Path, tuple[int, str]] = {}

    for path in GEMINI_FORBIDDEN:
        if path.exists():
            snapshot[path] = (
                path.stat().st_mtime_ns,
                path.read_text(encoding="utf-8")[:80],
            )

    return snapshot


def main() -> int:
    arguments = parse_arguments()
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass

    if arguments.delay_seconds < 0:
        print("ERROR: --delay-seconds cannot be negative.", file=sys.stderr)
        return 1

    if arguments.validation_attempts <= 0:
        print("ERROR: --validation-attempts must be positive.", file=sys.stderr)
        return 1

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)
    model = arguments.model.strip() or default_ollama_model()
    host = default_ollama_host()
    gemini_snapshot = snapshot_gemini()

    try:
        all_tasks = load_jsonl(TASKS_PATH)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    tasks = all_tasks[: arguments.limit] if arguments.limit > 0 else all_tasks

    if not tasks:
        print("ERROR: No alignment tasks were found.", file=sys.stderr)
        return 1

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

    if arguments.restart:
        for path in (RESPONSES_PATH, VALIDATED_PATH, RAW_ATTEMPTS_PATH, MANIFEST_PATH):
            if path.exists():
                path.unlink()

    try:
        responses_by_fragment, validated_by_fragment = (
            load_valid_existing_responses(tasks)
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: Could not load Ollama checkpoints: {error}", file=sys.stderr)
        return 1

    missing_fragment_ids = [
        str(task["fragment_id"]).strip()
        for task in tasks
        if str(task["fragment_id"]).strip() not in responses_by_fragment
    ]
    failed_fragment_ids: list[str] = []
    new_completed = 0
    live_attempt_count = 0
    start_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    print("=== OLLAMA CONSTRAINED EXPERIMENT ===")
    print("This run does not modify Gemini checkpoints.")
    print(f"Host: {host}")
    print(f"Model: {model}")
    print("Temperature: 0")
    print(f"Selected tasks: {len(tasks)}")
    print(f"Valid Ollama checkpoints: {len(responses_by_fragment)}")
    print(f"Missing: {len(missing_fragment_ids)}")
    print()

    try:
        with OllamaAlignmentClient(host=host, model=model) as client:
            client.require_model()
            print(f"Transport: {client.last_transport}")
            print()

            for task_index, task in enumerate(tasks, start=1):
                fragment_id = str(task["fragment_id"])

                if fragment_id in responses_by_fragment:
                    print(
                        f"[{task_index}/{len(tasks)}] SKIP {fragment_id} "
                        "(valid Ollama checkpoint exists)"
                    )
                    continue

                current_task: Mapping[str, Any] = task
                task_completed = False

                for validation_attempt in range(1, arguments.validation_attempts + 1):
                    live_attempt_count += 1

                    try:
                        model_response, raw_response, usage = client.align(
                            current_task
                        )
                    except OllamaAlignmentError as error:
                        append_jsonl(
                            ERRORS_PATH,
                            {
                                "fragment_id": fragment_id,
                                "validation_attempt": validation_attempt,
                                "error": str(error),
                            },
                        )
                        print(
                            f"[{task_index}/{len(tasks)}] API ERROR {fragment_id} "
                            f"(attempt {validation_attempt}/"
                            f"{arguments.validation_attempts})"
                        )

                        if validation_attempt < arguments.validation_attempts:
                            time.sleep(2.0)
                            continue

                        break

                    validated = validate_alignment_response(
                        task=task,
                        response=model_response,
                    )
                    append_jsonl(
                        RAW_ATTEMPTS_PATH,
                        {
                            "fragment_id": fragment_id,
                            "validation_attempt": validation_attempt,
                            "valid": validated["valid"],
                            "validation_errors": validated["validation_errors"],
                            "usage": usage.to_dict(),
                            "model_response": model_response,
                            "raw_api_response": raw_response,
                        },
                    )

                    if validated["valid"]:
                        responses_by_fragment[fragment_id] = model_response
                        validated_by_fragment[fragment_id] = validated
                        write_jsonl(
                            ordered_records(tasks, responses_by_fragment),
                            RESPONSES_PATH,
                        )
                        write_jsonl(
                            ordered_records(tasks, validated_by_fragment),
                            VALIDATED_PATH,
                        )
                        print(
                            f"[{task_index}/{len(tasks)}] PASS {fragment_id} "
                            "(validated, Ollama checkpoint saved)"
                        )
                        new_completed += 1
                        task_completed = True
                        break

                    print(
                        f"[{task_index}/{len(tasks)}] INVALID {fragment_id} "
                        f"(attempt {validation_attempt}/"
                        f"{arguments.validation_attempts}, errors="
                        f"{len(validated['validation_errors'])})"
                    )

                    if validation_attempt < arguments.validation_attempts:
                        current_task = build_repair_task(
                            original_task=task,
                            previous_response=model_response,
                            validation_errors=list(
                                validated["validation_errors"]
                            ),
                        )
                        time.sleep(1.0)

                if not task_completed:
                    failed_fragment_ids.append(fragment_id)

                if arguments.delay_seconds and task_index < len(tasks):
                    time.sleep(arguments.delay_seconds)

                assert_gemini_untouched(gemini_snapshot)

    except OllamaAlignmentError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    manifest = {
        "experiment": "POST-HOC LOCAL OLLAMA COMPARISON",
        "not_part_of_original_gemini_run": True,
        "model_provider": "ollama",
        "model_name": model,
        "host": host,
        "temperature": 0,
        "candidate_restriction": "BM25 Top-5",
        "max_selections": 3,
        "task_count": len(tasks),
        "valid_count": len(validated_by_fragment),
        "new_completed": new_completed,
        "failed_fragment_ids": failed_fragment_ids,
        "live_attempt_count": live_attempt_count,
        "started_at": start_timestamp,
        "finished_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "outputs": {
            "responses": str(RESPONSES_PATH.relative_to(PROJECT_ROOT)),
            "validated": str(VALIDATED_PATH.relative_to(PROJECT_ROOT)),
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    assert_gemini_untouched(gemini_snapshot)
    print()
    print(f"Valid Ollama responses: {len(validated_by_fragment)}/{len(tasks)}")
    print(f"Wrote {VALIDATED_PATH}")

    if failed_fragment_ids:
        print("Failed fragments:")
        for fragment_id in failed_fragment_ids:
            print(f"- {fragment_id}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
