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
 * The study boundary stored on each analysis when it is created.
 *
 * The value is copied from the plugin setting at that moment and is not
 * recomputed from the clock later.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class study_phase {
    /** Local development, including automated tests. */
    public const DEVELOPMENT = 'development';

    /** A controlled live-model check, kept apart from the teacher study. */
    public const LIVE_VERIFICATION = 'development_live_verification';

    /** The teacher study. */
    public const PILOT = 'pilot';

    /** Rows that must not enter a research export of the study. */
    public const EXCLUDED = 'excluded';

    /** @var string[] */
    public const ALL = [
        self::DEVELOPMENT,
        self::LIVE_VERIFICATION,
        self::PILOT,
        self::EXCLUDED,
    ];

    /**
     * The phase new analyses should be labelled with.
     *
     * @return string One of ALL.
     */
    public static function current(): string {
        $value = (string) get_config('local_compalign', 'studyphase');
        if (!in_array($value, self::ALL, true)) {
            return self::DEVELOPMENT;
        }
        return $value;
    }
}
