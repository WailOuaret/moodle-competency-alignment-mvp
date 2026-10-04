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
 * Tests for how a catalogue description is split on the review card.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(competency_display::class)]
final class competency_display_test extends advanced_testcase {
    /**
     * Catalogue metadata leaves the main sentence and stays available beside it.
     */
    public function test_catalogue_metadata_is_separated_from_the_description(): void {
        $split = competency_display::split(
            'Assurer la qualité logicielle. English label: Software quality and sustainable engineering '
                . 'UTC competency ID: GI_C1_2 Source URI: http://gamaizer.ia/ontology#GI_C1_2',
            'GI_C1_2'
        );

        $this->assertSame('Assurer la qualité logicielle.', $split['main']);
        $this->assertSame('Software quality and sustainable engineering', $split['englishlabel']);
        $this->assertSame('http://gamaizer.ia/ontology#GI_C1_2', $split['sourceuri']);
        $this->assertSame('', $split['extraid'], 'The id already shown on the card is not repeated.');
    }

    /**
     * A description that has no catalogue labels is shown as it is.
     */
    public function test_a_plain_description_is_left_whole(): void {
        $split = competency_display::split('Plan and run tests that verify software.', 'T1');

        $this->assertSame('Plan and run tests that verify software.', $split['main']);
        $this->assertSame('', $split['englishlabel']);
        $this->assertSame('', $split['sourceuri']);
        $this->assertSame('', $split['extraid']);
    }

    /**
     * An identifier that is not the one on the card is kept for the technical details.
     */
    public function test_a_different_catalogue_id_is_kept(): void {
        $split = competency_display::split(
            'Design software. UTC competency ID: OTHER-1',
            'GI_C1'
        );

        $this->assertSame('Design software.', $split['main']);
        $this->assertSame('OTHER-1', $split['extraid']);
    }
}
