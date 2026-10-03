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

namespace local_compalign\fixtures;

use local_compalign\service\analysis_manager;
use local_compalign\service\competency_catalogue;

/**
 * Builds the Moodle objects the plugin works with: a course, a teacher, a Page and a framework.
 *
 * Used by test cases, which supply getDataGenerator().
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
trait environment {
    /**
     * Create a course with a teacher and a Page, and select a framework in the plugin settings.
     *
     * The framework has a parent T1, its child T1_1, and an unrelated competency T2.
     *
     * @param string $suffix Added to the framework ID number, so a test can build a second environment.
     * @return array{course: \stdClass, teacher: \stdClass, student: \stdClass, page: \stdClass, cm: \cm_info,
     *         framework: \core_competency\competency_framework, competencies: array<string, \core_competency\competency>}
     */
    protected function create_environment(string $suffix = ''): array {
        $generator = $this->getDataGenerator();

        $course = $generator->create_course();
        $teacher = $generator->create_and_enrol($course, 'editingteacher');
        $student = $generator->create_and_enrol($course, 'student');
        $page = $generator->create_module('page', [
            'course' => $course->id,
            'name' => 'Software testing',
            'intro' => '',
            'content' => '<p>Unit tests check one function at a time.</p>'
                . '<p>Integration tests check how the parts of a program work together.</p>',
        ]);

        // The teacher is the one who asks for analyses, so the Page is read as they see it.
        $this->setUser($teacher);
        $cm = get_fast_modinfo($course)->get_cm((int) $page->cmid);

        $competencygenerator = $generator->get_plugin_generator('core_competency');
        $framework = $competencygenerator->create_framework([
            'shortname' => 'Test framework' . $suffix,
            'idnumber' => 'TF' . $suffix,
        ]);
        $frameworkid = $framework->get('id');

        $competencies = [];
        $competencies['T1'] = $competencygenerator->create_competency([
            'competencyframeworkid' => $frameworkid,
            'idnumber' => 'T1',
            'shortname' => 'Verify software',
            'description' => 'Plan and run tests that verify software.',
        ]);
        $competencies['T1_1'] = $competencygenerator->create_competency([
            'competencyframeworkid' => $frameworkid,
            'idnumber' => 'T1_1',
            'shortname' => 'Unit testing',
            'description' => 'Write unit tests for single functions.',
            'parentid' => $competencies['T1']->get('id'),
        ]);
        $competencies['T2'] = $competencygenerator->create_competency([
            'competencyframeworkid' => $frameworkid,
            'idnumber' => 'T2',
            'shortname' => 'Deploy software',
            'description' => 'Release software to production.',
        ]);

        set_config('frameworkid', $frameworkid, 'local_compalign');
        set_config('maxsuggestions', 3, 'local_compalign');

        return [
            'course' => $course,
            'teacher' => $teacher,
            'student' => $student,
            'page' => $page,
            'cm' => $cm,
            'framework' => $framework,
            'competencies' => $competencies,
        ];
    }

    /**
     * An analysis manager that talks to a stub of the service.
     *
     * @param array $queue What the fake network answers, in order. Defaults to one valid analysis.
     * @return analysis_manager
     */
    protected function create_manager(array $queue = []): analysis_manager {
        $queue = $queue ?: [service_stub::answer_analysis()];

        return new analysis_manager(static fn() => service_stub::client($queue));
    }

    /**
     * Request and run an analysis of a Page, and return it with its suggestions.
     *
     * @param array $environment As returned by create_environment().
     * @param array $override Values that replace the ones of the stub's answer.
     * @return array{analysis: \stdClass, suggestions: \stdClass[], catalogue: \local_compalign\service\catalogue_snapshot}
     */
    protected function create_completed_analysis(array $environment, array $override = []): array {
        $manager = $this->create_manager([service_stub::answer_analysis($override)]);

        $requested = $manager->request_analysis($environment['cm'], (int) $environment['teacher']->id);
        $manager->run((int) $requested['analysis']->id);

        $analysis = $manager->get_latest((int) $environment['cm']->id);

        return [
            'analysis' => $analysis,
            'suggestions' => $manager->get_suggestions((int) $analysis->id),
            'catalogue' => (new competency_catalogue((int) $analysis->frameworkid))->build(),
        ];
    }
}
