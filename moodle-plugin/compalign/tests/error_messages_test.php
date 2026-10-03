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
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

/**
 * Tests for the sentences a teacher sees when something goes wrong.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(error_messages::class)]
final class error_messages_test extends advanced_testcase {
    /**
     * Every code the plugin stores on a failed analysis.
     *
     * @return array<string, array{string}>
     */
    public static function code_provider(): array {
        $codes = [
            'notconfigured_url', 'notconfigured_token', 'competencies_disabled', 'framework_not_selected',
            'framework_unavailable', 'framework_hidden', 'framework_empty', 'framework_invalid',
            'unsupported_resource_type', 'resource_not_accessible', 'resource_missing', 'resource_empty',
            'resource_too_large', 'busy', 'unavailable', 'unauthorized', 'blocked', 'invalid_response',
            'model_output_invalid', 'backend_unavailable', 'internal_error', 'invalid_review',
        ];

        return array_combine($codes, array_map(static fn(string $code): array => [$code], $codes));
    }

    /**
     * Every stored code has a sentence of its own, not the generic one.
     *
     * @param string $code The error code.
     */
    #[DataProvider('code_provider')]
    public function test_every_code_has_its_own_sentence(string $code): void {
        $generic = get_string('error_generic', 'local_compalign');
        $sentence = error_messages::for_code($code);

        $this->assertNotSame('', $sentence);
        $this->assertNotSame($generic, $sentence, $code);
    }

    /**
     * A code the service sent is shown as a fixed word, and anything else is the generic sentence.
     */
    public function test_codes_from_the_service_and_unknown_codes(): void {
        $generic = get_string('error_generic', 'local_compalign');

        $this->assertStringContainsString('invalid_request', error_messages::for_code('service_invalid_request'));
        $this->assertSame($generic, error_messages::for_code(null));
        $this->assertSame($generic, error_messages::for_code(''));
        $this->assertSame($generic, error_messages::for_code('something_new'));
        $this->assertSame($generic, error_messages::for_code('service_<script>alert(1)</script>'));
        $this->assertStringNotContainsString('<', error_messages::for_code('service_<script>'));
    }
}
