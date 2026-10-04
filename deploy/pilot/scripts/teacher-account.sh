#!/usr/bin/env bash
# Look at or change one pilot teacher account.
#
#   scripts/teacher-account.sh status [teacher03]
#   scripts/teacher-account.sh suspend teacher03       cannot log in; signed out at once
#   scripts/teacher-account.sh unsuspend teacher03
#   scripts/teacher-account.sh reset-password teacher03    new random password, written to the credentials file
#
# Nothing is ever deleted. A password is never printed: reset-password replaces that teacher's row in
# the private credentials file, and you read it there.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

action="${1:-}"; user="${2:-}"
case "$action" in
    status)
        moodle_php /opt/pilot/provision/account.php status ${user:+--user="$user"} ;;
    suspend|unsuspend)
        [ -n "$user" ] || die "usage: teacher-account.sh $action teacherNN"
        moodle_php /opt/pilot/provision/account.php "$action" --user="$user"
        plog "$action $user" ;;
    reset-password)
        [ -n "$user" ] || die "usage: teacher-account.sh reset-password teacherNN"
        [ -f "$CREDENTIALS_FILE" ] || die "no credentials file at $CREDENTIALS_FILE to update"
        tmp="$(mktemp "$PILOT_PRIVATE_DIR/.row.XXXXXX")"; chmod 600 "$tmp"
        trap 'rm -f "$tmp"' EXIT
        moodle_php /opt/pilot/provision/account.php reset-password --user="$user" --credentials-to-stdout >"$tmp"
        python3 - "$CREDENTIALS_FILE" "$tmp" "$user" <<'PY'
import csv, os, sys
path, newrow, user = sys.argv[1:4]
rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
fresh = list(csv.reader(open(newrow, newline="", encoding="utf-8")))[0]
out = [rows[0]] + [fresh if r[1] == user else r for r in rows[1:]]
if not any(r[1] == user for r in rows[1:]):
    out.append(fresh)
tmp = path + ".new"
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
    csv.writer(fh, lineterminator="\n").writerows(out)
os.replace(tmp, path)
PY
        chmod 600 "$CREDENTIALS_FILE"
        plog "password reset for $user (value not logged)"
        say "New password for $user is in $CREDENTIALS_FILE. It was not printed." ;;
    *) die "usage: teacher-account.sh status|suspend|unsuspend|reset-password [teacherNN]" ;;
esac
