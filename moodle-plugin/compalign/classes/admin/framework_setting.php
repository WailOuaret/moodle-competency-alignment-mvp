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

namespace local_compalign\admin;

use core_competency\api;

/**
 * Lets the administrator choose the one competency framework the assistant proposes from.
 *
 * The choices are the visible frameworks of the site, read through Moodle's competency API when the
 * settings page is shown. Nothing is selected by default and frameworks are never combined.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class framework_setting extends \admin_setting_configselect {
    /**
     * Constructor.
     *
     * @param string $name Setting name, for example local_compalign/frameworkid.
     * @param string $visiblename Localised name.
     * @param string $description Localised description.
     */
    public function __construct(string $name, string $visiblename, string $description) {
        parent::__construct($name, $visiblename, $description, 0, null);
    }

    /**
     * Load the frameworks the administrator can choose from.
     *
     * @return bool Always true: an empty list of choices is still a valid state.
     */
    public function load_choices() {
        if (is_array($this->choices)) {
            return true;
        }

        $this->choices = [0 => get_string('framework_none', 'local_compalign')];

        if (!api::is_enabled()) {
            $this->description .= ' ' . get_string('framework_nocompetencies', 'local_compalign');

            return true;
        }

        $frameworks = api::list_frameworks('shortname', 'ASC', 0, 0, \context_system::instance(), 'children', true);
        foreach ($frameworks as $framework) {
            $this->choices[(int) $framework->get('id')] = $framework->get('shortname')
                . ' (' . $framework->get('idnumber') . ')';
        }

        return true;
    }
}
