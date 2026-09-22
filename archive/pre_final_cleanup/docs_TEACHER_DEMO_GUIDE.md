# Teacher demo guide

Short supervisor walkthrough of the runtime MVP. This does **not** start a formal teacher study.

**Do not run live Gemini or Ollama until you explicitly want a live analysis.** The software was implemented and tested with mocks first.

## Launch

From the project root, with the virtualenv active:

```bash
streamlit run app.py
```

The app opens on **Analyze Resource** (`Learning Resource → Competencies`). Other pages are in the Streamlit sidebar:

1. Analyze Resource
2. Review Suggestions
3. Competency → Resources
4. Review History / Progress
5. Research Results

## Demo A — existing Moodle resource

1. Choose **Existing Moodle resource**.
2. Course: `MVP-SW`.
3. Resource: a Page such as the software-testing / lifecycle page, or a Quiz question.
4. Backend: **Gemini** if `GEMINI_API_KEY` is configured; otherwise the Gemini option is marked unavailable.
5. Click **ANALYZE COMPETENCIES**.
6. Watch the seven stages (extract → fragment → BM25 → align → validate → hierarchy → aggregate).
7. Inspect one competency card: id, name, confidence, supporting fragment, highlighted quote, BM25 ranks, and **Post-processing hierarchy check**.
8. Optionally enable the hierarchy-reconciled view. Original labels stay visible.

If you record a decision while testing yourself, set **Reviewer role = researcher**. That is a researcher review, not a teacher review.

## Demo B — paste text (no Moodle required)

1. Choose **Upload / paste resource**.
2. Title: `Verification notes`.
3. Paste:

   `Software verification includes testing software against specified requirements. User testing can also evaluate interface usability.`

4. Select an available backend.
5. Click **ANALYZE COMPETENCIES**.
6. Show evidence quotes in fragment context, not quotes alone.

## Demo C — inverse index

Open **Competency → Resources**, pick e.g. `GI_C1_2`, and show:

- MODEL SUGGESTIONS
- VALIDATED (empty until a human ACCEPT/MODIFY exists)

## Demo D — frozen research numbers

Open **Research Results**. Confirm original Gemini metrics and that hierarchy numbers are labelled **POST-HOC ABLATION**.

## Failure messages to expect

- Empty paste: rejected
- Image-only PDF: “No machine-readable text was found. OCR is outside the current MVP.”
- Ollama not running: “Ollama backend unavailable.” (no silent fallback)
- Gemini key missing: “Gemini backend unavailable.”

## After the demo

Teacher decisions remain **0** until a real teacher (role `teacher`) saves ACCEPT / REJECT / MODIFY. Do not describe researcher tests as teacher validation.
