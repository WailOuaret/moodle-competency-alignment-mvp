<?php
// Create the pilot course "Competency Alignment Pilot" (COMPALIGN-PILOT) and its sample Pages.
// Idempotent: a course or a Page that is already there is left alone.
//
// The course is private. Self enrolment and guest access are switched off. People are added
// by an administrator only (see teachers.php).

require(__DIR__ . '/_bootstrap.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');

const PILOT_COURSE_SHORTNAME = 'COMPALIGN-PILOT';

$summary = '<p>A private course for the teacher pilot of the Competency Alignment Assistant. '
    . 'It holds a few sample Pages. Ask the assistant for competency suggestions on a Page, '
    . 'then accept, reject or modify each suggestion. Nothing you do here writes to Moodle competency links.</p>';

$course = $DB->get_record('course', ['shortname' => PILOT_COURSE_SHORTNAME]);
if (!$course) {
    $course = create_course((object) [
        'fullname' => 'Competency Alignment Pilot',
        'shortname' => PILOT_COURSE_SHORTNAME,
        'idnumber' => PILOT_COURSE_SHORTNAME,
        'category' => core_course_category::get_default()->id,
        'format' => 'topics',
        'visible' => 1,
        'summary' => $summary,
        'summaryformat' => FORMAT_HTML,
        'startdate' => time(),
    ]);
    pilot_say('course: created (id ' . $course->id . ')');
} else {
    pilot_say('course: already present (id ' . $course->id . '), left unchanged');
}

// Nobody joins by themselves and there is no guest access.
foreach (['self', 'guest'] as $method) {
    $DB->set_field('enrol', 'status', ENROL_INSTANCE_DISABLED, ['courseid' => $course->id, 'enrol' => $method]);
}

$pages = json_decode(file_get_contents('/opt/pilot/content/pages/pages.json'), true, 512, JSON_THROW_ON_ERROR);
$moduleid = $DB->get_field('modules', 'id', ['name' => 'page'], MUST_EXIST);
$created = 0;
foreach ($pages as $page) {
    if ($DB->record_exists('course_modules', ['course' => $course->id, 'idnumber' => $page['idnumber']])) {
        continue;
    }
    $html = file_get_contents('/opt/pilot/content/pages/' . $page['file']);
    if ($html === false || trim($html) === '') {
        pilot_say('course: the content file ' . $page['file'] . ' is empty or missing');
        exit(1);
    }
    add_moduleinfo((object) [
        'modulename' => 'page',
        'module' => $moduleid,
        'course' => $course->id,
        'section' => 1,
        'visible' => 1,
        'visibleoncoursepage' => 1,
        'cmidnumber' => $page['idnumber'],
        'name' => $page['name'],
        'intro' => '<p>' . s($page['intro']) . '</p>',
        'introformat' => FORMAT_HTML,
        // page_add_instance copies page[text] only when a form is passed. add_moduleinfo
        // does not pass one, so the columns are set here as well.
        'content' => $html,
        'contentformat' => FORMAT_HTML,
        'page' => ['text' => $html, 'format' => FORMAT_HTML, 'itemid' => 0],
        'display' => 5,
        'printintro' => 0,
        'printlastmodified' => 1,
        'revision' => 1,
    ], $course);
    $created++;
}
pilot_say('course: ' . $created . ' Page(s) created, ' . count($pages) . ' in the sample set');
rebuild_course_cache($course->id, true);
