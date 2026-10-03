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

/**
 * The outcome of checking the connection to the alignment service.
 *
 * Holds a status code and, for diagnosis, the HTTP status. It never holds a body,
 * a header or an exception message.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class connection_result {
    /**
     * Constructor.
     *
     * @param string $status One of the alignment_client::STATUS_* constants.
     * @param int|null $httpstatus HTTP status of the deciding response, if there was one.
     * @param string|null $reason Short stable reason code, if the status needs one.
     */
    public function __construct(
        public readonly string $status,
        public readonly ?int $httpstatus = null,
        public readonly ?string $reason = null,
    ) {
    }

    /**
     * Whether the service answered and accepted the token.
     *
     * @return bool
     */
    public function is_connected(): bool {
        return $this->status === alignment_client::STATUS_CONNECTED;
    }
}
