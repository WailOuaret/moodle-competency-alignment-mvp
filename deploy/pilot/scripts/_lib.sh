# Shared helpers for the pilot scripts. Sourced, never run.
#
# Where things live. Locally, everything sits next to docker-compose.yml. On the server set
# PILOT_HOME (for example /opt/compalign-pilot) and the private files, backups and logs go
# under it instead:
#
#   $PILOT_HOME/private/pilot.env                  the env file (secrets), chmod 600
#   $PILOT_HOME/private/teacher_credentials.csv    teacher passwords, chmod 600
#   $PILOT_HOME/backups/                           database and file backups
#   $PILOT_HOME/logs/pilot.log                     what these scripts did (no secrets)
#
# Each can also be set on its own: PILOT_ENV_FILE, PILOT_PRIVATE_DIR, PILOT_BACKUP_DIR, PILOT_LOG_DIR.

PILOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "$PILOT_DIR/../.." && pwd)"

if [ -n "${PILOT_HOME:-}" ]; then
    PILOT_PRIVATE_DIR="${PILOT_PRIVATE_DIR:-$PILOT_HOME/private}"
    PILOT_ENV_FILE="${PILOT_ENV_FILE:-$PILOT_PRIVATE_DIR/pilot.env}"
    PILOT_BACKUP_DIR="${PILOT_BACKUP_DIR:-$PILOT_HOME/backups}"
    PILOT_LOG_DIR="${PILOT_LOG_DIR:-$PILOT_HOME/logs}"
else
    PILOT_PRIVATE_DIR="${PILOT_PRIVATE_DIR:-$PILOT_DIR/private}"
    PILOT_ENV_FILE="${PILOT_ENV_FILE:-$PILOT_DIR/.env}"
    PILOT_BACKUP_DIR="${PILOT_BACKUP_DIR:-$PILOT_DIR/backups}"
    PILOT_LOG_DIR="${PILOT_LOG_DIR:-$PILOT_DIR/logs}"
fi
CREDENTIALS_FILE="$PILOT_PRIVATE_DIR/teacher_credentials.csv"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

# Append a line to the pilot log, rotating it at 5 MB (five old files kept). Never pass a secret here.
plog() {
    mkdir -p "$PILOT_LOG_DIR"
    local file="$PILOT_LOG_DIR/pilot.log"
    if [ -f "$file" ] && [ "$(stat -c %s "$file")" -gt 5242880 ]; then
        for i in 4 3 2 1; do [ -f "$file.$i" ] && mv "$file.$i" "$file.$((i + 1))"; done
        mv "$file" "$file.1"
    fi
    printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(basename "$0")" "$*" >>"$file"
}

# Value of VAR from the env file. Prints nothing if it is absent. Not for display of secrets.
read_env() {
    [ -f "$PILOT_ENV_FILE" ] || return 1
    grep -E "^$1=" "$PILOT_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

require_env_file() {
    [ -f "$PILOT_ENV_FILE" ] || die "no env file at $PILOT_ENV_FILE (run scripts/init-env.sh)"
    local mode
    mode="$(stat -c %a "$PILOT_ENV_FILE")"
    [ "$mode" = "600" ] || die "$PILOT_ENV_FILE has mode $mode. It holds secrets: chmod 600 it."
}

# Refuse to continue while a placeholder is still in the env file.
require_real_env() {
    require_env_file
    if grep -Eq '^[A-Z_]+=.*(CHANGE_ME|pilot\.example\.org)' "$PILOT_ENV_FILE"; then
        grep -En '^[A-Z_]+=.*(CHANGE_ME|pilot\.example\.org)' "$PILOT_ENV_FILE" | cut -d= -f1 | sed 's/^/  still a placeholder: /' >&2
        die "fill in the placeholders in $PILOT_ENV_FILE first"
    fi
}

compose() {
    require_env_file
    local project
    project="$(read_env COMPOSE_PROJECT_NAME || true)"
    docker compose -p "${project:-compalign_pilot}" --project-directory "$PILOT_DIR" \
        --env-file "$PILOT_ENV_FILE" -f "$PILOT_DIR/docker-compose.yml" "$@"
}

# Run a provisioning script inside the running Moodle container, as www-data.
moodle_php() {
    compose exec -T -u www-data moodle php "$@"
}

# A private file: owner-only from the moment it is created.
private_file() {
    ( umask 077; : >"$1" )
    chmod 600 "$1"
}
