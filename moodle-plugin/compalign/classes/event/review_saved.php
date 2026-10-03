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
 * A teacher saved a decision on a suggested competency.
 *
 * Only the decision and the revision are logged. The comment, the rating and the review time
 * stay in the plugin's own table, where the privacy provider covers them.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class review_saved extends \core\event\base {
    /**
     * Initialise the event.
     */
    protected function init() {
        $this->data['crud'] = 'c';
        $this->data['edulevel'] = self::LEVEL_TEACHING;
        $this->data['objecttable'] = 'local_compalign_review';
    }

    /**
     * Localised name of the event.
     *
     * @return string
     */
    public static function get_name() {
        return get_string('event_review_saved', 'local_compalign');
    }

    /**
     * Description for the logs.
     *
     * @return string
     */
    public function get_description() {
        $decision = $this->other['decision'] ?? '';
        $revision = $this->other['revision'] ?? '';

        return "The user with id '{$this->userid}' saved the decision '{$decision}' (revision {$revision}, review id "
            . "'{$this->objectid}') on a suggested competency for the course module with id '{$this->contextinstanceid}'.";
    }

    /**
     * Where to see the review.
     *
     * @return \moodle_url
     */
    public function get_url() {
        return new \moodle_url('/local/compalign/review.php', ['cmid' => $this->contextinstanceid]);
    }

    /**
     * Check the event data.
     *
     * @throws \coding_exception When the decision or the revision is missing.
     */
    protected function validate_data() {
        parent::validate_data();

        if (!isset($this->other['decision']) || !isset($this->other['revision'])) {
            throw new \coding_exception('The decision and the revision must be set in other.');
        }
    }

    /**
     * Reviews are not part of a course backup, so the id is not restored.
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
