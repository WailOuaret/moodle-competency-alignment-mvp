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

require_once(__DIR__ . '/fixtures/fake_transport.php');
require_once(__DIR__ . '/fixtures/service_stub.php');
require_once(__DIR__ . '/fixtures/environment.php');

/**
 * Tests for the competency catalogue built from the selected Moodle framework.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(competency_catalogue::class)]
#[CoversClass(catalogue_snapshot::class)]
final class competency_catalogue_test extends advanced_testcase {
    use environment;

    /**
     * The catalogue describes the selected framework, as Moodle holds it now.
     */
    public function test_build_describes_the_framework(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();

        $snapshot = (new competency_catalogue())->build();

        $this->assertSame((int) $environment['framework']->get('id'), $snapshot->frameworkid);
        $this->assertSame('TF', $snapshot->frameworkidnumber);
        $this->assertSame('Test framework', $snapshot->frameworkname);
        $this->assertEqualsCanonicalizing(['T1', 'T1_1', 'T2'], $snapshot->idnumbers());
        $this->assertMatchesRegularExpression('/^sha256:[0-9a-f]{64}$/', $snapshot->hash);

        $items = array_column($snapshot->items, null, 'idnumber');
        $this->assertSame('Verify software', $items['T1']['shortname']);
        $this->assertSame('Plan and run tests that verify software.', $items['T1']['description_text']);
        $this->assertNull($items['T1']['parent_idnumber']);
        $this->assertSame('T1', $items['T1_1']['parent_idnumber']);
        $this->assertSame('TF', $items['T2']['framework_idnumber']);
        $this->assertSame('Test framework', $items['T2']['framework_shortname']);

        $this->assertEquals($environment['competencies']['T1_1']->get('id'), $snapshot->find('T1_1')['id']);
        $this->assertNull($snapshot->find('ZZ'));
    }

    /**
     * A description written with markup reaches the service as plain text.
     */
    public function test_descriptions_are_plain_text(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $DB->set_field(
            'competency',
            'description',
            '<p>Plan <b>tests</b>&nbsp;and   run them.</p><script>alert(1)</script>',
            ['id' => $environment['competencies']['T2']->get('id')]
        );

        $items = array_column((new competency_catalogue())->build()->items, null, 'idnumber');

        $this->assertSame('Plan tests and run them.', $items['T2']['description_text'], 'Bold text keeps its case.');
    }

    /**
     * The digest ignores the order the competencies were listed in, and follows their content.
     */
    public function test_the_hash_follows_the_content(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $snapshot = (new competency_catalogue())->build();

        $this->assertSame($snapshot->hash, competency_catalogue::hash(array_reverse($snapshot->items)));
        $this->assertSame($snapshot->hash, (new competency_catalogue())->build()->hash);

        $DB->set_field('competency', 'description', 'A new description.', ['id' => $environment['competencies']['T2']->get('id')]);

        $this->assertNotSame($snapshot->hash, (new competency_catalogue())->build()->hash);
    }

    /**
     * Frameworks are never combined: only the selected one is read.
     */
    public function test_only_the_selected_framework_is_read(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $generator = $this->getDataGenerator()->get_plugin_generator('core_competency');
        $second = $generator->create_framework(['idnumber' => 'OTHER', 'shortname' => 'Other framework']);
        $generator->create_competency([
            'competencyframeworkid' => $second->get('id'),
            'idnumber' => 'O1',
            'shortname' => 'Elsewhere',
            'description' => 'Belongs to the other framework.',
        ]);

        $this->assertEqualsCanonicalizing(['T1', 'T1_1', 'T2'], (new competency_catalogue())->build()->idnumbers());
        $this->assertSame(['O1'], (new competency_catalogue((int) $second->get('id')))->build()->idnumbers());
        $this->assertSame((int) $environment['framework']->get('id'), (new competency_catalogue())->build()->frameworkid);
    }

    /**
     * Situations in which no catalogue can be built, with the error code that says why.
     */
    public function test_a_framework_that_cannot_be_used_is_reported(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $generator = $this->getDataGenerator()->get_plugin_generator('core_competency');
        $empty = $generator->create_framework(['idnumber' => 'EMPTY']);

        $framework = $environment['framework'];
        $framework->set('visible', 0);
        $framework->update();

        $cases = [
            'framework is hidden' => [(int) $framework->get('id'), 'framework_hidden'],
            'framework has no competencies' => [(int) $empty->get('id'), 'framework_empty'],
            'framework does not exist' => [999999, 'framework_unavailable'],
            'no framework selected' => [0, 'framework_not_selected'],
        ];

        foreach ($cases as $label => [$frameworkid, $code]) {
            try {
                (new competency_catalogue($frameworkid))->build();
                $this->fail("$label was accepted.");
            } catch (analysis_exception $exception) {
                $this->assertSame($code, $exception->get_error_code(), $label);
            }
        }
    }

    /**
     * Nothing can be built while competencies are switched off on the site.
     */
    public function test_disabled_competencies_are_reported(): void {
        $this->resetAfterTest();
        $this->create_environment();
        set_config('enabled', 0, 'core_competency');

        try {
            (new competency_catalogue())->build();
            $this->fail('A catalogue was built.');
        } catch (analysis_exception $exception) {
            $this->assertSame('competencies_disabled', $exception->get_error_code());
        }
    }

    /**
     * Competencies the service cannot use block the whole framework, and each one is named.
     */
    public function test_unusable_competencies_are_listed(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $ids = array_map(static fn($competency): int => (int) $competency->get('id'), $environment['competencies']);

        $DB->set_field('competency', 'idnumber', '', ['id' => $ids['T2']]);
        $DB->set_field('competency', 'description', '', ['id' => $ids['T1_1']]);

        try {
            (new competency_catalogue())->build();
            $this->fail('An unusable framework was accepted.');
        } catch (analysis_exception $exception) {
            $this->assertSame('framework_invalid', $exception->get_error_code());
            $details = implode(' | ', $exception->get_details());
            $this->assertStringContainsString(
                'Deploy software',
                $details,
                'A competency without an ID number is named by its name.'
            );
            $this->assertStringContainsString('T1_1', $details, 'A competency without a description is named by its ID number.');
        }
    }

    /**
     * A repeated ID number, and a parent without one, are problems too.
     */
    public function test_duplicate_and_parentless_idnumbers_are_problems(): void {
        global $DB;

        $this->resetAfterTest();
        $environment = $this->create_environment();
        $ids = array_map(static fn($competency): int => (int) $competency->get('id'), $environment['competencies']);

        $DB->set_field('competency', 'idnumber', 'T1', ['id' => $ids['T2']]);
        try {
            (new competency_catalogue())->build();
            $this->fail('A repeated ID number was accepted.');
        } catch (analysis_exception $exception) {
            $this->assertSame('framework_invalid', $exception->get_error_code());
            $this->assertStringContainsString('T1', implode(' | ', $exception->get_details()));
        }

        $DB->set_field('competency', 'idnumber', 'T2', ['id' => $ids['T2']]);
        $DB->set_field('competency', 'idnumber', '', ['id' => $ids['T1']]);
        try {
            (new competency_catalogue())->build();
            $this->fail('A parent without an ID number was accepted.');
        } catch (analysis_exception $exception) {
            $this->assertSame('framework_invalid', $exception->get_error_code());
            $this->assertStringContainsString('T1_1', implode(' | ', $exception->get_details()));
        }
    }

    /**
     * A framework with many problems lists only the first few.
     */
    public function test_the_list_of_problems_is_capped(): void {
        $this->resetAfterTest();
        $environment = $this->create_environment();
        $generator = $this->getDataGenerator()->get_plugin_generator('core_competency');
        for ($i = 0; $i < 15; $i++) {
            $generator->create_competency([
                'competencyframeworkid' => $environment['framework']->get('id'),
                'idnumber' => 'X' . $i,
                'shortname' => 'Without description ' . $i,
                'description' => ' ',
            ]);
        }

        try {
            (new competency_catalogue())->build();
            $this->fail('An unusable framework was accepted.');
        } catch (analysis_exception $exception) {
            $this->assertCount(10, $exception->get_details());
        }
    }
}
