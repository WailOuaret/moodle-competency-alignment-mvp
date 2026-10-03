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

namespace local_compalign\output;

/**
 * Turns a stored error code into a sentence a teacher can understand.
 *
 * Codes come from the service layer and are stored with the analysis. Nothing else is ever shown:
 * no exception message, no response body and no trace.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class error_messages {
    /**
     * The sentence for an error code.
     *
     * @param string|null $code The stored error code.
     * @return string
     */
    public static function for_code(?string $code): string {
        $code = (string) $code;
        $manager = get_string_manager();

        if ($code !== '' && $manager->string_exists('error_' . $code, 'local_compalign')) {
            return get_string('error_' . $code, 'local_compalign');
        }

        // The service refused the request for a reason of its own. Its code is safe: it is a fixed word.
        if (str_starts_with($code, 'service_') && preg_match('/^service_[a-z0-9_]{1,52}$/', $code)) {
            return get_string('error_service', 'local_compalign', substr($code, strlen('service_')));
        }

        return get_string('error_generic', 'local_compalign');
    }
}
