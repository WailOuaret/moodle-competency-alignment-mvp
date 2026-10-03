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

namespace local_compalign\privacy;

use core_privacy\local\metadata\collection;
use core_privacy\local\request\approved_contextlist;
use core_privacy\local\request\approved_userlist;
use core_privacy\local\request\contextlist;
use core_privacy\local\request\transform;
use core_privacy\local\request\userlist;
use core_privacy\local\request\writer;

/**
 * Privacy provider for the Competency Alignment Assistant.
 *
 * The plugin stores, per course, who requested an analysis and each teacher's decision
 * on a suggestion (the decision, the rating, the comment and the review time). That is
 * personal data, so it is described, exported and deleted here.
 *
 * Deleting a user's data removes their reviews and unlinks them from the analyses they
 * requested. The analyses and the model's original suggestions stay, because they describe
 * a resource, not a person, and other teachers' reviews depend on them. Deleting all data
 * in a course context removes the analyses with everything that belongs to them.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class provider implements
        // This plugin stores personal data.
        \core_privacy\local\metadata\provider,

        // This plugin can say which users have data in a context.
        \core_privacy\local\request\core_userlist_provider,

        // This plugin exports and deletes the data of a user.
        \core_privacy\local\request\plugin\provider {

    /**
     * Describe the data stored by the plugin and the external location it is sent to.
     *
     * @param collection $collection The collection to add the description to.
     * @return collection The updated collection.
     */
    public static function get_metadata(collection $collection): collection {
        $collection->add_database_table('local_compalign_analysis', [
            'courseid' => 'privacy:metadata:local_compalign_analysis:courseid',
            'cmid' => 'privacy:metadata:local_compalign_analysis:cmid',
            'requestedby' => 'privacy:metadata:local_compalign_analysis:requestedby',
            'timecreated' => 'privacy:metadata:local_compalign_analysis:timecreated',
        ], 'privacy:metadata:local_compalign_analysis');

        $collection->add_database_table('local_compalign_review', [
            'userid' => 'privacy:metadata:local_compalign_review:userid',
            'decision' => 'privacy:metadata:local_compalign_review:decision',
            'finalcompetencyidnumber' => 'privacy:metadata:local_compalign_review:finalcompetencyidnumber',
            'evidenceusefulness' => 'privacy:metadata:local_compalign_review:evidenceusefulness',
            'commenttext' => 'privacy:metadata:local_compalign_review:commenttext',
            'reviewdurationseconds' => 'privacy:metadata:local_compalign_review:reviewdurationseconds',
            'timecreated' => 'privacy:metadata:local_compalign_review:timecreated',
        ], 'privacy:metadata:local_compalign_review');

        $collection->add_external_location_link('alignmentservice', [
            'resourcetitle' => 'privacy:metadata:alignmentservice:resourcetitle',
            'resourcetext' => 'privacy:metadata:alignmentservice:resourcetext',
            'competencies' => 'privacy:metadata:alignmentservice:competencies',
        ], 'privacy:metadata:alignmentservice');

        return $collection;
    }

    /**
     * Get the course contexts that hold data about a user.
     *
     * @param int $userid The user.
     * @return contextlist The contexts.
     */
    public static function get_contexts_for_userid(int $userid): contextlist {
        $sql = "SELECT ctx.id
                  FROM {context} ctx
                  JOIN {local_compalign_analysis} a ON a.courseid = ctx.instanceid
                 WHERE ctx.contextlevel = :courselevel1
                       AND a.requestedby = :requester
                 UNION
                SELECT ctx.id
                  FROM {context} ctx
                  JOIN {local_compalign_analysis} a ON a.courseid = ctx.instanceid
                  JOIN {local_compalign_review} r ON r.analysisid = a.id
                 WHERE ctx.contextlevel = :courselevel2
                       AND r.userid = :reviewer";

        $contextlist = new contextlist();
        $contextlist->add_from_sql($sql, [
            'courselevel1' => CONTEXT_COURSE,
            'courselevel2' => CONTEXT_COURSE,
            'requester' => $userid,
            'reviewer' => $userid,
        ]);

        return $contextlist;
    }

    /**
     * Get the users that have data in a course context.
     *
     * @param userlist $userlist The list to add the users to.
     */
    public static function get_users_in_context(userlist $userlist) {
        $context = $userlist->get_context();
        if (!$context instanceof \context_course) {
            return;
        }

        $params = ['courseid' => $context->instanceid];

        $userlist->add_from_sql('requestedby', "SELECT a.requestedby
                                                  FROM {local_compalign_analysis} a
                                                 WHERE a.courseid = :courseid AND a.requestedby > 0", $params);

        $userlist->add_from_sql('userid', "SELECT r.userid
                                             FROM {local_compalign_review} r
                                             JOIN {local_compalign_analysis} a ON a.id = r.analysisid
                                            WHERE a.courseid = :courseid", $params);
    }

    /**
     * Export the data of a user in the approved course contexts.
     *
     * @param approved_contextlist $contextlist The approved contexts.
     */
    public static function export_user_data(approved_contextlist $contextlist) {
        global $DB;

        if (!$contextlist->count()) {
            return;
        }

        $user = $contextlist->get_user();

        foreach ($contextlist->get_contexts() as $context) {
            if (!$context instanceof \context_course) {
                continue;
            }

            $analyses = [];
            $records = $DB->get_records('local_compalign_analysis', [
                'courseid' => $context->instanceid,
                'requestedby' => $user->id,
            ], 'timecreated ASC');
            foreach ($records as $record) {
                $analyses[] = (object) [
                    'resource' => $record->resourceid,
                    'status' => $record->status,
                    'requested' => transform::datetime($record->timecreated),
                ];
            }

            if ($analyses) {
                writer::with_context($context)->export_data(
                    [get_string('privacy:path:analyses', 'local_compalign')],
                    (object) ['analyses' => $analyses]
                );
            }

            $sql = "SELECT r.*, a.resourceid
                      FROM {local_compalign_review} r
                      JOIN {local_compalign_analysis} a ON a.id = r.analysisid
                     WHERE a.courseid = :courseid AND r.userid = :userid
                  ORDER BY r.timecreated ASC, r.id ASC";
            $reviews = [];
            $recordset = $DB->get_recordset_sql($sql, ['courseid' => $context->instanceid, 'userid' => $user->id]);
            foreach ($recordset as $review) {
                $reviews[] = (object) [
                    'resource' => $review->resourceid,
                    'revision' => $review->revision,
                    'decision' => $review->decision,
                    'finalcompetency' => $review->finalcompetencyidnumber,
                    'evidenceusefulness' => $review->evidenceusefulness,
                    'comment' => $review->commenttext,
                    'reviewdurationseconds' => $review->reviewdurationseconds,
                    'saved' => transform::datetime($review->timecreated),
                ];
            }
            $recordset->close();

            if ($reviews) {
                writer::with_context($context)->export_data(
                    [get_string('privacy:path:reviews', 'local_compalign')],
                    (object) ['reviews' => $reviews]
                );
            }
        }
    }

    /**
     * Delete everything the plugin holds for a course context.
     *
     * @param \context $context The context.
     */
    public static function delete_data_for_all_users_in_context(\context $context) {
        if (!$context instanceof \context_course) {
            return;
        }

        self::delete_analyses_of_course($context->instanceid);
    }

    /**
     * Delete the data of one user in the approved course contexts.
     *
     * @param approved_contextlist $contextlist The approved contexts.
     */
    public static function delete_data_for_user(approved_contextlist $contextlist) {
        if (!$contextlist->count()) {
            return;
        }

        $userid = $contextlist->get_user()->id;

        foreach ($contextlist->get_contexts() as $context) {
            if ($context instanceof \context_course) {
                self::delete_users_data_in_course($context->instanceid, [$userid]);
            }
        }
    }

    /**
     * Delete the data of several users in one course context.
     *
     * @param approved_userlist $userlist The approved users and their context.
     */
    public static function delete_data_for_users(approved_userlist $userlist) {
        $context = $userlist->get_context();
        if (!$context instanceof \context_course) {
            return;
        }

        self::delete_users_data_in_course($context->instanceid, $userlist->get_userids());
    }

    /**
     * Remove users' reviews in a course and unlink them from the analyses they requested.
     *
     * @param int $courseid The course.
     * @param int[] $userids The users.
     */
    private static function delete_users_data_in_course(int $courseid, array $userids): void {
        global $DB;

        if (!$userids) {
            return;
        }

        $analysisids = $DB->get_fieldset_select('local_compalign_analysis', 'id', 'courseid = :courseid', [
            'courseid' => $courseid,
        ]);

        [$usersql, $userparams] = $DB->get_in_or_equal($userids, SQL_PARAMS_NAMED, 'user');

        if ($analysisids) {
            [$analysissql, $analysisparams] = $DB->get_in_or_equal($analysisids, SQL_PARAMS_NAMED, 'analysis');
            $DB->delete_records_select(
                'local_compalign_review',
                "userid {$usersql} AND analysisid {$analysissql}",
                $userparams + $analysisparams
            );
        }

        $DB->set_field_select(
            'local_compalign_analysis',
            'requestedby',
            0,
            "courseid = :courseid AND requestedby {$usersql}",
            ['courseid' => $courseid] + $userparams
        );
    }

    /**
     * Delete every analysis of a course with its suggestions, evidence and reviews.
     *
     * @param int $courseid The course.
     */
    private static function delete_analyses_of_course(int $courseid): void {
        global $DB;

        $analysisids = $DB->get_fieldset_select('local_compalign_analysis', 'id', 'courseid = :courseid', [
            'courseid' => $courseid,
        ]);

        foreach (array_chunk($analysisids, 500) as $chunk) {
            [$sql, $params] = $DB->get_in_or_equal($chunk, SQL_PARAMS_NAMED);
            $DB->delete_records_select('local_compalign_review', "analysisid {$sql}", $params);
            $DB->delete_records_select(
                'local_compalign_evidence',
                "suggestionid IN (SELECT id FROM {local_compalign_sugg} WHERE analysisid {$sql})",
                $params
            );
            $DB->delete_records_select('local_compalign_sugg', "analysisid {$sql}", $params);
            $DB->delete_records_select('local_compalign_analysis', "id {$sql}", $params);
        }
    }
}
