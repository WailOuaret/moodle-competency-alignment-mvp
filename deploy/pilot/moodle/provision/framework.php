<?php
// Create the UTC GI competency framework from the repository's competencies.jsonl, if it is not
// there yet. Prints the framework id on standard output. Never changes an existing framework.
//
// The file is the same list the research study used, so the pilot teachers are shown the same 13
// competencies, with the same codes, names and descriptions.

require(__DIR__ . '/_bootstrap.php');

use core_competency\api;
use core_competency\competency_framework;

const PILOT_FRAMEWORK_IDNUMBER = 'UTC_GI_MVP_2026';
const PILOT_SCALE_NAME = 'Default competence scale';

$existing = competency_framework::get_record(['idnumber' => PILOT_FRAMEWORK_IDNUMBER]);
if ($existing) {
    pilot_say('framework: already present (id ' . $existing->get('id') . '), left unchanged');
    echo $existing->get('id') . PHP_EOL;
    exit(0);
}

$rows = [];
foreach (file('/opt/pilot/data/competencies.jsonl', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
    $rows[] = json_decode($line, true, 512, JSON_THROW_ON_ERROR);
}
if (count($rows) !== 13) {
    pilot_say('framework: expected 13 competencies, found ' . count($rows) . '. Nothing was created.');
    exit(1);
}

// Parents before children, siblings in their own order.
usort($rows, static function (array $a, array $b): int {
    return [(int) $a['depth'], (string) $a['parent_idnumber'], (int) $a['sortorder']]
        <=> [(int) $b['depth'], (string) $b['parent_idnumber'], (int) $b['sortorder']];
});

$transaction = $DB->start_delegated_transaction();

$scale = $DB->get_record('scale', ['name' => PILOT_SCALE_NAME, 'courseid' => 0]);
if (!$scale) {
    $scale = (object) [
        'courseid' => 0,
        'userid' => 0,
        'name' => PILOT_SCALE_NAME,
        'scale' => 'Not yet competent,Competent',
        'description' => '',
        'descriptionformat' => FORMAT_HTML,
        'timemodified' => time(),
    ];
    $scale->id = $DB->insert_record('scale', $scale);
}

$first = $rows[0];
$framework = api::create_framework((object) [
    'shortname' => $first['framework_shortname'],
    'idnumber' => PILOT_FRAMEWORK_IDNUMBER,
    'contextid' => context_system::instance()->id,
    'visible' => 1,
    'description' => '',
    'descriptionformat' => FORMAT_HTML,
    'scaleid' => $scale->id,
    'scaleconfiguration' => json_encode([
        ['scaleid' => (string) $scale->id],
        ['id' => 2, 'scaledefault' => 1, 'proficient' => 1],
    ]),
    'taxonomies' => 'competency,competency,competency,competency',
]);

$ids = [];
foreach ($rows as $row) {
    if ($row['framework_idnumber'] !== PILOT_FRAMEWORK_IDNUMBER) {
        throw new moodle_exception('Unexpected framework in competencies.jsonl: ' . $row['framework_idnumber']);
    }
    $parentid = $row['parent_idnumber'] === '' ? 0 : $ids[$row['parent_idnumber']];
    $competency = api::create_competency((object) [
        'competencyframeworkid' => $framework->get('id'),
        'parentid' => $parentid,
        'shortname' => $row['shortname'],
        'idnumber' => $row['idnumber'],
        'description' => $row['description_raw'],
        'descriptionformat' => (int) ($row['metadata']['description_format'] ?? FORMAT_HTML),
    ]);
    $ids[$row['idnumber']] = $competency->get('id');
}

$transaction->allow_commit();
pilot_say('framework: created "' . $first['framework_shortname'] . '" with ' . count($ids) . ' competencies');
echo $framework->get('id') . PHP_EOL;
