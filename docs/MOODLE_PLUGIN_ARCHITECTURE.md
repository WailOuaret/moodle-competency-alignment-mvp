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
| Moodle plugin (`moodle-plugin/compalign/`) | Not started. Design below. |
| Review workflow, write-back, study export | Not started. Design below. |

Tested Moodle version: none yet. The target is the existing local sandbox,
Moodle 5.2.1+ (build 20260722, `$version` 2026042001.07). No other Moodle version
is claimed.

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

## Review workflow (design)

1. The teacher requests suggestions for a resource. The plugin stores an analysis
   record and queues a background task. The task calls the service and stores the
   result. The page shows the status and does not wait on a model call.
2. For each proposed competency the teacher sees the competency, its description,
   the exact evidence, any hierarchy warning, and the decision controls. Model
   confidence, BM25 rank and support count are available as collapsed technical
   details. A reference label is never shown before the decision.
3. The teacher chooses ACCEPT, REJECT or MODIFY, optionally rates the evidence
   (0, 1 or 2, never pre-selected) and adds an optional comment.

| Decision | Final competency | May be written to Moodle |
|---|---|---|
| ACCEPT | the proposed competency | yes |
| MODIFY | the competency the teacher selects | yes, that one only |
| REJECT | none | never |

Evidence usefulness: 0 = did not help justify the decision, 1 = partly useful,
2 = clearly supported the decision.

**Review time** is the time from the review card being displayed to the decision
being saved. The browser measures it; the server validates it against its own clock
and rejects or clamps negative or implausibly long values.

**The proposal is immutable.** A decision never overwrites the model's proposal.
Decisions are appended as revisions, so the original proposal, the first decision
time and the latest decision can all be reconstructed.

## Write-back boundary (design)

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

## Data stored by the plugin (design)

Tables in the Moodle database, not CSV files. Proposals (`local_compalign_sugg`,
`local_compalign_evidence`) are written once. Decisions (`local_compalign_review`)
are append-only.

| Table | Holds |
|---|---|
| `local_compalign_analysis` | Course, resource, content hash, catalogue hash, status, requester, timestamps, backend, model, Top-K, error code |
| `local_compalign_sugg` | The original proposal: competency, confidence, BM25 rank, support count, warnings |
| `local_compalign_evidence` | The exact quotations and their fragment ids |
| `local_compalign_review` | Decision, final competency, evidence usefulness, comment, review time, write-back status, revision |

Full resource text is not stored if it can be avoided.

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
| Moodle Page | evaluated on the frozen corpus | accepted, tested with the mock backend | not yet |
| Quiz question | evaluated on the frozen corpus | not accepted yet | not yet |
| Assignment | adapter tested offline only | not accepted | not yet |
| Other types | not evaluated | not accepted | not yet |

A type is listed as supported only after it has been run end to end.

## Known limitations

- `top_k` is fixed at 5. It is a constant inside the engine and Top-5 is the
  evaluated configuration. Another value would need a change to
  `runtime_analysis.py`, a file whose SHA-256 is recorded in
  `reports/reproducibility_manifest.json`.
- The service is synchronous per request, has no queue and no result store. An
  analysis with a live model can take minutes.
- A competency without a description is refused, because the engine's connector
  contract requires one.
- The service is not production-hardened: there is no rate limit and no
  concurrency limit.
- Moodle runs in Docker. A host symlink to the plugin does not resolve inside the
  container, so the sandbox must bind-mount the plugin directory at
  `public/local/compalign`.
