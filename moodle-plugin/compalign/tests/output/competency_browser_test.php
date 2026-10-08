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

/**
 * Tests for the Competency -> Resources view.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(competency_browser::class)]
final class competency_browser_test extends advanced_testcase {
    /**
     * Every cell carries its column name.
     *
     * Regression: on a phone the stylesheet hides the table header and shows each cell's
     * data-label instead. Without it the cells read "Reviewed" or "No" with no column name.
     */
    public function test_each_cell_is_labelled_for_the_phone_layout(): void {
        global $PAGE;

        $this->resetAfterTest();
        $course = $this->getDataGenerator()->create_course();
        $PAGE->set_url('/local/compalign/index.php', ['courseid' => $course->id, 'view' => 'competencies']);
        $PAGE->set_context(\context_course::instance($course->id));
        $row = [
            'name' => 'Software testing',
            'type' => 'Page',
            'relationship' => 'Model proposed',
            'source' => 'MODEL_PROPOSED',
            'stale' => false,
            'reviewstatus' => 'Accepted',
            'evidence' => 'Show in source',
            'evidencenote' => '',
            'sourceurl' => 'https://example.invalid/source',
            'official' => false,
            'openurl' => 'https://example.invalid/open',
            'reviewurl' => 'https://example.invalid/review',
        ];
        $html = $PAGE->get_renderer('core')->render(new competency_browser($course, [], 'T1', '', 'all', [$row]));

        $document = new \DOMDocument();
        libxml_use_internal_errors(true);
        $document->loadHTML('<?xml encoding="utf-8"?>' . $html);
        libxml_clear_errors();
        $labels = [];
        foreach ((new \DOMXPath($document))->query('//table//tbody//td') as $cell) {
            $labels[] = $cell->getAttribute('data-label');
        }
        $expected = array_map(
            static fn(string $key): string => get_string($key, 'local_compalign'),
            ['column_type', 'column_relationship', 'column_reviewstatus', 'column_evidence', 'column_official_link', 'column_action']
        );
        $this->assertSame($expected, $labels);
    }
}
