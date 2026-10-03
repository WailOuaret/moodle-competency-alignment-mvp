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

namespace local_compalign\service;

use core_competency\api;

/**
 * Reads the official competency links of an activity through Moodle's competency API.
 *
 * This class only reads. Nothing in this release creates, changes or removes a link.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class competency_links {
    /**
     * The competencies officially linked to an activity.
     *
     * Returns an empty list when competencies are disabled or the user may not see the links, so a
     * page never fails because of them.
     *
     * @param \cm_info $cm The activity.
     * @return array[] Each with idnumber and shortname, in the order Moodle lists them.
     */
    public static function list_for_cm(\cm_info $cm): array {
        if (!api::is_enabled()) {
            return [];
        }

        try {
            $links = api::list_course_module_competencies($cm->id);
        } catch (\moodle_exception) {
            return [];
        }

        $result = [];
        foreach ($links as $link) {
            $competency = $link['competency'];
            $result[] = [
                'idnumber' => (string) $competency->get('idnumber'),
                'shortname' => (string) $competency->get('shortname'),
            ];
        }

        return $result;
    }
}
