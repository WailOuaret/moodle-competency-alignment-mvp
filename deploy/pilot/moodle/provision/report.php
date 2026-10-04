<?php
// A read-only report on the state of the pilot site, as JSON on standard output.
//
//   php report.php            the whole report
//   php report.php --check    the same, and exit 1 if any check failed
//
// It reports whether a secret is set, never the secret.

require(__DIR__ . '/_bootstrap.php');

use core_competency\competency_framework;
use local_compalign\service\alignment_client;

[$options] = cli_get_params(['check' => false], []);

$checks = [];
$check = static function (string $name, bool $passed, string $detail = '') use (&$checks): void {
    $checks[] = ['check' => $name, 'passed' => $passed, 'detail' => $detail];
};

$plugin = core_plugin_manager::instance()->get_plugin_info('local_compalign');
$framework = competency_framework::get_record(['idnumber' => 'UTC_GI_MVP_2026']);
$course = $DB->get_record('course', ['shortname' => 'COMPALIGN-PILOT']);

$config = [
    'serviceurl' => (string) get_config('local_compalign', 'serviceurl'),
    'frameworkid' => (int) get_config('local_compalign', 'frameworkid'),
    'requesttimeout' => (int) get_config('local_compalign', 'requesttimeout'),
    'maxsuggestions' => (int) get_config('local_compalign', 'maxsuggestions'),
    'enablewriteback' => (bool) get_config('local_compalign', 'enablewriteback'),
    'token_set' => (string) get_config('local_compalign', 'servicetoken') !== '',
];

$teachers = 0;
$suspended = 0;
$enrolled = 0;
if ($course) {
    $context = context_course::instance($course->id);
    $enrolled = count(get_enrolled_users($context, '', 0, 'u.id'));
}
foreach ($DB->get_records_select('user', "deleted = 0 AND username LIKE 'teacher__'", [], '', 'id, username, suspended') as $u) {
    if (preg_match('/^teacher\d{2}$/', $u->username)) {
        $teachers++;
        $suspended += (int) $u->suspended;
    }
}

$byStatus = [];
foreach ($DB->get_records_sql('SELECT status, COUNT(1) AS n FROM {local_compalign_analysis} GROUP BY status') as $row) {
    $byStatus[$row->status] = (int) $row->n;
}

$lastcron = (int) get_config('tool_task', 'lastcronstart');
$connection = alignment_client::check_configured_connection();

$check('plugin installed', (bool) $plugin && $plugin->is_installed_and_upgraded(), $plugin ? $plugin->versiondb . '' : 'missing');
$check('framework present with 13 competencies', $framework !== false
    && $DB->count_records('competency', ['competencyframeworkid' => $framework->get('id')]) === 13);
$check('plugin points at the framework', $framework !== false && $config['frameworkid'] === (int) $framework->get('id'));
$check('pilot course present', (bool) $course);
$check('write-back is off', $config['enablewriteback'] === false);
$check('service token is set', $config['token_set']);
$check('service url is an http address on the private network', (bool) preg_match('#^http://\d+\.\d+\.\d+\.\d+$#', $config['serviceurl']));
$check('debug is off', (int) $CFG->debug === 0 && empty($CFG->debugdisplay));
$check('web cron is disabled', !empty($CFG->cronclionly));
$check('site requires login', (int) get_config('core', 'forcelogin') === 1);
$check('self registration is off', (string) get_config('core', 'registerauth') === '');
$check('cron ran in the last 5 minutes', $lastcron > 0 && (time() - $lastcron) < 300,
    $lastcron ? (time() - $lastcron) . ' seconds ago' : 'never');
$check('alignment service answers and accepts the token', $connection->is_connected(), $connection->status);

$report = [
    'generated_utc' => gmdate('Y-m-d\TH:i:s\Z'),
    'moodle' => ['release' => $CFG->release, 'version' => $CFG->version, 'wwwroot' => $CFG->wwwroot],
    'plugin' => ['version' => $plugin ? $plugin->versiondb : null, 'release' => $plugin ? $plugin->release : null],
    'framework' => $framework ? [
        'id' => (int) $framework->get('id'),
        'idnumber' => $framework->get('idnumber'),
        'competencies' => $DB->count_records('competency', ['competencyframeworkid' => $framework->get('id')]),
    ] : null,
    'course' => $course ? [
        'shortname' => $course->shortname,
        'pages' => $DB->count_records('page', ['course' => $course->id]),
        'enrolled_users' => $enrolled,
    ] : null,
    'teacher_accounts' => ['total' => $teachers, 'suspended' => $suspended],
    'plugin_config' => $config,
    'email_disabled' => !empty($CFG->noemailever),
    'cron' => [
        'last_start_utc' => $lastcron ? gmdate('Y-m-d\TH:i:s\Z', $lastcron) : null,
        'adhoc_tasks_waiting' => $DB->count_records('task_adhoc'),
    ],
    'analyses' => ['total' => array_sum($byStatus), 'by_status' => $byStatus],
    'reviews' => $DB->count_records('local_compalign_review'),
    'checks' => $checks,
];
echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;

if ($options['check']) {
    $failed = array_filter($checks, static fn($c) => !$c['passed']);
    exit($failed ? 1 : 0);
}
