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

use core\http_client;
use GuzzleHttp\ClientInterface;
use GuzzleHttp\Exception\GuzzleException;
use GuzzleHttp\Exception\RequestException;
use Psr\Http\Message\ResponseInterface;

/**
 * Transport client for the Python alignment service.
 *
 * It sends JSON over HTTP with the bearer token and decodes what comes back. It knows
 * nothing about how competencies are chosen: that happens in the service, which owns
 * every model credential. All requests go through Moodle's HTTP client, so the site's
 * HTTP security settings (blocked hosts and allowed ports) always apply. Redirects are
 * refused so the token is never forwarded to another host.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class alignment_client {
    /** The service answered and accepted the token. */
    public const STATUS_CONNECTED = 'connected';
    /** No answer, or a server error. */
    public const STATUS_UNAVAILABLE = 'unavailable';
    /** The service is reachable but rejected the token. */
    public const STATUS_UNAUTHORIZED = 'unauthorized';
    /** Something answered, but not the alignment service. */
    public const STATUS_INVALIDRESPONSE = 'invalidresponse';
    /** Moodle's HTTP security settings refused the address or port. */
    public const STATUS_BLOCKED = 'blocked';
    /** The URL or the token is missing or unusable. */
    public const STATUS_NOTCONFIGURED = 'notconfigured';

    /** Contract version this client speaks. */
    public const SCHEMA_VERSION = '1.0';
    /** API version reported by the service health endpoint. */
    public const API_VERSION = '1';
    /** Service name reported by the service health endpoint. */
    public const SERVICE_NAME = 'moodle-competency-alignment';
    /** The only Top-K the prototype may request: the evaluated research configuration. */
    public const SUPPORTED_TOP_K = 5;

    /** Smallest accepted request timeout, in seconds. */
    public const MIN_TIMEOUT = 5;
    /** Largest accepted request timeout, in seconds. */
    public const MAX_TIMEOUT = 900;
    /** Request timeout used when none is configured, in seconds. */
    public const DEFAULT_TIMEOUT = 120;

    /** Seconds allowed for the connection check, however long analyses may take. */
    private const CHECK_TIMEOUT = 5;
    /** Seconds allowed to open a connection. */
    private const CONNECT_TIMEOUT = 5;
    /** Largest response body the client accepts. */
    private const MAX_RESPONSE_BYTES = 2097152;

    /** @var string Base URL without a trailing slash. */
    private string $baseurl;

    /** @var string Bearer token. Never logged, rendered or put in an exception message. */
    private string $token;

    /** @var int Seconds to wait for an analysis. */
    private int $timeout;

    /** @var ClientInterface HTTP client. */
    private ClientInterface $http;

    /**
     * Constructor.
     *
     * @param string $baseurl Base URL of the service.
     * @param string $token Bearer token.
     * @param int $timeout Seconds to wait for an analysis.
     * @param ClientInterface|null $http HTTP client. Defaults to Moodle's, which enforces the site HTTP security settings.
     */
    public function __construct(
        string $baseurl,
        #[\SensitiveParameter] string $token,
        int $timeout = self::DEFAULT_TIMEOUT,
        ?ClientInterface $http = null,
    ) {
        $this->baseurl = rtrim(trim($baseurl), '/');
        $this->token = $token;
        $this->timeout = max(self::MIN_TIMEOUT, min(self::MAX_TIMEOUT, $timeout));
        $this->http = $http ?? new http_client();
    }

    /**
     * Build a client from the plugin settings.
     *
     * @return self
     * @throws service_exception When the URL or the token is missing or unusable.
     */
    public static function from_config(): self {
        $url = trim((string) get_config('local_compalign', 'serviceurl'));
        if ($url === '' || self::validate_service_url($url) !== null) {
            throw new service_exception('notconfigured_url', 'The service URL is missing or not valid.');
        }

        $stored = (string) get_config('local_compalign', 'servicetoken');
        if ($stored === '') {
            throw new service_exception('notconfigured_token', 'The service token is not set.');
        }

        try {
            $token = \core\encryption::decrypt($stored);
        } catch (\moodle_exception) {
            // Wrong key or damaged value. The exception is not passed on, as it may describe the value.
            throw new service_exception('notconfigured_token', 'The service token cannot be read.');
        }

        $timeout = (int) get_config('local_compalign', 'requesttimeout');

        return new self($url, $token, $timeout > 0 ? $timeout : self::DEFAULT_TIMEOUT);
    }

    /**
     * Check the connection using the plugin settings.
     *
     * A missing or unusable setting is reported as a status, not thrown, so callers can
     * show it to the administrator.
     *
     * @return connection_result
     */
    public static function check_configured_connection(): connection_result {
        try {
            return self::from_config()->check_connection();
        } catch (service_exception $exception) {
            return new connection_result(self::STATUS_NOTCONFIGURED, null, $exception->get_error_code());
        }
    }

    /**
     * Validate the service URL setting.
     *
     * An empty value is allowed, meaning not configured. Plain HTTP is accepted only
     * for hosts that are not on the public internet; anything else needs HTTPS.
     *
     * @param string $url The URL.
     * @return string|null Localised error, or null when the URL is acceptable.
     */
    public static function validate_service_url(string $url): ?string {
        $url = trim($url);
        if ($url === '') {
            return null;
        }

        $parts = parse_url($url);
        $scheme = strtolower((string) ($parts['scheme'] ?? ''));
        $malformed = $parts === false
            || !in_array($scheme, ['http', 'https'], true)
            || empty($parts['host'])
            || isset($parts['user'])
            || isset($parts['pass'])
            || isset($parts['query'])
            || isset($parts['fragment']);
        if ($malformed) {
            return get_string('serviceurl_invalid', 'local_compalign');
        }

        if ($scheme === 'http' && !self::is_local_development_host($parts['host'])) {
            return get_string('serviceurl_httpsrequired', 'local_compalign');
        }

        return null;
    }

    /**
     * Validate the request timeout setting.
     *
     * @param string $value The value in seconds.
     * @return string|null Localised error, or null when the value is acceptable.
     */
    public static function validate_timeout(string $value): ?string {
        $seconds = filter_var($value, FILTER_VALIDATE_INT);
        if ($seconds !== false && $seconds >= self::MIN_TIMEOUT && $seconds <= self::MAX_TIMEOUT) {
            return null;
        }

        return get_string('requesttimeout_invalid', 'local_compalign', (object) [
            'min' => self::MIN_TIMEOUT,
            'max' => self::MAX_TIMEOUT,
        ]);
    }

    /**
     * Check that the service is reachable and accepts the token.
     *
     * The service health endpoint needs no credentials, so it only proves reachability.
     * To prove the token, an empty analysis request is sent. The service checks the
     * token before it reads the body: a wrong token gets HTTP 401, and a right one gets
     * HTTP 422 because the body is empty. Nothing is analysed, no model is called and
     * nothing is stored.
     *
     * @return connection_result
     */
    public function check_connection(): connection_result {
        try {
            $health = $this->send('GET', '/health', false, self::CHECK_TIMEOUT);
        } catch (GuzzleException | \RuntimeException $exception) {
            return $this->classify_failure($exception);
        }

        $code = $health->getStatusCode();
        if ($code >= 500) {
            return new connection_result(self::STATUS_UNAVAILABLE, $code);
        }

        $body = $this->decode($health);
        $isservice = $code === 200
            && is_array($body)
            && ($body['status'] ?? null) === 'ok'
            && ($body['service'] ?? null) === self::SERVICE_NAME
            && ($body['api_version'] ?? null) === self::API_VERSION;
        if (!$isservice) {
            return new connection_result(self::STATUS_INVALIDRESPONSE, $code);
        }

        try {
            $probe = $this->send('POST', '/v1/analyses', true, self::CHECK_TIMEOUT, new \stdClass());
        } catch (GuzzleException | \RuntimeException $exception) {
            return $this->classify_failure($exception);
        }

        return $this->interpret_probe($probe);
    }

    /**
     * Ask the service to analyse one resource against one competency catalogue.
     *
     * Only the decoded answer is returned. It is untrusted: the caller validates it before
     * anything is stored. Every failure becomes a service_exception with a stable code and a
     * message that is safe to log: no token, header or response body is ever included.
     *
     * @param array $request The request body, following contract version 1.0.
     * @param string $requestid Correlation id, sent as X-Request-ID so the service log can be matched.
     * @return array The decoded answer.
     * @throws service_exception When the service cannot be reached or does not answer with an analysis.
     */
    public function analyse(array $request, string $requestid): array {
        try {
            $response = $this->send('POST', '/v1/analyses', true, null, $request, $requestid);
        } catch (GuzzleException | \RuntimeException $exception) {
            $failure = $this->classify_failure($exception);
            throw new service_exception($failure->status, 'The alignment service could not be reached.', $exception);
        }

        $code = $response->getStatusCode();
        $body = $this->decode($response);

        if ($code === 200 && is_array($body)) {
            return $body;
        }

        $errorcode = $body['error']['code'] ?? null;
        $errorcode = is_string($errorcode) && preg_match('/^[a-z][a-z0-9_]{0,59}$/', $errorcode) ? $errorcode : null;

        throw match (true) {
            $code === 401 => new service_exception(self::STATUS_UNAUTHORIZED, 'The service rejected the token.'),
            $errorcode === 'model_output_invalid' => new service_exception($errorcode, 'No model response passed validation.'),
            $errorcode === 'backend_unavailable' => new service_exception($errorcode, 'The model backend is not available.'),
            $code >= 500 => new service_exception(self::STATUS_UNAVAILABLE, "The service answered HTTP $code."),
            $code >= 400 && $errorcode !== null => new service_exception(
                'service_' . $errorcode,
                "The service refused the request: $errorcode."
            ),
            default => new service_exception('invalid_response', "The service answered HTTP $code."),
        };
    }

    /**
     * Ask the service to turn one teacher file into plain text.
     *
     * The bytes are not logged. A parser failure becomes a stable error code.
     *
     * @param string $bytes File contents.
     * @param string $format pdf, docx, pptx, text, markdown, vtt or srt.
     * @param string $filename Original file name, sent only as the upload name.
     * @param string $requestid Correlation id.
     * @return array{text: string, segments: array}
     * @throws service_exception When extraction fails.
     */
    public function extract_document(string $bytes, string $format, string $filename, string $requestid): array {
        try {
            $response = $this->http->request('POST', $this->baseurl . '/v1/extractions', [
                'headers' => [
                    'Accept' => 'application/json',
                    'Authorization' => 'Bearer ' . $this->token,
                    'X-Request-ID' => $requestid,
                ],
                'multipart' => [
                    ['name' => 'declared_format', 'contents' => $format],
                    ['name' => 'upload', 'contents' => $bytes, 'filename' => $filename],
                ],
                'http_errors' => false,
                'allow_redirects' => false,
                'timeout' => $this->timeout,
                'connect_timeout' => min(self::CONNECT_TIMEOUT, $this->timeout),
            ]);
        } catch (GuzzleException | \RuntimeException $exception) {
            $failure = $this->classify_failure($exception);
            throw new service_exception($failure->status, 'The alignment service could not be reached.', $exception);
        }

        $body = $this->decode($response);
        if ($response->getStatusCode() === 200 && is_array($body) && is_string($body['text'] ?? null) && $body['text'] !== '') {
            return [
                'text' => $body['text'],
                'segments' => is_array($body['segments'] ?? null) ? $body['segments'] : [],
            ];
        }

        $errorcode = $body['error']['code'] ?? 'document_malformed';
        $errorcode = is_string($errorcode) && preg_match('/^[a-z][a-z0-9_]{0,59}$/', $errorcode) ? $errorcode : 'document_malformed';
        throw new service_exception($errorcode, 'The document could not be read.');
    }

    /**
     * Turn the answer to the credentials probe into a connection result.
     *
     * @param ResponseInterface $probe The answer to the empty analysis request.
     * @return connection_result
     */
    private function interpret_probe(ResponseInterface $probe): connection_result {
        $code = $probe->getStatusCode();
        $errorcode = $this->decode($probe)['error']['code'] ?? null;

        if ($code === 401) {
            return new connection_result(self::STATUS_UNAUTHORIZED, $code, is_string($errorcode) ? $errorcode : null);
        }

        if ($code === 503 && $errorcode === 'service_not_configured') {
            return new connection_result(self::STATUS_UNAVAILABLE, $code, 'service_not_configured');
        }

        if ($code === 422 && $errorcode === 'invalid_request') {
            return new connection_result(self::STATUS_CONNECTED, $code);
        }

        $status = $code >= 500 ? self::STATUS_UNAVAILABLE : self::STATUS_INVALIDRESPONSE;

        return new connection_result($status, $code);
    }

    /**
     * Send one request to the service.
     *
     * @param string $method HTTP method.
     * @param string $path Path below the base URL.
     * @param bool $authenticated Whether to send the bearer token.
     * @param int|null $timeout Seconds to wait. Defaults to the configured timeout.
     * @param mixed $json Value to send as the JSON body, or null for no body.
     * @param string|null $requestid Correlation id. A random one is used when omitted.
     * @return ResponseInterface
     * @throws GuzzleException When the request cannot be completed.
     */
    private function send(
        string $method,
        string $path,
        bool $authenticated,
        ?int $timeout = null,
        mixed $json = null,
        ?string $requestid = null,
    ): ResponseInterface {
        $timeout ??= $this->timeout;
        $headers = [
            'Accept' => 'application/json',
            'X-Request-ID' => $requestid ?? 'compalign-' . bin2hex(random_bytes(8)),
        ];
        if ($authenticated) {
            $headers['Authorization'] = 'Bearer ' . $this->token;
        }

        $options = [
            'headers' => $headers,
            'http_errors' => false,
            'allow_redirects' => false,
            'timeout' => $timeout,
            'connect_timeout' => min(self::CONNECT_TIMEOUT, $timeout),
            'on_headers' => static function (ResponseInterface $response): void {
                if ((int) $response->getHeaderLine('Content-Length') > self::MAX_RESPONSE_BYTES) {
                    throw new \RuntimeException('The response is too large.');
                }
            },
        ];
        if ($json !== null) {
            $options['json'] = $json;
        }

        return $this->http->request($method, $this->baseurl . $path, $options);
    }

    /**
     * Decode a JSON object response.
     *
     * @param ResponseInterface $response The response.
     * @return array|null The decoded object, or null if the body is not a JSON object.
     */
    private function decode(ResponseInterface $response): ?array {
        $body = (string) $response->getBody();
        if ($body === '' || strlen($body) > self::MAX_RESPONSE_BYTES) {
            return null;
        }

        try {
            $data = json_decode($body, true, 32, JSON_THROW_ON_ERROR);
        } catch (\JsonException) {
            return null;
        }

        return is_array($data) ? $data : null;
    }

    /**
     * Classify a transport failure without exposing its message.
     *
     * @param \Throwable $exception What went wrong.
     * @return connection_result
     */
    private function classify_failure(\Throwable $exception): connection_result {
        $blocked = $exception instanceof RequestException
            && !$exception->hasResponse()
            && $exception->getMessage() === get_string('curlsecurityurlblocked', 'admin');

        return new connection_result($blocked ? self::STATUS_BLOCKED : self::STATUS_UNAVAILABLE);
    }

    /**
     * Whether a host is meant for local development, so plain HTTP is tolerable.
     *
     * @param string $host Host name or IP address from the URL.
     * @return bool
     */
    private static function is_local_development_host(string $host): bool {
        $host = strtolower(trim($host, '[]'));
        if (in_array($host, ['localhost', 'host.docker.internal'], true)) {
            return true;
        }

        if (filter_var($host, FILTER_VALIDATE_IP) === false) {
            return false;
        }

        // Private, loopback and link-local addresses are not reachable from the internet.
        return filter_var($host, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false;
    }
}
