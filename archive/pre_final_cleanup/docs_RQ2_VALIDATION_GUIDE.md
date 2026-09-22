# RQ2 validation guide

**RQ2.** Do textual evidence spans help teachers verify alignment suggestions?

This guide defines a **minimal within-reviewer** exercise. With one teacher or supervisor it is a **small exploratory usability/validation exercise**, not a controlled teacher study. Do not claim statistical significance.

## What the project already provides

- Mechanical exact-substring validation (83/83 frozen Gemini quotes)
- Researcher pedagogical ratings (clear / partial / unsupported)
- A teacher-facing UI that highlights the quote inside the fragment

Those artefacts **do not fully answer RQ2**. Direct teacher or supervisor use of evidence vs no-evidence is still required.

## Design

For several stored suggestions (3–8 is enough):

**Condition A — without_evidence.** Show competency ID, name, confidence. Hide the quote and the highlighted fragment.

**Condition B — with_evidence.** Show the same suggestion with the exact quote highlighted in fragment context.

Same reviewer, same suggestions. Prefer Condition A first to reduce carry-over from already seeing the quote.

## Record

Use `data/templates/human_validation_form.csv`. Do not pre-fill answers.

| Field | Allowed values |
|---|---|
| condition | `without_evidence` or `with_evidence` |
| decision | ACCEPT / REJECT / MODIFY |
| evidence_usefulness_rating | 1–5 (1 = not useful … 5 = very useful) |
| confidence_in_decision | 1–5 |
| decision_time_seconds | elapsed seconds if measured |
| reviewer_role | teacher or supervisor |

## Analysis

`scripts/34_summarize_human_validation.py` reports descriptive means/medians only when answers exist. It does not run significance tests.

Interpret a tiny sample as qualitative feedback: whether the quote made the decision faster, more confident, or easier to justify.

## Wording to avoid

- “Teachers validated the system”
- “Evidence is 100% correct”
- “RQ2 is confirmed”

Correct wording while this form is empty: RQ2 remains **WAITING_FOR_HUMAN**.
