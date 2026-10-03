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

namespace local_compalign\task;

use local_compalign\service\analysis_manager;

/**
 * Runs one queued analysis in the background, so no web request waits on a model call.
 *
 * The task runs as the teacher who asked, so the resource is read with that teacher's own
 * visibility. It never rethrows: a failure is recorded on the analysis with a stable error code,
 * and a new analysis is an explicit action, so there is nothing for Moodle to retry.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class analyse_resource extends \core\task\adhoc_task {
    /**
     * Create the task for one analysis.
     *
     * @param int $analysisid The queued analysis.
     * @param int $userid The teacher who requested it. The task runs as this user.
     * @return self
     */
    public static function instance(int $analysisid, int $userid): self {
        $task = new self();
        $task->set_custom_data(['analysisid' => $analysisid]);
        $task->set_userid($userid);

        return $task;
    }

    /**
     * Name shown in the task administration pages.
     *
     * @return string
     */
    public function get_name(): string {
        return get_string('task_analyse_resource', 'local_compalign');
    }

    /**
     * A failed analysis is not retried automatically.
     *
     * @return bool
     */
    public function retry_until_success(): bool {
        return false;
    }

    /**
     * Run the analysis.
     */
    public function execute() {
        $data = $this->get_custom_data();
        $analysisid = (int) ($data->analysisid ?? 0);

        if ($analysisid > 0) {
            (new analysis_manager())->run($analysisid);
        }
    }
}
