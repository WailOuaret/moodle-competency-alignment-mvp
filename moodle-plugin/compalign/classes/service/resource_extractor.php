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

use cm_info;
use local_compalign\resource\registry;

/**
 * Turns a Moodle Page into the plain-text resource the alignment service analyses.
 *
 * Only teacher-authored content leaves Moodle: the title, the description and the body of
 * the Page, plus the names of its course and section. Nothing about learners is read.
 * The text follows the normalisation of the frozen research pipeline: the description and
 * the body are each reduced to plain text and joined by a blank line.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class resource_extractor {
    /** Resource type sent to the service for a Moodle Page. */
    public const TYPE_PAGE = 'page';

    /** Longest text accepted. It must not exceed the limit the service enforces. */
    public const MAX_TEXT_CHARS = 200000;

    /**
     * Whether the resource type can be analysed in this prototype.
     *
     * @param cm_info $cm The course module.
     * @return bool
     */
    public static function supports(cm_info $cm): bool {
        return registry::supports($cm);
    }

    /**
     * Read a Page and describe it as a service resource.
     *
     * @param cm_info $cm The course module, as visible to the current user.
     * @param string $resourceid Empty when the activity has exactly one analytical item.
     * @return array{resource: array<string, string>, hash: string} The resource for the request, and a
     *         digest of everything in it that can change the analysis.
     * @throws analysis_exception When the resource cannot or should not be analysed.
     */
    public function extract(cm_info $cm, string $resourceid = ''): array {
        if (!self::supports($cm)) {
            throw new analysis_exception('unsupported_resource_type');
        }
        if (!$cm->uservisible) {
            throw new analysis_exception('resource_not_accessible');
        }

        return registry::extract($cm, $resourceid);
    }

    /**
     * Digest of every part of a resource that can change an analysis.
     *
     * Identifiers are left out: the same words under another id are the same analysis.
     *
     * @param array<string, string> $resource The resource as built by extract().
     * @return string sha256: followed by the hex digest.
     */
    public static function hash(array $resource): string {
        // A file is fingerprinted from its bytes and the extractor version, so a
        // parser change can invalidate an analysis even when the file is unchanged.
        // A Page still hashes the words only. Identifiers stay out of both.
        if (!empty($resource['content_hash'])) {
            $content = [
                $resource['resource_type'] ?? '',
                $resource['content_hash'],
                $resource['extractor_version'] ?? '',
                $resource['filename'] ?? '',
            ];
        } else {
            $content = [
                $resource['resource_type'] ?? '',
                $resource['title'] ?? '',
                $resource['text'] ?? '',
                $resource['course_fullname'] ?? '',
                $resource['section_name'] ?? '',
                $resource['activity_name'] ?? '',
            ];
        }

        return 'sha256:' . hash('sha256', json_encode(
            $content,
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
        ));
    }

    /**
     * Reduce HTML to plain text.
     *
     * Scripts and styles are dropped and every tag becomes a space, so words in neighbouring
     * elements stay apart. HTML is never executed or rendered here.
     *
     * @param string|null $html Moodle HTML.
     * @return string Plain text with whitespace collapsed.
     */
    public static function html_to_text(?string $html): string {
        $html = (string) $html;
        if (trim($html) === '') {
            return '';
        }

        $stripped = preg_replace('#<(script|style|noscript|template)\b[^>]*>.*?</\1\s*>#is', ' ', $html);
        $stripped = preg_replace('/<!--.*?-->/s', ' ', $stripped ?? $html);
        $text = preg_replace('/<[^>]*>/', ' ', $stripped ?? $html);

        return self::collapse(html_entity_decode((string) $text, ENT_QUOTES | ENT_HTML5, 'UTF-8'));
    }

    /**
     * Join non-empty parts by a blank line, skipping a part that repeats an earlier one.
     *
     * @param string ...$parts The parts.
     * @return string The parts joined by a blank line.
     */
    public static function combine_text(string ...$parts): string {
        $unique = [];
        $seen = [];

        foreach ($parts as $part) {
            $part = self::collapse($part);
            $key = mb_strtolower($part);

            if ($part === '' || isset($seen[$key])) {
                continue;
            }

            $seen[$key] = true;
            $unique[] = $part;
        }

        return implode("\n\n", $unique);
    }

    /**
     * Collapse every run of whitespace, non-breaking spaces included, into one space.
     *
     * @param string $text Any text.
     * @return string The collapsed, trimmed text.
     */
    private static function collapse(string $text): string {
        return trim((string) preg_replace('/\s+/u', ' ', $text));
    }
}
