# Data dictionary

Field provenance uses:

- **automatic** — produced by Python / Moodle extraction
- **human** — filled by a researcher or teacher
- **mixed** — automatic template with human values

Required means required for that file’s intended use, not that every experimental gate is open.

Do not treat PARTIAL Gemini or blank gold cells as final results.

---

## `data/processed/resources.jsonl`

Normalized Moodle Pages and Quiz questions. Quiz questions remain independent resources.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| resource_id | string | Stable resource key (`page:{id}` or `quiz_question:{quiz}:{question}`) | Python normalization | automatic | yes | `scripts/03_normalize_resources.py` |
| resource_type | string | `page` or `quiz_question` | Moodle + normalization | automatic | yes | REST / SQL |
| title | string | Display title | Moodle | automatic | yes | REST / SQL |
| activity_id | int | Moodle activity instance id | Moodle | automatic | yes | REST / SQL |
| activity_name | string | Activity name | Moodle | automatic | yes | REST |
| course_id | int | Moodle course id | Moodle | automatic | yes | REST |
| course_shortname | string | `MVP-SW` or `MVP-DATA` | Moodle | automatic | yes | REST |
| course_fullname | string | Course full name | Moodle | automatic | yes | REST |
| course_module_id | int | `cmid` | Moodle | automatic | yes | REST |
| section_id | int | Course section id | Moodle | automatic | no | REST |
| section_name | string | Section name | Moodle | automatic | no | REST |
| section_number | int | Section number | Moodle | automatic | no | REST |
| source_item_id | int | Page id or question id | Moodle | automatic | yes | REST / SQL |
| source_extraction | string | `moodle_rest` or SQL marker | Python | automatic | yes | extraction scripts |
| text | string | Clean visible body | Moodle HTML cleaned | automatic | yes | `html_clean` |
| search_text | string | Retrieval text (title + body) | Python | automatic | yes | normalization |
| metadata | object | Extra Moodle fields (visibility, completion, formats) | Moodle | automatic | no | REST |

---

## `data/processed/fragments.jsonl`

Page chunks plus one fragment per Quiz question.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| fragment_id | string | `{resource_id}#f{nnn}` | fragmentation | automatic | yes | `scripts/05_fragment_resources.py` |
| fragment_index | int | 1-based index inside the resource | Python | automatic | yes | fragmentation |
| fragment_type | string | `page_chunk` or `quiz_question` | Python | automatic | yes | fragmentation |
| fragments_in_resource | int | How many fragments that resource produced | Python | automatic | yes | fragmentation |
| resource_id | string | Parent resource | resources.jsonl | automatic | yes | copy |
| resource_type | string | `page` or `quiz_question` | resources.jsonl | automatic | yes | copy |
| text | string | Fragment body | resources.jsonl | automatic | yes | split of `text` |
| search_text | string | Query text for BM25 | Python | automatic | yes | fragmentation |
| word_count | int | Token/word count of fragment text | Python | automatic | no | fragmentation |
| character_count | int | Character count | Python | automatic | no | fragmentation |
| fragmentation_version | string | Algorithm version | Python | automatic | yes | `"1.0"` |
| title / activity / course / section fields | mixed | Copied context | resources.jsonl | automatic | yes | copy |
| metadata | object | Nested source metadata | resources.jsonl | automatic | no | copy |

---

## `data/processed/competencies.jsonl`

Normalized 13 UTC GI competencies after Moodle import.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| idnumber | string | GI id (`GI_C1`, `GI_C1_1`, …) | Moodle competency table | automatic | yes | SQL export + `scripts/04_normalize_competencies.py` |
| competency_id | int | Moodle numeric competency id | Moodle | automatic | yes | SQL |
| shortname | string | Moodle short name | Moodle | automatic | yes | SQL |
| description_raw | string | HTML description | Moodle | automatic | no | SQL |
| description_text | string | Stripped description | Python | automatic | yes | HTML clean |
| full_text / search_text | string | Retrieval documents | Python | automatic | yes | normalization |
| parent_idnumber | string | Parent GI id, empty for roots | Moodle Parent ID number | automatic | yes | SQL / CSV hierarchy |
| parent_competency_id | int/null | Moodle parent numeric id | Moodle | automatic | no | SQL |
| parent_shortname | string | Parent label | Moodle | automatic | no | SQL |
| depth | int | 0 parent, 1 child in this subset | Python | automatic | yes | hierarchy |
| hierarchy_idnumbers | string[] | Path of IDs | Python | automatic | yes | hierarchy |
| hierarchy_labels | string[] | Path of shortnames | Python | automatic | yes | hierarchy |
| framework_id | int | Moodle framework id | Moodle | automatic | yes | SQL |
| framework_idnumber | string | `UTC_GI_MVP_2026` | Moodle | automatic | yes | SQL |
| framework_shortname | string | Framework name | Moodle | automatic | yes | SQL |
| sortorder | int | Moodle order | Moodle | automatic | no | SQL |
| source_extraction | string | `postgresql_read_only` | Python | automatic | yes | SQL |
| normalization_version | string | `"1.0"` | Python | automatic | yes | Python |
| metadata | object | rule/path timestamps | Moodle | automatic | no | SQL |

---

## `data/interim/bm25_candidates.jsonl`

BM25 Okapi Top-5 per fragment.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| fragment_id | string | Query fragment | fragments.jsonl | automatic | yes | `scripts/06_retrieve_bm25_candidates.py` |
| resource_id / resource_type / course / activity / title | mixed | Copied context | fragments | automatic | yes | copy |
| fragment_text | string | Body used in the query | fragments | automatic | yes | copy |
| query_text | string | Full BM25 query | Python | automatic | yes | retrieval |
| query_token_count | int | Query tokens | Python | automatic | no | retrieval |
| retrieval_method | string | `bm25_okapi` | Python | automatic | yes | rank-bm25 |
| retrieval_version | string | `"1.0"` | Python | automatic | yes | retrieval |
| candidate_count | int | Usually 5 | Python | automatic | yes | retrieval |
| all_scores_zero | bool | Degenerate scores flag | Python | automatic | yes | retrieval |
| top_bm25_score | float | Best candidate score | Python | automatic | yes | retrieval |
| candidates | object[] | Ranked competencies | competencies + BM25 | automatic | yes | retrieval |
| candidates[].rank | int | 1 = best | Python | automatic | yes | retrieval |
| candidates[].idnumber | string | Competency ID | competencies.jsonl | automatic | yes | catalogue |
| candidates[].bm25_score | float | Okapi BM25 | Python | automatic | yes | retrieval |
| candidates[].shortname / depth / parent_idnumber / competency_id | mixed | Competency metadata | competencies.jsonl | automatic | yes | copy |

---

## `data/interim/llm_tasks.jsonl`

Constrained Gemini prompts. Candidate space is the BM25 Top-5.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| task_id | string | `alignment:{fragment_id}` | Python | automatic | yes | `scripts/07_build_llm_tasks.py` |
| task_version | string | `"1.0"` | Python | automatic | yes | llm_tasks |
| fragment_id / resource_id / fragment_text / course / activity / title | mixed | Copied context | BM25 + fragments | automatic | yes | copy |
| allowed_idnumbers | string[] | The five candidate IDs | BM25 | automatic | yes | retrieval |
| candidates | object[] | Candidate metadata + scores | BM25 + competencies | automatic | yes | copy |
| instructions | object | max 3, abstention, exact evidence | Python | automatic | yes | llm_tasks |
| output_contract | object | Required JSON shape | Python | automatic | yes | llm_tasks |
| prompt | string | Full model prompt | Python | automatic | yes | llm_tasks |

---

## `data/interim/gemini_validated.jsonl`

Locally validated constrained Gemini responses. Current coverage is incomplete (23/35). Do not overwrite valid rows.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| fragment_id | string | Predicted fragment | Gemini + validator | automatic | yes | `scripts/10_run_gemini_alignments.py` |
| task_id | string | Matching LLM task | llm_tasks | automatic | yes | copy |
| model_name | string | e.g. `gemini-3.5-flash` | API / env | automatic | yes | Gemini |
| model_provider | string | Provider label | Python | automatic | yes | gemini_alignment |
| valid | bool | Passed local schema + evidence checks | Python validator | automatic | yes | llm_validation |
| validation_errors | list | Empty when valid | Python | automatic | yes | llm_validation |
| abstain | bool | No competency selected | Gemini | automatic | yes | model JSON |
| selected | object[] | Chosen competencies | Gemini | automatic | yes | model JSON |
| selected[].idnumber | string | Must be in BM25 Top-5 | Gemini | automatic | yes | constrained |
| selected[].evidence | string[] | Exact substrings of fragment_text | Gemini | automatic | yes if not abstain | constrained |
| selected[].reason | string | Short justification | Gemini | automatic | no | model |
| selected[].confidence | float | 0–1 | Gemini | automatic | no | model |
| overall_reason | string | Fragment-level reason | Gemini | automatic | no | model |

---

## `data/gold/manual_fragment_annotations.csv`

Independent human gold. Semantic cells must not be filled by software.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| fragment_id | string | Annotated fragment | fragments.jsonl | automatic | yes | template |
| resource_id / course_id / course_shortname / resource_type / activity_name / resource_title / fragment_text | mixed | Blinded context | fragments | automatic | yes | template |
| gold_competency_ids | string | Semicolon-separated GI IDs | researcher | human | yes unless `no_competency=true` | annotation helper |
| gold_evidence | string | Optional human quotes | researcher | human | no | helper |
| no_competency | string bool | Gold set empty | researcher | human | yes | helper |
| ambiguous | string bool | Hard case flag | researcher | human | yes | helper |
| ambiguity_reason | string | Why ambiguous | researcher | human | if ambiguous | helper |
| comment | string | Free note | researcher | human | no | helper |
| annotator | string | Who labelled | researcher | human | yes for final | helper |
| annotation_date | string | `YYYY-MM-DD` | researcher | human | yes for final | helper |

Companion files: `annotation_competency_catalogue.csv` (unranked 13 IDs), `manual_annotation_manifest.json`.

`data/gold/manual_moodle_links.csv` is **activity-level** Moodle mapping, not fragment gold. It is not used to build resource-level gold.

---

## `data/processed/resource_reference.jsonl`

Derived resource-level human reference. Built only from `manual_fragment_annotations.csv`. Not a second independent annotation exercise.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| resource_id | string | Page or Quiz question | resources.jsonl | automatic | yes | copy |
| course_id / course_shortname / resource_type / title | mixed | Resource identity | resources | automatic | yes | copy |
| fragment_ids | string[] | Gold fragments on this resource | fragment gold | automatic | yes | gold grouping |
| reference_competency_ids | string[] | Derived resource labels | fragment gold | derived | yes | Page union or question labels |
| reference_label_count | int | Unique derived labels | Python | automatic | yes | set size |
| reference_derivation | string | `union_of_human_reviewed_fragment_labels` (Page) or `human_reviewed_question_fragment_label` (Quiz question) | Python | automatic | yes | resource_type |

---

## `data/processed/resource_predictions.jsonl`

Fragment → resource aggregation. Final file is written only when Gemini is complete. Partial development artefacts use `resource_predictions.partial.jsonl`.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| resource_id | string | Page or Quiz question | resources.jsonl | automatic | yes | aggregation |
| course_id / course_shortname / resource_type / title / activity_name | mixed | Copied context | resources | automatic | yes | copy |
| fragment_ids | string[] | Fragments belonging to this resource | fragments | automatic | yes | aggregation |
| predicted_competencies | object[] | Deduplicated competency hits | Gemini fragments | automatic | yes | aggregation |
| predicted_competencies[].competency_id | string | GI id | Gemini | automatic | yes | selected.idnumber |
| predicted_competencies[].fragment_ids | string[] | Supporting fragments | Gemini | automatic | yes | aggregation |
| predicted_competencies[].evidence | string[] | Unique exact quotes | Gemini | automatic | yes | selected.evidence |
| predicted_competencies[].confidences | float[] | Per-fragment confidences | Gemini | automatic | no | selected.confidence |
| predicted_competencies[].max_confidence | float/null | Max of confidences | Python | automatic | no | aggregation |
| predicted_competencies[].mean_confidence | float/null | Mean of confidences | Python | automatic | no | aggregation |
| predicted_competencies[].support_count | int | Distinct supporting fragments | Python | automatic | yes | aggregation |

Manifest `resource_predictions_manifest.json` records completeness, missing fragment IDs, resource/competency counts, timestamp, source files, aggregation version, and `final` / `passed`.

---

## `data/processed/competency_resource_index.jsonl`

Inverse of resource predictions. Includes all 13 competencies even with zero matches.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| competency_id | string | GI id | competencies.jsonl | automatic | yes | inverse_index |
| shortname | string | Competency label | competencies | automatic | yes | copy |
| description | string | Description text | competencies | automatic | no | copy |
| parent_idnumber | string | Parent GI id | competencies | automatic | yes | hierarchy |
| depth | int | Hierarchy depth | competencies | automatic | yes | copy |
| match_count | int | Number of matching resources | Python | automatic | yes | inverse_index |
| resources | object[] | Matching resources | resource_predictions | automatic | yes | inversion |
| resources[].resource_id / course_id / course_shortname / resource_type / resource_title | mixed | Resource identity | resource_predictions | automatic | yes | copy |
| resources[].fragment_ids | string[] | Supporting fragments | aggregation | automatic | yes | copy |
| resources[].evidence | string[] | Quotes | aggregation | automatic | yes | copy |
| resources[].max_confidence / mean_confidence / support_count | mixed | Confidence stats | aggregation | automatic | no | copy |
| resources[].teacher_decision_status | string | `pending` unless a real review exists | teacher_reviews or default | mixed | yes | never invented |
| upstream_completeness | string | `complete` or `partial` | aggregation manifest | automatic | yes | propagated |
| inverse_index_version | string | `"1.0"` | Python | automatic | yes | inverse_index |

---

## `data/reviews/evidence_review.csv`

One row per predicted evidence quote. Pedagogical ratings start blank.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| fragment_id | string | Source fragment | Gemini | automatic | yes | script 17 |
| resource_id | string | Parent resource | fragments | automatic | yes | copy |
| competency_id | string | Predicted GI id | Gemini | automatic | yes | selected |
| competency_shortname | string | Label | competencies | automatic | no | copy |
| fragment_text | string | Full fragment | fragments | automatic | yes | copy |
| evidence_quote | string | Quoted span | Gemini | automatic | yes | selected.evidence |
| mechanically_valid | string bool | Quote is exact substring | Python | automatic | yes | evidence_review |
| evidence_start | string int | First-occurrence start offset of the quote | Python | automatic | no | derived; first `str.find` if the quote repeats |
| evidence_end | string int | Exclusive end offset | Python | automatic | no | derived; quote is not changed |
| offset_valid | string bool | Quote was found as a contiguous substring | Python | automatic | no | derived |
| pedagogical_rating | string | `0` / `1` / `2` or blank | researcher | human | yes for Gate 2 | never auto-filled |
| reviewer | string | Who rated | researcher | human | yes for Gate 2 | human |
| comment | string | Free note | researcher | human | no | human |
| review_date | string | `YYYY-MM-DD` | researcher | human | yes for Gate 2 | human; missing on legacy rows until rated |

Rating meanings: `0` does not justify, `1` partial/ambiguous, `2` clearly supports.

---

## `data/reviews/corpus_teacher_reviews.csv` (frozen-corpus teacher decisions)

External teacher decisions about the **frozen research corpus**, written by
`app/pages/2_Teacher_Review.py` through `corpus_app.save_review`. One row per
reviewed (resource, competency) mapping; 34 are reviewable.

The file contains the column header and **zero genuine decisions**.
Rows marked `research_status=demo` (or `record_status=demo`) are test data.
They are not teacher or supervisor validation, and the summary ignores them.
A later genuine decision is written atomically, after a timestamped backup into
`data/reviews/corpus_teacher_review_backups/`. Re-deciding a mapping replaces
the earlier row rather than duplicating it.

**Why this path and not `teacher_reviews.csv`:** that name was already taken by
the runtime app's review log (below), which uses different columns and holds
real researcher decisions. The two are kept separate so neither overwrites the
other; both are hashed in the reproducibility manifest and both are read by
`scripts/28_summarize_teacher_reviews.py`.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| review_id | string | `{resource_id}|{competency_id}` | Python | automatic | yes | storage layer |
| resource_id | string | Reviewed resource | inverse index | automatic | yes | copy |
| competency_id | string | Reviewed competency | inverse index | automatic | yes | copy |
| fragment_ids | string | Semicolon-separated supports | aggregation | automatic | no | copy |
| decision | string | `accept` / `reject` / `modify` | teacher | human | yes for Gate 3 | never invented |
| modified_competency_ids | string | Replacement IDs if modify | teacher | human | if modify | human |
| comment | string | Free note | teacher | human | no | human |
| evidence_relevance | string | Optional 0/1/2 | teacher | human | no | human |
| reviewer | string | Who decided | teacher | human | yes for Gate 3 | human |
| review_date | string | `YYYY-MM-DD` | teacher | human | yes for Gate 3 | human |

`decision` also accepts `add`, for a competency the model never predicted for
that resource. An `add` row is counted separately and sits outside the
reviewed-percentage denominator.

A decision is refused if the resource or competency ID is unknown, the reviewer
is blank, the date is not `YYYY-MM-DD`, `modify` has no replacement,
replacements appear without `modify`, or `evidence_relevance` is not blank /
`0` / `1` / `2`.

---

## `data/reviews/teacher_reviews.csv` (runtime app review log — different schema)

Decisions recorded by the **separate runtime app** (`app.py` + `pages/`) about
ad-hoc analyses of arbitrary Moodle resources. It is **not** about the frozen
research corpus and is never merged into corpus teacher-validation rates.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| review_id | string | `{analysis}\|{resource}\|{fragment}\|{competency}\|{date}\|{reviewer}` | Python | automatic | yes | `persist_runtime_review` |
| analysis_id | string | Runtime analysis run | runtime_storage | automatic | yes | copy |
| runtime_resource_id | string | Ingested resource | runtime_storage | automatic | yes | copy |
| fragment_id | string | Fragment, may be blank | runtime | automatic | no | copy |
| competency_id | string | Reviewed competency | runtime | automatic | yes | copy |
| suggested_by_model | string bool | Model proposed it | runtime | automatic | yes | copy |
| original_prediction | string bool | In the original output | runtime | automatic | yes | copy |
| reconciled_prediction | string bool | Kept after the decision | Python | automatic | yes | derived |
| decision | string | `ACCEPT` / `REJECT` / `MODIFY` | reviewer | human | yes | never invented |
| replacement_competency_id | string | Replacement if MODIFY | reviewer | human | if modify | human |
| comment | string | Free note | reviewer | human | no | human |
| reviewer_name | string | Who decided | reviewer | human | yes | human |
| reviewer_role | string | `researcher` / `teacher` / `supervisor` | reviewer | human | yes | human; only teacher/supervisor count as validation |
| review_date | string | `YYYY-MM-DD` | Python | automatic | yes | UTC at write |
| backend | string | Model backend | runtime | automatic | no | copy |
| model | string | Model name | runtime | automatic | no | copy |

Currently 2 rows, both `reviewer_role=researcher` (Wail Ouaret, 2026-09-18).

---

## `data/studies/teacher_study_cases.csv` (evidence-usefulness pilot design)

The reproducible A/B design from `scripts/27_prepare_teacher_study.py`. Built
with a fixed seed; rerunning with the same seed reproduces it exactly.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| case_id | string | `{fragment_id}\|{competency_id}` | Python | automatic | yes | derived |
| condition | string | `A` evidence hidden initially · `B` evidence shown | Python | automatic | yes | seeded, balanced within stratum |
| stratum | string | `parent_child_redundancy` / `incorrect_prediction` / `correct_prediction` | error analysis | automatic | yes | first match wins |
| fragment_id | string | Source fragment | error analysis | automatic | yes | copy |
| resource_id / resource_type / course_shortname | string | Resource context | error analysis | automatic | yes | copy |
| competency_id / competency_shortname | string | Suggested competency | error analysis | automatic | yes | copy |
| fragment_text | string | Full fragment | evidence review | automatic | yes | copy |
| evidence_quote | string | The quote under test | evidence review | automatic | yes | copy |
| reference_competency_ids | string | Human reference labels | error analysis | automatic | yes | copy |
| predicted_competency_ids | string | All model labels for the fragment | error analysis | automatic | yes | copy |
| model_is_correct | string bool | Is this competency in the reference | Python | automatic | yes | derived |
| parent_child_redundancy | string bool | Fragment shows the redundancy pattern | error analysis | automatic | yes | copy |

`data/studies/teacher_study_manifest.json` records the seed, candidate and
sampled counts, and the condition / stratum / course / resource-type balance.

---

## `data/studies/teacher_study_responses.csv` (pilot responses)

Written by `app/pages/7_Evidence_Usefulness_Pilot.py`. **Does not exist until a
human responds**; no response is ever simulated.

| name | type | meaning | source | human/automatic | required | provenance |
|---|---|---|---|---|---|---|
| case_id | string | Case answered | design | automatic | yes | copy |
| condition | string | `A` or `B` | design | automatic | yes | copy |
| reviewer | string | Who answered | reviewer | human | yes | human |
| reviewer_role | string | `teacher` / `supervisor` / `researcher` | reviewer | human | yes | human; sets the study label |
| decision | string | `accept` / `reject` / `modify` | reviewer | human | yes | human |
| confidence | string int | `1`–`5` | reviewer | human | yes | human |
| evidence_shown | string bool | Evidence was visible when deciding | Python | automatic | yes | derived from condition + reveal |
| evidence_opened | string bool | Reviewer chose to reveal it (condition A) | Python | automatic | yes | recorded interaction |
| start_timestamp / end_timestamp | string | ISO-8601 UTC | Python | automatic | yes | page timer |
| elapsed_seconds | string float | `end − start` | Python | automatic | yes | derived |
| comment | string | Free note | reviewer | human | no | human |

---

## Moodle competency CSV (import, not a model output)

`data/processed/utc_gi_mvp_moodle.csv` is generated from UTC GI subset JSONL plus Moodle’s exported template.

Moodle columns present: Parent ID number, ID number, Short name, Description, Description format, Scale values, Scale configuration, Rule type (optional), Rule outcome (optional), Rule config (optional), Cross-referenced competency ID numbers, Exported ID (optional), Is framework, Taxonomy.

Parent ID numbers preserve GI_C1 / GI_C2 / GI_C3. After import, Moodle stores the framework in native competency tables. Python `competencies.jsonl` is the retrieval/LLM copy of that same 13-competency set.
