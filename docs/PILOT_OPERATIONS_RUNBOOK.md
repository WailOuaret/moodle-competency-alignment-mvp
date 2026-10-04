# Private teacher pilot: operations runbook

**Status: DRAFT. Every procedure below is written but has not been run on the VPS.** The ones marked
"tried locally" were run against a disposable copy of the stack on a development machine. Mark each
procedure here as verified on the VPS the first time you run it.

All commands are run as the `claude` operator account on the server, from the pilot's scripts
directory, with `PILOT_HOME` set:

```bash
export PILOT_HOME=/opt/compalign-pilot
cd $PILOT_HOME/app/deploy/pilot
```

**Nothing in this runbook prints a password, the service token, the model key or the database password.**
If a step seems to need one, it reads it from a file or a prompt. Do not paste any of them into a chat, an
email or a ticket.

## 1. Where things are

| What | Where |
|---|---|
| The code and scripts | `$PILOT_HOME/app/` (scripts in `app/deploy/pilot/scripts/`) |
| Settings and secrets (mode 600) | `$PILOT_HOME/private/pilot.env` |
| Teacher credentials (mode 600) | `$PILOT_HOME/private/teacher_credentials.csv` |
| Backups (mode 700) | `$PILOT_HOME/backups/<UTC time>[-label]/` |
| What the scripts did | `$PILOT_HOME/logs/pilot.log` (rotates itself at 5 MB, never holds a secret) |
| Release records for rollback | `$PILOT_HOME/releases/` |
| Pilot start record | `$PILOT_HOME/PILOT_RECORD.json` |
| Container logs | `scripts/compose.sh logs --since 1h <service>` (rotated by Docker at 10 MB x 5) |
| nginx logs | `/var/log/nginx/compalign-pilot.{access,error}.log` |

Services: `db`, `alignment-api`, `moodle`, `moodle-cron`.

## 2. Routine

**Every day (two minutes):**

```bash
scripts/healthcheck.sh            # HEALTHY, or a list of FAIL lines
scripts/teacher-account.sh status # who logged in, who is suspended
```

The same check runs every five minutes from cron and writes failures to `logs/cron-health.log`.

**Every week:** look at `df -h`, `scripts/compose.sh logs --since 168h alignment-api | grep -c "analysis completed"` (the number of model
calls, see section 9), and the newest backup's `MANIFEST.txt`.

**Every month:** do a restore drill (section 5) on a scratch copy.

## 3. Starting, stopping, restarting

```bash
scripts/compose.sh ps                     # what is running
scripts/compose.sh up -d                  # start everything, recreate what changed
scripts/compose.sh restart moodle         # restart one service
scripts/compose.sh stop                   # stop everything, keep all data
```

Containers restart by themselves after a crash or a reboot (`restart: unless-stopped`), provided Docker starts at boot. **Never** run
`scripts/compose.sh down -v`: it deletes the database and Moodle's data.

To keep teachers out while you work: `scripts/compose.sh exec -u www-data moodle php /var/www/html/admin/cli/maintenance.php --enable` (and `--disable`).

## 4. Cron

Analyses start only when Moodle's cron runs them. The `moodle-cron` container runs `cron.php` in a loop with a 20-second pause. Each run stays
alive about three minutes picking up new tasks within seconds, so a queued analysis waits at most about 20 seconds for a free run.

```bash
scripts/compose.sh logs --since 10m moodle-cron      # a line per run: "run finished, exit 0"
scripts/compose.sh exec -T -u www-data moodle php /opt/pilot/provision/report.php | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["cron"], d["analyses"])'
```

If analyses stay "Queued": check that `moodle-cron` is running and healthy; look at Site administration, Server, Tasks, Ad hoc tasks for
failures; restart it with `scripts/compose.sh restart moodle-cron`. The healthcheck fails when cron has not started in 5 minutes.

## 5. Backup and restore

```bash
scripts/backup.sh                         # a verified backup now (nightly from cron at 03:15 UTC; keeps 14)
scripts/backup.sh --label before-x        # a labelled one, never deleted automatically
ls -1 $PILOT_HOME/backups
scripts/restore.sh $PILOT_HOME/backups/<name> --yes-replace-live-data
```

A backup is the database (`db.sql.gz`), Moodle's data directory (`moodledata.tar.gz`, without caches and sessions), a manifest and checksums. It
is **verified** when written: the files are tested and the database dump is loaded into a scratch database and its tables counted. It does **not**
contain the env file or the teacher credentials, which are secrets: keep a copy of those two files in your password manager or an encrypted
store. **Copy backups off the server too** (the provider's VPS snapshot, or `scp` of a backup directory): a backup on the same disk does not
survive the disk.

A restore **replaces** the live data with the backup's. It first takes a safety backup (`before-restore`). Teacher decisions saved after the
backup was made are lost: tell the teachers first. Afterwards run `scripts/healthcheck.sh` and `scripts/test-teacher-access.sh`.

**Restore drill (monthly).** Restore the newest backup onto a scratch Compose project on another port (a copy of the env file with
`COMPOSE_PROJECT_NAME=compalign_drill`, a different `MOODLE_HOST_PORT`, `PILOT_SUBNET` and `ALIGNMENT_IP`), check that Moodle comes up and the
review pages show the saved decisions, then `compose down -v` that scratch project. The drill must never be run against the live project name.

## 6. Updating and rolling back

```bash
# 1. get the new code onto the server (docs/VPS_DEPLOYMENT_GUIDE.md section 6)
# 2.
scripts/update.sh                         # backs up, builds new images, restarts, checks
# if it says the new version is unhealthy:
scripts/rollback.sh --yes-replace-live-data      # previous images AND the pre-update data
```

`update.sh` refuses to start unless the pilot is healthy now. A plugin version bump upgrades Moodle's database on start-up; that cannot be
undone by starting older code, which is why rollback restores the backup taken just before. Do not update while teachers are working. Do not update
during the pilot unless a defect requires it, and record why in `logs/pilot.log` notes: the study treats the system as fixed.

## 7. Teacher accounts

```bash
scripts/teacher-account.sh status                  # all seven: active/suspended, last access, whether the first-login password change is still pending
scripts/teacher-account.sh suspend teacher03       # cannot log in, signed out at once
scripts/teacher-account.sh unsuspend teacher03
scripts/teacher-account.sh reset-password teacher03    # a new random password, written to the credentials file, forced change at next login
scripts/test-teacher-access.sh                     # checks every password in the file and every account's rights (before first login only)
```

Nothing is ever deleted: a teacher's saved decisions stay attached to the account. Passwords are not printed anywhere; read them from
`$PILOT_HOME/private/teacher_credentials.csv` when you hand them out, and hand each one out only to its person, by a channel that is not the chat or
the same email as the address of the site. `test-teacher-access.sh` can only check a password that has not yet been changed: after a
teacher's first login the file's password is obsolete by design, and the check will report it as rejected.

The mapping from a pseudonym (T001 to T007) to a real person exists **only** in your own private list, not on the server and not in the repository.

## 8. Secrets

| Secret | Rotate with | When |
|---|---|---|
| Service token (Moodle and service) | `scripts/rotate-token.sh` | if it may have leaked; after the pilot |
| Model key | revoke it at the provider, then `scripts/set-secret.sh GEMINI_API_KEY` and `scripts/compose.sh up -d alignment-api` | if it may have leaked; after the pilot |
| Teacher password | `scripts/teacher-account.sh reset-password teacherNN` | forgotten, or leaked |
| Moodle administrator password | `scripts/compose.sh exec -u www-data moodle php /var/www/html/admin/cli/reset_password.php --username=admin` (prompts) | if it may have leaked |
| Database password | change it in PostgreSQL (`ALTER USER`), then in the env file, then `scripts/compose.sh up -d`. The database is reachable only from the two Moodle containers, so this is rarely needed | if it may have leaked |

The administrator password in the env file is used only the first time Moodle is installed. Changing it in Moodle afterwards does not require
changing the file, but the file then holds an obsolete value: replace or delete that line once the site is installed.

## 9. Watching the cost of the model

There is **no per-teacher or daily limit inside the application**. What limits spending:

- only the seven teachers can start an analysis, one at a time per Page;
- an identical Page, framework and settings reuses the earlier result; **Reanalyse** is a deliberate button;
- one analysis is one model request, with a timeout (120 s), at most 3 suggestions, and a 2 MB request limit;
- nginx limits POSTs to the plugin to 20 per minute per visitor address (once nginx is set up);
- **the spending cap you set with the model provider.** Set a low budget limit and an alert on the key before the live test. This is the real ceiling.

To count the day's model calls: `scripts/compose.sh logs --since 24h alignment-api | grep -c "analysis completed"`. Failed ones appear as `analysis failed` or `backend unavailable` (the log holds the resource id, never the Page text).
**To stop all model spending at once:** `scripts/compose.sh stop alignment-api` (teachers then see "The alignment service could not be reached"),
or clear the key: `scripts/set-secret.sh GEMINI_API_KEY --clear && scripts/compose.sh up -d alignment-api`.

If you want a hard daily cap inside the service, that is a change to `service/` with tests. It needs your approval and has not been built.

## 10. Before the pilot starts

In this order, after docs/TEACHER_PILOT_CHECKLIST.md gates are met:

```bash
scripts/clear-test-data.sh                 # shows the rows
scripts/clear-test-data.sh --delete        # backup first, then type DELETE-PILOT-TEST-DATA
scripts/healthcheck.sh --readiness         # must end HEALTHY
scripts/record-pilot-start.sh              # writes PILOT_RECORD.json: UTC start time, versions, hashes, settings. No secrets
```

`record-pilot-start.sh` refuses to run if the plugin's tables are not empty, so test data can never be mixed into the pilot's records.

## 11. Export study data

**NOT IMPLEMENTED. This needs Checkpoint H, which has not been authorised.** There is no study export yet, and none has been designed in code.

What exists today is preservation, not an export. The data lives in four tables, and a backup (section 5) contains all of it. A raw copy of just
those tables, for safekeeping:

```bash
scripts/compose.sh exec -T db pg_dump -U moodle -d moodle --data-only -t 'mdl_local_compalign_*' > $PILOT_HOME/private/compalign_tables_$(date -u +%Y%m%dT%H%M%SZ).sql && chmod 600 $PILOT_HOME/private/compalign_tables_*.sql
```

That file holds teacher user ids and free-text comments. It is **not** a study export: it is not pseudonymised beyond the ids, not joined to the
pseudonyms, and its format is not agreed. Treat it as a private backup. The study export will be designed and built under Checkpoint H.

## 12. Ending the pilot

1. Tell the teachers it is over. `scripts/teacher-account.sh suspend teacher01` and the other six.
2. `scripts/backup.sh --label pilot-final`, and copy it off the server together with the raw table copy from section 11.
3. When Checkpoint H exists, produce the study export from that final backup.
4. Decide, with the people responsible for the study, how long the data is kept. Then either keep the stack stopped
   (`scripts/compose.sh stop`) or remove it (docs/VPS_DEPLOYMENT_GUIDE.md section 8).
5. Revoke the model key at the provider, and delete `$PILOT_HOME/private/teacher_credentials.csv`.
6. Remove the operator's sudo and Docker access (docs/VPS_DEPLOYMENT_GUIDE.md section 4).

## 13. If something goes wrong

| Situation | Do |
|---|---|
| A password or the credentials file may have leaked | `teacher-account.sh reset-password` for each affected account; if the file itself leaked, `provision-teachers.sh --rotate-existing` |
| The model key may have leaked | revoke it at the provider first, then replace it (section 8) |
| The service token may have leaked | `scripts/rotate-token.sh` |
| The site looks compromised | `scripts/compose.sh stop`, keep everything as it is, take a backup labelled `incident`, tell the owner, restore from a known-good backup onto a rebuilt stack |
| A teacher asks for their data or its removal | Moodle's Privacy API (Site administration, Users, Privacy and policies, Data requests) exports or deletes that user's reviews. Do it, and record that you did |
| Disk nearly full | `docker system df`; delete old labelled backups you no longer need; `docker image prune` only for images no longer in use |
| The healthcheck fails and you do not know why | `scripts/compose.sh ps`, then `logs --since 15m` for the failing service; check the newest lines of `logs/pilot.log` |
| The existing production site is affected | stop the pilot's nginx block first: `sudo rm /etc/nginx/sites-enabled/compalign-pilot.conf && sudo nginx -t && sudo systemctl reload nginx`, then investigate |

## 14. Known limits

- No per-teacher or daily quota in the application (section 9).
- No study export (section 11).
- Pages only. Quiz and other modules are not supported.
- No email: password resets are the operator's job.
- The cron container checks Moodle's schedule every 20 seconds, but Moodle's own scheduled tasks (cleanup, caches) run on Moodle's usual timetable.
- The pilot uses the plugin as it stands, ALPHA, on one Moodle build. A browser check of its screens by a person was still pending when this was written.
