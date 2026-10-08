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
 * Add a competency the model did not suggest.
 *
 * The competency must belong to the configured framework. Saving does not
 * create an official Moodle competency link.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');

use core\output\notification;
use local_compalign\form\add_competency_form;
use local_compalign\output\error_messages;
use local_compalign\service\analysis_exception;
use local_compalign\service\competency_catalogue;
use local_compalign\service\manual_relationship;
use local_compalign\service\source_context;

$cmid = required_param('cmid', PARAM_INT);
$item = required_param('item', PARAM_RAW_TRIMMED);
if (!preg_match('/^moodle:[a-z0-9:_-]{1,220}$/', $item)) {
    throw new moodle_exception('invalidparameter', 'error');
}

[$course, $cm] = get_course_and_cm_from_cmid($cmid);
require_login($course, false, $cm);
$context = context_module::instance($cm->id);
require_capability('local/compalign:review', $context);

$url = new moodle_url('/local/compalign/add.php', ['cmid' => $cm->id, 'item' => $item]);
$back = new moodle_url('/local/compalign/review.php', ['cmid' => $cm->id, 'item' => $item]);
$PAGE->set_url($url);
$PAGE->set_context($context);
$PAGE->set_title(get_string('addcompetency', 'local_compalign'));
$PAGE->set_heading($course->fullname);
$PAGE->set_pagelayout('incourse');

$manager = new manual_relationship();
try {
    $catalogue = (new competency_catalogue())->build();
    $packed = $manager->require_resource($cm, $item);
    $text = source_context::canonical_text($packed);
} catch (analysis_exception $exception) {
    redirect($back, error_messages::for_code($exception->get_error_code()), null, notification::NOTIFY_ERROR);
}

$form = new add_competency_form($url, [
    'cmid' => $cm->id,
    'item' => $item,
    'catalogue' => $catalogue,
    'resourcehash' => $packed['hash'],
    'text' => $text,
    'active' => $manager->active_idnumbers((int) $course->id, $item, (int) $USER->id, $packed['hash']),
]);

if ($form->is_cancelled()) {
    redirect($back);
}
if ($data = $form->get_data()) {
    try {
        $manager->add(
            $cm,
            $item,
            (int) $course->id,
            (int) $USER->id,
            (string) $data->competency,
            (string) $data->resourcehash,
            (string) ($data->evidencetext ?? ''),
            (string) ($data->commenttext ?? ''),
            $context
        );
    } catch (analysis_exception $exception) {
        redirect($url, error_messages::for_code($exception->get_error_code()), null, notification::NOTIFY_ERROR);
    }
    redirect($back, get_string('competencyadded', 'local_compalign'), null, notification::NOTIFY_SUCCESS);
}

echo $OUTPUT->header();
echo $OUTPUT->heading(get_string('addcompetency', 'local_compalign'));
echo html_writer::tag('p', get_string('addcompetency_help', 'local_compalign'));
$form->display();
echo $OUTPUT->footer();
