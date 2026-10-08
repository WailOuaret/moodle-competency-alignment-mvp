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

use core_competency\api;
use local_compalign\resource\registry;

/**
 * Resource-to-competency and competency-to-resource views over stored records.
 *
 * Model suggestions, teacher reviews, teacher-added relationships and official
 * Moodle links stay distinct. Nothing here calls the alignment service or writes
 * an official competency link.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class relationship_index {
    /** A model suggestion that the teacher has not turned into a reviewed relationship. */
    public const MODEL_PROPOSED = 'MODEL_PROPOSED';
    /** The teacher accepted the proposed competency. */
    public const TEACHER_ACCEPTED = 'TEACHER_ACCEPTED';
    /** The teacher replaced a proposal with this competency. */
    public const TEACHER_MODIFIED = 'TEACHER_MODIFIED';
    /** The teacher added this competency without replacing a proposal. */
    public const TEACHER_ADDED = 'TEACHER_ADDED';
    /** Moodle's own activity competency link. */
    public const OFFICIAL_MOODLE = 'OFFICIAL_MOODLE';

    /** Export value for an accepted suggestion. */
    public const EXPORT_ACCEPTED = 'MODEL_ACCEPTED';
    /** Export value for a modified suggestion. */
    public const EXPORT_MODIFIED = 'MODEL_MODIFIED';
    /** Export value for a teacher-added relationship. */
    public const EXPORT_ADDED = 'TEACHER_ADDED';

    /** @var catalogue_snapshot|null|false The framework, false until first read, null when it cannot be read. */
    private catalogue_snapshot|null|false $catalogue = false;

    /** @var array<string, int> Which reviewed origin to keep when two name the same competency. */
    private const RANK = [
        self::TEACHER_ACCEPTED => 3,
        self::TEACHER_MODIFIED => 2,
        self::TEACHER_ADDED => 1,
    ];

    /**
     * Official write-back is not implemented. The setting cannot turn it on.
     *
     * @return bool
     */
    public static function writeback_enabled(): bool {
        return false;
    }

    /**
     * Relationships for every resource whose current fingerprint is known.
     *
     * @param int $courseid The course.
     * @param int $userid The teacher whose reviews and additions are shown.
     * @param array<string, string|null> $hashes Current fingerprint by resource id. Null means unreadable.
     * @return array<string, array> Keyed by resource id.
     */
    public function bundles(int $courseid, int $userid, array $hashes): array {
        $loaded = $this->load($courseid, $userid);
        $bundles = [];
        foreach ($hashes as $resourceid => $hash) {
            $bundles[$resourceid] = $this->bundle_for((string) $resourceid, $hash, $loaded);
        }

        return $bundles;
    }

    /**
     * Resources associated with one competency.
     *
     * @param \stdClass $course The course.
     * @param int $userid The teacher.
     * @param string $idnumber The competency. Empty returns no rows.
     * @param string $filter all, reviewed, proposed, official or stale.
     * @return array[] Table rows.
     */
    public function for_competency(\stdClass $course, int $userid, string $idnumber, string $filter): array {
        if ($idnumber === '') {
            return [];
        }

        $loaded = $this->load((int) $course->id, $userid);
        $modinfo = get_fast_modinfo($course, $userid);
        $rows = [];
        $seenofficial = [];

        foreach ($modinfo->get_cms() as $cm) {
            if (!$cm->uservisible || $cm->deletioninprogress) {
                continue;
            }
            foreach (registry::enumerate($cm) as $item) {
                $hash = null;
                if ($item->supported) {
                    try {
                        $hash = (new resource_extractor())->extract($cm, $item->resourceid)['hash'];
                    } catch (analysis_exception) {
                        $hash = null;
                    }
                }
                $bundle = $this->bundle_for($item->resourceid, $hash, $loaded);
                $rows = array_merge($rows, $this->rows_from_bundle($cm, $item, $idnumber, $bundle, $filter));
            }

            foreach ($loaded['official'][(int) $cm->id] ?? [] as $link) {
                if ($link['idnumber'] !== $idnumber || isset($seenofficial[$cm->id])) {
                    continue;
                }
                $seenofficial[$cm->id] = true;
                $row = $this->official_row($cm, $link);
                if ($this->keeps($row, $filter)) {
                    $rows[] = $row;
                }
            }
        }

        return $rows;
    }

    /**
     * Competencies of the configured framework, optionally filtered by a search.
     *
     * @param string $query Text matched against the idnumber, name and description.
     * @return array[] Each with idnumber, shortname, breadcrumb and depth.
     */
    public function framework_list(string $query = ''): array {
        $catalogue = $this->catalogue();
        if ($catalogue === null) {
            return [];
        }

        $query = mb_strtolower(trim($query));
        $rows = [];
        foreach ($catalogue->lookup as $idnumber => $competency) {
            $idnumber = (string) $idnumber;
            $haystack = mb_strtolower($idnumber . ' ' . $competency['shortname'] . ' ' . $competency['description']);
            if ($query !== '' && !str_contains($haystack, $query)) {
                continue;
            }
            $breadcrumb = $this->breadcrumb($catalogue, $idnumber);
            $rows[] = [
                'idnumber' => $idnumber,
                'shortname' => (string) $competency['shortname'],
                'description' => (string) $competency['description'],
                'breadcrumb' => $breadcrumb,
                'depth' => max(0, substr_count($breadcrumb, ' / ')),
                'parentidnumber' => (string) ($competency['parentidnumber'] ?? ''),
            ];
        }

        return $rows;
    }

    /**
     * Official links for every activity in a course, read from Moodle's tables.
     *
     * @param int $courseid The course.
     * @return array<int, array[]> Keyed by course-module id.
     */
    public function official_by_cm(int $courseid): array {
        return $this->load($courseid, 0)['official'];
    }

    /**
     * One resource's proposals, reviewed competencies and active manual idnumbers.
     *
     * @param string $resourceid The resource.
     * @param string|null $hash Current fingerprint.
     * @param array $loaded Course data from load().
     * @return array
     */
    private function bundle_for(string $resourceid, ?string $hash, array $loaded): array {
        $analysis = $loaded['analyses'][$resourceid] ?? null;
        $staleanalysis = $analysis === null || $hash === null
            || !hash_equals((string) $analysis->resourcehash, $hash);
        $proposals = [];
        $reviewed = [];

        if ($analysis !== null) {
            foreach ($loaded['suggestions'][(int) $analysis->id] ?? [] as $suggestion) {
                $proposed = (string) $suggestion->competencyidnumber;
                $proposals[$proposed] = $this->competency_row($proposed, [
                    'source' => self::MODEL_PROPOSED,
                    'stale' => $staleanalysis,
                    'suggestionid' => (int) $suggestion->id,
                    'evidenceid' => $loaded['firstevidence'][(int) $suggestion->id] ?? 0,
                    'quote' => $loaded['firstquote'][(int) $suggestion->id] ?? '',
                ]);

                $review = $loaded['reviews'][(int) $suggestion->id] ?? null;
                if ($review === null) {
                    continue;
                }
                // Keep the model row honest about what happened to it. Without this a proposal the
                // teacher accepted, rejected or modified would still read "Not reviewed".
                $proposals[$proposed]['decision'] = (string) $review->decision;
                $proposals[$proposed]['finalidnumber'] = (string) ($review->finalcompetencyidnumber ?? '');
                if ($review->decision === review_manager::DECISION_ACCEPT) {
                    $this->remember_reviewed($reviewed, $proposed, self::TEACHER_ACCEPTED, $staleanalysis, $suggestion, $loaded, '');
                } else if ($review->decision === review_manager::DECISION_MODIFY && $review->finalcompetencyidnumber) {
                    $this->remember_reviewed(
                        $reviewed,
                        (string) $review->finalcompetencyidnumber,
                        self::TEACHER_MODIFIED,
                        $staleanalysis,
                        $suggestion,
                        $loaded,
                        get_string('evidence_original_proposal', 'local_compalign')
                    );
                }
            }
        }

        $manualactive = [];
        foreach ($loaded['manuals'] as $manual) {
            if ((string) $manual->resourceid !== $resourceid || $manual->status !== manual_relationship::STATUS_ACTIVE) {
                continue;
            }
            $manualactive[] = (string) $manual->competencyidnumber;
            $stale = $hash === null || !hash_equals((string) $manual->resourcehash, $hash);
            $this->remember_reviewed($reviewed, (string) $manual->competencyidnumber, self::TEACHER_ADDED, $stale, null, $loaded, '', $manual);
        }

        return [
            'proposals' => array_values($proposals),
            'reviewed' => array_values($reviewed),
            'manualactive' => array_values(array_unique($manualactive)),
            'warnings' => $this->hierarchy_warnings($reviewed),
        ];
    }

    /**
     * Keep one reviewed competency. A current relationship replaces a stale one.
     *
     * @param array $reviewed Rows keyed by idnumber.
     * @param string $idnumber The competency.
     * @param string $source The origin.
     * @param bool $stale Whether it belongs to an older fingerprint.
     * @param \stdClass|null $suggestion The model suggestion, when the origin is a review.
     * @param array $loaded Course data.
     * @param string $evidencenote Extra wording for modified relationships.
     * @param \stdClass|null $manual The teacher-added row, when that is the origin.
     */
    private function remember_reviewed(
        array &$reviewed,
        string $idnumber,
        string $source,
        bool $stale,
        ?\stdClass $suggestion,
        array $loaded,
        string $evidencenote,
        ?\stdClass $manual = null
    ): void {
        $row = $this->competency_row($idnumber, [
            'source' => $source,
            'stale' => $stale,
            'suggestionid' => $suggestion ? (int) $suggestion->id : 0,
            'evidenceid' => $suggestion ? ($loaded['firstevidence'][(int) $suggestion->id] ?? 0) : 0,
            'quote' => $manual ? (string) ($manual->evidencetext ?? '') : ($suggestion ? ($loaded['firstquote'][(int) $suggestion->id] ?? '') : ''),
            'manualid' => $manual ? (int) $manual->id : 0,
            'evidencenote' => $evidencenote,
            'comment' => $manual ? (string) ($manual->commenttext ?? '') : '',
        ]);
        $current = $reviewed[$idnumber] ?? null;
        if ($current === null) {
            $reviewed[$idnumber] = $row;
            return;
        }
        $currentisstale = !empty($current['stale']);
        if ($currentisstale && !$stale) {
            $reviewed[$idnumber] = $row;
            return;
        }
        if ($currentisstale === $stale && self::RANK[$source] > self::RANK[$current['source']]) {
            $reviewed[$idnumber] = $row;
        }
    }

    /**
     * A competency label plus the fields the caller added.
     *
     * @param string $idnumber The competency.
     * @param array $extra Origin fields.
     * @return array
     */
    private function competency_row(string $idnumber, array $extra): array {
        $found = $this->lookup($idnumber);

        return [
            'idnumber' => $idnumber,
            'shortname' => $found['shortname'] ?? get_string('competency_removed', 'local_compalign'),
            'removed' => $found === null,
        ] + $extra;
    }

    /**
     * Parent and child both confirmed for the current version of a resource.
     *
     * @param array $reviewed Rows keyed by idnumber.
     * @return string[]
     */
    private function hierarchy_warnings(array $reviewed): array {
        $warnings = [];
        foreach ($reviewed as $idnumber => $row) {
            if (!empty($row['stale'])) {
                continue;
            }
            $parent = (string) ($this->lookup($idnumber)['parentidnumber'] ?? '');
            if ($parent !== '' && isset($reviewed[$parent]) && empty($reviewed[$parent]['stale'])) {
                $warnings[] = get_string('hierarchy_both', 'local_compalign', (object) [
                    'child' => $idnumber,
                    'parent' => $parent,
                ]);
            }
        }

        return $warnings;
    }

    /**
     * @param catalogue_snapshot $catalogue The framework.
     * @param string $idnumber The competency.
     * @return string
     */
    private function breadcrumb(catalogue_snapshot $catalogue, string $idnumber): string {
        $chain = [$idnumber];
        $parent = (string) ($catalogue->find($idnumber)['parentidnumber'] ?? '');
        $guard = 0;
        while ($parent !== '' && $guard < 8) {
            array_unshift($chain, $parent);
            $parent = (string) ($catalogue->find($parent)['parentidnumber'] ?? '');
            $guard++;
        }

        return implode(' / ', $chain);
    }

    /**
     * @param string $idnumber The competency.
     * @return array|null
     */
    private function lookup(string $idnumber): ?array {
        $catalogue = $this->catalogue();

        return $catalogue ? $catalogue->find($idnumber) : null;
    }

    /**
     * The configured framework, read once per index.
     *
     * @return catalogue_snapshot|null
     */
    private function catalogue(): ?catalogue_snapshot {
        if ($this->catalogue === false) {
            try {
                $this->catalogue = (new competency_catalogue())->build();
            } catch (analysis_exception) {
                $this->catalogue = null;
            }
        }

        return $this->catalogue;
    }

    /**
     * Course-scoped records used by both directions.
     *
     * @param int $courseid The course.
     * @param int $userid The teacher. Zero skips reviews and manual rows.
     * @return array
     */
    private function load(int $courseid, int $userid): array {
        global $DB;

        $analyses = [];
        $sql = "SELECT a.*
                  FROM {local_compalign_analysis} a
                  JOIN (SELECT resourceid, MAX(id) AS maxid
                          FROM {local_compalign_analysis}
                         WHERE courseid = :courseid
                      GROUP BY resourceid) latest ON latest.maxid = a.id";
        foreach ($DB->get_records_sql($sql, ['courseid' => $courseid]) as $analysis) {
            $analyses[(string) $analysis->resourceid] = $analysis;
        }

        $suggestions = [];
        $firstevidence = [];
        $firstquote = [];
        $reviews = [];
        $ids = array_map(static fn(\stdClass $analysis): int => (int) $analysis->id, $analyses);
        if ($ids) {
            [$insql, $params] = $DB->get_in_or_equal($ids, SQL_PARAMS_NAMED);
            foreach ($DB->get_records_select('local_compalign_sugg', "analysisid $insql", $params, 'sortorder ASC, id ASC') as $suggestion) {
                $suggestions[(int) $suggestion->analysisid][] = $suggestion;
            }
            $evidence = $DB->get_records_select(
                'local_compalign_evidence',
                "suggestionid IN (SELECT id FROM {local_compalign_sugg} WHERE analysisid $insql)",
                $params,
                'evidenceorder ASC, id ASC'
            );
            foreach ($evidence as $row) {
                $suggestionid = (int) $row->suggestionid;
                if (!isset($firstevidence[$suggestionid])) {
                    $firstevidence[$suggestionid] = (int) $row->id;
                    $firstquote[$suggestionid] = (string) $row->evidencetext;
                }
            }
            if ($userid > 0) {
                $reviewsql = "SELECT r.*
                                FROM {local_compalign_review} r
                                JOIN (SELECT suggestionid, MAX(revision) AS revision
                                        FROM {local_compalign_review}
                                       WHERE userid = :userid
                                    GROUP BY suggestionid) latest
                                  ON latest.suggestionid = r.suggestionid AND latest.revision = r.revision
                               WHERE r.userid = :userid2 AND r.analysisid $insql";
                foreach ($DB->get_records_sql($reviewsql, ['userid' => $userid, 'userid2' => $userid] + $params) as $review) {
                    $reviews[(int) $review->suggestionid] = $review;
                }
            }
        }

        $manuals = [];
        if ($userid > 0) {
            $manuals = array_values($DB->get_records('local_compalign_manualrel', [
                'courseid' => $courseid,
                'userid' => $userid,
            ], 'id ASC'));
        }

        return [
            'analyses' => $analyses,
            'suggestions' => $suggestions,
            'firstevidence' => $firstevidence,
            'firstquote' => $firstquote,
            'reviews' => $reviews,
            'manuals' => $manuals,
            'official' => $this->official($courseid),
        ];
    }

    /**
     * @param int $courseid The course.
     * @return array<int, array[]>
     */
    private function official(int $courseid): array {
        global $DB;

        if (!api::is_enabled()) {
            return [];
        }

        $sql = "SELECT mc.id, cm.id AS cmid, c.idnumber, c.shortname
                  FROM {course_modules} cm
                  JOIN {competency_modulecomp} mc ON mc.cmid = cm.id
                  JOIN {competency} c ON c.id = mc.competencyid
                 WHERE cm.course = :courseid
              ORDER BY mc.sortorder ASC, mc.id ASC";
        $bycm = [];
        foreach ($DB->get_records_sql($sql, ['courseid' => $courseid]) as $row) {
            $bycm[(int) $row->cmid][] = [
                'idnumber' => (string) $row->idnumber,
                'shortname' => (string) $row->shortname,
            ];
        }

        return $bycm;
    }

    /**
     * Inverse-view rows for one resource and one competency.
     *
     * @param \cm_info $cm The activity.
     * @param \local_compalign\resource\item $item The resource.
     * @param string $idnumber The selected competency.
     * @param array $bundle The resource bundle.
     * @param string $filter The selected filter.
     * @return array[]
     */
    private function rows_from_bundle(\cm_info $cm, \local_compalign\resource\item $item, string $idnumber, array $bundle, string $filter): array {
        $rows = [];
        foreach (array_merge($bundle['proposals'], $bundle['reviewed']) as $entry) {
            if ($entry['idnumber'] !== $idnumber) {
                continue;
            }
            $row = $this->resource_row($cm, $item, $entry);
            if ($this->keeps($row, $filter)) {
                $rows[] = $row;
            }
        }

        return $rows;
    }

    /**
     * @param \cm_info $cm The activity.
     * @param \local_compalign\resource\item $item The resource.
     * @param array $entry A proposal or reviewed competency.
     * @return array
     */
    private function resource_row(\cm_info $cm, \local_compalign\resource\item $item, array $entry): array {
        $sourceurl = '';
        if (!empty($entry['evidenceid'])) {
            $sourceurl = (new \moodle_url('/local/compalign/source.php', [
                'cmid' => $cm->id,
                'item' => $item->resourceid,
                'evidence' => $entry['evidenceid'],
            ]))->out(false);
        } else if (!empty($entry['manualid']) && ($entry['quote'] ?? '') !== '') {
            $sourceurl = (new \moodle_url('/local/compalign/source.php', [
                'cmid' => $cm->id,
                'item' => $item->resourceid,
                'manual' => $entry['manualid'],
            ]))->out(false);
        }

        $evidence = $this->evidence_label($entry);

        return [
            'name' => $item->title !== '' ? $item->title : $cm->get_formatted_name(),
            'type' => $cm->get_module_type_name(),
            'relationship' => $this->source_label($entry['source']),
            'source' => $entry['source'],
            'stale' => !empty($entry['stale']),
            'reviewstatus' => $this->review_status($entry),
            'evidence' => $evidence,
            'evidencenote' => (string) ($entry['evidencenote'] ?? ''),
            'sourceurl' => $sourceurl,
            'official' => false,
            'openurl' => $cm->url ? $cm->url->out(false) : '',
            'reviewurl' => (new \moodle_url('/local/compalign/review.php', [
                'cmid' => $cm->id,
                'item' => $item->resourceid,
            ]))->out(false),
        ];
    }

    /**
     * @param \cm_info $cm The activity.
     * @param array $link The official competency.
     * @return array
     */
    private function official_row(\cm_info $cm, array $link): array {
        return [
            'name' => $cm->get_formatted_name(),
            'type' => $cm->get_module_type_name(),
            'relationship' => $this->source_label(self::OFFICIAL_MOODLE),
            'source' => self::OFFICIAL_MOODLE,
            'stale' => false,
            'reviewstatus' => get_string('official_link_status', 'local_compalign'),
            'evidence' => get_string('evidence_none', 'local_compalign'),
            'evidencenote' => '',
            'sourceurl' => '',
            'official' => true,
            'openurl' => $cm->url ? $cm->url->out(false) : '',
            'reviewurl' => '',
            'idnumber' => $link['idnumber'],
        ];
    }

    /**
     * @param array $row A table row.
     * @param string $filter The selected filter.
     * @return bool
     */
    private function keeps(array $row, string $filter): bool {
        return match ($filter) {
            'reviewed' => in_array($row['source'], [self::TEACHER_ACCEPTED, self::TEACHER_MODIFIED, self::TEACHER_ADDED], true),
            'proposed' => $row['source'] === self::MODEL_PROPOSED,
            'official' => $row['source'] === self::OFFICIAL_MOODLE,
            'stale' => !empty($row['stale']),
            default => true,
        };
    }

    /**
     * @param string $source The origin constant.
     * @return string
     */
    private function source_label(string $source): string {
        $key = match ($source) {
            self::TEACHER_ACCEPTED => 'rel_teacher_accepted',
            self::TEACHER_MODIFIED => 'rel_teacher_modified',
            self::TEACHER_ADDED => 'rel_teacher_added',
            self::OFFICIAL_MOODLE => 'rel_official',
            default => 'rel_model_proposed',
        };

        return get_string($key, 'local_compalign');
    }

    /**
     * @param array $entry A proposal or reviewed competency.
     * @return string
     */
    private function review_status(array $entry): string {
        if (!empty($entry['stale'])) {
            return get_string('reviewstatus_stale', 'local_compalign');
        }
        if (in_array($entry['source'], [self::TEACHER_ACCEPTED, self::TEACHER_MODIFIED, self::TEACHER_ADDED], true)) {
            return get_string('reviewstatus_reviewed', 'local_compalign');
        }
        if ($entry['source'] === self::MODEL_PROPOSED) {
            switch ($entry['decision'] ?? '') {
                case review_manager::DECISION_ACCEPT:
                    return get_string('decision_accept_summary', 'local_compalign');
                case review_manager::DECISION_REJECT:
                    return get_string('decision_reject_summary', 'local_compalign');
                case review_manager::DECISION_MODIFY:
                    return get_string('decision_modify_summary', 'local_compalign', (string) ($entry['finalidnumber'] ?? ''));
            }
        }

        return get_string('reviewstatus_notreviewed', 'local_compalign');
    }

    /**
     * @param array $entry A proposal or reviewed competency.
     * @return string
     */
    private function evidence_label(array $entry): string {
        if (($entry['source'] ?? '') === self::TEACHER_ADDED && trim((string) ($entry['quote'] ?? '')) === '') {
            return get_string('evidence_teacher_none', 'local_compalign');
        }
        if (trim((string) ($entry['quote'] ?? '')) === '' && empty($entry['evidenceid'])) {
            return get_string('evidence_none', 'local_compalign');
        }

        return get_string('showinsource', 'local_compalign');
    }
}
