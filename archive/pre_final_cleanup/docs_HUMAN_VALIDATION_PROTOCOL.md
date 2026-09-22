# Human validation protocol

**Purpose:** a small, realistic teacher or supervisor review of the runtime MVP.  
**Not:** a controlled teacher study, and not a substitute for the frozen Gemini experiment.

Researcher reviews (including Wail Ouaret’s own ACCEPT/REJECT tests) **do not count**.

## Target

2–5 resources. Prefer:

- at least one Moodle **Page**
- at least one Moodle **Quiz question**
- optionally one pasted or uploaded resource

## Who may validate

| Role | Counts as teacher/supervisor validation? |
|---|---|
| teacher | yes |
| supervisor | yes |
| researcher | no |

If Wail demonstrates the UI, he must keep **researcher**. Supervisors use **supervisor**.

## Procedure

1. Launch `streamlit run app.py`.
2. Open **Analyze Resource**.
3. Select an existing Moodle resource (or paste text).
4. Choose **Gemini** (frozen experiment backend) unless the demo specifically compares Ollama.
5. Click **ANALYZE COMPETENCIES**.
6. For each suggested competency, inspect:
   - competency ID and name
   - evidence quote **in fragment context**
   - confidence
   - BM25 rank
   - post-processing hierarchy warning, if any
   - original vs hierarchy-reconciled labels
7. Choose **Review decision** explicitly (nothing is preselected):
   - ACCEPT
   - REJECT
   - MODIFY (replacement must be one of the 13 catalogue IDs)
8. Add an optional comment.
9. Set reviewer name and the correct role, then save.
10. Repeat on **Review Suggestions** if a stored analysis should be reviewed without rerunning the model.

Suggested starting resources:

- Page: `Knowledge Representation, Logic and Ontologies` (MVP-DATA)
- Quiz question: `SW_Q3_User_Centred_Design` (the known retrieval-failure case; useful for discussing BM25 limits)

## RQ2 add-on (optional)

For a few suggestions, also fill `data/templates/human_validation_form.csv` under both `without_evidence` and `with_evidence`. See `docs/RQ2_VALIDATION_GUIDE.md`.

## After the session

```bash
python scripts/34_summarize_human_validation.py
```

If no teacher/supervisor decisions exist, the script prints `HUMAN VALIDATION NOT YET PERFORMED` and exits successfully.
