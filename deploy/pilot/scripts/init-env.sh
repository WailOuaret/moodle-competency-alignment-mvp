#!/usr/bin/env bash
# Create the pilot's env file from .env.example, with freshly generated secrets.
#
#   scripts/init-env.sh            create the env file (refuses to overwrite one)
#
# The generated values (database password, Moodle administrator password, service token) come from
# Python's `secrets` module, which uses the operating system's CSPRNG. They are written only to the
# env file, which is created owner-only. Nothing is printed except the file's path. The Gemini
# key is not generated: add it yourself with scripts/set-secret.sh GEMINI_API_KEY.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"

[ ! -e "$PILOT_ENV_FILE" ] || die "$PILOT_ENV_FILE already exists. Edit it, or move it away first."
mkdir -p "$(dirname "$PILOT_ENV_FILE")"
chmod 700 "$PILOT_PRIVATE_DIR" 2>/dev/null || true

private_file "$PILOT_ENV_FILE"
python3 - "$PILOT_DIR/.env.example" "$PILOT_ENV_FILE" <<'PY'
import secrets, string, sys

src, dst = sys.argv[1:3]

def moodle_password() -> str:
    # 28 characters, with at least three of each kind Moodle's policy asks for. No quote, space,
    # dollar, hash or backslash, so the value is safe in an env file and on a command line.
    sets = [string.ascii_uppercase, string.ascii_lowercase, string.digits, "-_.+=@"]
    chars = [secrets.choice(s) for s in sets for _ in range(3)]
    pool = "".join(sets)
    chars += [secrets.choice(pool) for _ in range(28 - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)

generated = {
    "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
    "MOODLE_ADMIN_PASSWORD": moodle_password(),
    "ALIGNMENT_SERVICE_TOKEN": secrets.token_urlsafe(48),
}
lines = []
for line in open(src, encoding="utf-8"):
    name = line.split("=", 1)[0]
    if name in generated and "CHANGE_ME" in line:
        line = f"{name}={generated[name]}\n"
    lines.append(line)
with open(dst, "w", encoding="utf-8") as out:
    out.writelines(lines)
PY
chmod 600 "$PILOT_ENV_FILE"
plog "env file created at $PILOT_ENV_FILE"
say "Created $PILOT_ENV_FILE (mode 600) with generated secrets. Nothing was printed."
say "Next: set MOODLE_WWWROOT and PILOT_SUBNET/ALIGNMENT_IP for your host, and add the model key with"
say "      scripts/set-secret.sh GEMINI_API_KEY    (only when you are ready for the one authorised live test)"
