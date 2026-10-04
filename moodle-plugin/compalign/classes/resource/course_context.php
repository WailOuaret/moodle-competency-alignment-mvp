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
 * Shared fields every adapter puts on the service resource.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class course_context {
    /**
     * Build the resource array and its fingerprint.
     *
     * @param \cm_info $cm The course module.
     * @param item $item The analytical item.
     * @param string $text Plain text to analyse. Empty when a file is extracted later.
     * @param array<string, string> $extra Local fingerprint fields. Not sent to the service.
     * @return array{resource: array<string, string>, hash: string}
     */
    public static function pack(\cm_info $cm, item $item, string $text, array $extra = []): array {
        global $CFG;

        require_once($CFG->dirroot . '/course/lib.php');

        if ($text === '' && empty($extra['content_hash'])) {
            throw new analysis_exception('resource_empty');
        }
        if (mb_strlen($text) > resource_extractor::MAX_TEXT_CHARS) {
            throw new analysis_exception('resource_too_large');
        }

        $course = $cm->get_course();
        $title = resource_extractor::html_to_text($item->title !== '' ? $item->title : $cm->name);
        $resource = [
            'resource_id' => $item->resourceid,
            'resource_type' => $item->resourcetype,
            'course_id' => (string) $cm->course,
            'course_module_id' => (string) $cm->id,
            'title' => $title,
            'text' => $text,
            'search_text' => resource_extractor::combine_text($title, $text),
            'course_shortname' => resource_extractor::html_to_text((string) $course->shortname),
            'course_fullname' => resource_extractor::html_to_text((string) $course->fullname),
            'section_name' => resource_extractor::html_to_text((string) get_section_name($course, $cm->sectionnum)),
            'activity_name' => resource_extractor::html_to_text($cm->name),
        ] + $extra;

        $resource = array_filter($resource, static fn(string $value): bool => $value !== '');

        return [
            'resource' => $resource,
            'hash' => resource_extractor::hash($resource),
        ];
    }
}
