# Hosted browser checklist (Checkpoint E)

**Status: PENDING.** A person has not yet walked through the hosted screens. Do not mark this
checkpoint passed until Wail records the result of each row.

Site: https://srv1872740.hstgr.cloud/

Use the existing admin account and the existing teacher sandbox account. Do not use a student
account except for the denial row. Do not print passwords. Keep the mock alignment backend.
Do not call Gemini.

| # | Check | Expected |
|---|---|---|
| 1 | Open the URL and log in as the teacher sandbox | Moodle opens. No PHP or Python traceback. |
| 2 | Open the course **Competency Alignment Pilot** | The course opens. |
| 3 | Open **Competency Alignment** under **More** | The plugin dashboard opens. |
| 4 | Dashboard | The six sample Pages are listed. |
| 5 | **Suggest competencies** on one Page | The page shows queued, then running, then completed, without a second press. |
| 6 | Exact evidence | Quoted sentences from that Page, not a summary standing in for the quotation. |
| 7 | Hierarchy warnings | Shown only when a parent and child are both proposed. |
| 8 | No gold or reference label | Nothing says the suggestion is the correct or reference answer. |
| 9 | No raw JSON, and no Python or PHP traceback | The page is the teacher view. |
| 10 | ACCEPT | Saves, with a success message. |
| 11 | REJECT | Saves, with a success message. |
| 12 | MODIFY | The competency selector appears only after MODIFY is chosen. |
| 13 | Evidence usefulness | Starts unselected. Values are 0, 1 and 2. Empty is allowed. |
| 14 | Optional comment | Can be left empty or filled, then saved. |
| 15 | Final competency | On MODIFY, the saved decision shows the competency the teacher picked. |
| 16 | Error feedback | A failed save or a failed analysis shows Moodle's message, not a stack trace. |
| 17 | Narrow window (about 390 px wide) | The course menu, the table and the decision buttons stay usable. |
| 18 | Student account | The student cannot open the plugin actions. |
| 19 | Admin settings | The token field does not display the stored token. Top-K reads as fixed at 5. Write-back is clearly off. |

Record pass or fail for each row, and a note for any fail. Checkpoint E stays PENDING until that record exists.
