<?php
// Site-wide settings of the pilot. Safe to run on every start.
//
// Settings the pilot's privacy depends on are set every time ("pinned"). Everything else is a
// default that is applied once, so that a change made in the web interface survives a restart.

require(__DIR__ . '/_bootstrap.php');

// A private site: no visitor sees anything without an account, nobody can sign up, and there is
// no guest access.
pilot_pin('forcelogin', 1);
pilot_pin('auth', 'manual');
pilot_pin('registerauth', '');
pilot_pin('guestloginbutton', 0);
pilot_pin('autologinguests', 0);

// Moodle's web services and mobile app access are not used.
pilot_pin('enablewebservices', 0);
pilot_pin('enablemobilewebservice', 0);

// The competency features the plugin builds on.
pilot_pin('enabled', 1, 'core_competency');

pilot_default('lang', 'en');
pilot_default('timezone', getenv('MOODLE_TIMEZONE') ?: 'UTC');

pilot_say('site settings: applied');
