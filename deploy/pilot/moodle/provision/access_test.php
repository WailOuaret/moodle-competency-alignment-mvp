<?php
// Read the credentials CSV on standard input and check each account. Prints no password.
//
// Per account: the password works, the account is not suspended, it is enrolled in the pilot
// course with the Teacher role and no other role anywhere, it may view, analyse and review in the
// plugin, and it may not write back, see other teachers' reviews, or configure the site. The
// force-password-change flag must still be set, because nobody has logged in yet.
//
// Exit 0 only if every account passes.

require(__DIR__ . '/_bootstrap.php');

$course = $DB->get_record('course', ['shortname' => 'COMPALIGN-PILOT'], '*', MUST_EXIST);
$coursecontext = context_course::instance($course->id);
$systemcontext = context_system::instance();

$input = fopen('php://stdin', 'r');
$header = fgetcsv($input, 0, ',', '"', '');
if ($header === false || array_slice($header, 0, 3) !== ['pseudonym', 'username', 'password']) {
    pilot_say('access test: standard input is not a credentials CSV');
    exit(2);
}

$failed = 0;
$seen = 0;
while (($row = fgetcsv($input, 0, ',', '"', '')) !== false) {
    if (count($row) < 3) {
        continue;
    }
    [$pseudonym, $username, $password] = $row;
    $seen++;
    $problems = [];

    $reason = null;
    $user = authenticate_user_login($username, $password, true, $reason);
    if (!$user) {
        $problems[] = 'password rejected (reason ' . $reason . ')';
    } else {
        $record = $DB->get_record('user', ['id' => $user->id], '*', MUST_EXIST);
        if ($record->idnumber !== $pseudonym) {
            $problems[] = 'idnumber is ' . $record->idnumber;
        }
        if ($record->suspended) {
            $problems[] = 'suspended';
        }
        if (!get_user_preferences('auth_forcepasswordchange', 0, $user->id)) {
            $problems[] = 'password change is not forced';
        }
        if (!is_enrolled($coursecontext, $user, '', true)) {
            $problems[] = 'not actively enrolled in the pilot course';
        }
        $roles = array_values(array_map(static fn($r) => $r->shortname, get_user_roles($coursecontext, $user->id, false)));
        if ($roles !== ['editingteacher']) {
            $problems[] = 'course roles: ' . implode(',', $roles);
        }
        if (get_user_roles($systemcontext, $user->id, false)) {
            $problems[] = 'has a system-wide role';
        }
        foreach (['local/compalign:view', 'local/compalign:analyse', 'local/compalign:review'] as $capability) {
            if (!has_capability($capability, $coursecontext, $user)) {
                $problems[] = 'lacks ' . $capability;
            }
        }
        foreach (['local/compalign:writeback' => $coursecontext, 'local/compalign:viewallreviews' => $systemcontext,
                  'moodle/site:config' => $systemcontext, 'moodle/user:create' => $systemcontext] as $capability => $context) {
            if (has_capability($capability, $context, $user)) {
                $problems[] = 'must not have ' . $capability;
            }
        }
    }

    if ($problems) {
        $failed++;
        echo "FAIL  $pseudonym  " . implode('; ', $problems) . PHP_EOL;
    } else {
        echo "PASS  $pseudonym  password works, Teacher in COMPALIGN-PILOT only, plugin access correct, no write-back" . PHP_EOL;
    }
}
echo ($failed === 0 && $seen > 0 ? "ALL $seen ACCOUNTS PASS" : "$failed OF $seen ACCOUNTS FAIL") . PHP_EOL;
exit($failed === 0 && $seen > 0 ? 0 : 1);
