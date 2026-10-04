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

/**
 * One analytical resource inside a course module.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class item {
    /**
     * Constructor.
     *
     * @param string $resourceid Stable id. Not a display title.
     * @param string $resourcetype Service resource type.
     * @param string $title Short label for the teacher.
     * @param string $preview Plain-text preview. Empty when there is nothing to show.
     * @param bool $supported Whether this item can be analysed.
     * @param string $reason Language-string key when it cannot.
     * @param string $provenance Human description of where the text comes from.
     */
    public function __construct(
        public string $resourceid,
        public string $resourcetype,
        public string $title,
        public string $preview = '',
        public bool $supported = true,
        public string $reason = '',
        public string $provenance = '',
    ) {
    }
}
