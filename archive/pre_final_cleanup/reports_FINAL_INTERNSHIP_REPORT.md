# From Moodle Learning Resources to Competency Alignments: a Constrained Retrieve-then-Generate MVP

**Internship technical / research report**

**Researcher:** Wail Ouaret (ENSIA)  
**Supervision:** Marie-Hélène Abel and Le Ngoc Luyen (UTC / Heudiasyc / CNRS)  
**Project:** Moodle Learning Resource → Competency Alignment MVP  
**Date:** 18 September 2026  
**Corpus:** two local Moodle 5.2 test courses (`MVP-SW`, `MVP-DATA`); 13 UTC Génie informatique competencies; 20 resources; 35 fragments

All numerical results below are taken from frozen experimental files. Original Gemini metrics are never replaced by the post-hoc hierarchy ablation. Ollama is an optional post-hoc comparison and is not mixed into `reports/metrics/constrained_llm_metrics.json`.

---

## 1. Title

Moodle Learning Resource → Competency Alignment MVP: BM25 candidate retrieval, constrained Gemini alignment with exact evidence, resource-level evaluation, and a teacher-facing review application.

---

## 2. Abstract

This internship built a reduced but complete research prototype that suggests UTC GI competencies for Moodle Pages and Quiz questions, shows the exact sentence used as evidence, and lets a human accept, reject, or modify each suggestion.

On a controlled corpus of 20 resources (8 Pages, 12 Quiz-question resources) fragmented into 35 units, BM25 retrieved a Top-5 candidate set with label-level Recall@5 = 0.9737. A constrained Gemini Flash model (`gemini-3.5-flash`, temperature 0, at most three labels, candidates restricted to that Top-5) produced 35/35 valid JSON responses. Fragment-level micro precision / recall / F1 were 0.7255 / 0.9737 / 0.8315. Gemini recall equalled BM25 Top-5 recall; the only missed reference label was caused by one retrieval failure, not by the model omitting a retrievable reference competency (`llm_missed_gold_label = 0`).

Eighty-three evidence quotes were mechanical exact substrings (83/83). A separate pedagogical review judged 65 (78.3%) clearly supportive, 16 (19.3%) partial, and 2 (2.4%) unsupported. Resource-level evaluation, using Page unions of fragment labels and keeping each quiz question independent, yielded micro F1 = 0.7931. A post-hoc child-preference hierarchy ablation raised fragment micro F1 from 0.8315 to 0.9367 without changing recall; those ablation numbers do not replace the original Gemini run. The original Gemini system did not use graph reasoning.

A Streamlit application implements the same pipeline at runtime (Gemini or local Ollama). Two researcher reviews exist on a live Gemini analysis. **Teacher reviews: 0. Supervisor reviews: 0.** RQ2 therefore remains waiting for a real teacher or supervisor session. LTI is documented as a future extension. A native Moodle PHP plugin is deferred.

---

## 3. Context and motivation

UTC courses already encode a Génie informatique competency framework, and Moodle can attach competencies to courses and activities. In practice, teachers still map learning resources to those competencies largely by hand. The mapping is slow, inconsistent across people, and difficult to audit because a competency ID on an activity does not show *which sentence* justified the link.

The internship therefore asked a narrow, supervisor-approved question: can an external Python system read Moodle Pages and Quiz questions, propose a small set of GI competencies, and show exact textual evidence a teacher can check? The work is a research MVP, not a production recommender, not a learning-path engine, and not a replacement for teacher judgement.

---

## 4. Problem statement

Given a Moodle learning resource (a Page or a Quiz question) and a closed catalogue of 13 UTC GI competencies, produce:

1. zero, one, or several competency identifiers;
2. a contiguous evidence span from the resource text for every selected identifier;
3. a resource-level aggregation that teachers can review;
4. the inverse view: for each competency, the resources that were suggested or validated.

The system must not freely invent competencies outside a retrieved candidate list. Evidence must be an exact substring, not a paraphrase. Quiz questions must remain independent resources: an activity-level Moodle competency must not be copied onto every question.

---

## 5. Research questions

**RQ1.** To what extent can Moodle resources and activities be automatically aligned with a competency framework?

**RQ2.** Do textual evidence spans help teachers verify alignment suggestions?

**RQ3.1.** What is the role of BM25 candidate preselection?

**RQ3.2.** Do minimal competency-graph constraints reduce incoherent or redundant predictions?

RQ1 is answered with measured retrieval and constrained-LLM metrics against a human-reviewed fragment reference. RQ3.1 is answered by the Top-5 recall, the single retrieval miss, and the comparison of BM25 Top-1 versus BM25 Top-5 + Gemini. RQ3.2 is answered only as a **post-hoc hierarchy ablation**, not as an in-model graph reasoner.

RQ2 is **not fully answered**. The project provides mechanical evidence validation, a researcher pedagogical rating of every quote, and a completed teacher-facing interface. Direct teacher usability validation remains pending. Researcher ratings and researcher ACCEPT/REJECT clicks are not a teacher study.

---

## 6. Scope of the MVP

**In scope**

- Local Moodle 5.2 development instance
- Two test courses: `MVP-SW`, `MVP-DATA`
- 13 UTC GI competencies (3 parents, 10 children)
- Moodle Pages and Quiz questions
- REST extraction plus read-only SQL for full question text
- Author-structure fragmentation
- BM25 Top-5
- Constrained Gemini (`gemini-3.5-flash`, temperature 0, max 3)
- Exact-substring evidence
- Human-reviewed fragment reference
- Resource aggregation and inverse index
- Error analysis and post-hoc hierarchy ablation
- Optional local Ollama comparison
- Teacher-facing Streamlit application

**Out of scope / deferred / future**

- Native Moodle PHP plugin — **DEFERRED**
- LTI launch from Moodle — **OPTIONAL / FUTURE EXTENSION** (documentation only)
- ROME 4.0, OCR, scanned PDFs, video
- Relation types (`teaches` / `assesses` / `supports` / `mentions`)
- Recommendation and learning paths
- LLM fine-tuning
- Unconstrained Gemini over all 13 competencies (not run)
- Formal multi-teacher controlled study

---

## 7. Related work

Automatic skill and competency tagging sits between information retrieval, multi-label classification, and educational data mining. Typical families of methods are:

- **Lexical retrieval** (BM25, TF–IDF) over competency labels, descriptions, and keywords. These methods are transparent and cheap, but they confuse close siblings (for example user-centred design versus software testing).
- **Supervised multi-label classifiers** (linear models, sentence transformers). They need substantial labelled training data, which this internship corpus does not provide.
- **Zero-shot or open LLM labelling** over a full catalogue. Models can paraphrase well but often over-predict, invent IDs, or quote evidence that is not in the source.
- **Retrieve-then-generate** pipelines: a ranker shortlists candidates; a constrained generator selects among them and must ground each label in a span.

Moodle itself stores competency frameworks and activity mappings, but it does not explain *why* a resource matches a competency. External learning-tool architectures (LTI) can attach research tools without rewriting Moodle in PHP. This MVP follows that split: Moodle holds content and the GI framework; Python holds retrieval, generation, evidence checks, and review.

---

## 8. Reference paper and adaptation

The internship adapts the existing UTC pipeline documented as *From Learning Resources to Competencies: LLM-Based Tagging with Evidence and Graph Constraints* (Le, Abel, Laforge, 2026) and the accompanying `competency-tagging` software.

That reference pipeline:

1. retrieves BM25 Top-K competency profiles;
2. calls an LLM with a JSON contract and evidence spans;
3. validates (and optionally repairs) quotes;
4. applies graph reconciliation (parent–child redundancy, prerequisites, label caps);
5. aggregates fragments to resources;
6. evaluates micro/macro P/R/F1 and evidence validity.

This Moodle MVP keeps the same scientific skeleton and changes the setting:

| Reference pipeline | This MVP |
|---|---|
| Generic learning-resource fragments | Moodle Pages and independent Quiz questions |
| OpenAI tagging | Constrained Gemini Flash for the frozen experiment; optional Ollama |
| Evidence repair | Frozen experiment: exact substring required; invalid JSON rejected, not silently repaired into new labels |
| Graph inside the tagging run | **Not used by Gemini.** Hierarchy is a post-hoc ablation and a runtime warning / reconciled view |
| Large gold collections / CV | 35-fragment human-reviewed reference, single researcher |
| Standalone runner | Moodle extraction + teacher-facing Streamlit review |

The adaptation is therefore institutional and technical (Moodle 5.2, UTC GI import, quiz-question independence, teacher review roles), not a claim of a new tagging algorithm.

---

## 9. Moodle technical exploration

The development site is Moodle 5.2.1+ (local Docker / WSL2, PostgreSQL). Two courses were created for the experiment. The 13-competency CSV was imported under framework idnumber `UTC_GI_MVP_2026`.

Extraction used:

- Moodle REST for course, Page, and Quiz metadata;
- read-only SQL for full Quiz question text, which REST did not always expose completely.

Python never wrote competency decisions back into Moodle. Activity-level links in `data/gold/manual_moodle_links.csv` were inspected as Moodle UI mappings and were **not** used as fragment or question gold.

Native plugin development was not started (Section 36 / Phase I). LTI was studied on paper only (`docs/LTI_INTEGRATION_FEASIBILITY.md`).

---

## 10. Competency framework

The source UTC GI framework is larger. Supervisors asked for about 10–20 competencies. Thirteen IDs were selected so that parent–child structure survived and two coherent courses could be taught against it:

- **GI_C1** software design and development — children GI_C1_1 … GI_C1_4
- **GI_C2** architectures, networks, cybersecurity — children GI_C2_1 … GI_C2_3
- **GI_C3** data, knowledge, databases, AI — children GI_C3_1 … GI_C3_3

Parent and child identifiers are distinct evaluation labels. Predicting a parent does not automatically satisfy a child. In this corpus the human-reviewed reference contains **zero** positive labels for GI_C1, GI_C2 and GI_C3. That fact later explains why child-preference looks strong and why it may not generalize.

---

## 11. Dataset / corpus construction

| Item | Count |
|---|---:|
| Courses | 2 |
| Pages | 8 |
| Quiz activities | 2 (not used as evaluation units) |
| Quiz-question resources | 12 |
| Normalized resources | 20 |
| Fragments | 35 (23 `page_chunk` + 12 `quiz_question`) |
| Competencies | 13 |
| Human-reviewed reference rows | 35 / 35 |
| Reference labels | 38 |
| Multi-label fragments | 3 |
| Ambiguous fragments | 1 (`page:3#f003`) |
| NONE fragments | 0 |

The corpus is small, English, text-native, and built for a research demo. It is not a random sample of UTC production courses.

---

## 12. Resource extraction

Scripts `01_extract_moodle_rest.py` and `02_extract_moodle_sql.py` produced raw dumps. Script `03_normalize_resources.py` built `data/processed/resources.jsonl` (20 records). HTML was reduced to readable text. Quiz questions stayed one resource each.

Runtime ingestion later reused the same extractors for existing Moodle resources and added paste / TXT / HTML / text-native PDF (no OCR) for the teacher app. Runtime files are isolated under `data/runtime/` and do not rewrite frozen experiment files.

---

## 13. Fragmentation

Script `05_fragment_resources.py` split Pages on author-created structure (headings / pedagogical blocks) before falling back to length. Each Quiz question is exactly one fragment. Fragment identifiers look like `page:5#f001` or `quiz_question:1:4#f001`.

Fragmentation is the unit of retrieval and of the frozen Gemini experiment. Teachers still see resource-level suggestions; fragments are an internal pedagogical grain, not a Moodle object.

---

## 14. Competency profiles

Script `04_normalize_competencies.py` wrote `data/processed/competencies.jsonl`. Each profile concatenates identifier, short name, description, and available keywords/aliases for BM25. Hierarchy neighbours (parent / children) are stored for later graph checks but were **not** passed to Gemini as a reasoning graph.

---

## 15. BM25 candidate retrieval

For each fragment, BM25 ranked the 13 profiles and kept Top-5. That shortlist is the only legal candidate space for the constrained LLM.

Measured against the human-reviewed reference (`reports/metrics/bm25_metrics.json`):

| Metric | Value |
|---|---:|
| Recall@1 | 0.6842 |
| Recall@3 | 0.8684 |
| Recall@5 | 0.9737 |
| Hit@1 | 0.7429 |
| Hit@3 | 0.8857 |
| Hit@5 | 0.9714 |
| MRR | 0.8310 |
| Top-1 micro P / R / F1 | 0.7429 / 0.6842 / 0.7123 |
| Top-1 macro F1 | 0.5900 |

Recall@K is label-level over 38 reference labels. Hit@K and MRR are fragment-level over 35 non-empty reference sets.

The known miss: fragment `quiz_question:1:4#f001`, reference **GI_C1_3**, absent from Top-5 (`GI_C1_2`, `GI_C3_2`, `GI_C3`, `GI_C1_1`, `GI_C1_4`). This single miss is the entire recall gap at K = 5 (1/38).

RQ3.1 interpretation on this corpus: Top-5 is almost sufficient coverage. BM25 Top-1 as a classifier already has useful precision (0.7429) but weaker recall (0.6842). The constrained LLM is therefore mainly a recall-preserving reranker / multi-label selector inside a high-recall shortlist, not a search over the whole catalogue.

---

## 16. Constrained LLM alignment

Tasks (`data/interim/llm_tasks.jsonl`) bind each fragment to its Top-5, the JSON schema, temperature 0, maximum three selections, and an abstention option. Gemini checkpoints were resumed, never restarted. File: `data/interim/gemini_validated.jsonl`.

Contract:

- selected IDs ⊆ BM25 Top-5;
- at most three IDs;
- each ID has a contiguous quote from the fragment;
- empty selection is allowed.

Result: **35 / 35 valid**. Coverage = 1.0. Abstention = 0.0. Average predicted labels per fragment = 1.4571.

---

## 17. Evidence extraction and validation

A quote is **mechanically valid** if and only if it is an exact contiguous substring of `fragment_text`. All 83 frozen quotes passed that check.

A quote is **pedagogically supportive** only if a human rates it:

- 2 = clearly supports the predicted competency
- 1 = partial / ambiguous
- 0 = unsupported

Human Gate 2 (researcher): 65 / 16 / 2 = 78.3% / 19.3% / 2.4%.

Required wording: *100% of evidence spans were mechanically traceable exact substrings, while 78.3% were judged to clearly support the predicted competency.* This is not “evidence was 100% correct.”

Both unsupported quotes belong to `quiz_question:1:4#f001` predicted **GI_C1_1** (reference **GI_C1_3**):

- `User_Centred_Design`
- `Testing a prototype with representative users`

They appear in the stem, but they do not justify the software-development child that Gemini selected after retrieval failed to offer GI_C1_3.

---

## 18. Human-reviewed reference

File: `data/gold/manual_fragment_annotations.csv`. Annotator: Wail Ouaret, 2026-09-18. Validator: `python scripts/12_validate_manual_annotations.py --mode final` **PASSED**.

This set is a **human-reviewed reference**. It is not described as fully independent blinded gold created entirely from scratch. There is no second annotator and no inter-annotator agreement. The researcher had access to the catalogue and the fragment text; activity-level Moodle links were not copied onto fragments.

| Property | Value |
|---|---|
| Rows complete | 35 / 35 |
| Labels | 38 |
| Multi-label | 3 |
| Ambiguous | 1 (`page:3#f003`) |
| NONE | 0 |

The absence of NONE examples is a corpus limitation: the model was never tested on fragments that should abstain.

---

## 19. Experimental protocol

1. Freeze resources, fragments, BM25, and Gemini once complete.
2. Finalize the 35-row reference independently of metric scripts (researcher review).
3. Evaluate BM25 (script 15) and constrained Gemini (script 16) only after the reference validator passes.
4. Rate evidence pedagogically (scripts 17–18, helper `review_evidence_pedagogically.py`).
5. Run evidence-aware error analysis (script 19).
6. Derive resource gold from fragment unions / question labels (script 22). **Do not** use `manual_moodle_links.csv`.
7. Run graph *warnings* on frozen predictions, then a separate child-preference copy under `data/experiments/` (script 23). Do not overwrite Gemini files.
8. Optional Ollama: same tasks, `mistral:latest`, files only under `data/experiments/`.
9. Runtime UI uses the same modules but writes to `data/runtime/` and `data/reviews/teacher_reviews.csv`.

No metric in this report is fabricated. Where a file does not exist (frozen Ollama metrics JSON), the table cell is NA.

---

## 20. BM25 results

See Section 15. Comparison as a standalone Top-1 classifier versus the later LLM:

| System | Micro P | Micro R | Micro F1 |
|---|---:|---:|---:|
| BM25 Top-1 | 0.7429 | 0.6842 | 0.7123 |
| BM25 Top-5 + constrained Gemini | 0.7255 | 0.9737 | 0.8315 |

On this corpus, Gemini raises recall and F1 relative to Top-1 BM25, with a small precision drop. That is a measured difference, not a claim that BM25 is unnecessary: without Top-5, Gemini would not have been constrained, and the only gold miss is exactly a retrieval miss.

---

## 21. Gemini constrained results

Source: `reports/metrics/constrained_llm_metrics.json` and `reports/metrics/macro_label_views.json`.

| Metric | Value |
|---|---:|
| Micro precision | 0.7255 |
| Micro recall | 0.9737 |
| Micro F1 | 0.8315 |
| Macro all 13 P / R / F1 | 0.6833 / 0.7436 / 0.6958 |
| Macro over reference-supported labels F1 | 0.9046 |
| Exact-set match | 0.6286 |
| Coverage | 1.0 |
| Abstention | 0.0 |
| Average predicted labels | 1.4571 |

BM25 Top-5 recall = Gemini recall = 0.9737. `llm_missed_gold_label = 0`. The precision problem is overprediction, especially broad parents.

Macro over all 13 is pulled down by GI_C1, GI_C2 and GI_C3, which have no reference support but are sometimes predicted. The gold-supported macro is a second view, not a replacement of the frozen full-13 macro.

---

## 22. Evidence evaluation

| Item | Value |
|---|---|
| Evidence rows | 83 quotes (not 83 fragments) |
| Mechanical exact substring | 83 / 83 = 100% |
| Pedagogical 2 / 1 / 0 | 65 / 16 / 2 |
| Clear rate | 78.3% |
| Partial rate | 19.3% |
| Unsupported rate | 2.4% |

Join key for later error flags: `fragment_id` + `competency_id`. Mechanical validity is automatic; pedagogical ratings are human and single-researcher.

---

## 23. Error analysis

Source: `reports/metrics/error_summary.json`. Overlapping flags are **not** a partition. Primary category is a presentation partition (priority: retrieval_failure > … > correct_prediction).

**Overlapping flags (35 fragments)**

| Flag | n |
|---|---:|
| correct_prediction | 22 |
| llm_wrong_selection | 13 |
| overprediction | 13 |
| parent_child_redundancy | 10 |
| retrieval_failure | 1 |
| underprediction | 1 |
| llm_missed_gold_label | 0 |
| incorrect_abstention | 0 |
| correct_abstention | 0 |
| ambiguous_gold | 1 |
| evidence_clear | 23 |
| evidence_partial | 11 |
| evidence_unsupported | 1 |
| exact_but_weak_evidence | 12 |

**Primary-category partition**

| Category | n |
|---|---:|
| llm_wrong_selection | 12 |
| correct_prediction | 21 |
| retrieval_failure | 1 |
| ambiguous_gold | 1 |

Dominant pattern: Gemini often adds a parent next to a correct child. That is an overprediction and a hierarchy redundancy, not a retrieval miss. The retrieval miss is isolated to `quiz_question:1:4`.

---

## 24. Resource-level evaluation

Teachers assign competencies to resources. Page reference = union of that Page’s human-reviewed fragment labels. Quiz question reference = that question’s fragment labels. No Moodle activity label was propagated to every question.

| Metric | Value |
|---|---:|
| Resources | 20 / 20 |
| Micro P / R / F1 | 0.6765 / 0.9583 / 0.7931 |
| TP / FP / FN | 23 / 11 / 1 |
| Macro all 13 P / R / F1 | 0.7051 / 0.7308 / 0.7026 |
| Macro reference-supported P / R / F1 | 0.9167 / 0.9500 / 0.9133 |
| Exact-set accuracy | 0.45 |
| Average reference labels | 1.20 |
| Average predicted labels | 1.70 |
| Average absolute label-count error | 0.50 |
| Coverage / abstention | 1.0 / 0.0 |

Precision is lower than at fragment level because false-positive parents union onto Pages. The single false negative is the same retrieval failure (`quiz_question:1:4`, GI_C1_3 vs predicted GI_C1_1).

---

## 25. Post-hoc graph / hierarchy ablation

**The original Gemini system did not use graph reasoning.** Script 23 first wrote non-destructive warnings, then a simulated child-preference copy:

> remove parent P if P and a direct child C are both predicted.

This is **not** prediction correction of stored Gemini labels.

Fragment-level findings: 10 fragments with parent–child redundancy; 10 redundant pairs; 7 granularity conflicts; invalid hierarchy references = 0. Parents causing redundancy: GI_C3 = 6, GI_C1 = 3, GI_C2 = 1. Ten redundant parent instances removed; **0 true reference labels removed**.

| Level | Original | Post-hoc child preference | Δ |
|---|---:|---:|---:|
| Fragment P | 0.7255 | 0.9024 | +0.1769 |
| Fragment R | 0.9737 | 0.9737 | 0 |
| Fragment F1 | 0.8315 | 0.9367 | +0.1052 |
| Fragment exact-set | 0.6286 | 0.9143 | +0.2857 |
| Fragment avg labels | 1.4571 | 1.1714 | −0.2857 |
| Resource P | 0.6765 | 0.9200 | +0.2435 |
| Resource R | 0.9583 | 0.9583 | 0 |
| Resource F1 | 0.7931 | 0.9388 | +0.1457 |
| Resource exact-set | 0.45 | 0.90 | +0.45 |
| Resource label-count error | 0.50 | 0.05 | −0.45 |

Why the jump is large here: the reference never used the three broad parents, so dropping them only removes false positives. This will not automatically generalize to a corpus where parent labels are genuine gold. Hierarchy results must never be presented as “the Gemini score.”

Wrong substitutions (GI_C1_1 instead of GI_C1_3) are **not** repaired by this rule.

---

## 26. Ollama post-hoc comparison

Optional local backend: `mistral:latest` via Ollama, same 35 constrained tasks, temperature 0, BM25 Top-5. Checkpoints: `data/experiments/ollama_constrained_*.jsonl` (35/35 valid). Manifest records this as **not part of the original Gemini run**.

No frozen `reports/metrics/ollama_constrained_metrics.json` was written (`scripts/30_evaluate_ollama_constrained.py` was not part of the frozen Gemini evaluation). Final tables therefore leave Ollama metric cells as **NA**. Checkpoints are preserved for reproducibility.

The teacher UI can call Ollama. One live demonstration on the Moodle Page *Knowledge Representation, Logic and Ontologies* (`page:5`):

| Backend | Original labels | Hierarchy-reconciled |
|---|---|---|
| Gemini `an_433ef0bd8a6d9752` | GI_C3, GI_C3_1 | GI_C3_1 |
| Ollama `an_5133dbb54c6266db` | GI_C3_1 | GI_C3_1 |

This is a **demonstration case**. It does not rank backends globally.

---

## 27. Teacher-facing runtime application

Launch:

```bash
streamlit run app.py
```

Inputs: existing Moodle Page, existing Moodle Quiz question, pasted text, TXT, HTML, text-native PDF (no OCR).

Pipeline: resource → extraction → normalization → fragmentation → BM25 Top-5 → constrained LLM → exact evidence validation → post-processing hierarchy check → resource aggregation → human review.

Backends: Gemini (`gemini-3.5-flash`) and Ollama (`mistral:latest`). Reviewer roles: researcher, teacher, supervisor. Decisions: ACCEPT / REJECT / MODIFY. No default decision is preselected. Pages: Analyze Resource, Review Suggestions, Competency → Resources, Review History, Research Results.

Runtime data stay under `data/runtime/`. Frozen scientific files are protected. Live Gemini and live Ollama runtime tests were completed. Software tests at the last pre-finalization check: 217 passed, `compileall` succeeded.

---

## 28. Resource → competencies workflow

Function A is the teacher’s main loop. After analysis the UI shows, per suggestion: competency ID and name, original versus hierarchy-reconciled sets, BM25 rank, confidence, quote highlighted in fragment context, and hierarchy warnings. The reviewer must explicitly choose ACCEPT, REJECT, or MODIFY. MODIFY replacements are limited to the 13-catalogue IDs.

Unreviewed suggestions remain model suggestions. They are never labelled “validated.”

---

## 29. Competency → resources workflow

Function B is an inverse index over stored analyses, not a second model. Competency → Resources keeps Gemini and Ollama analyses separate, shows backend/model, and splits MODEL SUGGESTIONS from VALIDATED mappings (those with a human decision). Researcher rows are labelled as researcher and are not teacher-study results.

---

## 30. Human validation

**Status: WAITING_FOR_HUMAN**

| Role | Completed ACCEPT/REJECT/MODIFY rows |
|---|---:|
| teacher | 0 |
| supervisor | 0 |
| researcher | 2 (Wail Ouaret, 2026-09-18, Gemini analysis `an_433ef0bd8a6d9752`: REJECT GI_C3, ACCEPT GI_C3_1) |

Researcher reviews are not teacher-study results. RQ2 form `data/templates/human_validation_form.csv` is header-only. Protocol: `docs/HUMAN_VALIDATION_PROTOCOL.md`. RQ2 guide: `docs/RQ2_VALIDATION_GUIDE.md`. Summary script: `python scripts/34_summarize_human_validation.py` (prints `HUMAN VALIDATION NOT YET PERFORMED` when teacher/supervisor counts are zero).

What the project already contributes to RQ2 without teacher data: mechanical traceability, pedagogical ratings, and a UI that can show or (in the RQ2 form) withhold evidence. What it does **not** contribute: a measured teacher usefulness effect.

---

## 31. Discussion

On this small corpus the retrieve-then-generate contract works as designed. BM25 almost always puts the reference child in Top-5. Gemini almost always selects every retrievable reference label and then often adds a parent. Exact quotes are easy to check mechanically and mostly, but not always, pedagogically fair. Resource-level precision is the teacher-visible cost of that parent overprediction.

The hierarchy ablation is scientifically useful and easy to oversell. It shows that a one-line deterministic rule, applied after the fact, removes the dominant false-positive pattern **in a reference set that never uses parents**. The correct sentence for a supervisor is: Gemini did not use the graph; a post-hoc child-preference view improves precision here; we do not know whether teachers want parent labels, child labels, or both.

RQ1, limited to this MVP: automatic alignment is feasible enough to be worth teacher review (high recall, inspectable evidence), not accurate enough to write Moodle mappings without a human. RQ3.1: BM25 Top-5 is doing the coverage job; the remaining miss is lexical confusion on a quiz stem. RQ3.2: graph constraints help if treated as post-processing against a child-only reference; they are untested as an in-model constraint and untested where parents are gold. RQ2: still a human question.

---

## 32. Limitations

- 35 fragments, 20 resources, 13 competencies, two courses, one institution, one framework.
- Single-researcher reference and single-researcher pedagogical ratings.
- No NONE examples, so abstention behaviour is unevaluated.
- Text-focused resources; no OCR, video, or scanned slides.
- Constrained candidate space: Gemini cannot recover a label BM25 omitted.
- Post-hoc hierarchy experiment is not the deployed Gemini model.
- Runtime demos are not the frozen 35-fragment experiment.
- Gemini versus Ollama differences are not a completed metric study.
- No teacher or supervisor validation yet.
- Possible annotation influence: the same researcher designed the courses, reviewed fragments, and rated evidence.

---

## 33. Threats to validity

**Internal.** The reference is human-reviewed by the system author, not independent blinded gold from scratch. Seeing fragment text while knowing the 13-way catalogue can bias labels toward children that the pages were written to teach. Error flags such as `llm_wrong_selection` inherit that reference.

**Construct.** Exact-substring validity is not pedagogical support. Resource gold is derived from fragments, so resource metrics are not a second independent annotation. Exact-set accuracy punishes extra parents even when the child is correct; that is intentional but strict.

**External.** Results may not transfer to French production courses, larger catalogues, mixed media, or teachers who routinely want parent competencies. Child-preference gains rely on zero parent support in this reference.

**Conclusion validity.** No significance tests are reported. n = 35 fragments is a demo corpus. One Ollama runtime example is not a backend bake-off.

**Runtime versus experiment.** Live analyses can differ from frozen files (new fragmentation of the same Page, model sampling even at temperature 0, prompt packaging). Research Results in the UI read frozen metrics; Analyze Resource does not silently update them.

---

## 34. Reproducibility

Offline evaluation does not need Moodle, Gemini, or Ollama. Required inputs are already in `data/processed/`, selected `data/interim/` checkpoints, `data/gold/`, and `reports/metrics/`.

```bash
python -m pytest -q
python -m compileall -q src scripts tests app.py pages
python scripts/20_write_reproducibility_manifest.py
python scripts/34_summarize_human_validation.py
python scripts/35_generate_final_figures.py
```

Secrets stay in `.env` (never committed). The reproducibility manifest hashes artefacts and records package versions; it does not read `.env`. See `reports/FINAL_REPRODUCIBILITY_CHECK.md` and `reports/reproducibility_manifest.json`.

---

## 35. Future work

1. Real teacher or supervisor review of 2–5 resources (the only remaining human gate).
2. Optional RQ2 within-reviewer evidence on/off form — still a tiny exploratory exercise.
3. Larger, multi-annotator reference including NONE fragments and genuine parent gold.
4. LTI 1.3 launch from Moodle (`docs/LTI_INTEGRATION_FEASIBILITY.md`).
5. Decide whether child-preference should become a default post-process or remain a warning.
6. If supervisors later request it: unconstrained-13 ablation, frozen Ollama metrics, or a native plugin (currently deferred).

Do not add new research features before the supervisor meeting.

---

## 36. Conclusion

The internship MVP is technically complete for its reduced scope. Moodle resources can be aligned automatically under a BM25 Top-5 + constrained Gemini contract with inspectable exact evidence. On the 35-fragment human-reviewed reference, fragment micro F1 is 0.8315 with very high recall and moderate precision. The only missed reference competency is a retrieval failure. Evidence is 100% mechanically traceable and 78.3% pedagogically clear. Resource-level F1 is 0.7931. A post-hoc hierarchy rule improves precision here because broad parents were never in the reference; that rule was not part of Gemini. A teacher-facing application is ready. **Real teacher/supervisor validation has not been performed.** LTI is a future extension. A native Moodle plugin is deferred.

Native Moodle plugin development was explicitly deferred for the MVP. Additional PHP development, Moodle permission and security complexity, maintenance, and deployment cost would have coupled the experimental pipeline to Moodle internals. The current Python web application demonstrates the research workflow without that coupling.

**Native plugin = DEFERRED EXTENSION.**  
**LTI = FUTURE EXTENSION.**  
**Teacher/supervisor validation = WAITING_FOR_HUMAN.**
