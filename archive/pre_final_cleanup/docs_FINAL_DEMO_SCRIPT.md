# Final demo script

Spoken English for a 5–10 minute supervisor walkthrough.

## 30-second motivation

Moodle already stores Pages, quizzes, and a competency framework, but teachers still map resources to competencies largely by hand. This internship asks whether we can suggest those mappings automatically, and whether showing the exact sentence that justified a suggestion helps a teacher check it.

## What we built

We kept two functions only. Function A: given a learning resource, suggest UTC GI competencies with evidence. Function B: given a competency, list the resources linked to it. We did not build a recommender, a learning path, or a Moodle PHP plugin.

## Corpus

The evaluation corpus is small and controlled: two test courses, 20 resources, 35 fragments, 13 competencies. I reviewed all 35 fragments myself. That file is a human-reviewed reference set, not independent blinded gold from scratch, and there is no second annotator.

## BM25

We do not send all 13 competencies to the model. For each fragment we retrieve five candidates with BM25. Recall at 5 is 0.974, so almost every reference label is in that shortlist. The model is then forbidden from leaving that shortlist. That is the candidate-preselection role in RQ3.1.

## Constrained LLM

Gemini Flash, temperature 0, at most three labels, abstention allowed, and every label must quote a contiguous substring of the fragment. All 35 responses were valid JSON under that contract. Fragment-level micro F1 is 0.8315, with very high recall and lower precision. The typical error is overprediction, often a broad parent plus a child.

## Why exact evidence

Mechanical checks can confirm that the quote really appears in the text. They cannot confirm that the quote pedagogically supports the competency. In this corpus every quote was an exact substring, but only 78.3 percent were judged clearly supportive. That distinction is the honest answer to “is the evidence correct?”

## Why hierarchy reconciliation

Gemini itself did not use the competency graph. After the fact we warn when a parent and a direct child are both selected, and we can show a child-preference copy that drops the parent. Recall stays the same; precision and exact-set match rise because the reference never used the three broad parents. That is a post-hoc ablation, not a repaired Gemini run.

## Resource to competencies

Teachers do not want fragment IDs. We union fragment labels onto Pages, and we keep each quiz question as its own resource. Resource-level F1 is 0.7931. Precision falls because parent overprediction accumulates across fragments.

## Competency to resources

The inverse page is not a second model. It reads the same suggestions and splits model suggestions from human-validated mappings. Unreviewed predictions are never called validated.

## Original versus post-hoc metrics

Please keep both numbers. Original Gemini fragment F1 0.8315. Post-hoc hierarchy F1 0.9367. If we only reported the second number we would overstate what Gemini did.

## Limitations

Small corpus, one institution, one framework, one researcher, no NONE fragments, text-only resources, and no teacher or supervisor review yet. Ollama was a post-hoc optional backend, not the core result.

## Next work

A short teacher or supervisor review of two to five resources in this UI; later, LTI launch from Moodle if you want the app inside a course. A native Moodle plugin stays deferred.
