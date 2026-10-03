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
 * Library callbacks for the Competency Alignment Assistant.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

/**
 * Add the Competency Alignment entry to the course navigation.
 *
 * Moodle calls this for every plugin when it builds the course navigation, so it
 * must stay cheap: a capability check and a link, nothing else.
 *
 * @param navigation_node $navigation The course navigation node.
 * @param stdClass $course The course.
 * @param context $context The course context.
 */
function local_compalign_extend_navigation_course(navigation_node $navigation, stdClass $course, context $context): void {
    if (!has_capability('local/compalign:view', $context)) {
        return;
    }

    $navigation->add(
        get_string('competencyalignment', 'local_compalign'),
        new moodle_url('/local/compalign/index.php', ['courseid' => $course->id]),
        navigation_node::TYPE_SETTING,
        null,
        'local_compalign',
        new pix_icon('i/competencies', '')
    );
}
