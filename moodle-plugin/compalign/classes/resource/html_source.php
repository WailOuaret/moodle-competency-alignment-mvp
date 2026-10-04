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

use local_compalign\service\resource_extractor;

/**
 * One teacher-authored HTML field, reduced to plain text.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class html_source {
    /**
     * @param string $resourceid Stable id.
     * @param string $resourcetype Service type.
     * @param string $title Teacher-facing title.
     * @param string $html HTML or plain text from Moodle.
     * @param string $provenance Where the text sits in the activity.
     * @return item
     */
    public static function item(
        string $resourceid,
        string $resourcetype,
        string $title,
        string $html,
        string $provenance
    ): item {
        $text = resource_extractor::html_to_text($html);
        return new item(
            $resourceid,
            $resourcetype,
            $title !== '' ? $title : $provenance,
            mb_substr($text, 0, 160),
            $text !== '',
            $text === '' ? 'resourceempty' : '',
            $provenance
        );
    }
}
