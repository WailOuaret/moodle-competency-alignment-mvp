# Multi-resource architecture

Release 0.3.0, plugin version `2026100402`.

The scientific method is unchanged. `src/moodle_competency/runtime_analysis.py` is not modified. Every source becomes the same resource object the service already accepts: type, title, text, course and section context. Top-K stays 5. Schema version stays 1.0.

## Adapters

`local_compalign\resource\registry` maps a Moodle module to one adapter:

| Module | Adapter | Resource id |
| --- | --- | --- |
| page | page_adapter | `moodle:page:{pageid}` |
| quiz | quiz_adapter | `moodle:quiz:{quizid}:question:{versionid}` |
| book | book_adapter | `moodle:book:{bookid}:chapter:{chapterid}` |
| lesson | lesson_adapter | `moodle:lesson:{lessonid}:page:{pageid}` |
| assign | assignment_adapter | `moodle:assign:{assignid}` and `moodle:file:{fileid}` for intro attachments |
| resource, folder | files_adapter | `moodle:file:{fileid}` |
| label | label_adapter | `moodle:label:{labelid}` |
| forum | intro_adapter | `moodle:forum:{forumid}` |
| url | intro_adapter | `moodle:url:{urlid}` |

An unsupported module produces one dashboard row with the reason, and does not stop the rest of the course. An unsupported question does not stop the other questions in the quiz.

## Files and transcripts

PHP does not parse PDF, DOCX or PPTX. The ad-hoc task reads the Moodle file and calls `POST /v1/extractions`. The service returns canonical text and segments (page, slide, paragraph or caption cue). That text is then sent to the existing `POST /v1/analyses`. The model receives text, not file bytes.

Extracted text is cached in `local_compalign_extract` by the Moodle content hash and extractor version `1.0`. Changing the file or the extractor version misses the cache. The analysis fingerprint for a file is the type, content hash, extractor version and filename, so an old analysis becomes stale.

## Provenance

`local_compalign_analysis.provenance` stores the slot, version, page, slide, heading or cue list. Exact evidence is still a substring of the canonical text. The provenance tells the teacher where that substring sits.

## What is not sent

Student attempts, grades, names, emails, submission files, forum posts and the remote target of a URL activity are not read. Quiz answer scores are not included. Short-answer and numerical accepted answers are not included. True/false is sent as the statement plus the two choices, without marking which one is correct.
