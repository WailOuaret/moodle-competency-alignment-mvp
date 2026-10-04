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
use local_compalign\fixtures\environment;
use local_compalign\form\review_form;
use local_compalign\service\analysis_manager;
use local_compalign\service\catalogue_snapshot;
use local_compalign\service\review_manager;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Tests for the review page, rendered with Moodle's own renderer and templates.
 *
 * Scripts cannot judge how a page looks, but they can check what it says and what it must never say.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(review_page::class)]
final class review_page_test extends advanced_testcase {
    use environment;

    /**
     * An answer with a parent and its child, each carrying the hierarchy warning the engine would give.
     *
     * @return array The values that replace the stub's answer.
     */
    private function parent_and_child(): array {
        $suggestion = static fn(string $idnumber, string $quote, string $role, string $related): array => [
            'competency_idnumber' => $idnumber,
            'confidence' => 0.8,
            'bm25_rank' => 1,
            'support_count' => 1,
            'evidence' => [['fragment_id' => 'moodle:page:1#f001', 'quote' => $quote]],
            'warnings' => [[
                'code' => 'parent_child_redundancy',
                'role' => $role,
                'related_idnumber' => $related,
                'message' => 'The service\'s own wording is not used.',
            ]],
        ];

        return ['suggestions' => [
            $suggestion('T1', 'Unit tests check one function at a time.', 'parent', 'T1_1'),
            $suggestion('T1_1', 'Integration tests check how the parts of a program work together.', 'child', 'T1'),
        ]];
    }

    /**
     * Render the review page.
     *
     * @param array $environment As returned by create_environment().
     * @param \stdClass|null $analysis The analysis to show.
     * @param array $suggestions Its suggestions, with evidence.
     * @param catalogue_snapshot|null $catalogue The framework.
     * @param array $reviews The current user's latest reviews, by suggestion id.
     * @param array $forms The rendered decision forms, by suggestion id.
     * @return string The HTML.
     */
    private function render(
        array $environment,
        ?\stdClass $analysis,
        array $suggestions = [],
        ?catalogue_snapshot $catalogue = null,
        array $reviews = [],
        array $forms = []
    ): string {
        global $PAGE;

        $PAGE->set_url('/local/compalign/review.php', ['cmid' => $environment['cm']->id]);
        $PAGE->set_context(\context_module::instance($environment['cm']->id));
        $page = new review_page($environment['cm'], true, $analysis, $suggestions, $catalogue, $reviews, $forms, [], [], '');

        return $PAGE->get_renderer('core')->render($page);
    }

    /**
     * The text a person would read, without the markup.
     *
     * @param string $html The page.
     * @return string
     */
    private static function text(string $html): string {
        return trim((string) preg_replace('/\s+/', ' ', html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5)));
    }

    /**
     * The decision form of a suggestion, built the way the review page builds it.
     *
     * @param \stdClass $suggestion The suggestion.
     * @param catalogue_snapshot $catalogue The framework.
     * @param int $cmid The Page.
     * @param array|null $data Values to show in the form.
     * @return string The form's HTML.
     */
    private function form_html(\stdClass $suggestion, catalogue_snapshot $catalogue, int $cmid, ?array $data = null): string {
        $proposed = (string) $suggestion->competencyidnumber;
        $choices = [];
        foreach ($catalogue->lookup as $idnumber => $competency) {
            if ((string) $idnumber !== $proposed) {
                $choices[(string) $idnumber] = $idnumber . ' - ' . $competency['shortname'];
            }
        }

        $form = new review_form(new \moodle_url('/local/compalign/review.php', ['cmid' => $cmid]), [
            'cmid' => $cmid,
            'suggestionid' => (int) $suggestion->id,
            'proposedidnumber' => $proposed,
            'choices' => $choices,
            'validids' => $catalogue->idnumbers(),
        ]);
        if ($data !== null) {
            $form->set_data($data);
        }

        return $form->render();
    }

    /**
     * Each card shows the competency, the exact evidence and the hierarchy note, and keeps the details secondary.
     */
    public function test_each_card_shows_the_competency_the_evidence_and_the_hierarchy_note(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment, $this->parent_and_child());

        $html = $this->render($environment, $made['analysis'], $made['suggestions'], $made['catalogue']);
        $text = self::text($html);

        $this->assertSame(2, substr_count($text, 'Suggested competency'));
        $this->assertStringContainsString('Verify software', $text);
        $this->assertStringContainsString('Plan and run tests that verify software.', $text);
        $this->assertStringContainsString('Unit testing', $text);
        $this->assertSame(2, substr_count($text, 'Exact evidence from the resource'));
        $this->assertStringContainsString('Unit tests check one function at a time.', $text);
        $this->assertStringContainsString('Integration tests check how the parts of a program work together.', $text);

        $this->assertStringContainsString(
            'A more specific child competency (T1_1 Unit testing) is also suggested for this resource.',
            $text
        );
        $this->assertStringContainsString('Its parent competency (T1 Verify software) is also suggested for this resource.', $text);
        $this->assertStringNotContainsString('The service\'s own wording', $text, 'The plugin words the note itself.');

        $this->assertSame(2, substr_count($html, '<details'), 'The technical details are a disclosure on each card.');
        $this->assertSame(0, preg_match('/<details[^>]*\sopen/i', $html), 'They are collapsed until someone opens them.');
        $this->assertStringContainsString('Model confidence (not a probability)', $text);
        $this->assertStringContainsString('0.80', $text);
        $this->assertStringNotContainsString('80%', $text, 'The confidence is never shown as a percentage.');
    }

    /**
     * What the page says about where the suggestions come from and what saving does.
     */
    public function test_the_page_says_it_is_a_test_backend_and_that_nothing_is_written(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);

        $text = self::text($this->render($environment, $made['analysis'], $made['suggestions'], $made['catalogue']));

        $this->assertStringContainsString(
            'This analysis used the test backend. Its suggestions are placeholders and are not model output.',
            $text
        );
        $this->assertStringContainsString(
            'Official write-back is off. Saving a decision does not create or change any Moodle competency link.',
            $text
        );
        $this->assertStringContainsString('Not reviewed yet', $text);
    }

    /**
     * Nothing that should stay hidden is ever on the page.
     */
    public function test_nothing_that_should_stay_hidden_is_shown(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment, $this->parent_and_child());

        $html = $this->render($environment, $made['analysis'], $made['suggestions'], $made['catalogue']);
        $text = strtolower(self::text($html));

        $forbidden = ['gold', 'ground truth', 'reference label', 'annotation', 'prompt', 'sha256', 'traceback', 'stack trace'];
        foreach ($forbidden as $word) {
            $this->assertStringNotContainsString($word, $text, "The page mentions '$word'.");
        }
        foreach (['{"', '[{', '"competency_idnumber"', '"fragment_id"'] as $json) {
            $this->assertStringNotContainsString($json, $html, 'Raw JSON is on the page.');
        }
    }

    /**
     * Text from a Page that looks like markup is shown as text, never as markup.
     */
    public function test_evidence_that_looks_like_markup_is_escaped(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $DB->set_field(
            'page',
            'content',
            '<p>Use &lt;b&gt;tags&lt;/b&gt; &amp; entities carefully, never &lt;script&gt;alert(1)&lt;/script&gt;.</p>',
            ['id' => $environment['page']->id]
        );
        $quote = 'Use <b>tags</b> & entities carefully, never <script>alert(1)</script>.';
        $made = $this->create_completed_analysis($environment, ['suggestions' => [[
            'competency_idnumber' => 'T1',
            'confidence' => 0.8,
            'bm25_rank' => 1,
            'support_count' => 1,
            'evidence' => [['fragment_id' => 'moodle:page:1#f001', 'quote' => $quote]],
            'warnings' => [],
        ]]]);

        $html = $this->render($environment, $made['analysis'], $made['suggestions'], $made['catalogue']);

        $this->assertStringContainsString('Use &lt;b&gt;tags&lt;/b&gt; &amp; entities carefully', $html);
        $this->assertStringNotContainsString('<b>tags</b>', $html);
        $this->assertStringNotContainsString('<script>alert(1)', $html);
        $this->assertStringContainsString($quote, self::text($html), 'A reader still sees the words as written.');
    }

    /**
     * A saved decision is summarised on its card, and the form shows it again with the comment escaped.
     */
    public function test_a_saved_decision_is_summarised_and_its_comment_is_escaped(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment, $this->parent_and_child());
        $first = reset($made['suggestions']);
        $second = next($made['suggestions']);
        $comment = '<img src=x onerror=alert(1)> & "quoted"';

        $manager = new review_manager();
        $userid = (int) $environment['teacher']->id;
        $manager->save($made['analysis'], $first, $userid, 'accept', null, '0', $comment, null, $made['catalogue']);
        $manager->save($made['analysis'], $second, $userid, 'modify', 'T2', '2', null, null, $made['catalogue']);
        $reviews = $manager->latest_reviews((int) $made['analysis']->id, $userid);

        $forms = [];
        foreach ([$first, $second] as $suggestion) {
            $review = $reviews[(int) $suggestion->id];
            $forms[(int) $suggestion->id] = $this->form_html($suggestion, $made['catalogue'], (int) $environment['cm']->id, [
                'decision' => $review->decision,
                'finalcompetency' => $review->decision === 'modify' ? $review->finalcompetencyidnumber : '',
                'usefulness' => $review->evidenceusefulness,
                'commenttext' => $review->commenttext,
            ]);
        }

        $html = $this->render($environment, $made['analysis'], $made['suggestions'], $made['catalogue'], $reviews, $forms);
        $text = self::text($html);

        $this->assertStringContainsString('Your decision: Accepted', $text);
        $this->assertStringContainsString('Your decision: Modified to T2 Deploy software', $text);
        $this->assertSame(2, substr_count($text, 'Revision 1, saved'));
        $this->assertStringNotContainsString('Not reviewed yet', $text);
        $this->assertStringContainsString('&lt;img src=x onerror=alert(1)&gt;', $html, 'The comment is shown as text.');
        $this->assertStringNotContainsString('<img src=x', $html, 'The comment must never become markup.');
    }

    /**
     * What each state of an analysis says when there is nothing to review yet.
     *
     * @return array<string, array>
     */
    public static function state_provider(): array {
        return [
            'queued' => [
                analysis_manager::STATUS_QUEUED,
                null,
                ['Queued', 'The analysis starts when Moodle next runs its background tasks (cron). This page refreshes by itself.'],
            ],
            'running' => [
                analysis_manager::STATUS_RUNNING,
                null,
                ['Analysing', 'The resource is being analysed. This page refreshes by itself.'],
            ],
            'failed because the service is down' => [
                analysis_manager::STATUS_FAILED,
                'unavailable',
                [
                    'The analysis did not complete',
                    'The alignment service could not be reached.',
                    'Nothing was changed in your course.',
                    'use Reanalyse to try again',
                ],
            ],
            'failed because the answer was not valid' => [
                analysis_manager::STATUS_FAILED,
                'invalid_response',
                ['The alignment service answered with something that did not pass validation. No suggestion was stored.'],
            ],
        ];
    }

    /**
     * A waiting, running or failed analysis is explained in plain words and shows no suggestion.
     *
     * @param string $status The state of the analysis.
     * @param string|null $errorcode The stored error code.
     * @param string[] $expected What the page must say.
     */
    #[DataProvider('state_provider')]
    public function test_an_unfinished_analysis_is_explained(string $status, ?string $errorcode, array $expected): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $manager = $this->create_manager();
        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);
        $DB->update_record('local_compalign_analysis', (object) [
            'id' => $requested['analysis']->id,
            'status' => $status,
            'errorcode' => $errorcode,
        ]);

        $html = $this->render($environment, $manager->get_latest((int) $environment['cm']->id));
        $text = self::text($html);

        foreach ($expected as $sentence) {
            $this->assertStringContainsString($sentence, $text);
        }
        $this->assertStringNotContainsString('Suggested competency', $text);
    }

    /**
     * A resource of a type that cannot be analysed is explained by its own notice and not by "none requested".
     */
    public function test_an_unsupported_resource_has_its_own_notice(): void {
        global $PAGE;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $PAGE->set_url('/local/compalign/review.php', ['cmid' => $environment['cm']->id]);
        $PAGE->set_context(\context_module::instance($environment['cm']->id));

        $notice = [['type' => 'info', 'text' => get_string('unsupportedtype', 'local_compalign')]];
        $page = new review_page($environment['cm'], false, null, [], null, [], [], [], $notice, '');
        $text = self::text($PAGE->get_renderer('core')->render($page));

        $this->assertStringContainsString('Resource type not supported in this prototype.', $text);
        $this->assertStringNotContainsString('No analysis has been requested', $text);
    }
}
