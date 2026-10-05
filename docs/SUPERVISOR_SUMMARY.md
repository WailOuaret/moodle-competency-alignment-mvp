# Moodle Competency Alignment — short summary

**Wail Ouaret** · supervisors Marie-Hélène Abel and Le Ngoc Luyen · UTC / Heudiasyc

The research MVP maps a learning resource to competencies from the UTC GI catalogue. BM25 proposes five candidates. A constrained model may select only from that list, and only with a quotation copied from the resource. A person decides.

That engine is now inside Moodle. The local plugin `local_compalign` (Competency Alignment Assistant, release 0.2.0) sends a course Page and the live competency framework to a Python service. The service returns suggestions. The teacher accepts, rejects, or replaces each one. Saving a decision does not write a Moodle competency link.

## Where it runs

Private pilot: https://srv1872740.hstgr.cloud/

It is a separate Moodle site on the same server as the academy site. The academy site was left in service. The alignment service and its database are not published on the host. Cron runs by itself. The model backend is Gemini (`gemini-3.5-flash`), Top-K is 5, and official write-back is off.

## What was checked

- Python: 559 tests passed.
- The 21 protected research files are byte-identical to the frozen experiment.
- Manual annotation check: 35/35 passed.
- Six controlled Pages were analysed once with the live model. None failed. All 24 stored quotations are exact substrings of the page text. No API key appeared in the service log.
- A browser walk-through on the hosted site covered login, the six pages, exact quotations, the hierarchy note, Accept, Reject, Modify, the hidden replacement list, a student who is refused access, and admin settings (empty token field, Top-K fixed at 5, write-back off).

On those six pages the expected competency was the only suggestion twice, was present together with an extra label three times, and was only partly present once (networks and security: GI_C2_2 returned, GI_C2_3 not returned). That is a development check, not a new benchmark.

## How to try it

1. Open https://srv1872740.hstgr.cloud/ .
2. Log in with the account sent separately. Do not share accounts.
3. Change the temporary password if Moodle asks.
4. Open the course **Competency Alignment Pilot**.
5. Choose **More**, then **Competency Alignment**.
6. Open a Page and press **Suggest competencies**. Wait. Do not press it again while it runs.
7. Read the competency and the quoted sentences. There is no reference answer on the page.
8. Choose Accept, Reject, or Modify. Rate the evidence 0, 1, or 2 if you want. A comment is optional.
9. Save. The page confirms that nothing was written to Moodle competency links.

## Feedback that would help

Whether the suggestion was usable, whether the quotation justified it, how long the decision took, and what was missing or misleading. Comments are the most useful part.

## Limits

The hosted pilot analyses Pages only. Quiz questions are not analysed there. Write-back is off. Seven teachers have accounts and have not been invited yet. The six-page model check is not a teacher study. A repository-wide licence is not decided, so the plugin is not published to the Moodle Plugins Directory.

## Two versions

**Hosted pilot.** Release 0.2.0 is Page-only and is what is deployed at https://srv1872740.hstgr.cloud/. The seven teachers have not used a later release.

**Repository latest implementation.** Release 0.3.0 (version `2026100403`) is the code on `feature/moodle-plugin`. It is not installed on the hosted teacher pilot. It supports quiz questions, PDF, DOCX, PPTX, plain text, Markdown, VTT and SRT transcripts, Book chapters, assignment instructions, Lesson pages, Folder files, and selected teacher-authored content. Moodle PHPUnit on an isolated database passed (321 tests, 1159 assertions). Python tests passed (577).

Eight controlled Gemini analyses on a throwaway site all succeeded: 18 of 18 quotations were exact. That check is a development diagnostic, not a benchmark. The main limitation was retrieval. Because the model may choose only from the BM25 Top-5, it could not select `GI_C1_3` for the DOCX or the assignment, `GI_C3_3` for the VTT transcript, or `GI_C2_3` for the PPTX. Where the expected competency was in the Top-5, the quiz recovered `GI_C3_2` plus the parent `GI_C3`, the PDF recovered `GI_C1_2` plus `GI_C1_1`, the book returned `GI_C1_4` exactly, and the lesson recovered `GI_C2_3` plus the parent `GI_C2`. Prompt, Top-K, and descriptions were not changed after that result.

Passwords are not in this file. They are sent separately.
