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
use local_compalign\fixtures\environment;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/fixtures/fake_transport.php');
require_once(__DIR__ . '/fixtures/service_stub.php');
require_once(__DIR__ . '/fixtures/environment.php');

/**
 * Tests for reading a Moodle Page as the resource the alignment service analyses.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(resource_extractor::class)]
final class resource_extractor_test extends advanced_testcase {
    use environment;

    /**
     * HTML with the plain text it must become.
     *
     * @return array<string, array>
     */
    public static function html_provider(): array {
        return [
            'nothing' => ['', ''],
            'only white space' => ["  \n ", ''],
            'two paragraphs stay apart' => ['<p>Hello</p><p>World</p>', 'Hello World'],
            'a script is dropped, not read' => ['<script>alert(1)</script>Safe', 'Safe'],
            'a style is dropped' => ['<style>p { color: red; }</style><p>Text</p>', 'Text'],
            'a comment is dropped' => ['<!-- hidden -->Visible', 'Visible'],
            'entities are decoded' => ['A&nbsp;B &amp; C', 'A B & C'],
            'list items stay apart' => ['<ul><li>One</li><li>Two</li></ul>', 'One Two'],
            'a line break stays a space' => ['<p>Line<br>break</p>', 'Line break'],
            'words in neighbouring tags stay apart' => ['Tom<b>and</b>Jerry', 'Tom and Jerry'],
            'attributes are not text' => ['<a href="https://example.org" title="Secret">Link</a>', 'Link'],
        ];
    }

    /**
     * Markup is reduced to plain text and never executed.
     *
     * @param string $html The Moodle HTML.
     * @param string $expected The plain text.
     */
    #[DataProvider('html_provider')]
    public function test_html_to_text(string $html, string $expected): void {
        $this->assertSame($expected, resource_extractor::html_to_text($html));
    }

    /**
     * A missing value is the empty text.
     */
    public function test_html_to_text_of_null(): void {
        $this->assertSame('', resource_extractor::html_to_text(null));
    }

    /**
     * Parts are joined by a blank line, and a part that repeats an earlier one is skipped.
     */
    public function test_combine_text(): void {
        $this->assertSame("Intro\n\nBody", resource_extractor::combine_text('Intro', 'Body'));
        $this->assertSame('Same', resource_extractor::combine_text('Same', 'same'));
        $this->assertSame('Body', resource_extractor::combine_text('', 'Body'));
        $this->assertSame('', resource_extractor::combine_text('', '  '));
        $this->assertSame('A B', resource_extractor::combine_text(" A \n B "));
    }

    /**
     * The digest follows what can change an analysis, and not the identifiers.
     */
    public function test_hash(): void {
        $resource = [
            'resource_id' => 'moodle:page:1',
            'resource_type' => 'page',
            'title' => 'Testing',
            'text' => 'Unit tests check one function.',
            'course_fullname' => 'Software',
            'section_name' => 'Week 1',
            'activity_name' => 'Testing',
        ];
        $hash = resource_extractor::hash($resource);

        $this->assertMatchesRegularExpression('/^sha256:[0-9a-f]{64}$/', $hash);
        $this->assertSame($hash, resource_extractor::hash($resource));
        $this->assertSame(
            $hash,
            resource_extractor::hash(['resource_id' => 'moodle:page:2'] + $resource),
            'Another id, same words.'
        );
        $this->assertNotSame($hash, resource_extractor::hash(['text' => 'Different words.'] + $resource));
        $this->assertNotSame($hash, resource_extractor::hash(['title' => 'Other title'] + $resource));
    }

    /**
     * Only a Page can be analysed in this prototype.
     */
    public function test_only_pages_are_supported(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $forum = $this->getDataGenerator()->create_module('forum', ['course' => $environment['course']->id]);
        $forumcm = get_fast_modinfo($environment['course'])->get_cm((int) $forum->cmid);

        $this->assertTrue(resource_extractor::supports($environment['cm']));
        $this->assertFalse(resource_extractor::supports($forumcm));

        try {
            (new resource_extractor())->extract($forumcm);
            $this->fail('A forum was read.');
        } catch (analysis_exception $exception) {
            $this->assertSame('unsupported_resource_type', $exception->get_error_code());
        }
    }

    /**
     * A Page becomes a resource with its text, and nothing about people.
     */
    public function test_extract_describes_the_page(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();

        $extracted = (new resource_extractor())->extract($environment['cm']);
        $resource = $extracted['resource'];

        $this->assertSame('moodle:page:' . $environment['page']->id, $resource['resource_id']);
        $this->assertSame('page', $resource['resource_type']);
        $this->assertSame((string) $environment['course']->id, $resource['course_id']);
        $this->assertSame((string) $environment['cm']->id, $resource['course_module_id']);
        $this->assertSame('Software testing', $resource['title']);
        $this->assertSame(
            "Introduction to software testing.\n\n"
                . 'Unit tests check one function at a time. Integration tests check how the parts of a program work together.',
            $resource['text'],
            'The introduction and the body are joined by a blank line.'
        );
        $this->assertSame(
            "Software testing\n\n" . preg_replace('/\s+/', ' ', $resource['text']),
            $resource['search_text'],
            'The retrieval text is the title and the text, with the white space inside each part collapsed.'
        );
        $this->assertSame($environment['course']->fullname, $resource['course_fullname']);
        $this->assertSame(resource_extractor::hash($resource), $extracted['hash']);

        $encoded = json_encode($resource);
        foreach ([$environment['teacher'], $environment['student']] as $user) {
            $this->assertStringNotContainsString($user->email, $encoded);
            $this->assertStringNotContainsString($user->lastname, $encoded);
        }
    }

    /**
     * Editing the Page changes the digest, so a stale analysis can be told from a current one.
     */
    public function test_editing_the_page_changes_the_hash(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $extractor = new resource_extractor();

        $before = $extractor->extract($environment['cm'])['hash'];
        $this->assertSame($before, $extractor->extract($environment['cm'])['hash']);

        $DB->set_field('page', 'content', '<p>Something else entirely.</p>', ['id' => $environment['page']->id]);

        $this->assertNotSame($before, $extractor->extract($environment['cm'])['hash']);
    }

    /**
     * A Page the user cannot see, with no text, or with too much text is not analysed.
     */
    public function test_pages_that_cannot_be_analysed(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $generator = $this->getDataGenerator();
        $course = $environment['course'];
        $extractor = new resource_extractor();

        $hidden = $generator->create_module('page', ['course' => $course->id, 'visible' => 0, 'content' => '<p>Secret.</p>']);
        // The generator gives every Page an introduction of its own, so this one is emptied afterwards.
        $empty = $generator->create_module('page', ['course' => $course->id, 'content' => '<p> </p>']);
        $DB->set_field('page', 'intro', '', ['id' => $empty->id]);
        $toolong = $generator->create_module('page', [
            'course' => $course->id,
            'content' => '<p>' . str_repeat('a ', resource_extractor::MAX_TEXT_CHARS / 2 + 1) . '</p>',
        ]);

        $asstudent = get_fast_modinfo($course, (int) $environment['student']->id);
        $asteacher = get_fast_modinfo($course, (int) $environment['teacher']->id);

        $cases = [
            'hidden from a student' => [$asstudent->get_cm((int) $hidden->cmid), 'resource_not_accessible'],
            'no text' => [$asteacher->get_cm((int) $empty->cmid), 'resource_empty'],
            'too long' => [$asteacher->get_cm((int) $toolong->cmid), 'resource_too_large'],
        ];

        foreach ($cases as $label => [$cm, $code]) {
            try {
                $extractor->extract($cm);
                $this->fail("$label was read.");
            } catch (analysis_exception $exception) {
                $this->assertSame($code, $exception->get_error_code(), $label);
            }
        }
    }
}
