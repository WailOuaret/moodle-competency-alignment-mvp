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
use local_compalign\service\alignment_client;
use local_compalign\service\connection_result;

/**
 * The overview page: plugin state and, for managers, the alignment service status.
 *
 * Nothing here can carry a token, a header or a response body: the connection is
 * described only by its status code and a localised sentence.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class overview implements renderable, named_templatable {
    /** Alert style for each connection status. */
    private const ALERT_TYPES = [
        alignment_client::STATUS_CONNECTED => 'success',
        alignment_client::STATUS_UNAUTHORIZED => 'warning',
        alignment_client::STATUS_BLOCKED => 'warning',
        alignment_client::STATUS_NOTCONFIGURED => 'info',
        alignment_client::STATUS_UNAVAILABLE => 'danger',
        alignment_client::STATUS_INVALIDRESPONSE => 'danger',
    ];

    /**
     * Constructor.
     *
     * @param connection_result|null $connection The connection status, or null to hide it.
     * @param bool $showsettings Whether to link to the plugin settings.
     */
    public function __construct(
        private ?connection_result $connection,
        private bool $showsettings,
    ) {
    }

    /**
     * Name of the template that renders this page.
     *
     * @param renderer_base $renderer The renderer.
     * @return string
     */
    public function get_template_name(renderer_base $renderer): string {
        return 'local_compalign/overview';
    }

    /**
     * Export the data for the template.
     *
     * @param renderer_base $output The renderer.
     * @return array Template context.
     */
    public function export_for_template(renderer_base $output): array {
        $plugininfo = \core_plugin_manager::instance()->get_plugin_info('local_compalign');

        return [
            'release' => $plugininfo ? $plugininfo->release : '',
            'topk' => alignment_client::SUPPORTED_TOP_K,
            'writebackstatus' => get_string('writeback_off', 'local_compalign'),
            'humanreview' => get_string('humanreview_always', 'local_compalign'),
            'showconnection' => $this->connection !== null,
            'connection' => $this->connection ? $this->describe($this->connection) : null,
            'showsettings' => $this->showsettings,
            'settingsurl' => (new \moodle_url('/admin/settings.php', ['section' => 'local_compalign']))->out(false),
        ];
    }

    /**
     * Describe a connection result for the template.
     *
     * @param connection_result $result The result.
     * @return array Alert type, label, help text and the time of the check.
     */
    private function describe(connection_result $result): array {
        $helpkey = 'status_' . $result->status . '_help';
        $reasons = ['notconfigured_url', 'notconfigured_token'];
        if ($result->status === alignment_client::STATUS_NOTCONFIGURED && in_array($result->reason, $reasons, true)) {
            $helpkey = 'status_' . $result->reason;
        }

        return [
            'type' => self::ALERT_TYPES[$result->status] ?? 'danger',
            'label' => get_string('status_' . $result->status, 'local_compalign'),
            'help' => get_string($helpkey, 'local_compalign'),
            'checked' => get_string('connectionchecked', 'local_compalign', userdate(time())),
        ];
    }
}
