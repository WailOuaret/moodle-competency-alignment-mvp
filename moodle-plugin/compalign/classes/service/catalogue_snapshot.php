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

/**
 * An immutable view of the competency framework as it was sent to the service.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class catalogue_snapshot {
    /**
     * Constructor.
     *
     * @param int $frameworkid Moodle id of the framework.
     * @param string $frameworkidnumber ID number of the framework.
     * @param string $frameworkname Short name of the framework.
     * @param array[] $items The competencies in the shape the service expects.
     * @param array[] $lookup Competency details by idnumber: id, shortname, description, parentidnumber.
     * @param string $hash Digest of the catalogue content, computed by the plugin.
     */
    public function __construct(
        public readonly int $frameworkid,
        public readonly string $frameworkidnumber,
        public readonly string $frameworkname,
        public readonly array $items,
        public readonly array $lookup,
        public readonly string $hash,
    ) {
    }

    /**
     * The idnumbers of every competency in the catalogue.
     *
     * @return string[]
     */
    public function idnumbers(): array {
        return array_map('strval', array_keys($this->lookup));
    }

    /**
     * Details of one competency.
     *
     * @param string $idnumber The competency idnumber.
     * @return array|null id, shortname, description and parentidnumber, or null when unknown.
     */
    public function find(string $idnumber): ?array {
        return $this->lookup[$idnumber] ?? null;
    }
}
