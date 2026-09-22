# Blinded fragment annotation guide

This guide is for the independent fragment-level gold corpus of the Moodle competency-alignment MVP. Annotate from the fragment text and the 13 UTC GI competency descriptions only.

## 1. Purpose

Create a human reference that says, for each pedagogical fragment, which UTC GI competencies the fragment actually supports. Later evaluation will compare BM25 and the constrained LLM against this corpus. The gold labels must therefore be independent of those systems.

## 2. Why the annotation is blinded

If you see BM25 ranks or Gemini selections while annotating, those outputs can bias your decisions. Read the fragment. Read the catalogue. Decide from the text.

## 3. Files to open

Use only:

- `data/gold/manual_fragment_annotations.csv`
- `data/gold/annotation_competency_catalogue.csv`
- this guide: `docs/ANNOTATION_GUIDE.md`

Open the CSV in a spreadsheet or a plain-text editor that preserves UTF-8 and does not rewrite the header.

## 4. Files you must not open while annotating

Do not open, search, or otherwise inspect:

- `data/interim/bm25_candidates.jsonl`
- `data/interim/llm_tasks.jsonl`
- `data/interim/gemini_responses.jsonl`
- `data/interim/gemini_validated.jsonl`

Also do not copy labels from `data/gold/manual_moodle_links.csv` onto fragments.

## 5. How to annotate one row

Work one fragment at a time.

1. Read `fragment_text`.
2. Read the 13 catalogue rows (`idnumber`, `shortname`, `description`, `hierarchy_path`).
3. Decide whether the fragment supports one competency, several, or none.
4. Fill the human fields for that row.
5. Leave source fields (`fragment_id` through `fragment_text`) unchanged.

Fill every row before running final validation.

Required human fields in the finished sheet:

- a decision: competency IDs **or** `no_competency=true`
- `ambiguous`: `true` or `false`
- `annotator`: your name, for example `Wail Ouaret`
- `annotation_date`: `YYYY-MM-DD`, for example `2026-09-18`

Boolean fields accept `true` / `false` (also `yes` / `no` or `1` / `0`). Do not leave them blank in the finished sheet.

## 6. Zero competencies

If the fragment does not support any of the 13 competencies:

```
gold_competency_ids=
no_competency=true
```

Do not leave both the ID field and `no_competency` blank. That is an incomplete decision.

## 7. One competency

```
gold_competency_ids=GI_C1_1
no_competency=false
```

Use the catalogue `idnumber`, not the shortname.

## 8. Multiple competencies

Separate IDs with a semicolon, with or without spaces:

```
gold_competency_ids=GI_C1_1;GI_C1_3
no_competency=false
```

Do not repeat the same ID. Prefer the most specific child competency that the fragment actually supports. Add the parent only if the fragment supports the parent as a whole, not merely one child.

## 9. Optional exact evidence

Evidence is optional. If you include it, copy a contiguous phrase from `fragment_text` with the same spelling, capitalization and punctuation. Store one or more quotes as a JSON array inside the CSV cell:

```
["design software", "user requirements"]
```

Do not paraphrase. Do not invent wording that is not in the fragment. An empty evidence cell is valid.

## 10. Ambiguity

If the decision is genuine but uncertain:

```
ambiguous=true
ambiguity_reason=The fragment could reasonably correspond to both GI_C2_1 and GI_C2_2.
```

`ambiguous=true` still needs a decision (`gold_competency_ids` or `no_competency=true`) plus a non-empty reason.

If the decision is clear:

```
ambiguous=false
ambiguity_reason=
```

## 11. Comments

Use `comment` for notes that are not part of the label, for example why you preferred a child over a parent. Comments are optional.

## 12. Fragment gold versus Moodle activity links

`manual_moodle_links.csv` records teacher/Moodle associations at Page or Quiz level. That is useful provenance. It is not this gold corpus.

This CSV records what **one fragment** supports. A Quiz is not automatically the same as each of its questions. A Page is not automatically the same as each of its chunks.

## 13. Do not copy activity labels onto fragments

A Page linked to `GI_C1_2` may still contain a fragment that never discusses software quality. Annotate that fragment as unsupported or as a different competency if the text warrants it. Copying the activity mapping would overstate coverage.

## 14. Check the blank template

After generation, and before you start:

```bash
python scripts/12_validate_manual_annotations.py --mode template
```

Expected: 35 annotation rows, 13 catalogue competencies, status `PASSED`.

## 15. Check the finished annotations

When every row has a decision:

```bash
python scripts/12_validate_manual_annotations.py --mode final
```

## 16. If final validation fails

Read the listed errors. Typical fixes:

- unknown ID: use a catalogue `idnumber`
- duplicate ID in one cell: keep it once
- `no_competency=true` with IDs: choose one option
- blank decision: add IDs or set `no_competency=true`
- `ambiguous=true` without a reason: write `ambiguity_reason`
- evidence rejected: paste an exact substring, in a JSON array
- date rejected: use `YYYY-MM-DD`
- missing annotator: fill `annotator`

Do not ask the validator, BM25, or Gemini to invent labels. Correct the row yourself, then re-run final validation.
