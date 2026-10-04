#!/bin/sh
# Entrypoint of the pilot's Moodle image.
#
#   web   (default) wait for the database, install or upgrade Moodle, apply the pilot's settings,
#                   create the framework and the course, then run Apache
#   cron            wait until the web container has finished, then run Moodle's cron in a loop
#   cli ...         run a command as www-data (for `docker compose run`)
#
# Only the web container installs and upgrades. The cron container waits for it.
set -eu

say() { printf '%s pilot: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
as_web() { runuser -u www-data -- "$@"; }
provision() { script="$1"; shift; as_web php "/opt/pilot/provision/$script" "$@"; }

wait_for_db() {
    tries=0
    until php /opt/pilot/provision/db_ready.php; do
        tries=$((tries + 1))
        if [ "$tries" -ge 90 ]; then
            say "the database did not answer after 3 minutes"
            exit 1
        fi
        sleep 2
    done
}

fix_permissions() {
    # A new volume is owned by root. Only touch it when it is not already www-data's.
    if [ "$(stat -c %U /var/www/moodledata)" != "www-data" ]; then
        chown -R www-data:www-data /var/www/moodledata
    fi
    chmod 2770 /var/www/moodledata
}

install_or_upgrade() {
    if php /opt/pilot/provision/db_ready.php --installed; then
        set +e
        as_web php /var/www/html/admin/cli/upgrade.php --is-pending
        pending=$?
        set -e
        case "$pending" in
            0) say "Moodle is installed and up to date" ;;
            2)
                say "an upgrade is pending: running it"
                as_web php /var/www/html/admin/cli/upgrade.php --non-interactive
                ;;
            *) say "could not tell whether an upgrade is pending (exit $pending)"; exit 1 ;;
        esac
    else
        say "Moodle is not installed: installing (this takes a few minutes)"
        : "${MOODLE_ADMIN_PASSWORD:?MOODLE_ADMIN_PASSWORD is not set}"
        : "${MOODLE_ADMIN_EMAIL:?MOODLE_ADMIN_EMAIL is not set}"
        as_web php /var/www/html/admin/cli/install_database.php \
            --lang=en \
            --adminuser=admin \
            --adminpass="$MOODLE_ADMIN_PASSWORD" \
            --adminemail="$MOODLE_ADMIN_EMAIL" \
            --fullname="${MOODLE_SITE_NAME:-Competency Alignment Pilot}" \
            --shortname="${MOODLE_SITE_SHORTNAME:-CA Pilot}" \
            --supportemail="$MOODLE_ADMIN_EMAIL" \
            --agree-license
    fi
}

mode="${1:-web}"
case "$mode" in
    web)
        wait_for_db
        fix_permissions
        install_or_upgrade
        provision site.php
        frameworkid="$(provision framework.php)"
        provision plugin.php "$frameworkid"
        provision course.php
        as_web php /var/www/html/admin/cli/purge_caches.php
        say "ready: starting Apache"
        exec apache2-foreground
        ;;
    cron)
        say "waiting for Moodle to be installed and up to date"
        until wait_for_db && php /opt/pilot/provision/db_ready.php --installed \
              && as_web php /var/www/html/admin/cli/upgrade.php --is-pending >/dev/null 2>&1; do
            sleep 10
        done
        exec /usr/local/bin/pilot-cron
        ;;
    cli)
        shift
        exec runuser -u www-data -- "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
