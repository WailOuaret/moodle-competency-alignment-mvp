#!/usr/bin/env bash
# Empty the plugin's tables (analyses, suggestions, evidence, reviews) so that nothing saved while the
# site was being tested is mixed with the teachers' decisions. Run it on the day the pilot starts,
# before the pilot start is recorded. It touches those four tables only: not accounts, not the
# course, not Moodle's own competency links.
#
#   scripts/clear-test-data.sh            shows what would be deleted
#   scripts/clear-test-data.sh --delete   takes a backup, then deletes (asks you to type a confirmation)
set -euo pipefail
. "$(dirname "$0")/_lib.sh"
require_env_file

compose exec -T -u www-data moodle php /opt/pilot/provision/clear_test_data.php --count
[ "${1:-}" = "--delete" ] || { say "Nothing deleted. Run with --delete to remove these rows."; exit 0; }

printf 'Type DELETE-PILOT-TEST-DATA to delete the rows above: '
read -r answer
[ "$answer" = "DELETE-PILOT-TEST-DATA" ] || die "not confirmed; nothing deleted"
"$(dirname "$0")/backup.sh" --label before-clear-test-data
compose exec -T -u www-data moodle php /opt/pilot/provision/clear_test_data.php --confirm=DELETE-PILOT-TEST-DATA
plog "plugin test data cleared (backup taken first)"
