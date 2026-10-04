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
 * One Lesson page is one analytical resource.
 *
 * The page content and the answer texts are included. Scores, jumps and student
 * attempts are not.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class lesson_adapter implements adapter {
    public function modname(): string {
        return 'lesson';
    }

    public function enumerate(\cm_info $cm): array {
        global $DB;

        $pages = $DB->get_records('lesson_pages', ['lessonid' => $cm->instance], 'id ASC');
        $items = [];
        foreach ($pages as $page) {
            $answers = $DB->get_records('lesson_answers', ['pageid' => $page->id], 'id ASC');
            $html = (string) $page->contents;
            foreach ($answers as $answer) {
                $html .= "\n" . ($answer->answer ?? '');
            }
            $title = resource_extractor::html_to_text($page->title) ?: 'Page';
            $items[] = html_source::item(
                'moodle:lesson:' . $cm->instance . ':page:' . $page->id,
                'lesson_page',
                $title,
                $html,
                $cm->name . ', ' . $title
            );
        }
        return $items;
    }

    public function extract(\cm_info $cm, item $item): array {
        foreach ($this->enumerate($cm) as $candidate) {
            if ($candidate->resourceid !== $item->resourceid || !$candidate->supported) {
                continue;
            }
            $text = $candidate->preview;
            // Preview is truncated. Rebuild the full text.
            $pageid = (int) substr(strrchr($item->resourceid, ':'), 1);
            $text = $this->full_text($cm, $pageid);
            return course_context::pack($cm, $candidate, $text) + [
                'provenance' => ['kind' => 'lesson_page', 'label' => $candidate->provenance, 'pageid' => $pageid],
            ];
        }
        throw new analysis_exception('resource_missing');
    }

    private function full_text(\cm_info $cm, int $pageid): string {
        global $DB;

        $page = $DB->get_record('lesson_pages', ['id' => $pageid, 'lessonid' => $cm->instance], '*', MUST_EXIST);
        $parts = [resource_extractor::html_to_text($page->contents)];
        $answers = $DB->get_records('lesson_answers', ['pageid' => $page->id], 'id ASC');
        foreach ($answers as $answer) {
            $parts[] = resource_extractor::html_to_text($answer->answer ?? '');
        }
        return resource_extractor::combine_text(...$parts);
    }
}
