# Teacher interface guide

**Project:** Moodle Learning Resource-to-Competency Alignment MVP
**For:** the teacher, supervisor or researcher who will validate the suggested alignments
**Time needed:** about 30–45 minutes to review all 34 suggestions

---

## 1. What you are being asked to do

A pipeline read a set of Moodle learning resources and proposed, for each one,
which competencies from the UTC GI framework that resource covers. Each
proposal comes with a quote taken word-for-word from the resource as its
justification.

**Your job is to say whether each proposal is right.** You accept it, reject
it, or replace it with the competency you think is correct. You can also add a
competency the system missed entirely.

Nothing is decided for you. No box is pre-ticked, and the interface never
suggests which answer to give.

There are **34 suggestions** in total, spread over 20 resources in 2 courses.

---

## 2. Starting the interface

From the project root:

```bash
source .venv/bin/activate
streamlit run app/Home.py
```

Streamlit prints a local URL (normally <http://localhost:8501>). Open it in a
browser. To stop, press `Ctrl+C` in the terminal.

### There are two apps in this repository — use this one

| App | Command | What it does |
|---|---|---|
| **Corpus validation app** (this guide) | `streamlit run app/Home.py` | Reviews the **fixed research corpus** of 20 resources that the published results are based on. |
| Runtime analysis app | `streamlit run app.py` | Analyses an **arbitrary new** Moodle resource on demand. Not part of the reported experiment. |

If you were asked to validate the research results, you want `app/Home.py`.

---

## 3. Before you start: fill in your name and role

In the left sidebar of the **Teacher Review** page, enter your name and pick
your role. Both are required — no decision is stored anonymously, and the role
determines how your decisions are reported:

| Role | How it is reported |
|---|---|
| `teacher` | Counts as teacher validation. |
| `supervisor` | Counts as supervisor validation. |
| `researcher` | Reported **separately**, and never presented as teacher validation. |

Please record your real role. The distinction matters for the honesty of the
write-up, not for anything else.

---

## 4. The pages

### Home — course and resource browser

Pick a course (`MVP-SW` or `MVP-DATA`) and expand any resource to see its text,
its fragments, and which competencies were predicted for it. Start here to get a
feel for the material.

### 1 · Resource → Competencies

Function A, read-only. Pick one resource and see every competency proposed for
it, with:

- the **confidence** the model reported,
- the **BM25 rank** — where the retrieval step placed that competency (`#1` is
  the best match; *not retrieved* means the model could not have chosen it),
- the **evidence quote**,
- the **hierarchy** — whether this is a parent competency or a child,
- any **warning** from the hierarchy check.

The bottom section shows the same thing per fragment, including the full list
of five candidates BM25 offered, marked with whether the model chose each one.

### 2 · Teacher Review — **this is where you work**

One card per suggestion. Each card shows the resource, the competency and its
description, the confidence, the BM25 rank, the evidence quote and the fragment
text, and then asks for your decision.

| Action | Use it when |
|---|---|
| **ACCEPT** | The competency genuinely fits this resource. |
| **REJECT** | It does not fit. |
| **MODIFY** | It is wrong, but you can name the competency that *is* right. Pick one or more replacements from the list. |

You are also asked, optionally, **whether the evidence quote was useful** to
you — `0` not at all, `1` partly, `2` it clearly justified the competency. This
is the question the project most wants answered, so please fill it in when you
have a view.

Use the filters at the top (course, resource type, *Pending only*) to work
through the list without losing your place.

Press **Save this decision** on each card. Nothing is stored until you do.

At the bottom of the page there is a separate form to **add a competency the
model missed** — a competency the resource covers that was never suggested.

### 3 · Competency → Resources

Function B, the inverse direction: pick a competency and see every resource
that supports it, with evidence and your decisions so far. This answers "what
in my course teaches this competency?"

### 4 · Evidence Review

Read-only record of an earlier review pass, in which every one of the 83
evidence quotes was checked by hand for whether it pedagogically justifies its
competency. You do not need to do anything here; it is context.

### 5 · Review Progress

How far through you are, broken down by course and resource type, and which
suggestions are still pending. Acceptance and rejection rates appear only once
real decisions exist.

### 6 · Experiment Results

Read-only measured results. This page cannot change any metric file.

---

## 5. What the interface writes, and what it never touches

**It writes exactly one file:**

```
data/reviews/corpus_teacher_reviews.csv
```

Each save takes a timestamped backup of the previous version into
`data/reviews/corpus_teacher_review_backups/` first, then writes atomically, so
an interrupted save cannot leave a half-written file. Re-deciding the same
suggestion replaces your earlier answer rather than adding a duplicate row.

**It never writes to:**

- Moodle — nothing is sent back to the LMS, and no Moodle competency assignment is changed;
- `data/gold/manual_fragment_annotations.csv` — the human-reviewed reference;
- `data/interim/gemini_validated.jsonl` — the model output;
- `data/reviews/evidence_review.csv` — the earlier evidence review;
- `data/reviews/teacher_reviews.csv` — the *runtime* app's separate review log;
- anything under `reports/metrics/` — the measured results.

### A note on the file name

Section L of the project plan named `data/reviews/teacher_reviews.csv` for these
reviews. That path was already taken by the runtime app's review log, which uses
different columns and already contains real decisions. Writing there would have
destroyed them, so this interface uses `corpus_teacher_reviews.csv` instead.
Both files are hashed in the reproducibility manifest and both are read by the
review summary script.

---

## 6. Validation rules

A decision is refused, with the reason shown on screen, if:

- the competency ID is not one of the 13 in the framework;
- the resource ID is not one of the 20 in the corpus;
- your name is blank;
- the decision is not ACCEPT, REJECT, MODIFY or ADD;
- MODIFY is chosen without at least one replacement competency;
- replacements are given for a decision other than MODIFY;
- the evidence rating is not blank, `0`, `1` or `2`.

---

## 7. Reading the display

**Confidence** is what the model reported about its own choice. It is not a
calibrated probability and has not been validated — treat it as a weak hint.

**BM25 rank** is the position of that competency in the retrieval step. The
model could only choose from the top 5, so a competency that was *not
retrieved* was never available to it. This distinguishes a retrieval failure
from a model failure.

**⚠️ parent_child_redundancy** means both a parent competency and one of its
children were predicted for the same fragment — for example both `GI_C3` and
`GI_C3_2`. This is the most common problem in the current output, affecting 10
fragments. Usually the child is the useful label and the parent adds nothing.

**⚠️ granularity_conflict** means the predictions mix levels of the hierarchy in
a way worth a second look.

These are **warnings only**. Nothing was auto-corrected, and the model's
predictions were never edited.

---

## 8. Recovering from a mistake

Re-decide the suggestion and save again; the new answer replaces the old one.
If you need an earlier state, every save left a timestamped copy in
`data/reviews/corpus_teacher_review_backups/`.

To discard everything and start over, delete
`data/reviews/corpus_teacher_reviews.csv`. The backups remain.

---

## 9. When you have finished

Tell the researcher. The summary is produced with:

```bash
python scripts/28_summarize_teacher_reviews.py
```

Your name and role are recorded with each decision, and researcher decisions
are reported separately from teacher validation.

---

## 10. Honest limits of this exercise

So that nothing here is oversold:

- The corpus is small and was built for this study: 20 resources, 35 fragments, 13 competencies, 2 courses.
- The reference annotations it is scored against were produced by one person, with no second annotator and no measured inter-annotator agreement.
- No resource in the corpus has "no competency" as its correct answer, so the system's ability to abstain is untested.
- Only Moodle Pages and quiz questions are covered — no assignments, PDFs, slides or video.
- Your review is a usability and usefulness exercise on a small sample. It is not a controlled study of teachers in general, and it will not be reported as one.
