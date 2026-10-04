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

namespace local_compalign;

use advanced_testcase;
use local_compalign\admin\framework_setting;
use local_compalign\admin\validated_text_setting;
use local_compalign\fixtures\service_stub;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;

require_once(__DIR__ . '/fixtures/fake_transport.php');
require_once(__DIR__ . '/fixtures/service_stub.php');

/**
 * Tests for the plugin's administration settings, as Moodle's own settings page builds them.
 *
 * @package    local_compalign
 * @category   test
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
#[CoversClass(framework_setting::class)]
#[CoversClass(validated_text_setting::class)]
final class settings_test extends advanced_testcase {
    /**
     * One setting of the plugin's settings page.
     *
     * @param string $name The setting's name without the plugin prefix, for example serviceurl.
     * @return \admin_setting
     */
    private function setting(string $name): \admin_setting {
        global $CFG;

        require_once($CFG->libdir . '/adminlib.php');
        $this->setAdminUser();

        $page = admin_get_root(true, true)->locate('local_compalign');
        $this->assertInstanceOf(\admin_settingpage::class, $page, 'The plugin has no settings page.');

        $key = 'local_compalign' . $name;
        $this->assertTrue(isset($page->settings->$key), "The settings page has no '$name' setting.");

        return $page->settings->$key;
    }

    /**
     * The settings page offers each setting, with the kind of control that keeps the token secret.
     */
    public function test_the_settings_page_has_the_expected_settings(): void {
        $this->resetAfterTest();

        $this->assertInstanceOf(validated_text_setting::class, $this->setting('serviceurl'));
        $this->assertInstanceOf(\admin_setting_encryptedpassword::class, $this->setting('servicetoken'));
        $this->assertInstanceOf(validated_text_setting::class, $this->setting('requesttimeout'));
        $this->assertInstanceOf(framework_setting::class, $this->setting('frameworkid'));
        $this->assertInstanceOf(\admin_setting_configselect::class, $this->setting('maxsuggestions'));
        $this->assertInstanceOf(\admin_setting_configcheckbox::class, $this->setting('enablewriteback'));
        foreach (['topkfixed', 'requirehumanreview', 'connectionstatus'] as $name) {
            $this->assertInstanceOf(\admin_setting_description::class, $this->setting($name), $name);
        }
    }

    /**
     * The token is stored encrypted, can be read back by the plugin, and is never written into the page.
     */
    public function test_the_token_is_stored_encrypted_and_never_shown(): void {
        $this->resetAfterTest();
        $setting = $this->setting('servicetoken');

        $this->assertSame('', $setting->write_setting(service_stub::TOKEN), 'Moodle refused to store the token.');

        $stored = (string) get_config('local_compalign', 'servicetoken');
        $this->assertNotSame('', $stored);
        $this->assertStringNotContainsString(service_stub::TOKEN, $stored, 'The token is stored in plain text.');
        $this->assertSame(service_stub::TOKEN, \core\encryption::decrypt($stored), 'The plugin cannot read its own token back.');

        $html = $setting->output_html($setting->get_setting());
        $this->assertStringNotContainsString(service_stub::TOKEN, $html);
        $this->assertStringNotContainsString($stored, $html);
    }

    /**
     * Clearing the token leaves the plugin unconfigured, and the analyses refuse to start.
     *
     * Moodle's widget stores an empty value when it is told to. Leaving the field alone keeps the token only because
     * the browser then does not send the field at all.
     */
    public function test_clearing_the_token_leaves_the_plugin_unconfigured(): void {
        $this->resetAfterTest();
        set_config('serviceurl', 'https://align.example.org', 'local_compalign');
        $setting = $this->setting('servicetoken');
        $setting->write_setting(service_stub::TOKEN);
        $this->assertInstanceOf(service\alignment_client::class, service\alignment_client::from_config());

        $this->assertSame('', $setting->write_setting(''));

        try {
            service\alignment_client::from_config();
            $this->fail('A client was built without a token.');
        } catch (service\service_exception $exception) {
            $this->assertSame('notconfigured_token', $exception->get_error_code());
        }
        $this->assertSame(
            service\alignment_client::STATUS_NOTCONFIGURED,
            service\alignment_client::check_configured_connection()->status
        );
    }

    /**
     * Service addresses, with whether the setting accepts them.
     *
     * @return array<string, array>
     */
    public static function url_provider(): array {
        return [
            'not set yet' => ['', true],
            'https on a public host' => ['https://align.example.org', true],
            'http on the docker host' => ['http://host.docker.internal:8001', true],
            'http on localhost' => ['http://localhost:8001', true],
            'http on a public host' => ['http://example.org', false],
            'credentials in the address' => ['https://user:pass@example.org', false],
            'a query string' => ['https://example.org/?token=1', false],
            'another scheme' => ['ftp://example.org', false],
        ];
    }

    /**
     * Only an acceptable address is stored.
     *
     * @param string $url The address.
     * @param bool $accepted Whether it is accepted.
     */
    #[DataProvider('url_provider')]
    public function test_the_service_url_is_validated(string $url, bool $accepted): void {
        $this->resetAfterTest();
        set_config('serviceurl', 'https://before.example.org', 'local_compalign');
        $setting = $this->setting('serviceurl');

        $result = $setting->validate($url);
        $this->assertSame($accepted, $result === true, is_string($result) ? $result : 'accepted');

        $error = $setting->write_setting($url);
        if ($accepted) {
            $this->assertSame('', $error);
            $this->assertSame($url, (string) get_config('local_compalign', 'serviceurl'));
        } else {
            $this->assertNotSame('', $error);
            $this->assertSame(
                'https://before.example.org',
                get_config('local_compalign', 'serviceurl'),
                'A refused value was stored.'
            );
        }
    }

    /**
     * The request timeout has to be a whole number of seconds inside the supported range.
     */
    public function test_the_timeout_is_validated(): void {
        $this->resetAfterTest();
        $setting = $this->setting('requesttimeout');

        foreach (['5', '120', '900'] as $value) {
            $this->assertTrue($setting->validate($value), $value);
        }
        foreach (['4', '901', 'abc', '60.5'] as $value) {
            $this->assertNotTrue($setting->validate($value), $value);
        }
    }

    /**
     * Only visible frameworks can be chosen, and a framework that is not offered is never stored.
     */
    public function test_only_visible_frameworks_can_be_chosen(): void {
        $this->resetAfterTest();
        $generator = $this->getDataGenerator()->get_plugin_generator('core_competency');
        $visible = $generator->create_framework(['idnumber' => 'SHOWN', 'shortname' => 'Shown framework']);
        $hidden = $generator->create_framework(['idnumber' => 'HIDDEN', 'shortname' => 'Hidden framework', 'visible' => 0]);
        $setting = $this->setting('frameworkid');

        $setting->load_choices();

        $this->assertSame(0, array_key_first($setting->choices), 'Nothing is selected by default.');
        $this->assertSame('Shown framework (SHOWN)', $setting->choices[(int) $visible->get('id')]);
        $this->assertArrayNotHasKey((int) $hidden->get('id'), $setting->choices);

        $this->assertSame('', $setting->write_setting((string) $visible->get('id')));
        $this->assertEquals($visible->get('id'), get_config('local_compalign', 'frameworkid'));

        $setting->write_setting((string) $hidden->get('id'));
        $this->assertEquals($visible->get('id'), get_config('local_compalign', 'frameworkid'), 'A hidden framework was stored.');
    }

    /**
     * Settings that cannot be changed are explained, not offered.
     */
    public function test_fixed_and_reserved_settings_are_explained(): void {
        $this->resetAfterTest();

        $this->assertStringContainsString('Fixed at 5', $this->setting('topkfixed')->description);
        $this->assertStringContainsString('Always on', $this->setting('requirehumanreview')->description);
        $this->assertSame(0, (int) $this->setting('enablewriteback')->get_defaultsetting(), 'Write-back must be off by default.');
        $this->assertSame(0, (int) get_config('local_compalign', 'enablewriteback'), 'Write-back must be off on a fresh install.');
    }
}
