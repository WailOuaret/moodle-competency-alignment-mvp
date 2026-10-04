<?php
// Shared start-up for the pilot's provisioning scripts. Every script is run as www-data, from
// the command line, through the image's entrypoint. None of them prints a secret.

define('CLI_SCRIPT', true);
require('/var/www/html/config.php');
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->libdir . '/adminlib.php');

// The scripts act as the site administrator, so that Moodle's own capability checks pass
// without weakening them.
\core\session\manager::set_user(get_admin());

/**
 * Say something. Progress goes to standard error, so that standard output stays free for data.
 *
 * @param string $message
 */
function pilot_say(string $message): void {
    fwrite(STDERR, $message . PHP_EOL);
}

/**
 * Set a core or plugin setting only when it has no value yet.
 *
 * This is for defaults an administrator may later change in the web interface: a restart must
 * not undo that.
 *
 * @param string $name
 * @param mixed $value
 * @param string|null $plugin
 * @return bool True when the value was set.
 */
function pilot_default(string $name, $value, ?string $plugin = null): bool {
    if (get_config($plugin ?? 'core', $name) !== false) {
        return false;
    }
    set_config($name, $value, $plugin);
    return true;
}

/**
 * Set a setting every time. For the settings the pilot's safety depends on.
 *
 * @param string $name
 * @param mixed $value
 * @param string|null $plugin
 */
function pilot_pin(string $name, $value, ?string $plugin = null): void {
    if ((string) get_config($plugin ?? 'core', $name) !== (string) $value) {
        set_config($name, $value, $plugin);
    }
}

/**
 * A random password that meets the site's password policy.
 *
 * Twenty characters from sets without look-alike characters (no 0/O, 1/l/I), at least three of
 * each kind, in a random order. Drawn with random_int, which is the operating system's CSPRNG. A
 * candidate is redrawn until Moodle's own policy accepts it.
 *
 * @return string
 */
function pilot_password(): string {
    $sets = ['ABCDEFGHJKLMNPQRSTUVWXYZ', 'abcdefghijkmnopqrstuvwxyz', '23456789', '-_.+=@#%'];
    $all = implode('', $sets);
    do {
        $chars = [];
        foreach ($sets as $set) {
            for ($i = 0; $i < 3; $i++) {
                $chars[] = $set[random_int(0, strlen($set) - 1)];
            }
        }
        while (count($chars) < 20) {
            $chars[] = $all[random_int(0, strlen($all) - 1)];
        }
        for ($i = count($chars) - 1; $i > 0; $i--) {
            $j = random_int(0, $i);
            [$chars[$i], $chars[$j]] = [$chars[$j], $chars[$i]];
        }
        $password = implode('', $chars);
        $problem = '';
    } while (!check_password_policy($password, $problem));
    return $password;
}
