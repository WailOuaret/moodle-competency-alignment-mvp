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

use local_compalign\service\analysis_exception;
use local_compalign\service\resource_extractor;
use mod_quiz\question\bank\qbank_helper;

/**
 * One quiz question version is one analytical resource.
 *
 * Random slots have no fixed question, so they are listed as unsupported.
 * Student attempts are never read. The correct-answer fraction is never copied
 * into the text.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class quiz_adapter implements adapter {
    public function modname(): string {
        return 'quiz';
    }

    public function enumerate(\cm_info $cm): array {
        $items = [];
        foreach ($this->slots($cm) as $slot) {
            $items[] = $this->item_for_slot($cm, $slot);
        }
        return $items;
    }

    public function extract(\cm_info $cm, item $item): array {
        foreach ($this->slots($cm) as $slot) {
            $candidate = $this->item_for_slot($cm, $slot);
            if ($candidate->resourceid !== $item->resourceid) {
                continue;
            }
            if (!$candidate->supported) {
                throw new analysis_exception('unsupported_question_type');
            }
            $built = $this->text_for_slot($slot);
            if ($built['text'] === '') {
                throw new analysis_exception('resource_empty');
            }
            $label = $cm->name . ', question ' . $slot->slot;
            return course_context::pack($cm, $candidate, $built['text']) + [
                'provenance' => [
                    'kind' => 'quiz_question',
                    'label' => $label,
                    'slot' => (int) $slot->slot,
                    'questionid' => (int) ($slot->questionid ?? 0),
                    'versionid' => (int) ($slot->versionid ?? 0),
                ],
            ];
        }

        throw new analysis_exception('resource_missing');
    }

    /**
     * @param \cm_info $cm The quiz.
     * @return \stdClass[] Slots from Moodle's question-structure query.
     */
    private function slots(\cm_info $cm): array {
        return qbank_helper::get_question_structure(
            (int) $cm->instance,
            \context_module::instance($cm->id)
        );
    }

    /**
     * @param \cm_info $cm The quiz.
     * @param \stdClass $slot One slot from get_question_structure().
     * @return item
     */
    private function item_for_slot(\cm_info $cm, \stdClass $slot): item {
        $slotnumber = (int) $slot->slot;
        $title = 'Q' . $slotnumber;
        $name = trim(resource_extractor::html_to_text($slot->name ?? ''));
        if ($name !== '') {
            $title .= ' — ' . $name;
        }

        if (!empty($slot->random) || ($slot->qtype ?? '') === 'missingtype' || empty($slot->versionid)) {
            return new item(
                'moodle:quiz:' . $cm->instance . ':slot:' . $slot->id,
                'quiz_question',
                $title,
                '',
                false,
                'unsupportedquestion',
                $cm->name . ', question ' . $slotnumber
            );
        }

        $built = $this->text_for_slot($slot);
        if (!$built['supported']) {
            return new item(
                'moodle:quiz:' . $cm->instance . ':question:' . $slot->versionid,
                'quiz_question',
                $title,
                '',
                false,
                'unsupportedquestion',
                $cm->name . ', question ' . $slotnumber
            );
        }

        return new item(
            'moodle:quiz:' . $cm->instance . ':question:' . $slot->versionid,
            'quiz_question',
            $title,
            mb_substr($built['text'], 0, 160),
            true,
            '',
            $cm->name . ', question ' . $slotnumber
        );
    }

    /**
     * @param \stdClass $slot A non-random slot.
     * @return array{supported: bool, text: string}
     */
    private function text_for_slot(\stdClass $slot): array {
        $qtype = (string) ($slot->qtype ?? '');
        if (!in_array($qtype, question_text::SUPPORTED, true) || empty($slot->questionid)) {
            return ['supported' => false, 'text' => ''];
        }

        $question = \question_bank::load_question((int) $slot->questionid);
        $stem = resource_extractor::html_to_text($question->questiontext ?? '');
        $choices = [];

        if ($qtype === 'multichoice') {
            foreach ($question->answers ?? [] as $answer) {
                $choices[] = resource_extractor::html_to_text($answer->answer ?? '');
            }
        } else if ($qtype === 'truefalse') {
            $choices[] = get_string('true', 'qtype_truefalse');
            $choices[] = get_string('false', 'qtype_truefalse');
        } else if ($qtype === 'match') {
            foreach ($question->stems ?? [] as $prompt) {
                $choices[] = resource_extractor::html_to_text((string) $prompt);
            }
            foreach ($question->choices ?? [] as $option) {
                $choices[] = resource_extractor::html_to_text((string) $option);
            }
        }

        return question_text::build($qtype, resource_extractor::html_to_text($question->name ?? ''), $stem, $choices);
    }
}
