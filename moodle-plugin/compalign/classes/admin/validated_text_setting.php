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

/**
 * A text setting that applies one extra validation rule after the parameter type check.
 *
 * The rule is a callable that receives the trimmed value and returns null when it is
 * acceptable, or the localised error message to show the administrator.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class validated_text_setting extends \admin_setting_configtext {
    /** @var callable Returns null when the value is valid, otherwise an error message. */
    private $rule;

    /**
     * Constructor.
     *
     * @param string $name Setting name, for example local_compalign/serviceurl.
     * @param string $visiblename Localised name.
     * @param string $description Localised description.
     * @param string $defaultsetting Default value.
     * @param string $paramtype PARAM_* type the value is cleaned with.
     * @param int $size Width of the input.
     * @param callable $rule Extra validation rule.
     */
    public function __construct(
        string $name,
        string $visiblename,
        string $description,
        string $defaultsetting,
        string $paramtype,
        int $size,
        callable $rule,
    ) {
        $this->rule = $rule;
        parent::__construct($name, $visiblename, $description, $defaultsetting, $paramtype, $size);
    }

    /**
     * Check the parameter type first, then the extra rule.
     *
     * @param string $data The submitted value.
     * @return true|string True when valid, otherwise the error message.
     */
    public function validate($data) {
        $result = parent::validate($data);
        if ($result !== true) {
            return $result;
        }

        $error = ($this->rule)(trim((string) $data));

        return $error === null ? true : $error;
    }
}
