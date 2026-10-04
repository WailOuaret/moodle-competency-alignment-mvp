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
 * One Moodle Page is one analytical resource.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class page_adapter implements adapter {
    public function modname(): string {
        return 'page';
    }

    public function enumerate(\cm_info $cm): array {
        global $DB;

        $page = $DB->get_record('page', ['id' => $cm->instance], 'id, name, intro, content');
        if (!$page) {
            return [];
        }

        $text = resource_extractor::combine_text(
            resource_extractor::html_to_text($page->intro),
            resource_extractor::html_to_text($page->content)
        );

        return [new item(
            'moodle:page:' . $page->id,
            resource_extractor::TYPE_PAGE,
            resource_extractor::html_to_text($page->name) ?: $page->name,
            mb_substr($text, 0, 160),
            true,
            '',
            'Page'
        )];
    }

    public function extract(\cm_info $cm, item $item): array {
        global $DB;

        $page = $DB->get_record('page', ['id' => $cm->instance], 'id, name, intro, content');
        if (!$page || $item->resourceid !== 'moodle:page:' . $page->id) {
            throw new analysis_exception('resource_missing');
        }

        $text = resource_extractor::combine_text(
            resource_extractor::html_to_text($page->intro),
            resource_extractor::html_to_text($page->content)
        );

        return course_context::pack($cm, $item, $text) + [
            'provenance' => ['kind' => 'page', 'label' => $item->title],
        ];
    }
}
