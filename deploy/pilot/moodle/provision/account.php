<?php
// Look at or change one pilot teacher account.
//
//   php account.php status [--user=teacher03]
//   php account.php suspend --user=teacher03
//   php account.php unsuspend --user=teacher03
//   php account.php reset-password --user=teacher03 --credentials-to-stdout
//
// Only accounts named teacherNN, the ones teachers.php makes, can be changed here. A suspended
// user is signed out at once and cannot log in. Nothing is ever deleted: the reviews a teacher saved
// stay attached to the account, and the study data is not affected.

require(__DIR__ . '/_bootstrap.php');
require_once($CFG->dirroot . '/user/lib.php');

$action = $argv[1] ?? '';
[$options] = cli_get_params(['user' => '', 'credentials-to-stdout' => false], []);

if (!in_array($action, ['status', 'suspend', 'unsuspend', 'reset-password'], true)) {
    pilot_say('usage: account.php status|suspend|unsuspend|reset-password [--user=teacherNN] [--credentials-to-stdout]');
    exit(1);
}
if ($options['user'] !== '' && !preg_match('/^teacher\d{2}$/', $options['user'])) {
    pilot_say('account: only accounts named teacher01, teacher02, ... can be managed here');
    exit(1);
}

$sql = "SELECT * FROM {user} WHERE deleted = 0 AND username " . $DB->sql_like('username', ':pattern', false);
$users = $DB->get_records_sql($sql . ' ORDER BY username', ['pattern' => 'teacher__']);
$users = array_filter($users, static fn($u) => preg_match('/^teacher\d{2}$/', $u->username) === 1);

if ($action === 'status') {
    printf("%-10s %-10s %-10s %-16s %s\n", 'username', 'pseudonym', 'status', 'last access (UTC)', 'must change password');
    foreach ($users as $u) {
        if ($options['user'] !== '' && $u->username !== $options['user']) {
            continue;
        }
        printf(
            "%-10s %-10s %-10s %-16s %s\n",
            $u->username,
            $u->idnumber,
            $u->suspended ? 'suspended' : 'active',
            $u->lastaccess ? gmdate('Y-m-d H:i', $u->lastaccess) : 'never',
            get_user_preferences('auth_forcepasswordchange', 0, $u->id) ? 'yes' : 'no'
        );
    }
    exit(0);
}

$target = null;
foreach ($users as $u) {
    if ($u->username === $options['user']) {
        $target = $u;
    }
}
if (!$target) {
    pilot_say('account: no such pilot account: ' . ($options['user'] ?: '(no --user given)'));
    exit(1);
}

switch ($action) {
    case 'suspend':
        user_update_user((object) ['id' => $target->id, 'suspended' => 1], false, false);
        \core\session\manager::destroy_user_sessions($target->id);
        pilot_say("account: {$target->username} suspended and signed out");
        break;
    case 'unsuspend':
        user_update_user((object) ['id' => $target->id, 'suspended' => 0], false, false);
        pilot_say("account: {$target->username} can log in again");
        break;
    case 'reset-password':
        $password = pilot_password();
        update_internal_user_password($target, $password);
        set_user_preference('auth_forcepasswordchange', 1, $target->id);
        \core\session\manager::destroy_user_sessions($target->id);
        if ($options['credentials-to-stdout']) {
            $out = fopen('php://stdout', 'w');
            fputcsv($out, [$target->idnumber, $target->username, $password, $CFG->wwwroot . '/login/index.php', 'yes', gmdate('Y-m-d\TH:i:s\Z')], ',', '"', '');
            fclose($out);
        }
        pilot_say("account: {$target->username} has a new password and must change it at the next login. It was not printed.");
        break;
}
