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
use local_compalign\service\alignment_client;
use local_compalign\service\analysis_exception;
use local_compalign\service\analysis_manager;
use local_compalign\service\competency_catalogue;
use local_compalign\service\competency_links;
use local_compalign\service\resource_extractor;
use local_compalign\service\service_exception;

/**
 * The course dashboard: every resource of a course with its analysis status and official links.
 *
 * Only Pages can be analysed in this prototype. Every other resource type says so instead of being
 * processed in silence. When the assistant is not ready (no framework, no service address, and so
 * on) the page says why and offers no analysis button.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class dashboard implements renderable, named_templatable {
    /** Badge style for each status. The label is always shown too, so colour is never the only signal. */
    private const BADGES = [
        'none' => 'secondary',
        'queued' => 'info',
        'running' => 'info',
        'ready' => 'primary',
        'nosuggestion' => 'secondary',
        'reviewed' => 'success',
        'failed' => 'danger',
    ];

    /**
     * Constructor.
     *
     * @param \stdClass $course The course.
     * @param array[] $issues Reasons the assistant is not ready, each with text and details.
     * @param array[] $rows One entry per resource, as built by create().
     * @param bool $showoverviewlink Whether to link to the plugin overview.
     */
    public function __construct(
        private \stdClass $course,
        private array $issues,
        private array $rows,
        private bool $showoverviewlink,
    ) {
    }

    /**
     * Gather what the dashboard shows for a course.
     *
     * @param \stdClass $course The course.
     * @param int $userid The logged-in user: whose resources are visible and whose reviews are counted.
     * @return self
     */
    public static function create(\stdClass $course, int $userid): self {
        $canmanage = has_capability('local/compalign:manage', \context_system::instance());
        $issues = self::find_issues($canmanage);
        $modinfo = get_fast_modinfo($course, $userid);

        $cms = array_filter(
            $modinfo->get_cms(),
            static fn(\cm_info $cm): bool => $cm->uservisible && !$cm->deletioninprogress && $cm->modname !== 'label'
        );
        $latest = self::latest_analyses((int) $course->id);
        [$totals, $reviewed] = self::review_progress(
            array_map(static fn(\stdClass $analysis): int => (int) $analysis->id, $latest),
            $userid
        );
        $byanalysis = [];
        foreach ($latest as $cmid => $analysis) {
            $byanalysis[$cmid] = [
                'analysis' => $analysis,
                'total' => (int) ($totals[$analysis->id] ?? 0),
                'reviewed' => (int) ($reviewed[$analysis->id] ?? 0),
            ];
        }

        $rows = [];
        foreach ($cms as $cm) {
            $rows[] = [
                'cm' => $cm,
                'state' => $byanalysis[$cm->id] ?? null,
                'links' => competency_links::list_for_cm($cm),
                'canstart' => !$issues && has_capability('local/compalign:analyse', \context_module::instance($cm->id)),
            ];
        }

        return new self($course, $issues, $rows, $canmanage);
    }

    /**
     * The status key for a resource.
     *
     * @param \stdClass|null $analysis The latest analysis, if any.
     * @param int $total How many suggestions it stored.
     * @param int $reviewed How many of them the user has reviewed.
     * @return string none, queued, running, ready, nosuggestion, reviewed or failed.
     */
    public static function status_key(?\stdClass $analysis, int $total, int $reviewed): string {
        if ($analysis === null) {
            return 'none';
        }

        return match ($analysis->status) {
            analysis_manager::STATUS_QUEUED => 'queued',
            analysis_manager::STATUS_RUNNING => 'running',
            analysis_manager::STATUS_FAILED => 'failed',
            default => $total === 0 ? 'nosuggestion' : ($reviewed >= $total ? 'reviewed' : 'ready'),
        };
    }

    /**
     * Name of the template that renders this page.
     *
     * @param renderer_base $renderer The renderer.
     * @return string
     */
    public function get_template_name(renderer_base $renderer): string {
        return 'local_compalign/dashboard';
    }

    /**
     * Export the data for the template.
     *
     * @param renderer_base $output The renderer.
     * @return array Template context.
     */
    public function export_for_template(renderer_base $output): array {
        $rows = [];
        foreach ($this->rows as $row) {
            $rows[] = $this->export_row($output, $row);
        }

        return [
            'issues' => array_map(static fn(array $issue): array => [
                'text' => $issue['text'],
                'hasdetails' => !empty($issue['details']),
                'details' => array_map(static fn(string $text): array => ['text' => $text], $issue['details']),
            ], $this->issues),
            'hasissues' => (bool) $this->issues,
            'hasrows' => (bool) $rows,
            'rows' => $rows,
            'showoverviewlink' => $this->showoverviewlink,
            'overviewurl' => (new \moodle_url('/local/compalign/index.php'))->out(false),
        ];
    }

    /**
     * Describe one resource for the template.
     *
     * @param renderer_base $output The renderer.
     * @param array $row The resource, as built by create().
     * @return array Template context for one table row.
     */
    private function export_row(renderer_base $output, array $row): array {
        /** @var \cm_info $cm */
        $cm = $row['cm'];
        $analysis = $row['state']['analysis'] ?? null;
        $total = $row['state']['total'] ?? 0;
        $reviewed = $row['state']['reviewed'] ?? 0;
        $key = self::status_key($analysis, $total, $reviewed);
        $reviewurl = new \moodle_url('/local/compalign/review.php', ['cmid' => $cm->id]);

        $action = [];
        if (!resource_extractor::supports($cm)) {
            $action['text'] = get_string('unsupportedtype', 'local_compalign');
        } else if ($analysis !== null) {
            $action = ['url' => $reviewurl->out(false), 'label' => get_string('viewsuggestions', 'local_compalign')];
        } else if ($row['canstart']) {
            $action['html'] = $output->render(new \single_button(
                new \moodle_url($reviewurl, ['action' => 'analyse']),
                get_string('suggestcompetencies', 'local_compalign'),
                'post',
                \single_button::BUTTON_PRIMARY
            ));
        }

        return [
            'name' => $cm->get_formatted_name(),
            'url' => $cm->url ? $cm->url->out(false) : '',
            'typename' => $cm->get_module_type_name(),
            'statuskey' => $key,
            'statuslabel' => get_string('analysis_' . $key, 'local_compalign'),
            'statustype' => self::BADGES[$key],
            'progress' => ($key === 'ready' && $reviewed > 0)
                ? get_string('analysis_progress', 'local_compalign', (object) ['reviewed' => $reviewed, 'total' => $total])
                : '',
            'links' => array_map(static fn(array $link): array => [
                'text' => $link['idnumber'] . ' ' . $link['shortname'],
            ], $row['links']),
            'haslinks' => (bool) $row['links'],
            'action' => $action,
        ];
    }

    /**
     * Why the assistant cannot analyse anything yet. Nothing here makes a network call.
     *
     * @param bool $detailed Whether to include the specific problems. Administrators see them.
     * @return array[] Each with text and details.
     */
    private static function find_issues(bool $detailed): array {
        $issues = [];

        try {
            alignment_client::from_config();
        } catch (service_exception $exception) {
            $issues[] = ['text' => error_messages::for_code($exception->get_error_code()), 'details' => []];
        }

        try {
            (new competency_catalogue())->build();
        } catch (analysis_exception $exception) {
            $issues[] = [
                'text' => error_messages::for_code($exception->get_error_code()),
                'details' => $detailed ? $exception->get_details() : [],
            ];
        }

        return $issues;
    }

    /**
     * The latest analysis of every resource of a course.
     *
     * @param int $courseid The course.
     * @return \stdClass[] Analyses keyed by course module id.
     */
    private static function latest_analyses(int $courseid): array {
        global $DB;

        $sql = "SELECT a.*
                  FROM {local_compalign_analysis} a
                  JOIN (SELECT cmid, MAX(id) AS maxid
                          FROM {local_compalign_analysis}
                         WHERE courseid = :courseid
                      GROUP BY cmid) latest ON latest.maxid = a.id";

        $byresource = [];
        foreach ($DB->get_records_sql($sql, ['courseid' => $courseid]) as $analysis) {
            $byresource[(int) $analysis->cmid] = $analysis;
        }

        return $byresource;
    }

    /**
     * How many suggestions each analysis has and how many of them one user has reviewed.
     *
     * @param int[] $analysisids The analyses to count for.
     * @param int $userid The reviewer.
     * @return array[] Suggestion totals by analysis id, then reviewed counts by analysis id.
     */
    private static function review_progress(array $analysisids, int $userid): array {
        global $DB;

        if (!$analysisids) {
            return [[], []];
        }

        [$in, $inparams] = $DB->get_in_or_equal($analysisids, SQL_PARAMS_NAMED, 'analysis');
        $totals = $DB->get_records_sql_menu(
            "SELECT analysisid, COUNT(1) FROM {local_compalign_sugg} WHERE analysisid $in GROUP BY analysisid",
            $inparams
        );
        $reviewed = $DB->get_records_sql_menu(
            "SELECT analysisid, COUNT(DISTINCT suggestionid) FROM {local_compalign_review}
              WHERE userid = :userid AND analysisid $in GROUP BY analysisid",
            ['userid' => $userid] + $inparams
        );

        return [$totals, $reviewed];
    }
}
