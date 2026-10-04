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
 * A teacher file stored by Moodle. Bytes are not read until the background task.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class file_item {
    /** Largest file the background task will send for extraction. */
    public const MAX_BYTES = 20971520;

    /** Extractor version. A change invalidates stored file analyses. */
    public const EXTRACTOR_VERSION = '1.0';

    /** @var array<string, string> Extension to extraction format. */
    private const FORMATS = [
        'pdf' => 'pdf',
        'docx' => 'docx',
        'pptx' => 'pptx',
        'txt' => 'text',
        'md' => 'markdown',
        'markdown' => 'markdown',
        'vtt' => 'vtt',
        'srt' => 'srt',
    ];

    /** @var array<string, string> Service resource type for each format. */
    private const TYPES = [
        'pdf' => 'pdf',
        'docx' => 'docx',
        'pptx' => 'pptx',
        'text' => 'text',
        'markdown' => 'markdown',
        'vtt' => 'transcript',
        'srt' => 'transcript',
    ];

    /**
     * @param \cm_info $cm The activity that holds the file.
     * @param \stored_file $file The file. Directories are ignored by the caller.
     * @param string $container Human name of the container, such as the folder name.
     * @return item
     */
    public static function from_stored_file(\cm_info $cm, \stored_file $file, string $container): item {
        $filename = $file->get_filename();
        $extension = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
        $format = self::FORMATS[$extension] ?? '';
        $mimetype = (string) $file->get_mimetype();
        $supported = $format !== '' && (int) $file->get_filesize() <= self::MAX_BYTES && (int) $file->get_filesize() > 0
            && !self::mime_conflicts($format, $mimetype);
        $reason = '';
        if (in_array($extension, ['doc', 'ppt'], true)) {
            $reason = 'legacyoffice';
        } else if (in_array($extension, ['mp4', 'webm', 'mov'], true)) {
            $reason = 'transcriptrequired';
        } else if ($format === '') {
            $reason = 'unsupportedfile';
        } else if (self::mime_conflicts($format, $mimetype)) {
            $reason = 'mimemismatch';
            $supported = false;
        } else if ((int) $file->get_filesize() > self::MAX_BYTES) {
            $reason = 'filetoolarge';
        } else if ((int) $file->get_filesize() === 0) {
            $reason = 'resourceempty';
        }

        return new item(
            'moodle:file:' . $file->get_id(),
            $format === '' ? 'file' : self::TYPES[$format],
            $filename,
            '',
            $supported,
            $reason,
            $container . ', ' . $filename
        );
    }

    /**
     * Describe a file for a later extraction. The content hash is the fingerprint.
     *
     * @param \cm_info $cm The activity.
     * @param item $item The file item.
     * @return array
     */
    public static function extract(\cm_info $cm, item $item): array {
        $file = self::require_file($item);
        $extension = strtolower(pathinfo($file->get_filename(), PATHINFO_EXTENSION));
        $format = self::FORMATS[$extension] ?? '';
        if ($format === '' || self::mime_conflicts($format, (string) $file->get_mimetype())) {
            throw new analysis_exception('unsupported_resource_type');
        }
        if ((int) $file->get_filesize() > self::MAX_BYTES) {
            throw new analysis_exception('resource_too_large');
        }

        $packed = course_context::pack($cm, $item, '', [
            'content_hash' => $file->get_contenthash(),
            'extractor_version' => self::EXTRACTOR_VERSION,
            'filename' => $file->get_filename(),
        ]);
        $packed['file'] = [
            'fileid' => (string) $file->get_id(),
            'format' => $format,
            'filename' => $file->get_filename(),
            'mimetype' => $file->get_mimetype(),
            'contenthash' => $file->get_contenthash(),
        ];
        $packed['provenance'] = [
            'kind' => self::TYPES[$format],
            'label' => $item->provenance,
            'filename' => $file->get_filename(),
        ];
        return $packed;
    }

    /**
     * @param item $item The file item.
     * @return \stored_file
     */
    public static function require_file(item $item): \stored_file {
        $fileid = (int) substr(strrchr($item->resourceid, ':'), 1);
        $file = get_file_storage()->get_file_by_id($fileid);
        if (!$file || $file->is_directory()) {
            throw new analysis_exception('resource_missing');
        }
        return $file;
    }

    /**
     * A stored MIME type that contradicts the extension.
     *
     * An empty type, or application/octet-stream, is left to the extractor,
     * which checks the file signature.
     *
     * @param string $format Extraction format, or an empty string.
     * @param string $mimetype Moodle's stored MIME type.
     * @return bool
     */
    private static function mime_conflicts(string $format, string $mimetype): bool {
        $mimetype = strtolower(trim($mimetype));
        if ($format === '' || $mimetype === '' || $mimetype === 'application/octet-stream') {
            return false;
        }
        $allowed = [
            'pdf' => ['application/pdf'],
            'docx' => [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/zip',
            ],
            'pptx' => [
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/zip',
            ],
            'text' => ['text/plain'],
            'markdown' => ['text/plain', 'text/markdown'],
            'vtt' => ['text/vtt', 'text/plain'],
            'srt' => ['text/plain', 'application/x-subrip'],
        ];
        return !in_array($mimetype, $allowed[$format] ?? [], true);
    }
}
