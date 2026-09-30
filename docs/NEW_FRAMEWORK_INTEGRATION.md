# Integrating a new competency framework

**Status:** the retrieval and model path is ID-agnostic.  
**Not true:** the published Precision/Recall/F1 numbers apply to any framework. They were measured on the 13-competency UTC GI subset and the 35-fragment human-reviewed reference.

A new framework needs its own reference sample before any performance claim.

---

## What the engine actually needs

From `competency_normalization.py` and `retrieval.build_competency_document`:

| Field | Role |
|---|---|
| internal numeric id (`competency_id`) | provenance; optional for a non-Moodle framework |
| `idnumber` | stable identifier the model must copy exactly |
| `shortname` | BM25 document and prompt label |
| `description_text` | BM25 document and prompt |
| `parent_idnumber` | hierarchy warnings and child-preference view |
| `framework_idnumber` | groups profiles; included in the BM25 document |
| aliases | **not a first-class field today** — if you have them, append them to `search_text` |

`graph_checks.build_hierarchy_index` walks `parent_idnumber`. It does not parse `GI_C*`.

`error_analysis.parent_of` **does** parse `GI_C1_2` into `GI_C1`. Do not use that helper for another naming scheme. Use the hierarchy index.

## Procedure

1. **Export** the framework (Moodle competency CSV, Canvas outcome export, or a spreadsheet). Keep the source file immutable.
2. **Map** each row to the fields above. Strip HTML from descriptions (`html_clean.html_to_text`).
3. **Reject duplicate** `idnumber` values.
4. **Check parents.** Every non-empty `parent_idnumber` must exist. Record missing parents; do not guess them.
5. **Check cycles.** `competency_normalization` already records `hierarchy_cycle` when a Moodle path loops. A new importer must do the same and refuse to build an index on a cycle.
6. **Keep aliases** in `search_text` or a future `aliases` list. Do not drop synonyms that teachers actually use.
7. **Keep multilingual names.** The current tokenizer keeps Unicode letters, so French and English tokens both survive. It does not translate. Store the language in metadata. Do not mix two languages in one profile without labelling them.
8. **Build the BM25 index** with `BM25CompetencyRetriever`. Index build reads every profile once. Query cost grows with the number of profiles because BM25 scores the full set (`BM25Okapi.get_scores`).
9. **Annotate a small sample** of real course fragments against this framework. The old 35-fragment file is not valid gold for the new IDs.
10. **Measure Recall@K** on that sample before calling a model.
11. **Choose K** from that Recall@K curve. K = 5 was enough for 13 competencies (Recall@5 = 0.9737 on that corpus). It is not a universal setting.
12. **Run the constrained model** only on the recorded Top-K, temperature 0, with the exact-substring validator.
13. **Freeze a new reference** and only then report precision, recall, and F1. Write metrics to a new file. Do not overwrite `reports/metrics/constrained_llm_metrics.json`.

## What must stay true

- Candidate IDs are stored with the task.
- A wrong label is attributed either to retrieval (gold absent from Top-K) or to the model (gold present but not selected).
- The validator does not depend on the vendor. Gemini, Ollama, and the mock backend all pass through `validate_alignment_response`.

## Settings that are still experiment-specific

| Setting | Where | Reuse impact |
|---|---|---|
| Top-K = 5 | `runtime_analysis.RETRIEVAL_TOP_K`, script 06 default | configuration; `retrieve()` already takes `top_k` |
| Max selections = 3 | runtime and task contract | configuration of the prompt, not of the framework size |
| 13 IDs | selected subset and some report wording | experimental scope, not a hard limit in `BM25CompetencyRetriever` |
| `validate_fragments` expects 20 resources and 12 quiz questions | `fragmentation.py` | harmless acceptance check for the frozen corpus; a real blocker if reused as a general validator |
| Two course IDs in `Settings` | `settings.py` | Moodle extraction only |
