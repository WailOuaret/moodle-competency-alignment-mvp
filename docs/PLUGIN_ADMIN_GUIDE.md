# Competency Alignment Assistant (local_compalign): administrator guide

**Status: DRAFT for the private teacher pilot.** The plugin is version 0.2.0, maturity ALPHA. It has
been verified on one Moodle build only (5.2.1+, 22 July 2026) by 295 PHPUnit tests, and a browser
check of the screens by a person is **still pending** (docs/MOODLE_PLUGIN_BROWSER_CHECKLIST.md). It has
not been used by any teacher. Nothing here is a claim of production readiness.

**PUBLIC DISTRIBUTION REQUIRES LICENSING/IP CONFIRMATION.** This guide covers installing the plugin on
a site you control for the private pilot. It does not cover, and nothing in this repository authorises,
publication to the Moodle Plugins Directory, Packagist or any public download.

## What the plugin is

A **local plugin** for Moodle 5.2. For a course Page it asks an external **alignment service**
(a small Python/FastAPI service in this repository, `service/`) which of the competencies in one
Moodle competency framework the Page supports, and shows the answer to the teacher with the exact
quotations that justify it. The teacher accepts, rejects or modifies each suggestion.

What it does not do, by design in this release:

- It **never writes** to Moodle competency links. The write-back setting is reserved and has no
  effect. No role holds the write-back capability.
- It handles **Pages only**. Forums, quizzes and every other module say "Resource type not supported
  in this prototype".
- It never sends student data. Only the text of the Page and the framework's competencies leave Moodle.

## Requirements

| | |
|---|---|
| Moodle | 5.2 (the plugin's `requires` is 2026042001). Tested only on 5.2.1+, build 20260722. |
| PHP / database | Whatever that Moodle needs. The pilot image uses PHP 8.3 and PostgreSQL 16. |
| Competencies | Moodle's competency feature on, and one framework with the competencies to align against. |
| Cron | Moodle's cron must run: **an analysis only starts when cron runs it**. The pilot runs cron every 20 seconds. |
| Alignment service | Reachable from Moodle over HTTPS, or over plain http on a private address (see "Service address"). |

## Installing

### In the pilot (automatic)

The pilot's Docker image contains the plugin and the pilot's start-up script installs and configures
it. Nothing to do by hand. See docs/VPS_DEPLOYMENT_GUIDE.md.

### By hand, on another site

1. Build the package (docs/PLUGIN_PACKAGING_GUIDE.md): `scripts/package-plugin.sh`.
2. Site administration, Plugins, Install plugins, upload the ZIP, or unpack it into `public/local/`
   so that the folder is `public/local/compalign`. Moodle 5.2 serves from `public/`.
3. Visit Site administration, Notifications, and let Moodle upgrade the database. The plugin creates
   four tables: `local_compalign_analysis`, `_sugg`, `_evidence`, `_review`.
4. Configure it (below).

## Settings

Site administration, Plugins, Local plugins, **Competency Alignment Assistant**
(`/admin/settings.php?section=local_compalign`).

| Setting | Pilot value | Meaning |
|---|---|---|
| Service URL | `http://<fixed private IP>` | Where the alignment service listens. See below. |
| Service token | (stored encrypted) | The shared secret the service demands. The field never shows it. Entering a new value replaces it; clearing the field removes it. |
| Request timeout | 120 | Seconds Moodle waits for the service. 5 to 900. |
| Competency framework | UTC GI Competency Framework - MVP | Which framework the suggestions are drawn from. Only visible frameworks are offered. |
| Top-K | fixed at 5 | The research engine was evaluated at 5. The service rejects any other value, so it is not a setting. |
| Maximum suggestions | 3 | At most this many suggestions per resource, 1 to 10. |
| Enable official write-back | **off** | Reserved. No effect in this release. Leave it off. |
| Require human review | always on | Not a setting. A suggestion is never applied without a teacher's decision. |

The connection status (`/local/compalign/index.php`, as an administrator) shows **Connected** only
when the service answered *and accepted the token*. The other states are: not configured, unavailable,
unauthorised (token rejected), blocked (see below), invalid response.

In the pilot, the start-up script keeps the service URL, the token, the framework and the write-back
switch **pinned**: a restart sets them again from the server's environment, so a change typed into this page
does not survive a restart. Timeout and maximum suggestions are set once and are yours to change.

### Service address

The plugin only talks to the service over **https**, with one exception: plain **http** is allowed
for `localhost`, `host.docker.internal` and addresses PHP classes as private or reserved
(for example `172.29.80.10`). The pilot's service is reachable only on a private Docker network, so it
uses that exception and the traffic never leaves the host.

Moodle's own protection against requests to internal addresses (Site administration, Security, HTTP
security) blocks private ranges by default, which is right for a site that fetches users' URLs. The pilot
opens **exactly one address**, the service's, on port 80, in `config.php` (`$CFG->curlsecurityblockedhosts`
and `curlsecurityallowedport`, computed from the environment). Do not delete the other entries from that list
and do not add a range. If the status says **blocked**, this carve-out is missing or the address changed.

## Permissions

The plugin adds these capabilities. Students receive none.

| Capability | Default roles | Lets the holder |
|---|---|---|
| `local/compalign:view` | teacher, editingteacher, manager (course) | see the dashboard and the stored suggestions |
| `local/compalign:analyse` | teacher, editingteacher | ask for an analysis of a Page |
| `local/compalign:review` | teacher, editingteacher | accept, reject or modify |
| `local/compalign:writeback` | nobody | reserved |
| `local/compalign:viewallreviews` | manager (system) | see every teacher's reviews. In the pilot nobody holds this role. |

A teacher sees only their own decisions. The suggestions for a Page are shared between the teachers
of its course.

## What the plugin stores

Four tables. Reviews hold the teacher's user id, decision, the competency chosen when modifying, the
optional 0 to 2 rating and comment (up to 1000 characters), timestamps, and the seconds between the
card first being shown and the decision (null if unknown or over 4 hours). Analyses hold the
resource id and content hash, the framework, model name, request id and diagnostics. The plugin
implements Moodle's Privacy API: export and deletion of a user's reviews work through Site administration,
Users, Privacy and policies, Data requests.

## Cost and abuse protection

| Protection | Where | State |
|---|---|---|
| Only course teachers can trigger an analysis | capability `analyse` | in the plugin, tested |
| One analysis per Page at a time | lock and active-analysis check | in the plugin, tested |
| An identical analysis is reused instead of re-run | same Page text, framework, Top-K and maximum suggestions | in the plugin, tested |
| Re-running is an explicit button, never automatic | **Reanalyse** | in the plugin, tested |
| Maximum suggestions and timeout | settings | in the plugin |
| Service refuses oversize requests | `ALIGNMENT_MAX_BODY_BYTES` (2 MB) | in the service, tested |
| Ceiling on POSTs to the plugin per visitor address | nginx `limit_req` (20 per minute) | in the proxy template; untested until the VPS is set up |
| **A per-teacher or daily quota inside the application** | n/a | **does not exist.** See docs/PILOT_OPERATIONS_RUNBOOK.md for how to watch spend and set a cap at the model provider. Adding one would change the service and needs your approval. |

## Uninstalling

Site administration, Plugins, Plugins overview, find the plugin, Uninstall. This drops the four tables:
**every analysis and every teacher decision is deleted**. Export first (docs/PILOT_OPERATIONS_RUNBOOK.md,
"Export study data"). Then remove `public/local/compalign` from the server.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| Analysis stays **Queued** | Cron is not running | `scripts/compose.sh logs --since 10m moodle-cron`; Site administration, Server, Tasks, Ad hoc tasks |
| Status **Blocked** | The carve-out for the service address is missing | Check `ALIGNMENT_IP` is set for both Moodle containers and that `config.php` is the pilot's |
| Status **Unauthorised** | The token in Moodle differs from the service's | Restart Moodle so it re-applies the environment's token |
| Status **Unavailable** | The service is down, or the address is wrong | `scripts/compose.sh ps`, `scripts/compose.sh logs alignment-api` |
| "The analysis did not complete" | The model backend refused or timed out | The reason code is on the page and in the service log. Key missing, quota used up, or timeout |
| **Not configured** | No service URL or no framework set | Open the settings page |

The service log never contains the Page text, the token or the model key.
