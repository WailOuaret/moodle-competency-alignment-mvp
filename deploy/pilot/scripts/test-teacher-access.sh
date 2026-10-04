#!/usr/bin/env bash
# Check every account in the credentials file: the password in the file works, the account is
# active, it is a Teacher of the pilot course and nothing else, and it can use the plugin but not
# write competency links or see other teachers' reviews. Prints a PASS or FAIL line per pseudonym.
# Passwords are read from the private file and never printed. No session is created, so the
# teachers' accounts are not touched: they still have to change their password at first login.
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file
[ -f "$CREDENTIALS_FILE" ] || die "no credentials file at $CREDENTIALS_FILE"
[ "$(stat -c %a "$CREDENTIALS_FILE")" = "600" ] || die "$CREDENTIALS_FILE must be mode 600"
compose exec -T -u www-data moodle php /opt/pilot/provision/access_test.php <"$CREDENTIALS_FILE"
