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

use local_compalign\fixtures\environment;
use local_compalign\resource\file_item;
use local_compalign\resource\registry;

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Showing a quotation in its source text.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[\PHPUnit\Framework\Attributes\CoversClass(source_context::class)]
#[\PHPUnit\Framework\Attributes\CoversClass(quote_span::class)]
final class source_context_test extends \advanced_testcase {
    use environment;

    /**
     * Exact text, collapsed whitespace and escaped markup.
     */
    public function test_highlight_matches_and_escapes(): void {
        $exact = quote_span::render('Unit tests check one function.', 'Unit tests check one function.');
        $this->assertTrue($exact['found']);
        $this->assertStringContainsString('<mark>', $exact['html']);
        $this->assertStringContainsString('Unit tests check one function.', $exact['html']);

        $wrapped = quote_span::render("Unit tests\ncheck one function.", 'Unit tests check one function.');
        $this->assertTrue($wrapped['found']);
        $this->assertStringContainsString('<mark>', $wrapped['html']);

        $unsafe = quote_span::render('before <script>alert(1)</script> after', '<script>alert(1)</script>');
        $this->assertTrue($unsafe['found']);
        $this->assertStringNotContainsString('<script>', $unsafe['html']);
        $this->assertStringContainsString('&lt;script&gt;', $unsafe['html']);
        $this->assertStringContainsString('<mark>', $unsafe['html']);

        $missing = quote_span::render('Unit tests check one function.', 'this sentence is absent');
        $this->assertFalse($missing['found']);
    }

    /**
     * A page quotation is highlighted. A student cannot open it, and another course cannot.
     */
    public function test_page_source_permissions(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $viewer = new source_context();
        $context = \context_module::instance($environment['cm']->id);
        $resourceid = 'moodle:page:' . $environment['page']->id;

        $view = $viewer->build(
            $environment['cm'],
            (int) $environment['course']->id,
            $resourceid,
            'Unit tests check one function at a time.',
            $context
        );
        $this->assertTrue($view['found']);
        $this->assertStringContainsString('<mark>', $view['html']);
        $this->assertStringNotContainsString('<p>', $view['html']);

        $missing = $viewer->build($environment['cm'], (int) $environment['course']->id, $resourceid, 'not in the page', $context);
        $this->assertFalse($missing['found']);
        $this->assertSame('quote_not_found', $missing['error']);

        $this->setUser($environment['student']);
        $this->expectException(\required_capability_exception::class);
        $viewer->build($environment['cm'], (int) $environment['course']->id, $resourceid, 'Unit tests', $context);
    }

    /**
     * Evidence from another course is not readable through this activity.
     */
    public function test_cross_course_evidence_is_refused(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $evidenceid = (int) $suggestion->evidence[0]->id;

        $other = $this->create_environment('b');
        $this->expectException(analysis_exception::class);
        (new source_context())->quote_from_evidence($evidenceid, $other['cm'], 'moodle:page:' . $other['page']->id);
    }

    /**
     * Quiz, book, assignment and lesson context excludes student work.
     */
    public function test_activity_sources_exclude_student_data(): void {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/mod/quiz/locallib.php');

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $generator = $this->getDataGenerator();
        $viewer = new source_context();

        $quiz = $generator->create_module('quiz', ['course' => $environment['course']->id, 'name' => 'Quiz']);
        $qgen = $generator->get_plugin_generator('core_question');
        $category = $qgen->create_question_category(['contextid' => \context_module::instance($quiz->cmid)->id]);
        $question = $qgen->create_question('multichoice', 'one_of_four', [
            'category' => $category->id,
            'name' => 'Joins',
            'questiontext' => ['text' => 'A join combines rows from two tables.', 'format' => FORMAT_HTML],
        ]);
        quiz_add_quiz_question($question->id, $quiz, 0, 1);
        rebuild_course_cache((int) $environment['course']->id, true);
        $quizcm = get_fast_modinfo($environment['course'])->get_cm($quiz->cmid);
        $quizitem = registry::enumerate($quizcm)[0];
        $quizview = $viewer->build(
            $quizcm,
            (int) $environment['course']->id,
            $quizitem->resourceid,
            'combines rows from two tables',
            \context_module::instance($quizcm->id)
        );
        $this->assertTrue($quizview['found']);
        $this->assertStringNotContainsString('SECRET_ATTEMPT', $quizview['html']);
        $this->assertStringNotContainsString('fraction', strtolower($quizview['html']));

        $book = $generator->create_module('book', ['course' => $environment['course']->id, 'name' => 'Distributed systems']);
        $chapter = $generator->get_plugin_generator('mod_book')->create_content($book, [
            'title' => 'Replication',
            'content' => '<p>Replication keeps a copy on another node.</p>',
        ]);
        rebuild_course_cache((int) $environment['course']->id, true);
        $bookcm = get_fast_modinfo($environment['course'])->get_cm($book->cmid);
        $bookitem = registry::enumerate($bookcm)[0];
        $bookview = $viewer->build(
            $bookcm,
            (int) $environment['course']->id,
            $bookitem->resourceid,
            'keeps a copy on another node',
            \context_module::instance($bookcm->id)
        );
        $this->assertTrue($bookview['found']);
        $this->assertStringContainsString('Replication', $bookview['provenance']);
        $this->assertNotEmpty($chapter->id);

        $assign = $generator->create_module('assign', [
            'course' => $environment['course']->id,
            'name' => 'Prototype',
            'intro' => '<p>Review the prototype with a participant.</p>',
        ]);
        $generator->get_plugin_generator('mod_assign')->create_submission([
            'userid' => $environment['student']->id,
            'cmid' => $assign->cmid,
            'onlinetext' => 'SECRET_SUBMISSION_TEXT',
        ]);
        $assigncm = get_fast_modinfo($environment['course'])->get_cm($assign->cmid);
        $assignitem = null;
        foreach (registry::enumerate($assigncm) as $item) {
            if ($item->resourcetype === 'assignment') {
                $assignitem = $item;
            }
        }
        $assignview = $viewer->build(
            $assigncm,
            (int) $environment['course']->id,
            $assignitem->resourceid,
            'Review the prototype',
            \context_module::instance($assigncm->id)
        );
        $this->assertTrue($assignview['found']);
        $this->assertStringNotContainsString('SECRET_SUBMISSION_TEXT', $assignview['html']);

        $lesson = $generator->create_module('lesson', ['course' => $environment['course']->id, 'name' => 'Threats']);
        $page = $generator->get_plugin_generator('mod_lesson')->create_content($lesson, [
            'title' => 'Phishing',
            'contents_editor' => ['text' => 'Phishing asks a person for a credential.', 'format' => FORMAT_HTML, 'itemid' => 0],
        ]);
        $answerid = $DB->insert_record('lesson_answers', (object) [
            'lessonid' => $lesson->id,
            'pageid' => $page->id,
            'jumpto' => 0,
            'grade' => 1,
            'score' => 5,
            'flags' => 0,
            'timecreated' => time(),
            'timemodified' => time(),
            'answer' => 'Teacher option',
            'answerformat' => FORMAT_HTML,
            'response' => '',
            'responseformat' => FORMAT_HTML,
        ]);
        $DB->insert_record('lesson_attempts', (object) [
            'lessonid' => $lesson->id,
            'pageid' => $page->id,
            'userid' => $environment['student']->id,
            'answerid' => $answerid,
            'retry' => 0,
            'correct' => 1,
            'useranswer' => 'SECRET_LESSON_ATTEMPT',
            'timeseen' => time(),
        ]);
        rebuild_course_cache((int) $environment['course']->id, true);
        $lessoncm = get_fast_modinfo($environment['course'])->get_cm($lesson->cmid);
        $lessonitem = registry::enumerate($lessoncm)[0];
        $lessonview = $viewer->build(
            $lessoncm,
            (int) $environment['course']->id,
            $lessonitem->resourceid,
            'asks a person for a credential',
            \context_module::instance($lessoncm->id)
        );
        $this->assertTrue($lessonview['found']);
        $this->assertStringNotContainsString('SECRET_LESSON_ATTEMPT', $lessonview['html']);
    }

    /**
     * File types use the extraction cache and name the page, slide or cue.
     *
     * @param string $filename The teacher file.
     * @param string $mimetype The stored type.
     * @param string $quote A quotation in the cached text.
     * @param array $segment Provenance for that quotation.
     * @param string $needle Text expected in the provenance label.
     */
    #[\PHPUnit\Framework\Attributes\DataProvider('file_provider')]
    public function test_file_source_uses_cache(string $filename, string $mimetype, string $quote, array $segment, string $needle): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $resource = $this->getDataGenerator()->create_module('resource', [
            'course' => $environment['course']->id,
            'name' => $filename,
        ]);
        $cm = get_fast_modinfo($environment['course'])->get_cm($resource->cmid);
        $context = \context_module::instance($cm->id);
        get_file_storage()->delete_area_files($context->id, 'mod_resource', 'content');
        $file = get_file_storage()->create_file_from_string([
            'contextid' => $context->id,
            'component' => 'mod_resource',
            'filearea' => 'content',
            'itemid' => 0,
            'filepath' => '/',
            'filename' => $filename,
            'mimetype' => $mimetype,
        ], 'teacher file bytes');
        $DB->insert_record('local_compalign_extract', (object) [
            'contenthash' => $file->get_contenthash(),
            'extractorversion' => file_item::EXTRACTOR_VERSION,
            'canonicaltext' => $segment['text'],
            'provenance' => json_encode([$segment]),
            'timecreated' => time(),
        ]);
        rebuild_course_cache((int) $environment['course']->id, true);
        $cm = get_fast_modinfo($environment['course'])->get_cm($resource->cmid);
        $item = registry::enumerate($cm)[0];
        $view = (new source_context())->build(
            $cm,
            (int) $environment['course']->id,
            $item->resourceid,
            $quote,
            $context
        );
        $this->assertTrue($view['found'], $filename);
        $this->assertStringContainsString('<mark>', $view['html']);
        $this->assertStringContainsString($needle, $view['provenance']);
        $this->assertStringNotContainsString('/var/', $view['openurl']);
    }

    /**
     * @return array<string, array>
     */
    public static function file_provider(): array {
        return [
            'pdf' => ['notes.pdf', 'application/pdf', 'releases are automated', [
                'kind' => 'page', 'number' => '2', 'text' => "releases are\nautomated",
            ], '2'],
            'docx' => ['notes.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'headings structure the text', [
                'kind' => 'paragraph', 'number' => '1', 'heading' => 'Scenario', 'text' => 'headings structure the text',
            ], 'Scenario'],
            'pptx' => ['slides.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'networks connect services', [
                'kind' => 'slide', 'number' => '3', 'text' => 'networks connect services',
            ], '3'],
            'vtt' => ['captions.vtt', 'text/vtt', 'models read the transcript', [
                'kind' => 'cue', 'start' => '00:00:01.000', 'end' => '00:00:04.000', 'text' => 'models read the transcript',
            ], '00:00:01.000'],
        ];
    }
}
