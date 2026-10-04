#!/bin/sh
# Moodle's cron, as a loop.
#
# Each run of cron.php does its work and then stays alive for about three minutes (Moodle's "keep
# alive" setting) picking up new tasks, such as a teacher's analysis request, within seconds. When it
# ends, the next one starts after a short pause. Whatever happens, a queued task waits at most
# CRON_INTERVAL_SECONDS (default 20) for a free run, which is more than the once-a-minute the pilot
# needs.
#
# Output is kept short: one line per run, plus any line that mentions a failure.
set -u

pause="${CRON_INTERVAL_SECONDS:-20}"
stopping=0
child=""
out="$(mktemp)"

stop() {
    stopping=1
    [ -n "$child" ] && kill -TERM "$child" 2>/dev/null
}
trap stop TERM INT

say() { printf '%s cron: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

say "loop started (pause ${pause}s between runs)"
while [ "$stopping" -eq 0 ]; do
    runuser -u www-data -- php /var/www/html/admin/cli/cron.php >"$out" 2>&1 &
    child=$!
    wait "$child"
    status=$?
    child=""
    say "run finished, exit $status"
    grep -Ei 'fail|exception|error|warning' "$out" | tail -n 20
    [ "$stopping" -eq 0 ] && sleep "$pause"
done
say "loop stopped"
