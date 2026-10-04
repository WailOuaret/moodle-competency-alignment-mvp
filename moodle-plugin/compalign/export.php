<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * Download a pseudonymised review export. Requires local/compalign:viewallreviews.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');

use local_compalign\service\study_export;

require_login();
$context = context_system::instance();
require_capability('local/compalign:viewallreviews', $context);

$format = optional_param('format', 'csv', PARAM_ALPHA);
$filters = [
    'courseid' => optional_param('courseid', 0, PARAM_INT),
    'resourcetype' => optional_param('resourcetype', '', PARAM_ALPHANUMEXT),
    'participant' => optional_param('participant', '', PARAM_ALPHANUMEXT),
    'from' => optional_param('from', 0, PARAM_INT),
    'to' => optional_param('to', 0, PARAM_INT),
];

$export = new study_export();
$rows = $export->rows($filters);

if ($format === 'json') {
    $payload = json_encode(['reviews' => $rows], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="compalign-reviews.json"');
    echo $payload;
    exit;
}

header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="compalign-reviews.csv"');
echo $export->csv($rows);
