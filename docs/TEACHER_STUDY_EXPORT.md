# Study export

The export is `local/compalign/export.php`. It requires `local/compalign:viewallreviews` at system level.

Formats: `format=csv` (default) and `format=json`.

Filters: `courseid`, `resourcetype`, `participant` (for example `T001`), `from` and `to` as Unix timestamps.

The participant column is the Moodle id number when it looks like `T001`. Otherwise it is a short hash of the id number, or `user-{id}` when the id number is empty. Names and emails are not exported.

A review comment is exported. A teacher can type a name into that box, so treat the file as personal data even though the other columns are pseudonymised.

The export does not include passwords, addresses, session data, service tokens or model credentials.

Development rows and teacher-study rows live in the same tables. Filter by course and by time so a development course is not mixed into the study file. The 0.2.0 Page pilot was not upgraded to this export.
