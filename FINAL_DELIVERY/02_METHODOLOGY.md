# Methodology

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — UTC / Heudiasyc / CNRS — 22 September 2026

This document records the methodology in sufficient detail for a reviewer or a
subsequent student to reconstruct the reasoning behind the experiment. Operating
instructions are in `05_REPRODUCIBILITY_GUIDE.md`.

Throughout, a distinction is maintained between the **core system**, which
produced the reported results, and **post-hoc experiments**, which were carried
out after those results were frozen and which never modified them.

---

## A. Research design

The study is a single-corpus, single-annotator evaluation of a two-stage
alignment pipeline against a lexical baseline, with a manual audit of the
justifications the pipeline produces.

Three comparisons are made:

1. BM25 Top-1 as a standalone classifier against the reference.
2. BM25 Top-5 followed by constrained model selection against the same reference.
3. A post-hoc hierarchy ablation against both.

The design is deliberately staged so that a missed label can be attributed to a
specific component. Recording the candidate set for every fragment makes it
decidable whether the correct competency was available to the selection stage at
all — the distinction that carries most of the analysis.

**What the design cannot do.** With one annotator and 38 labels it cannot
estimate performance with uncertainty, establish generalisation, or measure
utility to a teacher. It can establish that the pipeline runs end to end, quantify
its behaviour on this corpus, and characterise its failure modes.

---

## B. Moodle environment

| Property | Value |
|---|---|
| Version | Moodle 5.2.1+ (Build 20260722) |
| Deployment | Local development instance |
| Courses | `MVP-SW`, `MVP-DATA` |
| Resource types | Page, quiz question |
| Primary extraction | REST web services |
| Secondary extraction | Direct SQL |

### Extraction routes

Course structure, Page content and quiz metadata were obtained through the
web-service API (`core_course_get_contents`, `mod_page_get_pages_by_courses`,
`mod_quiz_get_quizzes_by_courses`). Responses were stored verbatim before
processing.

**Why a SQL fallback was required.** Moodle's web services expose quiz
*activities* but not, on this version, the text of individual *questions* in a
form usable for retrieval. The question bank is reachable only through the
database. Since a quiz question is the unit at which a competency is actually
assessed, and since discarding the questions would have removed 12 of 20
resources, the text was read directly with a documented SQL query.

The consequence is recorded rather than minimised: this route requires database
access that a managed institutional Moodle would not normally grant, so this part
of the pipeline is specific to a local development deployment.

---

## C. Competency framework

Thirteen competencies were selected from the UTC *Génie Informatique* framework:
three top-level competencies and ten children, chosen to span the subject matter
of the two courses while remaining small enough to annotate exhaustively.

### Import path

```
UTC GI source (JSON/JSONL)
   → selection of 13 identifiers        configs/selected_competency_ids.txt
   → Moodle 5.2 competency CSV          scripts/build_moodle_competency_csv.py
   → Moodle native competency tables    manual import through the Moodle UI
   → normalised JSON Lines              scripts/04_normalize_competencies.py
```

Both representations derive from the same source and share identifiers, so a
competency shown in the Moodle interface and one used by the retrieval stage are
the same object.

### Normalised representation

Each record carries `idnumber`, `shortname`, `description_text`, `description_raw`,
`depth`, `parent_idnumber`, `hierarchy_idnumbers`, `hierarchy_labels`,
`sortorder`, and a `search_text` field used for indexing.

The framework encodes **parent–child relations only**. No prerequisite or
related-to relation exists in it, and none was introduced. Every later stage that
reasons about structure uses only these relations.

---

## D. Resource representation

A *resource* is the unit a teacher acts upon. Two decisions define it here.

A Moodle Page is one resource. Each quiz **question** is also one resource,
rather than being folded into the quiz that contains it.

**Rationale.** A quiz typically assesses several competencies across its
questions, while an individual question usually assesses one. Treating a quiz as
the unit would attach a heterogeneous label set to a single object and lose the
question-level signal that no later stage could recover. The cost is that the
corpus contains 12 quiz questions and 8 Pages, so questions dominate by count;
this is reported wherever corpus composition matters.

Every resource retains its Moodle course identifier, course-module identifier,
activity identifier, section, title and extraction route.

---

## E. Text normalisation

Moodle stores Page content as HTML authored through a rich-text editor.
Normalisation removes markup while preserving block boundaries, resolves
entities, collapses whitespace, and strips navigation and boilerplate.

Quiz questions are normalised into a single text combining the question stem with
its answer options, because the options frequently carry the technical vocabulary
that identifies the competency; discarding them would weaken retrieval on
precisely the resources where retrieval matters most.

Each resource carries a display text and a `search_text`; only the latter is
indexed.

---

## F. Fragmentation

Pages are divided at paragraph boundaries subject to a target length, yielding 23
fragments from 8 Pages. Each quiz question forms exactly one fragment, yielding
12. The corpus comprises 35 fragments.

**Why fragment at all.** An evidence quotation must be locatable in a bounded
span of text. A whole Page covering several topics would permit a quotation
drawn from a passage unrelated to the competency being justified, which would
defeat the purpose of requiring evidence.

**Provenance.** Every fragment carries `fragment_id`, `resource_id`,
`fragment_index`, `fragments_in_resource`, `fragment_type`, character and word
counts, and the full Moodle provenance chain. Fragment identifiers follow
`{resource_id}#f{NNN}`, so the parent resource is recoverable from the identifier
alone and the aggregation described in section L is a lossless regrouping.

---

## G. Candidate retrieval

A BM25 index is built over the `search_text` of the thirteen competencies. For
each fragment, the fragment text is the query; the five highest-scoring
competencies are retained with their scores and ranks.

### Choosing K

K governs a trade-off that is decided by measurement rather than by preference.

- K too small: the correct competency is absent from the candidate set and the
  selection stage cannot recover it. Recall is capped below a usable level.
- K too large: selection degenerates into a search over the whole framework and
  the restriction stops doing useful work. With only 13 competencies, K = 13 is
  no restriction at all.

Measured recall at each value:

| K | Recall@K |
|---:|---:|
| 1 | 0.6842 |
| 3 | 0.8684 |
| 5 | 0.9737 |

K = 5 places 37 of 38 reference labels within reach while still excluding 8 of
13 competencies per fragment. This value **fixes the recall ceiling of the whole
pipeline**, and the constrained system reaches exactly that ceiling.

### Metric definitions

Recall@K is label-level, over the 38 reference labels:

```
Recall@K = |{reference labels appearing in some Top-K set}| / |{reference labels}|
```

Hit@K is fragment-level, over the 35 fragments with a non-empty reference:

```
Hit@K = |{fragments with ≥1 reference label in their Top-K}| / |{fragments}|
```

Mean reciprocal rank uses the rank of the first reference label retrieved:

```
MRR = (1/N) · Σ 1/rank_first_correct
```

Parent and child are distinct labels throughout: retrieving `GI_C3` does not
satisfy a reference of `GI_C3_2`.

---

## H. Constrained model selection

Each fragment and its five candidates form a task carrying the fragment text, the
candidate descriptions with hierarchy context, and an explicit output contract.

| Parameter | Value | Reason |
|---|---|---|
| Model | `gemini-3.5-flash` | Availability and cost; the pipeline is model-agnostic |
| Temperature | 0 | Determinism as far as the API allows |
| Candidate space | BM25 Top-5 | Section G |
| Maximum selections | 3 | Headroom above the reference mean of 1.09 without permitting enumeration |
| Minimum selections | 0 | Abstention must be expressible |
| Evidence | Mandatory, exact substring | Section I |
| Output | JSON only | Machine-checkable |

The instructions state twelve numbered rules: select only from the supplied
identifiers; never invent an identifier; select between zero and three; select
only where the fragment provides direct pedagogical evidence; supply at least one
quotation per selection; every quotation must be an exact contiguous substring of
the fragment; do not paraphrase; do not quote the competency description itself;
abstain where no candidate is adequately supported; an abstention carries no
selections; confidence lies in [0, 1]; return JSON only.

### Checkpointing

Responses are written per fragment as they arrive, so an interrupted run resumes
from the last completed fragment. Historical responses are treated as frozen
experimental artefacts: the pipeline offers no mechanism to regenerate them, and
reproduction proceeds from the stored responses rather than from repeated API
calls, since a third-party model cannot be assumed stable over time.

---

## I. Evidence validation

Every response is validated before acceptance. The validator checks that:

1. the response fragment identifier matches the task;
2. the response conforms to the schema;
3. at most three competencies are selected;
4. every identifier appears among the supplied candidates;
5. every selection carries at least one quotation;
6. every quotation is an **exact contiguous substring** of the fragment text;
7. confidence lies in [0, 1];
8. an abstention carries an empty selection list.

A response failing any check is recorded invalid with its reasons and excluded
from evaluation. Of 35 responses, 35 passed and none was excluded.

Check 6 is the substantive control. A claim of support that does not appear in
the source cannot survive a mechanical comparison against the source.

**What the check does not establish.** That a quotation appears in the text says
nothing about whether it demonstrates the competency. This is why the manual
review in section K exists, and the two measurements are reported separately and
never conflated.

Character offsets for each quotation were derived afterwards for audit purposes
using first-occurrence matching. Where a quotation occurs more than once the
first occurrence is recorded; the quotation itself is never altered.

---

## J. Human-reviewed reference annotation

### Procedure

A terminal tool presents one fragment at a time with the full text and the
thirteen-competency catalogue, and records the selected competencies, supporting
quotations, an ambiguity flag with reason, and a free-text comment. It saves
after every decision, supports interruption and resumption, and writes
timestamped backups. It never proposes a label.

Annotation preceded any inspection of model predictions.

### Fields

`fragment_id`, `resource_id`, `course_id`, `course_shortname`, `resource_type`,
`activity_name`, `resource_title`, `fragment_text`, `gold_competency_ids`,
`gold_evidence`, `no_competency`, `ambiguous`, `ambiguity_reason`, `comment`,
`annotator`, `annotation_date`.

### Conventions

**Multi-label.** A fragment may carry several competencies where it genuinely
addresses several. Three fragments do.

**Ambiguity.** Where a fragment could defensibly receive different labels, the
`ambiguous` flag is set with a stated reason, and the annotator's best judgement
is still recorded. One fragment is flagged.

**No applicable competency.** The `no_competency` flag exists and is set for no
fragment: every fragment in this corpus addresses at least one competency.

**Granularity.** Labels were assigned **only at child level**. All three
top-level competencies have zero reference support.

This last convention is consistent and defensible — a child label is strictly
more informative — but it was **never stated in the model's instructions**. It is
the single most consequential methodological decision in the study, and section N
and the results documents trace its effect.

### Validation

A validator confirms one annotation row per source fragment, no unknown fragment
or competency identifier, no duplicate, no drift between the annotated text and
its source, and no incomplete decision. Result: 35 of 35 complete, no errors.

### Limitations of the reference

One annotator produced all 38 labels. No second annotator participated and **no
inter-annotator agreement was measured**. The annotations are termed
*human-reviewed reference annotations*; they are not independent blinded gold
produced from scratch and not machine-generated. Every reported score is an
agreement rate with one person's judgement.

---

## K. Evaluation metrics

Predictions and references are compared as label sets per unit.

### Micro-averaged

Pooling counts over all units:

```
Precision = ΣTP / (ΣTP + ΣFP)
Recall    = ΣTP / (ΣTP + ΣFN)
F1        = 2PR / (P + R)
```

Micro averaging weights each *label decision* equally, so frequent competencies
dominate.

### Macro-averaged

Per-competency scores averaged without weighting:

```
Macro-P = (1/|L|) · Σ Precision(l)
```

Macro averaging weights each *competency* equally, so a rare competency counts as
much as a frequent one.

### Two macro views

Three competencies have zero reference support, which makes a single macro figure
ambiguous. Both are therefore reported:

| View | Label set | Interpretation |
|---|---|---|
| `macro_all_13` | all 13 | Penalises predicting a competency the reference never uses |
| `macro_gold_supported_labels` | the 10 with support | Describes performance on competencies genuinely in play |

Measured values differ by roughly 0.21 in F1. Neither replaces the other;
quoting only one would misrepresent the system.

### Set-level

```
Exact-set match = |{units where predicted set == reference set}| / N
Coverage        = |{units with ≥1 prediction}| / N
Abstention rate = |{units with no prediction}| / N
```

Exact-set match is strict: one extra or missing label makes the unit incorrect.
It is reported because a teacher receives a set, not a label.

---

## L. Resource-level derivation

Fragment predictions are aggregated upward: a resource is predicted to address a
competency when any of its fragments does. The aggregate retains supporting
fragment identifiers, individual confidences, a support count and the quotations.

The resource-level **reference** is derived from the fragment reference:

| Resource type | Derivation |
|---|---|
| Page | Union of the labels of its fragments |
| Quiz question | The labels of its single fragment |

**This is a derivation, not a second annotation.** It is recorded as such in the
output file, and the resource-level figures inherit every property of the
fragment annotation. Because aggregation takes a union, a spurious label on any
single fragment contaminates the whole resource, which is why resource-level
precision is lower than fragment-level precision.

Activity-level competency links available in Moodle were **not** used as
question-level references. Such a link describes an entire quiz and would be a
considerably coarser signal presented as ground truth.

---

## M. Error taxonomy

Each fragment is classified against non-exclusive categories:

| Category | Definition |
|---|---|
| `correct_prediction` | Predicted set equals reference set |
| `retrieval_failure` | A reference label was absent from the Top-K candidates |
| `llm_missed_gold_label` | A reference label was present in the candidates but not selected |
| `llm_wrong_selection` | A predicted label is not in the reference |
| `overprediction` | More labels predicted than referenced |
| `underprediction` | Fewer labels predicted than referenced |
| `parent_child_redundancy` | A competency and its direct parent are both predicted |
| `ambiguous_gold` | The annotator flagged the fragment ambiguous |
| `correct_abstention` | Abstained where the reference is empty |
| `incorrect_abstention` | Abstained where the reference is not empty |
| `exact_but_weak_evidence` | Quotations valid but rated 0 or 1 |

The pair `retrieval_failure` / `llm_missed_gold_label` partitions the causes of a
missed label and makes the attribution decidable rather than a matter of opinion.

**Overlap.** One mistake commonly triggers three categories. The flag counts
therefore do not sum to 35 and must not be read as a partition. A single
`primary_error_category` is assigned per fragment for a non-overlapping view, and
both are reported.

---

## N. Hierarchy analysis

A consistency check compares each prediction set against the parent–child
relations in the framework and emits:

| Warning | Condition |
|---|---|
| `parent_child_redundancy` | A competency and its direct parent both predicted for the same unit |
| `granularity_conflict` | Predictions mix hierarchy levels in a way warranting review |
| `invalid_hierarchy_reference` | A predicted identifier implies a relation absent from the framework |

The check uses only relations present in the framework. It is **diagnostic**: it
emits warnings and does not alter predictions.

### The ablation, and its standing

A separate simulated prediction set removes the parent where a parent and its
direct child are both predicted. It is written to a distinct location under
`data/experiments/`; the original predictions are untouched, and the output
records `original_predictions_modified: false`.

The ablation is **post-hoc**. The rule was formulated after inspecting the errors
and exploits a property of this reference — that no top-level competency is ever
correct. On a corpus where a parent is sometimes the right label, the same rule
would delete true positives. It is reported as a diagnosis showing the residual
error is systematic and mechanically detectable, and it is labelled a post-hoc
ablation wherever it appears. It is never presented as part of the original
system.

---

## O. Teacher validation workflow

The review unit is one predicted (resource, competency) pair; there are 34.

Each is presented with the resource and fragment text, the competency and its
description, the model's confidence, the **BM25 rank** or an explicit indication
that the competency was not retrieved, the evidence quotation with its manual
rating, hierarchy context, and any warning.

Displaying the BM25 rank lets a reviewer distinguish a retrieval failure from a
model error — the same distinction that structures the error analysis.

Available decisions: `accept`, `reject`, `modify` with one or more replacement
competencies, and `add` for a competency the model never proposed. A reviewer may
additionally rate whether the evidence was useful (0, 1, 2).

**Controls.** No decision is pre-filled and none is suggested. The reviewer's name
and role are required, and a role of `researcher` is reported separately from
`teacher` or `supervisor` and never counted as teacher validation. Decisions are
written atomically to a single file after a timestamped backup; re-deciding
replaces rather than duplicates. Identifiers are validated against the catalogue.

**Reporting rule.** Rates are computed only where decisions exist. With nothing
reviewed, acceptance, edit and rejection rates are recorded as null rather than
0.0, because 0.0 would assert that reviewers accepted nothing.

### Evidence-usefulness pilot

An exploratory comparison presents a suggestion either with the evidence quotation
hidden behind an explicit action (condition A) or shown alongside (condition B),
recording the decision, a 1–5 confidence rating, elapsed time, and whether a
reviewer in condition A chose to reveal the evidence.

Sampling is stratified over `parent_child_redundancy`, `incorrect_prediction` and
`correct_prediction`, rotating across courses within each stratum; conditions are
balanced within stratum. A fixed seed and a saved manifest make the design exactly
reproducible.

The design is exploratory. No significance test will be computed, and if only the
researcher participates the result is labelled a researcher pilot rather than a
teacher study — the label is derived from the recorded roles rather than assumed.

---

## P. Reproducibility controls

**Frozen artefacts.** Extraction output, normalised resources, fragments,
competencies, BM25 candidates, model tasks, model responses, the reference
annotation and the core metric files are treated as frozen. Scripts that could
overwrite them refuse to do so, and each verifies that protected checksums are
unchanged before and after running.

**Checksums.** A manifest records SHA-256 for every artefact together with the
Python version, pinned dependency versions, the model identifier, temperature,
candidate count, selection limit, corpus counts and unambiguous reference counts.
Artefacts that do not exist are recorded as null rather than with a placeholder.

**Determinism.** Temperature 0; fixed seeds for sampling; sorted, fixed-timestamp
archive construction. Regenerating a derived summary reproduces it byte for byte,
which was verified.

**Isolation of optional work.** Every post-hoc or optional experiment writes
under `data/experiments/` and cannot overwrite a core artefact.

**Cost control.** The optional unconstrained experiment spends API quota and
refuses to execute without an explicit authorisation flag. A dry run reports what
would be sent and makes no request. The evaluator refuses to score a run that has
not occurred and estimates nothing in its place.

**Secrets.** Credentials are read from the environment, never committed, and never
written to any generated output. The delivery build scans every staged text file
for key, token and password patterns and aborts on a match.

---

## Core system and post-hoc experiments

| Component | Standing |
|---|---|
| Extraction, normalisation, fragmentation | Core |
| BM25 retrieval | Core |
| Constrained model selection | Core |
| Evidence validation | Core |
| Resource aggregation | Core |
| Fragment- and resource-level evaluation | Core |
| Error analysis | Core |
| Manual evidence review | Core (human gate) |
| Teacher validation interface | Core (pending human use) |
| Hierarchy warnings | Post-hoc diagnostic |
| Child-preference ablation | **Post-hoc ablation; not the original system** |
| Ollama comparison | Post-hoc optional |
| Unconstrained all-13 comparison | Optional; software only, not run |

The reported headline results are those of the core system. The ablation figures
are always accompanied by their post-hoc label.
