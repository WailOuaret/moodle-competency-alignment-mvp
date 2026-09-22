# Supervisor demo checklist

Companion to `docs/SUPERVISOR_DEMO.md`. Print this; run the demo from it.

---

## T-30 minutes — environment

- [ ] `cd ~/projects/moodle_competency_mvp && source .venv/bin/activate`
- [ ] Local Moodle is running and you are logged in
- [ ] `streamlit run app/Home.py` in a second terminal, reachable at <http://localhost:8501>
- [ ] Browser tabs open: Streamlit · Moodle · `reports/RESULTS_ONE_PAGE.md`
- [ ] A clean terminal in the project root, font large enough to read
- [ ] Notifications silenced; screen sharing tested

## T-15 minutes — verify nothing is broken

Run these and confirm each line:

```bash
python scripts/12_validate_manual_annotations.py --mode final   # Status: PASSED
python -m pytest -q                                             # 435 passed
python -m compileall -q src scripts tests app                   # silent = OK
python scripts/ui_smoke_check.py                                # UI smoke check: OK
```

- [ ] Gold validator **PASSED**, 35/35
- [ ] Test suite passes
- [ ] Compile silent
- [ ] All 14 Streamlit pages **OK**

## T-5 minutes — click through once

- [ ] **Home** loads, shows 20 resources / 35 fragments / 13 competencies
- [ ] **1 Resource to Competencies** → `page:1` shows evidence and a ⚠️ warning
- [ ] **3 Competency to Resources** → `GI_C3_2` lists resources
- [ ] **4 Evidence Review** shows 83/83 rated, 78.3% clear
- [ ] **5 Review Progress** shows **0 of 34** reviewed
- [ ] **6 Experiment Results** loads all metric sections

---

## Run order — 25 steps

| # | Step | Open | 📸 |
|---:|---|---|:--:|
| **Framing** | | | |
| 1 | Research problem | — say it | |
| 2 | Reduced scope | `RESULTS_ONE_PAGE.md` | |
| 3 | Competency hierarchy | Moodle → Competencies | 1 |
| 4 | MVP-SW / MVP-DATA | Moodle → courses | 2 |
| **Pipeline** | | | |
| 5 | Page example | Moodle Page | 3 |
| 6 | Quiz-question example | Moodle quiz preview | 4 |
| 7 | Extraction / normalization | `ls data/raw/api data/raw/sql` | |
| 8 | A fragment | app → Home → `page:1` | |
| 9 | BM25 Top-5 | app → page 1 → fragment detail | 5 |
| 10 | Constrained Gemini | app → page 1 | |
| 11 | Exact evidence | app → page 1, quote block | 6 |
| **Results** | | | |
| 12 | Human-reviewed reference | terminal → validator | |
| 13 | BM25 Recall@1/3/5 | app → page 6, §1 | 7 |
| 14 | BM25 Top-1 P/R/F1 | app → page 6, §1 | |
| 15 | Gemini micro/macro | app → page 6, §2–4 | |
| 16 | **Main interpretation** | app → page 6, §3 | |
| **Errors** | | | |
| 17 | Retrieval failure | app → `quiz_question:1:4` | |
| 18 | **Parent-child overprediction** | app → page 1 → `GI_C1` card | 6 |
| 19 | **Evidence review result** | app → page 4 | 8 |
| **Tool** | | | |
| 20 | Function A | app → page 1 | |
| 21 | Function B | app → page 3 → `GI_C3_2` | 9 |
| 22 | Teacher interface | app → pages 2 and 5 | 10, 11 |
| **Close** | | | |
| 23 | Graph ablation | `RESULTS_ONE_PAGE.md` | |
| 24 | Limitations | `FINAL_LIMITATIONS.md` §1 | |
| 25 | Future work | — say it | |

**Pace:** steps 1–11 in ~6 min, 12–19 in ~6 min, 20–25 in ~3 min.
**If running long:** cut to **1 → 3 → 9 → 11 → 16 → 18 → 19 → 22**.

---

## Numbers to have memorised

| | |
|---|---|
| Corpus | 20 resources · 35 fragments · 13 competencies · 38 reference labels |
| BM25 Recall@1/3/5 | 0.6842 / 0.8684 / **0.9737** |
| BM25 Top-1 P/R/F1 | 0.7429 / 0.6842 / 0.7123 |
| Gemini micro P/R/F1 | 0.7255 / **0.9737** / **0.8315** |
| The trade-off | **−0.017 precision, +0.290 recall, +0.119 F1** |
| Macro F1 | 0.6958 (all 13) / 0.9046 (10 supported) |
| Evidence | **83/83 exact (100%)**, only **78.3% clearly supporting** |
| False positives | 14 total — **10 (71%) are parents** |
| Missed labels | **1**, and it is a retrieval failure |
| `llm_missed_gold_label` | **0** |
| Ablation | precision 0.7255 → **0.9024**, recall **unchanged** |
| Teacher decisions | **0 of 34** |

---

## Language discipline

| Say | Never say |
|---|---|
| "human-reviewed reference annotations" | "gold standard" / "blinded gold" |
| "higher recall and F1, slightly lower precision" | "the LLM wins" |
| "abstention is **untested**" | "the model abstains correctly" |
| "post-hoc minimal graph ablation" | "the graph layer improved the system" |
| "**no** teacher has reviewed this" | any acceptance rate |
| "researcher decisions" (for the 2 runtime reviews) | "teacher validation" |
| "predicted coverage" | "coverage" (when unvalidated) |

---

## Four questions that will come, and the first sentence of each answer

**"Isn't it circular — you built the system and the reference?"**
> "It's a real limitation and it's stated first in the limitations document."
Then: annotated against the catalogue before seeing predictions; the evidence
review was a separate pass that independently found the same defects; but it is
one person and I don't claim otherwise.

**"Which macro number is the real one?"**
> "Neither replaces the other."
All-13 penalises predicting an unsupported parent; gold-supported describes
labels in play. Quoting only the higher one would misrepresent the system.

**"Is your precision figure even meaningful, given the convention?"**
> "It's meaningful, but it has to be read as granularity-convention agreement."
71% of false positives are parents I never told the model not to predict. That
sentence is in the limitations, and it's exactly why teacher review matters.

**"Is 35 fragments enough?"**
> "For an existence proof and an error profile, yes. For a performance estimate,
> no."
One label is worth 2.6 points of recall; no significance test is claimed.

---

## Do not claim

- ❌ Any teacher acceptance rate — **0 of 34 reviewed**
- ❌ Any evidence-usefulness result — pilot designed, **0 responses**
- ❌ Any unconstrained all-13 result — software ready, **not run**
- ❌ That the graph ablation is a validated technique
- ❌ That abstention works
- ❌ Any statistical significance

---

## After the demo

- [ ] Note which steps prompted questions
- [ ] Ask directly: **will a supervisor or teacher run the 34-item review?**
      (`streamlit run app/Home.py` → page 2; ~30–45 min)
- [ ] Ask: **authorize the optional unconstrained all-13 run?** It spends API
      quota and the runner refuses without an explicit flag
- [ ] Record any scope change against the deferred list
