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

use local_compalign\fixtures\environment;
use local_compalign\output\dashboard;
use local_compalign\service\analysis_manager;
use local_compalign\service\competency_catalogue;
use local_compalign\service\resource_extractor;
use mod_quiz\quiz_settings;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Generator coverage for the resource adapters and the stale state a teacher sees.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[\PHPUnit\Framework\Attributes\CoversClass(\local_compalign\resource\registry::class)]
final class adapters_test extends \advanced_testcase {
    use environment;

    /**
     * A quiz lists each supported question and leaves a random slot unsupported.
     */
    public function test_quiz_questions_are_separate_resources(): void {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/mod/quiz/locallib.php');

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $generator = $this->getDataGenerator();
        $quiz = $generator->create_module('quiz', [
            'course' => $environment['course']->id,
            'name' => 'Quiz 1',
        ]);
        $qgen = $generator->get_plugin_generator('core_question');
        $context = \context_module::instance($quiz->cmid);
        $category = $qgen->create_question_category(['contextid' => $context->id]);
        $types = [
            'multichoice' => ['which' => 'one_of_four', 'name' => 'Normal forms'],
            'truefalse' => ['which' => null, 'name' => 'A key is unique'],
            'shortanswer' => ['which' => null, 'name' => 'Name the key'],
            'numerical' => ['which' => null, 'name' => 'How many normal forms'],
            'essay' => ['which' => null, 'name' => 'Explain a transaction'],
            'match' => ['which' => null, 'name' => 'Match the terms'],
        ];
        $created = [];
        foreach ($types as $qtype => $spec) {
            $created[$qtype] = $qgen->create_question($qtype, $spec['which'], [
                'category' => $category->id,
                'name' => $spec['name'],
                'questiontext' => ['text' => 'Teacher stem for ' . $spec['name'] . '.', 'format' => FORMAT_HTML],
            ]);
            quiz_add_quiz_question($created[$qtype]->id, $quiz, 0, 1);
        }
        $randomcategory = $qgen->create_question_category(['contextid' => $context->id]);
        $qgen->create_question('truefalse', null, ['category' => $randomcategory->id]);
        $quizobj = quiz_settings::create($quiz->id);
        $quizobj->get_structure()->add_random_questions(0, 1, [
            'filter' => [
                'category' => [
                    'jointype' => \core_question\local\bank\condition::JOINTYPE_DEFAULT,
                    'values' => [$randomcategory->id],
                    'filteroptions' => ['includesubcategories' => false],
                ],
            ],
        ]);

        $student = $environment['student'];
        $student->firstname = 'Secretfirst';
        $student->lastname = 'Secretlast';
        $student->email = 'secret.student@example.invalid';
        user_update_user($student, false);
        $DB->insert_record('quiz_grades', (object) [
            'quiz' => $quiz->id,
            'userid' => $student->id,
            'grade' => 17,
            'timemodified' => time(),
        ]);

        $this->setUser($environment['teacher']);
        $cm = get_fast_modinfo($environment['course'])->get_cm($quiz->cmid);
        $items = \local_compalign\resource\registry::enumerate($cm);
        $supported = array_values(array_filter($items, static fn($item): bool => $item->supported));
        $unsupported = array_values(array_filter($items, static fn($item): bool => !$item->supported));

        $this->assertCount(6, $supported);
        $this->assertCount(1, $unsupported);
        $this->assertSame('unsupportedquestion', $unsupported[0]->reason);
        $this->assertStringContainsString(':slot:', $unsupported[0]->resourceid);

        $blob = '';
        foreach ($supported as $item) {
            $this->assertStringContainsString(':question:', $item->resourceid);
            $extracted = (new resource_extractor())->extract($cm, $item->resourceid);
            $blob .= json_encode($extracted);
            $this->assertSame('quiz_question', $extracted['resource']['resource_type']);
            $this->assertSame('quiz_question', $extracted['provenance']['kind']);
            $this->assertStringContainsString('Quiz 1, question', $extracted['provenance']['label']);
        }
        $this->assertStringNotContainsString('Secretfirst', $blob);
        $this->assertStringNotContainsString('Secretlast', $blob);
        $this->assertStringNotContainsString('secret.student@example.invalid', $blob);
        $this->assertStringNotContainsString('SECRET_QUIZ_ANSWER', $blob);

        $short = null;
        foreach ($supported as $item) {
            if (str_contains($item->title, 'Name the key')) {
                $short = (new resource_extractor())->extract($cm, $item->resourceid);
            }
        }
        $this->assertNotNull($short);
        $this->assertStringNotContainsString('fraction', $short['resource']['text']);

        $before = (new resource_extractor())->extract($cm, $supported[0]->resourceid);
        $qgen->update_question($created['multichoice'], null, [
            'questiontext' => ['text' => 'A revised stem about isolation levels.', 'format' => FORMAT_HTML],
        ]);
        get_fast_modinfo($environment['course'], 0, true);
        $cm = get_fast_modinfo($environment['course'])->get_cm($quiz->cmid);
        $afteritems = registry::enumerate($cm);
        $afterids = array_map(static fn($item): string => $item->resourceid, $afteritems);
        $this->assertNotContains($before['resource']['resource_id'], $afterids);
    }

    /**
     * Editing a question without a new version makes the stored analysis stale.
     */
    public function test_quiz_text_edit_makes_the_analysis_stale(): void {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/mod/quiz/locallib.php');

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $quiz = $this->getDataGenerator()->create_module('quiz', [
            'course' => $environment['course']->id,
            'name' => 'Quiz 1',
        ]);
        $qgen = $this->getDataGenerator()->get_plugin_generator('core_question');
        $category = $qgen->create_question_category([
            'contextid' => \context_module::instance($quiz->cmid)->id,
        ]);
        $question = $qgen->create_question('essay', null, [
            'category' => $category->id,
            'name' => 'Explain a transaction',
            'questiontext' => ['text' => 'Explain what a transaction groups together.', 'format' => FORMAT_HTML],
        ]);
        quiz_add_quiz_question($question->id, $quiz);
        $cm = get_fast_modinfo($environment['course'])->get_cm($quiz->cmid);
        $item = registry::enumerate($cm)[0];
        $extracted = (new resource_extractor())->extract($cm, $item->resourceid);
        $this->seed_completed($cm, $extracted, 'quiz_question');

        $DB->set_field('question', 'questiontext', '<p>A different explanation is required.</p>', ['id' => $question->id]);
        \question_bank::notify_question_edited($question->id);
        $this->assert_stale($environment, $cm->id, $item->resourceid);
    }

    /**
     * Files are enumerated by type, and a replaced file makes the old analysis stale.
     */
    public function test_files_and_folder_children(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $courseid = $environment['course']->id;
        $resource = $this->getDataGenerator()->create_module('resource', [
            'course' => $courseid,
            'name' => 'Notes',
        ]);
        $cm = get_fast_modinfo($environment['course'])->get_cm($resource->cmid);
        $context = \context_module::instance($cm->id);
        get_file_storage()->delete_area_files($context->id, 'mod_resource', 'content');
        $file = $this->add_file($cm, 'mod_resource', 'content', 'notes.txt', 'Plain teacher notes.', 'text/plain');
        $items = registry::enumerate($cm);
        $this->assertCount(1, $items);
        $this->assertTrue($items[0]->supported);
        $this->assertSame('text', $items[0]->resourcetype);
        $this->assertSame('moodle:file:' . $file->get_id(), $items[0]->resourceid);
        $extracted = (new resource_extractor())->extract($cm, $items[0]->resourceid);
        $this->assertSame($file->get_contenthash(), $extracted['resource']['content_hash']);
        $this->assertSame('Notes, notes.txt', $extracted['provenance']['label']);
        $this->seed_completed($cm, $extracted, 'text');
        $DB->set_field('files', 'contenthash', hash('sha1', 'replaced-notes'), ['id' => $file->get_id()]);
        $this->assert_stale($environment, $cm->id, $items[0]->resourceid);

        $folder = $this->getDataGenerator()->create_module('folder', [
            'course' => $courseid,
            'name' => 'Week 4 Resources',
        ]);
        $foldercm = get_fast_modinfo($environment['course'])->get_cm($folder->cmid);
        $this->add_file($foldercm, 'mod_folder', 'content', 'database.pdf', '%PDF-1.4 teacher', 'application/pdf');
        $this->add_file($foldercm, 'mod_folder', 'content', 'slides.pptx', 'PK teacher', 'application/vnd.openxmlformats-officedocument.presentationml.presentation');
        $this->add_file($foldercm, 'mod_folder', 'content', 'old.doc', 'legacy', 'application/msword');
        $this->add_file($foldercm, 'mod_folder', 'content', 'spoof.pdf', 'not a pdf', 'text/plain');
        $children = registry::enumerate($foldercm);
        $byname = [];
        foreach ($children as $child) {
            $byname[$child->title] = $child;
        }
        $this->assertTrue($byname['database.pdf']->supported);
        $this->assertTrue($byname['slides.pptx']->supported);
        $this->assertFalse($byname['old.doc']->supported);
        $this->assertSame('legacyoffice', $byname['old.doc']->reason);
        $this->assertFalse($byname['spoof.pdf']->supported);
        $this->assertSame('mimemismatch', $byname['spoof.pdf']->reason);
        $blob = json_encode($children);
        $this->assertStringNotContainsString('Week 4 Resources', $byname['database.pdf']->title);
    }

    /**
     * Visible book chapters are resources. A hidden chapter is omitted. An edit is stale.
     */
    public function test_book_chapters(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $book = $this->getDataGenerator()->create_module('book', [
            'course' => $environment['course']->id,
            'name' => 'Database Design',
        ]);
        $bookgen = $this->getDataGenerator()->get_plugin_generator('mod_book');
        $visible = $bookgen->create_content($book, [
            'title' => 'Normalization',
            'content' => '<p>Normalization removes redundancy.</p>',
        ]);
        $hidden = $bookgen->create_content($book, [
            'title' => 'Hidden draft',
            'content' => '<p>SECRET_HIDDEN_CHAPTER</p>',
            'hidden' => 1,
        ]);
        $cm = get_fast_modinfo($environment['course'])->get_cm($book->cmid);
        $items = registry::enumerate($cm);
        $this->assertCount(1, $items);
        $this->assertSame('moodle:book:' . $book->id . ':chapter:' . $visible->id, $items[0]->resourceid);
        $extracted = (new resource_extractor())->extract($cm, $items[0]->resourceid);
        $this->assertStringContainsString('removes redundancy', $extracted['resource']['text']);
        $this->assertStringNotContainsString('SECRET_HIDDEN_CHAPTER', $extracted['resource']['text']);
        $this->assertSame('book_chapter', $extracted['provenance']['kind']);
        $this->assertStringContainsString('Normalization', $extracted['provenance']['label']);
        $this->seed_completed($cm, $extracted, 'book_chapter');
        $DB->set_field('book_chapters', 'content', '<p>A revised chapter.</p>', ['id' => $visible->id]);
        $this->assert_stale($environment, $cm->id, $items[0]->resourceid);
        $this->assertNotEmpty($hidden->id);
    }

    /**
     * Assignment instructions are read. Submissions, feedback and grades are not.
     */
    public function test_assignment_ignores_student_work(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $assign = $this->getDataGenerator()->create_module('assign', [
            'course' => $environment['course']->id,
            'name' => 'Schema task',
            'intro' => '<p>Write a relational schema for a library.</p>',
            'assignsubmission_onlinetext_enabled' => 1,
        ]);
        $this->add_file(
            get_fast_modinfo($environment['course'])->get_cm($assign->cmid),
            'mod_assign',
            'introattachment',
            'brief.txt',
            'Teacher attachment text.',
            'text/plain'
        );
        $this->getDataGenerator()->get_plugin_generator('mod_assign')->create_submission([
            'userid' => $environment['student']->id,
            'cmid' => $assign->cmid,
            'onlinetext' => 'SECRET_SUBMISSION_TEXT',
        ]);
        $DB->insert_record('assign_grades', (object) [
            'assignment' => $assign->id,
            'userid' => $environment['student']->id,
            'timecreated' => time(),
            'timemodified' => time(),
            'grader' => $environment['teacher']->id,
            'grade' => 88,
            'penalty' => 0,
            'attemptnumber' => 0,
        ]);

        $this->setUser($environment['teacher']);
        $cm = get_fast_modinfo($environment['course'])->get_cm($assign->cmid);
        $items = registry::enumerate($cm);
        $blob = '';
        $sawfile = false;
        foreach ($items as $item) {
            if (!$item->supported) {
                continue;
            }
            $extracted = (new resource_extractor())->extract($cm, $item->resourceid);
            $blob .= json_encode($extracted);
            if ($item->resourcetype === 'text') {
                $sawfile = true;
                $this->assertStringContainsString('brief.txt', $extracted['provenance']['label']);
            }
        }
        $this->assertTrue($sawfile);
        $this->assertStringContainsString('relational schema', $blob);
        $this->assertStringContainsString('brief.txt', $blob);
        $this->assertStringNotContainsString('SECRET_SUBMISSION_TEXT', $blob);
        $this->assertStringNotContainsString($environment['student']->email, $blob);

        $intro = null;
        foreach ($items as $item) {
            if ($item->resourcetype === 'assignment') {
                $intro = $item;
            }
        }
        $extracted = (new resource_extractor())->extract($cm, $intro->resourceid);
        $this->seed_completed($cm, $extracted, 'assignment');
        $DB->set_field('assign', 'intro', '<p>A revised instruction.</p>', ['id' => $assign->id]);
        $this->assert_stale($environment, $cm->id, $intro->resourceid);
    }

    /**
     * A lesson page includes the teacher answer text and not the attempt or the score.
     */
    public function test_lesson_page_ignores_attempts(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $lesson = $this->getDataGenerator()->create_module('lesson', [
            'course' => $environment['course']->id,
            'name' => 'Transactions lesson',
        ]);
        $page = $this->getDataGenerator()->get_plugin_generator('mod_lesson')->create_content($lesson, [
            'title' => 'Commit',
            'contents_editor' => [
                'text' => 'A commit makes the changes durable.',
                'format' => FORMAT_HTML,
                'itemid' => 0,
            ],
        ]);
        $answerid = $DB->insert_record('lesson_answers', (object) [
            'lessonid' => $lesson->id,
            'pageid' => $page->id,
            'jumpto' => 0,
            'grade' => 1,
            'score' => 77,
            'flags' => 0,
            'timecreated' => time(),
            'timemodified' => time(),
            'answer' => 'Teacher choice alpha',
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
            'correct' => 0,
            'useranswer' => 'SECRET_LESSON_ATTEMPT',
            'timeseen' => time(),
        ]);

        $this->setUser($environment['teacher']);
        $cm = get_fast_modinfo($environment['course'])->get_cm($lesson->cmid);
        $items = registry::enumerate($cm);
        $this->assertCount(1, $items);
        $extracted = (new resource_extractor())->extract($cm, $items[0]->resourceid);
        $this->assertStringContainsString('makes the changes durable', $extracted['resource']['text']);
        $this->assertStringContainsString('Teacher choice alpha', $extracted['resource']['text']);
        $this->assertStringNotContainsString('SECRET_LESSON_ATTEMPT', $extracted['resource']['text']);
        $this->assertStringNotContainsString('77', $extracted['resource']['text']);
        $this->assertSame('lesson_page', $extracted['provenance']['kind']);
        $this->assertStringContainsString('Commit', $extracted['provenance']['label']);
        $this->seed_completed($cm, $extracted, 'lesson_page');
        $DB->set_field('lesson_pages', 'contents', 'A different lesson page.', ['id' => $page->id]);
        $this->assert_stale($environment, $cm->id, $items[0]->resourceid);
    }

    /**
     * A label, a forum introduction and a URL description are teacher text only.
     */
    public function test_label_forum_and_url_stay_on_teacher_text(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $courseid = $environment['course']->id;
        $label = $this->getDataGenerator()->create_module('label', [
            'course' => $courseid,
            'intro' => '<p>Teacher media note about indexes.</p>',
        ]);
        $forum = $this->getDataGenerator()->create_module('forum', [
            'course' => $courseid,
            'name' => 'Course forum',
            'intro' => '<p>Use this forum for questions about the course.</p>',
        ]);
        $this->getDataGenerator()->get_plugin_generator('mod_forum')->create_post([
            'discussion' => $this->getDataGenerator()->get_plugin_generator('mod_forum')->create_discussion([
                'course' => $courseid,
                'forum' => $forum->id,
                'userid' => $environment['teacher']->id,
                'name' => 'Welcome',
                'message' => 'Welcome thread',
            ])->id,
            'userid' => $environment['student']->id,
            'message' => 'SECRET_FORUM_POST',
        ]);
        $url = $this->getDataGenerator()->create_module('url', [
            'course' => $courseid,
            'name' => 'Further reading',
            'intro' => '<p>See the course handbook section on keys.</p>',
            'externalurl' => 'http://127.0.0.1/should-not-be-fetched',
        ]);

        $this->setUser($environment['teacher']);
        $modinfo = get_fast_modinfo($environment['course']);
        $labeltext = (new resource_extractor())->extract($modinfo->get_cm($label->cmid));
        $this->assertStringContainsString('indexes', $labeltext['resource']['text']);

        $forumcm = $modinfo->get_cm($forum->cmid);
        $forumitems = registry::enumerate($forumcm);
        $this->assertSame('Forum posts are not analysed in this release.', $forumitems[0]->provenance);
        $forumtext = (new resource_extractor())->extract($forumcm, $forumitems[0]->resourceid);
        $this->assertStringContainsString('questions about the course', $forumtext['resource']['text']);
        $this->assertStringNotContainsString('SECRET_FORUM_POST', json_encode($forumtext));

        $urlcm = $modinfo->get_cm($url->cmid);
        $urlitems = registry::enumerate($urlcm);
        $this->assertSame('Linked webpage content is not fetched.', $urlitems[0]->provenance);
        $urltext = (new resource_extractor())->extract($urlcm, $urlitems[0]->resourceid);
        $this->assertStringContainsString('course handbook', $urltext['resource']['text']);
        $this->assertStringNotContainsString('should-not-be-fetched', $urltext['resource']['text']);
    }

    /**
     * Page, document and transcript edits are stale on the dashboard.
     *
     * @param string $filename The teacher file.
     * @param string $mimetype Moodle's stored type.
     * @param string $type The service type.
     */
    #[DataProvider('stale_file_provider')]
    public function test_replaced_file_is_stale(string $filename, string $mimetype, string $type): void {
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
        $file = $this->add_file($cm, 'mod_resource', 'content', $filename, 'Original teacher text.', $mimetype);
        $item = registry::enumerate($cm)[0];
        $this->assertTrue($item->supported, $filename);
        $extracted = (new resource_extractor())->extract($cm, $item->resourceid);
        $this->assertSame($type, $extracted['resource']['resource_type']);
        $this->seed_completed($cm, $extracted, $type);
        $DB->set_field('files', 'contenthash', hash('sha1', 'replaced-' . $filename), ['id' => $file->get_id()]);
        $this->assert_stale($environment, $cm->id, $item->resourceid);
    }

    /**
     * @return array<string, array>
     */
    public static function stale_file_provider(): array {
        return [
            'pdf' => ['database.pdf', 'application/pdf', 'pdf'],
            'docx' => ['requirements.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx'],
            'pptx' => ['lecture.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'pptx'],
            'markdown' => ['notes.md', 'text/markdown', 'markdown'],
            'vtt' => ['captions.vtt', 'text/vtt', 'transcript'],
            'srt' => ['captions.srt', 'text/plain', 'transcript'],
        ];
    }

    /**
     * The same file bytes are extracted once. A new extractor version is not reused.
     */
    public function test_extraction_cache_is_keyed_by_hash_and_version(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $resource = $this->getDataGenerator()->create_module('resource', [
            'course' => $environment['course']->id,
            'name' => 'database.pdf',
        ]);
        $cm = get_fast_modinfo($environment['course'])->get_cm($resource->cmid);
        $context = \context_module::instance($cm->id);
        get_file_storage()->delete_area_files($context->id, 'mod_resource', 'content');
        $this->add_file($cm, 'mod_resource', 'content', 'database.pdf', '%PDF-1.4 synthetic', 'application/pdf');
        $item = registry::enumerate($cm)[0];

        $extraction = \local_compalign\fixtures\service_stub::json(200, [
            'text' => 'Transactions protect groups of related operations.',
            'segments' => [[
                'kind' => 'page',
                'number' => '4',
                'text' => 'Transactions protect groups of related operations.',
            ]],
        ]);
        $transport = null;
        $client = \local_compalign\fixtures\service_stub::client([
            $extraction,
            \local_compalign\fixtures\service_stub::answer_analysis(),
            \local_compalign\fixtures\service_stub::answer_analysis(),
            $extraction,
            \local_compalign\fixtures\service_stub::answer_analysis(),
        ], $transport);
        $manager = new analysis_manager(static fn() => $client);

        $first = $manager->request_analysis($cm, (int) $environment['teacher']->id, false, $item->resourceid);
        $manager->run((int) $first['analysis']->id);
        $this->assertSame(1, $DB->count_records('local_compalign_extract'));

        $second = $manager->request_analysis($cm, (int) $environment['teacher']->id, true, $item->resourceid);
        $manager->run((int) $second['analysis']->id);
        $this->assertSame(1, $DB->count_records('local_compalign_extract'));

        $DB->set_field('local_compalign_extract', 'extractorversion', '0.9');
        $third = $manager->request_analysis($cm, (int) $environment['teacher']->id, true, $item->resourceid);
        $manager->run((int) $third['analysis']->id);
        $this->assertSame(2, $DB->count_records('local_compalign_extract'));

        $paths = array_column($transport->requests, 'path');
        $this->assertSame(2, count(array_filter($paths, static fn(string $path): bool => $path === '/v1/extractions')));
        $this->assertSame(3, count(array_filter($paths, static fn(string $path): bool => $path === '/v1/analyses')));
    }

    /**
     * Editing the Page body makes the completed analysis stale.
     */
    public function test_page_edit_is_stale(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $extracted = (new resource_extractor())->extract($environment['cm']);
        $this->seed_completed($environment['cm'], $extracted, 'page');
        $DB->set_field('page', 'content', '<p>A rewritten page about something else.</p>', [
            'id' => $environment['page']->id,
        ]);
        $this->assert_stale($environment, (int) $environment['cm']->id, $extracted['resource']['resource_id']);
    }

    /**
     * @param \cm_info $cm The activity.
     * @param string $component The file component.
     * @param string $area The file area.
     * @param string $filename The file name.
     * @param string $content The bytes.
     * @param string $mimetype The stored MIME type.
     * @return \stored_file
     */
    private function add_file(
        \cm_info $cm,
        string $component,
        string $area,
        string $filename,
        string $content,
        string $mimetype
    ): \stored_file {
        return get_file_storage()->create_file_from_string([
            'contextid' => \context_module::instance($cm->id)->id,
            'component' => $component,
            'filearea' => $area,
            'itemid' => 0,
            'filepath' => '/',
            'filename' => $filename,
            'mimetype' => $mimetype,
        ], $content);
    }

    /**
     * Store a completed analysis for the current fingerprint.
     *
     * @param \cm_info $cm The activity.
     * @param array $extracted The adapter result.
     * @param string $type The resource type.
     */
    private function seed_completed(\cm_info $cm, array $extracted, string $type): void {
        global $DB, $USER;

        $catalogue = (new competency_catalogue())->build();
        $DB->insert_record('local_compalign_analysis', (object) [
            'courseid' => $cm->course,
            'cmid' => $cm->id,
            'resourceid' => $extracted['resource']['resource_id'],
            'sourceitemid' => $extracted['resource']['resource_id'],
            'extractorversion' => $extracted['resource']['extractor_version'] ?? '',
            'resourcetype' => $type,
            'researchstatus' => 'development',
            'resourcehash' => $extracted['hash'],
            'cataloguehash' => $catalogue->hash,
            'frameworkid' => $catalogue->frameworkid,
            'status' => analysis_manager::STATUS_COMPLETED,
            'requestedby' => $USER->id,
            'topk' => 5,
            'maxsuggestions' => 3,
            'abstained' => 0,
            'timecreated' => time(),
            'timecompleted' => time(),
        ]);
    }

    /**
     * The dashboard and the review change check both call the current analysis stale.
     *
     * @param array $environment The course fixture.
     * @param int $cmid The activity.
     * @param string $resourceid The item.
     */
    private function assert_stale(array $environment, int $cmid, string $resourceid): void {
        $course = $environment['course'];
        get_fast_modinfo($course, 0, true);
        $cm = get_fast_modinfo($course)->get_cm($cmid);
        $analysis = (new analysis_manager())->get_latest($cmid, $resourceid);
        $changes = (new analysis_manager())->find_changes($analysis, $cm, (new competency_catalogue())->build());
        $this->assertContains(analysis_manager::CHANGE_PAGE, $changes);

        $exported = dashboard::create($course, (int) $environment['teacher']->id)
            ->export_for_template($this->renderer());
        $matched = false;
        foreach ($exported['rows'] as $row) {
            if ($row['resourceid'] === $resourceid) {
                $matched = true;
                $this->assertSame('stale', $row['statuskey']);
            }
        }
        $this->assertTrue($matched);
    }

    /**
     * @return \core\output\renderer_base
     */
    private function renderer(): \core\output\renderer_base {
        global $PAGE;
        $PAGE->set_url('/');
        return $PAGE->get_renderer('core');
    }
}
