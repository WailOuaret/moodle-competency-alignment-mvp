# Scaling and multi-LMS roadmap

This is a plan. Phases 1–5 are **not implemented**, except where a phase says a piece already exists.

Full audit and the 20 supervisor answers: `reports/SCALABILITY_AND_INTEGRATION_AUDIT.md`.

Labels used here:

- **IMPLEMENTED NOW** — in the repository and used by the MVP
- **TESTED OFFLINE** — unit-tested, not run on a live LMS or a large corpus
- **ARCHITECTURALLY SUPPORTED** — the current function signatures already allow it
- **PROPOSED** — design only

---

## Phase 0 — Current research MVP

**Goal:** a measured Moodle experiment plus a teacher-facing demo. **Status: IMPLEMENTED NOW.**

- External Python package and Streamlit app
- Moodle REST + read-only SQL for two courses
- 13 competencies, 20 resources, 35 fragments
- BM25 Top-5, constrained Gemini, exact evidence, post-hoc hierarchy view
- Optional Ollama and a mock backend
- CSV/JSONL storage
- LTI document only; native PHP plugin not built
- Teacher/supervisor validation still waiting

**Unchanged by later phases:** frozen Gemini files, the human-reviewed reference, and the published metrics.

**Done when:** the supervisor can reproduce the 35-fragment numbers offline. That criterion is already met.

## Phase 1 — Reusable service

**Goal:** run the same engine on many courses without editing Python constants.

**Code changes**

- Stop requiring exactly two course IDs in `Settings` for any path except the original extractor
- Call `validate_resource_record` at the connector boundary
- Add a small HTTP API: `POST /analyses`, `GET /analyses/{id}`, `POST /reviews`, `GET /resources/{id}/competencies`, `GET /competencies/{id}/resources`
- Store reviews, jobs, and model outputs in a database; keep JSONL as the research export
- Background worker with the resume behaviour the Gemini batch script already has for one file

**New modules:** `api/`, `jobs/`, `db/` — **PROPOSED**.  
**Already present:** `resource_contract.py` (**TESTED OFFLINE**), `AlignmentBackend`, checkpointed Gemini client.

**Risk:** mixing runtime rows into frozen metric files. Keep a `research_status` flag, as runtime ingestion already does.

**Tests:** contract tests (present), API tests with the mock backend, resume-after-failure on a fixture queue.

**Unchanged:** BM25, prompt contract, evidence validator, frozen artefacts.

**Done when:** a second course can be aligned from a JSONL export with no code edit, and a killed job resumes without new model calls for finished fragments.

## Phase 2 — Stronger retrieval

**Goal:** choose K from data, and reduce lexical misses, without replacing the frozen BM25 run.

| Version | Method | Status |
|---|---|---|
| v1 | BM25, K = 5 | **IMPLEMENTED NOW** for the experiment |
| v2 | stop-words and aliases | **TESTED OFFLINE** as a post-hoc LBG retrieval diagnostic in `scaling_checks.py`. Not the published system accuracy. |
| v3 | hybrid BM25 + dense retrieval | **PROPOSED** |

Every version must record the candidate list and whether a miss was retrieval or model.

**Risk:** publishing v2 numbers as if they were the Gemini experiment.

**Done when:** a new framework has a Recall@K table and a written K, stored beside the new reference, not inside `bm25_metrics.json`.

## Phase 3 — Deeper Moodle integration

**Goal:** teachers stay in Moodle; the engine stays Python.

Order inside this phase:

1. REST service (Phase 1) called by Moodle
2. Activity-level “suggest competencies” that returns suggestions only
3. Replace read-only SQL quiz export with a supported question API or export
4. Write back only ACCEPT / MODIFY

**Not in the repo:** PHP plugin, Moodle AI placement, LTI launch code.

**Risk:** writing model labels into `competency_modulecomp` before a teacher decides.

**Done when:** one Page and one question can be suggested and, after an explicit accept, stored once in Moodle without duplicates.

## Phase 4 — Second LMS

**Goal:** Canvas adapter. **Status: PROPOSED.** See `docs/CANVAS_INTEGRATION.md`.

**Unchanged:** alignment core.

**Done when:** fixture tests map Canvas JSON into the contract, and a separate small reference exists before any score is quoted. “Architecturally reusable” is not “validated on Canvas”.

## Phase 5 — Institutional scaling

**Goal:** many teachers, many universities, one service.

- Tenant id on every course, framework, job, and review
- Per-tenant framework version and model backend
- Queue, concurrency limit, and backoff (Gemini already retries 429 on a single process)
- HTTPS, least-privilege LMS tokens, no student submissions in the default path
- Audit log that keeps the original prediction

**Risk:** one global `.env` (`settings.py` loads a single Moodle token and two course IDs). That is a multi-tenant blocker until configuration is per request.

**Done when:** two tenants can run different frameworks and different backends without sharing review rows, and a load test states its corpus size instead of borrowing the 35-fragment scores.

---

## What I can demonstrate now

- The frozen Moodle metrics and the Streamlit demo
- A mock backend and an Ollama path that do not change Gemini files
- An assignment record that fragments through the existing generic branch (**TESTED OFFLINE**, not a Moodle experiment)
- Documents that separate the reusable engine from Moodle extraction
- Offline retrieval checks in `scaling_checks.py`: 13 versus 22 competencies on the MVP fragments, the local LBG 432-fragment corpus, computational timings up to 22,000 synthetic profiles, and post-hoc stop-word/alias diagnostics. No model calls. Numbers are in `scaling_results.json`.

## What I cannot demonstrate now

- Final Gemini precision, recall, F1, or teacher validation on the LBG corpus
- Thousands of real Moodle resources
- Live Canvas, D2L, Open edX, or Blackboard
- A production database or queue
- A Moodle plugin or LTI launch
- Automatic write-back

## Scalability status

| Status | Items |
|---|---|
| IMPLEMENTED | Moodle Pages / Quiz Questions pipeline; BM25; constrained Gemini; exact evidence; aggregation; hierarchy checks; Streamlit; Ollama/mock |
| TESTED OFFLINE | Resource contract; Assignment adapter; 22-competency retrieval scaling; LBG 432-fragment retrieval reuse; computational framework-size retrieval checks; stop-word/alias diagnostic retrieval variants |
| ARCHITECTURALLY SUPPORTED | Arbitrary normalized competency catalogue; parameterized Top-K; generic `resource_chunk` path; alternative model backend |
| PROPOSED | REST production service; database; queue; Moodle AI placement; native Moodle plugin; LTI launch; live Canvas connector; D2L/Open edX/Blackboard connectors; write-back |
