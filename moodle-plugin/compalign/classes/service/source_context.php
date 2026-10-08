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

use local_compalign\output\error_messages;
use local_compalign\resource\file_item;
use local_compalign\resource\registry;

/**
 * Shows one quotation inside the resource text it was taken from.
 *
 * The text is the canonical extract already stored or read from the activity.
 * This class does not call the alignment service and does not start an analysis.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class source_context {
    /**
     * Plain text of an extract result. File text comes from the extraction cache.
     *
     * @param array $packed Result of resource_extractor::extract().
     * @return string|null Null when a file has not been extracted yet.
     */
    public static function canonical_text(array $packed): ?string {
        $text = (string) ($packed['resource']['text'] ?? '');
        if ($text !== '') {
            return $text;
        }

        $cached = self::cached_file($packed);
        if ($cached === null) {
            return isset($packed['resource']['content_hash']) ? null : '';
        }

        return $cached['text'];
    }

    /**
     * Build the source view for a quote that belongs to this resource.
     *
     * @param \cm_info $cm The activity. The caller has already checked access.
     * @param int $courseid The course the request names.
     * @param string $resourceid The stable resource id.
     * @param string $quote The quotation to highlight.
     * @param \context $context Module context.
     * @return array View data: title, type, provenance, found, html, openurl, error.
     */
    public function build(
        \cm_info $cm,
        int $courseid,
        string $resourceid,
        string $quote,
        \context $context
    ): array {
        require_capability('local/compalign:view', $context);
        if ((int) $cm->course !== $courseid || !$cm->uservisible) {
            throw new analysis_exception('resource_wrong_course');
        }

        $item = null;
        foreach (registry::enumerate($cm) as $candidate) {
            if ($candidate->resourceid === $resourceid) {
                $item = $candidate;
                break;
            }
        }
        if ($item === null) {
            throw new analysis_exception('resource_missing');
        }

        try {
            $packed = (new resource_extractor())->extract($cm, $resourceid);
        } catch (analysis_exception $exception) {
            return $this->shell($cm, $item, '', false, '', $exception->get_error_code());
        }

        $text = self::canonical_text($packed);
        if ($text === null) {
            return $this->shell($cm, $item, $this->provenance($packed, $quote, ''), false, '', 'source_missing');
        }

        $rendered = quote_span::render($text, $quote);
        $provenance = $this->provenance($packed, $quote, $text);

        return $this->shell(
            $cm,
            $item,
            $provenance,
            $rendered['found'],
            $rendered['html'],
            $rendered['found'] ? '' : 'quote_not_found'
        );
    }

    /**
     * Load a stored model quotation only when it belongs to this resource.
     *
     * @param int $evidenceid The evidence row.
     * @param \cm_info $cm The activity.
     * @param string $resourceid The resource.
     * @return string The quotation.
     */
    public function quote_from_evidence(int $evidenceid, \cm_info $cm, string $resourceid): string {
        global $DB;

        $sql = "SELECT e.evidencetext
                  FROM {local_compalign_evidence} e
                  JOIN {local_compalign_sugg} s ON s.id = e.suggestionid
                  JOIN {local_compalign_analysis} a ON a.id = s.analysisid
                 WHERE e.id = :evidenceid AND a.cmid = :cmid AND a.courseid = :courseid AND a.resourceid = :resourceid";
        $quote = $DB->get_field_sql($sql, [
            'evidenceid' => $evidenceid,
            'cmid' => (int) $cm->id,
            'courseid' => (int) $cm->course,
            'resourceid' => $resourceid,
        ]);
        if ($quote === false || $quote === null) {
            throw new analysis_exception('evidence_invalid');
        }

        return (string) $quote;
    }

    /**
     * Load teacher-supplied evidence only when the relationship belongs to this resource.
     *
     * @param int $manualid The relationship id.
     * @param \cm_info $cm The activity.
     * @param string $resourceid The resource.
     * @return string The quotation. Empty when the teacher gave none.
     */
    public function quote_from_manual(int $manualid, \cm_info $cm, string $resourceid): string {
        global $DB;

        $record = $DB->get_record('local_compalign_manualrel', [
            'id' => $manualid,
            'cmid' => (int) $cm->id,
            'courseid' => (int) $cm->course,
            'resourceid' => $resourceid,
        ]);
        if (!$record) {
            throw new analysis_exception('evidence_invalid');
        }

        return (string) ($record->evidencetext ?? '');
    }

    /**
     * Cached file text and its segments.
     *
     * @param array $packed Extract result.
     * @return array{text: string, segments: array}|null
     */
    private static function cached_file(array $packed): ?array {
        global $DB;

        $hash = (string) ($packed['resource']['content_hash'] ?? '');
        if ($hash === '') {
            return null;
        }
        $version = (string) ($packed['resource']['extractor_version'] ?? file_item::EXTRACTOR_VERSION);
        $cached = $DB->get_record('local_compalign_extract', [
            'contenthash' => $hash,
            'extractorversion' => $version,
        ]);
        if (!$cached) {
            return null;
        }
        $segments = json_decode((string) $cached->provenance, true);

        return [
            'text' => (string) $cached->canonicaltext,
            'segments' => is_array($segments) ? $segments : [],
        ];
    }

    /**
     * Human provenance for the quotation: page, slide, cue, heading or activity label.
     *
     * @param array $packed Extract result.
     * @param string $quote The quotation.
     * @param string $text Canonical text already loaded, used only as a fallback.
     * @return string
     */
    private function provenance(array $packed, string $quote, string $text): string {
        $base = trim((string) ($packed['provenance']['label'] ?? ''));
        $filename = trim((string) ($packed['provenance']['filename'] ?? $packed['resource']['filename'] ?? ''));
        $segments = $packed['provenance']['segments'] ?? [];
        $cached = self::cached_file($packed);
        if ($cached !== null && !$segments) {
            $segments = $cached['segments'];
        }

        $matched = $this->matching_segment(is_array($segments) ? $segments : [], $quote);
        $detail = '';
        if (is_array($matched)) {
            $heading = trim((string) ($matched['heading'] ?? ''));
            $detail = match ($matched['kind'] ?? '') {
                'page' => get_string('evidence_page', 'local_compalign', $matched['number'] ?? ''),
                'slide' => get_string('evidence_slide', 'local_compalign', $matched['number'] ?? ''),
                'paragraph', 'table' => $heading !== ''
                    ? get_string('evidence_section', 'local_compalign', $heading)
                    : get_string('evidence_paragraph', 'local_compalign', $matched['number'] ?? ''),
                'cue' => get_string('evidence_time', 'local_compalign', (object) [
                    'start' => $matched['start'] ?? '',
                    'end' => $matched['end'] ?? '',
                ]),
                default => '',
            };
        }

        $parts = array_filter([$filename, $base, $detail], static fn(string $part): bool => $part !== '');
        if ($parts) {
            return implode(' · ', $parts);
        }

        return $text === '' ? '' : get_string('source_provenance_resource', 'local_compalign');
    }

    /**
     * The segment whose text contains the quotation.
     *
     * @param array $segments Provenance segments.
     * @param string $quote The quotation.
     * @return array|null
     */
    private function matching_segment(array $segments, string $quote): ?array {
        $needle = response_validator::normalise_for_comparison($quote);
        if ($needle === '') {
            return null;
        }
        foreach ($segments as $segment) {
            if (!is_array($segment)) {
                continue;
            }
            $haystack = response_validator::normalise_for_comparison((string) ($segment['text'] ?? ''));
            if ($haystack !== '' && str_contains($haystack, $needle)) {
                return $segment;
            }
        }

        return null;
    }

    /**
     * The fields the source template needs.
     *
     * @param \cm_info $cm The activity.
     * @param \local_compalign\resource\item $item The resource.
     * @param string $provenance Provenance label.
     * @param bool $found Whether the quote was highlighted.
     * @param string $html Escaped window. May contain a mark element.
     * @param string $error Error code, or empty.
     * @return array
     */
    private function shell(\cm_info $cm, \local_compalign\resource\item $item, string $provenance, bool $found, string $html, string $error): array {
        return [
            'title' => $item->title !== '' ? $item->title : $cm->get_formatted_name(),
            'type' => $cm->get_module_type_name(),
            'resourcetype' => $item->resourcetype,
            'provenance' => $provenance,
            'found' => $found,
            'html' => $html,
            'error' => $error,
            'errormessage' => $error === '' ? '' : error_messages::for_code($error),
            'openurl' => $cm->url ? $cm->url->out(false) : '',
            'backurl' => (new \moodle_url('/local/compalign/review.php', [
                'cmid' => $cm->id,
                'item' => $item->resourceid,
            ]))->out(false),
        ];
    }
}
