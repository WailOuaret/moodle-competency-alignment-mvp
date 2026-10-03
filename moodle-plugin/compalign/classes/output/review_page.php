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

use core\output\named_templatable;
use core\output\renderable;
use core\output\renderer_base;
use local_compalign\service\analysis_manager;
use local_compalign\service\catalogue_snapshot;
use local_compalign\service\review_manager;

/**
 * The page of one resource: its official links, the state of its analysis, and one card per suggestion.
 *
 * A card shows the competency, its description, the exact evidence, any hierarchy note and the
 * decision form. The technical details (rank, confidence, passage ids) are collapsed. Nothing here
 * shows a reference label, a prompt, hidden model reasoning, raw JSON or a stack trace.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class review_page implements renderable, named_templatable {
    /**
     * Constructor.
     *
     * @param \cm_info $cm The resource.
     * @param bool $supported Whether the plugin can analyse this type of resource.
     * @param \stdClass|null $analysis The latest analysis, if any.
     * @param \stdClass[] $suggestions Its stored suggestions, with evidence and warningslist.
     * @param catalogue_snapshot|null $catalogue The framework as it is now, or null when it cannot be read.
     * @param \stdClass[] $reviews The current user's latest review of each suggestion, by suggestion id.
     * @param string[] $forms The rendered decision form of each suggestion, by suggestion id.
     * @param array[] $links The resource's official competency links.
     * @param array[] $notices Extra notices to show, each with type and text.
     * @param string $actionhtml A rendered button that starts or repeats the analysis, or an empty string.
     */
    public function __construct(
        private \cm_info $cm,
        private bool $supported,
        private ?\stdClass $analysis,
        private array $suggestions,
        private ?catalogue_snapshot $catalogue,
        private array $reviews,
        private array $forms,
        private array $links,
        private array $notices,
        private string $actionhtml,
    ) {
    }

    /**
     * Name of the template that renders this page.
     *
     * @param renderer_base $renderer The renderer.
     * @return string
     */
    public function get_template_name(renderer_base $renderer): string {
        return 'local_compalign/resource';
    }

    /**
     * Export the data for the template.
     *
     * @param renderer_base $output The renderer.
     * @return array Template context.
     */
    public function export_for_template(renderer_base $output): array {
        $cards = [];
        foreach ($this->suggestions as $suggestion) {
            $cards[] = $this->export_card($suggestion);
        }

        return [
            'heading' => get_string('reviewheading', 'local_compalign', $this->cm->get_formatted_name()),
            'typename' => $this->cm->get_module_type_name(),
            'coursename' => format_string($this->cm->get_course()->fullname),
            'backurl' => (new \moodle_url('/local/compalign/index.php', ['courseid' => $this->cm->course]))->out(false),
            'links' => array_map(static fn(array $link): array => [
                'idnumber' => $link['idnumber'],
                'shortname' => $link['shortname'],
            ], $this->links),
            'haslinks' => (bool) $this->links,
            'notices' => array_map(static function (array $notice): array {
                return $notice + [
                    'title' => '',
                    'role' => in_array($notice['type'], ['danger', 'warning'], true) ? 'alert' : 'status',
                ];
            }, array_merge($this->state_notices(), $this->notices)),
            'actionhtml' => $this->actionhtml,
            'hascards' => (bool) $cards,
            'cards' => $cards,
        ];
    }

    /**
     * Notices that describe the state of the analysis.
     *
     * @return array[] Each with type, title and text.
     */
    private function state_notices(): array {
        $analysis = $this->analysis;

        if ($analysis === null) {
            // A resource of an unsupported type is explained by its own notice, not by "none requested".
            return $this->supported ? [['type' => 'info', 'text' => get_string('noanalysis', 'local_compalign')]] : [];
        }

        if ($analysis->status === analysis_manager::STATUS_QUEUED) {
            return [[
                'type' => 'info',
                'title' => get_string('analysis_queued', 'local_compalign'),
                'text' => get_string('analysis_queued_hint', 'local_compalign'),
            ]];
        }

        if ($analysis->status === analysis_manager::STATUS_RUNNING) {
            return [[
                'type' => 'info',
                'title' => get_string('analysis_running', 'local_compalign'),
                'text' => get_string('analysis_running_hint', 'local_compalign'),
            ]];
        }

        if ($analysis->status === analysis_manager::STATUS_FAILED) {
            return [[
                'type' => 'danger',
                'title' => get_string('analysis_failed_heading', 'local_compalign'),
                'text' => error_messages::for_code($analysis->errorcode) . ' '
                    . get_string('analysis_failed_hint', 'local_compalign'),
            ]];
        }

        $notices = [];
        if ($analysis->backend === 'mock') {
            $notices[] = ['type' => 'warning', 'text' => get_string('backend_mock_notice', 'local_compalign')];
        }

        if (!empty($analysis->abstained)) {
            $notices[] = ['type' => 'info', 'text' => get_string('analysisabstained', 'local_compalign')];
        }

        if ($analysis->completeness === 'partial') {
            $notices[] = ['type' => 'warning', 'text' => get_string('analysispartial', 'local_compalign')];
        }

        $notices[] = ['type' => 'info', 'text' => get_string('writebackoffnotice', 'local_compalign')];

        return $notices;
    }

    /**
     * Describe one suggestion for the card template.
     *
     * @param \stdClass $suggestion The stored suggestion.
     * @return array Template context for one card.
     */
    private function export_card(\stdClass $suggestion): array {
        $idnumber = (string) $suggestion->competencyidnumber;
        $competency = $this->catalogue ? $this->catalogue->find($idnumber) : null;
        $fragments = array_values(array_unique(array_map(
            static fn(\stdClass $item): string => (string) $item->fragmentid,
            $suggestion->evidence
        )));
        $warnings = [];
        foreach ($suggestion->warningslist as $warning) {
            $warnings[] = ['text' => $this->warning_text($warning)];
        }

        return [
            'id' => (int) $suggestion->id,
            'code' => $idnumber,
            'name' => $competency['shortname'] ?? $idnumber,
            'description' => $competency['description'] ?? '',
            'evidence' => array_map(static fn(\stdClass $item): array => ['quote' => $item->evidencetext], $suggestion->evidence),
            'haswarnings' => (bool) $warnings,
            'warnings' => $warnings,
            'bm25rank' => $suggestion->bm25rank !== null
                ? (int) $suggestion->bm25rank
                : get_string('unknownvalue', 'local_compalign'),
            'confidence' => $suggestion->confidence !== null
                ? format_float((float) $suggestion->confidence, 2)
                : get_string('unknownvalue', 'local_compalign'),
            'supportcount' => (int) $suggestion->supportcount,
            'passages' => implode(', ', $fragments),
            'reviewed' => $this->export_review($this->reviews[(int) $suggestion->id] ?? null),
            'form' => $this->forms[(int) $suggestion->id] ?? '',
        ];
    }

    /**
     * Describe the user's latest decision on a suggestion.
     *
     * @param \stdClass|null $review The review, if any.
     * @return array|null Summary and when it was saved, or null when not yet reviewed.
     */
    private function export_review(?\stdClass $review): ?array {
        if ($review === null) {
            return null;
        }

        $summary = get_string('decision_' . $review->decision . '_summary', 'local_compalign', $this->competency_label(
            $review->finalcompetencyidnumber
        ));

        return [
            'summary' => $summary,
            'saved' => get_string('revisionsaved', 'local_compalign', (object) [
                'revision' => (int) $review->revision,
                'time' => userdate((int) $review->timecreated),
            ]),
        ];
    }

    /**
     * The sentence for a hierarchy warning.
     *
     * @param array $warning code, role and related competency of the warning.
     * @return string
     */
    private function warning_text(array $warning): string {
        $key = 'warning_' . $warning['code'] . '_' . ($warning['role'] ?? '');

        if (!empty($warning['related']) && get_string_manager()->string_exists($key, 'local_compalign')) {
            return get_string($key, 'local_compalign', $this->competency_label($warning['related']));
        }

        return get_string('warning_generic', 'local_compalign');
    }

    /**
     * A competency's idnumber and name, as far as the framework can say.
     *
     * @param string|null $idnumber The competency idnumber.
     * @return string
     */
    private function competency_label(?string $idnumber): string {
        if ($idnumber === null || $idnumber === '') {
            return '';
        }

        $competency = $this->catalogue ? $this->catalogue->find($idnumber) : null;

        return $competency ? $idnumber . ' ' . $competency['shortname'] : $idnumber;
    }
}
