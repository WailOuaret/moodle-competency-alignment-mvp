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

use local_compalign\service\resource_extractor;

/**
 * Teacher-authored question text, without the answer key or any student attempt.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class question_text {
    /** Question types whose teacher text can be normalised safely. */
    public const SUPPORTED = ['multichoice', 'truefalse', 'shortanswer', 'numerical', 'essay', 'match'];

    /**
     * Build the text sent for alignment.
     *
     * Choices are the visible options. Nothing in this method receives a fraction,
     * a right-answer id, a grade, or a student response, so it cannot leak them.
     *
     * @param string $qtype Moodle question type name.
     * @param string $name Question name.
     * @param string $stem Plain-text stem.
     * @param string[] $choices Visible choices, prompts or options. Not paired with correctness.
     * @return array{supported: bool, text: string}
     */
    public static function build(string $qtype, string $name, string $stem, array $choices): array {
        if (!in_array($qtype, self::SUPPORTED, true)) {
            return ['supported' => false, 'text' => ''];
        }

        $parts = [];
        $name = trim($name);
        $stem = trim($stem);
        if ($name !== '' && $name !== $stem) {
            $parts[] = $name;
        }
        if ($stem !== '') {
            $parts[] = $stem;
        }

        // Short answer, numerical and essay prompts are the question. The accepted
        // answers are the key, so they are not added.
        if (in_array($qtype, ['multichoice', 'truefalse', 'match'], true)) {
            foreach ($choices as $choice) {
                $choice = trim($choice);
                if ($choice !== '') {
                    $parts[] = $choice;
                }
            }
        }

        return [
            'supported' => true,
            'text' => resource_extractor::combine_text(...$parts),
        ];
    }
}
