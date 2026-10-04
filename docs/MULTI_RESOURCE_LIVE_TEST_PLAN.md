# Controlled live-test plan (not run)

Branch `feature/moodle-multiresource`. Do not run these calls until Wail authorises them. Do not use teacher accounts T001–T007. Do not point this branch at https://srv1872740.hstgr.cloud/.

One call each, after the local Moodle sandbox can queue an analysis and the service is the same Gemini configuration as the Page pilot (prompt 1.0, schema 1.0, Top-K 5, maximum suggestions 3, write-back off):

| Item | What to send | Pass if |
| --- | --- | --- |
| One multichoice question | Stem and choices, no scores | Completed, every quote is an exact substring, no attempt data in the request |
| One text-layer PDF | Extracted page text | Evidence names the file and a page |
| One DOCX | Extracted paragraphs | Evidence names a heading or paragraph, not an invented page |
| One PPTX | Slide text, no speaker notes | Evidence names a slide |
| One VTT or SRT | Caption text | Evidence names a start and end time |
| One Book chapter | Chapter title and body | Evidence names the chapter |
| One assignment | Introduction only | No submission file is read |
| One Lesson page | Page content | No attempt is read |

Stop after these eight. Record the plugin commit, the service commit, extractor version 1.0, and each resource hash. Do not calculate accuracy from them.
