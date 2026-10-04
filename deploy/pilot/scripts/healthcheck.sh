#!/usr/bin/env bash
# Is the pilot healthy? Exit 0 if every check passes, 1 if any fails.
#
#   scripts/healthcheck.sh               the checks that are cheap enough to run every few minutes
#   scripts/healthcheck.sh --readiness   also the host and public checks to pass BEFORE any teacher is invited
#   scripts/healthcheck.sh --quiet       print only failures
#
# It never prints a secret. It reports whether one is set.
set -uo pipefail
. "$(dirname "$0")/_lib.sh"

readiness=0; quiet=0
for a in "$@"; do
    case "$a" in
        --readiness) readiness=1 ;;
        --quiet) quiet=1 ;;
        *) die "unknown option $a" ;;
    esac
done

failed=0
pass() { [ "$quiet" = 1 ] || printf 'PASS  %s\n' "$1${2:+ ($2)}"; }
fail() { printf 'FAIL  %s\n' "$1${2:+ ($2)}"; failed=1; }
warn() { printf 'WARN  %s\n' "$1${2:+ ($2)}"; }
check() { # name, command...
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then pass "$name"; else fail "$name"; fi
}

[ -f "$PILOT_ENV_FILE" ] || { fail "env file exists" "$PILOT_ENV_FILE"; exit 1; }
[ "$(stat -c %a "$PILOT_ENV_FILE")" = "600" ] && pass "env file is private (mode 600)" || fail "env file is private (mode 600)"

# ---- containers ----
for svc in db alignment-api moodle moodle-cron; do
    state="$(compose ps --format '{{.State}} {{.Health}}' "$svc" 2>/dev/null | head -n 1)"
    case "$state" in
        "running healthy"|"running ") pass "container $svc" "$state" ;;
        *) fail "container $svc" "${state:-not found}" ;;
    esac
done

# ---- the site, as the host's reverse proxy sees it ----
port="$(read_env MOODLE_HOST_PORT || echo 8080)"
code="$(curl -s -o /dev/null -m 15 -w '%{http_code}' "http://127.0.0.1:$port/login/index.php" || true)"
case "$code" in 200|301|302|303) pass "Moodle answers on 127.0.0.1:$port" "HTTP $code" ;; *) fail "Moodle answers on 127.0.0.1:$port" "HTTP ${code:-none}" ;; esac

# ---- the application's own checks (settings, cron, service connection) ----
report="$(compose exec -T -u www-data moodle php /opt/pilot/provision/report.php --check 2>/dev/null)"; rc=$?
if [ -z "$report" ]; then
    fail "application report" "could not run"
else
    printf '%s' "$report" | python3 -c '
import json, sys
quiet = sys.argv[1] == "1"
data = json.load(sys.stdin)
for c in data["checks"]:
    if c["passed"]:
        if not quiet: print("PASS  " + c["check"] + (" (" + c["detail"] + ")" if c["detail"] else ""))
    else:
        print("FAIL  " + c["check"] + (" (" + c["detail"] + ")" if c["detail"] else ""))
' "$quiet"
    [ "$rc" = 0 ] || failed=1
fi

# ---- disk ----
used="$(df --output=pcent / | tail -n 1 | tr -dc 0-9)"
if [ "${used:-100}" -ge 90 ]; then fail "disk space" "root is ${used}% full"; elif [ "${used:-100}" -ge 80 ]; then warn "disk space" "root is ${used}% full"; else pass "disk space" "${used}% used"; fi

if [ "$readiness" = 1 ]; then
    echo "--- readiness: run before any teacher is invited ---"
    wwwroot="$(read_env MOODLE_WWWROOT)"; host="${wwwroot#*://}"; host="${host%%/*}"

    [ "$(read_env ALIGNMENT_BACKEND)" != "mock" ] && pass "model backend is not the mock" "$(read_env ALIGNMENT_BACKEND)" || fail "model backend is not the mock" "mock output must never be shown to teachers"
    [ -n "$(read_env GEMINI_API_KEY)" ] && pass "model key is set (value not shown)" || fail "model key is set" "scripts/set-secret.sh GEMINI_API_KEY"
    ! grep -Eq 'CHANGE_ME|pilot\.example\.org' "$PILOT_ENV_FILE" && pass "no placeholder left in the env file" || fail "no placeholder left in the env file"

    case "$wwwroot" in
        https://*)
            pass "site address uses https" "$wwwroot"
            pcode="$(curl -s -o /dev/null -m 20 -w '%{http_code}' "$wwwroot/login/index.php" || true)"
            case "$pcode" in 200|303) pass "public HTTPS answers with a valid certificate" "HTTP $pcode" ;; *) fail "public HTTPS answers with a valid certificate" "HTTP ${pcode:-none}" ;; esac
            expiry="$(echo | openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)"
            if [ -n "$expiry" ]; then
                days=$(( ( $(date -d "$expiry" +%s) - $(date +%s) ) / 86400 ))
                [ "$days" -ge 14 ] && pass "certificate lifetime" "$days days left" || fail "certificate lifetime" "$days days left"
            else
                fail "certificate lifetime" "could not read the certificate"
            fi
            hcode="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "http://$host/" || true)"
            case "$hcode" in 301|302|308) pass "plain http redirects" "HTTP $hcode" ;; *) fail "plain http redirects to https" "HTTP ${hcode:-none}" ;; esac
            ;;
        *) fail "site address uses https" "$wwwroot" ;;
    esac

    # nothing but the web ports and ssh may listen on a public address
    if command -v ss >/dev/null; then
        exposed="$(ss -H -ltn | awk '{print $4}' | grep -Ev '^(127\.|\[::1\]|\[fe80)' | grep -E ':(5432|8001|'"$port"')$' || true)"
        [ -z "$exposed" ] && pass "5432, 8001 and Moodle's local port are not on a public address" || fail "a private port is on a public address" "$exposed"
    fi
    if command -v ufw >/dev/null && sudo -n true 2>/dev/null; then
        rules="$(sudo -n ufw status | grep -E '^[0-9]' | awk '{print $1}' | sort -u | tr '\n' ' ')"
        sudo -n ufw status | grep -q "Status: active" && pass "firewall is active" || fail "firewall is active"
        echo "$rules" | grep -Eq '(^| )(8001|5432)(/| )' && fail "firewall opens 8001 or 5432" "$rules" || pass "firewall does not open 8001 or 5432" "$rules"
    else
        warn "firewall" "cannot read ufw without sudo; check by hand: sudo ufw status verbose"
    fi
    systemctl is-enabled docker >/dev/null 2>&1 && pass "docker starts at boot" || warn "docker starts at boot" "could not confirm; systemctl is-enabled docker"

    latest="$(ls -1 "$PILOT_BACKUP_DIR" 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z' | sort | tail -n 1)"
    if [ -n "$latest" ]; then
        age=$(( ( $(date +%s) - $(stat -c %Y "$PILOT_BACKUP_DIR/$latest") ) / 3600 ))
        [ "$age" -le 26 ] && pass "a backup exists from the last 26 hours" "$latest" || fail "a backup exists from the last 26 hours" "newest is ${age}h old"
    else
        fail "a backup exists" "run scripts/backup.sh"
    fi

    if [ -f "$CREDENTIALS_FILE" ]; then
        [ "$(stat -c %a "$CREDENTIALS_FILE")" = "600" ] && pass "teacher credentials file is private (mode 600)" || fail "teacher credentials file is private (mode 600)"
        rows=$(( $(wc -l <"$CREDENTIALS_FILE") - 1 ))
        [ "$rows" -eq 7 ] && pass "credentials for 7 teachers" || fail "credentials for 7 teachers" "found $rows"
    else
        fail "teacher credentials file exists" "scripts/provision-teachers.sh"
    fi
    [ -f "${PILOT_HOME:-$PILOT_DIR}/PILOT_RECORD.json" ] && pass "pilot start is recorded" || warn "pilot start is recorded" "scripts/record-pilot-start.sh, on the day"
fi

if [ "$failed" = 0 ]; then
    [ "$quiet" = 1 ] || echo "HEALTHY"
    plog "healthcheck passed (readiness=$readiness)"
    exit 0
fi
echo "UNHEALTHY"
plog "healthcheck FAILED (readiness=$readiness)"
exit 1
