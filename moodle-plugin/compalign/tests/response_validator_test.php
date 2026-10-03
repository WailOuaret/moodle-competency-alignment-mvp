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
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

/**
 * Tests for the validation of the alignment service's answer.
 *
 * The answer is untrusted input: whatever fails here is never stored or shown.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(response_validator::class)]
final class response_validator_test extends advanced_testcase {
    /** @var string The resource id Moodle sent. */
    private const RESOURCE_ID = 'moodle:page:7';

    /** @var string The text Moodle sent. */
    private const TEXT = 'Unit tests check one function at a time. Integration tests check how parts work together.';

    /** @var string[] The competencies Moodle sent. */
    private const IDNUMBERS = ['T1', 'T1_1', 'T2'];

    /**
     * An answer that passes every check.
     *
     * @return array
     */
    private static function valid(): array {
        return [
            'schema_version' => '1.0',
            'analysis_id' => 'abc-123',
            'status' => 'completed',
            'resource_id' => self::RESOURCE_ID,
            'manifest' => [
                'backend' => 'mock',
                'model' => 'mock-deterministic-1',
                'prompt_version' => '1.0',
                'top_k' => 5,
                'max_selections_per_fragment' => 3,
                'competency_catalogue_hash' => 'sha256:' . str_repeat('0', 64),
                'resource_hash' => 'sha256:' . str_repeat('1', 64),
                'fragment_count' => 2,
                'completeness' => 'complete',
                'analysed_at' => '2026-10-03T22:00:00Z',
                'duration_ms' => 12,
            ],
            'suggestions' => [self::suggestion('T1', 'Unit tests check one function at a time.')],
            'abstained' => false,
            'diagnostics' => [],
        ];
    }

    /**
     * A suggestion that passes every check.
     *
     * @param string $idnumber The competency.
     * @param string $quote The quotation.
     * @return array
     */
    private static function suggestion(string $idnumber, string $quote): array {
        return [
            'competency_idnumber' => $idnumber,
            'confidence' => 0.8,
            'bm25_rank' => 1,
            'support_count' => 1,
            'evidence' => [['fragment_id' => 'moodle:page:7#f001', 'quote' => $quote]],
            'warnings' => [],
        ];
    }

    /**
     * A change that sets the value at a dotted path, for example manifest.top_k or suggestions.0.confidence.
     *
     * @param string $path The path.
     * @param mixed $value The new value.
     * @return \Closure
     */
    private static function with(string $path, mixed $value): \Closure {
        return static function (array $response) use ($path, $value): array {
            $node = &$response;
            foreach (explode('.', $path) as $key) {
                $node = &$node[$key];
            }
            $node = $value;

            return $response;
        };
    }

    /**
     * A change that removes the value at a dotted path.
     *
     * @param string $path The path.
     * @return \Closure
     */
    private static function without(string $path): \Closure {
        return static function (array $response) use ($path): array {
            $keys = explode('.', $path);
            $last = array_pop($keys);
            $node = &$response;
            foreach ($keys as $key) {
                $node = &$node[$key];
            }
            unset($node[$last]);

            return $response;
        };
    }

    /**
     * Validate with the values Moodle sent.
     *
     * @param array $response The answer.
     * @param int $maxsuggestions The most suggestions asked for.
     * @param string $text The text Moodle sent.
     * @return array
     */
    private function validate(array $response, int $maxsuggestions = 3, string $text = self::TEXT): array {
        return response_validator::validate($response, self::RESOURCE_ID, self::IDNUMBERS, 5, $maxsuggestions, $text);
    }

    /**
     * Answers that must be refused, with a word that the problem must contain.
     *
     * @return array<string, array>
     */
    public static function rejected_provider(): array {
        $warning = ['code' => 'parent_child_redundancy', 'role' => 'parent', 'related_idnumber' => 'T1_1', 'message' => 'Note.'];
        $four = ['suggestions' => [
            self::suggestion('T1', 'Unit tests check one function at a time.'),
            self::suggestion('T1_1', 'Unit tests check one function at a time.'),
            self::suggestion('T2', 'Unit tests check one function at a time.'),
            self::suggestion('T1', 'Unit tests check one function at a time.'),
        ]];

        return [
            'another schema version' => [self::with('schema_version', '2.0'), 'schema_version'],
            'no schema version' => [self::without('schema_version'), 'schema_version'],
            'analysis id with a space' => [self::with('analysis_id', 'a b'), 'analysis_id'],
            'no analysis id' => [self::without('analysis_id'), 'analysis_id'],
            'status other than completed' => [self::with('status', 'failed'), 'status'],
            'another resource' => [self::with('resource_id', 'moodle:page:8'), 'resource_id'],
            'abstained is not a boolean' => [self::with('abstained', 'no'), 'abstained is not a boolean'],
            'abstained although there are suggestions' => [self::with('abstained', true), 'abstained disagrees'],
            'not abstained although there are none' => [
                static fn(array $r): array => ['suggestions' => [], 'abstained' => false] + $r,
                'abstained disagrees',
            ],
            'no manifest' => [self::without('manifest'), 'manifest is missing'],
            'another Top-K than was requested' => [self::with('manifest.top_k', 3), 'Top-K that was requested'],
            'Top-K as text' => [self::with('manifest.top_k', '5'), 'manifest.top_k'],
            'completeness that is not known' => [self::with('manifest.completeness', 'done'), 'completeness'],
            'no backend' => [self::without('manifest.backend'), 'manifest.backend'],
            'suggestions are not a list' => [self::with('suggestions', ['first' => []]), 'not a list'],
            'more suggestions than were asked for' => [static fn(array $r): array => $four + $r, 'more suggestions'],
            'competency that was not sent' => [self::with('suggestions.0.competency_idnumber', 'ZZ'), 'not sent'],
            'competency repeated' => [
                static function (array $r): array {
                    $r['suggestions'][] = $r['suggestions'][0];
                    return $r;
                },
                'repeats',
            ],
            'confidence above one' => [self::with('suggestions.0.confidence', 1.5), 'confidence'],
            'confidence as text' => [self::with('suggestions.0.confidence', 'high'), 'confidence'],
            'rank beyond Top-K' => [self::with('suggestions.0.bm25_rank', 6), 'bm25_rank'],
            'rank of zero' => [self::with('suggestions.0.bm25_rank', 0), 'bm25_rank'],
            'support count of zero' => [self::with('suggestions.0.support_count', 0), 'support_count'],
            'no evidence' => [self::with('suggestions.0.evidence', []), 'evidence'],
            'quotation that is not in the text' => [
                self::with('suggestions.0.evidence.0.quote', 'Nothing like this was ever written.'),
                'exact quotation',
            ],
            'quotation with other capitals' => [
                self::with('suggestions.0.evidence.0.quote', 'unit tests check one function at a time.'),
                'exact quotation',
            ],
            'empty quotation' => [self::with('suggestions.0.evidence.0.quote', '  '), 'valid quote'],
            'no fragment id' => [self::without('suggestions.0.evidence.0.fragment_id'), 'fragment_id'],
            'too many quotations' => [
                self::with('suggestions.0.evidence', array_fill(
                    0,
                    21,
                    ['fragment_id' => 'f', 'quote' => 'Unit tests check one function at a time.']
                )),
                'one to 20',
            ],
            'warning about a competency that was not sent' => [
                self::with('suggestions.0.warnings', [['related_idnumber' => 'ZZ'] + $warning]),
                'malformed',
            ],
            'warning with an unknown role' => [
                self::with('suggestions.0.warnings', [['role' => 'sibling'] + $warning]),
                'malformed',
            ],
            'warning code in capitals' => [
                self::with('suggestions.0.warnings', [['code' => 'Parent'] + $warning]),
                'malformed',
            ],
            'warnings are not a list' => [self::with('suggestions.0.warnings', 'none'), 'warnings'],
            'diagnostics are not a list' => [self::with('diagnostics', 'none'), 'diagnostics'],
            'diagnostic without a message' => [self::with('diagnostics', [['code' => 'partial_run']]), 'malformed'],
        ];
    }

    /**
     * Anything wrong with the answer rejects all of it.
     *
     * @param \Closure $change Turns a valid answer into the one under test.
     * @param string $expected A word the problem must contain.
     */
    #[DataProvider('rejected_provider')]
    public function test_a_bad_answer_is_rejected(\Closure $change, string $expected): void {
        try {
            $this->validate($change(self::valid()));
            $this->fail('The answer was accepted.');
        } catch (analysis_exception $exception) {
            $this->assertSame('invalid_response', $exception->get_error_code());
            $this->assertStringContainsString($expected, implode(' | ', $exception->get_details()));
        }
    }

    /**
     * A valid answer is returned in the shape the manager stores.
     */
    public function test_a_valid_answer_is_accepted(): void {
        $validated = $this->validate(self::valid());

        $this->assertSame('abc-123', $validated['analysisid']);
        $this->assertSame('mock', $validated['backend']);
        $this->assertSame('complete', $validated['completeness']);
        $this->assertFalse($validated['abstained']);
        $this->assertSame(5, $validated['manifest']['top_k']);
        $this->assertCount(1, $validated['suggestions']);
        $this->assertSame('T1', $validated['suggestions'][0]['idnumber']);
        $this->assertSame(0.8, $validated['suggestions'][0]['confidence']);
        $this->assertSame('Unit tests check one function at a time.', $validated['suggestions'][0]['evidence'][0]['quote']);
    }

    /**
     * Ratings and ranks are optional, and the limits themselves are allowed.
     */
    public function test_optional_values_and_limits(): void {
        $response = self::valid();
        $response['suggestions'][0]['confidence'] = null;
        $response['suggestions'][0]['bm25_rank'] = null;
        $validated = $this->validate($response);
        $this->assertNull($validated['suggestions'][0]['confidence']);
        $this->assertNull($validated['suggestions'][0]['bm25rank']);

        foreach ([0, 1, 0.0, 1.0] as $confidence) {
            $response['suggestions'][0]['confidence'] = $confidence;
            $this->assertSame((float) $confidence, $this->validate($response)['suggestions'][0]['confidence']);
        }

        $response['suggestions'][0]['bm25_rank'] = 5;
        $this->assertSame(5, $this->validate($response)['suggestions'][0]['bm25rank']);
    }

    /**
     * A service that has nothing to suggest abstains.
     */
    public function test_abstaining_with_no_suggestions_is_accepted(): void {
        $response = ['suggestions' => [], 'abstained' => true] + self::valid();

        $validated = $this->validate($response);

        $this->assertTrue($validated['abstained']);
        $this->assertSame([], $validated['suggestions']);
    }

    /**
     * Several suggestions are accepted up to the number that was asked for.
     */
    public function test_several_suggestions_up_to_the_limit(): void {
        $response = self::valid();
        $response['suggestions'] = [
            self::suggestion('T1', 'Unit tests check one function at a time.'),
            self::suggestion('T1_1', 'Integration tests check how parts work together.'),
            self::suggestion('T2', 'Unit tests check one function at a time.'),
        ];

        $validated = $this->validate($response, 3);

        $this->assertSame(['T1', 'T1_1', 'T2'], array_column($validated['suggestions'], 'idnumber'));
    }

    /**
     * White space, HTML entities and compatibility characters do not make an exact quotation inexact.
     */
    public function test_quotations_are_compared_after_normalising(): void {
        $text = "Tom &amp; Jerry   test the  \u{FB01}rst release.\nDone.";
        $response = self::valid();

        $quotes = ['Tom & Jerry test the first release.', 'Tom &amp; Jerry test the first release.', "Jerry\ntest   the first"];
        foreach ($quotes as $quote) {
            $response['suggestions'][0]['evidence'][0]['quote'] = $quote;
            $this->assertSame($quote, $this->validate($response, 3, $text)['suggestions'][0]['evidence'][0]['quote']);
        }
    }

    /**
     * Hierarchy warnings are kept, with the related competency.
     */
    public function test_warnings_are_kept(): void {
        $response = self::valid();
        $response['suggestions'][0]['warnings'] = [[
            'code' => 'parent_child_redundancy',
            'role' => 'parent',
            'related_idnumber' => 'T1_1',
            'message' => 'A more specific child competency (T1_1) is also suggested for this resource.',
        ]];

        $warnings = $this->validate($response)['suggestions'][0]['warnings'];

        $this->assertCount(1, $warnings);
        $this->assertSame('parent_child_redundancy', $warnings[0]['code']);
        $this->assertSame('parent', $warnings[0]['role']);
        $this->assertSame('T1_1', $warnings[0]['related']);
    }

    /**
     * Fields the plugin does not know are dropped, so nothing unexpected is ever stored.
     */
    public function test_unknown_fields_are_dropped(): void {
        $response = self::valid();
        $response['debug_trace'] = 'Traceback (most recent call last)';
        $response['manifest']['internal_prompt'] = 'SECRET PROMPT';
        $response['suggestions'][0]['gold_label'] = 'T2';
        $response['suggestions'][0]['evidence'][0]['reference'] = 'secret';

        $encoded = json_encode($this->validate($response));

        foreach (['Traceback', 'SECRET', 'gold_label', 'reference'] as $forbidden) {
            $this->assertStringNotContainsString($forbidden, $encoded);
        }
    }

    /**
     * A problem names the field, never the value, and only a few are listed.
     */
    public function test_problems_do_not_repeat_the_offending_value_and_are_capped(): void {
        $secret = 'A sentence nobody wrote, with a secret in it.';
        $response = self::valid();
        $response['suggestions'] = [];
        for ($i = 0; $i < 12; $i++) {
            $response['suggestions'][] = self::suggestion('ZZ' . $i, $secret);
        }

        try {
            $this->validate($response, 20);
            $this->fail('The answer was accepted.');
        } catch (analysis_exception $exception) {
            $details = $exception->get_details();
            $this->assertLessThanOrEqual(10, count($details));
            $this->assertStringNotContainsString('secret', implode(' ', $details) . $exception->getMessage());
        }
    }

    /**
     * The normalisation used for the comparison is public and stable.
     */
    public function test_normalise_for_comparison(): void {
        $this->assertSame('a & b c', response_validator::normalise_for_comparison("  a &amp;\n b\u{00A0}c "));
        $this->assertSame('fi', response_validator::normalise_for_comparison("\u{FB01}"));
    }
}
