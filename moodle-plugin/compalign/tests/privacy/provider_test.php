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
use core_privacy\local\request\userlist;
use core_privacy\local\request\writer;
use core_privacy\tests\provider_testcase;
use local_compalign\fixtures\environment;
use local_compalign\service\review_manager;
use PHPUnit\Framework\Attributes\CoversClass;

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Tests for the privacy provider: what is described, exported and deleted.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(provider::class)]
final class provider_test extends provider_testcase {
    use environment;

    /**
     * Build a course where the teacher requested an analysis and two teachers reviewed it.
     *
     * @param string $suffix Added to the framework ID number, so a test can build a second course.
     * @return array The environment, the analysis, and the colleague who also reviewed.
     */
    private function create_reviewed_course(string $suffix = ''): array {
        $environment = $this->create_environment($suffix);
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $colleague = $this->getDataGenerator()->create_and_enrol($environment['course'], 'editingteacher');
        $manager = new review_manager();

        $manager->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'accept',
            null,
            '2',
            'Clear match.',
            time() - 20,
            $made['catalogue']
        );
        $manager->save(
            $made['analysis'],
            $suggestion,
            (int) $colleague->id,
            'reject',
            null,
            '0',
            'Too broad.',
            null,
            $made['catalogue']
        );

        return [$environment, $made, $colleague];
    }

    /**
     * Everything the plugin stores about people, and what it sends out, is described.
     */
    public function test_get_metadata(): void {
        $items = provider::get_metadata(new collection('local_compalign'))->get_collection();

        $names = array_map(static fn($item): string => $item->get_name(), $items);
        $this->assertEqualsCanonicalizing(['local_compalign_analysis', 'local_compalign_review', 'alignmentservice'], $names);

        foreach ($items as $item) {
            $keys = array_merge([$item->get_summary()], array_values($item->get_privacy_fields()));
            foreach ($keys as $key) {
                $this->assertTrue(get_string_manager()->string_exists($key, 'local_compalign'), "Missing string: $key");
            }
        }
    }

    /**
     * Requesters and reviewers have data in their course, and others do not.
     */
    public function test_contexts_and_users(): void {
        $this->resetAfterTest();
        [$environment, , $colleague] = $this->create_reviewed_course();
        $context = \context_course::instance($environment['course']->id);

        $teachercontexts = provider::get_contexts_for_userid($environment['teacher']->id)->get_contextids();
        $colleaguecontexts = provider::get_contexts_for_userid($colleague->id)->get_contextids();
        $this->assertSame([(int) $context->id], array_map('intval', $teachercontexts));
        $this->assertSame([(int) $context->id], array_map('intval', $colleaguecontexts));
        $this->assertSame([], provider::get_contexts_for_userid($environment['student']->id)->get_contextids());

        $userlist = new userlist($context, 'local_compalign');
        provider::get_users_in_context($userlist);
        $this->assertEqualsCanonicalizing(
            [(int) $environment['teacher']->id, (int) $colleague->id],
            array_map('intval', $userlist->get_userids())
        );
    }

    /**
     * A requester's export holds their analyses and their own reviews, and nobody else's.
     */
    public function test_export_user_data(): void {
        $this->resetAfterTest();
        [$environment] = $this->create_reviewed_course();
        $context = \context_course::instance($environment['course']->id);

        $this->export_context_data_for_user((int) $environment['teacher']->id, $context, 'local_compalign');
        $writer = writer::with_context($context);

        $this->assertTrue($writer->has_any_data());
        $exported = $writer->get_data([get_string('privacy:path:reviews', 'local_compalign')]);
        $this->assertCount(1, $exported->reviews);
        $this->assertSame('accept', $exported->reviews[0]->decision);
        $this->assertSame('Clear match.', $exported->reviews[0]->comment);
        $this->assertStringNotContainsString('Too broad.', json_encode($exported), 'Another teacher\'s comment is not exported.');

        $this->assertCount(1, $writer->get_data([get_string('privacy:path:analyses', 'local_compalign')])->analyses);
    }

    /**
     * A reviewer who requested nothing has reviews to export but no analyses.
     */
    public function test_export_user_data_of_a_reviewer(): void {
        $this->resetAfterTest();
        [$environment, , $colleague] = $this->create_reviewed_course();
        $context = \context_course::instance($environment['course']->id);

        $this->export_context_data_for_user((int) $colleague->id, $context, 'local_compalign');
        $writer = writer::with_context($context);

        $exported = $writer->get_data([get_string('privacy:path:reviews', 'local_compalign')]);
        $this->assertSame('reject', $exported->reviews[0]->decision);
        $this->assertEmpty($writer->get_data([get_string('privacy:path:analyses', 'local_compalign')]));
    }

    /**
     * Deleting a user removes their reviews, unlinks them from their analyses, and keeps what others rely on.
     */
    public function test_delete_data_for_user(): void {
        global $DB;

        $this->resetAfterTest();
        [$environment, $made, $colleague] = $this->create_reviewed_course();
        $context = \context_course::instance($environment['course']->id);

        provider::delete_data_for_user(new approved_contextlist(
            $environment['teacher'],
            'local_compalign',
            [$context->id]
        ));

        $this->assertSame(0, $DB->count_records('local_compalign_review', ['userid' => $environment['teacher']->id]));
        $this->assertSame(1, $DB->count_records('local_compalign_review', ['userid' => $colleague->id]));
        $this->assertEquals(0, $DB->get_field('local_compalign_analysis', 'requestedby', ['id' => $made['analysis']->id]));
        $this->assertSame(1, $DB->count_records('local_compalign_sugg'), 'The model\'s suggestions describe a page, not a person.');
        $this->assertSame(1, $DB->count_records('local_compalign_evidence'));
    }

    /**
     * Deleting several users in a course works the same way.
     */
    public function test_delete_data_for_users(): void {
        global $DB;

        $this->resetAfterTest();
        [$environment, $made, $colleague] = $this->create_reviewed_course();
        $context = \context_course::instance($environment['course']->id);

        provider::delete_data_for_users(new approved_userlist(
            $context,
            'local_compalign',
            [(int) $environment['teacher']->id, (int) $colleague->id]
        ));

        $this->assertSame(0, $DB->count_records('local_compalign_review'));
        $this->assertEquals(0, $DB->get_field('local_compalign_analysis', 'requestedby', ['id' => $made['analysis']->id]));
        $this->assertSame(1, $DB->count_records('local_compalign_analysis'));
    }

    /**
     * Deleting a course removes its analyses with everything that belongs to them, and only those.
     */
    public function test_delete_data_for_all_users_in_context(): void {
        global $DB;

        $this->resetAfterTest();
        [$environment] = $this->create_reviewed_course();
        [$other] = $this->create_reviewed_course('B');
        $context = \context_course::instance($environment['course']->id);

        // Another kind of context is not the plugin's to delete.
        provider::delete_data_for_all_users_in_context(\context_module::instance($environment['cm']->id));
        $this->assertSame(2, $DB->count_records('local_compalign_analysis'));

        provider::delete_data_for_all_users_in_context($context);

        $this->assertSame(0, $DB->count_records('local_compalign_analysis', ['courseid' => $environment['course']->id]));
        $this->assertSame(1, $DB->count_records('local_compalign_analysis', ['courseid' => $other['course']->id]));
        $this->assertSame(1, $DB->count_records('local_compalign_sugg'));
        $this->assertSame(1, $DB->count_records('local_compalign_evidence'));
        $this->assertSame(2, $DB->count_records('local_compalign_review'), 'Only the other course keeps its two reviews.');
    }
}
