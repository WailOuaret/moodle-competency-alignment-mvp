#!/usr/bin/env bash
# Build the private plugin package: dist/local_compalign-<release>-pilot.zip
#
#   scripts/package-plugin.sh [--with-tests]
#
# The package is made from the files Git tracks at HEAD, so nothing untracked, ignored or
# uncommitted can get into it: not .env, not keys, not notes. Its top-level folder is `compalign`, which is what
# Moodle expects for a local plugin. Tests are left out unless --with-tests is given.
#
# This is a PRIVATE package for the pilot. PUBLIC DISTRIBUTION REQUIRES LICENSING/IP CONFIRMATION.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO"

with_tests=0
[ "${1:-}" = "--with-tests" ] && with_tests=1

plugin=moodle-plugin/compalign
release="$(sed -n "s/.*\$plugin->release = '\([^']*\)'.*/\1/p" "$plugin/version.php")"
[ -n "$release" ] || { echo "error: could not read the release from $plugin/version.php" >&2; exit 1; }

if [ -n "$(git status --porcelain -- "$plugin")" ]; then
    echo "error: $plugin has uncommitted changes. The package is made from HEAD, so commit them first." >&2
    git status --short -- "$plugin" >&2
    exit 1
fi

mkdir -p dist
out="dist/local_compalign-${release}-pilot.zip"
rm -f "$out" "$out.sha256"
excludes=()
[ "$with_tests" = 0 ] && excludes=(':(exclude)tests')
git archive --format=zip --prefix=compalign/ -o "$out" "HEAD:$plugin" -- . "${excludes[@]}"

listing="$(unzip -Z1 "$out")"

# Refuse anything that looks like a secret or a private file.
if grep -Eiq '(^|/)(\.env[^/]*|.*\.pem|.*\.key|id_(rsa|ed25519)[^/]*|.*credentials.*|.*secret.*|\.git/.*|.*wget-log.*)$' <<<"$listing"; then
    echo "error: the package contains a file that looks private:" >&2
    grep -Ei '(^|/)(\.env[^/]*|.*\.pem|.*\.key|id_(rsa|ed25519)[^/]*|.*credentials.*|.*secret.*|\.git/.*|.*wget-log.*)$' <<<"$listing" >&2
    rm -f "$out"; exit 1
fi
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
unzip -q "$out" -d "$tmp"
if grep -rEl 'AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ALIGNMENT_SERVICE_TOKEN=[A-Za-z0-9_-]{32,}' "$tmp" >/dev/null 2>&1; then
    echo "error: the package contains text that looks like a key or token:" >&2
    grep -rEl 'AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ALIGNMENT_SERVICE_TOKEN=[A-Za-z0-9_-]{32,}' "$tmp" >&2
    rm -f "$out"; exit 1
fi
# The plugin must be the single top-level folder, with version.php directly inside it.
[ "$(cut -d/ -f1 <<<"$listing" | sort -u)" = "compalign" ] || { echo "error: unexpected top-level entries" >&2; rm -f "$out"; exit 1; }
grep -qx 'compalign/version.php' <<<"$listing" || { echo "error: compalign/version.php is missing" >&2; rm -f "$out"; exit 1; }

# Every PHP file must at least parse, when PHP is available.
if command -v php >/dev/null; then
    find "$tmp/compalign" -name '*.php' -print0 | xargs -0 -n1 php -l >/dev/null
fi

( cd dist && sha256sum "$(basename "$out")" >"$(basename "$out").sha256" )
echo "Built $out"
echo "  files:   $(grep -vc '/$' <<<"$listing")"
echo "  size:    $(du -h "$out" | cut -f1)"
echo "  tests:   $([ "$with_tests" = 1 ] && echo included || echo excluded)"
echo "  sha256:  $(cut -d' ' -f1 "$out.sha256")"
echo "  commit:  $(git rev-parse --short=12 HEAD)"
