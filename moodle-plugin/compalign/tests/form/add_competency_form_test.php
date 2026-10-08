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


namespace local_compalign\form;

use advanced_testcase;
use local_compalign\service\catalogue_snapshot;
use PHPUnit\Framework\Attributes\CoversClass;

/**
 * Tests for the form that adds a competency the model did not propose.
 *
 * The form is rendered and submitted the way Moodle does it, so these tests see what a teacher's
 * browser would receive and what the server would accept.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(add_competency_form::class)]
final class add_competency_form_test extends advanced_testcase {
    /** @var string The fingerprint of the resource the form is built for. */
    private const HASH = 'resource-hash';

    /**
     * Build the form for one resource, in a framework with T1, T1_1 and T2.
     *
     * @return add_competency_form
     */
    private function make_form(): add_competency_form {
        $lookup = [];
        foreach ([['T1', 'Write software', ''], ['T1_1', 'Unit testing', 'T1'], ['T2', 'Deploy software', '']] as $i => $row) {
            [$idnumber, $shortname, $parent] = $row;
            $lookup[$idnumber] = ['id' => $i + 1, 'shortname' => $shortname, 'description' => '', 'parentidnumber' => $parent];
        }

        return new add_competency_form(new \moodle_url('/local/compalign/add.php', ['cmid' => 5, 'item' => 'moodle:page:1']), [
            'cmid' => 5,
            'item' => 'moodle:page:1',
            'catalogue' => new catalogue_snapshot(1, 'FW', 'Framework', [], $lookup, 'catalogue-hash'),
            'resourcehash' => self::HASH,
            'text' => 'Unit tests check one function at a time.',
            'active' => [],
        ]);
    }

    /**
     * Build the form after a teacher's browser has submitted a competency.
     *
     * @param string $competency The submitted competency.
     * @return add_competency_form
     */
    private function submit(string $competency): add_competency_form {
        add_competency_form::mock_submit([
            'cmid' => 5,
            'item' => 'moodle:page:1',
            'resourcehash' => self::HASH,
            'competency' => $competency,
        ]);

        return $this->make_form();
    }

    /**
     * No competency is chosen before the teacher picks one.
     *
     * Regression: a single-choice list selects its first option, so the first competency of the
     * framework was shown as chosen, and saved if the teacher submitted without picking one.
     */
    public function test_nothing_is_preselected(): void {
        $this->resetAfterTest();
        $options = self::options($this->make_form()->render(), 'competency');

        $this->assertSame(['', 'T1', 'T1_1', 'T2'], array_map('strval', array_keys($options)), 'The empty choice comes first.');
        $this->assertSame('', $options['']['label'], 'The empty choice has no label, so the widget shows its prompt.');
        $this->assertSame([], array_keys(array_filter($options, static fn(array $option): bool => $option['selected'])),
            'No competency is marked as selected.');
    }

    /**
     * Saving without picking a competency is refused; picking one is accepted.
     */
    public function test_a_competency_must_be_picked(): void {
        $this->resetAfterTest();
        $this->assertNull($this->submit('')->get_data(), 'A form without a competency was accepted.');

        $data = $this->submit('T2')->get_data();
        $this->assertNotNull($data, 'A framework competency was refused.');
        $this->assertSame('T2', $data->competency);
    }

    /**
     * The options of a select in rendered form HTML.
     *
     * @param string $html The form.
     * @param string $name The select's name.
     * @return array<string, array{label: string, selected: bool}>
     */
    private static function options(string $html, string $name): array {
        $document = new \DOMDocument();
        libxml_use_internal_errors(true);
        $document->loadHTML('<?xml encoding="utf-8"?>' . $html);
        libxml_clear_errors();
        $options = [];
        foreach ((new \DOMXPath($document))->query("//select[@name='$name']/option") as $option) {
            $options[$option->getAttribute('value')] = [
                'label' => trim($option->textContent),
                'selected' => $option->hasAttribute('selected'),
            ];
        }

        return $options;
    }
}
