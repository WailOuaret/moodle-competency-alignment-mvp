# Resource support matrix

Version 0.3.0. The alignment method is the same for every row that is supported:
normalise, fragment, BM25 top 5, constrained selection, exact evidence, teacher review.

| Resource | Granularity | Extracted | Evidence shown as | Student data | Status |
| --- | --- | --- | --- | --- | --- |
| Page | one Page | title, introduction, body | the Page | none | Supported |
| Quiz | one question version | stem; choices for multichoice, true/false and matching | Quiz, slot, question version | none; attempts are not read | Supported for multichoice, truefalse, shortanswer, numerical, essay, match |
| PDF | one file | text layer, one segment per page | filename and page | none | Supported when a text layer exists. A scanned PDF is reported as having no extractable text. OCR is off |
| DOCX | one file | paragraphs, headings, tables | filename and heading or paragraph | none | Supported. Page numbers are not invented |
| PPTX | one file | slide text | filename and slide | none | Supported. Speaker notes are not included |
| TXT and Markdown | one file | plain text | filename | none | Supported. Markdown is not rendered as HTML |
| Video | one caption file | VTT, SRT or plain transcript | filename and timestamps | none | Supported when a transcript file is stored in Moodle. Automatic transcription is off |
| Book | one visible chapter | chapter title and content | book and chapter | none | Supported |
| Assignment | the activity instructions | introduction and teacher intro attachments | the assignment | none | Supported. Submissions, grades and feedback are not read |
| Lesson | one content page | page content and answer texts | lesson and page | none | Supported. Attempts and scores are not read |
| Folder | each supported file | as the file type | the file | none | The folder title is not analysed |
| Text and media (label) | one area | the text | the area | none | Supported |
| Forum | the introduction only | introduction | the forum | none | Posts and replies are not read |
| URL | the description only | title and description | the URL activity | none | The remote address is not fetched |
| Choice, Glossary, Wiki, Database, SCORM, H5P, Workshop | — | — | — | mixed or learner-authored | Not supported in 0.3.0 |
| Random quiz slot | — | — | — | — | Not supported, because there is no fixed question |

Quiz competency write-back, if enabled later, can attach only to the Quiz activity. Moodle does not store a competency on a question.
