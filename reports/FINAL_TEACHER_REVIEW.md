# Final teacher review

**Moodle learning resource-to-competency alignment — reduced MVP**
**Researcher:** Wail Ouaret · UTC / Heudiasyc / CNRS
**Date:** 2026-09-22
**Status: `WAITING_FOR_HUMAN`**

---

## 1. The headline, stated plainly

**No teacher has reviewed the research corpus. No acceptance rate, edit rate or
rejection rate is reported, because there is nothing real to compute one from.**

`reports/metrics/teacher_review_summary.json`:

| Field | Value |
|---|---|
| `status` | `WAITING_FOR_HUMAN` |
| `reviewable_mappings` | 34 |
| `reviewed` | 0 |
| `pending` | 34 |
| `accepted` / `rejected` / `modified` / `added` | 0 / 0 / 0 / 0 |
| `acceptance_rate` | `null` |
| `edit_rate` | `null` |
| `rejection_rate` | `null` |
| `teacher_or_supervisor_validation_performed` | `false` |

The rates are `null`, not `0.0`. That distinction is deliberate: `0.0` would
read as "teachers accepted nothing", which is a finding about the system.
`null` says "nothing was reviewed", which is the truth. The summary code
enforces this and is covered by tests.

---

## 2. What human decisions do exist

Two, and neither is teacher validation of the research corpus.

`data/reviews/teacher_reviews.csv` — the separate **runtime** app's review log,
recorded by Wail Ouaret on 2026-09-18:

| Decision | Competency | Reviewer | Role |
|---|---|---|---|
| `REJECT` | `GI_C3` | Wail Ouaret | researcher |
| `ACCEPT` | `GI_C3_1` | Wail Ouaret | researcher |

These are **researcher** decisions about a runtime analysis of an ad-hoc
resource, not decisions about the 20-resource frozen corpus the results are
based on. They are reported separately and never merged into a teacher
acceptance rate.

They are worth one observation, offered as an anecdote and nothing more: the
researcher rejected a parent competency and accepted its child — the same
granularity judgement the reference convention encodes and the model failed to
make. One data point suggests nothing on its own.

### Human Gate 2 — the review that *was* completed

The one human review pass genuinely finished is the **pedagogical evidence
review**: all 83 evidence quotes rated 0/1/2 by Wail Ouaret on 2026-09-18.
That is reported in `reports/FINAL_EXPERIMENTAL_RESULTS.md` §8 and
`reports/FINAL_ERROR_ANALYSIS.md` §5. It is a researcher review, not teacher
validation, and is labelled as such throughout.

---

## 3. What is waiting to be reviewed

34 predicted resource-competency alignments across 20 resources:

| Breakdown | Total | Reviewed | Pending |
|---|---:|---:|---:|
| **All** | 34 | 0 | 34 |
| MVP-SW | 19 | 0 | 19 |
| MVP-DATA | 15 | 0 | 15 |
| Pages | 18 | 0 | 18 |
| Quiz questions | 16 | 0 | 16 |

18 of the 34 carry a hierarchy warning, and all 34 have at least one
human-rated evidence quote available to show the reviewer.

---

## 4. The interface is built and works

`docs/TEACHER_INTERFACE_GUIDE.md` · launch with `streamlit run app/Home.py`

| Page | Purpose | Writes? |
|---|---|---|
| `Home` | Course and resource browser | no |
| `1 Resource to Competencies` | Function A with evidence, BM25 rank, hierarchy | no |
| `2 Teacher Review` | **accept / reject / modify / add** | **yes — one file** |
| `3 Competency to Resources` | Function B, the inverse direction | no |
| `4 Evidence Review` | The closed Gate 2, read-only | no |
| `5 Review Progress` | Coverage by course and resource type | no |
| `6 Experiment Results` | Measured metrics, read-only | no |
| `7 Evidence Usefulness Pilot` | Section M pilot | writes pilot responses |
| `8 Validated Coverage` | Section O, validated mappings only | no |

All 14 Streamlit pages (these plus the older runtime app) render without
exception under `scripts/ui_smoke_check.py` with outbound network access
blocked, so no page can silently reach an external service.

### What a reviewer sees per suggestion

Resource and fragment text · predicted competency with its description ·
model confidence · **BM25 rank** (or "not retrieved", which distinguishes a
retrieval failure from a model failure) · the exact evidence quote with its
human pedagogical rating · hierarchy context · any graph warning · and the
current decision.

### What the interface never does

It does not write to Moodle. It does not modify the human-reviewed reference,
the model output, the evidence review, or any metric file. It writes exactly one
file, with a timestamped backup and an atomic replace.

---

## 5. Where teacher decisions will be stored

**`data/reviews/corpus_teacher_reviews.csv`** — not `teacher_reviews.csv`.

Section L of the plan named `data/reviews/teacher_reviews.csv`. That path was
already occupied by the runtime app's review log, which uses different columns
and holds the two real researcher decisions above. Writing corpus reviews there
would have destroyed real human data, which the project's own rules forbid and
which Section R requires be preserved. The two files are therefore kept
separate, both are hashed in the reproducibility manifest, and both are read by
`scripts/28_summarize_teacher_reviews.py`.

Schema: `review_id, resource_id, competency_id, fragment_ids, decision,
modified_competency_ids, comment, evidence_relevance, reviewer, review_date`.

A decision is refused, with the reason shown on screen, if the competency or
resource ID is unknown, the reviewer name is blank, the decision is not one of
the four allowed values, MODIFY has no replacement, replacements are supplied
without MODIFY, or the evidence rating is not blank/`0`/`1`/`2`. Review IDs are
unique; re-deciding replaces rather than duplicates.

---

## 6. The evidence-usefulness pilot

**Status: `WAITING_FOR_HUMAN` — designed, not performed.**

`data/studies/teacher_study_manifest.json` records a reproducible design built
with seed `20260918`:

| Property | Value |
|---|---|
| Cases sampled | 12 of 51 candidates |
| Condition A (evidence hidden until requested) | 6 |
| Condition B (evidence shown) | 6 |
| Strata | 4 correct · 4 incorrect · 4 parent-child redundancy |
| Courses | 8 MVP-SW · 4 MVP-DATA |
| Resource types | 6 Pages · 6 quiz questions |

Each response records the case, condition, reviewer, role, decision, a 1–5
confidence rating, start and end timestamps, elapsed seconds, a comment, and
**whether the reviewer chose to open the hidden evidence**.

`teacher_study_responses.csv` does not exist. No response has been recorded and
none will be simulated.

When it is run, the label will be set from the recorded roles, not assumed: if
only the researcher participates it is reported as a **researcher pilot**, never
as a teacher study. No significance test will be computed — the sample size and
within-reviewer design do not support one.

---

## 7. Validated coverage

**Empty, by design.** `app/pages/8_Validated_Coverage.py` reports 0 validated
mappings, all 20 resources unmapped and all 13 competencies uncovered.

Coverage is deliberately *not* filled in from predictions. An unreviewed
suggestion is not coverage. The page says so rather than showing predicted
coverage that a reader might mistake for confirmed coverage — a distinction that
matters because the predicted inverse index looks complete (13/13 competencies
have a predicted resource) while validated coverage is zero.

---

## 8. What is needed, and what it would answer

### The step

```bash
source .venv/bin/activate
streamlit run app/Home.py
```

Open **2 Teacher Review**, enter a name and role, and work through the 34
pending suggestions. Roughly 30–45 minutes. Then optionally **7 Evidence
Usefulness Pilot** (12 cases). Then:

```bash
python scripts/28_summarize_teacher_reviews.py
```

### What it would answer that the metrics cannot

The measured results say the system agrees with **one annotator's reference**.
They cannot say whether a teacher finds the suggestions useful. Three open
questions in particular:

1. **Is parent-child redundancy actually a problem for a teacher?** It costs
   0.18 micro precision against the reference. A teacher might regard tagging a
   resource with both `GI_C3` and `GI_C3_2` as harmless, or as noise. The
   reference cannot tell us; only a teacher can. If it is harmless, the headline
   precision figure overstates the real defect.
2. **Does the evidence quote change the decision?** That is what the A/B pilot
   asks. Exact-substring validity is a property of the string; usefulness is a
   property of the reader.
3. **Does a teacher agree with the annotator at all?** With one annotator and no
   inter-annotator agreement, a teacher's decisions would be the first
   independent check on whether the reference is broadly reasonable.

Until those decisions exist, the honest position is the one recorded throughout:
the system has been measured against a single-annotator reference and has not
been validated by a teacher.
