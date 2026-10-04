#!/usr/bin/env bash
# Deploy the code that is currently in the repository directory: back up, build new images, restart,
# check. Run it only after the new code has reached the server (see the VPS guide: git pull of an
# approved branch, or an rsync of the private pilot build).
#
#   scripts/update.sh [--tag NAME]
#
# What happens, in order:
#   1. the env file must be complete, and the pilot must be healthy now
#   2. a labelled backup is taken (before-update)
#   3. the running images are kept under the tag they have now, so rollback.sh can return to them
#   4. new images are built under a new tag and the containers are recreated
#   5. the healthcheck runs. If it fails the script says so and stops. It does not roll back by itself:
#      a database upgrade cannot be undone by starting old code. Use scripts/rollback.sh.
#
# Moodle upgrades its database on start-up when the plugin's version number is higher.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_real_env

tag=""
while [ $# -gt 0 ]; do
    case "$1" in
        --tag) tag="$2"; shift 2 ;;
        *) die "unknown option $1" ;;
    esac
done
commit="$(git -C "$REPO_DIR" rev-parse --short=12 HEAD 2>/dev/null || true)"
tag="${tag:-${commit:+g$commit}}"
tag="${tag:-t$(date -u +%Y%m%d%H%M%S)}"
[[ "$tag" =~ ^[A-Za-z0-9_.-]+$ ]] || die "the tag may only hold letters, digits, . _ -"

current="$(read_env PILOT_IMAGE_TAG || echo pilot)"
[ "$tag" != "$current" ] || die "the images already carry the tag $tag. Pass --tag NAME for a new one."

say "Checking the pilot is healthy before changing anything..."
"$(dirname "$0")/healthcheck.sh" --quiet || die "the pilot is not healthy now. Fix that first, or restore, before updating."

releases="${PILOT_HOME:-$PILOT_DIR}/releases"; mkdir -p "$releases"
say "Backing up..."
"$(dirname "$0")/backup.sh" --label before-update
backup="$(ls -1d "$PILOT_BACKUP_DIR"/*-before-update | sort | tail -n 1)"

cat >"$releases/previous.json" <<JSON
{"image_tag": "$current", "backup": "$backup", "recorded_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "git_commit": "$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"}
JSON
chmod 600 "$releases/previous.json"

say "Building images tagged $tag..."
PILOT_IMAGE_TAG="$tag" compose build
python3 - "$PILOT_ENV_FILE" "$tag" <<'PY'
import sys
path, tag = sys.argv[1:3]
lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
open(path, "w", encoding="utf-8").writelines(
    [f"PILOT_IMAGE_TAG={tag}\n" if l.startswith("PILOT_IMAGE_TAG=") else l for l in lines])
PY
chmod 600 "$PILOT_ENV_FILE"

say "Recreating the containers..."
compose up -d
plog "updated from image tag $current to $tag (backup $backup)"

say "Waiting for Moodle (an upgrade can take a few minutes)..."
for _ in $(seq 1 90); do
    state="$(compose ps --format '{{.Health}}' moodle | head -n 1)"
    [ "$state" = "healthy" ] && break
    sleep 5
done
if "$(dirname "$0")/healthcheck.sh"; then
    cat >"$releases/current.json" <<JSON
{"image_tag": "$tag", "updated_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "git_commit": "$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"}
JSON
    say "Updated to $tag. The previous images ($current) and the backup are kept for scripts/rollback.sh."
else
    say ""
    say "The new version did not pass the healthcheck. Nothing was rolled back."
    say "Look at: scripts/compose.sh logs --since 15m moodle"
    say "To go back: scripts/rollback.sh --yes-replace-live-data"
    exit 1
fi
