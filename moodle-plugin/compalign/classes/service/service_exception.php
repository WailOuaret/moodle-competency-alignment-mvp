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
 * A failure to talk to the alignment service.
 *
 * The message is written for administrators and never contains a token, a request
 * header or a response body. The stable error code is what gets stored and shown.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class service_exception extends \Exception {
    /** @var string Stable machine-readable code. */
    private string $errorcode;

    /**
     * Constructor.
     *
     * @param string $errorcode Stable machine-readable code.
     * @param string $message Safe description for administrators.
     * @param \Throwable|null $previous Underlying cause. Never rendered to users.
     */
    public function __construct(string $errorcode, string $message = '', ?\Throwable $previous = null) {
        parent::__construct($message !== '' ? $message : $errorcode, 0, $previous);
        $this->errorcode = $errorcode;
    }

    /**
     * The stable machine-readable code.
     *
     * @return string
     */
    public function get_error_code(): string {
        return $this->errorcode;
    }
}
