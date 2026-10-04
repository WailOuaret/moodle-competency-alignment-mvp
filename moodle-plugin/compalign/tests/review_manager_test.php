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

use advanced_testcase;
use local_compalign\event\review_saved;
use local_compalign\fixtures\environment;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/fixtures/fake_transport.php');
require_once(__DIR__ . '/fixtures/service_stub.php');
require_once(__DIR__ . '/fixtures/environment.php');

/**
 * Tests for the teacher's decision on a suggested competency.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(review_manager::class)]
final class review_manager_test extends advanced_testcase {
    use environment;

    /**
     * Decisions with the fields that must be reported, if any.
     *
     * @return array<string, array>
     */
    public static function error_provider(): array {
        $valid = ['T1', 'T1_1', 'T2'];

        return [
            'accept without a rating' => ['accept', null, null, null, 'T1', $valid, []],
            'accept with every field' => ['accept', '', '2', 'Clear.', 'T1', $valid, []],
            'reject with a rating of zero' => ['reject', null, '0', null, 'T1', $valid, []],
            'rating given as the integer zero' => ['accept', null, 0, null, 'T1', $valid, []],
            'modify to another competency' => ['modify', 'T2', '1', null, 'T1', $valid, []],
            'modify to a child of the proposed one' => ['modify', 'T1_1', null, null, 'T1', $valid, []],
            'no decision' => ['', null, null, null, 'T1', $valid, ['decision']],
            'unknown decision' => ['approve', null, null, null, 'T1', $valid, ['decision']],
            'decision in capitals' => ['ACCEPT', null, null, null, 'T1', $valid, ['decision']],
            'modify without a competency' => ['modify', '', null, null, 'T1', $valid, ['finalcompetency']],
            'modify with only spaces' => ['modify', '  ', null, null, 'T1', $valid, ['finalcompetency']],
            'modify to the proposed competency' => ['modify', 'T1', null, null, 'T1', $valid, ['finalcompetency']],
            'modify to an unknown competency' => ['modify', 'ZZ', null, null, 'T1', $valid, ['finalcompetency']],
            'rating 3' => ['accept', null, '3', null, 'T1', $valid, ['usefulness']],
            'rating -1' => ['accept', null, '-1', null, 'T1', $valid, ['usefulness']],
            'rating that is text' => ['accept', null, 'abc', null, 'T1', $valid, ['usefulness']],
            'rating with a decimal' => ['accept', null, '1.5', null, 'T1', $valid, ['usefulness']],
            'rating given as a list' => ['accept', null, ['1'], null, 'T1', $valid, ['usefulness']],
            'comment of 1000 characters' => ['accept', null, null, str_repeat('a', 1000), 'T1', $valid, []],
            'comment of 1001 characters' => ['accept', null, null, str_repeat('a', 1001), 'T1', $valid, ['commenttext']],
            'comment is counted in characters, not bytes' => ['accept', null, null, str_repeat('é', 1000), 'T1', $valid, []],
            'several problems at once' => [
                'modify', 'T1', '9', str_repeat('a', 1001), 'T1', $valid, ['finalcompetency', 'usefulness', 'commenttext'],
            ],
        ];
    }

    /**
     * Every problem with a decision is found, and nothing else is.
     *
     * @param string $decision The decision.
     * @param string|null $final The competency chosen for a modification.
     * @param mixed $usefulness The rating.
     * @param string|null $comment The comment.
     * @param string $proposed The proposed competency.
     * @param string[] $valid The competencies of the framework.
     * @param string[] $expectedfields The fields with an error.
     */
    #[DataProvider('error_provider')]
    public function test_find_errors(
        string $decision,
        ?string $final,
        mixed $usefulness,
        ?string $comment,
        string $proposed,
        array $valid,
        array $expectedfields
    ): void {
        $errors = review_manager::find_errors($decision, $final, $usefulness, $comment, $proposed, $valid);

        $this->assertEqualsCanonicalizing($expectedfields, array_keys($errors));
        foreach ($errors as $message) {
            $this->assertNotSame('', $message);
        }
    }

    /**
     * Ratings, with whether the submitted value was acceptable.
     *
     * @return array<string, array>
     */
    public static function usefulness_provider(): array {
        return [
            'not given' => [null, null, true],
            'empty' => ['', null, true],
            'zero is a rating' => [0, 0, true],
            'zero as text' => ['0', 0, true],
            'one' => ['1', 1, true],
            'two as an integer' => [2, 2, true],
            'too high' => ['3', null, false],
            'negative' => ['-1', null, false],
            'text' => ['x', null, false],
        ];
    }

    /**
     * A rating is optional, and zero is a real rating.
     *
     * @param mixed $value The submitted value.
     * @param int|null $expected The rating that is read.
     * @param bool $expectedvalid Whether the value was acceptable.
     */
    #[DataProvider('usefulness_provider')]
    public function test_normalise_usefulness(mixed $value, ?int $expected, bool $expectedvalid): void {
        $this->assertSame($expected, review_manager::normalise_usefulness($value, $valid));
        $this->assertSame($expectedvalid, $valid);
    }

    /**
     * The final competency follows from the decision.
     */
    public function test_final_idnumber(): void {
        $this->assertSame('T1', review_manager::final_idnumber('accept', 'T1', null));
        $this->assertSame(
            'T1',
            review_manager::final_idnumber('accept', 'T1', 'T2'),
            'A submitted value never replaces the proposal.'
        );
        $this->assertSame('T2', review_manager::final_idnumber('modify', 'T1', ' T2 '));
        $this->assertNull(review_manager::final_idnumber('reject', 'T1', 'T2'));
    }

    /**
     * Review times, with the start and the end in seconds.
     *
     * @return array<string, array>
     */
    public static function duration_provider(): array {
        return [
            'start unknown' => [null, 100, null],
            'saved at once' => [100, 100, 0],
            'ordinary review' => [100, 137, 37],
            'exactly four hours' => [100, 100 + 14400, 14400],
            'longer than four hours' => [100, 100 + 14401, null],
            'start in the future' => [100, 99, null],
        ];
    }

    /**
     * The review time is the time between the first display and the save, or unknown.
     *
     * @param int|null $start When the card was first shown.
     * @param int $now When the decision was saved.
     * @param int|null $expected The recorded seconds.
     */
    #[DataProvider('duration_provider')]
    public function test_review_duration(?int $start, int $now, ?int $expected): void {
        $this->assertSame($expected, review_manager::review_duration($start, $now));
    }

    /**
     * Accepting records the proposed competency and leaves write-back disabled.
     */
    public function test_accept_records_the_proposed_competency(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);

        $review = (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            review_manager::DECISION_ACCEPT,
            null,
            '2',
            'Clear match.',
            time() - 30,
            $made['catalogue']
        );

        $stored = $DB->get_record('local_compalign_review', ['id' => $review->id], '*', MUST_EXIST);
        $this->assertSame('accept', $stored->decision);
        $this->assertEquals($suggestion->competencyid, $stored->finalcompetencyid);
        $this->assertSame($suggestion->competencyidnumber, $stored->finalcompetencyidnumber);
        $this->assertEquals(2, $stored->evidenceusefulness);
        $this->assertSame('Clear match.', $stored->commenttext);
        $this->assertEquals(1, $stored->revision);
        $this->assertGreaterThanOrEqual(30, (int) $stored->reviewdurationseconds);
        $this->assertSame(review_manager::WRITEBACK_DISABLED, $stored->writebackstatus);
    }

    /**
     * Rejecting creates no Moodle competency link and queues no task.
     */
    public function test_reject_creates_no_link_and_no_task(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);

        $modulelinks = $DB->count_records('competency_modulecomp');
        $courselinks = $DB->count_records('competency_coursecomp');
        $tasks = $DB->count_records('task_adhoc');
        $sink = $this->redirectEvents();

        $review = (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            review_manager::DECISION_REJECT,
            null,
            '0',
            null,
            null,
            $made['catalogue']
        );

        $stored = $DB->get_record('local_compalign_review', ['id' => $review->id], '*', MUST_EXIST);
        $this->assertSame('reject', $stored->decision);
        $this->assertNull($stored->finalcompetencyid);
        $this->assertNull($stored->finalcompetencyidnumber);
        $this->assertNull($stored->reviewdurationseconds, 'Without a known start the time is unknown, not zero.');
        $this->assertEquals(0, $stored->evidenceusefulness, 'A rating of zero is a rating, not an absent one.');
        $this->assertSame(review_manager::WRITEBACK_NONE, $stored->writebackstatus);

        $this->assertSame($modulelinks, $DB->count_records('competency_modulecomp'));
        $this->assertSame($courselinks, $DB->count_records('competency_coursecomp'));
        $this->assertSame($tasks, $DB->count_records('task_adhoc'));

        $names = array_map(static fn($event): string => get_class($event), $sink->get_events());
        $this->assertSame([review_saved::class], $names, 'Only the plugin\'s own event is triggered.');
    }

    /**
     * Accepting and modifying only record the decision: no link is created while write-back is off.
     */
    public function test_accept_and_modify_create_no_link(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $other = $this->other_idnumber($made['catalogue'], $suggestion->competencyidnumber);
        $manager = new review_manager();
        $userid = (int) $environment['teacher']->id;

        $modulelinks = $DB->count_records('competency_modulecomp');
        $courselinks = $DB->count_records('competency_coursecomp');
        $tasks = $DB->count_records('task_adhoc');

        $manager->save($made['analysis'], $suggestion, $userid, 'accept', null, null, null, null, $made['catalogue']);
        $manager->save($made['analysis'], $suggestion, $userid, 'modify', $other, null, null, null, $made['catalogue']);

        $this->assertSame($modulelinks, $DB->count_records('competency_modulecomp'));
        $this->assertSame($courselinks, $DB->count_records('competency_coursecomp'));
        $this->assertSame($tasks, $DB->count_records('task_adhoc'));
        $this->assertSame([], \core_competency\api::list_course_module_competencies($environment['cm']->id));
    }

    /**
     * Modifying records the competency the teacher chose, with its Moodle id.
     */
    public function test_modify_records_the_chosen_competency(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $other = $this->other_idnumber($made['catalogue'], $suggestion->competencyidnumber);

        $review = (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            review_manager::DECISION_MODIFY,
            $other,
            '1',
            null,
            null,
            $made['catalogue']
        );

        $stored = $DB->get_record('local_compalign_review', ['id' => $review->id], '*', MUST_EXIST);
        $this->assertSame($other, $stored->finalcompetencyidnumber);
        $this->assertEquals($made['catalogue']->find($other)['id'], $stored->finalcompetencyid);
        $this->assertSame(review_manager::WRITEBACK_DISABLED, $stored->writebackstatus);
    }

    /**
     * Invalid decisions are refused and nothing is stored.
     */
    public function test_invalid_decisions_store_nothing(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $userid = (int) $environment['teacher']->id;
        $manager = new review_manager();

        // A real competency, but of a framework the assistant is not configured to use.
        $generator = $this->getDataGenerator()->get_plugin_generator('core_competency');
        $elsewhere = $generator->create_framework(['idnumber' => 'OTHER', 'shortname' => 'Another framework']);
        $generator->create_competency([
            'competencyframeworkid' => $elsewhere->get('id'),
            'idnumber' => 'O1',
            'shortname' => 'Elsewhere',
            'description' => 'Belongs to another framework.',
        ]);

        $attempts = [
            'modify without a competency' => ['modify', null, null, null],
            'modify to the proposed competency' => ['modify', $suggestion->competencyidnumber, null, null],
            'modify to an unknown competency' => ['modify', 'ZZ', null, null],
            'modify to a competency of another framework' => ['modify', 'O1', null, null],
            'unknown decision' => ['approve', null, null, null],
            'rating out of range' => ['accept', null, '3', null],
            'comment too long' => ['accept', null, null, str_repeat('a', 1001)],
        ];

        foreach ($attempts as $label => [$decision, $final, $usefulness, $comment]) {
            try {
                $manager->save(
                    $made['analysis'],
                    $suggestion,
                    $userid,
                    $decision,
                    $final,
                    $usefulness,
                    $comment,
                    null,
                    $made['catalogue']
                );
                $this->fail("$label was accepted.");
            } catch (analysis_exception $exception) {
                $this->assertSame('invalid_review', $exception->get_error_code(), $label);
            }
        }

        $this->assertSame(0, $DB->count_records('local_compalign_review'));
    }

    /**
     * A suggestion can only be reviewed through the completed analysis it belongs to.
     */
    public function test_a_suggestion_of_another_or_unfinished_analysis_is_refused(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $userid = (int) $environment['teacher']->id;
        $manager = new review_manager();

        $another = clone $made['analysis'];
        $another->id = $made['analysis']->id + 1;
        $failed = clone $made['analysis'];
        $failed->status = analysis_manager::STATUS_FAILED;

        foreach ([$another, $failed] as $analysis) {
            try {
                $manager->save($analysis, $suggestion, $userid, 'accept', null, null, null, null, $made['catalogue']);
                $this->fail('The review was accepted.');
            } catch (analysis_exception $exception) {
                $this->assertSame('invalid_review', $exception->get_error_code());
            }
        }

        $this->assertSame(0, $DB->count_records('local_compalign_review'));
    }

    /**
     * Ratings as they may arrive, with what is stored.
     *
     * @return array<string, array>
     */
    public static function stored_rating_provider(): array {
        return [
            'not given' => [null, null],
            'empty' => ['', null],
            'zero' => ['0', 0],
            'zero as an integer' => [0, 0],
            'one' => ['1', 1],
            'two' => [2, 2],
        ];
    }

    /**
     * A rating is stored as 0, 1 or 2, and left empty only when none was given.
     *
     * @param mixed $given What was submitted.
     * @param int|null $expected What is stored.
     */
    #[DataProvider('stored_rating_provider')]
    public function test_the_rating_is_stored_as_given(mixed $given, ?int $expected): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);

        $review = (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'accept',
            null,
            $given,
            null,
            null,
            $made['catalogue']
        );

        $stored = $DB->get_field('local_compalign_review', 'evidenceusefulness', ['id' => $review->id]);
        if ($expected === null) {
            $this->assertNull($stored);
        } else {
            $this->assertNotNull($stored, 'A rating of zero must not be stored as empty.');
            $this->assertSame($expected, (int) $stored);
        }
    }

    /**
     * A comment is stored trimmed, in full up to the limit, and as empty when it is only spaces.
     */
    public function test_the_comment_is_trimmed_and_kept_whole(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $manager = new review_manager();
        $userid = (int) $environment['teacher']->id;
        $longest = str_repeat('é', review_manager::MAX_COMMENT_CHARS);

        $cases = [
            'padded' => ["  Clear match.  \n", 'Clear match.'],
            'only spaces' => ["   \n ", null],
            'not given' => [null, null],
            'the longest allowed' => [$longest, $longest],
        ];

        foreach ($cases as $label => [$comment, $expected]) {
            $review = $manager->save(
                $made['analysis'],
                $suggestion,
                $userid,
                'accept',
                null,
                null,
                $comment,
                null,
                $made['catalogue']
            );
            $this->assertSame($expected, $DB->get_field('local_compalign_review', 'commenttext', ['id' => $review->id]), $label);
        }
    }

    /**
     * The review time comes from the server clock: unknown, or between zero and four hours.
     */
    public function test_the_review_time_is_validated_when_saving(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $manager = new review_manager();
        $userid = (int) $environment['teacher']->id;

        $cases = [
            'start unknown' => [null, null, null],
            'one minute ago' => [time() - 60, 60, 65],
            'longer than four hours ago' => [time() - review_manager::MAX_REVIEW_SECONDS - 600, null, null],
            'a start in the future' => [time() + 3600, null, null],
        ];

        foreach ($cases as $label => [$startedat, $least, $most]) {
            $review = $manager->save(
                $made['analysis'],
                $suggestion,
                $userid,
                'accept',
                null,
                null,
                null,
                $startedat,
                $made['catalogue']
            );
            $duration = $DB->get_field('local_compalign_review', 'reviewdurationseconds', ['id' => $review->id]);

            if ($least === null) {
                $this->assertNull($duration, $label);
            } else {
                $this->assertGreaterThanOrEqual($least, (int) $duration, $label);
                $this->assertLessThanOrEqual($most, (int) $duration, $label);
            }
        }
    }

    /**
     * Every save is a new revision, earlier ones stay as they were, and each reviewer has their own.
     */
    public function test_every_save_appends_a_revision(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $other = $this->other_idnumber($made['catalogue'], $suggestion->competencyidnumber);
        $teacher = (int) $environment['teacher']->id;
        $colleague = (int) $this->getDataGenerator()->create_and_enrol($environment['course'], 'editingteacher')->id;
        $manager = new review_manager();

        $first = $manager->save(
            $made['analysis'],
            $suggestion,
            $teacher,
            'accept',
            null,
            '2',
            'First view.',
            null,
            $made['catalogue']
        );
        $firstrow = $DB->get_record('local_compalign_review', ['id' => $first->id]);
        $second = $manager->save($made['analysis'], $suggestion, $teacher, 'reject', null, null, null, null, $made['catalogue']);
        $third = $manager->save($made['analysis'], $suggestion, $teacher, 'modify', $other, null, null, null, $made['catalogue']);
        $theirs = $manager->save($made['analysis'], $suggestion, $colleague, 'accept', null, null, null, null, $made['catalogue']);

        $this->assertSame([1, 2, 3], [$first->revision, $second->revision, $third->revision]);
        $this->assertSame(1, $theirs->revision, 'Another reviewer starts again at one.');
        $this->assertEquals(
            $firstrow,
            $DB->get_record('local_compalign_review', ['id' => $first->id]),
            'An earlier revision is never edited.'
        );
        $this->assertSame(4, $DB->count_records('local_compalign_review'));

        $latest = $manager->latest_reviews((int) $made['analysis']->id, $teacher);
        $this->assertSame([(int) $suggestion->id], array_keys($latest));
        $this->assertEquals($third->id, $latest[(int) $suggestion->id]->id);
        $this->assertSame([], $manager->latest_reviews((int) $made['analysis']->id, (int) $environment['student']->id));
    }

    /**
     * The reviewer is the user the caller passes, and a review never changes what the model proposed.
     */
    public function test_the_reviewer_is_recorded_and_the_proposal_is_left_alone(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $other = $this->other_idnumber($made['catalogue'], $suggestion->competencyidnumber);
        $colleague = $this->getDataGenerator()->create_and_enrol($environment['course'], 'editingteacher');
        $manager = new review_manager();

        $suggestions = $DB->get_records('local_compalign_sugg');
        $evidence = $DB->get_records('local_compalign_evidence');

        $review = $manager->save(
            $made['analysis'],
            $suggestion,
            (int) $colleague->id,
            'modify',
            $other,
            '1',
            null,
            null,
            $made['catalogue']
        );
        $manager->save($made['analysis'], $suggestion, (int) $colleague->id, 'reject', null, null, null, null, $made['catalogue']);

        $this->assertSame((int) $colleague->id, $review->userid);
        $this->assertEquals((int) $colleague->id, $DB->get_field('local_compalign_review', 'userid', ['id' => $review->id]));
        $this->assertEquals($suggestions, $DB->get_records('local_compalign_sugg'));
        $this->assertEquals($evidence, $DB->get_records('local_compalign_evidence'));
    }

    /**
     * Saving triggers one event that says what was decided.
     */
    public function test_saving_triggers_an_event(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $sink = $this->redirectEvents();

        $review = (new review_manager())->save(
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

        $events = $sink->get_events();
        $this->assertCount(1, $events);
        $this->assertInstanceOf(review_saved::class, $events[0]);
        $this->assertEquals($review->id, $events[0]->objectid);
        $this->assertSame('accept', $events[0]->other['decision']);
        $this->assertSame(1, $events[0]->other['revision']);
        $this->assertEquals($environment['cm']->id, $events[0]->contextinstanceid);
    }

    /**
     * Another competency of the framework than the proposed one.
     *
     * @param catalogue_snapshot $catalogue The framework.
     * @param string $proposed The proposed competency.
     * @return string
     */
    private function other_idnumber(catalogue_snapshot $catalogue, string $proposed): string {
        foreach ($catalogue->idnumbers() as $idnumber) {
            if ($idnumber !== $proposed) {
                return $idnumber;
            }
        }

        $this->fail('The framework has no second competency.');
    }
}
