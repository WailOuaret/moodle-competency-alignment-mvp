# Alignment service

A small HTTP service that lets the Moodle plugin (`local_compalign`) use the
research alignment engine without reimplementing it.

The service is an adapter. Normalisation, fragmentation, BM25 retrieval,
constrained model selection, response and evidence validation, aggregation and
hierarchy diagnostics all run in `src/moodle_competency`, through
`runtime_analysis.analyze_runtime_resource`. This package validates the request,
calls the engine and maps the result onto a versioned JSON contract. It stores
nothing: reviews stay in Moodle.

```text
Moodle plugin ──HTTP/JSON──▶ service/ ──▶ analyze_runtime_resource ──▶ model backend
   (token)                  (adapter)      (research engine)           (Gemini / Ollama)
```

## Run it

From the repository root:

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-service.txt

# One-time: create a token and keep it in the git-ignored .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
#   add   ALIGNMENT_SERVICE_TOKEN=<that value>   to .env (see service/.env.example)

uvicorn service.main:app --host 0.0.0.0 --port 8001
curl http://localhost:8001/health
```

Without `ALIGNMENT_SERVICE_TOKEN` the service starts but refuses every request to
`/v1/*` (HTTP 503). To try the pipeline without calling a model, start it with the
mock backend:

```bash
ALIGNMENT_BACKEND=mock uvicorn service.main:app --host 0.0.0.0 --port 8001
```

Stop it with Ctrl+C. It keeps no state.

## Configuration

Read from the environment, and from the repository `.env` for variables that are
not already set. Only the variables below are taken from the file; Moodle
database credentials and `MOODLE_TOKEN`, which the research scripts keep in the
same file, are ignored on purpose.

| Variable | Default | Meaning |
|---|---|---|
| `ALIGNMENT_SERVICE_TOKEN` | none | Shared secret, at least 16 characters. Required for `/v1/*`. |
| `ALIGNMENT_BACKEND` | `gemini` | `gemini`, `ollama` or `mock`. |
| `ALIGNMENT_MODEL` | backend default | Model override. Otherwise `GEMINI_MODEL` / `OLLAMA_MODEL`. |
| `GEMINI_API_KEY`, `OLLAMA_HOST` | none | Provider settings, read by the engine. They never leave this host. |
| `ALIGNMENT_MAX_BODY_BYTES` | `2000000` | Larger request bodies are refused with 413. |
| `ALIGNMENT_ENABLE_DOCS` | off | Enables `/docs`, `/redoc` and `/openapi.json`. Off by default. |
| `ALIGNMENT_LOG_LEVEL` | `INFO` | Log level. |
| `ALIGNMENT_ENV_FILE` | repository `.env` | Alternative env file. |

The `mock` backend returns deterministic output and never calls a model. Results
carry `manifest.backend = "mock"` and must not be used as study data.

## Endpoints

### `GET /health`

No credentials. Returns exactly:

```json
{"status": "ok", "service": "moodle-competency-alignment", "api_version": "1"}
```

It exposes no configuration, paths or credentials.

### `POST /v1/analyses`

Requires `Authorization: Bearer <token>`. The token is checked before the body is
read, and compared in constant time.

Request (schema 1.0):

```json
{
  "schema_version": "1.0",
  "resource": {
    "resource_id": "moodle:page:42",
    "resource_type": "page",
    "course_id": "5",
    "course_module_id": "91",
    "title": "Software Development Lifecycle and Deployment",
    "text": "Plain text. Paragraphs are separated by a blank line.",
    "search_text": "optional; defaults to the title followed by the text"
  },
  "competencies": [
    {
      "idnumber": "GI_C1_1",
      "shortname": "…",
      "description_text": "…",
      "parent_idnumber": "GI_C1",
      "framework_idnumber": "UTC_GI",
      "framework_shortname": "optional, see below"
    }
  ],
  "config": {"top_k": 5, "max_suggestions": 3}
}
```

Rules:

- Unknown fields are rejected.
- `resource_id` is a stable platform id without whitespace. Fragment ids are
  `{resource_id}#f001`, `#f002`, …
- `text` must already be plain text. Keep blank lines between paragraphs: the
  fragmenter splits on them.
- The catalogue comes from the request. It is never completed from the frozen
  experiment files, and an empty catalogue is refused. It must belong to one
  framework, have unique `idnumber` values, a non-empty description for every
  competency, parents that exist in the catalogue, and no cycles.
- `framework_shortname` is optional but changes BM25 scores slightly, because the
  engine includes it in each competency profile. Send it to reproduce the
  retrieval of the frozen experiment.
- `resource.course_shortname`, `course_fullname`, `section_name` and
  `activity_name` are optional structural context. The frozen pipeline used them in
  the retrieval query and the prompt. `activity_name` defaults to `title`.
- `config.top_k` must be `5` or omitted. See [Known limitations](#known-limitations).
- `config.max_suggestions` is 1–10 (default 3). It only limits how many
  resource-level suggestions are returned; the engine's per-fragment limit of
  three selections is part of the evaluated prompt.
- `resource_type` must be `page`. Other types are refused until they have been
  exercised through the service.

Response `200`:

```json
{
  "schema_version": "1.0",
  "analysis_id": "an_…",
  "status": "completed",
  "resource_id": "moodle:page:42",
  "manifest": {
    "backend": "gemini", "model": "…", "prompt_version": "1.0",
    "top_k": 5, "max_selections_per_fragment": 3,
    "competency_catalogue_hash": "sha256:…", "resource_hash": "sha256:…",
    "fragment_count": 2, "completeness": "complete",
    "analysed_at": "2026-10-03T20:00:00+00:00", "duration_ms": 8120
  },
  "suggestions": [
    {
      "competency_idnumber": "GI_C1_1",
      "confidence": 0.87,
      "bm25_rank": 2,
      "support_count": 2,
      "evidence": [{"fragment_id": "moodle:page:42#f001", "quote": "exact source quotation"}],
      "warnings": [
        {"code": "parent_child_redundancy", "role": "child",
         "related_idnumber": "GI_C1", "message": "…"}
      ]
    }
  ],
  "abstained": false,
  "diagnostics": []
}
```

How to read it:

- Every `competency_idnumber` is in the request catalogue, and every `quote` is an
  exact substring of its fragment. The engine validates this, and the service
  checks it again before replying. A result that fails the check is withheld.
- `confidence` is the highest confidence the model reported over the supporting
  fragments. It is model metadata, not a calibrated probability, and should not be
  shown as a percentage chance of being correct.
- `bm25_rank` is the best retrieval rank over the supporting fragments.
- `warnings` come from the engine's hierarchy diagnostics. They never remove or
  rewrite a suggestion: a parent and its child are both returned, each with a
  warning that names the other.
- `completeness` is `partial` when at least one fragment's model response failed
  validation and was discarded. Each discarded fragment is listed in
  `diagnostics` (`fragment_response_invalid`).
- `abstained` is true when the model declined to select a competency for every
  fragment, so `suggestions` is empty.
- Other diagnostics: `retrieval_no_signal` (a fragment shares no vocabulary with
  any competency) and `suggestions_truncated` (`max_suggestions` removed some).
- The response never contains prompts, raw model output or model reasoning.

Suggestions are ordered by `support_count`, then `confidence`, then `bm25_rank`,
then `idnumber`, so the order is deterministic.

## Errors

Every error uses one envelope, never a stack trace, path, environment value or
request content. `request_id` matches the `X-Request-ID` response header and the
server log. A caller-supplied `X-Request-ID` (letters, digits, `.`, `_`, `-`, up
to 64 characters) is reused.

```json
{"schema_version": "1.0",
 "error": {"code": "invalid_competency_catalogue", "message": "…",
           "retryable": false, "request_id": "…",
           "details": [{"loc": "competencies", "message": "…"}]}}
```

| HTTP | `code` | Meaning |
|---|---|---|
| 401 | `auth_missing`, `auth_invalid` | No token, or one that was not accepted. |
| 503 | `service_not_configured` | No token is configured on the service. |
| 413 | `payload_too_large` | Body larger than `ALIGNMENT_MAX_BODY_BYTES`. |
| 422 | `invalid_request` | The body does not match the schema (`details` locate the fields). |
| 422 | `unsupported_schema_version`, `unsupported_resource_type`, `unsupported_config` | Valid JSON the service does not support. |
| 422 | `invalid_competency_catalogue`, `invalid_resource` | The catalogue or the resource is not usable. |
| 422 | `no_usable_fragments`, `engine_input_rejected` | The engine could not process the input. |
| 502 | `model_output_invalid` | No model response passed validation. Retryable. |
| 503 | `backend_unavailable` | The model backend cannot be used (no key, offline, quota). Retryable. |
| 500 | `analysis_failed`, `response_validation_failed`, `internal_error` | Service-side failure. The cause is in the server log. |
| 404, 405 | `not_found`, `method_not_allowed` | Unknown route or method. |

A failed analysis changes nothing: the service stores no state and never writes to
Moodle.

## Security notes

- `/v1/*` requires the bearer token and fails closed when none is configured.
  Authentication runs before the body is parsed.
- Provider secrets stay in this process. The Moodle plugin holds only the service
  URL and token.
- The service receives no Moodle database credentials and sends none: the plugin
  gives it the content it needs. Only the allow-listed variables above are read
  from `.env`.
- Validation errors report where a value is wrong, never the value.
- The engine runs in a throw-away directory. It does not write to `data/runtime`
  or to any frozen experiment file.
- Plain HTTP is acceptable only for the local sandbox. Any remote deployment must
  sit behind HTTPS.
- `Content-Length` is checked before the body is read. A chunked upload without a
  length is not limited by the service; put a reverse proxy with a body limit in
  front of any shared deployment.

## Connecting Moodle

Moodle runs in a Docker container, so `http://localhost:8001` inside Moodle is the
container, not this machine. From the container the service is expected at
`http://host.docker.internal:8001`. That name has **not been verified** on this
sandbox yet.

Moodle's HTTP client refuses private addresses and every port except 80 and 443
by default (Site administration → General → Security → HTTP security: *cURL
blocked hosts list* and *cURL allowed ports list*). For a sandbox the host and port
8001 must be allowed there. The plugin does not bypass this policy.

## Tests

```bash
python -m pytest tests/service -q
```

No test touches the network or a live model. A fixture refuses socket
connections, and model behaviour is supplied by `MockAlignmentBackend`. The tests
that read the frozen experiment files (`frozen_data`) only read them: they check
that a catalogue and a Page prepared by this service reproduce the frozen
fragments and the frozen BM25 top-5 scores exactly.

## Known limitations

- Only `page` resources are accepted. `quiz_question` is evaluated in the research
  experiment but has not been exercised through the service; other types have not
  been evaluated.
- `top_k` is fixed at 5. It is a constant inside the engine, and Top-5 is the
  evaluated configuration. Supporting another value needs a small change to
  `runtime_analysis.py`, which would also change a file whose SHA-256 is recorded
  in `reports/reproducibility_manifest.json`.
- A competency without a description is refused. The engine's connector contract
  requires one; the caller decides how to fill it.
- One request is one synchronous analysis and can take minutes with a live model
  (the Gemini client retries and waits out rate limits). The Moodle side is
  expected to call it from a background task.
- There is no queue, no concurrency limit and no result store.
- The live Gemini and Ollama backends have not been exercised through this service.
  Only the mock backend has.
