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

namespace local_compalign\output;

use core\output\named_templatable;
use core\output\renderable;
use core\output\renderer_base;
use local_compalign\service\relationship_index;

/**
 * Competency to resources: the configured framework and the resources linked to one competency.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class competency_browser implements renderable, named_templatable {
    /** Filters that match the relationship origins. */
    public const FILTERS = ['reviewed', 'all', 'proposed', 'official', 'stale'];

    /**
     * @param \stdClass $course The course.
     * @param array[] $competencies Framework rows.
     * @param string $selected The selected idnumber.
     * @param string $query The search text.
     * @param string $filter The relationship filter.
     * @param array[] $rows Resources for the selected competency.
     */
    public function __construct(
        private \stdClass $course,
        private array $competencies,
        private string $selected,
        private string $query,
        private string $filter,
        private array $rows,
    ) {
    }

    /**
     * @param \stdClass $course The course.
     * @param int $userid The teacher.
     * @param string $selected The competency idnumber.
     * @param string $query The search.
     * @param string $filter The relationship filter.
     * @return self
     */
    public static function create(\stdClass $course, int $userid, string $selected, string $query, string $filter): self {
        if (!in_array($filter, self::FILTERS, true)) {
            $filter = 'reviewed';
        }
        $index = new relationship_index();
        $known = array_column($index->framework_list(''), 'idnumber');
        if ($selected !== '' && !in_array($selected, $known, true)) {
            $selected = '';
        }
        $competencies = $index->framework_list($query);
        $rows = $selected === '' ? [] : $index->for_competency($course, $userid, $selected, $filter);

        return new self($course, $competencies, $selected, $query, $filter, $rows);
    }

    /**
     * @param renderer_base $renderer The renderer.
     * @return string
     */
    public function get_template_name(renderer_base $renderer): string {
        return 'local_compalign/competencies';
    }

    /**
     * @param renderer_base $output The renderer.
     * @return array
     */
    public function export_for_template(renderer_base $output): array {
        $base = new \moodle_url('/local/compalign/index.php', [
            'courseid' => $this->course->id,
            'view' => 'competencies',
        ]);
        $competencies = [];
        foreach ($this->competencies as $competency) {
            $competencies[] = [
                'idnumber' => $competency['idnumber'],
                'shortname' => $competency['shortname'],
                'breadcrumb' => $competency['breadcrumb'],
                'pad' => str_repeat('– ', (int) $competency['depth']),
                'url' => (new \moodle_url($base, [
                    'competency' => $competency['idnumber'],
                    'rel' => $this->filter,
                    'q' => $this->query,
                ]))->out(false),
                'active' => $competency['idnumber'] === $this->selected,
            ];
        }

        $filters = [];
        foreach (self::FILTERS as $key) {
            $filters[] = [
                'url' => (new \moodle_url($base, [
                    'competency' => $this->selected,
                    'rel' => $key,
                    'q' => $this->query,
                ]))->out(false),
                'label' => get_string('relfilter_' . $key, 'local_compalign'),
                'classes' => 'btn btn-sm me-1 mb-1 ' . ($this->filter === $key ? 'btn-primary' : 'btn-outline-secondary'),
                'active' => $this->filter === $key,
            ];
        }

        return [
            'competencies' => $competencies,
            'hascompetencies' => (bool) $competencies,
            'selected' => $this->selected,
            'query' => $this->query,
            'courseid' => (int) $this->course->id,
            'searchurl' => $base->out(false),
            'filters' => $filters,
            'rows' => $this->rows,
            'hasrows' => (bool) $this->rows,
            'showempty' => $this->selected !== '' && !$this->rows,
        ];
    }
}
