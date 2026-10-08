# VPS development and deployment workflow

**The VPS is the Moodle environment. Do not build a local Moodle Docker stack
for routine integration work.**

A local Moodle stack is only justified when a specific unit test cannot run any
other way, and only if Wail asks for it. Everything else — integration testing,
browser testing, upgrade testing, deployment — happens on the VPS.

Contains no credentials, hostnames or IP addresses.

---

## 1. Where work happens

| Local machine (WSL) | VPS |
|---|---|
| Edit code | Moodle |
| Git operations | PostgreSQL |
| Python tests (`pytest`) | Alignment service |
| `compileall`, UI smoke | Moodle cron |
| Static checks | Document extraction |
| Packaging a build | Moodle PHPUnit |
| | Browser testing |
| | The persistent hosted pilot |

The pilot runs unattended. **Wail's PC is not required** for teachers to use it.

---

## 2. Connecting

An `~/.ssh/config` entry defines the host alias. Two properties matter:

```
AddressFamily inet
KexAlgorithms curve25519-sha256
Ciphers aes128-ctr
ControlMaster auto
ControlPath ~/.ssh/cm/%r@%h:%p
ControlPersist 10m
```

**Why.** The hostname resolves to IPv6 but only IPv4 routes work, and the path
drops large packets — the default key-exchange offer is big enough to
black-hole, so the session hangs *after* the SSH banner appears. Pinning one KEX
algorithm and one cipher keeps the handshake small enough to get through.
Multiplexing reuses a single connection for many commands.

### Rules for a flaky link

1. **Never retry SSH in a tight loop.** fail2ban will ban the client IP. This
   has happened; clearing it needs the hosting browser console
   (`fail2ban-client set sshd unbanip <ip>`).
2. Space retries at least 30 seconds apart, and give up after about three.
3. `scp` is less reliable here than piping over the SSH channel:
   `ssh HOST 'cat > /path/file' < localfile`, then verify with `sha256sum`.
4. For anything long-running, **launch it detached on the server** and poll a
   log, so a dropped connection does not kill the job:
   ```bash
   ssh HOST 'setsid nohup /home/claude/job.sh >/dev/null 2>&1 &'
   ssh HOST 'tail -20 /home/claude/job.log'
   ```

---

## 3. The normal cycle

1. **Edit locally** on `feature/moodle-plugin`.
2. **Run local checks:** `pytest -q`, `compileall`, UI smoke, annotation validator.
3. **Commit.** No assistant attribution trailers.
4. **Push** — only with Wail's explicit say-so. Never `main` or
   `public-clean-2026-09-30`. Never force-push.
5. **Package the exact commit:**
   ```bash
   deploy/pilot/scripts/package-pilot-build.sh
   # -> dist/compalign-pilot-build-<commit>.tar.gz + .sha256
   ```
6. **Send it and verify the checksum on the server.**
7. **Test on the isolated stack first** (section 4).
8. **Back up** (section 5).
9. **Deploy** (section 6).
10. **Smoke-test**, then record the result.

Never deploy a dirty working tree. Every deployment corresponds to one commit.

---

## 4. Isolated testing on the VPS

A separate PHPUnit stack (`compalign_phpunit_*`) exists on the VPS with its own
Moodle, database and plugin bind mount. It is independent of the pilot and must
never share the pilot database.

> **Trap.** The production build **excludes `tests/`** by design. Syncing a
> production build over the PHPUnit stack therefore *removes its tests*. Ship
> the full plugin directory separately when refreshing that stack.

```bash
# after changing db/install.xml, the test database must be rebuilt
docker exec compalign_phpunit_moodle \
  php /var/www/html/public/admin/tool/phpunit/cli/init.php

# full suite
docker exec compalign_phpunit_moodle sh -c \
  'cd /var/www/html && php vendor/bin/phpunit --testsuite local_compalign_testsuite --no-coverage'
```

`tests/upgrade_test.php` exercises the real migration: it drops the new table,
stands the recorded version back down, runs the upgrade step and asserts both
the table and the resulting version. **A fresh install passing does not prove
the upgrade works** — run both.

The init step rebuilds the whole Moodle test database and takes several minutes
on this VPS. Run it detached.

---

## 5. Backup — mandatory before any deployment

The pilot scripts run from the deployed copy (`app/deploy/pilot` inside the
pilot directory) and need `PILOT_HOME` set to the pilot directory. Without it
they cannot find `private/pilot.env` and stop with "no env file".

```bash
export PILOT_HOME=~/compalign-pilot
scripts/backup.sh --label PRE_<CHANGE>
```

It writes `db.sql.gz`, `moodledata.tar.gz`, a manifest and checksums, then
**verifies by loading the dump into a scratch database** and counting the
plugin's tables. Labelled backups are never auto-pruned.

**Do not deploy if the backup or its verification fails.**

The pilot now holds **real teacher-study data**. A restore is not a theoretical
safety net.

---

## 6. Deployment

```bash
scripts/update.sh [--tag NAME]
```

In order: require a complete env file and a currently healthy pilot; take a
labelled backup; retag the running images so `rollback.sh` can return to them;
build the new tag; recreate containers; run the healthcheck. It uses
`set -euo pipefail` and stops on failure.

Moodle upgrades its database on start-up when the plugin version increases.

After deploying, prove the study data survived. Compare every plugin-table row
in the pre-deployment backup's dump with the live database, printing counts
only and never row contents. Every row must be identical; rows created after
the backup are expected.

`update.sh` performs **no** destructive data operation: no drop, truncate,
`down -v`, volume removal or prune, and it never calls `clear-test-data.sh`.
Named volumes survive container recreation.

### Rollback

```bash
scripts/rollback.sh
```

Returns to the retained previous images. Restore the database **only** if a
schema change actually requires it — starting old code does not undo a
completed database upgrade. Moodledata is preserved.

---

## 7. What must never happen

- Rebooting the VPS. It also runs a **live production Academy site**.
- Touching the Academy application, its database, its port or its nginx.
  Check Academy returns HTTP 200 before and after any pilot change.
- `docker system prune -a`, global volume pruning, or removing pilot volumes.
- Enabling official Moodle competency write-back.
- Weakening SSH security or disabling fail2ban.
- **Resetting the pilot database.** The study has begun; `teacher01` has
  submitted real reviews. Older instructions to clear analyses, suggestions,
  evidence and reviews to zero are obsolete.
- Using a `teacherNN` account for development. Use `devteacher`.

---

## 8. Health checks

```bash
scripts/healthcheck.sh
```

Covers Moodle over HTTPS, PostgreSQL, the alignment service on the private
network, and cron. Separately confirm the Academy site still returns 200.

Expected steady state: four pilot containers `Up (healthy)` with restart policy
`unless-stopped`, Docker enabled at boot, named volumes for the database and
moodledata, and the alignment service reachable only inside the Docker network
with no host port binding.

---

## 9. Starting a new session

Read `docs/CURRENT_PROJECT_STATE.md` first. It carries the current release, the
deployment gap, the study state and the outstanding work.

Do **not** begin by creating a local Moodle Docker environment.
