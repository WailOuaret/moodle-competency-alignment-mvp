<?php  // Moodle configuration for the private teacher pilot.
//
// Everything that differs between deployments, and every secret, comes from the environment of
// the container. This file holds no secret and is safe to keep in version control.
//
// Not part of the Moodle sandbox used for development. That one has its own config.php.

unset($CFG);
global $CFG;
$CFG = new stdClass();

/**
 * Read a required environment variable, or stop with a clear message.
 *
 * @param string $name
 * @return string
 */
function compalign_pilot_env(string $name): string {
    $value = getenv($name);
    if ($value === false || $value === '') {
        fwrite(STDERR, "Moodle pilot configuration: the environment variable {$name} is not set.\n");
        http_response_code(500);
        exit(1);
    }
    return $value;
}

/**
 * Cover a network range except for one address, as the smallest list of CIDR blocks.
 *
 * Moodle's HTTP security helper has only a block list. To let it reach one service inside a range
 * that is blocked by default, the range is replaced by the blocks that still cover everything
 * else. Only IPv4 is handled, which is all the pilot uses.
 *
 * @param string $range A CIDR block such as 172.16.0.0/12.
 * @param string $except An address inside it.
 * @return string[] CIDR blocks that together cover the range minus the address.
 */
function compalign_pilot_cidr_without(string $range, string $except): array {
    [$base, $bits] = explode('/', $range);
    $bits = (int) $bits;
    $start = ip2long($base) & (-1 << (32 - $bits));
    $address = ip2long($except);
    $end = $start + (1 << (32 - $bits)) - 1;
    if ($address === false || $address < $start || $address > $end) {
        return [$range];
    }

    $blocks = [];
    for ($length = $bits + 1; $length <= 32; $length++) {
        $half = 1 << (32 - $length);
        // Of the two halves of the current block, keep the one the address is not in.
        $lower = $start;
        $upper = $start + $half;
        if ($address >= $upper) {
            $blocks[] = long2ip($lower) . '/' . $length;
            $start = $upper;
        } else {
            $blocks[] = long2ip($upper) . '/' . $length;
        }
    }
    return $blocks;
}

$CFG->dbtype = 'pgsql';
$CFG->dblibrary = 'native';
$CFG->dbhost = compalign_pilot_env('MOODLE_DB_HOST');
$CFG->dbname = compalign_pilot_env('MOODLE_DB_NAME');
$CFG->dbuser = compalign_pilot_env('MOODLE_DB_USER');
$CFG->dbpass = compalign_pilot_env('MOODLE_DB_PASSWORD');
$CFG->prefix = 'mdl_';
$CFG->dboptions = ['dbpersist' => 0, 'dbport' => '5432', 'dbsocket' => ''];

// The public address of the site, for example https://pilot.example.org (no trailing slash).
$CFG->wwwroot = rtrim(compalign_pilot_env('MOODLE_WWWROOT'), '/');
$CFG->dataroot = '/var/www/moodledata';
$CFG->admin = 'admin';
$CFG->directorypermissions = 02770;

// TLS ends at the reverse proxy, which talks plain http to this container.
if (stripos($CFG->wwwroot, 'https://') === 0) {
    $CFG->sslproxy = true;
}

// Moodle runs its scheduled and ad hoc tasks only from the command line, never from the web.
$CFG->cronclionly = 1;
$CFG->pathtophp = '/usr/local/bin/php';

// Quiet and private. Nothing in an error page helps a teacher, and nothing in one may help
// anyone else.
$CFG->debug = 0;
$CFG->debugdisplay = 0;
$CFG->perfdebug = 0;
$CFG->debugpageinfo = 0;
$CFG->debugstringids = 0;
$CFG->allowthemechangeonurl = 0;
$CFG->themedesignermode = 0;
$CFG->cachejs = 1;

// No mail goes out: the teacher accounts have placeholder addresses that cannot receive mail, and no
// mail server is configured. A password is reset by the administrator (see the runbook).
$CFG->noemailever = getenv('MOODLE_ALLOW_EMAIL') === '1' ? false : true;

// Passwords: long, and the usual mix of characters.
$CFG->passwordpolicy = 1;
$CFG->minpasswordlength = 12;
$CFG->minpassworddigits = 1;
$CFG->minpasswordlower = 1;
$CFG->minpasswordupper = 1;
$CFG->minpasswordnonalphanum = 1;
$CFG->passwordreuselimit = 3;

// Sessions and cookies.
$CFG->cookiesecure = $CFG->sslproxy ?? false;
$CFG->cookiehttponly = 1;
$CFG->sessiontimeout = 8 * 60 * 60;

// Nothing updates itself in a pilot. The administrator decides when (scripts/update.sh).
$CFG->disableupdateautodeploy = true;
$CFG->disableupdatenotifications = true;

// A teacher's work must not leave through a plugin or theme install button.
$CFG->disableonclickaddoninstall = true;

// ---------------------------------------------------------------------------------------------
// Reaching the alignment service.
//
// Moodle blocks requests to private network ranges by default, which is right for a site that
// downloads files from users' URLs. The alignment service is on a private Docker network, so
// exactly one address is let through: the one the service has been given (ALIGNMENT_IP), on
// port 80. Nothing else is opened. The rest of the default block list stays as Moodle ships it.
//
// Moodle's default block list, as of 5.2 (admin/settings/security.php):
//   127.0.0.0/8, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 0.0.0.0, localhost, 169.254.169.254, 0000::1
// ---------------------------------------------------------------------------------------------
$alignmentip = getenv('ALIGNMENT_IP');
if ($alignmentip !== false && $alignmentip !== '') {
    if (filter_var($alignmentip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) === false) {
        fwrite(STDERR, "Moodle pilot configuration: ALIGNMENT_IP is not an IPv4 address.\n");
        exit(1);
    }
    $blocked = [];
    foreach (['127.0.0.0/8', '192.168.0.0/16', '10.0.0.0/8', '172.16.0.0/12'] as $range) {
        foreach (compalign_pilot_cidr_without($range, $alignmentip) as $block) {
            $blocked[] = $block;
        }
    }
    $blocked = array_merge($blocked, ['0.0.0.0', 'localhost', '169.254.169.254', '0000::1']);
    $CFG->curlsecurityblockedhosts = implode("\n", $blocked);
    $CFG->curlsecurityallowedport = "443\n80";
}

require_once(__DIR__ . '/lib/setup.php');

// There is no PHP closing tag in this file, so that nothing can be output after it.
