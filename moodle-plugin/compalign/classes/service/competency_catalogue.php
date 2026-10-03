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

use core_competency\api;

/**
 * Builds the competency catalogue sent to the alignment service from a Moodle framework.
 *
 * The catalogue always comes from the framework the administrator selected, read through
 * Moodle's competency API. Nothing is hard-coded and nothing comes from the research files.
 * Frameworks are never combined. A framework the service cannot use is reported as a
 * configuration problem and is not sent.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class competency_catalogue {
    /** Most problems listed for one framework, so a broken framework does not flood the page. */
    private const MAX_PROBLEMS = 10;

    /** @var int The framework to read. */
    private int $frameworkid;

    /**
     * Constructor.
     *
     * @param int|null $frameworkid The framework. Defaults to the one set in the plugin settings.
     */
    public function __construct(?int $frameworkid = null) {
        $this->frameworkid = $frameworkid ?? (int) get_config('local_compalign', 'frameworkid');
    }

    /**
     * Read the framework and build the catalogue.
     *
     * @return catalogue_snapshot
     * @throws analysis_exception When the framework cannot be used. The error code says why.
     */
    public function build(): catalogue_snapshot {
        if (!api::is_enabled()) {
            throw new analysis_exception('competencies_disabled');
        }

        if ($this->frameworkid <= 0) {
            throw new analysis_exception('framework_not_selected');
        }

        try {
            $framework = api::read_framework($this->frameworkid);
        } catch (\moodle_exception $exception) {
            throw new analysis_exception('framework_unavailable', 'The framework cannot be read.', [], $exception);
        }

        if (!$framework->get('visible')) {
            throw new analysis_exception('framework_hidden');
        }

        $records = api::list_competencies(['competencyframeworkid' => $this->frameworkid], 'path', 'ASC');
        if (!$records) {
            throw new analysis_exception('framework_empty');
        }

        $frameworkidnumber = trim((string) $framework->get('idnumber'));
        $frameworkname = self::collapse((string) $framework->get('shortname'));
        [$items, $lookup, $problems] = $this->describe_competencies($records, $frameworkidnumber, $frameworkname);

        if ($problems) {
            throw new analysis_exception(
                'framework_invalid',
                'The framework has competencies the alignment service cannot use.',
                array_slice($problems, 0, self::MAX_PROBLEMS)
            );
        }

        return new catalogue_snapshot(
            (int) $framework->get('id'),
            $frameworkidnumber,
            $frameworkname,
            $items,
            $lookup,
            self::hash($items)
        );
    }

    /**
     * Turn competency records into service items and a lookup, collecting every problem.
     *
     * @param \core_competency\competency[] $records The competencies of the framework.
     * @param string $frameworkidnumber ID number of the framework.
     * @param string $frameworkname Short name of the framework.
     * @return array The items, the lookup by idnumber, and the problems found.
     */
    private function describe_competencies(array $records, string $frameworkidnumber, string $frameworkname): array {
        $byid = [];
        foreach ($records as $record) {
            $byid[(int) $record->get('id')] = $record;
        }

        $items = [];
        $lookup = [];
        $problems = [];

        foreach ($records as $record) {
            $id = (int) $record->get('id');
            $idnumber = trim((string) $record->get('idnumber'));
            $shortname = self::collapse((string) $record->get('shortname'));
            $description = self::collapse(self::description_to_text(
                (string) $record->get('description'),
                (int) $record->get('descriptionformat')
            ));
            $label = $shortname !== '' ? $shortname : '#' . $id;

            if ($idnumber === '') {
                $problems[] = get_string('catalogueproblem_noidnumber', 'local_compalign', $label);
                continue;
            }

            if (isset($lookup[$idnumber])) {
                $problems[] = get_string('catalogueproblem_duplicate', 'local_compalign', $idnumber);
                continue;
            }

            if ($description === '') {
                $problems[] = get_string('catalogueproblem_nodescription', 'local_compalign', $idnumber);
            }

            $parentidnumber = '';
            $parentid = (int) $record->get('parentid');
            if ($parentid > 0) {
                $parent = $byid[$parentid] ?? null;
                $parentidnumber = $parent ? trim((string) $parent->get('idnumber')) : '';
                if ($parentidnumber === '') {
                    $problems[] = get_string('catalogueproblem_parent', 'local_compalign', $idnumber);
                }
            }

            $items[] = [
                'idnumber' => $idnumber,
                'shortname' => $shortname,
                'description_text' => $description,
                'parent_idnumber' => $parentidnumber !== '' ? $parentidnumber : null,
                'framework_idnumber' => $frameworkidnumber,
                'framework_shortname' => $frameworkname,
            ];
            $lookup[$idnumber] = [
                'id' => $id,
                'shortname' => $shortname,
                'description' => $description,
                'parentidnumber' => $parentidnumber,
            ];
        }

        return [$items, $lookup, $problems];
    }

    /**
     * A description as plain text.
     *
     * Moodle's own converter writes bold text and headings in capitals. Descriptions are converted the way
     * Pages are instead, so the words reach the service as they were written.
     *
     * @param string $description The description as stored.
     * @param int $format Its Moodle text format.
     * @return string Plain text.
     */
    private static function description_to_text(string $description, int $format): string {
        return match ($format) {
            FORMAT_PLAIN => $description,
            FORMAT_MARKDOWN => resource_extractor::html_to_text(markdown_to_html($description)),
            default => resource_extractor::html_to_text($description),
        };
    }

    /**
     * A stable digest of the catalogue content, independent of the order it was listed in.
     *
     * @param array[] $items The catalogue items.
     * @return string sha256: followed by the hex digest.
     */
    public static function hash(array $items): string {
        usort($items, static fn(array $a, array $b): int => strcmp($a['idnumber'], $b['idnumber']));

        return 'sha256:' . hash('sha256', json_encode(
            $items,
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
        ));
    }

    /**
     * Collapse whitespace.
     *
     * @param string $text Any text.
     * @return string The text with every run of whitespace replaced by one space, trimmed.
     */
    private static function collapse(string $text): string {
        return trim((string) preg_replace('/\s+/u', ' ', $text));
    }
}
