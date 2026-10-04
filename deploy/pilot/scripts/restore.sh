#!/usr/bin/env bash
# Restore a backup made by backup.sh. THIS REPLACES THE LIVE DATABASE AND DATA DIRECTORY.
#
#   scripts/restore.sh BACKUP_DIR --yes-replace-live-data
#
# What it does, in order:
#   1. checks the backup's checksums
#   2. takes a safety backup of the current state (labelled before-restore)
#   3. stops Moodle and cron
#   4. drops and recreates the database, loads db.sql.gz
#   5. empties the data directory and unpacks moodledata.tar.gz
#   6. starts everything again and re-applies the settings from the env file
#
# Teacher accounts, reviews and analyses come back as they were at the time of the backup. Anything
# saved after it is lost. Tell the teachers first.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

src="${1:-}"; confirm="${2:-}"
[ -n "$src" ] && [ -d "$src" ] || die "usage: restore.sh BACKUP_DIR --yes-replace-live-data"
[ "$confirm" = "--yes-replace-live-data" ] || die "this replaces the live data. Add --yes-replace-live-data to go ahead."
src="$(cd "$src" && pwd)"
[ -f "$src/db.sql.gz" ] && [ -f "$src/moodledata.tar.gz" ] && [ -f "$src/SHA256SUMS" ] || die "$src is not a complete backup"
( cd "$src" && sha256sum -c SHA256SUMS >/dev/null ) || die "the backup's checksums do not match. It is damaged; nothing was changed."

db="$(read_env POSTGRES_DB || echo moodle)"; dbuser="$(read_env POSTGRES_USER || echo moodle)"

say "Taking a safety backup of the current state first..."
"$(dirname "$0")/backup.sh" --label before-restore --no-verify

say "Stopping Moodle and cron..."
compose stop moodle moodle-cron
compose up -d db
until compose exec -T db pg_isready -U "$dbuser" -d postgres >/dev/null 2>&1; do sleep 2; done

say "Replacing the database..."
compose exec -T db psql -U "$dbuser" -d postgres -v ON_ERROR_STOP=1 -qc "DROP DATABASE IF EXISTS $db WITH (FORCE)"
compose exec -T db psql -U "$dbuser" -d postgres -v ON_ERROR_STOP=1 -qc "CREATE DATABASE $db OWNER $dbuser"
gunzip -c "$src/db.sql.gz" | compose exec -T db psql -U "$dbuser" -d "$db" -v ON_ERROR_STOP=1 -q >/dev/null

say "Replacing the data directory..."
compose run --rm --no-deps -T --entrypoint sh moodle -c \
    'find /var/www/moodledata -mindepth 1 -delete && tar -xzf - -C /var/www/moodledata && chown -R www-data:www-data /var/www/moodledata && chmod 2770 /var/www/moodledata' \
    <"$src/moodledata.tar.gz"

say "Starting everything..."
compose up -d
plog "restored from $src"
say "Restored from $src. Moodle re-applies the env file's settings on start-up (a minute or two)."
say "Then run scripts/healthcheck.sh."
