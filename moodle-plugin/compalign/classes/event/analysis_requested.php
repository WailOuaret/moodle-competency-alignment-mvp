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

namespace local_compalign\event;

/**
 * A teacher asked for competency suggestions for a resource.
 *
 * The event records who asked and for which resource. It never carries the service address,
 * the token, the resource text or anything the service returned.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class analysis_requested extends \core\event\base {
    /**
     * Initialise the event.
     */
    protected function init() {
        $this->data['crud'] = 'c';
        $this->data['edulevel'] = self::LEVEL_TEACHING;
        $this->data['objecttable'] = 'local_compalign_analysis';
    }

    /**
     * Localised name of the event.
     *
     * @return string
     */
    public static function get_name() {
        return get_string('event_analysis_requested', 'local_compalign');
    }

    /**
     * Description for the logs.
     *
     * @return string
     */
    public function get_description() {
        return "The user with id '{$this->userid}' requested competency suggestions (analysis id '{$this->objectid}') "
            . "for the course module with id '{$this->contextinstanceid}'.";
    }

    /**
     * Where to see the result.
     *
     * @return \moodle_url
     */
    public function get_url() {
        return new \moodle_url('/local/compalign/review.php', ['cmid' => $this->contextinstanceid]);
    }

    /**
     * Analyses are not part of a course backup, so the id is not restored.
     *
     * @return int
     */
    public static function get_objectid_mapping() {
        return self::NOT_MAPPED;
    }

    /**
     * No other value needs mapping on restore.
     *
     * @return bool
     */
    public static function get_other_mapping() {
        return false;
    }
}
