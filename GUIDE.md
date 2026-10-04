# Guide

Operational instructions for the Moodle resource-to-competency alignment MVP.
The short description of the project is in [README.md](README.md).

## 1. Purpose

The software proposes competency alignments for learning resources and keeps
the evidence for each proposal. A person decides whether the proposal stands.

It does not:

- create official Moodle competency links
- replace a teacher or a programme designer
- treat a model output as validated because it was produced

Suggestions stay in this application's files until a reviewer records a
decision. That decision is still not written back to Moodle.

The frozen research interface can be opened, and the published metrics can be
recalculated, without calling Gemini again. The historical responses are
already in `data/interim/`.

## 2. Requirements

Recorded development environment:

- Python 3.12.3
- Linux (the recorded machine was WSL2; WSL is not required)
- a virtual environment

Install the packages in `requirements.txt`. They include `rank-bm25`,
`streamlit`, `python-dotenv`, `beautifulsoup4`, `pypdf`, `google-genai`, and
`pytest`.

Docker is needed only if you want a local Moodle instance. It is not required
to run the frozen demo, the tests, or the offline evaluation.

## 3. Clone and install

```bash
git clone https://github.com/WailOuaret/moodle-competency-alignment-mvp.git
cd moodle-competency-alignment-mvp

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` installs the `moodle_competency` package from `src/`.
The test configuration also adds `src/` to `sys.path`, so pytest can run
after `pip install -r requirements.txt` alone.

Check the install:

```bash
python -c "import moodle_competency, streamlit; print('ok')"
```

## 4. Configuration

Copy the example file and edit the copy. Do not commit `.env`.

```bash
cp .env.example .env
```

Variables read by `src/moodle_competency/settings.py`:

| Variable | Used for |
|---|---|
| `MOODLE_BASE_URL` | Moodle site, without a trailing path to `server.php` |
| `MOODLE_TOKEN` | Web-service token. Required for live REST calls |
| `MOODLE_SERVICE_SHORTNAME` | External service shortname |
| `MOODLE_SW_COURSE_ID` | Numeric id of the software-engineering course |
| `MOODLE_DATA_COURSE_ID` | Numeric id of the data course |
| `MOODLE_SW_SHORTNAME` | Course shortname, `MVP-SW` in the frozen corpus |
| `MOODLE_DATA_SHORTNAME` | Course shortname, `MVP-DATA` in the frozen corpus |
| `COMPETENCY_FRAMEWORK_IDNUMBER` | Framework idnumber, `UTC_GI_MVP_2026` in the frozen corpus |
| `DATABASE_HOST` | PostgreSQL host for the quiz-text export |
| `DATABASE_PORT` | PostgreSQL port |
| `DATABASE_NAME` | Database name |
| `DATABASE_USER` | Database user |
| `DATABASE_PASSWORD` | Database password |

Variables read by the runtime model clients, not by `load_settings()`:

| Variable | Used for |
|---|---|
| `GEMINI_API_KEY` | Live Gemini calls |
| `GEMINI_MODEL` | Gemini model name. Default in code: `gemini-3.5-flash` |
| `OLLAMA_HOST` | Ollama server. Default: `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Ollama model. Default: `mistral:latest` |

Which run needs which values:

| Task | Configuration |
|---|---|
| Frozen demo and offline metrics | None of the secrets. Local JSONL and CSV files are enough |
| Live Moodle extraction | Moodle URL, token, service name, course ids, course shortnames, framework id |
| Quiz-question SQL export | Database variables, plus a Moodle database you are allowed to read |
| Gemini runtime analysis | `GEMINI_API_KEY` |
| Ollama runtime analysis | A running Ollama server. The host and model variables are optional |

Leave secrets empty in `.env.example`. Put real values only in `.env`.

## 5. Run the frozen research demo

```bash
source .venv/bin/activate
streamlit run app/Home.py
```

Open `http://localhost:8501`.

| Page | Purpose |
|---|---|
| Home | Browse the two courses and their frozen resources |
| Resource to Competencies | Open one resource and read the proposed competencies, evidence, and fragments |
| Teacher Review | Record accept, reject, or modify. For a genuine review, do not open the reference label before deciding |
| Competency to Resources | Inverse view: which resources were linked to one competency |
| Evidence Review | Read the quotations and the researcher's pedagogical ratings |
| Review Progress | Counts of genuine decisions. Demo rows are ignored. Current state: 0 / 34 |
| Experiment Results | Frozen BM25 and Gemini metrics |
| Evidence Usefulness Pilot | The 12-case study design. No responses are stored |
| Validated Coverage | Coverage of the catalogue by predictions and by the reference |

The runtime app is separate:

```bash
streamlit run app.py
```

It analyses a new resource. It does not write the frozen experiment files.

A genuine teacher or supervisor should see the model proposal, the quotation,
the hierarchy context, and the review controls. Do not show
`data/gold/manual_fragment_annotations.csv` before the decision.

## 6. Recommended demonstration resource

Course `MVP-SW`, resource `page:1`, title **Software Development Lifecycle and Deployment**.

On **Resource to Competencies**, inspect:

- the predicted competency and whether it is a parent or a child
- the BM25 rank of that competency
- the quotation and whether it occurs in the fragment
- any hierarchy warning
- which fragment the quotation came from

The known retrieval failure is `quiz_question:1:4`, fragment
`quiz_question:1:4#f001` (user-centred design). The reference label is
`GI_C1_3`. That identifier is not in the BM25 Top-5, so the constrained model
could not select it. The model selected `GI_C1_1` from the candidates it was
given. This is a retrieval miss, not a case of the model ignoring a candidate
that was on the list. `llm_missed_gold_label` on the frozen run is 0.

## 7. Run tests

```bash
source .venv/bin/activate
python scripts/12_validate_manual_annotations.py --mode final
python -m pytest -q
python -m compileall -q src scripts tests app
python scripts/ui_smoke_check.py
```

A successful run finishes without failures. The smoke check renders the
Streamlit pages with outbound network calls blocked. It does not click
through the review form and it does not write review decisions.

Do not treat a past test count as a permanent property of the project. The
count changes when tests are added.

## 8. Reproduce metrics offline

Frozen model responses live in `data/interim/gemini_responses.jsonl` and
`data/interim/gemini_validated.jsonl`. Candidate lists live in
`data/interim/bm25_candidates.jsonl`. The reference lives in
`data/gold/manual_fragment_annotations.csv`.

These commands reread those files:

```bash
python scripts/15_evaluate_bm25.py --dry-run
python scripts/16_evaluate_constrained_llm.py --dry-run
python -m pytest -q tests/test_core_result_regression.py tests/test_verify_frozen.py
```

`--dry-run` checks that the frozen inputs are complete and does not rewrite
`reports/metrics/`. Running scripts 15 or 16 without `--dry-run` rewrites the
published metric files. Do that only when you intend to regenerate them from
the same frozen inputs.

That is replay and evaluation. It is not a new model call.

`scripts/10_run_gemini_alignments.py` and
`scripts/25_run_unconstrained_gemini.py` contact Gemini. Do not run them if
you only want to reproduce the published numbers. Do not overwrite
`data/interim/gemini_validated.jsonl`, `data/interim/bm25_candidates.jsonl`,
or `reports/metrics/bm25_metrics.json` and
`reports/metrics/constrained_llm_metrics.json`.

`tests/test_core_result_regression.py` checks that the protected artefacts
still match their recorded hashes. `scripts/verify_frozen.py` is an older
whole-tree snapshot tool. Its snapshot is local and is not part of the public
file list, because that snapshot was taken before this cleanup.

## 9. Run scaling checks

```bash
python scaling_checks.py --project-root .
```

The script:

- does not call Gemini or Ollama
- does not contact Moodle
- does not modify frozen responses, the reference, the original BM25 file, or the published metric files
- writes `scaling_results.json` beside the script

It reports four offline checks:

1. Retrieval on the 35 MVP fragments with the frozen 13 competencies, then with the 22-competency UTC GI catalogue.
2. Retrieval on a local LBG fragment corpus, if that corpus is present under `data/source/competency-tagging/`. This repository does not redistribute that corpus.
3. Index and query timings for synthetic catalogues of size 22, 220, 2,200, and 22,000. Those copies are not a quality experiment. The prompt is built from Top-K candidates, so its length stays in the same range as the catalogue grows.
4. Post-hoc stop-word and alias variants on the LBG retrieval run.

Retrieval Recall@K is not final model precision, recall, or F1. No Gemini run
was executed on the LBG corpus, so there is no LBG teacher validation.

If `data/source/competency-tagging/` is absent, the LBG section cannot run.
Place a locally obtained copy there, or skip that check. Do not add that
corpus to this repository unless its licence allows redistribution.

## 10. Run with Moodle

On the Moodle site:

1. Enable web services.
2. Enable the REST protocol.
3. Create an external service. The research shortname is `moodle_competency_mvp`.
4. Add the functions the extractor calls. Start from read functions for courses, contents, and pages.
5. Authorise a service user and create a token for that user.
6. Grant only the capabilities those functions require.
7. Import or select the competency framework whose idnumber matches `COMPETENCY_FRAMEWORK_IDNUMBER`.
8. Put the URL, token, course ids, and shortnames in `.env`.

Then, from the repository root:

```bash
python scripts/01_extract_moodle_rest.py
python scripts/02_extract_moodle_sql.py
python scripts/03_normalize_resources.py
```

Script 01 reads Pages through REST. Script 02 reads quiz-question text from
PostgreSQL with `sql/export_quiz_questions.sql`. The SQL fallback exists
because the REST question payload in the research environment did not contain
the question text needed for alignment. It is a development limitation. It is
not a recommended production architecture. Use a database user that can only
read the question tables you need.

The frozen corpus is already in `data/processed/`. Re-running extraction
against another Moodle site produces a different corpus. Keep that output
separate from the frozen files if you still need the published numbers.

## 11. Local Moodle development environment

The recorded development machine used a Moodle tree and a Moodle Docker
checkout outside this repository, for example:

```text
~/moodle-dev/moodle
~/moodle-dev/moodle-docker
```

Those paths are specific to that machine. They are not repository paths, and
the Python package does not require them. Follow the upstream Moodle Docker
documentation if you need a local site. Point `MOODLE_BASE_URL` at whatever
host and port that site actually uses.

To develop the Moodle plugin on the `feature/moodle-plugin` branch against such
a site, see section 21.

## 12. Analyze a new resource

```bash
streamlit run app.py
```

The runtime path can analyse:

- text pasted into the form
- a `.txt` upload
- HTML
- a text-native PDF (embedded text, via `pypdf`)
- a Moodle resource already fetched into the runtime store

The assignment adapter (`src/moodle_competency/assignment_adapter.py`) maps an
assignment-shaped record onto the resource contract and can be fragmented with
the generic chunker. That path is tested offline. It was not part of the
frozen 20-resource evaluation, and it is not wired into scripts 01–03.

Not supported:

- a scanned PDF that has no embedded text
- audio
- video
- semantic extraction from slides

If no fragment is produced, the text was empty after normalisation or the
file had no embedded text.

## 13. Use a different competency framework

A normalised competency record uses:

| Field | Required |
|---|---|
| `idnumber` | yes |
| `shortname` | yes |
| `description_text` | yes |
| `parent_idnumber` | yes when the competency has a parent; empty for a root |
| `framework_idnumber` | yes for provenance |
| `search_text` | recommended; the retriever also reads the fields above |

Procedure:

1. Export the framework from Moodle or from the source catalogue.
2. Normalise rows with `scripts/04_normalize_competencies.py` or an equivalent mapping into the fields above.
3. Reject duplicate `idnumber` values.
4. Check that every `parent_idnumber` exists, and that a competency is not its own parent.
5. Detect cycles.
6. Keep aliases in the retrieval profile if the source has them. The frozen Moodle export did not store aliases.
7. Build a BM25 index with `BM25CompetencyRetriever`.
8. Annotate a sample of fragments against the new catalogue.
9. Measure Recall@K on that sample.
10. Choose K from that curve.
11. Run the constrained model only after K is chosen.
12. Write metrics to a new directory. Do not replace `reports/metrics/bm25_metrics.json` or `reports/metrics/constrained_llm_metrics.json`.

K = 5 is the setting used for the 13-competency reference, where Recall@5 was
0.9737. It is not a universal setting. Precision, recall, and F1 from the
frozen Gemini run do not transfer to another framework or another corpus.

## 14. Add a new Moodle resource type

Assignment is the worked example.

1. Fetch the assignment with the Moodle API you are allowed to call (`id` or `assignment_id`, `name`, intro HTML, activity HTML).
2. Pass the payload through `normalize_assignment` in `assignment_adapter.py`. The result has `resource_type=assignment` and must satisfy `validate_resource_record`.
3. Fragment it with `create_fragments`. An unknown type becomes a `resource_chunk`.
4. From there the existing retrieval, task builder, validator, aggregator, and review interface apply.

What is implemented and evaluated: Pages and quiz questions in the frozen corpus.

What is tested offline only: the assignment adapter and the resource contract.

What is not implemented: a live assignment extractor inside scripts 01–03, and write-back of the resulting links.

## 15. Connect another LMS

The core does not import Moodle types after the adapter. A connector must emit
resources with:

- `resource_id`
- `resource_type`
- `title`
- `text`

Optional fields: `search_text`, course identifiers, section name, activity
name, and other metadata. See
[docs/PLATFORM_CONNECTOR_CONTRACT.md](docs/PLATFORM_CONNECTOR_CONTRACT.md).

Canvas, as a design only:

```
Canvas API
  → Canvas connector
  → normalised resources
  → unchanged alignment core
```

`docs/CANVAS_INTEGRATION.md` describes that shape. There is no Canvas client
in this repository, and no Canvas course has been aligned. The same is true
for D2L, Open edX, and Blackboard. Do not quote the Moodle precision, recall,
or F1 as a cross-LMS result.

## 16. Human review workflow

On **Teacher Review** the stored decisions are:

| Decision | Meaning |
|---|---|
| ACCEPT | The proposed competency is kept |
| REJECT | The proposed competency is declined |
| MODIFY | The proposal is replaced by one or more other competency ids |
| ADD | A competency the model did not propose is recorded for that resource |

Review rows are written to `data/reviews/corpus_teacher_reviews.csv`.
They are not written into:

- the frozen Gemini responses
- the human-reviewed reference in `data/gold/`
- Moodle's competency link tables

`data/reviews/teacher_reviews.csv` belongs to the runtime app. It currently
holds two researcher decisions. Those are not teacher or supervisor validation
of the frozen corpus.

Rows with `research_status=demo`, or `record_status=demo`, are ignored by the
summary and by Review Progress. A synthetic example is in
`examples/corpus_review_example.csv` (`reviewer_001`). It is not a result.

The public corpus file has a header and no decisions. Progress is 0 / 34.
Status is `WAITING_FOR_HUMAN`. Acceptance, rejection, and modification rates
are null because there is no genuine denominator.

In a future production system, only a human ACCEPT or MODIFY would be allowed
to become an official LMS link. That write-back is not implemented.

## 17. Troubleshooting

**Port 8501 is busy.** Streamlit prints the command to use another port. For example:

```bash
streamlit run app/Home.py --server.port 8502
```

**The process starts but no browser opens.** Open the URL Streamlit prints,
usually `http://localhost:8501`.

**Missing environment variables.** `load_settings()` raises `ValueError` and
names the variable. Live extraction needs the Moodle variables in section 4.
The frozen demo does not.

**Gemini is unavailable.** The frozen demo does not need it. A runtime Gemini
analysis needs `GEMINI_API_KEY` and outbound network access. The UI smoke
check blocks the network on purpose.

**Ollama is unavailable.** Select another backend, or start Ollama and set
`OLLAMA_HOST` if it is not on `127.0.0.1:11434`.

**Moodle API is unavailable.** Check `MOODLE_BASE_URL`, the token, and that
the external service includes the function you called. The REST endpoint is
`{MOODLE_BASE_URL}/webservice/rest/server.php`.

**SQL extraction is unavailable.** Script 02 needs the database variables and
a readable Moodle database. Pages can still be extracted with script 01.

**No fragments produced.** The normalised `text` field is empty, or a PDF had
no embedded text. Scanned PDFs are not read.

**Unknown competency id.** The id is not in the loaded catalogue. MODIFY and
ADD only accept ids that exist.

**Invalid evidence substring.** The validator rejected a quotation that is not
an exact slice of the fragment. The model output is stored as invalid; it is
not silently repaired.

**Missing parent competency.** `parent_idnumber` does not match an `idnumber`
in the same catalogue, or a cycle was found. Fix the catalogue before
interpreting hierarchy warnings.

**A test fails.** Do not delete a frozen artefact to make the test pass. Read
the assertion. `tests/test_core_result_regression.py` compares hashes of the
frozen files.

## 18. Research reproducibility

External model APIs change. This project stores the response that was judged.

```
frozen model response
  + frozen human reference
  + recorded BM25 candidates
  → deterministic metric calculation
```

Normal reproduction does not generate a new response. Scripts 15 and 16, with
`--dry-run`, check that calculation without rewriting the published files.
`tests/test_core_result_regression.py` detects an accidental edit to the frozen
files.

Optional later runs (Ollama, unconstrained Gemini, hierarchy preference) are
under `data/experiments/` and are not merged into
`reports/metrics/constrained_llm_metrics.json`.

## 19. Safety and data handling

Do not send student submissions, names, grades, or other personal data to an
external model unless the institution has approved that data flow. The frozen
corpus is course material (pages and quiz questions), not a gradebook.

Use a Moodle token with the smallest capability set that can read the
resources you align. Do not commit `.env`.

A teacher decision should keep the reviewer, the date, the decision, and the
resource and competency identifiers. Do not overwrite the model prediction
when a human disagrees with it. Store the decision beside it.

## 20. Current limitations

- The frozen corpus is a controlled set of two courses.
- Frozen evaluation covers 20 resources and 35 fragments.
- The reference has a single annotator and no inter-annotator agreement.
- Abstention was not evaluated on genuine `NONE` fragments. The reference does not contain that case.
- Pages and quiz questions are the evaluated resource types.
- Quiz text uses a SQL fallback.
- Hierarchy numbers published beside the Gemini scores are a post-hoc diagnostic. The model did not receive the graph as an input.
- There is no production REST service, database, or queue. The service in `service/` is a development adapter with no queue and no result store.
- A Moodle plugin exists only as an alpha prototype on the `feature/moodle-plugin` branch, tested on one local Moodle 5.2 sandbox. It is not a released plugin. There is no LTI launch implementation.
- No second LMS has been connected or measured.
- Teacher and supervisor validation of the frozen mappings is `WAITING_FOR_HUMAN`: 0 reviewed of 34. Demo rows are not included in that count.

## 21. Moodle Plugin Development / Sandbox

**Status.** The Moodle plugin is under development on `feature/moodle-plugin`. It
has been installed and exercised only on one local Moodle 5.2 sandbox, with the
service's mock backend. A teacher can ask for suggestions for a Moodle Page and
accept, reject or modify each one; nothing is written to Moodle's competency links. It
is alpha software, has not been validated by teachers, and is not for production use.

### Where things are

| What | Where |
|---|---|
| Plugin source (component `local_compalign`) | `moodle-plugin/compalign/` |
| Python alignment service | `service/`, see `service/README.md` |
| Architecture and contract | `docs/MOODLE_PLUGIN_ARCHITECTURE.md` |
| Plugin location inside Moodle 5.2 | `public/local/compalign` |

Moodle 5.1 and later serve from a `public/` directory, so a plugin goes in
`public/local/`, not `local/`. The command-line scripts moved with the layout: they
are in `admin/cli/` at the Moodle root, not under `public/`.

### Link the plugin into the sandbox

The plugin source stays in this repository. Moodle Docker bind-mounts the Moodle
tree into the container, so a host symlink to this repository would dangle inside
the container. Mount the plugin directory instead, through Moodle Docker's
`local.yml` override. `bin/moodle-docker-compose` loads it automatically, and Moodle
Docker's own `.gitignore` excludes it. Create
`~/moodle-dev/moodle-docker/local.yml` (merge into an existing one, never overwrite):

```yaml
services:
  webserver:
    volumes:
      - "/home/<user>/projects/moodle_competency_mvp/moodle-plugin/compalign:/var/www/html/public/local/compalign"
```

**Back up first. In this setup `moodledata` is not on a volume.** `/var/www/moodledata`
lives in the web server container's writable layer, so recreating that container
deletes it: uploaded files, caches and the encryption key. The database is on a
volume and is not affected.

```bash
cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
STAMP=$(date +%Y%m%d-%H%M%S); mkdir -p ~/moodle-dev/backups
docker exec moodle_comp_mvp-db-1 pg_dump -U moodle --no-owner moodle > ~/moodle-dev/backups/moodle_$STAMP.sql
docker exec moodle_comp_mvp-webserver-1 tar -C /var/www -cpf - moodledata > ~/moodle-dev/backups/moodledata_$STAMP.tar
mkdir -p ~/moodle-dev/moodle/public/local/compalign    # the mount point, owned by you
```

Then validate, check what Compose would touch, recreate only the web server, and
restore the data:

```bash
bin/moodle-docker-compose config > /dev/null
bin/moodle-docker-compose --dry-run up -d --no-deps webserver    # must list only the webserver
bin/moodle-docker-compose up -d --no-deps webserver
docker exec -i moodle_comp_mvp-webserver-1 tar -C /var/www -xpf - < ~/moodle-dev/backups/moodledata_$STAMP.tar
bin/moodle-docker-compose exec -T webserver ls /var/www/html/public/local/compalign
```

Never run `docker compose down -v` on this sandbox: it removes the volumes,
including the database. Install the plugin, then clear the caches:

```bash
bin/moodle-docker-compose exec -T -u www-data webserver php /var/www/html/admin/cli/upgrade.php --non-interactive
bin/moodle-docker-compose exec -T -u www-data webserver php /var/www/html/admin/cli/purge_caches.php
```

You can also open `http://localhost:8000/admin`. Moodle enters maintenance mode
briefly during the install. The container names assume
`COMPOSE_PROJECT_NAME=moodle_comp_mvp` from `moodle-env.sh`.

### Start Moodle and the service

Docker Desktop must be running, with WSL integration enabled for the distribution.

```bash
cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
bin/moodle-docker-compose start
bin/moodle-docker-wait-for-db
bin/moodle-docker-compose ps
```

Moodle is at http://localhost:8000. In another terminal start the service. Use the
mock backend until a live model run has been authorised:

```bash
cd ~/projects/moodle_competency_mvp && source .venv/bin/activate
ALIGNMENT_BACKEND=mock uvicorn service.main:app --host 0.0.0.0 --port 8001
```

`ALIGNMENT_SERVICE_TOKEN` comes from the ignored `.env`. See `service/README.md`.

### Configure the plugin

Site administration → Plugins → Local plugins → Competency Alignment Assistant.

- **Alignment service URL:** `http://host.docker.internal:8001`. From inside the
  Moodle container this name reaches the machine that runs the service. Plain
  `http://` is accepted only for local development hosts.
- **Alignment service token:** the value of `ALIGNMENT_SERVICE_TOKEN`. It is stored
  encrypted and never shown again.
- **Competency framework:** the one framework the assistant reads. Choose a visible
  framework in which every competency has an ID number and a description. Frameworks
  are never combined. Until one is chosen, analyses are refused.
- **Maximum suggestions:** how many competencies may be proposed for one resource.
- **Top-K** is fixed at 5. The first plugin prototype uses Top-K=5, matching the
  evaluated research configuration, and the service refuses other values.
- **Official write-back** is off. It is not implemented in this release: the checkbox
  is reserved and has no effect.
- **Human review** is always required.

### SANDBOX ONLY: let Moodle reach the service

By default Moodle's HTTP client refuses private addresses and every port except 80
and 443, a defence against server-side request forgery. The plugin does not bypass
it. In this sandbox the service sits on a private address and port 8001, so two
settings under Site administration → General → Security → HTTP security were
changed, as narrowly as Moodle allows. The previous values and the restore commands
were saved beside the backups.

1. **cURL allowed ports list:** add `8001`, so the list is `443`, `80`, `8001`.
2. **cURL blocked hosts list:** inside the container `host.docker.internal` resolves
   to `192.168.65.254` (`getent ahosts host.docker.internal`). Moodle has no allow
   list, only a block list, so replace `192.168.0.0/16` with the 16 blocks that cover
   the same range except that one address:

```text
192.168.0.0/18     192.168.64.0/24    192.168.65.0/25    192.168.65.128/26
192.168.65.192/27  192.168.65.224/28  192.168.65.240/29  192.168.65.248/30
192.168.65.252/31  192.168.65.255/32  192.168.66.0/23    192.168.68.0/22
192.168.72.0/21    192.168.80.0/20    192.168.96.0/19    192.168.128.0/17
```

`python -c "import ipaddress as i; print(*i.ip_network('192.168.0.0/16').address_exclude(i.ip_network('192.168.65.254/32')), sep='\n')"`
prints them. The other entries (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`,
`localhost`, `169.254.169.254`, and so on) stay.

Do not remove `192.168.0.0/16` wholesale, and do not copy this to a production
site. Production should use HTTPS, a normal host name and port 443. If Docker
Desktop changes its host address the plugin reports "Blocked by Moodle": repeat the
lookup and adjust the carve-out.

**Restoring the original settings.** Do this only when local testing of the plugin is over,
because the plugin cannot reach the service without the exception. The values from before
the change are in `~/moodle-dev/backups/sandbox_http_security_before_compalign_20261003-220326.txt`.
From `~/moodle-dev/moodle-docker`, after `source ../moodle-env.sh`:

```bash
bin/moodle-docker-compose exec -u www-data webserver php /var/www/html/admin/cli/cfg.php \
  --name=curlsecurityblockedhosts --set='127.0.0.0/8
192.168.0.0/16
10.0.0.0/8
172.16.0.0/12
0.0.0.0
localhost
169.254.169.254
0000::1'
bin/moodle-docker-compose exec -u www-data webserver php /var/www/html/admin/cli/cfg.php \
  --name=curlsecurityallowedport --set='443
80'
```

Afterwards the connection page reports "Blocked by Moodle", which is the expected result.

### Test the connection

Open `http://localhost:8000/local/compalign/index.php` as an administrator. It is
also linked from the plugin settings page. The check runs on the server, so the
token never reaches the browser. The page shows one of: Connected, Unauthorized,
Service unavailable, Invalid response, Blocked by Moodle, or Not configured.

### Analyse a Page and review the suggestions

This works with the mock backend. Its suggestions are placeholders, not model output,
and the review page says so.

1. As an administrator, select the framework in the plugin settings (above) and check
   that the connection test says Connected.
2. As a teacher of the course, open **Competency Alignment** in the course navigation, or
   `http://localhost:8000/local/compalign/index.php?courseid=<course id>`. The dashboard
   lists every resource with its status and its current official competency links.
3. Open **View suggestions** for a Page and press **Suggest competencies**. The page
   says the analysis is queued. Forums, quizzes and other types are not supported yet.
4. **Run Moodle's background tasks.** The analysis starts when cron runs, and the sandbox
   does not run cron by itself. For development run Moodle's own cron script in a spare
   terminal. **Press Ctrl+C to stop it.**

   ```bash
   cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
   while true; do
     bin/moodle-docker-compose exec -T -u www-data webserver php /var/www/html/admin/cli/cron.php
     sleep 2
   done
   ```

   The script is `/var/www/html/admin/cli/cron.php` inside the container. Moodle 5.2 has no
   `public/admin/cli/cron.php`. Each run stays alive for about three minutes (Moodle's default
   keep-alive window) and keeps checking for new tasks: an analysis queued while cron was running
   finished 3 seconds later. **The very first run is slow**, about 4 minutes 30 seconds here: it
   runs about 90 overdue scheduled tasks, several of which reach out over the internet, and two of
   them (the update check and the Moodle Apps portal) report a failure in this sandbox that does
   not involve the plugin. Ctrl+C stops the loop, but a run already in progress lives on in the
   container for up to three minutes; adding `--stop` to the `cron.php` command ends it at once. A
   lighter loop that only runs the queued analyses uses
   `php /var/www/html/admin/cli/adhoc_task.php --execute` with `sleep 5` instead.
   Moodle recommends cron at least once a minute. Before teachers outside the project use the
   sandbox, cron has to run automatically; that is not set up yet.

5. The page refreshes itself while the analysis waits. When it completes there is one
   card per suggested competency: the competency and its description, the exact
   evidence from the Page, any hierarchy note, and the decision form.
6. Choose **Accept**, **Reject** or **Modify** (Modify needs a different competency of the
   framework), optionally rate the evidence 0, 1 or 2, add a comment, and save. Nothing
   is pre-selected. Saving again adds a new revision; the earlier one is kept.

A failed analysis shows a short reason and a **Reanalyse** button; an administrator
finds the detail in the analysis record. If the Page or the framework changes after an
analysis, the review page warns that the evidence may be out of date.

Review time is measured on the server, from the moment a card is first shown in the
session to the moment the decision is saved. It is stored as unknown when that cannot be
known or lasts more than four hours.

**Test data is not study data.** Decisions made in the sandbox come from mock output and
must never be mixed with real teacher reviews. To empty the plugin's tables in this
sandbox only:

```bash
docker exec moodle_comp_mvp-db-1 psql -U moodle -d moodle -c \
  "TRUNCATE m_local_compalign_review, m_local_compalign_evidence, m_local_compalign_sugg, m_local_compalign_analysis RESTART IDENTITY;"
```

(`m_` is this sandbox's table prefix. Do not run this on a site that holds real reviews.)

### Run the tests

```bash
python scripts/12_validate_manual_annotations.py --mode final
python -m pytest -q
python -m compileall -q src scripts tests app service
python scripts/ui_smoke_check.py
```

The syntax of the plugin is checked with the container's PHP:

```bash
cd moodle-plugin/compalign
for f in $(find . -name '*.php'); do docker exec -i moodle_comp_mvp-webserver-1 php -l < "$f"; done
```

#### Moodle PHPUnit: the plugin's own tests

The tests are in `moodle-plugin/compalign/tests/`: thirteen test classes and three fixture
files. They were run for the first time on 4 October 2026 on Moodle 5.2.1+, PHP 8.3.32,
PostgreSQL 16 and PHPUnit 11.5.55: **295 tests, 955 assertions, no failures, errors, skips or
warnings.** The first run found four mistakes in the tests themselves, which were fixed
without weakening any assertion. Tests added afterwards for the form, the review page, the
dashboard and the settings found one redundant hidden field in the plugin, which was removed.
To run them (about a minute):

```bash
cd ~/moodle-dev/moodle-docker && source ../moodle-env.sh
docker exec -u root -w /var/www/html moodle_comp_mvp-webserver-1 \
  php vendor/bin/phpunit --testsuite local_compalign_testsuite --testdox
```

Run PHPUnit as root, as Moodle Docker's own documentation does. Moodle's bootstrap needs the
live data root writable and writes `phpunit.xml` into the Moodle root, and no single
unprivileged user in the container can do both. Hand the generated file back to yourself
afterwards: `docker exec -u root moodle_comp_mvp-webserver-1 chown 1000:1000 /var/www/html/phpunit.xml`.

**The tests do not use the sandbox's data.** They use tables with the prefix `t_` (the site uses
`m_`) and the data root `/var/www/phpunitdata` (the site uses `/var/www/moodledata`), in the same
PostgreSQL database. Moodle's PHPUnit bootstrap refuses to start if the two prefixes or the two
data roots are the same. This was checked row by row. Against a backup taken before PHPUnit was
installed, the site's tables differed only by last-access times, two log rows and some sessions
written by scripted page requests made before PHPUnit was initialised. Initialising PHPUnit and
running the suite changed nothing in the site's tables.

**One-time setup, done in this sandbox.** Skip it unless the sandbox is rebuilt.

1. Composer is not in the web container. Install it with its official installer, checking the
   installer against the hash that Composer publishes on a second host. `init.php` would
   otherwise download an unverified development snapshot of Composer:

   ```bash
   docker exec -u 1000:1000 -e HOME=/tmp/composer-home moodle_comp_mvp-webserver-1 sh -c '
     mkdir -p /tmp/composer-tool /tmp/composer-home && cd /tmp/composer-tool &&
     curl -4 -sS --retry 5 --retry-all-errors -o installer.php https://getcomposer.org/installer &&
     [ "$(curl -4 -sS --retry 5 --retry-all-errors https://composer.github.io/installer.sig)" = "$(php -r "echo hash_file(\"sha384\", \"installer.php\");")" ] &&
     php installer.php --install-dir=/tmp/composer-tool --filename=composer.phar && rm installer.php'
   ```

2. Install the development dependencies from Moodle's own `composer.lock`. **Never run
   `composer update`**: the lock file and `composer.json` must stay unchanged.

   ```bash
   docker exec -u 1000:1000 -e HOME=/tmp/composer-home -w /var/www/html moodle_comp_mvp-webserver-1 \
     php -d memory_limit=-1 /tmp/composer-tool/composer.phar install --no-interaction
   docker exec -u 1000:1000 moodle_comp_mvp-webserver-1 cp /tmp/composer-tool/composer.phar /var/www/html/composer.phar
   ```

   This creates `~/moodle-dev/moodle/vendor/` and the copy of `composer.phar`, both ignored by
   Moodle's `.gitignore`. Running as uid 1000 keeps the files yours.
3. Initialise PHPUnit. `--disable-composer` stops `init.php` from running Composer itself:

   ```bash
   docker exec -u root -w /var/www/html moodle_comp_mvp-webserver-1 \
     php public/admin/tool/phpunit/cli/init.php --disable-composer
   ```

   It installs a full test Moodle in the `t_` tables and writes `phpunit.xml`.
4. **After changing the plugin's database schema or version** (`db/install.xml`, `db/upgrade.php`,
   `version.php`) run step 3 again, so the test tables match. Adding or editing test files needs
   no new initialisation.

**Side effects to know about.** With `vendor/` present Moodle loads the libraries it bundles
(Guzzle, the PSR interfaces, Mustache, Slim, Monolog and others) from `vendor/` instead of
`public/lib/`, at the versions pinned in the lock file, which are the bundled ones. The site was
checked afterwards and works. To undo everything, drop the test site first, while `vendor/` still
exists, then delete the generated files. The site's own tables are not touched:

```bash
docker exec -u root -w /var/www/html moodle_comp_mvp-webserver-1 php public/admin/tool/phpunit/cli/util.php --drop
rm -rf ~/moodle-dev/moodle/vendor ~/moodle-dev/moodle/phpunit.xml ~/moodle-dev/moodle/composer.phar ~/moodle-dev/moodle/.phpunit.cache
```

### Browser verification

A person has to look at the plugin in a browser: the scripted checks cannot see Moodle's theme.
The exact checklist, with the commands to start the service and cron, is
[docs/MOODLE_PLUGIN_BROWSER_CHECKLIST.md](docs/MOODLE_PLUGIN_BROWSER_CHECKLIST.md). **Browser
verification is pending** until someone reports the result.

### Release blockers

**LICENSING / IP CONFIRMATION REQUIRED BEFORE PUBLIC PLUGIN DISTRIBUTION.** This is an
administrative blocker, not a code one. The plugin's PHP files carry GPL v3 or later headers,
which is Moodle's convention and is fine for development. The repository has no root LICENSE
file on purpose. Until the ownership and licence of the plugin are confirmed, do not publish
it to the Moodle Plugins Directory or to Packagist, do not build a public release archive, and do
not add a repository-wide licence. (A private package for the private pilot is allowed; see below.)

### Private teacher pilot (draft)

`deploy/pilot/` holds Docker Compose files and scripts for a private pilot of the plugin with seven
named teachers on a server: Moodle, the plugin, the alignment service, one database for Moodle only,
and the host's nginx for HTTPS. Start with [docs/VPS_DEPLOYMENT_GUIDE.md](docs/VPS_DEPLOYMENT_GUIDE.md);
the other documents are [docs/PILOT_OPERATIONS_RUNBOOK.md](docs/PILOT_OPERATIONS_RUNBOOK.md),
[docs/TEACHER_PILOT_GUIDE.md](docs/TEACHER_PILOT_GUIDE.md),
[docs/PLUGIN_ADMIN_GUIDE.md](docs/PLUGIN_ADMIN_GUIDE.md),
[docs/PLUGIN_PACKAGING_GUIDE.md](docs/PLUGIN_PACKAGING_GUIDE.md) and the gates in
[docs/TEACHER_PILOT_CHECKLIST.md](docs/TEACHER_PILOT_CHECKLIST.md). **Status: drafted and tried on a
development machine only.** It has not been run on a server, the browser checklist above is still
pending, no teacher has used it and no live model has been called through it. Write-back stays off.
Nothing in it is a secret, and nothing in it is a release.
