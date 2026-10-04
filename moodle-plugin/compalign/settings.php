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
 * Administration settings: Site administration > Plugins > Local plugins.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

use local_compalign\admin\framework_setting;
use local_compalign\admin\validated_text_setting;
use local_compalign\service\alignment_client;
use local_compalign\service\study_phase;

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_compalign', get_string('pluginname', 'local_compalign'));
    $ADMIN->add('localplugins', $settings);

    if ($ADMIN->fulltree) {
        $settings->add(new admin_setting_heading(
            'local_compalign/servicesettings',
            get_string('servicesettings', 'local_compalign'),
            get_string('servicesettings_desc', 'local_compalign')
        ));

        $settings->add(new validated_text_setting(
            'local_compalign/serviceurl',
            get_string('serviceurl', 'local_compalign'),
            get_string('serviceurl_desc', 'local_compalign'),
            '',
            PARAM_URL,
            50,
            [alignment_client::class, 'validate_service_url']
        ));

        // The token is stored encrypted and the form never renders it back.
        $settings->add(new admin_setting_encryptedpassword(
            'local_compalign/servicetoken',
            get_string('servicetoken', 'local_compalign'),
            get_string('servicetoken_desc', 'local_compalign')
        ));

        $timeoutrange = (object) [
            'min' => alignment_client::MIN_TIMEOUT,
            'max' => alignment_client::MAX_TIMEOUT,
        ];
        $settings->add(new validated_text_setting(
            'local_compalign/requesttimeout',
            get_string('requesttimeout', 'local_compalign'),
            get_string('requesttimeout_desc', 'local_compalign', $timeoutrange),
            (string) alignment_client::DEFAULT_TIMEOUT,
            PARAM_INT,
            5,
            [alignment_client::class, 'validate_timeout']
        ));

        $settings->add(new framework_setting(
            'local_compalign/frameworkid',
            get_string('frameworkid', 'local_compalign'),
            get_string('frameworkid_desc', 'local_compalign')
        ));

        // The engine is evaluated at Top-5 and the service refuses any other value, so
        // the prototype shows the value instead of offering a setting it would reject.
        $settings->add(new admin_setting_description(
            'local_compalign/topkfixed',
            get_string('topk', 'local_compalign'),
            get_string('topk_fixed', 'local_compalign', alignment_client::SUPPORTED_TOP_K)
        ));

        $settings->add(new admin_setting_configselect(
            'local_compalign/maxsuggestions',
            get_string('maxsuggestions', 'local_compalign'),
            get_string('maxsuggestions_desc', 'local_compalign'),
            3,
            array_combine(range(1, 10), range(1, 10))
        ));

        $settings->add(new admin_setting_configselect(
            'local_compalign/studyphase',
            get_string('studyphase', 'local_compalign'),
            get_string('studyphase_desc', 'local_compalign'),
            study_phase::DEVELOPMENT,
            [
                study_phase::DEVELOPMENT => get_string('studyphase_development', 'local_compalign'),
                study_phase::LIVE_VERIFICATION => get_string('studyphase_verification', 'local_compalign'),
                study_phase::PILOT => get_string('studyphase_pilot', 'local_compalign'),
                study_phase::EXCLUDED => get_string('studyphase_excluded', 'local_compalign'),
            ]
        ));

        $settings->add(new admin_setting_configcheckbox(
            'local_compalign/enablewriteback',
            get_string('enablewriteback', 'local_compalign'),
            get_string('enablewriteback_desc', 'local_compalign'),
            0
        ));

        $settings->add(new admin_setting_description(
            'local_compalign/requirehumanreview',
            get_string('requirehumanreview', 'local_compalign'),
            get_string('requirehumanreview_desc', 'local_compalign')
        ));

        $settings->add(new admin_setting_description(
            'local_compalign/connectionstatus',
            get_string('connectionstatus', 'local_compalign'),
            html_writer::link(
                new moodle_url('/local/compalign/index.php'),
                get_string('connectionstatus_link', 'local_compalign')
            )
        ));
    }
}
