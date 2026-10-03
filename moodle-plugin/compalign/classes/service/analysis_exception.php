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
 * A failure to prepare, run or store an analysis.
 *
 * Carries a stable error code that is stored on the analysis and mapped to a language
 * string for the teacher. The message and details are for administrators: they never
 * contain a token, a request header or a response body.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class analysis_exception extends \Exception {
    /** @var string Stable machine-readable code. */
    private string $errorcode;

    /** @var string[] Specific problems, for example one per unusable competency. */
    private array $details;

    /**
     * Constructor.
     *
     * @param string $errorcode Stable machine-readable code.
     * @param string $message Safe description for administrators.
     * @param string[] $details Specific problems, already safe to show an administrator.
     * @param \Throwable|null $previous Underlying cause. Never rendered.
     */
    public function __construct(
        string $errorcode,
        string $message = '',
        array $details = [],
        ?\Throwable $previous = null,
    ) {
        parent::__construct($message !== '' ? $message : $errorcode, 0, $previous);
        $this->errorcode = $errorcode;
        $this->details = $details;
    }

    /**
     * The stable machine-readable code.
     *
     * @return string
     */
    public function get_error_code(): string {
        return $this->errorcode;
    }

    /**
     * Specific problems behind the failure.
     *
     * @return string[]
     */
    public function get_details(): array {
        return $this->details;
    }
}
