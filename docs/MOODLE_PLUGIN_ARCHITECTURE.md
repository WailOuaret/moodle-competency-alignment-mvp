# Moodle plugin architecture

Architecture of the Moodle integration of the competency-alignment engine:
a standard local plugin, `local_compalign` ("Competency Alignment Assistant"),
and a Python service that wraps the existing engine.

This document describes the design and records what exists. Anything not marked
**implemented** in the status table is design only.

## Status

Branch: `feature/moodle-plugin`, created from `public-clean-2026-09-30`.

| Part | Status |
|---|---|
| Frozen research experiment | Unchanged. The 21 protected artefacts are byte-identical to the base commit. |
| Python alignment service (`service/`) | **Implemented.** Tested with the mock backend and with parity tests against the frozen artefacts. The live Gemini and Ollama backends have not been exercised through it. |
| Moodle plugin (`moodle-plugin/compalign/`) | **Implemented as a prototype.** Service settings and connection check, Page analysis against the selected framework, response validation, teacher review, Privacy API. Not production-ready. |
| Review workflow | **Implemented.** ACCEPT, REJECT or MODIFY, evidence rating, comment, server-side review time, append-only revisions. |
| Write-back to Moodle competency links | **Not implemented.** No code path creates or changes a link. A decision records a write-back status of `disabled` or `none`. |
| Study export | Not started. |

No model has been called through the plugin. Every analysis made so far used the
service's mock backend, and the review page says so.

Tested Moodle version: 5.2.1+ (build 20260722, `$version` 2026042001.07), in the local
Docker sandbox with PHP 8.3 and PostgreSQL 16. No other Moodle version is claimed.

### How the plugin was checked

- Every PHP file passes `php -l` on the sandbox's PHP 8.3.
- Each page and flow was run in the sandbox: a script that starts Moodle and acts as a
  chosen user (teacher, student, administrator) requested analyses, opened the pages
  and submitted forms; Moodle's own task runner (`admin/cli/adhoc_task.php`) ran the
  queued analyses against the mock service and against a throw-away fake service that
  returns bad answers (invented quotations, unknown competencies, wrong Top-K, wrong
  resource, rejected token, model errors, invalid JSON).
- Checked this way: the decision rules, that REJECT, ACCEPT and MODIFY create no
  Moodle competency link and queue no write-back task, that the original suggestions
  are byte-identical after decisions, the privacy export and deletion, and the
  permission checks.
- **PHPUnit tests are written but have not been run.** They are in
  `moodle-plugin/compalign/tests/`. Moodle's PHPUnit dependencies are not installed in
  the sandbox, so no PHPUnit result exists. Their pure-logic cases were also run with a
  small stand-in assertion runner, which is not PHPUnit. The tests that need Moodle's
  database and generators have not been executed in any form.
- Not tested: a browser, other Moodle versions, a live model through the plugin, Behat.

## Design constraints

1. The research version stays as it is. Plugin and service code live in new
   directories and do not modify `src/moodle_competency/` or any frozen artefact.
2. The first version is a standard Moodle plugin in the course and resource
   interface. It does not use the Moodle AI subsystem or AI placement.
3. The Python engine is the backend. It is not ported to PHP.
4. Official competency links are created only after a teacher decision:
   the system proposes, the teacher accepts, rejects or modifies.
5. First teacher tests run in a separate Moodle sandbox, not on a production site.
6. The study records, per decision: the decision, how useful the evidence was,
   review time, the final competency, and an optional comment.

## Components

```text
┌───────────────────────── Moodle ─────────────────────────┐
│ course page → local_compalign → analysis job (ad-hoc task) │
│                                      │                     │
│  review UI ◀─ stored proposals ◀─────┤  review decisions   │
└───────────────────────────────────────┼─────────────────────┘
                     HTTPS + bearer token │ JSON
┌───────────────────────────────────────┼─────────────────────┐
│ service/  (FastAPI adapter, stateless)▼                     │
│   validate request → engine → map result to contract        │
│                         │                                   │
│ src/moodle_competency/  ▼                                   │
│   normalise → fragment → BM25 Top-5 → constrained model     │
│   selection → response + exact-evidence validation          │
│   → aggregation → hierarchy diagnostics                     │
└──────────────────────────────────────────────────────────────┘
```

**Moodle plugin.** Reads teacher-authored content and the competency catalogue
through Moodle APIs, queues an analysis, stores the proposals and the review
decisions, and is the only component that can write to Moodle. It holds the service
URL and token. It holds no model credentials.

**Python service.** Stateless. Validates the request, runs the engine, returns the
validated suggestions. It holds the model credentials. It has no access to Moodle
and no Moodle credentials.

## Service contract (schema 1.0)

Full field reference and error table: [`service/README.md`](../service/README.md).

- `GET /health` is open and returns a fixed three-field object.
- `POST /v1/analyses` takes one resource and one competency catalogue and returns the
  suggestions for that resource. It requires `Authorization: Bearer <token>`.
- The catalogue is supplied with every request. The service never completes it from
  the frozen experiment, so arbitrary valid catalogues work.
- A suggestion carries the competency `idnumber`, the model's confidence, the best
  BM25 rank, the number of supporting fragments, the exact evidence quotations and
  the hierarchy warnings.
- Every competency in a response is in the request catalogue and every quotation is
  an exact substring of its fragment. The engine validates this and the service
  re-checks it before replying.
- Prompts, raw model output and model reasoning are never returned.
- `confidence` is model metadata. It is not a calibrated probability and the plugin
  must not present it as a percentage chance of being correct.
- Failures use one error envelope with stable codes and a request id. A failed or
  partial analysis changes nothing in Moodle.

The resource contract follows [`PLATFORM_CONNECTOR_CONTRACT.md`](PLATFORM_CONNECTOR_CONTRACT.md):
plain text, a stable platform `resource_id`, paragraph breaks kept.

## Security boundary

| Asset | Held by |
|---|---|
| Model API keys | Python service only |
| Service URL and token | Moodle plugin (encrypted admin setting) and the service |
| Moodle database, users, grades, submissions | Moodle only |
| Reviews and decisions | Moodle only |

- The token is sent as a bearer token. The service compares it in constant time and
  refuses every request when none is configured.
- Remote deployments must use HTTPS. Plain HTTP is for the local sandbox.
- Moodle's HTTP client refuses private addresses and any port other than 80 and 443
  by default. A sandbox administrator must allow the service host and port in
  *Site administration → General → Security → HTTP security*. The plugin does not
  bypass this policy.
- The service receives no database credentials, and the Python service does not read
  the Moodle database.

## Review workflow

Where: the course navigation has a *Competency Alignment* entry. It opens the course
dashboard (`local/compalign/index.php?courseid=`), which lists every resource with its
analysis status and its current official competency links. A Page opens the review page
(`local/compalign/review.php?cmid=`). Only Pages can be analysed.

1. The teacher requests suggestions for a Page. This is a POST with a session key and
   needs `local/compalign:analyse`. The plugin stores an analysis record and queues an
   ad hoc task that runs as that teacher. The task reads the Page and the selected
   framework, calls the service, validates the answer and stores it. The page shows
   the status and refreshes itself every five seconds while the task is waiting or
   running (a `Refresh` header, no JavaScript). **Moodle's cron must run for the task to
   start.** Asking again while one is waiting reports the one in progress, and asking
   again for an identical completed analysis offers that one. *Reanalyse* always makes
   a new analysis; the earlier analysis and every decision on it are kept, and the page
   shows the latest.
2. For each proposed competency the teacher sees the competency, its description,
   the exact evidence, any hierarchy note, and the decision controls. Model
   confidence, BM25 rank and support count are in collapsed technical details. A
   reference label is never shown, because the plugin never holds one.
3. The teacher chooses ACCEPT, REJECT or MODIFY, optionally rates the evidence
   (0, 1 or 2, never pre-selected) and adds an optional comment of up to 1000
   characters. This is a POST with a session key and needs `local/compalign:review`.
   The reviewer is always the logged-in user: the form carries no user id and a
   submitted one is ignored.

| Decision | Final competency | Write-back status stored in this release |
|---|---|---|
| ACCEPT | the proposed competency | `disabled` |
| MODIFY | a different competency of the selected framework, chosen by the teacher | `disabled` |
| REJECT | none | `none` |

No decision creates or changes a Moodle competency link in this release.

Evidence usefulness: 0 = did not help justify the decision, 1 = partly useful,
2 = clearly supported the decision. Zero is a rating; leaving the rating empty is
stored as unknown.

**Review time** is measured on the server, not in the browser. The clock starts when the
review card is first shown to the teacher in their session and stops when the decision is
saved. If the start is unknown (the session ended), or the time is negative or longer than
four hours, it is stored as unknown (NULL) instead of a guess. After a save the clock
starts again the next time the card is shown, so a later revision measures its own review.

**The proposal is immutable.** A decision never overwrites the model's proposal.
Every save is appended as a new revision for that teacher and suggestion, so the original
proposal, the first decision and the latest decision can all be reconstructed.

**Stale analyses.** The analysis stores a hash of the text that was analysed and of the
framework that was sent. If the Page has been edited, or the framework changed or another
one was selected, since then, the review page warns that the evidence may no longer match
and suggests *Reanalyse*. The stored analysis is not changed.

## Write-back boundary (design only)

Nothing in this section is implemented. The plugin has no code that writes a competency
link. The design is kept so the boundary is agreed before any code exists.

Write-back is off by default and requires an explicit administrator setting.

- It needs both `local/compalign:writeback` and
  `moodle/competency:coursecompetencymanage`.
- It uses `\core_competency\api::add_competency_to_course_module()`. It never writes
  to a core competency table.
- A module link requires the competency to belong to the course. Moodle throws if it
  does not. If it does not, the plugin does not change the course silently: the
  teacher must confirm adding the competency to the course first.
- An existing link is never duplicated and never deleted. REJECT does not mean
  "remove this competency from Moodle", and MODIFY does not remove an existing link.
- If write-back fails, the review stays recorded and shows the failure.

Quiz questions stay individual analytical resources. Moodle stores competency links
at activity level, so question-level suggestions are kept in plugin tables for
evidence and evaluation, and only an approved competency is linked to the quiz
activity.

## Data stored by the plugin

Tables in the Moodle database, not CSV files. Proposals (`local_compalign_sugg`,
`local_compalign_evidence`) are written once, in one transaction with the analysis, so a
failed analysis leaves no partial result. Decisions (`local_compalign_review`) are
append-only.

| Table | Holds |
|---|---|
| `local_compalign_analysis` | Course, activity, resource id, hash of the analysed text, hash of the catalogue, framework, status, requester, backend, model, Top-K, completeness, abstention, the service's manifest and diagnostics, error code and message, timestamps |
| `local_compalign_sugg` | The original proposal: competency (Moodle id and ID number), confidence, BM25 rank, support count, order, hierarchy warnings |
| `local_compalign_evidence` | The exact quotations and their fragment ids |
| `local_compalign_review` | Reviewer, revision, decision, final competency (Moodle id and ID number), evidence usefulness, comment, when the card was first shown, review duration in seconds, write-back status |

The resource text itself is not stored, only its hash. The evidence quotations are.

## Privacy

Sent to the service: the teacher-authored resource title and text, the competency
catalogue, and structural names of the course, section and activity. Never sent:
student names, ids, emails, grades, submissions, messages or any learner data.

Stored by the plugin and attributable to a user: the reviewer's Moodle user id,
the decisions, the review durations and the comments. The plugin implements the
Moodle Privacy API for these. Study exports use a pseudonymous reviewer identifier
and do not contain teacher names.

Decisions made while testing the plugin are not study data and must be kept
separate from real teacher reviews.

## Supported resource types

| Type | Engine | Service | Plugin |
|---|---|---|---|
| Moodle Page | evaluated on the frozen corpus | accepted, tested with the mock backend | yes, run with the mock backend only |
| Quiz question | evaluated on the frozen corpus | not accepted yet | not yet |
| Assignment | adapter tested offline only | not accepted | not yet |
| Other types | not evaluated | not accepted | not yet |

A type is listed as supported only after it has been run end to end.

## Known limitations

- `top_k` is fixed at 5. The first plugin prototype uses Top-K=5, matching the evaluated
  research configuration. It is a constant inside the engine and Top-5 is the evaluated
  configuration. The service answers HTTP 422 to any other value. Another value would need
  a change to `runtime_analysis.py`, a file whose SHA-256 is recorded in
  `reports/reproducibility_manifest.json`.
- The service is synchronous per request, has no queue and no result store. An
  analysis with a live model can take minutes.
- The service is not production-hardened: there is no rate limit and no
  concurrency limit.
- Moodle runs in Docker. A host symlink to the plugin does not resolve inside the
  container, so the sandbox must bind-mount the plugin directory at
  `public/local/compalign`.
- Only Pages can be analysed. A forum, a quiz and every other type show "Resource type
  not supported in this prototype".
- Only one framework is read, the one an administrator selects in the plugin settings.
  Frameworks are never combined. A competency without an ID number or a description
  blocks the analysis, because the engine's connector contract requires both, and the
  page says which ones.
- Descriptions of competencies are converted to plain text by the plugin. Moodle's own
  converter writes bold text and headings in capitals, so it is not used.
- The mock backend is a placeholder: it picks the best BM25 candidate and quotes the
  first sentence. Its suggestions are not model output and the review page says so.
- There is no JavaScript. The page refreshes itself while an analysis waits, and the
  analysis only starts when Moodle's cron runs. The sandbox does not run cron by itself.
- A decision is final for its revision. A teacher cannot clear an evidence rating once
  one was saved; a new revision can only change it to another rating.
- The engine's suggestion-card code (`runtime_analysis.py`) recognises the warning types
  `parent_child_redundancy` and `granularity_mismatch`, while the hierarchy checks
  (`graph_checks.py`) emit `granularity_conflict`. The service does not use the engine's
  card text. It passes the structured `warning_type` through, so the plugin receives
  `granularity_conflict` correctly and has its own text for it. The engine is frozen and
  was not changed; this is recorded here, not fixed.
- Write-back, the study export and teacher validation have not been done. Nothing here
  is a claim that the plugin helps teachers: that has not been measured.
