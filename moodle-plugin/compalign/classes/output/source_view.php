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

/**
 * The source-context page: title, provenance and a highlighted quotation.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class source_view implements renderable, named_templatable {
    /**
     * @param array $view Fields from source_context::build().
     */
    public function __construct(private array $view) {
    }

    /**
     * @param renderer_base $renderer The renderer.
     * @return string
     */
    public function get_template_name(renderer_base $renderer): string {
        return 'local_compalign/source';
    }

    /**
     * @param renderer_base $output The renderer.
     * @return array
     */
    public function export_for_template(renderer_base $output): array {
        return [
            'title' => $this->view['title'],
            'type' => $this->view['type'],
            'provenance' => $this->view['provenance'],
            'hasprovenance' => ($this->view['provenance'] ?? '') !== '',
            'found' => !empty($this->view['found']),
            'html' => $this->view['html'] ?? '',
            'errormessage' => $this->view['errormessage'] ?? '',
            'openurl' => $this->view['openurl'] ?? '',
            'backurl' => $this->view['backurl'] ?? '',
        ];
    }
}
