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
 * A Text and media area. Only the teacher-authored introduction is read.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class label_adapter implements adapter {
    public function modname(): string {
        return 'label';
    }

    public function enumerate(\cm_info $cm): array {
        global $DB;

        $label = $DB->get_record('label', ['id' => $cm->instance], 'id, name, intro');
        if (!$label) {
            return [];
        }
        $title = resource_extractor::html_to_text($label->name) ?: resource_extractor::html_to_text($label->intro);
        $title = $title !== '' ? mb_substr($title, 0, 80) : 'Text and media';
        return [html_source::item('moodle:label:' . $label->id, 'label', $title, (string) $label->intro, 'Text and media')];
    }

    public function extract(\cm_info $cm, item $item): array {
        global $DB;

        $label = $DB->get_record('label', ['id' => $cm->instance], 'id, intro');
        if (!$label || $item->resourceid !== 'moodle:label:' . $label->id) {
            throw new analysis_exception('resource_missing');
        }
        return course_context::pack($cm, $item, resource_extractor::html_to_text($label->intro)) + [
            'provenance' => ['kind' => 'label', 'label' => $item->title],
        ];
    }
}
