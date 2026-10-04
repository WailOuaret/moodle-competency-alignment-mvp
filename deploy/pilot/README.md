# Private teacher pilot: deployment files

Docker Compose files and scripts for running Moodle, the Competency Alignment Assistant plugin and the alignment
service for a **private pilot with seven named teachers**.

**Status: DRAFT.** Tried on a development machine only. Not run on a server, not used by any teacher, no live model
called. Not production-ready. **Public distribution requires licensing/IP confirmation.** Start with
[docs/VPS_DEPLOYMENT_GUIDE.md](../../docs/VPS_DEPLOYMENT_GUIDE.md).

Nothing in this directory is a secret: `.env.example` holds placeholders, and the real env file, the teacher
credentials, backups and logs are kept out of Git (see the root `.gitignore`).

## What is here

| Path | What |
|---|---|
| `docker-compose.yml` | the four services (`db`, `alignment-api`, `moodle`, `moodle-cron`), two networks, two volumes |
| `.env.example` | every setting, with placeholders. `scripts/init-env.sh` turns it into the real, private env file |
| `alignment/` | Dockerfile and pinned requirements for the service image (non-root, read-only, no `/docs`) |
| `moodle/` | Dockerfile, env-driven `config.php`, entrypoint, cron loop, Apache and PHP settings, provisioning scripts |
| `content/pages/` | the six sample Pages of the pilot course |
| `nginx/` | templates for the host's reverse proxy (HTTPS, rate limits). Rendered by `scripts/render-nginx.sh`, never installed by a script |
| `host/crontab.example` | the operator's health check and nightly backup |
| `scripts/` | everything you run: see below |

## Scripts

| Script | Does | Changes the server? |
|---|---|---|
| `init-env.sh` | creates the env file with generated secrets (mode 600, nothing printed) | no |
| `set-secret.sh NAME` | sets one value from a silent prompt (for example the model key) | no |
| `compose.sh ...` | `docker compose` with the right project and env file | as the command says |
| `healthcheck.sh [--readiness]` | health, and the checks before inviting anyone | no (read only) |
| `backup.sh` / `restore.sh` | verified backup / restore (restore replaces live data) | restore does |
| `update.sh` / `rollback.sh` | back up, rebuild, check / go back | yes |
| `provision-teachers.sh` | creates teacher01 to teacher07, writes passwords to a private file | yes (Moodle data) |
| `teacher-account.sh` | status, suspend, unsuspend, reset a password | yes (Moodle data) |
| `test-teacher-access.sh` | checks each account's password and rights | no |
| `clear-test-data.sh` | empties the plugin's tables, after a backup | yes (Moodle data) |
| `record-pilot-start.sh` | writes `PILOT_RECORD.json` | no |
| `rotate-token.sh` | new service token | yes |
| `render-nginx.sh` | prints nginx configuration | no |
| `package-plugin.sh` | builds `dist/local_compalign-<release>-pilot.zip` | no |
| `package-pilot-build.sh` | builds the tarball of exactly the files the images need | no |

## Design in one paragraph

Moodle reaches the alignment service over a private Docker network at a fixed IP address, with plain http, as the plugin's
rules allow for private addresses. Moodle's own protection against requests to internal addresses stays on, with one hole: the
service's single address, on port 80, computed in `moodle/config.php` from the environment. Moodle's web port is published on
`127.0.0.1` only, so the host's nginx, which terminates TLS, is the only way in. PostgreSQL (5432) and the service (8001)
are not published. Moodle's cron runs in its own container, in a loop every 20 seconds. There is one database, for Moodle only: the
service keeps no state.

## First run on a development machine (disposable)

```bash
export PILOT_HOME=$(mktemp -d)                  # keeps the env file and backups out of the repository
scripts/init-env.sh
# edit $PILOT_HOME/private/pilot.env: MOODLE_WWWROOT=http://localhost:18080, MOODLE_HOST_PORT=18080,
# ALIGNMENT_BACKEND=mock (NEVER for teachers), COMPOSE_PROJECT_NAME=compalign_pilot_localtest
scripts/compose.sh up -d --build
scripts/compose.sh logs -f moodle               # the first start installs Moodle (minutes)
scripts/healthcheck.sh
```

Tear it down with `scripts/compose.sh down -v`. That deletes the database and Moodle's data, which is right for a disposable copy and wrong for the
pilot.
