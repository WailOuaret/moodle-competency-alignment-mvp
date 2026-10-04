#!/usr/bin/env bash
# Write PILOT_RECORD.json: the moment the pilot starts and exactly what is running. It holds no secret.
# Do this once, after clear-test-data.sh and the final healthcheck, immediately before the first
# teacher is invited. Everything the study later reports about "the system" is traceable to it.
#
#   scripts/record-pilot-start.sh [--force]
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

out="${PILOT_HOME:-$PILOT_DIR}/PILOT_RECORD.json"
if [ -e "$out" ] && [ "${1:-}" != "--force" ]; then die "$out exists. The start of a pilot is recorded once. --force overwrites it."; fi

"$(dirname "$0")/healthcheck.sh" --quiet || die "the pilot is not healthy; record the start only when it is"
rows="$(compose exec -T -u www-data moodle php /opt/pilot/provision/clear_test_data.php --count | python3 -c 'import json,sys; d=json.load(sys.stdin)["local_compalign rows"]; print(sum(d.values()))')"
[ "$rows" = "0" ] || die "the plugin tables hold $rows rows. Run scripts/clear-test-data.sh --delete first."

report="$(compose exec -T -u www-data moodle php /opt/pilot/provision/report.php)"
ids="$(compose images --format json 2>/dev/null || true)"

REPORT="$report" IMAGES="$ids" \
GIT_COMMIT="$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)" \
GIT_BRANCH="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)" \
GIT_DIRTY="$(git -C "$REPO_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')" \
ENGINE_HASH="$(cd "$REPO_DIR" && find src/moodle_competency -name '*.py' -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)" \
COMPETENCIES_HASH="$(sha256sum "$REPO_DIR/data/processed/competencies.jsonl" | cut -d' ' -f1)" \
BACKEND="$(read_env ALIGNMENT_BACKEND)" MODEL="$(read_env GEMINI_MODEL)" ALIGN_MODEL="$(read_env ALIGNMENT_MODEL)" \
IMAGE_TAG="$(read_env PILOT_IMAGE_TAG)" DOCKER="$(docker --version)" \
python3 - "$out" <<'PY'
import json, os, sys
report = json.loads(os.environ["REPORT"])
record = {
    "pilot_start_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "note": "Everything below was true at the moment the pilot started. It holds no secret.",
    "git": {"commit": os.environ["GIT_COMMIT"], "branch": os.environ["GIT_BRANCH"], "uncommitted_files": int(os.environ["GIT_DIRTY"])},
    "engine_source_sha256": os.environ["ENGINE_HASH"],
    "competencies_jsonl_sha256": os.environ["COMPETENCIES_HASH"],
    "image_tag": os.environ["IMAGE_TAG"],
    "docker": os.environ["DOCKER"],
    "model": {"backend": os.environ["BACKEND"], "gemini_model": os.environ["MODEL"] or "(engine default)", "service_model_override": os.environ["ALIGN_MODEL"] or "(none)"},
    "moodle": report["moodle"],
    "plugin": report["plugin"],
    "plugin_config": {k: v for k, v in report["plugin_config"].items() if k != "token_set"},
    "framework": report["framework"],
    "course": report["course"],
    "teacher_accounts": report["teacher_accounts"],
    "top_k": 5,
    "write_back": "off",
    "plugin_rows_at_start": 0,
}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(record, fh, indent=2)
    fh.write("\n")
PY
chmod 600 "$out"
plog "pilot start recorded at $out"
say "Pilot start recorded in $out"
