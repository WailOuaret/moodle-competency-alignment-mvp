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

use local_compalign\fixtures\environment;

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Teacher-reviewed relationships and the competency-to-resource view.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[\PHPUnit\Framework\Attributes\CoversClass(relationship_index::class)]
#[\PHPUnit\Framework\Attributes\CoversClass(manual_relationship::class)]
final class relationship_index_test extends \advanced_testcase {
    use environment;

    /**
     * Accept, modify and reject produce different reviewed relationships.
     */
    public function test_review_decisions_become_relationships(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $proposed = (string) $suggestion->competencyidnumber;
        $replacement = $proposed === 'T2' ? 'T1' : 'T2';
        $manager = new review_manager();
        $hash = $this->hash_of($environment);

        $manager->save($made['analysis'], $suggestion, (int) $environment['teacher']->id, 'reject', null, null, null, null, $made['catalogue']);
        $bundle = $this->bundle($environment, $hash);
        $this->assertSame([], $bundle['reviewed']);
        $this->assertSame([$proposed], array_column($bundle['proposals'], 'idnumber'));

        $manager->save($made['analysis'], $suggestion, (int) $environment['teacher']->id, 'accept', null, null, null, null, $made['catalogue']);
        $bundle = $this->bundle($environment, $hash);
        $this->assertSame([$proposed], array_column($bundle['reviewed'], 'idnumber'));
        $this->assertSame(relationship_index::TEACHER_ACCEPTED, $bundle['reviewed'][0]['source']);

        $manager->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'modify',
            $replacement,
            null,
            null,
            null,
            $made['catalogue']
        );
        $bundle = $this->bundle($environment, $hash);
        $this->assertSame([$replacement], array_column($bundle['reviewed'], 'idnumber'));
        $this->assertSame(relationship_index::TEACHER_MODIFIED, $bundle['reviewed'][0]['source']);
        $this->assertFalse($bundle['reviewed'][0]['stale']);
    }

    /**
     * A teacher can add a competency without replacing the accepted one.
     */
    public function test_teacher_can_add_without_replacing(): void {
        global $DB;

        $this->resetAfterTest();
        set_config('enablewriteback', 1, 'local_compalign');
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $proposed = (string) $suggestion->competencyidnumber;
        $added = $proposed === 'T1_1' ? 'T2' : 'T1_1';
        $hash = $this->hash_of($environment);
        $before = $DB->count_records('competency_modulecomp');

        (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'accept',
            null,
            null,
            null,
            null,
            $made['catalogue']
        );
        $record = $this->add($environment, $added, $hash, 'Unit tests check one function at a time.');

        $this->assertFalse(relationship_index::writeback_enabled());
        $this->assertSame($before, $DB->count_records('competency_modulecomp'));
        $this->assertSame('active', $record->status);
        $bundle = $this->bundle($environment, $hash);
        $byid = array_column($bundle['reviewed'], 'source', 'idnumber');
        $this->assertSame(relationship_index::TEACHER_ACCEPTED, $byid[$proposed]);
        $this->assertSame(relationship_index::TEACHER_ADDED, $byid[$added]);
        $this->assertCount(2, $bundle['reviewed']);
    }

    /**
     * Invalid, foreign, duplicate and stale additions are refused. Removal is kept.
     */
    public function test_manual_validation_and_removal(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $hash = $this->hash_of($environment);
        $manual = new manual_relationship();
        $context = \context_module::instance($environment['cm']->id);

        $other = $this->getDataGenerator()->get_plugin_generator('core_competency')->create_framework([
            'shortname' => 'Other',
            'idnumber' => 'OTHER',
        ]);
        $foreign = $this->getDataGenerator()->get_plugin_generator('core_competency')->create_competency([
            'competencyframeworkid' => $other->get('id'),
            'idnumber' => 'FOREIGN',
            'shortname' => 'Foreign',
        ]);

        $saved = $this->add($environment, 'T2', $hash, '', 'A reason');
        try {
            $this->add($environment, 'T2', $hash);
            $this->fail('A duplicate must be refused.');
        } catch (analysis_exception $exception) {
            $this->assertSame('competency_duplicate', $exception->get_error_code());
        }
        try {
            $this->add($environment, 'FOREIGN', $hash);
            $this->fail('Another framework must be refused.');
        } catch (analysis_exception $exception) {
            $this->assertSame('competency_other_framework', $exception->get_error_code());
        }
        try {
            $this->add($environment, 'NOT-A-COMPETENCY', $hash);
            $this->fail('An unknown competency must be refused.');
        } catch (analysis_exception $exception) {
            $this->assertSame('competency_invalid', $exception->get_error_code());
        }
        try {
            $manual->add(
                $environment['cm'],
                $environment['cm']->id ? 'moodle:page:' . $environment['page']->id : '',
                (int) $environment['course']->id,
                (int) $environment['teacher']->id,
                'T1',
                'sha256:stale',
                '',
                '',
                $context
            );
            $this->fail('A stale fingerprint must be refused.');
        } catch (analysis_exception $exception) {
            $this->assertSame('resource_changed', $exception->get_error_code());
        }
        try {
            $manual->add(
                $environment['cm'],
                'moodle:page:' . $environment['page']->id,
                (int) $environment['course']->id,
                (int) $environment['teacher']->id,
                'T1',
                $hash,
                '',
                str_repeat('a', review_manager::MAX_COMMENT_CHARS + 1),
                $context
            );
            $this->fail('A long comment must be refused.');
        } catch (analysis_exception $exception) {
            $this->assertSame('comment_too_long', $exception->get_error_code());
        }
        try {
            $this->add($environment, 'T1', $hash, 'this quotation is not in the page');
            $this->fail('Evidence must match the resource text.');
        } catch (analysis_exception $exception) {
            $this->assertSame('evidence_not_in_source', $exception->get_error_code());
        }

        $studentcontext = \context_module::instance($environment['cm']->id);
        $this->assertSame('FOREIGN', $foreign->get('idnumber'));
        $this->assertSame('T2', $saved->competencyidnumber);
        $this->setUser($environment['student']);
        $this->expectException(\required_capability_exception::class);
        $manual->add(
            $environment['cm'],
            'moodle:page:' . $environment['page']->id,
            (int) $environment['course']->id,
            (int) $environment['student']->id,
            'T1',
            $hash,
            '',
            '',
            $studentcontext
        );
    }

    /**
     * A removed relationship is not active, and a changed resource makes the old one stale.
     */
    public function test_removed_and_stale_manual_relationships(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $hash = $this->hash_of($environment);
        $saved = $this->add($environment, 'T2', $hash);
        $manual = new manual_relationship();
        $manual->remove($saved->id, $environment['cm'], (int) $environment['teacher']->id, \context_module::instance($environment['cm']->id));
        $bundle = $this->bundle($environment, $hash);
        $this->assertSame([], $bundle['reviewed']);
        $this->assertSame('removed', $DB->get_field('local_compalign_manualrel', 'status', ['id' => $saved->id]));

        $again = $this->add($environment, 'T2', $hash);
        $DB->set_field('page', 'content', '<p>A revised page.</p>', ['id' => $environment['page']->id]);
        rebuild_course_cache((int) $environment['course']->id, true);
        $environment['cm'] = get_fast_modinfo($environment['course'])->get_cm($environment['cm']->id);
        $bundle = $this->bundle($environment, $this->hash_of($environment));
        $this->assertTrue($bundle['reviewed'][0]['stale']);
        $this->assertSame((int) $again->id, (int) $bundle['reviewed'][0]['manualid']);
    }

    /**
     * The reverse view keeps origins apart and does not cross courses.
     */
    public function test_competency_to_resources(): void {
        $this->resetAfterTest();
        set_config('enabled', 1, 'core_competency');
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $proposed = (string) $suggestion->competencyidnumber;
        $replacement = $proposed === 'T2' ? 'T1' : 'T2';
        $hash = $this->hash_of($environment);
        (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'modify',
            $replacement,
            null,
            null,
            null,
            $made['catalogue']
        );
        $this->add($environment, 'T1_1', $hash);

        \core_competency\api::add_competency_to_course(
            (int) $environment['course']->id,
            (int) $environment['competencies']['T1']->get('id')
        );
        \core_competency\api::add_competency_to_course_module(
            (int) $environment['cm']->id,
            (int) $environment['competencies']['T1']->get('id')
        );

        $index = new relationship_index();
        $accepted = $index->for_competency($environment['course'], (int) $environment['teacher']->id, $replacement, 'reviewed');
        $this->assertCount(1, $accepted);
        $this->assertSame(relationship_index::TEACHER_MODIFIED, $accepted[0]['source']);
        $original = $index->for_competency($environment['course'], (int) $environment['teacher']->id, $proposed, 'reviewed');
        $this->assertSame([], array_filter($original, static fn(array $row): bool => $row['source'] === relationship_index::TEACHER_ACCEPTED));

        $proposedrows = $index->for_competency($environment['course'], (int) $environment['teacher']->id, $proposed, 'proposed');
        $this->assertNotEmpty($proposedrows);
        $this->assertSame(relationship_index::MODEL_PROPOSED, $proposedrows[0]['source']);

        $added = $index->for_competency($environment['course'], (int) $environment['teacher']->id, 'T1_1', 'reviewed');
        $this->assertSame(relationship_index::TEACHER_ADDED, $added[0]['source']);

        $official = $index->for_competency($environment['course'], (int) $environment['teacher']->id, 'T1', 'official');
        $this->assertNotEmpty($official);
        $this->assertSame(relationship_index::OFFICIAL_MOODLE, $official[0]['source']);
        $officialasreviewed = $index->for_competency($environment['course'], (int) $environment['teacher']->id, 'T1', 'reviewed');
        foreach ($officialasreviewed as $row) {
            $this->assertNotSame(relationship_index::OFFICIAL_MOODLE, $row['source']);
        }

        $othercourse = $this->getDataGenerator()->create_course();
        $this->getDataGenerator()->enrol_user($environment['teacher']->id, $othercourse->id, 'editingteacher');
        $this->assertSame([], $index->for_competency($othercourse, (int) $environment['teacher']->id, $replacement, 'all'));
    }

    /**
     * A changed resource is labelled stale in the reverse view.
     */
    public function test_stale_relationship_is_labelled(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $hash = $this->hash_of($environment);
        $this->add($environment, 'T2', $hash);
        $DB->set_field('page', 'content', '<p>Changed after review.</p>', ['id' => $environment['page']->id]);
        $rows = (new relationship_index())->for_competency(
            $environment['course'],
            (int) $environment['teacher']->id,
            'T2',
            'stale'
        );
        $this->assertNotEmpty($rows);
        $this->assertTrue($rows[0]['stale']);
        $this->assertSame(get_string('reviewstatus_stale', 'local_compalign'), $rows[0]['reviewstatus']);
    }

    /**
     * A model row reports what the teacher decided, never "Not reviewed" after a decision.
     *
     * Regression: the review status was derived from the row's origin alone, so a model
     * proposal the teacher had accepted, rejected or modified still read "Not reviewed",
     * directly beside the teacher-reviewed row that contradicted it.
     */
    public function test_model_row_reports_the_teacher_decision(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $proposed = (string) $suggestion->competencyidnumber;
        $replacement = $proposed === 'T2' ? 'T1' : 'T2';
        $teacherid = (int) $environment['teacher']->id;
        $manager = new review_manager();

        $modelstatus = function () use ($environment, $teacherid, $proposed): string {
            $rows = (new relationship_index())->for_competency($environment['course'], $teacherid, $proposed, 'proposed');
            $this->assertCount(1, $rows);
            $this->assertSame(relationship_index::MODEL_PROPOSED, $rows[0]['source']);
            return (string) $rows[0]['reviewstatus'];
        };

        $this->assertSame(get_string('reviewstatus_notreviewed', 'local_compalign'), $modelstatus());

        $manager->save($made['analysis'], $suggestion, $teacherid, 'accept', null, null, null, null, $made['catalogue']);
        $this->assertSame(get_string('decision_accept_summary', 'local_compalign'), $modelstatus());

        $manager->save($made['analysis'], $suggestion, $teacherid, 'reject', null, null, null, null, $made['catalogue']);
        $this->assertSame(get_string('decision_reject_summary', 'local_compalign'), $modelstatus());

        $manager->save($made['analysis'], $suggestion, $teacherid, 'modify', $replacement, null, null, null, $made['catalogue']);
        $this->assertSame(get_string('decision_modify_summary', 'local_compalign', $replacement), $modelstatus());

        // The teacher-reviewed row is unaffected and still reads "Reviewed".
        $reviewed = (new relationship_index())->for_competency($environment['course'], $teacherid, $replacement, 'reviewed');
        $this->assertSame(get_string('reviewstatus_reviewed', 'local_compalign'), $reviewed[0]['reviewstatus']);
    }

    /**
     * Adding a competency in another course is refused.
     */
    public function test_wrong_course_is_refused(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $other = $this->getDataGenerator()->create_course();
        $hash = $this->hash_of($environment);
        $this->expectException(analysis_exception::class);
        (new manual_relationship())->add(
            $environment['cm'],
            'moodle:page:' . $environment['page']->id,
            (int) $other->id,
            (int) $environment['teacher']->id,
            'T1',
            $hash,
            '',
            '',
            \context_module::instance($environment['cm']->id)
        );
    }

    /**
     * @param array $environment The fixture.
     * @param string $hash The current fingerprint.
     * @return array
     */
    private function bundle(array $environment, string $hash): array {
        $resourceid = 'moodle:page:' . $environment['page']->id;
        return (new relationship_index())->bundles(
            (int) $environment['course']->id,
            (int) $environment['teacher']->id,
            [$resourceid => $hash]
        )[$resourceid];
    }

    /**
     * @param array $environment The fixture.
     * @return string
     */
    private function hash_of(array $environment): string {
        $this->setUser($environment['teacher']);
        $cm = get_fast_modinfo($environment['course'])->get_cm($environment['cm']->id);
        return (new resource_extractor())->extract($cm, 'moodle:page:' . $environment['page']->id)['hash'];
    }

    /**
     * @param array $environment The fixture.
     * @param string $idnumber The competency.
     * @param string $hash The fingerprint shown on the form.
     * @param string $evidence Optional quotation.
     * @param string $comment Optional comment.
     * @return \stdClass
     */
    private function add(array $environment, string $idnumber, string $hash, string $evidence = '', string $comment = ''): \stdClass {
        $this->setUser($environment['teacher']);
        $cm = get_fast_modinfo($environment['course'])->get_cm($environment['cm']->id);
        return (new manual_relationship())->add(
            $cm,
            'moodle:page:' . $environment['page']->id,
            (int) $environment['course']->id,
            (int) $environment['teacher']->id,
            $idnumber,
            $hash,
            $evidence,
            $comment,
            \context_module::instance($cm->id)
        );
    }
}
