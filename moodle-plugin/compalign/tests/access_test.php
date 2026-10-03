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

namespace local_compalign;

use advanced_testcase;
use PHPUnit\Framework\Attributes\CoversNothing;

/**
 * Tests for who may do what with the plugin, as the capability definitions grant it.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversNothing]
final class access_test extends advanced_testcase {
    /**
     * In a course, teachers can use the assistant, managers can only look, and students have nothing.
     */
    public function test_course_capabilities_follow_the_roles(): void {
        $this->resetAfterTest();
        $generator = $this->getDataGenerator();
        $course = $generator->create_course();
        $users = [
            'editingteacher' => $generator->create_and_enrol($course, 'editingteacher'),
            'teacher' => $generator->create_and_enrol($course, 'teacher'),
            'student' => $generator->create_and_enrol($course, 'student'),
            'manager' => $generator->create_user(),
        ];
        $generator->role_assign('manager', $users['manager']->id);
        $context = \context_course::instance($course->id);

        $expected = [
            'local/compalign:view' => ['editingteacher' => true, 'teacher' => true, 'manager' => true, 'student' => false],
            'local/compalign:analyse' => ['editingteacher' => true, 'teacher' => true, 'manager' => false, 'student' => false],
            'local/compalign:review' => ['editingteacher' => true, 'teacher' => true, 'manager' => false, 'student' => false],
            // Nobody has it by default: write-back has to be granted on purpose.
            'local/compalign:writeback' => ['editingteacher' => false, 'teacher' => false, 'manager' => false, 'student' => false],
        ];

        foreach ($expected as $capability => $byrole) {
            foreach ($byrole as $role => $allowed) {
                $this->assertSame($allowed, has_capability($capability, $context, $users[$role]), "$role: $capability");
            }
        }
    }

    /**
     * Site-wide capabilities belong to managers only.
     */
    public function test_site_capabilities_belong_to_managers(): void {
        $this->resetAfterTest();
        $generator = $this->getDataGenerator();
        $course = $generator->create_course();
        $teacher = $generator->create_and_enrol($course, 'editingteacher');
        $manager = $generator->create_user();
        $generator->role_assign('manager', $manager->id);
        $context = \context_system::instance();

        foreach (['local/compalign:manage', 'local/compalign:viewallreviews'] as $capability) {
            $this->assertTrue(has_capability($capability, $context, $manager), $capability);
            $this->assertFalse(has_capability($capability, $context, $teacher), $capability);
        }
    }
}
