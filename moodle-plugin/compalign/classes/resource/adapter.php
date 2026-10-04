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
 * Reads one Moodle activity type into the shared resource contract.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
interface adapter {
    /**
     * Moodle module name, for example page or quiz.
     *
     * @return string
     */
    public function modname(): string;

    /**
     * List the analytical items inside one course module.
     *
     * @param \cm_info $cm The course module.
     * @return item[]
     */
    public function enumerate(\cm_info $cm): array;

    /**
     * Read one item as the plain-text resource the service analyses.
     *
     * @param \cm_info $cm The course module.
     * @param item $item The item returned by enumerate().
     * @return array{resource: array<string, string>, hash: string, file?: array<string, string>, provenance?: array}
     */
    public function extract(\cm_info $cm, item $item): array;
}
