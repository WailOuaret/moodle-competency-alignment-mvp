"""Build constrained, provider-independent LLM alignment tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def load_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    """Load JSON objects from a UTF-8 JSON Lines file."""

    if not path.exists():
        raise FileNotFoundError(
            f"JSONL file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}."
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} of {path} "
                    "is not a JSON object."
                )

            records.append(record)

    return records


def build_competency_lookup(
    competencies: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Index normalized competencies by exact idnumber."""

    lookup: dict[str, dict[str, Any]] = {}

    for competency in competencies:
        idnumber = str(
            competency.get("idnumber", "")
        ).strip()

        if not idnumber:
            raise ValueError(
                "A competency is missing its idnumber."
            )

        if idnumber in lookup:
            raise ValueError(
                f"Duplicate competency idnumber: {idnumber}"
            )

        lookup[idnumber] = dict(competency)

    return lookup


def build_output_contract(
    fragment_id: str,
) -> dict[str, Any]:
    """Return the exact response structure required from the LLM."""

    return {
        "fragment_id": fragment_id,
        "selected": [
            {
                "idnumber": "One allowed candidate idnumber",
                "evidence": [
                    "Exact contiguous quote copied from fragment_text"
                ],
                "reason": (
                    "Brief explanation of why the evidence "
                    "supports this competency"
                ),
                "confidence": (
                    "Floating-point number from 0.0 to 1.0"
                ),
            }
        ],
        "abstain": False,
        "overall_reason": (
            "Brief overall decision explanation"
        ),
    }


def build_prompt(
    *,
    fragment_id: str,
    fragment_text: str,
    title: str,
    activity_name: str,
    course_shortname: str,
    candidates: Sequence[Mapping[str, Any]],
) -> str:
    """Build the constrained alignment prompt."""

    candidate_lines: list[str] = []

    for candidate in candidates:
        hierarchy = " > ".join(
            str(value)
            for value in candidate.get(
                "hierarchy_labels",
                [],
            )
            if str(value).strip()
        )

        candidate_lines.append(
            "\n".join(
                [
                    (
                        f"Candidate {candidate['rank']}: "
                        f"{candidate['idnumber']}"
                    ),
                    (
                        f"Name: "
                        f"{candidate['shortname']}"
                    ),
                    (
                        f"Hierarchy: "
                        f"{hierarchy or 'Not available'}"
                    ),
                    (
                        f"Description: "
                        f"{candidate['description_text']}"
                    ),
                    (
                        f"BM25 score: "
                        f"{candidate['bm25_score']}"
                    ),
                ]
            )
        )

    allowed_ids = [
        candidate["idnumber"]
        for candidate in candidates
    ]

    response_example = {
        "fragment_id": fragment_id,
        "selected": [
            {
                "idnumber": allowed_ids[0],
                "evidence": [
                    "Exact quote from the fragment"
                ],
                "reason": (
                    "The quoted text directly demonstrates "
                    "the selected competency."
                ),
                "confidence": 0.85,
            }
        ],
        "abstain": False,
        "overall_reason": (
            "The fragment contains direct evidence for "
            "the selected competency."
        ),
    }

    return f"""You are reviewing a Moodle learning-resource fragment and aligning it with a competency framework.

STRICT RULES:
1. Select only from these allowed competency IDs: {", ".join(allowed_ids)}.
2. Never invent or return another competency ID.
3. Select between zero and three competencies.
4. Select a competency only when the fragment contains direct pedagogical evidence for it.
5. Every selected competency must contain at least one evidence quote.
6. Every evidence quote must be an exact, contiguous substring copied from FRAGMENT_TEXT.
7. Do not paraphrase evidence.
8. Do not use the candidate description itself as evidence.
9. Use abstain=true when none of the candidates is sufficiently supported.
10. When abstain=true, selected must be an empty list.
11. Confidence must be between 0.0 and 1.0.
12. Return valid JSON only. Do not use Markdown or explanatory text outside JSON.

FRAGMENT_ID:
{fragment_id}

COURSE:
{course_shortname}

ACTIVITY:
{activity_name}

TITLE:
{title}

FRAGMENT_TEXT:
{fragment_text}

ALLOWED CANDIDATES:

{chr(10).join(candidate_lines)}

REQUIRED JSON STRUCTURE:

{json.dumps(response_example, ensure_ascii=False, indent=2)}

Evaluate only the supplied fragment and candidates. Return JSON only.
"""


def build_alignment_task(
    *,
    candidate_set: Mapping[str, Any],
    competency_lookup: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    """Build one constrained alignment task."""

    fragment_id = str(
        candidate_set.get("fragment_id", "")
    ).strip()

    if not fragment_id:
        raise ValueError(
            "Candidate set is missing fragment_id."
        )

    fragment_text = str(
        candidate_set.get("fragment_text", "")
    ).strip()

    if not fragment_text:
        raise ValueError(
            f"Fragment {fragment_id} has empty text."
        )

    detailed_candidates: list[dict[str, Any]] = []

    for candidate_reference in candidate_set.get(
        "candidates",
        [],
    ):
        idnumber = str(
            candidate_reference.get(
                "idnumber",
                "",
            )
        ).strip()

        competency = competency_lookup.get(idnumber)

        if competency is None:
            raise ValueError(
                f"Unknown competency {idnumber!r} "
                f"for fragment {fragment_id}."
            )

        detailed_candidates.append(
            {
                "rank": int(
                    candidate_reference.get(
                        "rank",
                        0,
                    )
                ),
                "competency_id":
                    competency.get(
                        "competency_id"
                    ),
                "idnumber": idnumber,
                "shortname": competency.get(
                    "shortname",
                    "",
                ),
                "description_text":
                    competency.get(
                        "description_text",
                        "",
                    ),
                "parent_idnumber":
                    competency.get(
                        "parent_idnumber",
                        "",
                    ),
                "parent_shortname":
                    competency.get(
                        "parent_shortname",
                        "",
                    ),
                "hierarchy_idnumbers":
                    competency.get(
                        "hierarchy_idnumbers",
                        [],
                    ),
                "hierarchy_labels":
                    competency.get(
                        "hierarchy_labels",
                        [],
                    ),
                "depth": competency.get(
                    "depth"
                ),
                "bm25_score": float(
                    candidate_reference.get(
                        "bm25_score",
                        0.0,
                    )
                ),
            }
        )

    detailed_candidates.sort(
        key=lambda candidate: candidate["rank"]
    )

    title = str(
        candidate_set.get("title", "")
    ).strip()

    activity_name = str(
        candidate_set.get(
            "activity_name",
            "",
        )
    ).strip()

    course_shortname = str(
        candidate_set.get(
            "course_shortname",
            "",
        )
    ).strip()

    allowed_idnumbers = [
        candidate["idnumber"]
        for candidate in detailed_candidates
    ]

    return {
        "task_id": f"alignment:{fragment_id}",
        "fragment_id": fragment_id,
        "resource_id": candidate_set.get(
            "resource_id"
        ),
        "resource_type": candidate_set.get(
            "resource_type"
        ),
        "fragment_type": candidate_set.get(
            "fragment_type"
        ),
        "course_id": candidate_set.get(
            "course_id"
        ),
        "course_shortname": course_shortname,
        "course_module_id": candidate_set.get(
            "course_module_id"
        ),
        "activity_id": candidate_set.get(
            "activity_id"
        ),
        "activity_name": activity_name,
        "title": title,
        "fragment_text": fragment_text,
        "allowed_idnumbers": allowed_idnumbers,
        "candidates": detailed_candidates,
        "instructions": {
            "minimum_selections": 0,
            "maximum_selections": 3,
            "abstention_allowed": True,
            "evidence_must_be_exact_substring": True,
            "candidate_restriction_enforced": True,
            "response_format": "json_only",
        },
        "output_contract": build_output_contract(
            fragment_id
        ),
        "prompt": build_prompt(
            fragment_id=fragment_id,
            fragment_text=fragment_text,
            title=title,
            activity_name=activity_name,
            course_shortname=course_shortname,
            candidates=detailed_candidates,
        ),
        "task_version": "1.0",
    }


def build_alignment_tasks(
    *,
    candidate_sets: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build alignment tasks for all BM25 candidate sets."""

    competency_lookup = build_competency_lookup(
        competencies
    )

    return [
        build_alignment_task(
            candidate_set=candidate_set,
            competency_lookup=competency_lookup,
        )
        for candidate_set in candidate_sets
    ]


def validate_alignment_tasks(
    *,
    candidate_sets: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    expected_candidate_count: int = 5,
) -> dict[str, Any]:
    """Validate task coverage and candidate restrictions."""

    valid_idnumbers = {
        str(
            competency.get("idnumber", "")
        ).strip()
        for competency in competencies
        if str(
            competency.get("idnumber", "")
        ).strip()
    }

    expected_fragment_ids = {
        str(
            candidate_set.get(
                "fragment_id",
                "",
            )
        ).strip()
        for candidate_set in candidate_sets
    }

    task_fragment_ids = [
        str(task.get("fragment_id", "")).strip()
        for task in tasks
    ]

    task_ids = [
        str(task.get("task_id", "")).strip()
        for task in tasks
    ]

    duplicate_task_ids = sorted(
        task_id
        for task_id, count in Counter(
            task_ids
        ).items()
        if task_id and count > 1
    )

    duplicate_fragment_ids = sorted(
        fragment_id
        for fragment_id, count in Counter(
            task_fragment_ids
        ).items()
        if fragment_id and count > 1
    )

    missing_fragments = sorted(
        expected_fragment_ids
        - set(task_fragment_ids)
    )

    unknown_fragments = sorted(
        set(task_fragment_ids)
        - expected_fragment_ids
    )

    invalid_candidate_counts: list[str] = []
    duplicate_allowed_ids: list[str] = []
    unknown_allowed_ids: list[str] = []
    inconsistent_allowed_ids: list[str] = []
    empty_fragment_texts: list[str] = []
    empty_prompts: list[str] = []
    incomplete_candidate_profiles: list[str] = []

    for task in tasks:
        fragment_id = str(
            task.get("fragment_id", "")
        )

        candidates = list(
            task.get("candidates", [])
        )

        allowed_ids = [
            str(value).strip()
            for value in task.get(
                "allowed_idnumbers",
                [],
            )
        ]

        candidate_ids = [
            str(
                candidate.get(
                    "idnumber",
                    "",
                )
            ).strip()
            for candidate in candidates
        ]

        if len(candidates) != expected_candidate_count:
            invalid_candidate_counts.append(
                fragment_id
            )

        if len(allowed_ids) != len(set(allowed_ids)):
            duplicate_allowed_ids.append(
                fragment_id
            )

        for idnumber in allowed_ids:
            if idnumber not in valid_idnumbers:
                unknown_allowed_ids.append(
                    f"{fragment_id}:{idnumber}"
                )

        if allowed_ids != candidate_ids:
            inconsistent_allowed_ids.append(
                fragment_id
            )

        if not str(
            task.get("fragment_text", "")
        ).strip():
            empty_fragment_texts.append(
                fragment_id
            )

        prompt = str(task.get("prompt", "")).strip()

        if not prompt:
            empty_prompts.append(fragment_id)

        for candidate in candidates:
            if (
                not str(
                    candidate.get(
                        "idnumber",
                        "",
                    )
                ).strip()
                or not str(
                    candidate.get(
                        "shortname",
                        "",
                    )
                ).strip()
                or not str(
                    candidate.get(
                        "description_text",
                        "",
                    )
                ).strip()
            ):
                incomplete_candidate_profiles.append(
                    fragment_id
                )
                break

            if candidate["idnumber"] not in prompt:
                incomplete_candidate_profiles.append(
                    fragment_id
                )
                break

    passed = (
        len(tasks) == len(candidate_sets)
        and not duplicate_task_ids
        and not duplicate_fragment_ids
        and not missing_fragments
        and not unknown_fragments
        and not invalid_candidate_counts
        and not duplicate_allowed_ids
        and not unknown_allowed_ids
        and not inconsistent_allowed_ids
        and not empty_fragment_texts
        and not empty_prompts
        and not incomplete_candidate_profiles
    )

    return {
        "source_candidate_sets":
            len(candidate_sets),
        "source_competencies":
            len(competencies),
        "alignment_tasks":
            len(tasks),
        "expected_candidates_per_task":
            expected_candidate_count,
        "duplicate_task_ids":
            duplicate_task_ids,
        "duplicate_fragment_ids":
            duplicate_fragment_ids,
        "missing_fragments":
            missing_fragments,
        "unknown_fragments":
            unknown_fragments,
        "invalid_candidate_counts":
            invalid_candidate_counts,
        "duplicate_allowed_ids":
            duplicate_allowed_ids,
        "unknown_allowed_ids":
            unknown_allowed_ids,
        "inconsistent_allowed_ids":
            inconsistent_allowed_ids,
        "empty_fragment_texts":
            empty_fragment_texts,
        "empty_prompts":
            empty_prompts,
        "incomplete_candidate_profiles":
            sorted(
                set(
                    incomplete_candidate_profiles
                )
            ),
        "passed": passed,
    }


def write_jsonl(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> Path:
    """Write records as UTF-8 JSON Lines."""

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
