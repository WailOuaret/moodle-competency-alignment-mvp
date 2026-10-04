# Privacy and data flow

Release 0.3.0 on branch `feature/moodle-multiresource`. The hosted Page pilot (0.2.0) was not upgraded.

## What leaves Moodle

The alignment service receives teacher-authored text and the selected competency framework. It does not receive student attempts, grades, names, emails, submission files or forum posts.

| Source | Sent | Not sent |
| --- | --- | --- |
| Page | Title, introduction, body, course and section names | Learners |
| Quiz question | Stem. Choices for multichoice, true/false and matching | Scores, accepted short answers, attempts |
| PDF, DOCX, PPTX, TXT, Markdown | Extracted text | File bytes, macros, remote links inside the file |
| Transcript | Caption text | Audio and video bytes |
| Book chapter | Chapter title and content | Hidden chapters |
| Assignment | Introduction and teacher intro attachments | Submissions, feedback, grades |
| Lesson page | Page content and answer texts | Attempts, scores, jumps |
| Forum | Introduction | Posts and replies |
| URL | Title and description | The remote page |

Document bytes travel only as far as `POST /v1/extractions` on the alignment service. The model call uses the extracted text through `POST /v1/analyses`.

## What Moodle stores

`local_compalign_analysis` stores the requester, the resource id, a content fingerprint, provenance (slot, page, slide, chapter or cue list) and the service result.

`local_compalign_review` stores the teacher's decision, optional evidence rating, optional comment and review duration.

`local_compalign_extract` caches extracted file text by content hash and extractor version. It has no user id. A document can still contain a name if a teacher typed one.

The privacy provider declares these tables. Deleting a user removes their reviews and unlinks them from analyses they requested. The extraction cache is content-addressed and is not tied to a user, so user deletion does not remove it.

## Study export

`export.php` requires `local/compalign:viewallreviews`. It writes a pseudonym (`T001` when that is the id number) and the review comment. It does not write passwords, emails, addresses, tokens or model credentials. A comment can contain a name if the teacher typed one.
