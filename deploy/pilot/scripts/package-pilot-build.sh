#!/usr/bin/env bash
# Build the private pilot build: the exact files the pilot's images need, from one commit, in one tarball.
#
#   scripts/package-pilot-build.sh [--allow-dirty]
#
# Writes dist/compalign-pilot-build-<commit>.tar.gz, a checksum and a file list. It makes no network
# connection and sends nothing anywhere. Read the file list before transferring the tarball.
# It is made from the files Git tracks at HEAD: nothing untracked, ignored or uncommitted is
# included, so no .env, no key, no notes, no VPS details.
#
# This is for the "RSYNC PRIVATE PILOT BUILD" option, used when the branch has not been pushed.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO"

paths=(
    deploy/pilot
    moodle-plugin/compalign
    service
    src/moodle_competency
    data/processed/competencies.jsonl
    docs/TEACHER_PILOT_GUIDE.md
    docs/PLUGIN_ADMIN_GUIDE.md
    docs/VPS_DEPLOYMENT_GUIDE.md
    docs/PILOT_OPERATIONS_RUNBOOK.md
    docs/PLUGIN_PACKAGING_GUIDE.md
    docs/TEACHER_PILOT_CHECKLIST.md
    docs/MOODLE_PLUGIN_ARCHITECTURE.md
    docs/MOODLE_PLUGIN_BROWSER_CHECKLIST.md
)
excludes=(':(exclude)moodle-plugin/compalign/tests')

if [ -n "$(git status --porcelain -- "${paths[@]}")" ] && [ "${1:-}" != "--allow-dirty" ]; then
    echo "error: uncommitted changes in files that go into the build. It is made from HEAD, so commit first." >&2
    git status --short -- "${paths[@]}" >&2
    exit 1
fi
for p in "${paths[@]}"; do
    git ls-files --error-unmatch -- "$p" >/dev/null 2>&1 || { echo "error: $p is not tracked by Git at HEAD" >&2; exit 1; }
done

commit="$(git rev-parse --short=12 HEAD)"
mkdir -p dist
out="dist/compalign-pilot-build-${commit}.tar.gz"
rm -f "$out" "$out.sha256" "dist/compalign-pilot-build-${commit}.files.txt"
git archive --format=tar.gz -o "$out" HEAD -- "${paths[@]}" "${excludes[@]}"

tar -tzf "$out" | grep -v '/$' >"dist/compalign-pilot-build-${commit}.files.txt"

private='(^|/)(\.env$|\.env\.[^e]|.*\.pem|.*\.key|id_(rsa|ed25519)|.*credentials.*|prombt\.md|wget-log)'
if grep -Eiq "$private" "dist/compalign-pilot-build-${commit}.files.txt"; then
    echo "error: the build contains a file that looks private:" >&2
    grep -Ei "$private" "dist/compalign-pilot-build-${commit}.files.txt" >&2
    rm -f "$out"; exit 1
fi
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
tar -xzf "$out" -C "$tmp"
# 32 characters or more: the placeholder in .env.example is shorter than a generated token.
if grep -rEl 'AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ALIGNMENT_SERVICE_TOKEN=[A-Za-z0-9_-]{32,}' "$tmp" >/dev/null 2>&1; then
    echo "error: the build contains text that looks like a key or a token:" >&2
    grep -rEl 'AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ALIGNMENT_SERVICE_TOKEN=[A-Za-z0-9_-]{32,}' "$tmp" >&2
    rm -f "$out"; exit 1
fi

( cd dist && sha256sum "$(basename "$out")" >"$(basename "$out").sha256" )

echo "Built $out"
echo "  commit:  $(git rev-parse HEAD)"
echo "  files:   $(wc -l <"dist/compalign-pilot-build-${commit}.files.txt")"
echo "  size:    $(du -h "$out" | cut -f1)"
echo "  sha256:  $(cut -d' ' -f1 "$out.sha256")"
echo
echo "Top-level content (full list: dist/compalign-pilot-build-${commit}.files.txt):"
cut -d/ -f1-2 "dist/compalign-pilot-build-${commit}.files.txt" | sort | uniq -c | sort -k2
