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

use GuzzleHttp\Exception\RequestException;
use GuzzleHttp\Promise\Create;
use Psr\Http\Message\RequestInterface;
use Psr\Http\Message\ResponseInterface;

/**
 * A stand-in for the network, used as the handler of \core\http_client.
 *
 * It behaves like Guzzle's real handlers: the on_headers callback only ever sees a real response, and
 * an exception becomes a rejected promise. Each queued item is a response, an exception, or a callable
 * that receives the request and returns one of those. Every request that reaches it is recorded.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class fake_transport {
    /** @var array[] The requests seen: method, path, authorization, requestid, body and options. */
    public array $requests = [];

    /** @var array The answers still to give, in order. */
    private array $queue;

    /**
     * Constructor.
     *
     * @param array $queue Responses, exceptions or callables, in the order they will be used.
     */
    public function __construct(array $queue) {
        $this->queue = $queue;
    }

    /**
     * Answer one request.
     *
     * @param RequestInterface $request The request.
     * @param array $options The request options.
     * @return \GuzzleHttp\Promise\PromiseInterface
     */
    public function __invoke(RequestInterface $request, array $options) {
        $this->requests[] = [
            'method' => $request->getMethod(),
            'path' => $request->getUri()->getPath(),
            'authorization' => $request->getHeaderLine('Authorization'),
            'requestid' => $request->getHeaderLine('X-Request-ID'),
            'body' => (string) $request->getBody(),
            'options' => $options,
        ];

        $item = array_shift($this->queue);
        if (is_callable($item)) {
            $item = $item($request, $options);
        }

        if ($item instanceof \Throwable) {
            return Create::rejectionFor($item);
        }

        if (!$item instanceof ResponseInterface) {
            throw new \LogicException('The fake transport has nothing left to answer with.');
        }

        if (isset($options['on_headers'])) {
            try {
                $options['on_headers']($item);
            } catch (\Exception $exception) {
                return Create::rejectionFor(new RequestException(
                    'An error was encountered during the on_headers event',
                    $request,
                    $item,
                    $exception
                ));
            }
        }

        return Create::promiseFor($item);
    }
}
