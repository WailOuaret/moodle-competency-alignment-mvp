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
 * Finds the adapter for a course module.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class registry {
    /** @var array<string, adapter>|null */
    private static ?array $adapters = null;

    /**
     * @return array<string, adapter> Keyed by module name.
     */
    public static function adapters(): array {
        if (self::$adapters === null) {
            $list = [
                new page_adapter(),
                new quiz_adapter(),
                new book_adapter(),
                new lesson_adapter(),
                new assignment_adapter(),
                new label_adapter(),
                new files_adapter('resource', 'mod_resource'),
                new files_adapter('folder', 'mod_folder'),
                new intro_adapter('forum', 'forum', 'forum_intro'),
                new intro_adapter('url', 'url', 'url'),
            ];
            self::$adapters = [];
            foreach ($list as $adapter) {
                self::$adapters[$adapter->modname()] = $adapter;
            }
        }
        return self::$adapters;
    }

    /**
     * @param \cm_info $cm The course module.
     * @return adapter|null
     */
    public static function for_cm(\cm_info $cm): ?adapter {
        return self::adapters()[$cm->modname] ?? null;
    }

    /**
     * @param \cm_info $cm The course module.
     * @return bool
     */
    public static function supports(\cm_info $cm): bool {
        return self::for_cm($cm) !== null;
    }

    /**
     * @param \cm_info $cm The course module.
     * @return item[]
     */
    public static function enumerate(\cm_info $cm): array {
        $adapter = self::for_cm($cm);
        if ($adapter === null) {
            return [new item(
                'moodle:unsupported:' . $cm->id,
                'unsupported',
                $cm->name,
                '',
                false,
                'unsupportedtype',
                ''
            )];
        }
        return $adapter->enumerate($cm);
    }

    /**
     * @param \cm_info $cm The course module.
     * @param string $resourceid Empty to use the only item.
     * @return array
     */
    public static function extract(\cm_info $cm, string $resourceid = ''): array {
        $adapter = self::for_cm($cm);
        if ($adapter === null) {
            throw new analysis_exception('unsupported_resource_type');
        }

        $items = $adapter->enumerate($cm);
        if ($resourceid === '') {
            $supported = array_values(array_filter($items, static fn(item $item): bool => $item->supported));
            if (count($supported) !== 1) {
                throw new analysis_exception(count($items) > 1 ? 'resource_item_required' : 'resource_empty');
            }
            $resourceid = $supported[0]->resourceid;
        }

        foreach ($items as $item) {
            if ($item->resourceid === $resourceid) {
                if (!$item->supported) {
                    $code = $item->reason === 'unsupportedquestion' ? 'unsupported_question_type' : 'unsupported_resource_type';
                    if ($item->reason === 'filetoolarge') {
                        $code = 'resource_too_large';
                    }
                    if ($item->reason === 'resourceempty') {
                        $code = 'resource_empty';
                    }
                    throw new analysis_exception($code);
                }
                return $adapter->extract($cm, $item);
            }
        }

        throw new analysis_exception('resource_missing');
    }
}
