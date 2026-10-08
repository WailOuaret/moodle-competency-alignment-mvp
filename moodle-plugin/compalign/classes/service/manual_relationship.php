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

use local_compalign\event\manual_relationship_changed;
use local_compalign\resource\registry;

/**
 * Competencies a teacher adds to a resource, separate from model suggestions.
 *
 * Adding a competency does not create a suggestion and does not create an official
 * Moodle competency link. Removing one keeps the row and records who changed it.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class manual_relationship {
    /** The relationship is part of the teacher's current review. */
    public const STATUS_ACTIVE = 'active';
    /** The teacher withdrew the relationship. The row is kept. */
    public const STATUS_REMOVED = 'removed';
    /** Longest optional quotation, in characters. */
    public const MAX_EVIDENCE_CHARS = 4000;

    /**
     * Add a competency to a resource for the logged-in teacher.
     *
     * @param \cm_info $cm The activity that contains the resource.
     * @param string $resourceid Stable resource id.
     * @param int $courseid Course the caller claims. It must be the activity's course.
     * @param int $userid The authenticated teacher.
     * @param string $idnumber Competency idnumber from the configured framework.
     * @param string $expectedhash Fingerprint shown when the form was opened.
     * @param string $evidence Optional quotation. Empty when the teacher gave none.
     * @param string $comment Optional reason.
     * @param \context $context Module context, used for the capability check.
     * @return \stdClass The stored row.
     */
    public function add(
        \cm_info $cm,
        string $resourceid,
        int $courseid,
        int $userid,
        string $idnumber,
        string $expectedhash,
        string $evidence,
        string $comment,
        \context $context
    ): \stdClass {
        require_capability('local/compalign:review', $context);
        $this->assert_course($cm, $courseid);

        $catalogue = (new competency_catalogue())->build();
        $packed = $this->require_resource($cm, $resourceid);
        $text = source_context::canonical_text($packed);
        $errors = $this->find_errors(
            $catalogue,
            $idnumber,
            $comment,
            $evidence,
            $text,
            $expectedhash,
            $packed['hash'],
            $this->active_idnumbers($courseid, $resourceid, $userid, $packed['hash'])
        );
        if ($errors) {
            throw new analysis_exception($errors[0]);
        }

        $competency = $catalogue->find($idnumber);
        $now = time();
        $record = (object) [
            'courseid' => (int) $cm->course,
            'cmid' => (int) $cm->id,
            'resourceid' => $resourceid,
            'resourcetype' => (string) ($packed['resource']['resource_type'] ?? ''),
            'resourcehash' => $packed['hash'],
            'frameworkid' => $catalogue->frameworkid,
            'competencyid' => (int) $competency['id'],
            'competencyidnumber' => $idnumber,
            'userid' => $userid,
            'evidencetext' => trim($evidence) === '' ? null : trim($evidence),
            'evidenceprovenance' => $this->provenance_label($packed),
            'commenttext' => trim($comment) === '' ? null : trim($comment),
            'status' => self::STATUS_ACTIVE,
            'researchstatus' => study_phase::current(),
            'timecreated' => $now,
            'timemodified' => $now,
        ];

        global $DB;
        $record->id = $DB->insert_record('local_compalign_manualrel', $record);
        $this->log($cm, $record, 'added');

        return $record;
    }

    /**
     * Mark a teacher-added relationship as removed.
     *
     * @param int $id The relationship id.
     * @param \cm_info $cm The activity it must belong to.
     * @param int $userid The teacher making the correction.
     * @param \context $context Module context.
     * @return \stdClass The updated row.
     */
    public function remove(int $id, \cm_info $cm, int $userid, \context $context): \stdClass {
        global $DB;

        require_capability('local/compalign:review', $context);
        $record = $DB->get_record('local_compalign_manualrel', ['id' => $id]);
        if (!$record || (int) $record->courseid !== (int) $cm->course || (int) $record->cmid !== (int) $cm->id) {
            throw new analysis_exception('manual_not_found');
        }
        if ($record->status === self::STATUS_REMOVED) {
            return $record;
        }

        $record->status = self::STATUS_REMOVED;
        $record->removedby = $userid;
        $record->timeremoved = time();
        $record->timemodified = $record->timeremoved;
        $DB->update_record('local_compalign_manualrel', $record);
        $this->log($cm, $record, 'removed');

        return $record;
    }

    /**
     * Problems with a submitted addition. The form and the saver share this list.
     *
     * @param catalogue_snapshot $catalogue The configured framework.
     * @param string $idnumber The chosen competency.
     * @param string $comment The optional comment.
     * @param string $evidence The optional quotation.
     * @param string|null $text Canonical text, or null when it cannot be read.
     * @param string $expectedhash Hash shown on the form.
     * @param string $currenthash Hash of the resource now.
     * @param string[] $activeidnumbers Competencies already reviewed for this resource.
     * @return string[] Error codes.
     */
    public function find_errors(
        catalogue_snapshot $catalogue,
        string $idnumber,
        string $comment,
        string $evidence,
        ?string $text,
        string $expectedhash,
        string $currenthash,
        array $activeidnumbers
    ): array {
        $errors = [];
        $idnumber = trim($idnumber);
        $competency = $idnumber === '' ? null : $catalogue->find($idnumber);
        if ($competency === null || (int) $competency['id'] <= 0) {
            $errors[] = $this->invalid_competency_code($idnumber, $catalogue->frameworkid);
        }
        if (mb_strlen(trim($comment)) > review_manager::MAX_COMMENT_CHARS) {
            $errors[] = 'comment_too_long';
        }
        if (mb_strlen(trim($evidence)) > self::MAX_EVIDENCE_CHARS) {
            $errors[] = 'evidence_too_long';
        }
        if ($expectedhash === '' || !hash_equals($currenthash, $expectedhash)) {
            $errors[] = 'resource_changed';
        }
        if (in_array($idnumber, $activeidnumbers, true)) {
            $errors[] = 'competency_duplicate';
        }
        $evidence = trim($evidence);
        if ($evidence !== '') {
            if ($text === null) {
                $errors[] = 'evidence_unverified';
            } else if (!quote_span::contains($text, $evidence)) {
                $errors[] = 'evidence_not_in_source';
            }
        }

        return $errors;
    }

    /**
     * A missing competency is either unknown or from another framework.
     *
     * @param string $idnumber The submitted idnumber.
     * @param int $frameworkid The configured framework.
     * @return string
     */
    private function invalid_competency_code(string $idnumber, int $frameworkid): string {
        global $DB;

        if ($idnumber !== '' && $DB->record_exists_select(
            'competency',
            'idnumber = :idnumber AND competencyframeworkid <> :frameworkid',
            ['idnumber' => $idnumber, 'frameworkid' => $frameworkid]
        )) {
            return 'competency_other_framework';
        }

        return 'competency_invalid';
    }

    /**
     * Idnumbers already confirmed for this resource at its current fingerprint.
     *
     * A stale confirmation does not block a new addition for the changed resource.
     * An active manual row for the same competency still does, so two active rows
     * are never stored for one teacher and one resource.
     *
     * @param int $courseid The course.
     * @param string $resourceid The resource.
     * @param int $userid The teacher.
     * @param string $currenthash The resource fingerprint now.
     * @return string[]
     */
    public function active_idnumbers(int $courseid, string $resourceid, int $userid, string $currenthash): array {
        $index = new relationship_index();
        $bundle = $index->bundles($courseid, $userid, [$resourceid => $currenthash])[$resourceid] ?? null;
        $active = [];
        foreach ($bundle['reviewed'] ?? [] as $row) {
            if (empty($row['stale'])) {
                $active[] = $row['idnumber'];
            }
        }
        foreach ($bundle['manualactive'] ?? [] as $idnumber) {
            $active[] = $idnumber;
        }

        return array_values(array_unique($active));
    }

    /**
     * Read the resource and its current fingerprint.
     *
     * @param \cm_info $cm The activity.
     * @param string $resourceid The stable id.
     * @return array Extract result from the registry.
     */
    public function require_resource(\cm_info $cm, string $resourceid): array {
        $found = false;
        foreach (registry::enumerate($cm) as $item) {
            if ($item->resourceid === $resourceid) {
                $found = true;
                break;
            }
        }
        if (!$found) {
            throw new analysis_exception('resource_missing');
        }

        return (new resource_extractor())->extract($cm, $resourceid);
    }

    /**
     * The activity must belong to the course the request names.
     *
     * @param \cm_info $cm The activity.
     * @param int $courseid The course id from the request.
     */
    private function assert_course(\cm_info $cm, int $courseid): void {
        if ((int) $cm->course !== $courseid) {
            throw new analysis_exception('resource_wrong_course');
        }
    }

    /**
     * A short provenance label stored with optional teacher evidence.
     *
     * @param array $packed Extract result.
     * @return string|null
     */
    private function provenance_label(array $packed): ?string {
        $label = $packed['provenance']['label'] ?? '';

        return $label !== '' ? (string) $label : null;
    }

    /**
     * Write the audit event.
     *
     * @param \cm_info $cm The activity.
     * @param \stdClass $record The relationship.
     * @param string $action added or removed.
     */
    private function log(\cm_info $cm, \stdClass $record, string $action): void {
        $event = manual_relationship_changed::create([
            'objectid' => (int) $record->id,
            'context' => \context_module::instance($cm->id),
            'userid' => (int) ($action === 'removed' ? $record->removedby : $record->userid),
            'other' => [
                'action' => $action,
                'competency' => (string) $record->competencyidnumber,
                'resourceid' => (string) $record->resourceid,
                'resourcehash' => (string) $record->resourcehash,
            ],
        ]);
        $event->trigger();
    }
}
