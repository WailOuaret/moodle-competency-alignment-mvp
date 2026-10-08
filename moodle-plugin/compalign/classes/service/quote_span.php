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
 * Finds a quotation inside source text and renders a highlighted window.
 *
 * Matching uses the same whitespace normalisation as evidence validation, so a
 * quote still matches when a line break was stored as a space. The highlighted
 * window is escaped. The only markup added is a mark element around the quote.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class quote_span {
    /** Characters of source kept on each side of the quotation. */
    public const RADIUS = 280;

    /**
     * Locate a quote and return an escaped window.
     *
     * @param string $text Canonical plain text.
     * @param string $quote The quotation to highlight.
     * @return array{found: bool, html: string, match: string}
     */
    public static function render(string $text, string $quote): array {
        $span = self::locate($text, $quote);
        if ($span === null) {
            return ['found' => false, 'html' => '', 'match' => ''];
        }

        [$start, $length] = $span;
        $end = $start + $length;
        $windowstart = max(0, $start - self::RADIUS);
        $windowend = min(mb_strlen($text), $end + self::RADIUS);
        $windowstart = self::snap($text, $windowstart, $start, false);
        $windowend = self::snap($text, $windowend, $end, true);

        $before = s(mb_substr($text, $windowstart, $start - $windowstart));
        $match = s(mb_substr($text, $start, $length));
        $after = s(mb_substr($text, $end, $windowend - $end));
        $prefix = $windowstart > 0 ? s('… ') : '';
        $suffix = $windowend < mb_strlen($text) ? s(' …') : '';

        return [
            'found' => true,
            'html' => $prefix . $before . '<mark>' . $match . '</mark>' . $after . $suffix,
            'match' => $match,
        ];
    }

    /**
     * Whether the quote occurs in the text after normalisation.
     *
     * @param string $text Canonical plain text.
     * @param string $quote The quotation.
     * @return bool
     */
    public static function contains(string $text, string $quote): bool {
        return self::locate($text, $quote) !== null;
    }

    /**
     * Character offset and length of the quote inside the original text.
     *
     * @param string $text Canonical plain text.
     * @param string $quote The quotation.
     * @return array{0: int, 1: int}|null
     */
    public static function locate(string $text, string $quote): ?array {
        $needle = response_validator::normalise_for_comparison($quote);
        if ($needle === '') {
            return null;
        }

        $parts = preg_split('/ /u', $needle, -1, PREG_SPLIT_NO_EMPTY);
        if (!$parts) {
            return null;
        }

        $pattern = '/' . implode('\\s+', array_map(static fn(string $part): string => preg_quote($part, '/'), $parts)) . '/u';
        if (!preg_match($pattern, $text, $matches, PREG_OFFSET_CAPTURE)) {
            return null;
        }

        $bytes = (int) $matches[0][1];
        $start = mb_strlen(substr($text, 0, $bytes), 'UTF-8');
        $length = mb_strlen($matches[0][0], 'UTF-8');

        return [$start, $length];
    }

    /**
     * Move a window edge to a nearby space so words are not cut in half.
     *
     * @param string $text The source.
     * @param int $edge The candidate edge.
     * @param int $limit Do not cross the quotation.
     * @param bool $forward True when snapping the end.
     * @return int
     */
    private static function snap(string $text, int $edge, int $limit, bool $forward): int {
        if ($edge === $limit) {
            return $edge;
        }
        $slice = $forward
            ? mb_substr($text, $limit, $edge - $limit)
            : mb_substr($text, $edge, $limit - $edge);
        $space = $forward ? mb_strrpos($slice, ' ') : mb_strpos($slice, ' ');
        if ($space === false) {
            return $edge;
        }

        return $forward ? $limit + $space + 1 : $edge + $space + 1;
    }
}
