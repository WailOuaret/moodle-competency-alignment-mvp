# Supervisor Q&A

Concise answers for the final meeting.

## Why BM25?

It is a transparent lexical ranker over the 13 competency profiles. It gives a stable Top-5 shortlist without another LLM call and without embedding infrastructure.

## Why Top-5?

Empirically Recall@5 = 0.9737 on this corpus, and the LLM is limited to at most three labels. Top-5 is wide enough to cover almost all reference labels and narrow enough to constrain hallucination.

## Why not let the LLM choose from all 13?

The frozen protocol is retrieve-then-generate. Opening all 13 would change the contract, increase overprediction risk, and break comparability with the 35-fragment experiment. RQ3.1 is about the role of that preselection, not an unconstrained leaderboard.

## Why Gemini?

Supervisor-approved constrained backend for the core experiment: `gemini-3.5-flash`, temperature 0, JSON schema, 35/35 valid.

## Why Ollama?

Optional local post-hoc comparison (`mistral:latest`). Checkpoints live under `data/experiments/`. Runtime UI can call it, but those outputs are never mixed into `constrained_llm_metrics.json`.

## Why exact evidence?

RQ2 needs a checkable span. The validator requires a contiguous substring. Teachers can see the sentence, not only a competency ID.

## Why fragment resources?

Pages mix several pedagogical units. Quiz questions stay one fragment. Author-created structure is preferred before length-based chunking.

## Why aggregate to resource level?

Teachers assign competencies to activities/resources, not to anonymous chunks. Page gold is the union of fragment labels; quiz questions remain independent.

## Why was resource precision lower?

Fragment overprediction, especially redundant parents, unions onto the Page. Resource micro precision 0.6765 vs fragment 0.7255. Recall stays high (0.9583) with one false negative inherited from the retrieval miss.

## Why did hierarchy reconciliation help?

Ten fragments predicted a parent and a direct child. The human-reviewed reference has **zero** positive labels for GI_C1, GI_C2 and GI_C3. Dropping those parents removes false positives and does not remove true reference labels in this corpus. That will not automatically generalize.

## Was the graph used by Gemini?

No. It was applied as a post-hoc deterministic hierarchy ablation.

## Why are hierarchy results much higher?

Because many false positives were unsupported broad parent labels, and the human reference contained no positive labels for the three broad parents in this corpus. Do not claim this will always generalize.

## Did you repair wrong predictions?

No. We distinguish:

- **prediction correction** — changing Gemini’s stored labels (not done)
- **post-hoc redundant-parent removal** — a separate view that drops a parent when a direct child is also present

Wrong child substitutions (for example GI_C1_1 instead of GI_C1_3) are not “fixed” by the graph rule.

## What is the known retrieval failure?

`quiz_question:1:4` / fragment `quiz_question:1:4#f001`. Reference **GI_C1_3** is missing from BM25 Top-5. Gemini predicted **GI_C1_1**. This is the only missed reference label; `llm_missed_gold_label = 0`.

## What remains?

Real teacher or supervisor validation in the Streamlit UI; larger-scale evaluation if the corpus grows; LTI as a future launch path. Native Moodle plugin remains deferred.
