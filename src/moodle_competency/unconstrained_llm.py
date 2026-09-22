"""Section K — the optional all-13 unconstrained comparison (software only).

Purpose
-------
The constrained experiment let the model choose only from the BM25 Top-5. That
caps recall at the retrieval ceiling and may also *help* precision by hiding
implausible options. This experiment removes the restriction so the effect of
candidate restriction can be measured rather than assumed.

What is held identical to the constrained run
---------------------------------------------
Same model, same temperature 0, same maximum of three selections, same
abstention rule, same exact-substring evidence requirement, same output schema,
same fragment corpus, same competency descriptions, and the *same validator*:
``llm_validation.validate_alignment_response`` is reused unchanged, keyed off
each task's ``allowed_idnumbers``.

The one intended difference
---------------------------
``allowed_idnumbers`` is all 13 framework competencies instead of a BM25 Top-5
subset.

One consequence follows from that and is not a second design change: with no
retrieval step there is no BM25 score to show, so the candidate block omits the
``BM25 score:`` line the constrained prompt carries. Inventing a score would
inject a signal this condition does not have. The twelve numbered rules, the
field order and the required JSON structure are otherwise identical, and
:func:`prompt_rule_block` is shared so the rules cannot silently drift apart.

Safety
------
Nothing in this module calls an API. Running the experiment is a separate,
explicitly authorized step, and every output is written under
``data/experiments/`` so no constrained artefact can be overwritten.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import stripped_text
from moodle_competency.llm_tasks import build_output_contract


UNCONSTRAINED_TASK_VERSION = "1.0"
CANDIDATE_SPACE = "all_framework_competencies"
EXPECTED_CANDIDATE_COUNT = 13
MAXIMUM_SELECTIONS = 3

#: Written into the manifest so a reader can check the conditions really did
#: match without diffing two prompt files by eye.
HELD_CONSTANT = (
    "model",
    "temperature",
    "maximum_selections",
    "abstention_allowed",
    "evidence_must_be_exact_substring",
    "output_schema",
    "fragment_corpus",
    "competency_descriptions",
    "validator_semantics",
)

INTENDED_DIFFERENCE = (
    "candidate space is all framework competencies instead of BM25 Top-5"
)

PRESENTATION_DIFFERENCE = (
    "the candidate block omits the BM25 score line, because this condition has "
    "no retrieval step and a fabricated score would add a signal the condition "
    "does not have"
)


class UnconstrainedTaskError(ValueError):
    """Raised when an unconstrained task cannot be built as specified."""


def prompt_rule_block(allowed_ids: Sequence[str]) -> str:
    """The twelve numbered rules, shared with the constrained prompt.

    Kept in one place so the two conditions cannot drift apart silently.
    """

    return f"""STRICT RULES:
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
12. Return valid JSON only. Do not use Markdown or explanatory text outside JSON."""


def build_full_candidate_list(
    competencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Every framework competency as a candidate, in stable framework order.

    ``rank`` here is a presentation index, not a retrieval rank. It exists only
    so the candidate block is numbered; it carries no score information.
    """

    ordered = sorted(
        competencies,
        key=lambda record: (
            int(record.get("sortorder", 0) or 0),
            stripped_text(record.get("idnumber")),
        ),
    )

    candidates: list[dict[str, Any]] = []

    for index, competency in enumerate(ordered, start=1):
        idnumber = stripped_text(competency.get("idnumber"))

        if not idnumber:
            raise UnconstrainedTaskError(
                "Competency record has no idnumber; refusing to build a task."
            )

        candidates.append(
            {
                "rank": index,
                "competency_id": competency.get("competency_id"),
                "idnumber": idnumber,
                "shortname": stripped_text(competency.get("shortname")),
                "description_text": stripped_text(
                    competency.get("description_text")
                ),
                "parent_idnumber": stripped_text(
                    competency.get("parent_idnumber")
                ),
                "parent_shortname": stripped_text(
                    competency.get("parent_shortname")
                ),
                "hierarchy_idnumbers": list(
                    competency.get("hierarchy_idnumbers", []) or []
                ),
                "hierarchy_labels": list(
                    competency.get("hierarchy_labels", []) or []
                ),
                "depth": competency.get("depth"),
            }
        )

    return candidates


def build_unconstrained_prompt(
    *,
    fragment_id: str,
    fragment_text: str,
    title: str,
    activity_name: str,
    course_shortname: str,
    candidates: Sequence[Mapping[str, Any]],
) -> str:
    """The all-13 prompt. Same rules and structure as the constrained one."""

    candidate_lines: list[str] = []

    for candidate in candidates:
        hierarchy = " > ".join(
            str(value)
            for value in candidate.get("hierarchy_labels", []) or []
            if str(value).strip()
        )

        candidate_lines.append(
            "\n".join(
                [
                    f"Candidate {candidate['rank']}: {candidate['idnumber']}",
                    f"Name: {candidate['shortname']}",
                    f"Hierarchy: {hierarchy or 'Not available'}",
                    f"Description: {candidate['description_text']}",
                ]
            )
        )

    allowed_ids = [candidate["idnumber"] for candidate in candidates]

    response_example = {
        "fragment_id": fragment_id,
        "selected": [
            {
                "idnumber": allowed_ids[0],
                "evidence": ["Exact quote from the fragment"],
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

{prompt_rule_block(allowed_ids)}

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


def build_unconstrained_task(
    *,
    fragment: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one unconstrained task for a fragment."""

    fragment_id = stripped_text(fragment.get("fragment_id"))

    if not fragment_id:
        raise UnconstrainedTaskError("Fragment is missing fragment_id.")

    fragment_text = stripped_text(fragment.get("text")) or stripped_text(
        fragment.get("fragment_text")
    )

    if not fragment_text:
        raise UnconstrainedTaskError(f"Fragment {fragment_id} has empty text.")

    if not candidates:
        raise UnconstrainedTaskError(
            f"Fragment {fragment_id} has no candidate competencies."
        )

    title = stripped_text(fragment.get("title"))
    activity_name = stripped_text(fragment.get("activity_name"))
    course_shortname = stripped_text(fragment.get("course_shortname"))

    allowed_idnumbers = [
        stripped_text(candidate.get("idnumber")) for candidate in candidates
    ]

    if len(set(allowed_idnumbers)) != len(allowed_idnumbers):
        raise UnconstrainedTaskError(
            f"Duplicate competency ID in the candidate set for {fragment_id}."
        )

    return {
        "task_id": f"unconstrained_alignment:{fragment_id}",
        "fragment_id": fragment_id,
        "resource_id": fragment.get("resource_id"),
        "resource_type": fragment.get("resource_type"),
        "fragment_type": fragment.get("fragment_type"),
        "course_id": fragment.get("course_id"),
        "course_shortname": course_shortname,
        "course_module_id": fragment.get("course_module_id"),
        "activity_id": fragment.get("activity_id"),
        "activity_name": activity_name,
        "title": title,
        "fragment_text": fragment_text,
        "allowed_idnumbers": allowed_idnumbers,
        "candidates": [dict(candidate) for candidate in candidates],
        "instructions": {
            "minimum_selections": 0,
            "maximum_selections": MAXIMUM_SELECTIONS,
            "abstention_allowed": True,
            "evidence_must_be_exact_substring": True,
            "candidate_restriction_enforced": False,
            "response_format": "json_only",
        },
        "candidate_space": CANDIDATE_SPACE,
        "output_contract": build_output_contract(fragment_id),
        "prompt": build_unconstrained_prompt(
            fragment_id=fragment_id,
            fragment_text=fragment_text,
            title=title,
            activity_name=activity_name,
            course_shortname=course_shortname,
            candidates=candidates,
        ),
        "task_version": UNCONSTRAINED_TASK_VERSION,
        "experiment": "unconstrained_all_competencies",
    }


def build_unconstrained_tasks(
    *,
    fragments: Sequence[Mapping[str, Any]],
    competencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build one unconstrained task per fragment, in fragment order."""

    candidates = build_full_candidate_list(competencies)

    return [
        build_unconstrained_task(fragment=fragment, candidates=candidates)
        for fragment in fragments
    ]


def validate_unconstrained_tasks(
    tasks: Sequence[Mapping[str, Any]],
    *,
    expected_fragment_ids: Sequence[str],
    expected_candidate_count: int = EXPECTED_CANDIDATE_COUNT,
) -> dict[str, Any]:
    """Check the task set before anything is ever sent to a model."""

    errors: list[str] = []

    task_fragment_ids = [stripped_text(task.get("fragment_id")) for task in tasks]
    expected = [stripped_text(value) for value in expected_fragment_ids]

    missing = sorted(set(expected) - set(task_fragment_ids))
    unexpected = sorted(set(task_fragment_ids) - set(expected))

    duplicates = sorted(
        fragment_id
        for fragment_id in set(task_fragment_ids)
        if task_fragment_ids.count(fragment_id) > 1
    )

    if missing:
        errors.append(f"Missing tasks for fragments: {', '.join(missing)}")

    if unexpected:
        errors.append(f"Unexpected task fragments: {', '.join(unexpected)}")

    if duplicates:
        errors.append(f"Duplicate task fragments: {', '.join(duplicates)}")

    for task in tasks:
        fragment_id = stripped_text(task.get("fragment_id"))
        allowed = task.get("allowed_idnumbers", []) or []

        if len(allowed) != expected_candidate_count:
            errors.append(
                f"{fragment_id}: expected {expected_candidate_count} candidates, "
                f"found {len(allowed)}"
            )

        instructions = task.get("instructions", {}) or {}

        if instructions.get("candidate_restriction_enforced") is not False:
            errors.append(
                f"{fragment_id}: candidate_restriction_enforced must be false "
                "in the unconstrained condition"
            )

        if instructions.get("maximum_selections") != MAXIMUM_SELECTIONS:
            errors.append(
                f"{fragment_id}: maximum_selections must be {MAXIMUM_SELECTIONS} "
                "to match the constrained run"
            )

        if instructions.get("evidence_must_be_exact_substring") is not True:
            errors.append(
                f"{fragment_id}: the exact-substring evidence requirement must "
                "match the constrained run"
            )

        if not stripped_text(task.get("fragment_text")):
            errors.append(f"{fragment_id}: fragment_text is empty")

    return {
        "task_count": len(tasks),
        "expected_task_count": len(expected),
        "missing_fragment_ids": missing,
        "unexpected_fragment_ids": unexpected,
        "duplicate_fragment_ids": duplicates,
        "errors": errors,
        "status": "PASSED" if not errors else "FAILED",
    }


def compare_conditions(
    *,
    constrained_tasks: Sequence[Mapping[str, Any]],
    unconstrained_tasks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify the two conditions differ only in their candidate space.

    This is the audit that makes the comparison meaningful: if the fragment
    text or the instructions had drifted, any measured difference could not be
    attributed to candidate restriction.
    """

    constrained_by_fragment = {
        stripped_text(task.get("fragment_id")): task for task in constrained_tasks
    }
    unconstrained_by_fragment = {
        stripped_text(task.get("fragment_id")): task for task in unconstrained_tasks
    }

    shared = sorted(set(constrained_by_fragment) & set(unconstrained_by_fragment))

    text_mismatches: list[str] = []
    instruction_mismatches: list[str] = []
    candidate_space_identical: list[str] = []

    compared_instruction_keys = (
        "minimum_selections",
        "maximum_selections",
        "abstention_allowed",
        "evidence_must_be_exact_substring",
        "response_format",
    )

    for fragment_id in shared:
        constrained = constrained_by_fragment[fragment_id]
        unconstrained = unconstrained_by_fragment[fragment_id]

        if stripped_text(constrained.get("fragment_text")) != stripped_text(
            unconstrained.get("fragment_text")
        ):
            text_mismatches.append(fragment_id)

        constrained_instructions = constrained.get("instructions", {}) or {}
        unconstrained_instructions = unconstrained.get("instructions", {}) or {}

        for key in compared_instruction_keys:
            if constrained_instructions.get(key) != unconstrained_instructions.get(key):
                instruction_mismatches.append(f"{fragment_id}:{key}")

        if set(constrained.get("allowed_idnumbers", []) or []) == set(
            unconstrained.get("allowed_idnumbers", []) or []
        ):
            candidate_space_identical.append(fragment_id)

    errors: list[str] = []

    if text_mismatches:
        errors.append(
            "Fragment text differs between conditions: "
            + ", ".join(text_mismatches)
        )

    if instruction_mismatches:
        errors.append(
            "Instructions differ between conditions: "
            + ", ".join(instruction_mismatches)
        )

    missing = sorted(set(constrained_by_fragment) - set(unconstrained_by_fragment))

    if missing:
        errors.append(
            "Fragments missing from the unconstrained condition: "
            + ", ".join(missing)
        )

    return {
        "shared_fragment_count": len(shared),
        "fragment_text_mismatches": text_mismatches,
        "instruction_mismatches": instruction_mismatches,
        "fragments_with_identical_candidate_space": candidate_space_identical,
        "held_constant": list(HELD_CONSTANT),
        "intended_difference": INTENDED_DIFFERENCE,
        "presentation_difference": PRESENTATION_DIFFERENCE,
        "errors": errors,
        "status": "PASSED" if not errors else "FAILED",
    }


def experiment_manifest(
    *,
    tasks: Sequence[Mapping[str, Any]],
    model_name: str,
    temperature: float,
    validation: Mapping[str, Any] | None = None,
    comparison: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Manifest describing the unconstrained condition."""

    candidate_counts = sorted(
        {len(task.get("allowed_idnumbers", []) or []) for task in tasks}
    )

    return {
        "experiment": "unconstrained_all_competencies",
        "experiment_kind": "OPTIONAL POST-CORE CANDIDATE-RESTRICTION COMPARISON",
        "task_version": UNCONSTRAINED_TASK_VERSION,
        "candidate_space": CANDIDATE_SPACE,
        "candidate_counts_observed": candidate_counts,
        "task_count": len(tasks),
        "model_name": model_name,
        "temperature": temperature,
        "maximum_selections": MAXIMUM_SELECTIONS,
        "evidence_must_be_exact_substring": True,
        "held_constant": list(HELD_CONSTANT),
        "intended_difference": INTENDED_DIFFERENCE,
        "presentation_difference": PRESENTATION_DIFFERENCE,
        "validator": "llm_validation.validate_alignment_response (reused unchanged)",
        "constrained_outputs_overwritten": False,
        "output_location": "data/experiments/",
        "validation": dict(validation) if validation else None,
        "condition_comparison": dict(comparison) if comparison else None,
    }
