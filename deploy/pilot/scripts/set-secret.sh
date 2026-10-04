#!/usr/bin/env bash
# Set one value in the env file without it appearing on a command line, in shell history, or on screen.
#
#   scripts/set-secret.sh GEMINI_API_KEY      prompts silently
#   scripts/set-secret.sh GEMINI_API_KEY --clear   removes the value
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

name="${1:-}"
[[ "$name" =~ ^[A-Z][A-Z0-9_]*$ ]] || die "usage: set-secret.sh NAME [--clear]"
grep -q "^$name=" "$PILOT_ENV_FILE" || die "$name is not a setting in $PILOT_ENV_FILE"

if [ "${2:-}" = "--clear" ]; then
    value=""
else
    [ -t 0 ] || die "this reads from the terminal so the value is never in a pipe or a file; run it interactively"
    read -rsp "Value for $name (not shown): " value
    echo
    [ -n "$value" ] || die "empty value; use --clear to remove one"
    [[ "$value" != *[[:space:]\"\'\$\#\\]* ]] || die "the value has a space, quote, dollar, hash or backslash, which an env file cannot hold safely"
fi

VALUE="$value" python3 - "$PILOT_ENV_FILE" "$name" <<'PY'
import os, sys
path, name = sys.argv[1:3]
value = os.environ["VALUE"]
lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
out = [f"{name}={value}\n" if line.startswith(name + "=") else line for line in lines]
with open(path, "w", encoding="utf-8") as fh:
    fh.writelines(out)
PY
chmod 600 "$PILOT_ENV_FILE"
plog "$name updated in the env file (value not logged)"
say "$name updated. Recreate the container that uses it: scripts/compose.sh up -d"
