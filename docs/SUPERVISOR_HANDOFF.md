# Moodle Competency Alignment — Supervisor Handoff

**Researcher:** Wail Ouaret  
**Supervisors:** Marie-Hélène Abel, Le Ngoc Luyen  
**Institution:** Université de Technologie de Compiègne — Heudiasyc (UMR 7253, CNRS)  
**Date:** 4 October 2026  
**Branch:** `feature/moodle-plugin`

This note describes the Moodle plugin and the private pilot that sit on top of the frozen research experiment. It does not replace the research reports.

## 1. Executive summary

The original MVP takes a learning resource, retrieves five competency candidates with BM25, asks a constrained model to select from that list, and keeps only selections that quote the resource exactly. A person then accepts, rejects, or changes the suggestion. Those measurements are frozen.

The new work puts that engine behind a normal Moodle course. A local plugin, `local_compalign`, talks to a small Python HTTP service. The service runs the same engine. Teachers review suggestions inside Moodle. Official competency links are not written.

A private Moodle site is running for this pilot. Six sample Pages were analysed once with Gemini. The technical checks passed. Seven teacher accounts exist and have not been invited. The teacher study has not started.

## 2. Why the plugin was added

The research interface was a Streamlit application over the frozen corpus. It showed that the pipeline could be inspected, but it was not the place where a teacher works. The plugin was added so a teacher can stay in a Moodle course, open a Page, and review a suggestion with the quotation beside it.

The direction came out of the supervision of the project: move from the research demonstration to a workflow a teacher can use in Moodle, without turning the model into the system of record.

## 3. Architecture

```text
Moodle course Page
  → local_compalign (PHP)
  → Python alignment API
  → BM25 Top-5
  → constrained Gemini selection
  → exact-quote validation
  → aggregation and hierarchy notes
  → Moodle teacher review
```

PHP owns the Moodle side: reading the Page, reading the competency framework the administrator selected, queuing the job, checking the service response, storing suggestions and decisions, and drawing the review form.

Python owns the analysis: normalisation, fragmentation, BM25, the constrained prompt, evidence checks, aggregation, and hierarchy warnings. That code remains in `src/moodle_competency`. The package `service/` is an adapter. It does not store reviews and it does not hold a second copy of the catalogue.

The model may select only from the five candidates. Each quotation must be an exact substring. A hierarchy note is information. It does not delete a suggestion.

## 4. Teacher workflow

1. Open the course **Competency Alignment Pilot**.
2. Open **More**, then **Competency Alignment**.
3. Choose a Page and press **Suggest competencies**.
4. Wait. The page refreshes. Pressing the button again does not start a second analysis of the same text.
5. Read each suggestion and the sentences quoted from the Page.
6. Choose **Accept**, **Reject**, or **Modify**. Modify shows the replacement list only after it is chosen.
7. Optionally rate how useful the quotation was: 0, 1, or 2. Nothing is pre-selected.
8. Optionally write a comment.
9. Save.

Write-back is off. The confirmation says that nothing was written to Moodle competency links. There is no gold label and no “correct answer” on the page.

## 5. What was implemented

- Plugin installation as `local_compalign`, release 0.2.0, maturity alpha, version `2026100401`.
- Extraction of a Moodle Page: title, description, and body as plain text, plus the course and section names. Learner fields are not read.
- The competency catalogue is the framework selected in Moodle, not a file baked into the request.
- An ad-hoc task runs the analysis. Moodle cron runs that task. The pilot cron container repeats the run.
- The plugin authenticates to the service with a bearer token stored encrypted in Moodle. The Gemini key stays in the service environment.
- Suggestions, quotations, and decisions are stored in plugin tables. Decisions are append-only revisions.
- Quotations that are not exact substrings are rejected by the service and are not shown.
- A parent and its child, both suggested, produce a hierarchy note on each card.
- Accept, Reject, and Modify, including a replacement competency that must be a different valid id from the same framework.
- Review duration is measured on the server from when the card was shown.
- Evidence usefulness is 0, 1, or 2, and may be left empty.
- Comments are optional plain text.
- A Privacy API provider is included.
- Capabilities separate viewing, analysing, and reviewing. A student in the pilot course cannot open the assistant.
- A repeated request for an unchanged Page, catalogue, Top-K, and suggestion limit reuses the stored analysis unless the teacher presses Reanalyse.
- Deployment scripts cover Compose, cron, backup, restore, and teacher accounts. A backup is checked by reloading the database dump into a scratch database.
- Seven accounts, T001–T007 (`teacher01`–`teacher07`), enrolled as editing teachers on the pilot course only.

## 6. Testing completed

| Check | Result |
|---|---|
| Python tests | 559 passed (4 October 2026) |
| Manual annotation validator | PASSED, 35/35 fragments |
| Python compile | `compileall` of `src`, `scripts`, `tests`, `app`, and `service` completed with no error |
| Streamlit UI smoke | 14 pages rendered |
| Plugin PHP syntax | 48 PHP files, 0 syntax errors, PHP 8.3.35 |
| Protected research files | 21/21 byte-identical to `public-clean-2026-09-30` |
| Live Gemini | 6 Pages, 0 failed calls, 24/24 quotations exact |
| Hosted browser walk-through | Recorded in `docs/LIVE_GEMINI_VERIFICATION.md` |

Moodle PHPUnit was run again on 4 October 2026 against this plugin on Moodle 5.2.1+ (build 20260722), PHP 8.3.35, PostgreSQL 16.14, and PHPUnit 11.5.55. The suite `local_compalign_testsuite` passed: 300 tests, 972 assertions. The run used a throwaway database, which was dropped afterwards. It did not use the pilot tables. The production image does not ship PHPUnit.

## 7. Live Gemini controlled verification

Backend `gemini`, model `gemini-3.5-flash` (both model environment variables were empty, so the service default was used), prompt `1.0`, schema `1.0`, Top-K 5, at most 3 suggestions. One call per Page. No retry. No setting was changed after the results.

| Resource | Expected | Returned | Result |
|---|---|---|---|
| Relational Databases and SQL Queries | GI_C3_2 | GI_C3_2 | EXACT |
| Testing and Continuous Delivery of Software | GI_C1_2 | GI_C1_2, GI_C1_1 | EXTRA_LABELS |
| Designing Usable and Accessible Interfaces | GI_C1_3 | GI_C1_3, GI_C1 | EXTRA_LABELS |
| Networks, Cloud Services and Security Basics | GI_C2_2, GI_C2_3 | GI_C2_2 | PARTIAL |
| Introduction to Machine Learning on Text | GI_C3_3 | GI_C3_3, GI_C3_2 | EXTRA_LABELS |
| Scalable and Fault-Tolerant Distributed Systems | GI_C1_4 | GI_C1_4 | EXACT |

Counts: 2 exact, 3 cases where the expected competency was returned together with an extra label, 1 partial multi-label result (one of the two expected competencies). None abstained. None failed technically.

On these six resources, 6 of the 7 expected labels were returned and 3 extra labels were added (6 true positives, 3 false positives, 1 false negative). Precision 6/9 and recall 6/7 are a **development diagnostic only**. They are not a new benchmark and they are not comparable to the frozen 35-fragment metrics.

The full quotations and hashes are in `docs/LIVE_GEMINI_VERIFICATION.md` and `reports/live_gemini_verification.json`, labelled `development_live_verification`.

## 8. Important model behaviour

The specific child competency was present on every page except the networks page, where GI_C2_2 was returned and GI_C2_3 was not. Extra labels still appear: a sibling on the testing page and on the machine-learning page, and the parent GI_C1 together with GI_C1_3 on the interfaces page. That parent-child pair is the one hierarchy warning in the six results. The other pages stored no hierarchy warning, which matches the rule that the note appears only when a parent and its child are both suggested.

Every stored quotation was an exact substring of the analysed page. The evidence mechanism held on this run.

This is why the teacher’s Accept / Reject / Modify step stays in the workflow. The model often finds the relevant competency and can still add another one, or miss one label on a page that supports two.

## 9. Security and privacy

- The request built for a Page contains the teacher-authored text, the course and section names, and the competency catalogue. It does not contain passwords, tokens, email addresses, grades, or a student id. That was checked on the database page before the first live call, and the same builder is used for every page.
- The service token is stored encrypted in Moodle and is not shown again in the admin form. The field on the hosted site is an empty password input.
- The Gemini key is only in the service environment. It was not present in the alignment log after the six calls.
- The alignment API and PostgreSQL are on a private Docker network. Moodle is published only through the reverse proxy.
- A student enrolled on the pilot course receives Moodle’s permission error on the assistant, not the suggestions.
- Write-back is off. After Accept, Reject, and Modify were saved during the browser check, the course still had no Moodle competency links. Those development rows were deleted after a verified backup. They are not teacher-study data.
- HTTPS is enabled for the pilot hostname.
- Backups include the database and Moodle data. The backup taken before the development rows were removed was reloaded into a scratch database by the backup script. The env file inside a backup is mode 600 and is not in Git.

No password, token, or API key is included in this document.

## 10. Hosted pilot

Hosted CA Pilot: https://srv1872740.hstgr.cloud/

The pilot is a separate Moodle installation on the same VPS as the academy site. The academy site stayed on HTTP 200 through the deployment and the live analyses. Moodle, cron, PostgreSQL, and the alignment service are separate containers. Cron is healthy and runs without a manual trigger. The alignment service is not bound to a public port.

Reboot of the VPS has not been tested. Do not reboot it as part of a casual check.

## 11. Teacher pilot accounts

Seven accounts are prepared and are not suspended:

| Participant | Username |
|---|---|
| T001 | teacher01 |
| T002 | teacher02 |
| T003 | teacher03 |
| T004 | teacher04 |
| T005 | teacher05 |
| T006 | teacher06 |
| T007 | teacher07 |

Each is an editing teacher on **Competency Alignment Pilot** only. The id number is the participant code. The email addresses end in `@pilot.invalid` and cannot receive mail.

Credentials are supplied separately through a private credential sheet. They are not in this repository.

T001 has already logged in once, on 4 October 2026, and no longer has the forced password change. The other six have never logged in and still must change the temporary password. Do not treat any login so far as teacher-study data.

Teachers have not been invited.

## 12. How supervisors can test it

1. Open https://srv1872740.hstgr.cloud/ .
2. Log in with the account from the private sheet.
3. Change the temporary password if Moodle asks.
4. Open **Competency Alignment Pilot**.
5. Open **More**, then **Competency Alignment**.
6. Select a Page.
7. Press **Suggest competencies** and wait until the suggestions appear.
8. Read the competency and the quotation. There is no reference answer.
9. Choose Accept, Reject, or Modify.
10. Optionally rate evidence usefulness.
11. Optionally write a comment.
12. Save.

Use a development account, or an account that will not be counted in the study, if the goal is only to look around. The seven study accounts should be used for the real review, not for repeated technical trials. Decisions saved on those accounts after the pilot starts are study data.

If the temporary password is rejected, the placeholder address cannot receive a reset mail. Contact Wail Ouaret.

## 13. Repository structure

| Path | Role |
|---|---|
| `src/moodle_competency/` | Alignment engine used by the research scripts and by the service |
| `service/` | FastAPI adapter: authentication, schemas, the call into the engine |
| `moodle-plugin/compalign/` | `local_compalign` source |
| `deploy/pilot/` | Compose file, Dockerfiles, nginx template, and operator scripts. Placeholders only |
| `docs/SUPERVISOR_HANDOFF.md` | This note |
| `docs/SUPERVISOR_SUMMARY.md` | Short version |
| `docs/LIVE_GEMINI_VERIFICATION.md` | The six live analyses |
| `docs/TEACHER_PILOT_GUIDE.md` | Instructions meant for teachers |
| `docs/PLUGIN_ADMIN_GUIDE.md` | Installing the plugin on a Moodle site |
| `docs/VPS_DEPLOYMENT_GUIDE.md` | Standing up the Docker pilot |
| `docs/PILOT_OPERATIONS_RUNBOOK.md` | Backups, accounts, and day-to-day operation |
| `data/` and `reports/metrics/` | Frozen corpus and frozen metrics |

## 14. How to run locally

Python service, from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-service.txt
pip install -e .
```

Copy `service/.env.example` to `.env` and set `ALIGNMENT_SERVICE_TOKEN`. For a live model, set `ALIGNMENT_BACKEND=gemini` and `GEMINI_API_KEY`. Leave the model name empty to use the default (`gemini-3.5-flash`). Then:

```bash
uvicorn service.main:app --host 127.0.0.1 --port 8001
```

`GET /health` does not call the model. The rest of the contract is in [service/README.md](../service/README.md).

The Moodle pilot stack is [deploy/pilot/README.md](../deploy/pilot/README.md) and [docs/VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md). It needs Docker. The plugin is copied into the Moodle image at build time.

The frozen Streamlit demo does not need those secrets:

```bash
streamlit run app/Home.py
```

## 15. Deployment on another Moodle

Installing the plugin ZIP is not the whole system. A Moodle administrator also needs the Python service running and reachable from Moodle.

1. Install `local_compalign` (the ZIP root is the folder `compalign`).
2. In Site administration → Plugins → Local plugins, set the service URL and the bearer token.
3. Select one competency framework. Every competency needs an id number and a description.
4. Leave official write-back off.
5. Run Moodle cron. An analysis does not start until cron runs it.
6. Teachers use their existing Moodle accounts. The pilot’s `teacher01`–`teacher07` accounts are only for this hosted site.

Top-K is fixed at 5. The service rejects any other value. Across a public network the service URL must be HTTPS. The pilot’s plain HTTP hop stays on a private Docker network inside one machine.

**PUBLIC DISTRIBUTION REQUIRES LICENSING/IP CONFIRMATION.** This repository does not authorise publication to the Moodle Plugins Directory.

## 16. Limitations

- The plugin analyses Pages. Forums and other modules are shown as unsupported. Quiz questions were part of the frozen experiment and are not yet accepted by the plugin.
- Official write-back is off and is not part of the first teacher study.
- The seven-teacher evaluation has not been done.
- The six-page live run is a development verification. It is not a replacement for the frozen metrics.
- No second LMS has been connected or measured.
- The repository has no root licence decision. Public release of the plugin is blocked until that is confirmed.
- The VPS has not been rebooted to prove that cron comes back by itself.
- One study account, T001, was logged into once before the study. That login is not study data.

## 17. Next steps

- Invite the seven teachers and run the pilot.
- Read their Accept, Reject, and Modify decisions, the evidence ratings, the comments, and the review times.
- Compare the final competency they kept with the suggestion. Do not show them the expected labels beforehand.
- Add Quiz support only after the Page pilot is understood.
- Design write-back later, still only after an explicit accept or modify.
- Consider other frameworks or sites only with a new evaluation. The frozen scores are for this 13-competency catalogue.

## 18. Reproducibility of the frozen experiment

The original measurements were not recomputed and were not mixed with the live pilot. Twenty-one protected files are byte-identical to `public-clean-2026-09-30`: the frozen corpus, fragments, and competency catalogue; the BM25 candidate lists and the exact model tasks; the frozen Gemini responses and the validated responses; the human reference and the Moodle link table; the evidence review and the earlier teacher reviews; and the published metric files under `reports/metrics/`.

`src/moodle_competency` was not edited to chase the six live Pages. Top-K is still 5. The prompt version is still 1.0.

## 19. Multi-resource extension

Pages were the first Moodle activity. Branch `feature/moodle-multiresource` (plugin release 0.3.0, version `2026100402`) keeps the same alignment engine and adds adapters. Each adapter turns one teacher-authored item into the resource the service already accepts. Quiz questions, text-layer PDFs, DOCX, PPTX, plain text, Markdown, VTT and SRT transcripts, Book chapters, assignment instructions, Lesson pages, and supported files inside a Folder are in that set. Forum posts, student submissions, URL fetching, scanned-PDF OCR and automatic transcription are not.

This branch is local. It has not been deployed to https://srv1872740.hstgr.cloud/. The Page pilot remains 0.2.0. No teacher has reviewed a quiz question, a document or a transcript with this plugin. Do not treat the new types as validated.

Python tests on this branch: 575 passed. Moodle PHPUnit was not run here: this environment has no Docker and the hosted pilot must not be used as the test site. The earlier Page-pilot PHPUnit result (300 tests, 972 assertions) belongs to release 0.2.0.

Quiz suggestions, if write-back is enabled later, can be attached only to the Quiz activity. Moodle does not store a competency on a question. Write-back stays off.

Study export is `local/compalign/export.php`, capability `local/compalign:viewallreviews`. It pseudonymises the teacher and can include the free-text comment.
