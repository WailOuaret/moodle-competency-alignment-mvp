# Final supervisor demo (5–10 minutes)

Launch from the project root, virtualenv active:

```bash
streamlit run app.py
```

Do not present researcher ACCEPT/REJECT rows as teacher validation.

## Sequence

1. **Launch Streamlit.** Sidebar should list Analyze Resource, Review Suggestions, Competency → Resources, Review History / Progress, Research Results.
2. **Existing Moodle resource.** Input mode: Existing Moodle resource. Course `MVP-DATA`. Resource: Knowledge Representation, Logic and Ontologies.
3. **Analyze.** Backend Gemini (`gemini-3.5-flash`) if the key is configured. Click ANALYZE COMPETENCIES. A previous live run already exists; rerunning is optional.
4. **Explain the pipeline in one breath:** extract text → fragment by author structure → BM25 Top-5 of 13 GI competencies → constrained LLM (temperature 0, max 3, Top-5 only) → exact evidence substring check.
5. **Original vs hierarchy-reconciled.** Gemini often keeps GI_C3 and GI_C3_1 together. The reconciled view drops the broad parent. Label this **post-processing hierarchy check**, not Gemini graph reasoning.
6. **Review decision.** Show that ACCEPT / REJECT / MODIFY starts unselected. If a supervisor tries one decision, set role **supervisor**. If Wail clicks, role **researcher**.
7. **Competency → Resources.** Open GI_C3_1. Show MODEL SUGGESTIONS with backend/model (`Gemini — gemini-3.5-flash` vs `Ollama — mistral:latest`) kept on separate analyses. VALIDATED is empty of teacher mappings.
8. **Review History.** Aggregate counts plus the individual review table. Point to: researcher reviews are not teacher-study results.
9. **Research Results.** Read-only frozen metrics. Fragment Gemini F1 0.8315. Resource F1 0.7931. Hierarchy F1 values labelled POST-HOC ABLATION.
10. **Gemini vs Ollama demo case** (same Page): Gemini original GI_C3 + GI_C3_1; Ollama GI_C3_1. One resource is not a global ranking.
11. **Close with limits:** 35 fragments, 20 resources, 13 competencies, single-researcher reference, no NONE labels, teacher/supervisor validation still waiting, LTI future, native plugin deferred.

## If Gemini is unavailable during the meeting

Open a stored analysis on Review Suggestions, or use the Research Results page and the already-saved runtime manifests. Do not invent a live call.
