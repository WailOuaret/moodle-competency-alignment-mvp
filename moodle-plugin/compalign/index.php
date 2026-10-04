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

    $action = optional_param('action', '', PARAM_ALPHA);
    if ($action === 'batch' && data_submitted()) {
        require_sesskey();
        require_capability('local/compalign:analyse', $context);
        $items = optional_param_array('items', [], PARAM_RAW);
        $items = array_values(array_filter($items, static fn(string $id): bool => (bool) preg_match('/^moodle:[a-z0-9:_-]{1,220}$/', $id)));
        if (!$items) {
            redirect($PAGE->url, get_string('batch_none', 'local_compalign'), null, \core\output\notification::NOTIFY_ERROR);
        }
        if (count($items) > dashboard::MAX_BATCH) {
            redirect($PAGE->url, get_string('batch_toomany', 'local_compalign', dashboard::MAX_BATCH), null, \core\output\notification::NOTIFY_ERROR);
        }
        $manager = new \local_compalign\service\analysis_manager();
        $modinfo = get_fast_modinfo($course);
        $matches = [];
        foreach ($items as $resourceid) {
            foreach ($modinfo->get_cms() as $cm) {
                foreach (\local_compalign\resource\registry::enumerate($cm) as $candidate) {
                    if ($candidate->resourceid === $resourceid && $candidate->supported) {
                        $matches[] = [$cm, $resourceid];
                    }
                }
            }
        }
        $confirm = optional_param('confirm', 0, PARAM_BOOL);
        if (!$confirm) {
            $cached = 0;
            $fresh = 0;
            $active = 0;
            foreach ($matches as [$cm, $resourceid]) {
                $preview = $manager->preview_analysis($cm, $resourceid);
                if ($preview === \local_compalign\service\analysis_manager::OUTCOME_REUSED) {
                    $cached++;
                } else if ($preview === \local_compalign\service\analysis_manager::OUTCOME_ACTIVE) {
                    $active++;
                } else {
                    $fresh++;
                }
            }
            echo $OUTPUT->header();
            echo $OUTPUT->heading(get_string('batch_confirm', 'local_compalign'));
            echo html_writer::tag('p', get_string('batch_preview', 'local_compalign', (object) [
                'cached' => $cached,
                'fresh' => $fresh,
                'active' => $active,
            ]));
            echo html_writer::start_tag('form', ['method' => 'post', 'action' => $PAGE->url->out(false)]);
            echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'sesskey', 'value' => sesskey()]);
            echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'action', 'value' => 'batch']);
            echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'confirm', 'value' => '1']);
            foreach ($items as $resourceid) {
                echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'items[]', 'value' => $resourceid]);
            }
            echo html_writer::empty_tag('input', [
                'type' => 'submit',
                'class' => 'btn btn-primary',
                'value' => get_string('batch_confirm', 'local_compalign'),
            ]);
            echo html_writer::end_tag('form');
            echo $OUTPUT->footer();
            exit;
        }
        $queued = 0;
        foreach ($matches as [$cm, $resourceid]) {
            $manager->request_analysis($cm, (int) $USER->id, false, $resourceid);
            $queued++;
        }
        redirect($PAGE->url, get_string('batch_queued', 'local_compalign', $queued), null, \core\output\notification::NOTIFY_SUCCESS);
    }

    $filter = optional_param('filter', 'all', PARAM_ALPHA);
    $type = optional_param('type', 'all', PARAM_ALPHA);
    echo $OUTPUT->header();
    echo $OUTPUT->heading(get_string('competencyalignment', 'local_compalign'));
    echo $OUTPUT->render(dashboard::create($course, (int) $USER->id, $filter, $type));
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
