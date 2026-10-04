<?php
// Configure the Competency Alignment Assistant plugin for the pilot.
//
//   php plugin.php <framework id>
//
// The service address and token and the write-back switch are pinned: they follow the
// environment on every start, so a rotated token is picked up by a restart. The timeout and the
// number of suggestions are applied once and stay as the administrator leaves them.

require(__DIR__ . '/_bootstrap.php');

$frameworkid = (int) ($argv[1] ?? 0);
if ($frameworkid <= 0) {
    pilot_say('plugin: a framework id is required');
    exit(1);
}

$ip = getenv('ALIGNMENT_IP');
$token = getenv('ALIGNMENT_SERVICE_TOKEN');
if (!$ip || !$token) {
    pilot_say('plugin: ALIGNMENT_IP and ALIGNMENT_SERVICE_TOKEN must be set');
    exit(1);
}

// Plain http to a private address is the one case the plugin allows, and it is the design: the
// service is only reachable on the private compose network. The name is not used on purpose, so
// that nothing about the connection depends on DNS.
pilot_pin('serviceurl', 'http://' . $ip, 'local_compalign');
pilot_pin('frameworkid', $frameworkid, 'local_compalign');
pilot_pin('enablewriteback', 0, 'local_compalign');
pilot_default('requesttimeout', (int) (getenv('PLUGIN_REQUEST_TIMEOUT') ?: 120), 'local_compalign');
pilot_default('maxsuggestions', (int) (getenv('PLUGIN_MAX_SUGGESTIONS') ?: 3), 'local_compalign');

// The token goes through the plugin's own setting, so it is stored encrypted exactly as it would
// be if it were typed into the settings page.
// Individual settings live on the page, not as nodes the admin tree can locate by name.
$root = admin_get_root(true, true);
$page = $root->locate('local_compalign');
$setting = null;
if ($page instanceof admin_settingpage) {
    foreach ($page->settings as $candidate) {
        if ($candidate->name === 'servicetoken' && $candidate->plugin === 'local_compalign') {
            $setting = $candidate;
            break;
        }
    }
}
if (!$setting) {
    pilot_say('plugin: the token setting was not found. Is the plugin installed?');
    exit(1);
}
$problem = $setting->write_setting($token);
if ($problem !== '') {
    pilot_say('plugin: the token was not stored: ' . $problem);
    exit(1);
}

purge_caches(['muc' => true]);
pilot_say('plugin: configured for framework ' . $frameworkid . ' (token stored encrypted, write-back off)');
