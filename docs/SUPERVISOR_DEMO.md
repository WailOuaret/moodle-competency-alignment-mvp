# Supervisor demo script

**Moodle learning resource-to-competency alignment — reduced MVP**
**Presenter:** Wail Ouaret
**Audience:** Marie-Hélène Abel · Le Ngoc Luyen — UTC / Heudiasyc / CNRS
**Duration:** 10–15 minutes · 25 steps
**Date:** 2026-09-22

---

## Before you start

```bash
cd ~/projects/moodle_competency_mvp
source .venv/bin/activate
streamlit run app/Home.py          # leave running in a second terminal
```

Have open in tabs:

1. The Streamlit app (<http://localhost:8501>)
2. Local Moodle, logged in
3. `reports/RESULTS_ONE_PAGE.md`
4. A terminal in the project root

**Two rules for this demo.** Say "human-reviewed reference annotations", never
"gold standard". Never say the LLM "wins" without the precision trade-off.

---

## Part 1 — Framing (steps 1–4, ~2 min)

### 1. The research problem

**Open:** nothing — say it.

> "A Moodle course accumulates resources that are never linked to the
> competencies the programme claims to teach. A teacher cannot answer 'which of
> my materials covers this competency?', and the reverse is no easier. Manual
> tagging does not scale. I tested whether retrieval plus a constrained language
> model can propose alignments a teacher can **verify** — with evidence they can
> check, rather than a score they must trust."

**Likely question:** *Why not just ask an LLM to tag everything?*
**Answer:** "Because an untrusted tag is useless to a teacher. The design
requirement was auditability: every selection must quote the source verbatim, so
the teacher judges the justification rather than the model. That constraint is
what the experiment tests."

### 2. The reduced scope

**Open:** `reports/RESULTS_ONE_PAGE.md`, "The corpus" section.

> "On your guidance I cut the proposal to one end-to-end path that could actually
> be measured: local Moodle, 2 courses, Pages and quiz questions, 13 competencies.
> Deferred: the PHP plugin, write-back, LTI, PDFs and video, full ROME 4.0,
> recommendation. One measured path rather than several half-built ones."

**Likely question:** *Is the deferred work lost?*
**Answer:** "No — it is listed explicitly in `FINAL_EXPERIMENTAL_RESULTS.md`
§17 with status `DEFERRED`, and nothing deferred is presented as done anywhere."

### 3. The competency hierarchy in Moodle

**Open:** Moodle → Site administration → Competencies → the UTC GI framework.
**📸 Screenshot 1**

> "13 competencies: 3 parents, 10 children. Imported into Moodle, then normalized
> to JSONL. Parent/child only — no prerequisites in this framework, and I invented
> none. That hierarchy becomes important in step 18."

### 4. The two courses

**Open:** Moodle → MVP-SW and MVP-DATA, then course competency settings.
**📸 Screenshot 2**

> "Two courses, 20 resources total: 8 Pages and 12 quiz questions. I keep each
> quiz question as its own resource, because a quiz rarely assesses one competency
> while a question usually does."

---

## Part 2 — The pipeline (steps 5–11, ~4 min)

### 5. A Page example

**Open:** Moodle → MVP-SW → "Software Development Lifecycle and Deployment".
**📸 Screenshot 3**

> "This is a real Page. It becomes resource `page:1` and splits into two
> fragments."

### 6. A quiz question example

**Open:** Moodle → MVP-DATA quiz → preview a question.
**📸 Screenshot 4**

> "And this is a quiz question — its own resource, one fragment."

**Likely question:** *Why not use Moodle's own activity-level competency links?*
**Answer:** "They exist, and I deliberately did not use them as gold. They
describe a whole quiz, so using them as question-level ground truth would be a
much coarser signal presented as truth. I say so in the report."

### 7. Extraction and normalization

**Open:** terminal — `ls data/raw/api/ data/raw/sql/`

> "Pages came through the REST API. Quiz *question text* is not usably exposed by
> the web services on 5.2, so I read it from the database directly. That fallback
> is honest but local-development specific, and it is in the limitations."

### 8. A fragment

**Open:** app → **Home** → MVP-SW → expand `page:1`.

> "Normalized into 35 fragments: 23 Page chunks, 12 quiz questions. The fragment
> is the unit the model sees and the unit I annotated."

### 9. BM25 Top-5

**Open:** app → **1 Resource to Competencies** → `page:1` → scroll to
"Fragment-level detail" → expand a fragment. **📸 Screenshot 5**

> "For each fragment, BM25 retrieves the 5 nearest competencies. You can see the
> candidate list with scores, and a tick against the ones the model chose. **This
> Top-5 sets the recall ceiling for everything downstream** — Recall@5 is 0.9737."

### 10. Constrained Gemini

**Open:** same page, the prediction cards.

> "`gemini-3.5-flash`, temperature 0, restricted to those five candidates, at most
> three selections, abstention permitted. 35 of 35 responses came back valid; zero
> invalid were accepted."

### 11. Exact evidence

**Open:** same page — point at a quote block. **📸 Screenshot 6**

> "This is the core constraint. Every selection must carry a quote that is an
> **exact contiguous substring** of the fragment. A validator checks it
> mechanically. 83 of 83 quotes passed — the model never once fabricated a
> justification."

**Likely question:** *Doesn't that just force it to copy text?*
**Answer:** "Yes — that is the point. It cannot invent support. But it does not
guarantee the quote *proves* anything, which is exactly what step 19 measures."

---

## Part 3 — Results (steps 12–16, ~3 min)

### 12. The human-reviewed reference

**Open:** terminal —
`python scripts/12_validate_manual_annotations.py --mode final`

> "I reviewed all 35 fragments against the 13-competency catalogue: 38 reference
> labels, validator passes 35/35. I call these **human-reviewed reference
> annotations** — not independent blinded gold. One annotator, no second
> annotator, **no inter-annotator agreement**. Every score inherits that."

**Likely question (expect this one):** *Isn't that circular — you built the
system and the reference?*
**Answer:** "It is a real limitation and it is stated first in
`FINAL_LIMITATIONS.md`. Two things reduce the risk: I annotated against the
catalogue before comparing to predictions, and the evidence review was a separate
pass over quotes that independently reproduced both main findings. But it is one
person, and I do not claim otherwise."

### 13. BM25 Recall@1/3/5

**Open:** app → **6 Experiment Results**, section 1. **📸 Screenshot 7**

> "Recall@1 0.6842, @3 0.8684, @5 **0.9737**. MRR 0.8310. So retrieval alone
> finds the right competency first about two-thirds of the time, and within five
> almost always."

### 14. BM25 Top-1 as a classifier

**Open:** same section.

> "As a standalone tagger: precision 0.7429, recall 0.6842, F1 0.7123. That is the
> baseline the LLM has to beat."

### 15. Constrained Gemini metrics

**Open:** same page, sections 2–4.

> "Micro precision 0.7255, recall **0.9737**, F1 **0.8315**. And two macro
> numbers, deliberately: 0.6958 over all 13 labels, 0.9046 over the 10 labels the
> reference actually contains. Three parents have **zero** reference support, so a
> single macro figure would be misleading either way. I report both."

**Likely question:** *Which macro number is the real one?*
**Answer:** "Neither replaces the other. All-13 penalises predicting an
unsupported parent, which is a genuine defect. Gold-supported describes
performance on labels in play. Quoting only the higher one would misrepresent the
system."

### 16. The main interpretation

**Open:** the comparison table on the same page. **Slow down here.**

> "Three things.
>
> **One** — in this condition, the only label the system missed was one
> retrieval never offered it. `llm_missed_gold_label = 0`: the model selected
> **every** reference label available among its candidates, all 37. Its recall
> equals Recall@5 exactly. What it would select from all 13 is untested.
>
> **Two** — the trade-off. Against BM25 Top-1 the LLM gains **+0.29 recall** for
> **−0.02 precision**, and F1 goes 0.7123 → 0.8315. It does **not** win on every
> measure; BM25 Top-1 is slightly more precise.
>
> **Three** — abstention rate is 0.0, and that means **nothing**. There are no
> `NONE` fragments in the reference, so abstaining was never correct. It is
> untested, not good."

---

## Part 4 — Error analysis (steps 17–19, ~3 min)

### 17. The retrieval failure

**Open:** app → **1 Resource to Competencies** → the `quiz_question:1:4` resource.

> "Exactly one reference label was missed in the whole experiment. Reference
> `GI_C1_3`, IHM/UX. Look at the BM25 Top-5: `GI_C1_2, GI_C3_2, GI_C3, GI_C1_1,
> GI_C1_4` — `GI_C1_3` is **not there**. The model could not have chosen it. This
> is a **retrieval** failure, not a model failure, and no better prompt fixes it."

### 18. Parent-child overprediction

**Open:** app → **1 Resource to Competencies** → `page:1` → the `GI_C1` card with
its ⚠️ warning. **📸 Screenshot 6 again**

> "Now the dominant error. 14 false positives, and **10 of them — 71% — are the
> three parent competencies**, predicted alongside the *correct* child. Here the
> model said both `GI_C1_1` and its parent `GI_C1`, from the same sentence.
>
> And here is the honest part: **I never told it the convention.** I annotated
> only at child level; the prompt never says so. Saying `GI_C3` for a machine-
> learning fragment is defensible — my reference just does not count it. So this
> is a specification gap as much as a model defect."

**Likely question:** *So is your precision figure even meaningful?*
**Answer:** "It is meaningful but it must be read correctly: micro precision here
is substantially a measure of **granularity-convention agreement**, not topical
correctness. That sentence is in the limitations. It is also exactly why I want
teacher review — a teacher may find the extra parent tag harmless."

### 19. The evidence review result

**Open:** app → **4 Evidence Review**. **📸 Screenshot 8**

> "I rated all 83 quotes by hand for whether they *justify* the competency.
> **100% mechanically exact. But only 78.3% clearly supporting** — 19.3% partial,
> 2.4% unsupported.
>
> The interesting part: this pass was done quote-by-quote without looking at the
> metrics, and it found the same two defects. **Both** zero-rated quotes are on
> the retrieval-failure fragment — and my comment there names `GI_C1_3`, the exact
> label BM25 missed. And parent quotes were rated far worse than child ones: only
> **1 of 12** parent quotes clearly supporting, against **64 of 71** child quotes.
>
> So the conclusion is: exact-evidence validation stops fabrication, but it does
> not guarantee good reasoning. What it does is make weak reasoning **visible**."

---

## Part 5 — The tool (steps 20–22, ~2 min)

### 20. Function A — resource → competencies

**Open:** app → **1 Resource to Competencies**, browse one resource.

> "The first direction: for a resource, what does it teach? Each suggestion shows
> confidence, **BM25 rank** — or 'not retrieved', which tells a teacher whether it
> was a retrieval or a model problem — the evidence quote with its human rating,
> hierarchy context, and any warning."

### 21. Function B — competency → resources

**Open:** app → **3 Competency to Resources** → pick `GI_C3_2`. **📸 Screenshot 9**

> "The inverse direction you asked for: pick a competency, see which resources
> cover it and on what evidence. All 13 competencies have at least one predicted
> resource — but note the caution on screen: for the three parents that is the
> redundancy from step 18. Predicted coverage is not validated coverage."

### 22. The teacher interface

**Open:** app → **2 Teacher Review**, then **5 Review Progress**.
**📸 Screenshots 10 and 11**

> "And this is where a teacher accepts, rejects or modifies each of the 34
> suggestions, and tells me whether the evidence helped. It writes one CSV, with
> backups and atomic writes. It never writes to Moodle and never touches the
> reference, the model output or any metric file.
>
> **Progress shows 0 of 34.** No teacher has reviewed this yet, so I report **no
> acceptance rate** — the summary stores `null`, not zero. The two decisions on
> file are my own, from a separate runtime app, and are labelled researcher
> decisions."

---

## Part 6 — Closing (steps 23–25, ~2 min)

### 23. The optional graph ablation

**Open:** `reports/RESULTS_ONE_PAGE.md`, ablation table.

> "Since parent-child redundancy is mechanically detectable from the hierarchy, I
> tested removing it — as a **separate simulated output**, never modifying the
> predictions. Precision 0.7255 → 0.9024, F1 0.8315 → 0.9367, exact-set 0.63 →
> 0.91, and **recall unchanged**, because no parent is ever correct in this
> reference.
>
> I label it `POST-HOC MINIMAL GRAPH ABLATION` deliberately. The rule was designed
> after seeing the errors and exploits a property of my reference. It shows the
> errors are systematic — it does not mean I have a 0.94-F1 system."

### 24. Limitations

**Open:** `reports/FINAL_LIMITATIONS.md`, §1.

> "The three that matter: the corpus is small and built for this study — with 38
> labels, **one label is 2.6 points of recall**. There is **one annotator and no
> agreement measurement**. And the evidence review was done by the same person, so
> it is internal consistency, not independent validation.
>
> Plus: no `NONE` fragments so abstention is untested; Pages and quiz questions
> only; local Moodle; and **no significance testing** — the design does not
> support it."

### 25. Future work

> "In the order the evidence suggests:
>
> 1. **Real teacher decisions** — the interface is built, the data is the gap.
> 2. **Add `NONE` fragments** so abstention becomes testable.
> 3. **Run the unconstrained all-13 comparison** — the software is written and
>    audited as identical except for the candidate space; it just needs
>    authorization to spend quota.
> 4. **Fix granularity in the prompt** and re-measure, rather than pruning after
>    the fact.
> 5. **A second annotator on a subset**, for any agreement figure at all.
>
> Everything is reproducible from hashed frozen artefacts, 435 tests pass, and no
> secret appears in any generated report."

---

## Anticipated questions

| Question | Short answer |
|---|---|
| *Why BM25 and not embeddings?* | BM25 is transparent and reproducible, and the Top-5 recall ceiling of 0.9737 was high enough that retrieval was not the bottleneck for the model. Embeddings are a natural next comparison. |
| *Why Gemini specifically?* | Availability and cost. The pipeline is model-agnostic — an Ollama run exists in `data/experiments/`. External dependency is listed as a limitation. |
| *Could the LLM have memorised the framework?* | The competencies are a local UTC subset with French descriptions, supplied in the prompt. But the concern cannot be excluded and is not testable here. |
| *Why max 3 selections?* | The reference averages 1.09 labels per fragment; 3 gives headroom without letting the model list everything. It never became binding — the model averaged 1.46. |
| *Is 35 fragments enough to conclude anything?* | For an existence proof and an error profile, yes. For a performance estimate, no — and I make no such claim, nor any significance test. |
| *What would change your mind about the approach?* | A teacher finding the evidence quotes unhelpful. That is precisely what the A/B pilot is designed to test, and it has not been run. |

---

## Screenshot checklist

| # | Screen | Step |
|---|---|---|
| 1 | Moodle competency framework hierarchy | 3 |
| 2 | Moodle course competency selection | 4 |
| 3 | A Moodle Page | 5 |
| 4 | A Moodle quiz question | 6 |
| 5 | BM25 Top-5 candidate list with selections marked | 9 |
| 6 | A Gemini prediction with its exact evidence and ⚠️ warning | 11, 18 |
| 7 | Experiment Results — BM25 and LLM metrics | 13 |
| 8 | Evidence Review — the 0/1/2 distribution | 19 |
| 9 | Competency → Resources (inverse direction) | 21 |
| 10 | Teacher Review interface | 22 |
| 11 | Review Progress — 0 of 34 pending | 22 |

---

## If you are short on time

Cut to eight steps: **1 → 3 → 9 → 11 → 16 → 18 → 19 → 22**.
That is the problem, the framework, retrieval, evidence, the trade-off, the
dominant error, the evidence finding, and the honest status. About 6 minutes.
