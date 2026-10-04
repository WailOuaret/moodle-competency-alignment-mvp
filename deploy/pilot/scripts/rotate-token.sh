#!/usr/bin/env bash
# Replace the shared secret between Moodle and the alignment service.
#
#   scripts/rotate-token.sh
#
# A new token is generated (CSPRNG) and written to the env file. Both containers are recreated: the
# service starts demanding the new token, and Moodle re-applies it to the plugin's encrypted setting on
# start-up. Nothing is printed. Analyses that are running at that moment fail and can be repeated.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

python3 - "$PILOT_ENV_FILE" <<'PY'
import secrets, sys
path = sys.argv[1]
token = secrets.token_urlsafe(48)
lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
out = [f"ALIGNMENT_SERVICE_TOKEN={token}\n" if l.startswith("ALIGNMENT_SERVICE_TOKEN=") else l for l in lines]
open(path, "w", encoding="utf-8").writelines(out)
PY
chmod 600 "$PILOT_ENV_FILE"
compose up -d alignment-api moodle
plog "service token rotated (value not logged)"
say "Token rotated. Moodle re-applies it when it restarts: wait for 'moodle' to be healthy, then run scripts/healthcheck.sh."
