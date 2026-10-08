# Study export

The export is `local/compalign/export.php`. It requires `local/compalign:viewallreviews` at system level.

Formats: `format=csv` (default) and `format=json`.

Filters: `courseid`, `resourcetype`, `participant` (for example `T001`), `from` and `to` as Unix timestamps.

The participant column is the Moodle id number when it looks like `T001`. Otherwise it is `participant-` plus a short keyed hash. Names, emails and raw user ids are not exported.

A review comment is exported. A teacher can type a name into that box, so treat the file as personal data even though the other columns are pseudonymised.

The export does not include passwords, addresses, session data, service tokens or model credentials.

Release 0.3.1 adds three columns. Existing columns keep their meaning.

| Column | Meaning |
|---|---|
| `relationship_source` | `MODEL_ACCEPTED`, `MODEL_MODIFIED`, or `TEACHER_ADDED`. Empty when the latest decision is a rejection. A rejection is not a relationship. |
| `relationship_status` | `current` when the resource still matches the reviewed version, `stale` when it has changed, `removed` when the teacher withdrew an added competency. Empty for a rejection. |
| `teacher_evidence` | The quotation supplied with a teacher-added competency. Empty when the teacher gave none, and empty on model-review rows. |

Teacher-added rows use the same file. Their `decision` is empty, because they are not an accept, reject or modify of a model suggestion. `final_competency` is the competency the teacher added. `resource_id`, `resource_type`, `resource_hash`, `participant_id` and `review_time` (the time it was added) are filled. A removed addition stays in the file with status `removed`.

Development rows and teacher-study rows live in the same tables. Filter by course and by time so a development course is not mixed into the study file. The 0.2.0 Page pilot was not upgraded to this export.
