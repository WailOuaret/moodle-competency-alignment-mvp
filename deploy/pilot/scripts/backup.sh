#!/usr/bin/env bash
# Back up the pilot: the database, Moodle's data directory, and a manifest of what was backed up.
#
#   scripts/backup.sh [--label NAME] [--keep N] [--no-verify]
#
# A backup is a directory under the backup directory, named by the UTC time:
#   db.sql.gz           pg_dump of Moodle's database (plain SQL, no owners)
#   moodledata.tar.gz   Moodle's data directory without caches, sessions and temporary files
#   MANIFEST.txt        versions, sizes and what is in the backup (no secrets)
#   SHA256SUMS          checksums of the backup files
#
# It also keeps the files needed to start the stack again: docker-compose.yml and the env file.
# The env file is a secret. It is stored mode 600 inside this mode 700 directory and is never
# printed. Teacher credential passwords are not included.
#
# After writing the backup it is checked: the files are tested, and the database dump is loaded into
# a scratch database and the plugin's tables are counted. --no-verify skips that.
# The newest N backups are kept (default 14). Backups with a label are never deleted by this.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

label=""; keep=14; verify=1
while [ $# -gt 0 ]; do
    case "$1" in
        --label) label="$2"; shift 2 ;;
        --keep) keep="$2"; shift 2 ;;
        --no-verify) verify=0; shift ;;
        *) die "unknown option $1" ;;
    esac
done
[[ "$label" =~ ^[A-Za-z0-9_-]*$ ]] || die "the label may only hold letters, digits, - and _"

db="$(read_env POSTGRES_DB || echo moodle)"; dbuser="$(read_env POSTGRES_USER || echo moodle)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dir="$PILOT_BACKUP_DIR/${stamp}${label:+-$label}"
( umask 077; mkdir -p "$PILOT_BACKUP_DIR" "$dir" )
chmod 700 "$PILOT_BACKUP_DIR" "$dir"

( umask 077
  compose exec -T db pg_dump -U "$dbuser" -d "$db" --no-owner --no-privileges | gzip -9 >"$dir/db.sql.gz"
  compose exec -T moodle tar -C /var/www/moodledata \
      --exclude=./cache --exclude=./localcache --exclude=./temp --exclude=./sessions --exclude=./trashdir \
      -czf - . >"$dir/moodledata.tar.gz" )
chmod 600 "$dir"/*


# Deployment files required to start the stack again. The env file stays mode 600.
( umask 077
  cp "$PILOT_DIR/docker-compose.yml" "$dir/docker-compose.yml"
  cp "$PILOT_ENV_FILE" "$dir/pilot.env"
  if [ -n "${PILOT_HOME:-}" ] && [ -f "$PILOT_HOME/nginx-full.conf" ]; then
      cp "$PILOT_HOME/nginx-full.conf" "$dir/nginx-full.conf"
  fi
)
chmod 600 "$dir"/docker-compose.yml "$dir"/pilot.env
if [ -f "$dir/nginx-full.conf" ]; then chmod 600 "$dir/nginx-full.conf"; fi


gzip -t "$dir/db.sql.gz" || die "the database dump is damaged"
tar -tzf "$dir/moodledata.tar.gz" >/dev/null || die "the moodledata archive is damaged"
( cd "$dir" && sha256sum db.sql.gz moodledata.tar.gz docker-compose.yml pilot.env >SHA256SUMS )
if [ -f "$dir/nginx-full.conf" ]; then ( cd "$dir" && sha256sum nginx-full.conf >>SHA256SUMS ); fi
chmod 600 "$dir/SHA256SUMS" "$dir/MANIFEST.txt"

{
    echo "pilot backup $(basename "$dir")"
    echo "created_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "git_commit: $(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "image_tag: $(read_env PILOT_IMAGE_TAG || echo unknown)"
    echo "postgres: $(compose exec -T db postgres --version | tr -d '\r')"
    echo "moodle_release: $(compose exec -T -u www-data moodle php -r 'define("CLI_SCRIPT", true); define("ABORT_AFTER_CONFIG", true); require "/var/www/html/config.php"; require "/var/www/html/public/version.php"; echo $release;' 2>/dev/null || echo unknown)"
    echo "db.sql.gz: $(stat -c %s "$dir/db.sql.gz") bytes"
    echo "moodledata.tar.gz: $(stat -c %s "$dir/moodledata.tar.gz") bytes"
    echo "excluded from moodledata: cache localcache temp sessions trashdir"
    echo "pilot.env: included, mode 600, not printed"
    echo "not included: teacher credential passwords"
} >"$dir/MANIFEST.txt"
chmod 600 "$dir/MANIFEST.txt"

if [ "$verify" = 1 ]; then
    scratch="restore_check_$$"
    compose exec -T db psql -U "$dbuser" -d postgres -v ON_ERROR_STOP=1 -qc "CREATE DATABASE $scratch" >/dev/null
    cleanup() { compose exec -T db psql -U "$dbuser" -d postgres -qc "DROP DATABASE IF EXISTS $scratch WITH (FORCE)" >/dev/null 2>&1 || true; }
    trap cleanup EXIT
    gunzip -c "$dir/db.sql.gz" | compose exec -T db psql -U "$dbuser" -d "$scratch" -v ON_ERROR_STOP=1 -q >/dev/null
    tables="$(compose exec -T db psql -U "$dbuser" -d "$scratch" -Atc "select count(*) from information_schema.tables where table_schema='public'" | tr -d '\r')"
    plugin="$(compose exec -T db psql -U "$dbuser" -d "$scratch" -Atc "select count(*) from information_schema.tables where table_name like 'mdl_local_compalign_%'" | tr -d '\r')"
    [ "$plugin" = "4" ] || die "the restored scratch copy has $plugin plugin tables, expected 4"
    echo "verified: dump loads into a scratch database ($tables tables, $plugin plugin tables)" >>"$dir/MANIFEST.txt"
fi

# Retention: unlabelled backups only.
mapfile -t old < <(ls -1 "$PILOT_BACKUP_DIR" | grep -E '^[0-9]{8}T[0-9]{6}Z$' | sort | head -n -"$keep" || true)
for name in "${old[@]:-}"; do
    [ -n "$name" ] && rm -rf -- "${PILOT_BACKUP_DIR:?}/$name"
done

plog "backup written to $dir (verify=$verify)"
say "Backup written: $dir"
say "  $(cut -d' ' -f1 <<<"$(du -sh "$dir")") on disk. pilot.env is included and is mode 600. It is not printed."
