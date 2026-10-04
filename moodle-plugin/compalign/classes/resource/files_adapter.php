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

namespace local_compalign\resource;

use local_compalign\service\analysis_exception;

/**
 * Files in a File resource or a Folder. The folder title is not analysed.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class files_adapter implements adapter {
    /**
     * @param string $modname resource or folder.
     * @param string $component Moodle file component.
     */
    public function __construct(
        private string $modname,
        private string $component,
    ) {
    }

    public function modname(): string {
        return $this->modname;
    }

    public function enumerate(\cm_info $cm): array {
        $context = \context_module::instance($cm->id);
        $files = get_file_storage()->get_area_files(
            $context->id,
            $this->component,
            'content',
            0,
            'filepath, filename',
            false
        );
        $items = [];
        foreach ($files as $file) {
            $items[] = file_item::from_stored_file($cm, $file, $cm->name);
        }
        return $items;
    }

    public function extract(\cm_info $cm, item $item): array {
        foreach ($this->enumerate($cm) as $candidate) {
            if ($candidate->resourceid === $item->resourceid) {
                if (!$candidate->supported) {
                    throw new analysis_exception($candidate->reason === 'filetoolarge' ? 'resource_too_large' : 'unsupported_resource_type');
                }
                return file_item::extract($cm, $candidate);
            }
        }
        throw new analysis_exception('resource_missing');
    }
}
