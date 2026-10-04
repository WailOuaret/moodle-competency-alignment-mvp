<?php
// Create the pilot's teacher accounts and enrol them in the pilot course.
//
//   php teachers.php --count=7 --credentials-to-stdout
//   php teachers.php --count=7 --credentials-to-stdout --rotate-existing
//
// teacher01 is the pseudonym T001, teacher02 is T002, and so on. The pseudonym is stored as the
// user's ID number. The names are "Teacher T001" and so on, and the addresses end in .invalid, which
// can never receive mail. Nothing here knows who the real person is.
//
// Each password is random (PHP's random_int, the operating system's CSPRNG), twenty characters, and
// must be changed at the first login. Passwords leave this script only on standard output, and only
// with --credentials-to-stdout, so the caller can write them to a private file. Progress goes to
// standard error and never contains a password.
//
// All accounts are created in one database transaction. If anything fails, none exists afterwards.

require(__DIR__ . '/_bootstrap.php');
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->dirroot . '/lib/enrollib.php');

[$options] = cli_get_params([
    'count' => 7,
    'credentials-to-stdout' => false,
    'rotate-existing' => false,
    'help' => false,
], ['h' => 'help']);

if ($options['help']) {
    echo "Usage: php teachers.php [--count=7] [--credentials-to-stdout] [--rotate-existing]\n";
    exit(0);
}

$count = (int) $options['count'];
if ($count < 1 || $count > 99) {
    pilot_say('teachers: --count must be between 1 and 99');
    exit(1);
}

$course = $DB->get_record('course', ['shortname' => 'COMPALIGN-PILOT']);
if (!$course) {
    pilot_say('teachers: the pilot course does not exist yet');
    exit(1);
}
$role = $DB->get_record('role', ['shortname' => 'editingteacher'], '*', MUST_EXIST);
$manual = enrol_get_plugin('manual');
$instance = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual'], '*', MUST_EXIST);

// Decide before changing anything.
$plan = [];
$existing = [];
for ($n = 1; $n <= $count; $n++) {
    $username = sprintf('teacher%02d', $n);
    $found = $DB->get_record('user', ['username' => $username, 'mnethostid' => $CFG->mnet_localhost_id, 'deleted' => 0]);
    $plan[$n] = $found ?: null;
    if ($found) {
        $existing[] = $username;
    }
}
if ($existing && !$options['rotate-existing']) {
    pilot_say('teachers: these accounts already exist: ' . implode(', ', $existing));
    pilot_say('teachers: nothing was changed. Use --rotate-existing to give them new passwords.');
    exit(3);
}

$rows = [];
$transaction = $DB->start_delegated_transaction();
for ($n = 1; $n <= $count; $n++) {
    $username = sprintf('teacher%02d', $n);
    $pseudonym = sprintf('T%03d', $n);

    $password = pilot_password();

    if ($plan[$n]) {
        $user = $plan[$n];
        update_internal_user_password($user, $password);
        user_update_user((object) ['id' => $user->id, 'idnumber' => $pseudonym, 'suspended' => 0], false, false);
        $action = 'rotated';
    } else {
        $userid = user_create_user((object) [
            'username' => $username,
            'password' => $password,
            'idnumber' => $pseudonym,
            'firstname' => 'Teacher',
            'lastname' => $pseudonym,
            'email' => $username . '@pilot.invalid',
            'auth' => 'manual',
            'confirmed' => 1,
            'mnethostid' => $CFG->mnet_localhost_id,
            'lang' => 'en',
            'timezone' => '99',
            'calendartype' => 'gregorian',
        ], true, false);
        $user = $DB->get_record('user', ['id' => $userid], '*', MUST_EXIST);
        $action = 'created';
    }

    set_user_preference('auth_forcepasswordchange', 1, $user->id);
    $manual->enrol_user($instance, $user->id, $role->id, 0, 0, ENROL_USER_ACTIVE);

    $rows[] = [$pseudonym, $username, $password, $CFG->wwwroot . '/login/index.php', 'yes', gmdate('Y-m-d\TH:i:s\Z')];
    pilot_say(sprintf('teachers: %s %s (%s), Teacher role in %s', $action, $username, $pseudonym, $course->shortname));
}
$transaction->allow_commit();

if ($options['credentials-to-stdout']) {
    $out = fopen('php://stdout', 'w');
    fputcsv($out, ['pseudonym', 'username', 'password', 'login_url', 'must_change_password', 'issued_utc'], ',', '"', '');
    foreach ($rows as $row) {
        fputcsv($out, $row, ',', '"', '');
    }
    fclose($out);
}
pilot_say('teachers: ' . count($rows) . ' account(s) ready. Passwords were not printed.');
