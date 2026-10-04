# Live Gemini verification

**Status:** `development_live_verification`  
**Date:** 2026-10-04  
**Scope:** six hosted pilot Pages, one live analysis each.

This record is development evaluation data. It is not a frozen research metric, and it is not a result from the teacher study. The expected competencies below are private. They must not be shown to teachers, and they are not a reference answer inside Moodle.

No prompt, competency description, BM25 setting, Top-K, fragmentation, aggregation, or hierarchy rule was changed after these results. No call was repeated because a label looked wrong. There was no technical failure and no retry.

## Technical readiness

| Check | Result |
|---|---|
| Backend | `gemini` |
| Model | `gemini-3.5-flash` (both model environment variables were empty, so the service default was used) |
| Prompt version | `1.0` |
| Schema version | `1.0` |
| Top-K / max suggestions | 5 / 3 |
| Plugin | `2026100401`, release `0.2.0`, repository `9713453` |
| Service code | `runtime_analysis.py`, `alignment_adapter.py`, and `schemas.py` in the running container match that repository commit |
| Plugin catalogue hash | `sha256:2308a1b9d476fd636069ec435eba32fc91c825c7b75b7be27be97cc90fd88ab6` |
| Service catalogue hash | `sha256:cb2e07b436426c0718ec7ba9ea43dd8081aa5ee32d39699605c2b525e7d6fd04` |
| Calls | 6 completed, 0 failed, 0 retries |
| Competency ids | 9 suggestions, all resolved to the Moodle competency with the same idnumber |
| Evidence | 24 stored quotes, 0 that are not an exact substring of the analysed page text |
| Secret in alignment logs | absent |
| Write-back | off |
| Requester | `devteacher` only |

The plugin hash and the service hash describe different inputs. The plugin hashes the Moodle catalogue JSON, and for a page it hashes the type, title, body, course name, section name, and activity name. The service hashes its own canonical catalogue, and for a page it hashes the engine's normalized text. Both hashes are stable across this run: every page shares the two catalogue hashes above. They are not expected to be equal.

Pages that already had a completed mock analysis were reanalysed (`force`), so the live call was not replaced by the stored mock result. Pages without an analysis used the normal suggest path. The earlier mock rows were left in place. The alignment log contains six `analysis completed` lines and no `analysis failed` line.

## Model behaviour

Labels describe this run. They are not a pass threshold.

| Page | Expected | Suggested | Label |
|---|---|---|---|
| Relational Databases and SQL Queries | GI_C3_2 | GI_C3_2 | EXACT |
| Testing and Continuous Delivery of Software | GI_C1_2 | GI_C1_2, GI_C1_1 | EXTRA_LABELS |
| Designing Usable and Accessible Interfaces | GI_C1_3 | GI_C1_3, GI_C1 | EXTRA_LABELS |
| Networks, Cloud Services and Security Basics | GI_C2_2 and GI_C2_3 | GI_C2_2 | PARTIAL |
| Introduction to Machine Learning on Text | GI_C3_3 | GI_C3_3, GI_C3_2 | EXTRA_LABELS |
| Scalable and Fault-Tolerant Distributed Systems | GI_C1_4 | GI_C1_4 | EXACT |

Counts: EXACT 2, PARTIAL 1, EXTRA_LABELS 3, WRONG 0, ABSTAINED 0, TECHNICAL_FAILURE 0.

`GI_C1_1` on the testing page and `GI_C3_2` on the machine-learning page are extra siblings. `GI_C1` on the interfaces page is the parent of `GI_C1_3`. On the networks page, `GI_C2_2` is present and `GI_C2_3` is absent; the stored quotes are about protocols, cloud, and edge or IoT, not a security sentence. On the distributed-systems page the primary competency is the only suggestion. `GI_C2_2` was not returned there, so there was no secondary label to judge.

## Hierarchy warning

One parent-child pair was returned: `GI_C1` with its child `GI_C1_3`, on Designing Usable and Accessible Interfaces. Both stored suggestions carry a `parent_child_redundancy` warning. The other five pages returned no parent-child pair and stored no hierarchy warning. The live warning case is **triggered** on that one page.

## Timing

| Page | Analysis | Queued | Completed | Service duration |
|---|---:|---|---|---:|
| Relational Databases and SQL Queries | 5 | 2026-10-04T19:22:02Z | 2026-10-04T19:22:11Z | 8442 ms |
| Testing and Continuous Delivery of Software | 6 | 2026-10-04T19:27:51Z | 2026-10-04T19:28:01Z | 8923 ms |
| Designing Usable and Accessible Interfaces | 7 | 2026-10-04T19:28:07Z | 2026-10-04T19:28:18Z | 10184 ms |
| Networks, Cloud Services and Security Basics | 8 | 2026-10-04T19:28:24Z | 2026-10-04T19:28:33Z | 8620 ms |
| Introduction to Machine Learning on Text | 9 | 2026-10-04T19:28:40Z | 2026-10-04T19:29:12Z | 31972 ms |
| Scalable and Fault-Tolerant Distributed Systems | 10 | 2026-10-04T19:29:20Z | 2026-10-04T19:29:29Z | 8954 ms |

The machine-readable copy, including every stored quote, is `reports/live_gemini_verification.json`.

## Hosted browser check

Recorded on 2026-10-04 against the hosted pilot, after the six live analyses were stored. The development teacher account was used for the review screens. The development student account was used only for the denial check. No teacher account was used. Reanalyse was not pressed, so this check did not start another model call.

| # | Check | Result |
|---|---|---|
| 1 | Teacher login | Pass. The dashboard opened with no traceback. |
| 2 | Pilot course | Pass. The course name is shown on the alignment pages. |
| 3 | Competency Alignment | Pass. The course dashboard lists the plugin. |
| 4 | Six pages | Pass. All six Pages are "Suggestions ready". The forum is shown as not supported. |
| 5 | Suggest, then queued, running, completed | The transition was observed in the database while cron ran the six analyses. The browser was opened afterwards and showed "Suggestions ready" for each page. The browser was not watched during the transition. |
| 6 | Exact evidence | Pass. The database page and the interfaces page show the stored sentences. |
| 7 | Hierarchy warning | Pass. The interfaces page shows the parent and child notes. The database page, which has one suggestion, shows none. |
| 8 | No reference answer | Pass. The pages do not call a suggestion correct, gold, or a reference label. |
| 9 | No raw JSON or traceback | Pass on the screens that were opened. |
| 10 | Accept | Pass. Saving Accept showed "Your decision was saved. Nothing was written to Moodle competency links." The stored decision reads Accepted. |
| 11 | Reject | Pass. The parent suggestion on the interfaces page saved as Rejected. |
| 12 | Replacement selector | Pass. With no decision selected, both replacement rows were `display: none`. After Modify was chosen on one card, that row became `display: flex` and the other stayed hidden. |
| 13 | Evidence usefulness | Pass. The radios start unselected. The values are 0, 1 and 2. Accept was saved with 2. Reject was saved with none selected. |
| 14 | Comment | Pass. Accept was saved with a short comment. Reject was saved with the comment empty. |
| 15 | Modify | Pass. The saved decision reads "Modified to GI_C1_2". Moodle competency links stayed empty, and the page still says official write-back is off. |
| 16 | Error feedback | Not separately exercised. The student denial is Moodle's permission message, not a stack trace. A failed analysis was not produced. |
| 17 | Narrow window | Pass at 390 px. The page did not grow wider than the viewport. The hierarchy note and the decision radios remained visible. |
| 18 | Student | Pass. The dashboard and a suggestion page both say the student does not have permission to view the assistant. |
| 19 | Admin settings | Pass. The token field is an empty password input. Top-K is described as fixed at 5. Official write-back is unchecked. |

These three saved decisions are development reviews. They are not teacher-study data.
