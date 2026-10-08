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

/**
 * The teacher-added relationship table is installed and can be upgraded to.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class upgrade_test extends \advanced_testcase {
    /**
     * A fresh install creates the table and its course index.
     */
    public function test_fresh_install_has_manual_table(): void {
        $this->resetAfterTest();
        $dbman = $this->dbman();
        $table = new \xmldb_table('local_compalign_manualrel');
        $this->assertTrue($dbman->table_exists($table));
        $this->assertTrue($dbman->field_exists($table, new \xmldb_field('status')));
        $this->assertTrue($dbman->index_exists($table, new \xmldb_index('course_resource_status', XMLDB_INDEX_NOTUNIQUE, ['courseid', 'resourceid', 'status'])));
    }

    /**
     * Upgrading from 0.3.0 creates the table when it is missing.
     */
    public function test_upgrade_from_030_installs_manual_table(): void {
        global $CFG;
        // upgrade_plugin_savepoint() lives in upgradelib.php, which is not loaded by default under PHPUnit.
        require_once($CFG->libdir . '/upgradelib.php');

        $this->preventResetByRollback();
        $this->resetAfterTest();
        $dbman = $this->dbman();
        $table = new \xmldb_table('local_compalign_manualrel');
        $dbman->drop_table($table);
        $this->assertFalse($dbman->table_exists($table));

        // upgrade_plugin_savepoint() refuses to move to a version that is not ahead of the
        // one recorded for the plugin, so stand the recorded version back down to 0.3.0 and
        // let the upgrade step run as it would on a real 0.3.0 site.
        set_config('version', 2026100403, 'local_compalign');

        require_once($CFG->dirroot . '/local/compalign/db/upgrade.php');
        $this->assertTrue(xmldb_local_compalign_upgrade(2026100403));
        $this->assertTrue($dbman->table_exists($table));
        $this->assertEquals(2026100701, (int) get_config('local_compalign', 'version'));
    }

    /**
     * @return \database_manager
     */
    private function dbman(): \database_manager {
        global $DB;

        return $DB->get_manager();
    }
}
