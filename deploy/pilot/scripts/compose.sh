#!/usr/bin/env bash
# docker compose for the pilot, with the right project, env file and compose file.
#   scripts/compose.sh ps
#   scripts/compose.sh up -d --build
#   scripts/compose.sh logs --since 10m moodle-cron
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
compose "$@"
