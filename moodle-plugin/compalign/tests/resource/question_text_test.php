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

namespace local_compalign\resource;

/**
 * Quiz question text sent to the alignment service.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[\PHPUnit\Framework\Attributes\CoversClass(\local_compalign\resource\question_text::class)]
final class question_text_test extends \advanced_testcase {
    /**
     * Multiple choice keeps the visible choices. Scores are not an argument of this method.
     */
    public function test_multichoice_keeps_choices(): void {
        $built = question_text::build(
            'multichoice',
            'Normal forms',
            'Which normal form removes partial dependencies?',
            ['First normal form', 'Second normal form']
        );

        $this->assertTrue($built['supported']);
        $this->assertStringContainsString('Second normal form', $built['text']);
        $this->assertStringContainsString('partial dependencies', $built['text']);
    }

    /**
     * A short-answer question is the stem only, even if a caller passes accepted answers.
     */
    public function test_shortanswer_drops_the_answer_key(): void {
        $built = question_text::build(
            'shortanswer',
            'Key',
            'Name the key that uniquely identifies a row.',
            ['primary key']
        );

        $this->assertTrue($built['supported']);
        $this->assertStringContainsString('uniquely identifies', $built['text']);
        $this->assertStringNotContainsString('primary key', $built['text']);
    }

    /**
     * Calculated questions are refused without a text blob.
     */
    public function test_calculated_is_unsupported(): void {
        $built = question_text::build('calculated', 'Compute', 'What is the result?', ['42']);

        $this->assertFalse($built['supported']);
        $this->assertSame('', $built['text']);
    }
}
