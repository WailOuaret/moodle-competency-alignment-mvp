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
 * Entry page of the Competency Alignment Assistant.
 *
 * With a course id it is the course dashboard: every resource with its analysis status. Without one it
 * is the site overview for managers, including the alignment service connection status.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');

use local_compalign\output\dashboard;
use local_compalign\output\overview;
use local_compalign\service\alignment_client;

$courseid = optional_param('courseid', 0, PARAM_INT);

if ($courseid) {
    $course = get_course($courseid);
    require_login($course);
    $context = context_course::instance($course->id);
    require_capability('local/compalign:view', $context);
    $PAGE->set_pagelayout('incourse');
    $PAGE->set_heading($course->fullname);
    $PAGE->set_url(new moodle_url('/local/compalign/index.php', ['courseid' => $course->id]));
    $PAGE->set_context($context);
    $PAGE->set_title(get_string('pluginname', 'local_compalign'));

    echo $OUTPUT->header();
    echo $OUTPUT->heading(get_string('competencyalignment', 'local_compalign'));
    echo $OUTPUT->render(dashboard::create($course, (int) $USER->id));
    echo $OUTPUT->footer();
    exit;
}

require_login();
$context = context_system::instance();
require_capability('local/compalign:manage', $context);
$PAGE->set_pagelayout('admin');
$PAGE->set_heading(get_string('pluginname', 'local_compalign'));
$PAGE->set_url(new moodle_url('/local/compalign/index.php'));
$PAGE->set_context($context);
$PAGE->set_title(get_string('pluginname', 'local_compalign'));

// The service status is checked on the server, so the token never reaches the browser.
$connection = alignment_client::check_configured_connection();
$showsettings = has_capability('moodle/site:config', $context);

echo $OUTPUT->header();
echo $OUTPUT->heading(get_string('pluginname', 'local_compalign'));
echo $OUTPUT->render(new overview($connection, $showsettings));
echo $OUTPUT->footer();
