#!/usr/bin/env bash
# Print the nginx configuration for the pilot's host name. Installs nothing and needs no sudo.
#
#   scripts/render-nginx.sh http       step 1: port 80 only, for obtaining the certificate
#   scripts/render-nginx.sh full       step 2: http redirect + https reverse proxy
#   scripts/render-nginx.sh snippet    the shared proxy settings
#
# Review the output, then install it yourself (see docs/VPS_DEPLOYMENT_GUIDE.md). The host name and the
# local port come from the env file.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

wwwroot="$(read_env MOODLE_WWWROOT)"
host="${wwwroot#*://}"; host="${host%%/*}"; host="${host%%:*}"
[[ "$host" =~ ^[A-Za-z0-9.-]+$ ]] || die "MOODLE_WWWROOT has no usable host name: $wwwroot"
[ "$host" != "pilot.example.org" ] || die "MOODLE_WWWROOT is still the placeholder"
port="$(read_env MOODLE_HOST_PORT || echo 8080)"

case "${1:-}" in
    http)    template="$PILOT_DIR/nginx/compalign-pilot-http.conf.template" ;;
    full)    template="$PILOT_DIR/nginx/compalign-pilot.conf.template" ;;
    snippet) cat "$PILOT_DIR/nginx/compalign-pilot-proxy.snippet"; exit 0 ;;
    *) die "usage: render-nginx.sh http|full|snippet" ;;
esac
PILOT_HOST="$host" MOODLE_HOST_PORT="$port" envsubst '${PILOT_HOST} ${MOODLE_HOST_PORT}' <"$template"
