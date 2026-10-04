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
 * One Book chapter is one analytical resource.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class book_adapter implements adapter {
    public function modname(): string {
        return 'book';
    }

    public function enumerate(\cm_info $cm): array {
        global $DB;

        $chapters = $DB->get_records('book_chapters', ['bookid' => $cm->instance], 'pagenum ASC, id ASC');
        $items = [];
        foreach ($chapters as $chapter) {
            if (!empty($chapter->hidden)) {
                continue;
            }
            $title = resource_extractor::html_to_text($chapter->title) ?: 'Chapter';
            $items[] = html_source::item(
                'moodle:book:' . $cm->instance . ':chapter:' . $chapter->id,
                'book_chapter',
                $title,
                $chapter->content,
                $cm->name . ', ' . $title
            );
        }
        return $items;
    }

    public function extract(\cm_info $cm, item $item): array {
        global $DB;

        foreach ($this->enumerate($cm) as $candidate) {
            if ($candidate->resourceid !== $item->resourceid) {
                continue;
            }
            $chapterid = (int) substr(strrchr($item->resourceid, ':'), 1);
            $chapter = $DB->get_record('book_chapters', ['id' => $chapterid, 'bookid' => $cm->instance]);
            if (!$chapter) {
                throw new analysis_exception('resource_missing');
            }
            $text = resource_extractor::html_to_text($chapter->content);
            return course_context::pack($cm, $candidate, $text) + [
                'provenance' => ['kind' => 'book_chapter', 'label' => $candidate->provenance, 'chapterid' => $chapterid],
            ];
        }

        throw new analysis_exception('resource_missing');
    }
}
