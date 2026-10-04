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
use local_compalign\resource\registry;
use local_compalign\service\resource_extractor;
use local_compalign\service\service_exception;

/**
 * The course dashboard: every resource of a course with its analysis status and official links.
 *
 * Each supported item is one row: a Page, a quiz question, a chapter, a file, and so on.
 * An unsupported item says why, and does not stop the others. When the assistant is not ready
 * (no framework, no service address, and so on) the page says why and offers no analysis button.
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
        'stale' => 'warning',
        'unsupported' => 'secondary',
    ];

    /** Most items one batch may send to the model. */
    public const MAX_BATCH = 20;

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
        private string $filter = 'all',
        private string $type = 'all',
    ) {
    }

    /**
     * Gather what the dashboard shows for a course.
     *
     * @param \stdClass $course The course.
     * @param int $userid The logged-in user: whose resources are visible and whose reviews are counted.
     * @return self
     */
    public static function create(\stdClass $course, int $userid, string $filter = 'all', string $type = 'all'): self {
        $canmanage = has_capability('local/compalign:manage', \context_system::instance());
        $issues = self::find_issues($canmanage);
        $modinfo = get_fast_modinfo($course, $userid);

        $cms = array_filter(
            $modinfo->get_cms(),
            static fn(\cm_info $cm): bool => $cm->uservisible && !$cm->deletioninprogress
        );
        $latest = self::latest_analyses((int) $course->id);
        [$totals, $reviewed] = self::review_progress(
            array_map(static fn(\stdClass $analysis): int => (int) $analysis->id, $latest),
            $userid
        );

        $rows = [];
        foreach ($cms as $cm) {
            $canstart = !$issues && has_capability('local/compalign:analyse', \context_module::instance($cm->id));
            $links = competency_links::list_for_cm($cm);
            foreach (registry::enumerate($cm) as $item) {
                $analysis = $latest[$item->resourceid] ?? null;
                $state = null;
                if ($analysis) {
                    $state = [
                        'analysis' => $analysis,
                        'total' => (int) ($totals[$analysis->id] ?? 0),
                        'reviewed' => (int) ($reviewed[$analysis->id] ?? 0),
                    ];
                }
                $stale = false;
                if ($item->supported && $analysis && $analysis->status === analysis_manager::STATUS_COMPLETED) {
                    try {
                        $current = (new resource_extractor())->extract($cm, $item->resourceid);
                        $stale = !hash_equals((string) $analysis->resourcehash, $current['hash']);
                    } catch (analysis_exception) {
                        $stale = true;
                    }
                }
                $key = $item->supported
                    ? self::status_key($analysis, $state['total'] ?? 0, $state['reviewed'] ?? 0, $stale)
                    : 'unsupported';
                if (!self::matches_filter($filter, $key) || !self::matches_type($type, $item->resourcetype)) {
                    continue;
                }
                $rows[] = [
                    'cm' => $cm,
                    'item' => $item,
                    'state' => $state,
                    'links' => $links,
                    'canstart' => $canstart && $item->supported,
                    'stale' => $stale,
                    'statuskey' => $key,
                ];
            }
        }

        return new self($course, $issues, $rows, $canmanage, $filter, $type);
    }

    /**
     * The status key for a resource.
     *
     * @param \stdClass|null $analysis The latest analysis, if any.
     * @param int $total How many suggestions it stored.
     * @param int $reviewed How many of them the user has reviewed.
     * @return string none, queued, running, ready, nosuggestion, reviewed or failed.
     */
    public static function status_key(?\stdClass $analysis, int $total, int $reviewed, bool $stale = false): string {
        if ($analysis !== null && $stale && $analysis->status === analysis_manager::STATUS_COMPLETED) {
            return 'stale';
        }
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
            'selectable' => array_values(array_filter(
                $rows,
                static fn(array $row): bool => !empty($row['canselect'])
            )),
            'hasselectable' => (bool) array_filter($rows, static fn(array $row): bool => !empty($row['canselect'])),
            'filters' => $this->filter_links(),
            'sesskey' => sesskey(),
            'batchurl' => (new \moodle_url('/local/compalign/index.php', ['courseid' => $this->course->id]))->out(false),
            'maxbatch' => self::MAX_BATCH,
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
        /** @var \local_compalign\resource\item $item */
        $item = $row['item'];
        $analysis = $row['state']['analysis'] ?? null;
        $total = $row['state']['total'] ?? 0;
        $reviewed = $row['state']['reviewed'] ?? 0;
        $key = $row['statuskey'];
        $reviewurl = new \moodle_url('/local/compalign/review.php', [
            'cmid' => $cm->id,
            'item' => $item->resourceid,
        ]);

        $action = [];
        if (!$item->supported) {
            $reason = $item->reason !== '' ? $item->reason : 'unsupportedtype';
            $action['text'] = get_string($reason, 'local_compalign');
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
            'name' => $item->title !== '' ? $item->title : $cm->get_formatted_name(),
            'groupname' => $cm->get_formatted_name(),
            'url' => $cm->url ? $cm->url->out(false) : '',
            'typename' => $cm->get_module_type_name(),
            'provenance' => $item->provenance,
            'showgroup' => $item->title !== '' && $item->title !== $cm->get_formatted_name(),
            'resourceid' => $item->resourceid,
            'domid' => 'compalign-item-' . substr(sha1($item->resourceid), 0, 12),
            'canselect' => $row['canstart'] && $analysis === null,
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
                  JOIN (SELECT resourceid, MAX(id) AS maxid
                          FROM {local_compalign_analysis}
                         WHERE courseid = :courseid
                      GROUP BY resourceid) latest ON latest.maxid = a.id";

        $byresource = [];
        foreach ($DB->get_records_sql($sql, ['courseid' => $courseid]) as $analysis) {
            $byresource[(string) $analysis->resourceid] = $analysis;
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

    /**
     * Whether a status belongs in the selected filter.
     *
     * @param string $filter all, supported, none, ready, reviewed, stale or failed.
     * @param string $key The status key.
     * @return bool
     */
    private static function matches_filter(string $filter, string $key): bool {
        return match ($filter) {
            'supported' => $key !== 'unsupported',
            'none' => $key === 'none',
            'ready' => $key === 'ready',
            'reviewed' => $key === 'reviewed',
            'stale' => $key === 'stale',
            'failed' => $key === 'failed',
            default => true,
        };
    }

    /**
     * Whether a resource type belongs in the selected type filter.
     *
     * @param string $type all, page, quiz, document, transcript or other.
     * @param string $resourcetype The service type.
     * @return bool
     */
    private static function matches_type(string $type, string $resourcetype): bool {
        $documents = ['pdf', 'docx', 'pptx', 'text', 'markdown'];
        return match ($type) {
            'page' => $resourcetype === 'page',
            'quiz' => $resourcetype === 'quiz_question',
            'document' => in_array($resourcetype, $documents, true),
            'transcript' => $resourcetype === 'transcript',
            'other' => !in_array($resourcetype, array_merge(['page', 'quiz_question', 'transcript'], $documents), true),
            default => true,
        };
    }

    /**
     * Status and type filters for the course dashboard.
     *
     * @return array[] Each with url, label, classes and typefilter.
     */
    private function filter_links(): array {
        $base = new \moodle_url('/local/compalign/index.php', ['courseid' => $this->course->id]);
        $status = [
            'all' => 'filter_all',
            'supported' => 'filter_supported',
            'none' => 'filter_none',
            'ready' => 'filter_ready',
            'reviewed' => 'filter_reviewed',
            'stale' => 'filter_stale',
            'failed' => 'filter_failed',
        ];
        $types = [
            'all' => 'type_all',
            'page' => 'type_page',
            'quiz' => 'type_quiz',
            'document' => 'type_document',
            'transcript' => 'type_transcript',
            'other' => 'type_other',
        ];
        $links = [];
        foreach ($status as $key => $string) {
            $links[] = [
                'url' => (new \moodle_url($base, ['filter' => $key, 'type' => $this->type]))->out(false),
                'label' => get_string($string, 'local_compalign'),
                'classes' => 'btn btn-sm me-1 mb-1 ' . ($this->filter === $key ? 'btn-primary' : 'btn-outline-secondary'),
                'active' => $this->filter === $key,
                'typefilter' => false,
            ];
        }
        foreach ($types as $key => $string) {
            $links[] = [
                'url' => (new \moodle_url($base, ['filter' => $this->filter, 'type' => $key]))->out(false),
                'label' => get_string($string, 'local_compalign'),
                'classes' => 'btn btn-sm me-1 mb-1 ' . ($this->type === $key ? 'btn-primary' : 'btn-outline-secondary'),
                'active' => $this->type === $key,
                'typefilter' => true,
            ];
        }
        return $links;
    }
}
