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
 * Split a stored competency description into what a teacher should read first
 * and the catalogue metadata that belongs under technical details.
 *
 * This changes only the review card. The text sent to the alignment service is
 * the catalogue description, unchanged.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class competency_display {
    /** Labels the imported catalogue appends after the pedagogical description. */
    private const MARKERS = ['English label:', 'UTC competency ID:', 'Source URI:'];

    /**
     * Separate the pedagogical sentence from catalogue metadata.
     *
     * A description without those labels is returned whole. Nothing is dropped:
     * the English label and the source address are returned for the technical
     * details. The UTC id is returned only when it is not the competency id
     * already shown on the card.
     *
     * @param string $description Plain-text description from the catalogue.
     * @param string $idnumber The competency id shown on the card.
     * @return array{main: string, englishlabel: string, sourceuri: string, extraid: string}
     */
    public static function split(string $description, string $idnumber): array {
        $cut = strlen($description);
        foreach (self::MARKERS as $marker) {
            $pos = strpos($description, $marker);
            if ($pos !== false && $pos < $cut) {
                $cut = $pos;
            }
        }

        $main = trim(substr($description, 0, $cut));
        $rest = trim(substr($description, $cut));
        $english = self::between($rest, 'English label:', self::MARKERS);
        $utc = self::between($rest, 'UTC competency ID:', self::MARKERS);
        $uri = self::between($rest, 'Source URI:', self::MARKERS);

        if ($main === '' && $rest === '') {
            $main = trim($description);
        }

        return [
            'main' => $main,
            'englishlabel' => $english,
            'sourceuri' => $uri,
            'extraid' => ($utc !== '' && $utc !== $idnumber) ? $utc : '',
        ];
    }

    /**
     * The text after one label, up to the next catalogue label.
     *
     * @param string $text The metadata tail.
     * @param string $label The label to read.
     * @param string[] $markers Every catalogue label.
     * @return string
     */
    private static function between(string $text, string $label, array $markers): string {
        $start = strpos($text, $label);
        if ($start === false) {
            return '';
        }
        $start += strlen($label);
        $end = strlen($text);
        foreach ($markers as $marker) {
            if ($marker === $label) {
                continue;
            }
            $pos = strpos($text, $marker, $start);
            if ($pos !== false && $pos < $end) {
                $end = $pos;
            }
        }
        return trim(substr($text, $start, $end - $start));
    }
}
