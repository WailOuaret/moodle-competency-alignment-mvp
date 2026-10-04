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

namespace local_compalign\resource;

use local_compalign\service\analysis_exception;
use local_compalign\service\resource_extractor;

/**
 * Teacher-authored assignment instructions. Submissions are never read.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class assignment_adapter implements adapter {
    public function modname(): string {
        return 'assign';
    }

    public function enumerate(\cm_info $cm): array {
        global $DB;

        $assign = $DB->get_record('assign', ['id' => $cm->instance], 'id, name, intro');
        if (!$assign) {
            return [];
        }
        $items = [html_source::item(
            'moodle:assign:' . $assign->id,
            'assignment',
            resource_extractor::html_to_text($assign->name) ?: $cm->name,
            $assign->intro,
            $cm->name
        )];

        $context = \context_module::instance($cm->id);
        $files = get_file_storage()->get_area_files($context->id, 'mod_assign', 'introattachment', 0, 'filename', false);
        foreach ($files as $file) {
            $items[] = file_item::from_stored_file($cm, $file, 'assignment attachment');
        }
        return $items;
    }

    public function extract(\cm_info $cm, item $item): array {
        if (str_contains($item->resourceid, ':file:')) {
            return file_item::extract($cm, $item);
        }

        global $DB;
        $assign = $DB->get_record('assign', ['id' => $cm->instance], 'id, name, intro');
        if (!$assign || $item->resourceid !== 'moodle:assign:' . $assign->id) {
            throw new analysis_exception('resource_missing');
        }
        $text = resource_extractor::html_to_text($assign->intro);
        return course_context::pack($cm, $item, $text) + [
            'provenance' => ['kind' => 'assignment', 'label' => $item->title],
        ];
    }
}
