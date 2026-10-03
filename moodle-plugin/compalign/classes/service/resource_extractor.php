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
        return $cm->modname === 'page';
    }

    /**
     * Read a Page and describe it as a service resource.
     *
     * @param cm_info $cm The Page course module, as visible to the current user.
     * @return array{resource: array<string, string>, hash: string} The resource for the request, and a
     *         digest of everything in it that can change the analysis.
     * @throws analysis_exception When the Page cannot or should not be analysed.
     */
    public function extract(cm_info $cm): array {
        global $CFG, $DB;

        require_once($CFG->dirroot . '/course/lib.php');

        if (!self::supports($cm)) {
            throw new analysis_exception('unsupported_resource_type');
        }

        if (!$cm->uservisible) {
            throw new analysis_exception('resource_not_accessible');
        }

        $page = $DB->get_record('page', ['id' => $cm->instance], 'id, name, intro, content');
        if (!$page) {
            throw new analysis_exception('resource_missing');
        }

        $title = self::collapse($page->name);
        $text = self::combine_text(self::html_to_text($page->intro), self::html_to_text($page->content));

        if ($text === '') {
            throw new analysis_exception('resource_empty');
        }

        if (mb_strlen($text) > self::MAX_TEXT_CHARS) {
            throw new analysis_exception('resource_too_large');
        }

        $course = $cm->get_course();
        $resource = [
            'resource_id' => 'moodle:page:' . $page->id,
            'resource_type' => self::TYPE_PAGE,
            'course_id' => (string) $cm->course,
            'course_module_id' => (string) $cm->id,
            'title' => $title,
            'text' => $text,
            'search_text' => self::combine_text($title, $text),
            'course_shortname' => self::collapse((string) $course->shortname),
            'course_fullname' => self::collapse((string) $course->fullname),
            'section_name' => self::collapse((string) get_section_name($course, $cm->sectionnum)),
            'activity_name' => $title,
        ];

        return [
            'resource' => array_filter($resource, static fn(string $value): bool => $value !== ''),
            'hash' => self::hash($resource),
        ];
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
        $content = [
            $resource['resource_type'] ?? '',
            $resource['title'] ?? '',
            $resource['text'] ?? '',
            $resource['course_fullname'] ?? '',
            $resource['section_name'] ?? '',
            $resource['activity_name'] ?? '',
        ];

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
