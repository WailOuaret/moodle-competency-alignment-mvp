# Multi-resource live Gemini verification

status: development_live_verification

This is a development check of eight synthetic resources on the throwaway Moodle 5.2 site. It is not a research benchmark, not a teacher-study outcome, and not a replacement for the frozen Phase-0 results. Any comparison with the private development targets below is DEVELOPMENT DIAGNOSTIC ONLY.

date/time: 2026-10-05 02:10–02:12 Europe/London (01:10–01:12 UTC)

## Frozen configuration

Recorded before the first model call and left unchanged for all eight resources.

| Item | Value |
|---|---|
| Git commit | `c83e0a73e428808993b1a9f5fa6fe20ee0362a5f` |
| Branch | `feature/moodle-multiresource` |
| Plugin | 0.3.0 (`2026100403`) |
| Service commit | `edb64f221e946ebf6577b2ebf8503d003b08e270` |
| Moodle | 5.2.1+ (build 20260722), PHP 8.3.35, PostgreSQL 16.14 |
| Backend | gemini |
| Model | `gemini-3.5-flash` |
| Prompt | 1.0 |
| Schema | 1.0 |
| BM25 Top-K | 5 |
| Maximum suggestions | 3 |
| Write-back | OFF |
| UTC catalogue | `UTC_GI_MVP_2026`, 13 competencies, hash `sha256:2308a1b9d476fd636069ec435eba32fc91c825c7b75b7be27be97cc90fd88ab6` |
| File extractor | 1.0 (PDF, DOCX, PPTX, VTT). Quiz, Book, Assignment and Lesson use the plugin adapters and store no separate extractor version. |
| Study phase stored on each row | `development_live_verification` |

The throwaway site used the real 13-node UTC GI framework (`GI_C1`, `GI_C1_1`–`GI_C1_4`, `GI_C2`, `GI_C2_1`–`GI_C2_3`, `GI_C3`, `GI_C3_1`–`GI_C3_3`). Descriptions came from `data/processed/competencies.jsonl`. The synthetic TRAN/NET/NORM framework was not used.

Protected scientific files before the first call: 21/21 unchanged.

## Calls

Authorized: 8. Attempted: 8. Successful: 8. Technical failures: 0. Retries: 0.

Each resource produced one fragment, so each Moodle analysis made one model request. No resource was run again after the result was saved.

## Privacy

LIVE PAYLOAD PRIVACY: PASS

The outbound analysis body contained the teacher-authored resource text, title, course and activity provenance, the 13 competency records, and `top_k` / `max_suggestions`. It did not contain a student name, student email, student id, quiz attempt, student answer, grade, assignment submission, forum post, Lesson attempt, password, Moodle session, service token, or the Gemini key. The key was not in Moodle, not in the request JSON, not in the browser review pages, not in the service logs, and not in Git.

## Results

Private targets were compared only after each prediction had been stored. The private answer key was not uploaded, not sent, not shown on the review page, and not used to change the prompt or the competency descriptions.

Evidence quotes: 18. Exact: 18. Invalid: 0.

### Quiz

Resource `moodle:quiz:4:question:8`, question version 8. Analysis 37 at 2026-10-05T01:10:26Z, 13677 ms.

Top-5 before the call: `GI_C3_2`, `GI_C3`, `GI_C1`, `GI_C2`, `GI_C1_3`.

Expected: `GI_C3_2`. Predicted: `GI_C3_2`, `GI_C3`.

Strict: no. Diagnostic recovery: yes. Class: EXTRA_LABELS. The extra label is the parent.

Evidence, both exact, provenance “Quiz - Relational Databases and SQL Queries, question 1”:

- Relational database joins and transactions
- Relational keys, SQL joins, integrity constraints, and transactions

The second quotation is the teacher-authored correct option stored on the question. The student attempt was not sent. Hierarchy warning: yes (`GI_C3` with `GI_C3_2`). The review page showed “Hierarchy note”.

### PDF

File `01_text_layer_pdf_software_testing.pdf`, resource `moodle:file:32`. Analysis 38 at 2026-10-05T01:10:40Z, 16585 ms.

Top-5: `GI_C1_1`, `GI_C1`, `GI_C1_4`, `GI_C1_2`, `GI_C2_1`.

Expected: `GI_C1_2`. Predicted: `GI_C1_2`, `GI_C1_1`.

Strict: no. Diagnostic recovery: yes. Class: EXTRA_LABELS. The extra label is the sibling `GI_C1_1`, so no parent/child warning.

Evidence, both exact, filename plus Page 1:

- A reliable software release process depends on verification at several levels. Unit tests check small functions, integration tests check interactions between services, and acceptance tests confirm that requirements are satisfied.
- Continuous delivery keeps releases small, repeatable, and reversible. Monitoring and rollback plans reduce the risk of deployment failure.

### DOCX

File `02_docx_accessible_interface_design.docx`, resource `moodle:file:34`. Analysis 39 at 2026-10-05T01:10:57Z, 17099 ms.

Top-5: `GI_C1_2`, `GI_C3`, `GI_C1`, `GI_C2`, `GI_C3_2`. `GI_C1_3` was not a candidate.

Expected: `GI_C1_3`. Predicted: `GI_C1`.

Strict: no. Diagnostic recovery: no. Class: WRONG. The model returned the parent. This was not rerun.

Evidence, exact, filename `02_docx_accessible_interface_design.docx`, Section Scenario (no page number invented):

- A usable interface begins with an understanding of the people who will use it and the tasks they need to complete.

### PPTX

File `03_pptx_cloud_network_security.pptx`, resource `moodle:file:36`. Analysis 40 at 2026-10-05T01:11:15Z, 14573 ms.

Top-5: `GI_C2_2`, `GI_C3_2`, `GI_C3`, `GI_C1_4`, `GI_C1`. `GI_C2_3` was not a candidate.

Expected: `GI_C2_2` and/or `GI_C2_3`. Both concept families are intentionally present in the deck. Predicted: `GI_C2_2`, `GI_C1_4`.

Strict: no. Only `GI_C2_2` was recovered, so the special rule classifies this as PARTIAL. `GI_C1_4` is an extra label and is recorded. Speaker notes were not sent. No hierarchy warning.

Evidence, both exact:

- Slide 2: Applications often communicate across local networks, cloud services, and distributed components. Network design considers routing, latency, bandwidth, and service availability.
- Slide 3: Services can be scaled out during high demand and reduced when demand falls.

### VTT

File `05_video_transcript_ml_text.vtt`, resource `moodle:file:38`. The SRT was not sent. Analysis 41 at 2026-10-05T01:11:30Z, 14591 ms.

Top-5: `GI_C3_2`, `GI_C3`, `GI_C1`, `GI_C2`, `GI_C1_3`. `GI_C3_3` was not a candidate.

Expected: `GI_C3_3`. Predicted: `GI_C3`.

Strict: no. Diagnostic recovery: no. Class: WRONG. The model returned the parent. Caption text was sent; the video file was not.

Evidence, both exact:

- 00:00:01–00:00:09: Machine learning can classify and search text after words are converted into numerical features.
- 00:00:31–00:00:42: Responsible use also requires checking bias, documenting limitations, and treating the prediction as support for a human decision.

### Book

Chapter “Scalable and Fault-Tolerant Distributed Software”, resource `moodle:book:2:chapter:4`. Analysis 42 at 2026-10-05T01:11:45Z, 13013 ms.

Top-5: `GI_C1_4`, `GI_C2_3`, `GI_C1`, `GI_C1_2`, `GI_C2_1`.

Expected primary: `GI_C1_4`. `GI_C2_2` would have been a plausible secondary. Predicted: `GI_C1_4` only.

Primary target recovered: yes. Additional labels: none. Strict: yes. Class: EXACT. No hierarchy warning.

Evidence, both exact, chapter provenance:

- Distributed software is built from components that cooperate across machines.
- Scalability is improved by stateless services, load balancing, partitioning, caching, and monitored failover.

### Assignment

Resource `moodle:assign:3`, “Assignment - Human-Centred Prototype Review”. Analysis 43 at 2026-10-05T01:11:59Z, 13848 ms.

Top-5: `GI_C1_2`, `GI_C3`, `GI_C1`, `GI_C2`, `GI_C3_2`. `GI_C1_3` was not a candidate.

Expected: `GI_C1_3`. Predicted: `GI_C1`.

Strict: no. Diagnostic recovery: no. Class: WRONG. The payload was the teacher instructions. It did not contain a submission, a student identity, a grade, or feedback.

Evidence, both exact, activity provenance:

- evaluate a prototype interface for a campus service. They must identify usability problems, propose interface improvements, and justify their choices using user tasks, accessibility criteria, and feedback quality.
- how the design supports different users.

### Lesson

Resource `moodle:lesson:2:page:2`, “Cybersecurity Threats and Protection”. Analysis 44 at 2026-10-05T01:12:14Z, 12663 ms.

Top-5: `GI_C2_3`, `GI_C3`, `GI_C3_2`, `GI_C1`, `GI_C2`.

Expected: `GI_C2_3`. Predicted: `GI_C2_3`, `GI_C2`.

Strict: no. Diagnostic recovery: yes. Class: EXTRA_LABELS. The extra label is the parent. Hierarchy warning: yes (`GI_C2` with `GI_C2_3`). The page content was the teacher Lesson page. No Lesson attempt or score was sent.

Evidence, all exact, Lesson page provenance:

- A secure architecture identifies assets, threats, and likely attack paths before implementation.
- Authentication verifies identity, authorization limits what a user can do, and encryption protects sensitive communication.

## Hierarchy

HIERARCHY LIVE CASE: TRIGGERED

It occurred on the quiz (`GI_C3` + `GI_C3_2`) and the lesson (`GI_C2` + `GI_C2_3`). The quiz review page showed the hierarchy note. It was not forced on any other resource.

## Development diagnostic only

Single expected child recovered: quiz `GI_C3_2`, PDF `GI_C1_2`, book `GI_C1_4`, lesson `GI_C2_3`.

PPTX recovered `GI_C2_2` and missed `GI_C2_3` (partial), with extra `GI_C1_4`.

Missed the expected child: DOCX `GI_C1_3`, VTT `GI_C3_3`, assignment `GI_C1_3`. In each of those three, and for PPTX `GI_C2_3`, the expected child was outside the frozen Top-5, so the constrained pipeline could not select it. The prompt, schema, Top-K, and descriptions were not changed after these results.

## Browser

Quiz, PDF, DOCX, PPTX and VTT review pages were opened on the throwaway site with the development teacher account. No decision was saved.

Suggestions, evidence and provenance were visible. There was no mock-backend warning, no reference answer, and no toy TRAN/NET/NORM label. The replacement selector stayed hidden. Official write-back was shown as off.

## Boundaries

NO T001–T007 USED

HOSTED 0.2.0 PILOT NOT MODIFIED

The hosted pilot containers were not recreated. The hosted plugin release remained 0.2.0. Nothing was pushed.
