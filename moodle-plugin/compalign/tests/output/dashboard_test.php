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

use advanced_testcase;
use local_compalign\fixtures\environment;
use local_compalign\fixtures\service_stub;
use local_compalign\service\review_manager;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Tests for the course dashboard, rendered with Moodle's own renderer and templates.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(dashboard::class)]
final class dashboard_test extends advanced_testcase {
    use environment;

    /**
     * The status of a resource for each state of its analysis.
     *
     * @return array<string, array>
     */
    public static function status_provider(): array {
        $analysis = static fn(string $status): \stdClass => (object) ['status' => $status];

        return [
            'never analysed' => [null, 0, 0, 'none'],
            'queued' => [$analysis('queued'), 0, 0, 'queued'],
            'running' => [$analysis('running'), 0, 0, 'running'],
            'failed' => [$analysis('failed'), 0, 0, 'failed'],
            'completed, nothing suggested' => [$analysis('completed'), 0, 0, 'nosuggestion'],
            'completed, nothing reviewed' => [$analysis('completed'), 3, 0, 'ready'],
            'completed, some reviewed' => [$analysis('completed'), 3, 1, 'ready'],
            'completed, all reviewed' => [$analysis('completed'), 3, 3, 'reviewed'],
        ];
    }

    /**
     * The status follows the analysis and how much of it the user has reviewed.
     *
     * @param \stdClass|null $analysis The latest analysis.
     * @param int $total How many suggestions it has.
     * @param int $reviewed How many of them the user reviewed.
     * @param string $expected The status.
     */
    #[DataProvider('status_provider')]
    public function test_status_key(?\stdClass $analysis, int $total, int $reviewed, string $expected): void {
        $this->assertSame($expected, dashboard::status_key($analysis, $total, $reviewed));
    }

    /**
     * Tell the plugin where the alignment service is, so the assistant is ready to analyse.
     */
    private function configure_service(): void {
        set_config('serviceurl', 'https://align.example.org', 'local_compalign');
        set_config('servicetoken', \core\encryption::encrypt(service_stub::TOKEN), 'local_compalign');
    }

    /**
     * The dashboard of a course, as the current user sees it, as text.
     *
     * @param \stdClass $course The course.
     * @return string
     */
    private function dashboard_text(\stdClass $course): string {
        global $PAGE, $USER;

        $PAGE->set_url('/local/compalign/index.php', ['courseid' => $course->id]);
        $PAGE->set_context(\context_course::instance($course->id));
        $html = $PAGE->get_renderer('core')->render(dashboard::create($course, (int) $USER->id));

        return trim((string) preg_replace('/\s+/', ' ', html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5)));
    }

    /**
     * An assistant that is not ready says why and offers no analysis.
     */
    public function test_an_assistant_that_is_not_ready_explains_why_and_offers_nothing(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();

        $text = $this->dashboard_text($environment['course']);

        $this->assertStringContainsString('The assistant is not ready to analyse resources', $text);
        $this->assertStringContainsString('The alignment service address is not set.', $text);
        $this->assertStringNotContainsString('Suggest competencies', $text);
    }

    /**
     * Every resource is listed with its state, and only a Page without an analysis offers to start one.
     */
    public function test_each_resource_is_listed_with_its_state(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $this->configure_service();
        $this->getDataGenerator()->create_module('choice', ['course' => $environment['course']->id, 'name' => 'News']);

        $text = $this->dashboard_text($environment['course']);

        $this->assertStringNotContainsString('not ready', $text);
        $this->assertStringContainsString('Software testing', $text);
        $this->assertStringContainsString('Not analysed', $text);
        $this->assertSame(1, substr_count($text, 'Suggest competencies'), 'Only the Page offers to start an analysis.');
        $this->assertStringContainsString('News', $text);
        $this->assertSame(1, substr_count($text, 'Unsupported resource type.'));

        $this->create_completed_analysis($environment);
        $text = $this->dashboard_text($environment['course']);

        $this->assertStringContainsString('Suggestions ready', $text);
        $this->assertStringContainsString('View suggestions', $text);
        $this->assertStringNotContainsString('Suggest competencies', $text);
    }

    /**
     * Progress is shown while suggestions are unreviewed, and the resource is reviewed once every one is.
     */
    public function test_review_progress_is_shown(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $this->configure_service();
        $quotes = ['Unit tests check one function at a time.', 'Integration tests check how the parts of a program work together.'];
        $made = $this->create_completed_analysis($environment, ['suggestions' => array_map(
            static fn(string $idnumber, string $quote): array => [
                'competency_idnumber' => $idnumber,
                'confidence' => 0.8,
                'bm25_rank' => 1,
                'support_count' => 1,
                'evidence' => [['fragment_id' => 'moodle:page:1#f001', 'quote' => $quote]],
                'warnings' => [],
            ],
            ['T1', 'T2'],
            $quotes
        )]);
        $manager = new review_manager();
        $userid = (int) $environment['teacher']->id;
        $suggestions = array_values($made['suggestions']);

        $manager->save($made['analysis'], $suggestions[0], $userid, 'accept', null, null, null, null, $made['catalogue']);
        $text = $this->dashboard_text($environment['course']);
        $this->assertStringContainsString('Suggestions ready', $text);
        $this->assertStringContainsString('1 of 2 reviewed', $text);

        $manager->save($made['analysis'], $suggestions[1], $userid, 'reject', null, null, null, null, $made['catalogue']);
        $text = $this->dashboard_text($environment['course']);
        $this->assertStringContainsString('Reviewed', $text);
        $this->assertStringNotContainsString('of 2 reviewed', $text);
    }

    /**
     * A failed analysis is shown as failed.
     */
    public function test_a_failed_analysis_is_shown(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $this->configure_service();
        $manager = $this->create_manager([service_stub::error(401, 'auth_invalid')]);

        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);
        $manager->run((int) $requested['analysis']->id);

        $this->assertStringContainsString('Failed', $this->dashboard_text($environment['course']));
    }

    /**
     * The official links a resource already has are listed beside its state.
     */
    public function test_the_official_links_are_listed(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $this->configure_service();

        // Set up an official link the way a teacher would, before looking at the dashboard.
        $this->setAdminUser();
        $courseid = (int) $environment['course']->id;
        $competencyid = (int) $environment['competencies']['T2']->get('id');
        \core_competency\api::add_competency_to_course($courseid, $competencyid);
        \core_competency\api::add_competency_to_course_module((int) $environment['cm']->id, $competencyid);
        $this->setUser($environment['teacher']);

        $text = $this->dashboard_text($environment['course']);

        $this->assertStringContainsString('T2 Deploy software', $text);
    }

    /**
     * A student sees no hidden resource and is offered no analysis.
     */
    public function test_a_student_sees_no_hidden_resource_and_no_button(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $this->configure_service();
        $this->getDataGenerator()->create_module('page', [
            'course' => $environment['course']->id,
            'name' => 'Secret page',
            'visible' => 0,
        ]);

        $this->setUser($environment['student']);
        $text = $this->dashboard_text($environment['course']);

        $this->assertStringContainsString('Software testing', $text);
        $this->assertStringNotContainsString('Secret page', $text);
        $this->assertStringNotContainsString('Suggest competencies', $text);
    }
}
