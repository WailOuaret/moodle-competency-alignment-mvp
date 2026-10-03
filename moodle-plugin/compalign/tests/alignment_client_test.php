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
use GuzzleHttp\Exception\RequestException;
use GuzzleHttp\Psr7\Request;
use GuzzleHttp\Psr7\Response;
use local_compalign\fixtures\fake_transport;
use local_compalign\fixtures\service_stub;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/fixtures/fake_transport.php');
require_once(__DIR__ . '/fixtures/service_stub.php');

/**
 * Tests for the client of the alignment service.
 *
 * The network is replaced by a fake: no request leaves the test.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(alignment_client::class)]
#[CoversClass(connection_result::class)]
final class alignment_client_test extends advanced_testcase {
    /**
     * Service addresses, with whether they are acceptable.
     *
     * @return array<string, array>
     */
    public static function url_provider(): array {
        return [
            'not configured yet' => ['', true],
            'https on a public host' => ['https://align.example.org', true],
            'https with a path' => ['https://align.example.org/api', true],
            'http on localhost' => ['http://localhost:8001', true],
            'http on the docker host' => ['http://host.docker.internal:8001', true],
            'http on a private address' => ['http://192.168.1.20:8001', true],
            'http on a loopback address' => ['http://127.0.0.1:8001', true],
            'http on a public host' => ['http://example.org', false],
            'http on a public address' => ['http://8.8.8.8', false],
            'another scheme' => ['ftp://example.org', false],
            'not an address' => ['not a url', false],
            'credentials in the address' => ['https://user:pass@example.org', false],
            'a query string' => ['https://example.org/?token=1', false],
            'a fragment' => ['https://example.org/#top', false],
            'no host' => ['https://', false],
        ];
    }

    /**
     * Plain HTTP is only tolerated for hosts that are not on the public internet.
     *
     * @param string $url The address.
     * @param bool $acceptable Whether it is acceptable.
     */
    #[DataProvider('url_provider')]
    public function test_validate_service_url(string $url, bool $acceptable): void {
        $error = alignment_client::validate_service_url($url);

        $acceptable ? $this->assertNull($error) : $this->assertNotEmpty($error);
    }

    /**
     * The request timeout has to be a whole number of seconds inside the supported range.
     */
    public function test_validate_timeout(): void {
        foreach (['5', '60', '900'] as $value) {
            $this->assertNull(alignment_client::validate_timeout($value), $value);
        }

        foreach (['4', '901', 'abc', '', '60.5', '-5'] as $value) {
            $this->assertNotEmpty(alignment_client::validate_timeout($value), $value);
        }
    }

    /**
     * What the connection check says for each way the service can answer.
     *
     * @return array<string, array>
     */
    public static function connection_provider(): array {
        $other = static fn(string $service, string $version = '1'): Response => service_stub::json(
            200,
            ['status' => 'ok', 'service' => $service, 'api_version' => $version]
        );
        $request = new Request('GET', 'http://service.test:8001/health');

        return [
            'health ok, token accepted' => [
                [service_stub::health(), service_stub::error(422, 'invalid_request')],
                alignment_client::STATUS_CONNECTED,
            ],
            'token refused' => [
                [service_stub::health(), service_stub::error(401, 'auth_invalid')],
                alignment_client::STATUS_UNAUTHORIZED,
            ],
            'no token accepted' => [
                [service_stub::health(), service_stub::error(401, 'auth_missing')],
                alignment_client::STATUS_UNAUTHORIZED,
            ],
            'service not configured' => [
                [service_stub::health(), service_stub::error(503, 'service_not_configured')],
                alignment_client::STATUS_UNAVAILABLE,
            ],
            'model error on the probe' => [
                [service_stub::health(), service_stub::error(502, 'model_output_invalid')],
                alignment_client::STATUS_UNAVAILABLE,
            ],
            'the probe is accepted as an analysis' => [
                [service_stub::health(), service_stub::json(200, ['status' => 'completed'])],
                alignment_client::STATUS_INVALIDRESPONSE,
            ],
            'the probe is refused for another reason' => [
                [service_stub::health(), service_stub::error(422, 'something_else')],
                alignment_client::STATUS_INVALIDRESPONSE,
            ],
            'the probe answer is not JSON' => [
                [service_stub::health(), new Response(422, [], '<html>no</html>')],
                alignment_client::STATUS_INVALIDRESPONSE,
            ],
            'wrong address' => [[new Response(404, [], 'Not Found')], alignment_client::STATUS_INVALIDRESPONSE],
            'server error' => [[new Response(500, [], 'boom')], alignment_client::STATUS_UNAVAILABLE],
            'proxy error' => [[new Response(503, [], '')], alignment_client::STATUS_UNAVAILABLE],
            'health is not JSON' => [[new Response(200, [], 'hello')], alignment_client::STATUS_INVALIDRESPONSE],
            'another service' => [[$other('something-else')], alignment_client::STATUS_INVALIDRESPONSE],
            'another api version' => [[$other('moodle-competency-alignment', '2')], alignment_client::STATUS_INVALIDRESPONSE],
            'redirects are refused' => [
                [new Response(301, ['Location' => 'http://elsewhere.test/'], '')],
                alignment_client::STATUS_INVALIDRESPONSE,
            ],
            'a body that is too large' => [
                [new Response(200, ['Content-Length' => '3145728'], '')],
                alignment_client::STATUS_UNAVAILABLE,
            ],
            'connection refused' => [
                [new ConnectException('cURL error 7: secret-detail', $request)],
                alignment_client::STATUS_UNAVAILABLE,
            ],
            'timeout' => [
                [new ConnectException('cURL error 28: timed out', $request)],
                alignment_client::STATUS_UNAVAILABLE,
            ],
            'blocked by the site' => [
                [static fn(): RequestException => new RequestException(get_string('curlsecurityurlblocked', 'admin'), $request)],
                alignment_client::STATUS_BLOCKED,
            ],
            'another failure without a response' => [
                [new RequestException('some other failure', $request)],
                alignment_client::STATUS_UNAVAILABLE,
            ],
            'the probe times out' => [
                [service_stub::health(), new ConnectException('timed out', $request)],
                alignment_client::STATUS_UNAVAILABLE,
            ],
        ];
    }

    /**
     * The connection check classifies every answer, and never throws.
     *
     * A string that needs the language packs is built by a closure, as data providers run before the test is set up.
     *
     * @param array $queue What the fake network answers.
     * @param string $expected The status.
     */
    #[DataProvider('connection_provider')]
    public function test_check_connection(array $queue, string $expected): void {
        $this->resetAfterTest();

        $result = service_stub::client($queue)->check_connection();

        $this->assertSame($expected, $result->status);
        $this->assertSame($expected === alignment_client::STATUS_CONNECTED, $result->is_connected());
    }

    /**
     * The check proves the token without analysing anything.
     */
    public function test_check_connection_wire_format(): void {
        $this->resetAfterTest();

        $client = service_stub::client([service_stub::health(), service_stub::error(422, 'invalid_request')], $transport);
        $client->check_connection();

        $this->assertCount(2, $transport->requests);
        [$health, $probe] = $transport->requests;

        $this->assertSame(['GET', '/health', ''], [$health['method'], $health['path'], $health['authorization']]);
        $this->assertSame(
            ['POST', '/v1/analyses', 'Bearer ' . service_stub::TOKEN, '{}'],
            [$probe['method'], $probe['path'], $probe['authorization'], $probe['body']]
        );
        $this->assertMatchesRegularExpression('/^compalign-[0-9a-f]{16}$/', $health['requestid']);
        $this->assertFalse($probe['options']['allow_redirects']);
        $this->assertLessThanOrEqual(5, $probe['options']['timeout'], 'The check never waits as long as an analysis may.');
    }

    /**
     * A good answer is returned as it was decoded, and the request carries the token and the id.
     */
    public function test_analyse_returns_the_answer(): void {
        $this->resetAfterTest();
        $request = ['schema_version' => '1.0', 'resource' => ['resource_id' => 'moodle:page:1', 'text' => 'Some text.']];
        $answer = ['schema_version' => '1.0', 'status' => 'completed'];

        $client = service_stub::client([service_stub::json(200, $answer)], $transport);
        $result = $client->analyse($request, 'compalign-0123456789abcdef');

        $this->assertSame($answer, $result);
        $sent = $transport->requests[0];
        $this->assertSame(['POST', '/v1/analyses'], [$sent['method'], $sent['path']]);
        $this->assertSame('Bearer ' . service_stub::TOKEN, $sent['authorization']);
        $this->assertSame('compalign-0123456789abcdef', $sent['requestid']);
        $this->assertSame($request, json_decode($sent['body'], true));
    }

    /**
     * The error code for each way an analysis request can fail.
     *
     * @return array<string, array>
     */
    public static function failure_provider(): array {
        $request = new Request('POST', 'http://service.test:8001/v1/analyses');

        return [
            'token refused' => [service_stub::error(401, 'auth_invalid'), 'unauthorized'],
            'request refused' => [service_stub::error(422, 'invalid_request'), 'service_invalid_request'],
            'rate limited' => [service_stub::error(429, 'rate_limited'), 'service_rate_limited'],
            'model output did not pass' => [service_stub::error(502, 'model_output_invalid'), 'model_output_invalid'],
            'model not available' => [service_stub::error(503, 'backend_unavailable'), 'backend_unavailable'],
            'server error' => [new Response(500, [], 'secret server detail'), 'unavailable'],
            'service not configured' => [service_stub::error(503, 'service_not_configured'), 'unavailable'],
            'unknown path' => [new Response(404, [], 'secret not found page'), 'invalid_response'],
            'answer that is not JSON' => [new Response(200, [], 'secret html'), 'invalid_response'],
            'connection refused' => [new ConnectException('cURL error 7: secret-detail', $request), 'unavailable'],
            'blocked by the site' => [
                static fn(): RequestException => new RequestException(get_string('curlsecurityurlblocked', 'admin'), $request),
                'blocked',
            ],
            'a body that is too large' => [new Response(200, ['Content-Length' => '3145728'], ''), 'unavailable'],
        ];
    }

    /**
     * Every failure becomes an exception with a stable code and a message that is safe to log.
     *
     * @param \Psr\Http\Message\ResponseInterface|\Throwable|\Closure $answer What the fake network gives.
     * @param string $expectedcode The error code.
     */
    #[DataProvider('failure_provider')]
    public function test_analyse_failures(mixed $answer, string $expectedcode): void {
        $this->resetAfterTest();

        try {
            service_stub::client([$answer])->analyse(['schema_version' => '1.0'], 'compalign-0123456789abcdef');
            $this->fail('The failure was not reported.');
        } catch (service_exception $exception) {
            $this->assertSame($expectedcode, $exception->get_error_code());
            foreach (['secret', service_stub::TOKEN, 'Bearer'] as $forbidden) {
                $this->assertStringNotContainsString($forbidden, $exception->getMessage());
            }
        }
    }

    /**
     * Without settings there is nothing to connect to, and the check says so instead of throwing.
     */
    public function test_an_unconfigured_plugin_cannot_connect(): void {
        $this->resetAfterTest();

        $this->assertSame(alignment_client::STATUS_NOTCONFIGURED, alignment_client::check_configured_connection()->status);

        foreach (['', 'http://example.org', 'not a url'] as $url) {
            set_config('serviceurl', $url, 'local_compalign');
            try {
                alignment_client::from_config();
                $this->fail("The address '$url' was used.");
            } catch (service_exception $exception) {
                $this->assertSame('notconfigured_url', $exception->get_error_code());
            }
        }

        set_config('serviceurl', 'https://align.example.org', 'local_compalign');
        try {
            alignment_client::from_config();
            $this->fail('A client was built without a token.');
        } catch (service_exception $exception) {
            $this->assertSame('notconfigured_token', $exception->get_error_code());
        }
    }

    /**
     * The settings build a client, and the stored token is the encrypted one.
     */
    public function test_a_configured_plugin_builds_a_client(): void {
        $this->resetAfterTest();
        set_config('serviceurl', 'https://align.example.org', 'local_compalign');
        set_config('servicetoken', \core\encryption::encrypt(service_stub::TOKEN), 'local_compalign');
        set_config('requesttimeout', 60, 'local_compalign');

        $this->assertInstanceOf(alignment_client::class, alignment_client::from_config());
        $this->assertStringNotContainsString(service_stub::TOKEN, (string) get_config('local_compalign', 'servicetoken'));
    }
}
