# UTC Moodle deployment checklist

This note is for a later conversation with the UTC Moodle administration team.
UTC Moodle has not been installed with this plugin, and nothing here is a test result from that site.

The plugin that would be discussed is `local_compalign` release **0.3.1** (version `2026100701`), on branch `feature/moodle-plugin`.

## What was tested, and where

| Item | Tested value | Where |
|---|---|---|
| Moodle | 5.2.1+ (build 20260722), version `2026042001.07` | Private pilot and throwaway site on the project server. Not UTC Moodle. |
| PHP | 8.3 | Same private server. |
| Database | PostgreSQL 16 | The plugin uses Moodle's database API. MySQL or MariaDB are not claimed. |
| Plugin maturity | ALPHA | Not a Moodle plugins-directory release. |

## Installation

- Copy `moodle-plugin/compalign` to `local/compalign`.
- Log in as a site administrator and run the Moodle upgrade (`php admin/cli/upgrade.php --non-interactive`), or open the site so Moodle runs the upgrade.
- Upgrade from 0.3.0 (`2026100403`) creates `local_compalign_manualrel`. A fresh install creates it from `db/install.xml`.
- Confirm Site administration → Plugins → Local plugins → Competency Alignment Assistant shows release 0.3.1.
- Leave **Enable official write-back** unticked. The setting has no effect. Accept, Modify and Add competency do not create Moodle competency links.

## Moodle configuration the plugin expects

- A competency framework enabled in Moodle, and selected in the plugin settings. The pilot uses `UTC_GI_MVP_2026`. The interface reads that framework from Moodle. It does not hardcode competency ids.
- Competencies enabled (`core_competency`). Official links are read with Moodle's own API. If competencies are disabled, the official column is empty.
- Cron running. Analyses are ad hoc tasks. A file's text is extracted by a background task before the model call.
- Capabilities: teachers need `local/compalign:view`, `:analyse` and `:review` in the course. Study export needs `local/compalign:viewallreviews` at system level. Settings need `local/compalign:manage`. Students receive none of these. The write-back capability is granted to nobody.

## Alignment service

- The plugin calls a private HTTP service configured as a base URL and a bearer token. The pilot uses an address on the private Docker network. The token is an admin setting and must not be committed or pasted into a ticket.
- The service needs outbound HTTPS from the server that runs it to the Gemini API, when the backend is Gemini. The pilot model is `gemini-3.5-flash`. A UTC deployment could instead point the plugin at a service the university operates. That choice is not made here.
- The service is not published on the public internet in the pilot.
- Document extraction uses Python packages already in the service image: pypdf, python-docx, python-pptx. Scanned PDFs are not OCR'd. Video is not transcribed. A caption file (VTT or SRT) can be analysed.
- Request limits used on the pilot: JSON body about 2 MB, extraction body about 21 MB, web upload about 40 MB. A single file above 20 MB is refused by the plugin.

## Network boundary

- Moodle must reach the alignment service. The service must not need to reach student networks.
- The service receives teacher-authored resource text and the competency catalogue. It does not receive student attempts, grades, submissions or account passwords.
- Show in source reads text Moodle already stored or extracted. It does not call the model.

## Privacy

- Personal data in the plugin: who requested an analysis, review decisions and comments, and teacher-added competencies (optional comment and quotation).
- The privacy provider exports and deletes those records. The file-text cache has no user id.
- Study export uses a teacher pseudonym (`T001` or a keyed hash). It does not include the raw user id, passwords or the service token.
- No learner-generated content is part of this feature.

## Backup and rollback

- Back up the Moodle database and moodledata before installing or upgrading.
- Rollback of a bad upgrade is a restore of that backup, then the previous plugin code. Do not leave a newer database schema under an older plugin.
- Official Moodle competency links are not written by the plugin, so a rollback does not have to undo links the plugin created.

## Write-back

Write-back remains off. A teacher-reviewed relationship is a record in the plugin. An official Moodle competency link is a record Moodle itself stores on an activity. The interface shows them separately. They may differ on purpose while write-back is off.

## What UTC would still need to verify

- Their Moodle version and PHP version against the tested pair above.
- Their database engine.
- Whether their competency framework id numbers match the catalogue the research uses, or whether a different framework will be configured.
- Outbound HTTPS policy if the alignment service calls Gemini, or the internal URL if they host the service.
- Cron, file-size limits, and privacy review under their own data agreement.
- That students cannot receive the plugin capabilities.
- A backup and a restore drill on a copy of their site, not on production, before any teacher use.

This checklist does not authorise that deployment.
