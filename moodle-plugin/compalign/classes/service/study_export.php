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
 * Pseudonymised export of teacher reviews.
 *
 * Names, emails, passwords and tokens are not included. A free-text comment is
 * included because the study design asks for it; a teacher can type a name into it.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class study_export {
    /** @var array<string, string|null> Current resource fingerprints, keyed by module and resource. */
    private array $hashes = [];

    /** @var string[] Column order. */
    public const COLUMNS = [
        'participant_id',
        'resource_type',
        'course',
        'activity',
        'resource_title',
        'resource_id',
        'analysis_id',
        'suggestion_id',
        'proposed_competency',
        'decision',
        'final_competency',
        'evidence_usefulness',
        'review_duration_seconds',
        'comment',
        'hierarchy_warning',
        'backend',
        'model',
        'prompt_version',
        'schema_version',
        'top_k',
        'resource_hash',
        'catalogue_hash',
        'analysis_time',
        'review_time',
        'research_status',
        'relationship_source',
        'relationship_status',
        'teacher_evidence',
    ];

    /**
     * Rows for the latest review of each suggestion.
     *
     * @param array{courseid?: int, resourcetype?: string, participant?: string, from?: int, to?: int} $filters
     * @return array[]
     */
    public function rows(array $filters = []): array {
        global $DB;

        $where = ['1 = 1'];
        $params = [];
        if (!empty($filters['courseid'])) {
            $where[] = 'a.courseid = :courseid';
            $params['courseid'] = (int) $filters['courseid'];
        }
        if (!empty($filters['resourcetype'])) {
            $where[] = 'a.resourcetype = :resourcetype';
            $params['resourcetype'] = $filters['resourcetype'];
        }
        if (!empty($filters['from'])) {
            $where[] = 'r.timecreated >= :fromtime';
            $params['fromtime'] = (int) $filters['from'];
        }
        if (!empty($filters['to'])) {
            $where[] = 'r.timecreated <= :totime';
            $params['totime'] = (int) $filters['to'];
        }
        if (!empty($filters['researchstatus'])) {
            $where[] = 'a.researchstatus = :researchstatus';
            $params['researchstatus'] = $filters['researchstatus'];
        }

        $sql = "SELECT r.id, r.userid, r.decision, r.finalcompetencyidnumber, r.evidenceusefulness,
                       r.reviewdurationseconds, r.commenttext, r.timecreated AS reviewtime,
                       s.id AS suggestionid, s.competencyidnumber, s.warnings,
                       a.id AS analysisid, a.resourcetype, a.resourceid, a.courseid, a.cmid,
                       a.backend, a.model, a.manifest, a.topk, a.resourcehash, a.cataloguehash,
                       a.timecompleted, a.researchstatus,
                       c.shortname AS courseshortname,
                       u.idnumber
                  FROM {local_compalign_review} r
                  JOIN {local_compalign_sugg} s ON s.id = r.suggestionid
                  JOIN {local_compalign_analysis} a ON a.id = r.analysisid
                  JOIN {course} c ON c.id = a.courseid
                  JOIN {user} u ON u.id = r.userid
                  JOIN (
                        SELECT suggestionid, userid, MAX(revision) AS revision
                          FROM {local_compalign_review}
                      GROUP BY suggestionid, userid
                       ) latest ON latest.suggestionid = r.suggestionid
                               AND latest.userid = r.userid
                               AND latest.revision = r.revision
                 WHERE " . implode(' AND ', $where) . "
              ORDER BY r.timecreated ASC, r.id ASC";

        $rows = [];
        foreach ($DB->get_records_sql($sql, $params) as $record) {
            $participant = $this->participant((string) $record->idnumber, (int) $record->userid);
            if (!empty($filters['participant']) && $filters['participant'] !== $participant) {
                continue;
            }
            $manifest = json_decode((string) $record->manifest, true);
            $warnings = json_decode((string) $record->warnings, true);
            $activity = (string) $record->cmid;
            try {
                $cm = get_fast_modinfo((int) $record->courseid)->get_cm((int) $record->cmid);
                $activity = $cm->get_formatted_name();
            } catch (\Throwable) {
                $activity = (string) $record->cmid;
            }
            $rows[] = [
                'participant_id' => $participant,
                'resource_type' => (string) $record->resourcetype,
                'course' => (string) $record->courseshortname,
                'activity' => $activity,
                'resource_title' => (string) $record->resourceid,
                'resource_id' => (string) $record->resourceid,
                'analysis_id' => (string) $record->analysisid,
                'suggestion_id' => (string) $record->suggestionid,
                'proposed_competency' => (string) $record->competencyidnumber,
                'decision' => (string) $record->decision,
                'final_competency' => (string) ($record->finalcompetencyidnumber ?? ''),
                'evidence_usefulness' => $record->evidenceusefulness === null ? '' : (string) $record->evidenceusefulness,
                'review_duration_seconds' => $record->reviewdurationseconds === null ? '' : (string) $record->reviewdurationseconds,
                'comment' => (string) ($record->commenttext ?? ''),
                'hierarchy_warning' => is_array($warnings) && $warnings ? '1' : '0',
                'backend' => (string) ($record->backend ?? ''),
                'model' => (string) ($record->model ?? ''),
                'prompt_version' => is_array($manifest) ? (string) ($manifest['prompt_version'] ?? '') : '',
                'schema_version' => '1.0',
                'top_k' => (string) $record->topk,
                'resource_hash' => (string) ($record->resourcehash ?? ''),
                'catalogue_hash' => (string) ($record->cataloguehash ?? ''),
                'analysis_time' => $record->timecompleted ? gmdate('Y-m-d\TH:i:s\Z', (int) $record->timecompleted) : '',
                'review_time' => gmdate('Y-m-d\TH:i:s\Z', (int) $record->reviewtime),
                'research_status' => (string) ($record->researchstatus ?? study_phase::DEVELOPMENT),
                'relationship_source' => match ((string) $record->decision) {
                    review_manager::DECISION_ACCEPT => relationship_index::EXPORT_ACCEPTED,
                    review_manager::DECISION_MODIFY => relationship_index::EXPORT_MODIFIED,
                    default => '',
                },
                'relationship_status' => in_array((string) $record->decision, [
                    review_manager::DECISION_ACCEPT,
                    review_manager::DECISION_MODIFY,
                ], true) ? $this->freshness((int) $record->cmid, (string) $record->resourceid, (string) $record->resourcehash) : '',
                'teacher_evidence' => '',
            ];
        }

        return array_merge($rows, $this->manual_rows($filters));
    }

    /**
     * Teacher-added relationships, including ones the teacher later removed.
     *
     * @param array $filters The same filters as rows().
     * @return array[]
     */
    private function manual_rows(array $filters): array {
        global $DB;

        $where = ['1 = 1'];
        $params = [];
        if (!empty($filters['courseid'])) {
            $where[] = 'm.courseid = :courseid';
            $params['courseid'] = (int) $filters['courseid'];
        }
        if (!empty($filters['resourcetype'])) {
            $where[] = 'm.resourcetype = :resourcetype';
            $params['resourcetype'] = $filters['resourcetype'];
        }
        if (!empty($filters['from'])) {
            $where[] = 'm.timecreated >= :fromtime';
            $params['fromtime'] = (int) $filters['from'];
        }
        if (!empty($filters['to'])) {
            $where[] = 'm.timecreated <= :totime';
            $params['totime'] = (int) $filters['to'];
        }
        if (!empty($filters['researchstatus'])) {
            $where[] = 'm.researchstatus = :researchstatus';
            $params['researchstatus'] = $filters['researchstatus'];
        }

        $sql = "SELECT m.*, c.shortname AS courseshortname, u.idnumber
                  FROM {local_compalign_manualrel} m
                  JOIN {course} c ON c.id = m.courseid
                  JOIN {user} u ON u.id = m.userid
                 WHERE " . implode(' AND ', $where) . "
              ORDER BY m.timecreated ASC, m.id ASC";

        $rows = [];
        foreach ($DB->get_records_sql($sql, $params) as $record) {
            $participant = $this->participant((string) $record->idnumber, (int) $record->userid);
            if (!empty($filters['participant']) && $filters['participant'] !== $participant) {
                continue;
            }
            $activity = (string) $record->cmid;
            try {
                $cm = get_fast_modinfo((int) $record->courseid)->get_cm((int) $record->cmid);
                $activity = $cm->get_formatted_name();
            } catch (\Throwable) {
                $activity = (string) $record->cmid;
            }
            $status = $record->status === manual_relationship::STATUS_REMOVED
                ? 'removed'
                : $this->freshness((int) $record->cmid, (string) $record->resourceid, (string) $record->resourcehash);
            $rows[] = [
                'participant_id' => $participant,
                'resource_type' => (string) $record->resourcetype,
                'course' => (string) $record->courseshortname,
                'activity' => $activity,
                'resource_title' => (string) $record->resourceid,
                'resource_id' => (string) $record->resourceid,
                'analysis_id' => '',
                'suggestion_id' => '',
                'proposed_competency' => '',
                'decision' => '',
                'final_competency' => (string) $record->competencyidnumber,
                'evidence_usefulness' => '',
                'review_duration_seconds' => '',
                'comment' => (string) ($record->commenttext ?? ''),
                'hierarchy_warning' => '0',
                'backend' => '',
                'model' => '',
                'prompt_version' => '',
                'schema_version' => '',
                'top_k' => '',
                'resource_hash' => (string) $record->resourcehash,
                'catalogue_hash' => '',
                'analysis_time' => '',
                'review_time' => gmdate('Y-m-d\TH:i:s\Z', (int) $record->timecreated),
                'research_status' => (string) $record->researchstatus,
                'relationship_source' => relationship_index::EXPORT_ADDED,
                'relationship_status' => $status,
                'teacher_evidence' => (string) ($record->evidencetext ?? ''),
            ];
        }

        return $rows;
    }

    /**
     * Whether a stored fingerprint still matches the resource.
     *
     * @param int $cmid The activity.
     * @param string $resourceid The resource.
     * @param string $stored The fingerprint stored with the decision.
     * @return string current or stale.
     */
    private function freshness(int $cmid, string $resourceid, string $stored): string {
        $key = $cmid . ':' . $resourceid;
        if (!array_key_exists($key, $this->hashes)) {
            $this->hashes[$key] = null;
            try {
                [, $cm] = get_course_and_cm_from_cmid($cmid);
                $this->hashes[$key] = (new resource_extractor())->extract($cm, $resourceid)['hash'];
            } catch (\Throwable) {
                $this->hashes[$key] = null;
            }
        }
        $current = $this->hashes[$key];

        return $current !== null && hash_equals($stored, $current) ? 'current' : 'stale';
    }

    /**
     * @param array[] $rows Rows from rows().
     * @return string CSV, including the header.
     */
    public function csv(array $rows): string {
        $handle = fopen('php://temp', 'w+');
        fputcsv($handle, self::COLUMNS);
        foreach ($rows as $row) {
            $line = [];
            foreach (self::COLUMNS as $column) {
                $line[] = $row[$column] ?? '';
            }
            fputcsv($handle, $line);
        }
        rewind($handle);
        $csv = stream_get_contents($handle);
        fclose($handle);
        return (string) $csv;
    }

    /**
     * Prefer a study code such as T001. Otherwise a stable pseudonym, not a name.
     *
     * @param string $idnumber The Moodle id number.
     * @param int $userid The user id, used only inside the pseudonym.
     * @return string
     */
    public function participant(string $idnumber, int $userid): string {
        $idnumber = trim($idnumber);
        if (preg_match('/^T\d{3}$/', $idnumber)) {
            return $idnumber;
        }
        $material = $idnumber !== '' ? 'idnumber:' . $idnumber : 'userid:' . $userid;
        return 'participant-' . substr(hash_hmac('sha256', $material, $this->salt()), 0, 12);
    }

    /**
     * A secret kept in the plugin config. It is created once and never exported.
     *
     * @return string
     */
    private function salt(): string {
        $salt = (string) get_config('local_compalign', 'exportsecret');
        if ($salt === '') {
            $salt = bin2hex(random_bytes(32));
            set_config('exportsecret', $salt, 'local_compalign');
        }
        return $salt;
    }
}
