<?php
// Remove every analysis, suggestion, evidence quotation and review the plugin has stored.
//
//   php clear_test_data.php --count         only count them
//   php clear_test_data.php --confirm=DELETE-PILOT-TEST-DATA
//
// This is for the day the pilot starts: whatever was saved while the site was being tested (for
// example the one live-model test) must not be mixed with the teachers' decisions. It touches the
// the plugin's analysis, review and teacher-added relationship tables, and nothing else:
// not users, not the course, not Moodle's own competency links, and not the file-text cache.
// Take a backup first (scripts/backup.sh); the wrapper script does.

require(__DIR__ . '/_bootstrap.php');

[$options] = cli_get_params(['count' => false, 'confirm' => ''], []);

// Children first.
$tables = [
    'local_compalign_manualrel',
    'local_compalign_review',
    'local_compalign_evidence',
    'local_compalign_sugg',
    'local_compalign_analysis',
];

$counts = static function () use ($DB, $tables): array {
    $result = [];
    foreach ($tables as $table) {
        $result[$table] = $DB->count_records($table);
    }
    return $result;
};

$before = $counts();
if ($options['count'] || $options['confirm'] === '') {
    echo json_encode(['local_compalign rows' => $before], JSON_PRETTY_PRINT) . PHP_EOL;
    if (!$options['count']) {
        pilot_say('clear: nothing was deleted. Pass --confirm=DELETE-PILOT-TEST-DATA to delete.');
        exit(1);
    }
    exit(0);
}
if ($options['confirm'] !== 'DELETE-PILOT-TEST-DATA') {
    pilot_say('clear: the confirmation text is not right. Nothing was deleted.');
    exit(1);
}

$transaction = $DB->start_delegated_transaction();
foreach ($tables as $table) {
    $DB->delete_records($table);
}
$transaction->allow_commit();

echo json_encode(['before' => $before, 'after' => $counts(), 'cleared_utc' => gmdate('Y-m-d\TH:i:s\Z')], JSON_PRETTY_PRINT) . PHP_EOL;
