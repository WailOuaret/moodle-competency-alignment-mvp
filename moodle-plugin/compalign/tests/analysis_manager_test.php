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
use GuzzleHttp\Exception\ConnectException;
use GuzzleHttp\Psr7\Request;
use GuzzleHttp\Psr7\Response;
use local_compalign\event\analysis_requested;
use local_compalign\fixtures\environment;
use local_compalign\fixtures\fake_transport;
use local_compalign\fixtures\service_stub;
use local_compalign\task\analyse_resource;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/fixtures/fake_transport.php');
require_once(__DIR__ . '/fixtures/service_stub.php');
require_once(__DIR__ . '/fixtures/environment.php');

/**
 * Tests for requesting, running and storing analyses.
 *
 * The alignment service is replaced by a stub: no request leaves the test.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(analysis_manager::class)]
#[CoversClass(analyse_resource::class)]
final class analysis_manager_test extends advanced_testcase {
    use environment;

    /**
     * Requesting records the request and queues a task, and never calls the service.
     */
    public function test_a_request_is_queued_without_calling_the_service(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $transports = [];
        $manager = new analysis_manager(function () use (&$transports) {
            return service_stub::client([], $transports[]);
        });
        $sink = $this->redirectEvents();

        $result = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);

        $this->assertSame(analysis_manager::OUTCOME_QUEUED, $result['outcome']);
        $stored = $DB->get_record('local_compalign_analysis', ['id' => $result['analysis']->id], '*', MUST_EXIST);
        $this->assertSame(analysis_manager::STATUS_QUEUED, $stored->status);
        $this->assertEquals($environment['course']->id, $stored->courseid);
        $this->assertEquals($environment['cm']->id, $stored->cmid);
        $this->assertSame('moodle:page:' . $environment['page']->id, $stored->resourceid);
        $this->assertSame((new resource_extractor())->extract($environment['cm'])['hash'], $stored->resourcehash);
        $this->assertSame((new competency_catalogue())->build()->hash, $stored->cataloguehash);
        $this->assertEquals($environment['framework']->get('id'), $stored->frameworkid);
        $this->assertEquals($environment['teacher']->id, $stored->requestedby);
        $this->assertEquals(5, $stored->topk);
        $this->assertEquals(3, $stored->maxsuggestions);
        $this->assertMatchesRegularExpression('/^compalign-[0-9a-f]{16}$/', $stored->requestid);

        $tasks = \core\task\manager::get_adhoc_tasks(analyse_resource::class);
        $this->assertCount(1, $tasks);
        $task = reset($tasks);
        $this->assertEquals($environment['teacher']->id, $task->get_userid());
        $this->assertEquals($stored->id, $task->get_custom_data()->analysisid);

        $events = $sink->get_events();
        $this->assertCount(1, $events);
        $this->assertInstanceOf(analysis_requested::class, $events[0]);

        $this->assertNotEmpty($transports, 'The client was never built, so the check below would prove nothing.');
        foreach ($transports as $transport) {
            $this->assertSame([], $transport->requests, 'Requesting must not touch the network.');
        }
    }

    /**
     * A second request while one is waiting does not queue another.
     */
    public function test_a_second_request_reports_the_one_in_progress(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $manager = $this->create_manager();
        $userid = (int) $environment['teacher']->id;

        $first = $manager->request_analysis($environment['cm'], $userid);
        $second = $manager->request_analysis($environment['cm'], $userid, true);

        $this->assertSame(analysis_manager::OUTCOME_ACTIVE, $second['outcome']);
        $this->assertEquals($first['analysis']->id, $second['analysis']->id);
        $this->assertSame(1, $DB->count_records('local_compalign_analysis'));
        $this->assertCount(1, \core\task\manager::get_adhoc_tasks(analyse_resource::class));
    }

    /**
     * An identical completed analysis is offered again, unless the teacher asks for a new one.
     */
    public function test_an_identical_analysis_is_reused_unless_forced(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $manager = $this->create_manager();
        $userid = (int) $environment['teacher']->id;

        $again = $manager->request_analysis($environment['cm'], $userid);
        $this->assertSame(analysis_manager::OUTCOME_REUSED, $again['outcome']);
        $this->assertEquals($made['analysis']->id, $again['analysis']->id);

        $forced = $manager->request_analysis($environment['cm'], $userid, true);
        $this->assertSame(analysis_manager::OUTCOME_QUEUED, $forced['outcome']);
        $this->assertNotEquals($made['analysis']->id, $forced['analysis']->id);
        $this->assertSame(2, $DB->count_records('local_compalign_analysis'), 'The earlier analysis is kept.');
    }

    /**
     * Once the Page has changed, an earlier analysis no longer counts as identical.
     */
    public function test_a_changed_page_is_analysed_again(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $DB->set_field('page', 'content', '<p>Deploying software means releasing it.</p>', ['id' => $environment['page']->id]);

        $result = $this->create_manager()->request_analysis($environment['cm'], (int) $environment['teacher']->id);

        $this->assertSame(analysis_manager::OUTCOME_QUEUED, $result['outcome']);
        $this->assertNotEquals($made['analysis']->id, $result['analysis']->id);
    }

    /**
     * What is sent to the service: the Page, the framework and the settings, and nothing about people.
     */
    public function test_the_request_to_the_service_holds_only_the_resource_and_the_catalogue(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $transports = [];
        $manager = new analysis_manager(function () use (&$transports) {
            return service_stub::client([service_stub::answer_analysis()], $transports[]);
        });

        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);
        $manager->run((int) $requested['analysis']->id);

        $sent = null;
        foreach ($transports as $transport) {
            foreach ($transport->requests as $request) {
                $sent = $request;
            }
        }
        $this->assertNotNull($sent, 'No request reached the service.');
        $this->assertSame(['POST', '/v1/analyses', 'Bearer ' . service_stub::TOKEN], [
            $sent['method'], $sent['path'], $sent['authorization'],
        ]);

        $body = json_decode($sent['body'], true);
        $this->assertEqualsCanonicalizing(['schema_version', 'resource', 'competencies', 'config'], array_keys($body));
        $this->assertSame('1.0', $body['schema_version']);
        $this->assertSame(['top_k' => 5, 'max_suggestions' => 3], $body['config']);
        $this->assertSame('moodle:page:' . $environment['page']->id, $body['resource']['resource_id']);
        $this->assertCount(3, $body['competencies']);
        $this->assertSame($requested['analysis']->requestid, $sent['requestid']);

        foreach ([$environment['teacher'], $environment['student']] as $user) {
            $this->assertStringNotContainsString($user->email, $sent['body']);
            $this->assertStringNotContainsString($user->lastname, $sent['body']);
        }
    }

    /**
     * The validated answer is stored: the analysis, its suggestions and their evidence.
     */
    public function test_run_stores_the_validated_answer(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();

        $made = $this->create_completed_analysis($environment);
        $analysis = $made['analysis'];

        $this->assertSame(analysis_manager::STATUS_COMPLETED, $analysis->status);
        $this->assertSame('mock', $analysis->backend);
        $this->assertSame('stub-1', $analysis->model);
        $this->assertSame('complete', $analysis->completeness);
        $this->assertEquals(0, $analysis->abstained);
        $this->assertNull($analysis->errorcode);
        $this->assertSame(5, json_decode($analysis->manifest, true)['top_k']);

        $this->assertCount(1, $made['suggestions']);
        $suggestion = reset($made['suggestions']);
        $this->assertEquals($made['catalogue']->find($suggestion->competencyidnumber)['id'], $suggestion->competencyid);
        $this->assertEquals(0.8, $suggestion->confidence);
        $this->assertEquals(1, $suggestion->bm25rank);
        $this->assertSame([], $suggestion->warningslist);
        $this->assertCount(1, $suggestion->evidence);
        $this->assertSame('Introduction to software testing.', reset($suggestion->evidence)->evidencetext);
        $this->assertSame(1, $DB->count_records('local_compalign_evidence'));
    }

    /**
     * Each way a run can fail leaves a failed analysis with a stable code, and nothing else.
     *
     * @return array<string, array>
     */
    public static function failure_provider(): array {
        $request = new Request('POST', 'http://service.test:8001/v1/analyses');

        return [
            'the token is refused' => [service_stub::error(401, 'auth_invalid'), 'unauthorized'],
            'the model output did not pass' => [service_stub::error(502, 'model_output_invalid'), 'model_output_invalid'],
            'the model is not available' => [service_stub::error(503, 'backend_unavailable'), 'backend_unavailable'],
            'the service fails' => [new Response(500, [], 'secret detail'), 'unavailable'],
            'the service cannot be reached' => [new ConnectException('cURL error 7: secret detail', $request), 'unavailable'],
            'the answer is not JSON' => [new Response(200, [], 'secret detail'), 'invalid_response'],
            'the answer names another resource' => [
                service_stub::answer_analysis(['resource_id' => 'moodle:page:999999']),
                'invalid_response',
            ],
            'the answer quotes words that are not on the page' => [
                static function ($request): Response {
                    $answer = service_stub::analysis(json_decode((string) $request->getBody(), true));
                    $answer['suggestions'][0]['evidence'][0]['quote'] = 'Words that were never written here.';
                    return service_stub::json(200, $answer);
                },
                'invalid_response',
            ],
            'the answer proposes a competency that was not sent' => [
                static function ($request): Response {
                    $answer = service_stub::analysis(json_decode((string) $request->getBody(), true));
                    $answer['suggestions'][0]['competency_idnumber'] = 'ZZ';
                    return service_stub::json(200, $answer);
                },
                'invalid_response',
            ],
        ];
    }

    /**
     * A failed run is recorded on the analysis, shows nothing it should not, and stores no suggestion.
     *
     * @param mixed $answer What the stub of the service gives.
     * @param string $expectedcode The error code that is stored.
     */
    #[DataProvider('failure_provider')]
    public function test_a_failed_run_is_recorded(mixed $answer, string $expectedcode): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $manager = $this->create_manager([$answer]);

        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);
        $manager->run((int) $requested['analysis']->id);

        $analysis = $DB->get_record('local_compalign_analysis', ['id' => $requested['analysis']->id], '*', MUST_EXIST);
        $this->assertSame(analysis_manager::STATUS_FAILED, $analysis->status);
        $this->assertSame($expectedcode, $analysis->errorcode);
        $this->assertStringNotContainsString('secret', (string) $analysis->errormessage);
        $this->assertStringNotContainsString('Words that were never written', (string) $analysis->errormessage);
        $this->assertSame(0, $DB->count_records('local_compalign_sugg'));
        $this->assertSame(0, $DB->count_records('local_compalign_evidence'));
    }

    /**
     * One bad suggestion rejects the whole answer, so nothing partial is shown.
     */
    public function test_nothing_partial_is_stored(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $answer = static function ($request): Response {
            $answer = service_stub::analysis(json_decode((string) $request->getBody(), true));
            $good = $answer['suggestions'][0];
            $bad = $good;
            $bad['competency_idnumber'] = 'T2';
            $bad['evidence'][0]['quote'] = 'Words that were never written here.';
            $answer['suggestions'] = [$good, $bad];
            return service_stub::json(200, $answer);
        };
        $manager = $this->create_manager([$answer]);

        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);
        $manager->run((int) $requested['analysis']->id);

        $this->assertSame(analysis_manager::STATUS_FAILED, $DB->get_field('local_compalign_analysis', 'status', [
            'id' => $requested['analysis']->id,
        ]));
        $this->assertSame(0, $DB->count_records('local_compalign_sugg'), 'The good suggestion is not kept either.');
    }

    /**
     * An analysis that is not waiting is left alone.
     */
    public function test_only_a_queued_analysis_is_run(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $transports = [];
        $manager = new analysis_manager(function () use (&$transports) {
            return service_stub::client([], $transports[]);
        });

        $manager->run((int) $made['analysis']->id);
        $manager->run(999999);

        $this->assertSame(analysis_manager::STATUS_COMPLETED, $manager->get_latest((int) $environment['cm']->id)->status);
        foreach ($transports as $transport) {
            $this->assertSame([], $transport->requests);
        }
    }

    /**
     * A framework that became unusable after the request fails the run with its own code.
     */
    public function test_a_framework_that_became_unusable_fails_the_run(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $manager = $this->create_manager();
        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);

        $environment['framework']->set('visible', 0);
        $environment['framework']->update();
        $manager->run((int) $requested['analysis']->id);

        $this->assertSame('framework_hidden', $DB->get_field('local_compalign_analysis', 'errorcode', [
            'id' => $requested['analysis']->id,
        ]));
    }

    /**
     * A request that cannot possibly work is refused at once, with the reason.
     */
    public function test_requests_that_cannot_work_are_refused(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $userid = (int) $environment['teacher']->id;
        $choice = $this->getDataGenerator()->create_module('choice', ['course' => $environment['course']->id]);
        $choicecm = get_fast_modinfo($environment['course'])->get_cm((int) $choice->cmid);

        // The plugin has no service address or token yet.
        $cases = [
            'service not configured' => [new analysis_manager(), $environment['cm'], 'notconfigured_url'],
            'resource type not supported' => [$this->create_manager(), $choicecm, 'unsupported_resource_type'],
        ];
        foreach ($cases as $label => [$manager, $cm, $code]) {
            try {
                $manager->request_analysis($cm, $userid);
                $this->fail("$label was accepted.");
            } catch (analysis_exception $exception) {
                $this->assertSame($code, $exception->get_error_code(), $label);
            }
        }

        set_config('frameworkid', 0, 'local_compalign');
        try {
            $this->create_manager()->request_analysis($environment['cm'], $userid);
            $this->fail('A request was accepted without a framework.');
        } catch (analysis_exception $exception) {
            $this->assertSame('framework_not_selected', $exception->get_error_code());
        }
    }

    /**
     * An analysis is flagged when the Page or the framework has changed since it was made.
     */
    public function test_find_changes(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $manager = $this->create_manager();
        $cm = $environment['cm'];

        $this->assertSame([], $manager->find_changes($made['analysis'], $cm, $made['catalogue']));

        $DB->set_field('competency', 'description', 'Something else.', ['id' => $environment['competencies']['T2']->get('id')]);
        $changed = (new competency_catalogue((int) $made['analysis']->frameworkid))->build();
        $this->assertSame([analysis_manager::CHANGE_FRAMEWORK], $manager->find_changes($made['analysis'], $cm, $changed));

        $DB->set_field('page', 'content', '<p>Another page.</p>', ['id' => $environment['page']->id]);
        $this->assertSame(
            [analysis_manager::CHANGE_PAGE, analysis_manager::CHANGE_FRAMEWORK],
            $manager->find_changes($made['analysis'], $cm, $changed)
        );

        $generator = $this->getDataGenerator()->get_plugin_generator('core_competency');
        $other = $generator->create_framework(['idnumber' => 'OTHER']);
        set_config('frameworkid', $other->get('id'), 'local_compalign');
        $this->assertContains(
            analysis_manager::CHANGE_FRAMEWORK,
            $manager->find_changes($made['analysis'], $cm, null),
            'Selecting another framework makes the earlier analysis out of date.'
        );
    }

    /**
     * The number of suggestions asked for stays inside the supported range.
     */
    public function test_configured_max_suggestions(): void {
        $this->resetAfterTest();

        foreach ([[null, 3], [0, 3], [-2, 3], [1, 1], [5, 5], [10, 10], [50, 10]] as [$configured, $expected]) {
            set_config('maxsuggestions', $configured, 'local_compalign');
            $this->assertSame($expected, analysis_manager::configured_max_suggestions(), (string) $configured);
        }
    }

    /**
     * A quiz quotation is taken from the question name plus the stem.
     *
     * The engine fragments a quiz question from search_text. Checking the quote
     * against the stem alone rejects that quotation.
     */
    public function test_quiz_quote_is_checked_against_the_search_text(): void {
        $stem = 'Transactions protect groups of related operations.';
        $resource = [
            'resource_type' => 'quiz_question',
            'resource_id' => 'moodle:quiz:1:question:2',
            'title' => 'Explain a transaction',
            'text' => $stem,
            'search_text' => resource_extractor::combine_text('Explain a transaction', $stem),
        ];
        $quote = 'Explain a transaction Transactions protect groups of related operations.';

        $this->assertSame($resource['search_text'], analysis_manager::quoted_text($resource));
        $this->assertSame($stem, analysis_manager::quoted_text([
            'resource_type' => 'page',
            'text' => $stem,
            'search_text' => $resource['search_text'],
        ]));

        $response = [
            'schema_version' => '1.0',
            'analysis_id' => 'quiz-1',
            'status' => 'completed',
            'resource_id' => 'moodle:quiz:1:question:2',
            'manifest' => [
                'backend' => 'mock',
                'model' => 'mock-deterministic-1',
                'prompt_version' => '1.0',
                'top_k' => 5,
                'max_selections_per_fragment' => 3,
                'competency_catalogue_hash' => 'sha256:' . str_repeat('0', 64),
                'resource_hash' => 'sha256:' . str_repeat('1', 64),
                'fragment_count' => 1,
                'completeness' => 'complete',
                'analysed_at' => '2026-10-04T22:00:00Z',
                'duration_ms' => 4,
            ],
            'suggestions' => [[
                'competency_idnumber' => 'T1',
                'confidence' => 0.8,
                'bm25_rank' => 1,
                'support_count' => 1,
                'evidence' => [[
                    'fragment_id' => 'moodle:quiz:1:question:2#f001',
                    'quote' => $quote,
                ]],
                'warnings' => [],
            ]],
            'abstained' => false,
            'diagnostics' => [],
        ];

        $validated = response_validator::validate(
            $response,
            $resource['resource_id'],
            ['T1'],
            5,
            3,
            analysis_manager::quoted_text($resource)
        );
        $this->assertSame($quote, $validated['suggestions'][0]['evidence'][0]['quote']);
    }

    /**
     * The background task carries the analysis and the teacher who asked.
     */
    public function test_the_task_carries_the_analysis_and_the_user(): void {
        $this->resetAfterTest();

        $task = analyse_resource::instance(42, 7);

        $this->assertSame(7, (int) $task->get_userid());
        $this->assertEquals(42, $task->get_custom_data()->analysisid);
        $this->assertFalse($task->retry_until_success(), 'A failed analysis is recorded, not retried blindly.');
        $this->assertNotEmpty($task->get_name());
    }
}
