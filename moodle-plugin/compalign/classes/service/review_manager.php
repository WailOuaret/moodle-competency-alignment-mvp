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

use local_compalign\event\review_saved;

/**
 * The rules for a teacher's decision on a suggested competency, and its storage.
 *
 * - ACCEPT: the final competency is the proposed one.
 * - MODIFY: the final competency is the one the teacher chose, which must be a different
 *   competency of the configured framework.
 * - REJECT: there is no final competency. Nothing is created in Moodle.
 *
 * A decision never changes the model's original suggestion. Every save appends a new revision, so
 * earlier decisions can still be reconstructed. The reviewer is always the logged-in user:
 * the caller passes the user id, it is never read from the submitted form.
 *
 * Nothing in this class writes to a Moodle competency link. Accepting or modifying only records the
 * decision, with the write-back status set to disabled.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class review_manager {
    /** The teacher approved the proposed competency. */
    public const DECISION_ACCEPT = 'accept';
    /** The teacher refused the proposed competency. */
    public const DECISION_REJECT = 'reject';
    /** The teacher approved a different competency instead. */
    public const DECISION_MODIFY = 'modify';
    /** Every decision the plugin accepts. */
    public const DECISIONS = [self::DECISION_ACCEPT, self::DECISION_REJECT, self::DECISION_MODIFY];

    /** The evidence did not help justify the decision. */
    public const USEFULNESS_NONE = 0;
    /** The evidence was partly useful. */
    public const USEFULNESS_PARTLY = 1;
    /** The evidence clearly supported the decision. */
    public const USEFULNESS_CLEARLY = 2;
    /** Every rating the plugin accepts. A rating is optional. */
    public const USEFULNESS_VALUES = [self::USEFULNESS_NONE, self::USEFULNESS_PARTLY, self::USEFULNESS_CLEARLY];

    /** Longest comment accepted, in characters. */
    public const MAX_COMMENT_CHARS = 1000;
    /** Longest review time recorded, in seconds. Longer reviews are stored as unknown. */
    public const MAX_REVIEW_SECONDS = 14400;

    /** Nothing was written to Moodle and nothing was meant to be: the suggestion was rejected. */
    public const WRITEBACK_NONE = 'none';
    /** The decision approves a competency, but official write-back is not enabled. */
    public const WRITEBACK_DISABLED = 'disabled';

    /** How often a save is retried when two saves race for the same revision number. */
    private const SAVE_ATTEMPTS = 3;

    /**
     * Find every problem with a submitted decision.
     *
     * The form and the saver both call this, so the rules exist once.
     *
     * @param string $decision The submitted decision.
     * @param string|null $finalidnumber The competency chosen for a modification.
     * @param mixed $usefulness The submitted rating: null or empty when not given.
     * @param string|null $comment The submitted comment.
     * @param string $proposedidnumber The competency the model proposed.
     * @param string[] $valididnumbers The competencies of the configured framework.
     * @return array<string, string> Localised error by field name. Empty when the decision is valid.
     */
    public static function find_errors(
        string $decision,
        ?string $finalidnumber,
        mixed $usefulness,
        ?string $comment,
        string $proposedidnumber,
        array $valididnumbers
    ): array {
        $errors = [];

        if (!in_array($decision, self::DECISIONS, true)) {
            $errors['decision'] = get_string('error_decisionrequired', 'local_compalign');
        }

        if ($decision === self::DECISION_MODIFY) {
            $final = trim((string) $finalidnumber);

            if ($final === '') {
                $errors['finalcompetency'] = get_string('error_modifyneedscompetency', 'local_compalign');
            } else if (!in_array($final, $valididnumbers, true)) {
                $errors['finalcompetency'] = get_string('error_invalidcompetency', 'local_compalign');
            } else if ($final === $proposedidnumber) {
                $errors['finalcompetency'] = get_string('error_modifysame', 'local_compalign');
            }
        }

        if (self::normalise_usefulness($usefulness, $valid) === null && !$valid) {
            $errors['usefulness'] = get_string('error_invalidusefulness', 'local_compalign');
        }

        if (mb_strlen((string) $comment) > self::MAX_COMMENT_CHARS) {
            $errors['commenttext'] = get_string('error_commenttoolong', 'local_compalign', self::MAX_COMMENT_CHARS);
        }

        return $errors;
    }

    /**
     * Read the optional rating.
     *
     * @param mixed $value The submitted rating.
     * @param bool|null $valid Set to false when something was submitted that is not a valid rating.
     * @return int|null 0, 1 or 2, or null when no rating was given or the value is invalid.
     */
    public static function normalise_usefulness(mixed $value, ?bool &$valid = null): ?int {
        $valid = true;

        if ($value === null || $value === '') {
            return null;
        }

        $number = filter_var($value, FILTER_VALIDATE_INT);
        if ($number !== false && in_array($number, self::USEFULNESS_VALUES, true)) {
            return $number;
        }

        $valid = false;

        return null;
    }

    /**
     * The competency a decision finally approves.
     *
     * @param string $decision A valid decision.
     * @param string $proposedidnumber The competency the model proposed.
     * @param string|null $finalidnumber The competency chosen for a modification.
     * @return string|null The approved idnumber, or null for a rejection.
     */
    public static function final_idnumber(string $decision, string $proposedidnumber, ?string $finalidnumber): ?string {
        return match ($decision) {
            self::DECISION_ACCEPT => $proposedidnumber,
            self::DECISION_MODIFY => trim((string) $finalidnumber),
            default => null,
        };
    }

    /**
     * How long the review took.
     *
     * The time runs from the moment the review card was first shown to the teacher to the moment the
     * decision was saved, both read from the server clock. A duration that is negative or longer than
     * MAX_REVIEW_SECONDS, or whose start is unknown, is recorded as unknown rather than guessed.
     *
     * @param int|null $startedat When the card was first shown, or null if unknown.
     * @param int $now When the decision is saved.
     * @return int|null Seconds, or null when unknown or out of range.
     */
    public static function review_duration(?int $startedat, int $now): ?int {
        if ($startedat === null) {
            return null;
        }

        $seconds = $now - $startedat;

        return ($seconds >= 0 && $seconds <= self::MAX_REVIEW_SECONDS) ? $seconds : null;
    }

    /**
     * Save a decision as a new revision.
     *
     * @param \stdClass $analysis The completed analysis.
     * @param \stdClass $suggestion One of its suggestions.
     * @param int $userid The reviewer: the logged-in user, never a submitted value.
     * @param string $decision accept, reject or modify.
     * @param string|null $finalidnumber The competency chosen for a modification.
     * @param mixed $usefulness The optional rating, 0 to 2.
     * @param string|null $comment The optional comment.
     * @param int|null $startedat When the card was first shown to this teacher, or null if unknown.
     * @param catalogue_snapshot $catalogue The configured framework.
     * @return \stdClass The stored review.
     * @throws analysis_exception When the decision is not valid for this suggestion.
     */
    public function save(
        \stdClass $analysis,
        \stdClass $suggestion,
        int $userid,
        string $decision,
        ?string $finalidnumber,
        mixed $usefulness,
        ?string $comment,
        ?int $startedat,
        catalogue_snapshot $catalogue
    ): \stdClass {
        if ((int) $suggestion->analysisid !== (int) $analysis->id || $analysis->status !== analysis_manager::STATUS_COMPLETED) {
            throw new analysis_exception('invalid_review', 'The suggestion does not belong to a completed analysis.');
        }

        $errors = self::find_errors(
            $decision,
            $finalidnumber,
            $usefulness,
            $comment,
            (string) $suggestion->competencyidnumber,
            $catalogue->idnumbers()
        );
        if ($errors) {
            throw new analysis_exception('invalid_review', 'The decision is not valid.', array_values($errors));
        }

        $finalidnumber = self::final_idnumber($decision, (string) $suggestion->competencyidnumber, $finalidnumber);
        $finalid = null;
        if ($finalidnumber !== null) {
            $finalid = $decision === self::DECISION_ACCEPT
                ? (int) $suggestion->competencyid
                : (int) $catalogue->find($finalidnumber)['id'];
        }

        $now = time();
        $comment = trim((string) $comment);
        $review = (object) [
            'analysisid' => (int) $analysis->id,
            'suggestionid' => (int) $suggestion->id,
            'userid' => $userid,
            'decision' => $decision,
            'finalcompetencyid' => $finalid,
            'finalcompetencyidnumber' => $finalidnumber,
            'evidenceusefulness' => self::normalise_usefulness($usefulness),
            'commenttext' => $comment !== '' ? $comment : null,
            'reviewstartedat' => $startedat,
            'reviewdurationseconds' => self::review_duration($startedat, $now),
            'writebackstatus' => $decision === self::DECISION_REJECT ? self::WRITEBACK_NONE : self::WRITEBACK_DISABLED,
            'timecreated' => $now,
            'timemodified' => $now,
        ];

        $review->id = $this->insert_next_revision($review);

        review_saved::create([
            'context' => \context_module::instance((int) $analysis->cmid),
            'objectid' => $review->id,
            'other' => ['decision' => $decision, 'revision' => $review->revision],
        ])->trigger();

        return $review;
    }

    /**
     * The latest decision of a user on each suggestion of an analysis.
     *
     * @param int $analysisid The analysis.
     * @param int $userid The reviewer.
     * @return \stdClass[] Reviews keyed by suggestion id.
     */
    public function latest_reviews(int $analysisid, int $userid): array {
        global $DB;

        $sql = "SELECT r.*
                  FROM {local_compalign_review} r
                 WHERE r.analysisid = :analysisid AND r.userid = :userid
                       AND r.revision = (SELECT MAX(r2.revision)
                                           FROM {local_compalign_review} r2
                                          WHERE r2.suggestionid = r.suggestionid AND r2.userid = r.userid)";

        $latest = [];
        foreach ($DB->get_records_sql($sql, ['analysisid' => $analysisid, 'userid' => $userid]) as $review) {
            $latest[(int) $review->suggestionid] = $review;
        }

        return $latest;
    }

    /**
     * Insert a review as the next revision for its suggestion and reviewer.
     *
     * Two saves can race for the same number. The unique index refuses the second, which then
     * takes the next number.
     *
     * @param \stdClass $review The review without id and revision.
     * @return int The new review id. The chosen revision is set on $review.
     */
    private function insert_next_revision(\stdClass $review): int {
        global $DB;

        for ($attempt = 1; ; $attempt++) {
            $latest = $DB->get_field_sql(
                'SELECT MAX(revision) FROM {local_compalign_review} WHERE suggestionid = :suggestionid AND userid = :userid',
                ['suggestionid' => $review->suggestionid, 'userid' => $review->userid]
            );
            $review->revision = ((int) $latest) + 1;

            try {
                return $DB->insert_record('local_compalign_review', $review);
            } catch (\dml_write_exception $exception) {
                if ($attempt >= self::SAVE_ATTEMPTS) {
                    throw $exception;
                }
            }
        }
    }
}
