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
 * A teacher added or removed a competency on a resource.
 *
 * The log records the action, the competency idnumber and the resource hash.
 * The comment and the quotation stay in the plugin table.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class manual_relationship_changed extends \core\event\base {
    /**
     * Initialise the event.
     */
    protected function init() {
        $this->data['crud'] = 'c';
        $this->data['edulevel'] = self::LEVEL_TEACHING;
        $this->data['objecttable'] = 'local_compalign_manualrel';
    }

    /**
     * Localised name of the event.
     *
     * @return string
     */
    public static function get_name() {
        return get_string('event_manual_relationship', 'local_compalign');
    }

    /**
     * Description for the logs.
     *
     * @return string
     */
    public function get_description() {
        $action = $this->other['action'] ?? '';
        $competency = $this->other['competency'] ?? '';

        return "The user with id '{$this->userid}' {$action} competency '{$competency}' on resource "
            . "'{$this->other['resourceid']}' (relationship id '{$this->objectid}').";
    }

    /**
     * Where to see the resource review.
     *
     * @return \moodle_url
     */
    public function get_url() {
        return new \moodle_url('/local/compalign/review.php', [
            'cmid' => $this->contextinstanceid,
            'item' => $this->other['resourceid'] ?? '',
        ]);
    }

    /**
     * Check the event data.
     */
    protected function validate_data() {
        parent::validate_data();
        foreach (['action', 'competency', 'resourceid', 'resourcehash'] as $key) {
            if (!isset($this->other[$key])) {
                throw new \coding_exception("The {$key} must be set in other.");
            }
        }
    }

    /**
     * Relationships are not restored as part of a course backup.
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
