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

/**
 * Upgrade steps for the Competency Alignment Assistant.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

/**
 * Upgrade the plugin.
 *
 * @param int $oldversion The version being upgraded from.
 * @return bool
 */
function xmldb_local_compalign_upgrade(int $oldversion): bool {
    global $DB;

    $dbman = $DB->get_manager();

    if ($oldversion < 2026100301) {
        // Keep the provenance the service reports with each analysis.
        $table = new xmldb_table('local_compalign_analysis');
        $field = new xmldb_field('manifest', XMLDB_TYPE_TEXT, null, null, null, null, null, 'diagnostics');

        if (!$dbman->field_exists($table, $field)) {
            $dbman->add_field($table, $field);
        }

        upgrade_plugin_savepoint(true, 2026100301, 'local', 'compalign');
    }

    if ($oldversion < 2026100402) {
        $table = new xmldb_table('local_compalign_analysis');
        $source = new xmldb_field('sourceitemid', XMLDB_TYPE_CHAR, '255', null, XMLDB_NOTNULL, null, '', 'resourceid');
        if (!$dbman->field_exists($table, $source)) {
            $dbman->add_field($table, $source);
        }
        $extractor = new xmldb_field('extractorversion', XMLDB_TYPE_CHAR, '20', null, XMLDB_NOTNULL, null, '', 'sourceitemid');
        if (!$dbman->field_exists($table, $extractor)) {
            $dbman->add_field($table, $extractor);
        }
        $provenance = new xmldb_field('provenance', XMLDB_TYPE_TEXT, null, null, null, null, null, 'extractorversion');
        if (!$dbman->field_exists($table, $provenance)) {
            $dbman->add_field($table, $provenance);
        }
        $index = new xmldb_index('cm_resource', XMLDB_INDEX_NOTUNIQUE, ['cmid', 'resourceid']);
        if (!$dbman->index_exists($table, $index)) {
            $dbman->add_index($table, $index);
        }

        $cache = new xmldb_table('local_compalign_extract');
        if (!$dbman->table_exists($cache)) {
            $dbman->install_one_table_from_xmldb_file(__DIR__ . '/install.xml', 'local_compalign_extract');
        }

        upgrade_plugin_savepoint(true, 2026100402, 'local', 'compalign');
    }

    if ($oldversion < 2026100403) {
        $table = new xmldb_table('local_compalign_analysis');
        // Existing rows become development. That is an explicit label, not a guess from the timestamp.
        $field = new xmldb_field(
            'researchstatus',
            XMLDB_TYPE_CHAR,
            '40',
            null,
            XMLDB_NOTNULL,
            null,
            'development',
            'resourcetype'
        );
        if (!$dbman->field_exists($table, $field)) {
            $dbman->add_field($table, $field);
        }

        upgrade_plugin_savepoint(true, 2026100403, 'local', 'compalign');
    }

    return true;
}
