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
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

/**
 * Tests for the decision form shown under each suggestion.
 *
 * The form is rendered and submitted the way Moodle does it, so these tests see what a teacher's
 * browser would receive and what the server would accept.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(review_form::class)]
final class review_form_test extends advanced_testcase {
    /** @var int The suggestion the forms are built for. */
    private const SUGGESTION = 7;

    /**
     * Build the form for a suggestion of T1, in a framework with T1, T1_1 and T2.
     *
     * @param array|null $data Values to show in the form, as the review page does for an earlier decision.
     * @param int $suggestionid The suggestion.
     * @return review_form
     */
    private function make_form(?array $data = null, int $suggestionid = self::SUGGESTION): review_form {
        $form = new review_form(new \moodle_url('/local/compalign/review.php', ['cmid' => 5]), [
            'cmid' => 5,
            'suggestionid' => $suggestionid,
            'proposedidnumber' => 'T1',
            'choices' => ['T1_1' => 'T1_1 - Unit testing', 'T2' => 'T2 - Deploy software'],
            'validids' => ['T1', 'T1_1', 'T2'],
        ]);
        if ($data !== null) {
            $form->set_data($data);
        }

        return $form;
    }

    /**
     * Build the form after a teacher's browser has submitted values to it.
     *
     * @param array $post What the browser sends, besides the hidden fields the form adds itself.
     * @return review_form
     */
    private function submit(array $post): review_form {
        review_form::mock_submit($post, [], 'post', 'local_compalign_review_' . self::SUGGESTION);

        return $this->make_form();
    }

    /**
     * The radio buttons of a rendered form.
     *
     * @param string $html The form.
     * @return array<string, array<string, bool>> For each radio name, each value and whether it is checked.
     */
    private static function radios(string $html): array {
        $found = [];
        preg_match_all('/<input\b[^>]*>/is', $html, $tags);
        foreach ($tags[0] as $tag) {
            $isradio = preg_match('/\btype="radio"/i', $tag);
            $hasname = preg_match('/\bname="([^"]*)"/i', $tag, $name);
            $hasvalue = preg_match('/\bvalue="([^"]*)"/i', $tag, $value);
            if (!$isradio || !$hasname || !$hasvalue) {
                continue;
            }
            $found[$name[1]][(string) $value[1]] = (bool) preg_match('/\schecked(\s|=|>|\/)/i', $tag);
        }

        return $found;
    }

    /**
     * The competencies chosen in a drop-down of a rendered form.
     *
     * Moodle marks an option as selected only when a value was set. Without one the browser shows the first option,
     * the placeholder with an empty value, so the placeholder never counts as a choice.
     *
     * @param string $html The form.
     * @param string $name The drop-down's name.
     * @return string[] The values of the selected options, without the placeholder.
     */
    private static function chosen(string $html, string $name): array {
        preg_match('/<select\b[^>]*name="' . preg_quote($name, '/') . '".*?<\/select>/is', $html, $select);
        preg_match_all('/<option\b[^>]*value="([^"]*)"[^>]*\sselected/is', $select[0] ?? '', $options);

        return array_values(array_filter($options[1], static fn(string $value): bool => $value !== ''));
    }

    /**
     * The names of the hidden fields of a rendered form, whatever order their attributes are in.
     *
     * @param string $html The form.
     * @return string[] Sorted names.
     */
    private static function hidden_fields(string $html): array {
        $names = [];
        preg_match_all('/<input\b[^>]*>/is', $html, $tags);
        foreach ($tags[0] as $tag) {
            if (preg_match('/\btype="hidden"/i', $tag) && preg_match('/\bname="([^"]*)"/i', $tag, $name)) {
                $names[] = $name[1];
            }
        }
        sort($names);

        return $names;
    }

    /**
     * Nothing is preselected on a form that has not been used.
     */
    public function test_nothing_is_preselected(): void {
        $html = $this->make_form()->render();
        $radios = self::radios($html);

        $this->assertSame(['accept', 'reject', 'modify'], array_keys($radios['decision']));
        $this->assertSame(['0', '1', '2'], array_map('strval', array_keys($radios['usefulness'])));
        $this->assertSame([], array_keys(array_filter($radios['decision'])), 'No decision is preselected.');
        $this->assertSame([], array_keys(array_filter($radios['usefulness'])), 'No rating is preselected, not even zero.');
        $this->assertSame([], self::chosen($html, 'finalcompetency'), 'No replacement is preselected.');
    }

    /**
     * What an earlier decision shows when the form is opened again.
     *
     * @return array<string, array>
     */
    public static function prefill_provider(): array {
        return [
            'accept with a rating of zero' => [['decision' => 'accept', 'usefulness' => '0'], 'accept', '0', ''],
            'accept with zero as an integer' => [['decision' => 'accept', 'usefulness' => 0], 'accept', '0', ''],
            'reject with a rating of one' => [['decision' => 'reject', 'usefulness' => '1'], 'reject', '1', ''],
            'modify with a rating of two' => [
                ['decision' => 'modify', 'usefulness' => '2', 'finalcompetency' => 'T2'], 'modify', '2', 'T2',
            ],
            'a decision that was saved without a rating' => [['decision' => 'accept', 'usefulness' => null], 'accept', null, ''],
        ];
    }

    /**
     * An earlier decision is shown again, and zero is a rating that is shown as such.
     *
     * @param array $data What the review page passes in.
     * @param string $decision The decision that must be checked.
     * @param string|null $rating The rating that must be checked, or null for none.
     * @param string $replacement The replacement that must be selected.
     */
    #[DataProvider('prefill_provider')]
    public function test_an_earlier_decision_is_shown_again(
        array $data,
        string $decision,
        ?string $rating,
        string $replacement
    ): void {
        $html = $this->make_form($data)->render();
        $radios = self::radios($html);

        $this->assertSame([$decision], array_keys(array_filter($radios['decision'])));
        $this->assertSame(
            $rating === null ? [] : [$rating],
            array_map('strval', array_keys(array_filter($radios['usefulness'])))
        );
        $this->assertSame($replacement === '' ? [] : [$replacement], self::chosen($html, 'finalcompetency'));
    }

    /**
     * What a browser may submit, with the message the form must show when it is refused.
     *
     * @return array<string, array>
     */
    public static function submission_provider(): array {
        return [
            'accept and nothing else' => [['decision' => 'accept'], null],
            'accept with every field' => [['decision' => 'accept', 'usefulness' => '2', 'commenttext' => 'Clear.'], null],
            'reject with a rating of zero' => [['decision' => 'reject', 'usefulness' => '0'], null],
            'modify to another competency' => [['decision' => 'modify', 'finalcompetency' => 'T2'], null],
            'no decision' => [['usefulness' => '1'], 'error_decisionrequired'],
            'a decision that does not exist' => [['decision' => 'approve'], 'error_decisionrequired'],
            'modify without a competency' => [['decision' => 'modify', 'finalcompetency' => ''], 'error_modifyneedscompetency'],
            'modify to the suggested competency' => [
                ['decision' => 'modify', 'finalcompetency' => 'T1'], 'error_modifyneedscompetency',
            ],
            'modify to a competency that does not exist' => [
                ['decision' => 'modify', 'finalcompetency' => 'ZZ'], 'error_modifyneedscompetency',
            ],
            'a rating of three' => [['decision' => 'accept', 'usefulness' => '3'], 'error_invalidusefulness'],
            'a rating that is text' => [['decision' => 'accept', 'usefulness' => 'abc'], 'error_invalidusefulness'],
            'a negative rating' => [['decision' => 'accept', 'usefulness' => '-1'], 'error_invalidusefulness'],
            'several ratings at once' => [['decision' => 'accept', 'usefulness' => ['1', '2']], 'error_invalidusefulness'],
            'a comment of 1001 characters' => [
                ['decision' => 'accept', 'commenttext' => str_repeat('a', 1001)], 'error_commenttoolong',
            ],
        ];
    }

    /**
     * A submission is accepted or refused with a clear message, and a refused one yields no data.
     *
     * @param array $post What the browser sends.
     * @param string|null $errorkey The language string of the message, or null when it must be accepted.
     */
    #[DataProvider('submission_provider')]
    public function test_a_submission_is_accepted_or_refused(array $post, ?string $errorkey): void {
        $form = $this->submit($post);
        $data = $form->get_data();

        if ($errorkey === null) {
            $this->assertNotNull($data, 'A valid decision was refused.');
            $this->assertSame($post['decision'], $data->decision);
            return;
        }

        $this->assertNull($data, 'An invalid decision was accepted.');
        $this->assertStringContainsString(get_string($errorkey, 'local_compalign', 1000), $form->render());
    }

    /**
     * Fields that are not part of the form never reach the saver.
     */
    public function test_extra_fields_are_ignored(): void {
        $form = $this->submit([
            'decision' => 'accept',
            'userid' => 99,
            'reviewerid' => 99,
            'analysisid' => 5,
            'writebackstatus' => 'done',
        ]);

        $data = $form->get_data();

        $this->assertNotNull($data);
        foreach (['userid', 'reviewerid', 'analysisid', 'writebackstatus'] as $field) {
            $this->assertFalse(property_exists($data, $field), $field);
        }
    }

    /**
     * The form says who is reviewing nowhere: the page uses the logged-in user.
     */
    public function test_the_form_carries_no_user(): void {
        $html = $this->make_form()->render();

        $this->assertSame(
            ['_qf__local_compalign_review_7', 'cmid', 'sesskey', 'suggestionid'],
            self::hidden_fields($html)
        );
        $this->assertStringNotContainsString('name="userid"', $html);
    }

    /**
     * Every suggestion has its own form, so one page can hold several and a save reaches only its own.
     */
    public function test_each_suggestion_has_its_own_form_identifier(): void {
        $this->assertStringContainsString('_qf__local_compalign_review_7', $this->make_form()->render());
        $this->assertStringContainsString('_qf__local_compalign_review_8', $this->make_form(null, 8)->render());

        review_form::mock_submit(['decision' => 'accept'], [], 'post', 'local_compalign_review_8');
        $this->assertNull($this->make_form()->get_data(), 'A submission for suggestion 8 must not be taken by the form of 7.');
        $this->assertNotNull($this->make_form(null, 8)->get_data());
    }
}
