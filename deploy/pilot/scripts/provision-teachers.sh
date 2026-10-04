#!/usr/bin/env bash
# Create the seven pilot teacher accounts (teacher01..teacher07, pseudonyms T001..T007), enrol them
# in the pilot course, and write their passwords to the private credentials file.
#
#   scripts/provision-teachers.sh [--count 7] [--rotate-existing]
#
# The passwords are random, twenty characters, and each must be changed at the first login. They
# are written only to the credentials file (owner-only, never in Git) and are NOT printed here. To
# read them: cat that file yourself, on the server, when you hand them out.
#
# It refuses to run if the credentials file already exists. --rotate-existing gives every account a
# new password and moves the old file aside (mode 600) first.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

count=7; rotate=0
while [ $# -gt 0 ]; do
    case "$1" in
        --count) count="$2"; shift 2 ;;
        --rotate-existing) rotate=1; shift ;;
        *) die "unknown option $1" ;;
    esac
done
[[ "$count" =~ ^[0-9]+$ ]] || die "--count must be a number"

mkdir -p "$PILOT_PRIVATE_DIR"; chmod 700 "$PILOT_PRIVATE_DIR"
if [ -e "$CREDENTIALS_FILE" ] && [ "$rotate" = 0 ]; then
    die "$CREDENTIALS_FILE already exists. Passwords are not recreated by accident. Use --rotate-existing to issue new ones."
fi

tmp="$(mktemp "$PILOT_PRIVATE_DIR/.credentials.XXXXXX")"
chmod 600 "$tmp"
trap 'rm -f "$tmp"' EXIT

args=(--count="$count" --credentials-to-stdout)
[ "$rotate" = 1 ] && args+=(--rotate-existing)

# Progress goes to the terminal (it holds no password). The CSV goes straight into the private file.
moodle_php /opt/pilot/provision/teachers.php "${args[@]}" >"$tmp"

rows=$(( $(wc -l <"$tmp") - 1 ))
[ "$rows" -eq "$count" ] || die "expected $count credential rows, got $rows. Nothing was kept."

if [ -e "$CREDENTIALS_FILE" ]; then
    old="$CREDENTIALS_FILE.replaced-$(date -u +%Y%m%dT%H%M%SZ)"
    mv "$CREDENTIALS_FILE" "$old"; chmod 600 "$old"
    say "The previous credentials file was kept as $old (mode 600). Delete it once nobody needs it."
fi
mv "$tmp" "$CREDENTIALS_FILE"; trap - EXIT
chmod 600 "$CREDENTIALS_FILE"
plog "teacher accounts provisioned: $count (rotate=$rotate); credentials written to the private file"
say "Wrote $rows credentials to $CREDENTIALS_FILE (mode $(stat -c %a "$CREDENTIALS_FILE")). They were not printed."
