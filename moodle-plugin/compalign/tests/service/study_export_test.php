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
 * The research export: phase, pseudonym and filters.
 *
 * A comment is included. A teacher can type a name into it.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[\PHPUnit\Framework\Attributes\CoversClass(\local_compalign\service\study_export::class)]
final class study_export_test extends \advanced_testcase {
    use environment;

    /**
     * A study code is kept. Anything else is a keyed pseudonym, and the raw user id is absent.
     */
    public function test_export_is_pseudonymous_and_filterable(): void {
        global $DB;

        $this->resetAfterTest();
        set_config('studyphase', study_phase::PILOT, 'local_compalign');
        $environment = $this->create_environment();
        $environment['teacher']->idnumber = 'T001';
        user_update_user($environment['teacher'], false);
        $made = $this->create_completed_analysis($environment);
        $suggestion = reset($made['suggestions']);
        $this->assertSame(study_phase::PILOT, $made['analysis']->researchstatus);

        (new review_manager())->save(
            $made['analysis'],
            $suggestion,
            (int) $environment['teacher']->id,
            'accept',
            null,
            '2',
            'The quotation matches the page.',
            time() - 30,
            $made['catalogue']
        );

        $other = $this->getDataGenerator()->create_user([
            'idnumber' => '',
            'firstname' => 'Realname',
            'lastname' => 'Teacher',
            'email' => 'real.teacher@example.invalid',
        ]);
        $export = new study_export();
        $coded = $export->participant('T001', (int) $environment['teacher']->id);
        $fallback = $export->participant('', (int) $other->id);
        $this->assertSame('T001', $coded);
        $this->assertMatchesRegularExpression('/^participant-[0-9a-f]{12}$/', $fallback);
        $this->assertStringNotContainsString((string) $other->id, $fallback);
        $this->assertSame($fallback, $export->participant('', (int) $other->id));

        $rows = $export->rows(['researchstatus' => study_phase::PILOT]);
        $this->assertCount(1, $rows);
        $this->assertSame('T001', $rows[0]['participant_id']);
        $this->assertSame('pilot', $rows[0]['research_status']);
        $this->assertSame('page', $rows[0]['resource_type']);
        $this->assertSame('The quotation matches the page.', $rows[0]['comment']);

        $csv = $export->csv($rows);
        $json = json_encode(['reviews' => $rows]);
        foreach ([$csv, $json] as $payload) {
            $this->assertStringNotContainsString('Realname', $payload);
            $this->assertStringNotContainsString('real.teacher@example.invalid', $payload);
            $this->assertStringNotContainsString('password', strtolower($payload));
            $this->assertStringNotContainsString('sesskey', $payload);
            $this->assertStringNotContainsString((string) $other->id, $payload);
        }
        $this->assertStringContainsString('The quotation matches the page.', $csv);

        $this->assertSame([], $export->rows(['researchstatus' => study_phase::DEVELOPMENT]));
        $this->assertSame([], $export->rows(['courseid' => $environment['course']->id + 99]));
        $this->assertSame([], $export->rows(['resourcetype' => 'pdf']));
        $this->assertSame([], $export->rows(['participant' => 'T002']));
        $this->assertSame([], $export->rows(['from' => time() + 3600]));
        $this->assertCount(1, $export->rows([
            'courseid' => (int) $environment['course']->id,
            'resourcetype' => 'page',
            'participant' => 'T001',
            'to' => time() + 60,
        ]));

        $DB->set_field('local_compalign_analysis', 'researchstatus', study_phase::EXCLUDED, [
            'id' => $made['analysis']->id,
        ]);
        $this->assertSame([], $export->rows(['researchstatus' => study_phase::PILOT]));
        $this->assertCount(1, $export->rows(['researchstatus' => study_phase::EXCLUDED]));
    }
}
