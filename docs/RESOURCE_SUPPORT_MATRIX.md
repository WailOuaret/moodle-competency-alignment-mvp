# Resource support matrix

Version 0.3.0, plugin version `2026100403`. The alignment method is the same for every row that is supported: normalise, fragment, BM25 top 5, constrained selection, exact evidence, teacher review.

The four status columns are separate. A cell is yes only for a check that was actually run.

| Resource | Granularity | IMPLEMENTED | AUTOMATED TESTED | BROWSER TESTED | LIVE MODEL TESTED |
| --- | --- | --- | --- | --- | --- |
| Page | one Page | yes | yes | yes | no |
| Quiz question | one question version | yes | yes | yes | no |
| PDF | one file | yes | yes | yes | no |
| DOCX | one file | yes | yes | yes | no |
| PPTX | one file | yes | yes | yes | no |
| TXT and Markdown | one file | yes | yes | yes, listed on the dashboard | no |
| VTT and SRT | one caption file | yes | yes | yes | no |
| Book chapter | one visible chapter | yes | yes | yes, listed; hidden chapter omitted by the automated test | no |
| Assignment | the instructions | yes | yes | yes, listed | no |
| Lesson page | one content page | yes | yes | yes, listed | no |
| Folder file | each supported file | yes | yes | yes, listed | no |
| Text and media area | one area | yes | yes | yes, listed | no |
| Forum introduction | the introduction only | yes | yes | yes | no |
| URL description | title and description | yes | yes | yes | no |
| Random quiz slot | — | refused | yes | yes | no |
| Legacy DOC | — | refused | yes | yes | no |
| Video without a transcript | — | refused | yes | yes | no |
| Scanned PDF | — | refused after extraction | yes | yes | no |
| Choice, Glossary, Wiki, Database, SCORM, H5P, Workshop | — | not in 0.3.0 | yes, reported unsupported | not opened | no |

Student attempts, assignment submissions, grades, forum posts and lesson scores are not read. Automated tests and the browser course both contain synthetic learner rows, and those strings are absent from the extracted text and from the stored evidence.

Quiz competency write-back, if enabled later, can attach only to the Quiz activity. Moodle does not store a competency on a question. Write-back is off.

A live Gemini matrix is written in `docs/MULTI_RESOURCE_LIVE_TEST_PLAN.md` and has not been run.
