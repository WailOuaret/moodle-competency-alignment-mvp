<?php
// Plain PHP, no Moodle: is the database reachable, and is Moodle installed in it?
//
//   php db_ready.php              exit 0 when the database answers
//   php db_ready.php --installed  exit 0 when it answers and Moodle's config table holds a version
//
// Used by the entrypoint before Moodle's own code can be loaded.

$host = getenv('MOODLE_DB_HOST');
$name = getenv('MOODLE_DB_NAME');
$user = getenv('MOODLE_DB_USER');
$pass = getenv('MOODLE_DB_PASSWORD');
if (!$host || !$name || !$user || $pass === false) {
    fwrite(STDERR, "database settings are missing from the environment\n");
    exit(2);
}

$connection = @pg_connect(sprintf(
    "host=%s port=5432 dbname=%s user=%s password=%s connect_timeout=3",
    addcslashes($host, "' \\"),
    addcslashes($name, "' \\"),
    addcslashes($user, "' \\"),
    addcslashes($pass, "' \\")
));
if ($connection === false) {
    exit(1);
}

if (in_array('--installed', $argv, true)) {
    $result = @pg_query($connection, "SELECT value FROM mdl_config WHERE name = 'version'");
    exit($result !== false && pg_num_rows($result) === 1 ? 0 : 1);
}
exit(0);
