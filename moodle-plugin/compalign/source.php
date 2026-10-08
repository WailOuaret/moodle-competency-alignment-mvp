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
 * Show one quotation inside the resource it came from.
 *
 * The quotation must already belong to an analysis or a teacher-added
 * relationship for this activity. An id from another course is refused.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');

use local_compalign\output\error_messages;
use local_compalign\output\source_view;
use local_compalign\service\analysis_exception;
use local_compalign\service\source_context;

$cmid = required_param('cmid', PARAM_INT);
$item = required_param('item', PARAM_RAW_TRIMMED);
$evidenceid = optional_param('evidence', 0, PARAM_INT);
$manualid = optional_param('manual', 0, PARAM_INT);
if (!preg_match('/^moodle:[a-z0-9:_-]{1,220}$/', $item)) {
    throw new moodle_exception('invalidparameter', 'error');
}

[$course, $cm] = get_course_and_cm_from_cmid($cmid);
require_login($course, false, $cm);
$context = context_module::instance($cm->id);
require_capability('local/compalign:view', $context);

$url = new moodle_url('/local/compalign/source.php', ['cmid' => $cm->id, 'item' => $item]);
$PAGE->set_url($url);
$PAGE->set_context($context);
$PAGE->set_title(get_string('showinsource', 'local_compalign'));
$PAGE->set_heading($course->fullname);
$PAGE->set_pagelayout('incourse');

$viewer = new source_context();
try {
    if ($evidenceid > 0) {
        $quote = $viewer->quote_from_evidence($evidenceid, $cm, $item);
    } else if ($manualid > 0) {
        $quote = $viewer->quote_from_manual($manualid, $cm, $item);
    } else {
        throw new analysis_exception('evidence_invalid');
    }
    if (trim($quote) === '') {
        throw new analysis_exception('quote_not_found');
    }
    $view = $viewer->build($cm, (int) $course->id, $item, $quote, $context);
} catch (analysis_exception $exception) {
    $view = [
        'title' => $cm->get_formatted_name(),
        'type' => $cm->get_module_type_name(),
        'provenance' => '',
        'found' => false,
        'html' => '',
        'errormessage' => error_messages::for_code($exception->get_error_code()),
        'openurl' => '',
        'backurl' => (new moodle_url('/local/compalign/review.php', ['cmid' => $cm->id, 'item' => $item]))->out(false),
    ];
}

echo $OUTPUT->header();
echo $OUTPUT->heading(get_string('showinsource', 'local_compalign'));
echo $OUTPUT->render(new source_view($view));
echo $OUTPUT->footer();
