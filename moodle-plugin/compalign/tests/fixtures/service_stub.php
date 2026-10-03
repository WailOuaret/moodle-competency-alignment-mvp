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

namespace local_compalign\fixtures;

use GuzzleHttp\Psr7\Response;
use local_compalign\service\alignment_client;

/**
 * Canned answers of the alignment service, and a client wired to a fake network.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class service_stub {
    /** @var string Token given to every client built here. */
    public const TOKEN = 'unit-test-token-0123456789abcdef';

    /**
     * A client whose requests go to a fake network.
     *
     * @param array $queue The answers the fake network will give.
     * @param fake_transport|null $transport Receives the fake network, so a test can inspect the requests.
     * @return alignment_client
     */
    public static function client(array $queue, ?fake_transport &$transport = null): alignment_client {
        // The site's HTTP security checks run before the fake network. Tests that use a client open them.
        set_config('curlsecurityblockedhosts', '');
        set_config('curlsecurityallowedport', '');

        $transport = new fake_transport($queue);

        return new alignment_client(
            'http://service.test:8001',
            self::TOKEN,
            30,
            new \core\http_client(['mock' => $transport])
        );
    }

    /**
     * The answer of GET /health.
     *
     * @return Response
     */
    public static function health(): Response {
        return self::json(200, [
            'status' => 'ok',
            'service' => alignment_client::SERVICE_NAME,
            'api_version' => alignment_client::API_VERSION,
        ]);
    }

    /**
     * A JSON answer.
     *
     * @param int $status HTTP status.
     * @param array $body The body.
     * @return Response
     */
    public static function json(int $status, array $body): Response {
        return new Response($status, ['Content-Type' => 'application/json'], json_encode($body));
    }

    /**
     * An error answer in the service's envelope.
     *
     * @param int $status HTTP status.
     * @param string $code The error code.
     * @return Response
     */
    public static function error(int $status, string $code): Response {
        return self::json($status, [
            'schema_version' => alignment_client::SCHEMA_VERSION,
            'error' => ['code' => $code, 'message' => 'x', 'retryable' => false, 'request_id' => 'r', 'details' => []],
        ]);
    }

    /**
     * A valid analysis answer for a request: the first competency, quoted from the first sentence.
     *
     * @param array $request The decoded request body.
     * @param array $override Values that replace the ones built here, merged at the top level.
     * @return array
     */
    public static function analysis(array $request, array $override = []): array {
        $resource = $request['resource'];
        $sentences = preg_split('/(?<=[.!?])\s+/', trim($resource['text']), 2);

        $answer = [
            'schema_version' => alignment_client::SCHEMA_VERSION,
            'analysis_id' => 'stub-0001',
            'status' => 'completed',
            'resource_id' => $resource['resource_id'],
            'manifest' => [
                'backend' => 'mock',
                'model' => 'stub-1',
                'prompt_version' => '1.0',
                'top_k' => $request['config']['top_k'],
                'max_selections_per_fragment' => 3,
                'competency_catalogue_hash' => 'sha256:' . str_repeat('0', 64),
                'resource_hash' => 'sha256:' . str_repeat('1', 64),
                'fragment_count' => 1,
                'completeness' => 'complete',
                'analysed_at' => '2026-10-03T22:00:00Z',
                'duration_ms' => 5,
            ],
            'suggestions' => [[
                'competency_idnumber' => $request['competencies'][0]['idnumber'],
                'confidence' => 0.8,
                'bm25_rank' => 1,
                'support_count' => 1,
                'evidence' => [['fragment_id' => $resource['resource_id'] . '#f001', 'quote' => $sentences[0]]],
                'warnings' => [],
            ]],
            'abstained' => false,
            'diagnostics' => [],
        ];

        return array_replace($answer, $override);
    }

    /**
     * A queue item that answers an analysis request with a valid answer built from that request.
     *
     * @param array $override Values that replace the ones of the answer, merged at the top level.
     * @return \Closure
     */
    public static function answer_analysis(array $override = []): \Closure {
        return static fn($request): Response => self::json(
            200,
            self::analysis(json_decode((string) $request->getBody(), true), $override)
        );
    }
}
