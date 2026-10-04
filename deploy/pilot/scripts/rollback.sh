#!/usr/bin/env bash
# Go back to the version that ran before the last update.sh.
#
#   scripts/rollback.sh --yes-replace-live-data            old images AND the data from the pre-update backup
#   scripts/rollback.sh --images-only                      old images only
#
# --images-only is only safe when the update did not change the database. A plugin upgrade does, and
# Moodle refuses to start code older than its database. When in doubt use the default, which restores
# the backup taken just before the update. Anything teachers saved since then is lost: tell them.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

releases="${PILOT_HOME:-$PILOT_DIR}/releases"
[ -f "$releases/previous.json" ] || die "no previous release is recorded ($releases/previous.json)"
prev_tag="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_tag"])' "$releases/previous.json")"
prev_backup="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["backup"])' "$releases/previous.json")"
docker image inspect "compalign-moodle:$prev_tag" >/dev/null 2>&1 || die "the images tagged $prev_tag are gone from this host. Rebuild that version from its commit instead."
docker image inspect "compalign-alignment:$prev_tag" >/dev/null 2>&1 || die "the alignment image tagged $prev_tag is gone from this host."

mode="${1:-}"
case "$mode" in
    --images-only) ;;
    --yes-replace-live-data) [ -d "$prev_backup" ] || die "the pre-update backup $prev_backup is missing" ;;
    *) die "usage: rollback.sh --yes-replace-live-data | --images-only" ;;
esac

python3 - "$PILOT_ENV_FILE" "$prev_tag" <<'PY'
import sys
path, tag = sys.argv[1:3]
lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
open(path, "w", encoding="utf-8").writelines(
    [f"PILOT_IMAGE_TAG={tag}\n" if l.startswith("PILOT_IMAGE_TAG=") else l for l in lines])
PY
chmod 600 "$PILOT_ENV_FILE"

if [ "$mode" = "--yes-replace-live-data" ]; then
    "$(dirname "$0")/restore.sh" "$prev_backup" --yes-replace-live-data
else
    compose up -d
fi
plog "rolled back to image tag $prev_tag ($mode)"
say "Rolled back to $prev_tag. Run scripts/healthcheck.sh."
