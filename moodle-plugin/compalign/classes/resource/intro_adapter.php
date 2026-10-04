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
 * The teacher-authored introduction of an activity, and nothing the learners wrote.
 *
 * Used for a forum (the intro only; posts are out of scope) and a URL (the
 * description only; the address is not fetched).
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class intro_adapter implements adapter {
    /**
     * @param string $modname Moodle module name.
     * @param string $table Database table.
     * @param string $resourcetype Service resource type.
     */
    public function __construct(
        private string $modname,
        private string $table,
        private string $resourcetype,
    ) {
    }

    public function modname(): string {
        return $this->modname;
    }

    public function enumerate(\cm_info $cm): array {
        global $DB;

        $record = $DB->get_record($this->table, ['id' => $cm->instance], 'id, name, intro');
        if (!$record) {
            return [];
        }
        $note = match ($this->resourcetype) {
            'forum_intro' => get_string('forumpostsnotanalysed', 'local_compalign'),
            'url' => get_string('urlnofetch', 'local_compalign'),
            default => $cm->name,
        };
        return [html_source::item(
            'moodle:' . $this->modname . ':' . $record->id,
            $this->resourcetype,
            resource_extractor::html_to_text($record->name) ?: $cm->name,
            (string) $record->intro,
            $note
        )];
    }

    public function extract(\cm_info $cm, item $item): array {
        global $DB;

        $record = $DB->get_record($this->table, ['id' => $cm->instance], 'id, name, intro');
        if (!$record || $item->resourceid !== 'moodle:' . $this->modname . ':' . $record->id) {
            throw new analysis_exception('resource_missing');
        }
        return course_context::pack($cm, $item, resource_extractor::html_to_text($record->intro)) + [
            'provenance' => ['kind' => $this->resourcetype, 'label' => $item->title],
        ];
    }
}
