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

require_once(__DIR__ . '/../fixtures/fake_transport.php');
require_once(__DIR__ . '/../fixtures/service_stub.php');
require_once(__DIR__ . '/../fixtures/environment.php');

/**
 * Study export rows for reviews and teacher-added competencies.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[\PHPUnit\Framework\Attributes\CoversClass(study_export::class)]
final class manual_export_test extends \advanced_testcase {
    use environment;

    /**
     * Accept, reject, modify and teacher-added rows keep their sources and hide the user id.
     */
    public function test_export_includes_relationship_sources(): void {
        $this->resetAfterTest();
        set_config('studyphase', study_phase::PILOT, 'local_compalign');
        $environment = $this->create_environment();
        $environment['teacher']->idnumber = 'T004';
        user_update_user($environment['teacher'], false);
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $proposed = (string) $suggestion->competencyidnumber;
        $replacement = $proposed === 'T2' ? 'T1' : 'T2';
        $reviews = new review_manager();
        $export = new study_export();
        $courseid = (int) $environment['course']->id;
        $reviews->save($made['analysis'], $suggestion, (int) $environment['teacher']->id, 'reject', null, null, 'no', null, $made['catalogue']);
        $rejected = $export->rows(['courseid' => $courseid]);
        $this->assertSame('', $rejected[0]['relationship_source']);
        $this->assertSame('reject', $rejected[0]['decision']);

        $reviews->save($made['analysis'], $suggestion, (int) $environment['teacher']->id, 'accept', null, null, 'yes', null, $made['catalogue']);
        $accepted = $export->rows(['courseid' => $courseid]);
        $this->assertSame(relationship_index::EXPORT_ACCEPTED, $accepted[0]['relationship_source']);
        $this->assertSame($proposed, $accepted[0]['final_competency']);

        $reviews->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'modify',
            $replacement,
            null,
            'changed',
            null,
            $made['catalogue']
        );

        $packed = (new resource_extractor())->extract($environment['cm'], 'moodle:page:' . $environment['page']->id);
        $added = (new manual_relationship())->add(
            $environment['cm'],
            'moodle:page:' . $environment['page']->id,
            (int) $environment['course']->id,
            (int) $environment['teacher']->id,
            'T1_1',
            $packed['hash'],
            'Unit tests check one function at a time.',
            'Also relevant',
            \context_module::instance($environment['cm']->id)
        );
        (new manual_relationship())->remove(
            (int) $added->id,
            $environment['cm'],
            (int) $environment['teacher']->id,
            \context_module::instance($environment['cm']->id)
        );
        $kept = (new manual_relationship())->add(
            $environment['cm'],
            'moodle:page:' . $environment['page']->id,
            (int) $environment['course']->id,
            (int) $environment['teacher']->id,
            'T1_1',
            $packed['hash'],
            '',
            '',
            \context_module::instance($environment['cm']->id)
        );

        $rows = $export->rows(['courseid' => $courseid]);
        $sources = array_column($rows, 'relationship_source');
        $this->assertContains(relationship_index::EXPORT_MODIFIED, $sources);
        $this->assertContains(relationship_index::EXPORT_ADDED, $sources);
        $this->assertStringNotContainsString((string) $environment['teacher']->id, $export->csv($rows));

        $latestreview = null;
        foreach ($rows as $row) {
            $this->assertArrayHasKey('relationship_source', $row);
            $this->assertStringNotContainsString((string) $environment['teacher']->id, $row['participant_id']);
            if ($row['decision'] === 'reject') {
                $this->assertSame('', $row['relationship_source']);
            }
            if ($row['decision'] === 'modify') {
                $latestreview = $row;
            }
        }
        $this->assertNotNull($latestreview);
        $this->assertSame(relationship_index::EXPORT_MODIFIED, $latestreview['relationship_source']);
        $this->assertSame($replacement, $latestreview['final_competency']);
        $this->assertSame('current', $latestreview['relationship_status']);

        $removed = null;
        $active = null;
        foreach ($rows as $row) {
            if ($row['relationship_source'] !== relationship_index::EXPORT_ADDED) {
                continue;
            }
            if ($row['relationship_status'] === 'removed') {
                $removed = $row;
            }
            if ($row['final_competency'] === 'T1_1' && $row['relationship_status'] === 'current') {
                $active = $row;
            }
        }
        $this->assertNotNull($removed);
        $this->assertSame('Unit tests check one function at a time.', $removed['teacher_evidence']);
        $this->assertNotNull($active);
        $this->assertSame('', $active['teacher_evidence']);
        $this->assertSame('T004', $active['participant_id']);
        $this->assertNotEmpty($kept->id);

        $payload = $export->csv($rows) . json_encode($rows);
        $this->assertStringNotContainsString('password', strtolower($payload));
        $this->assertStringNotContainsString('servicetoken', strtolower($payload));
        $this->assertStringNotContainsString($environment['student']->email, $payload);
    }
}
