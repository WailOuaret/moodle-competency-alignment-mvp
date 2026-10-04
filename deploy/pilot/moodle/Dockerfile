# Moodle for the private teacher pilot, with the Competency Alignment Assistant plugin built in.
#
# Build context is the repository root (see docker-compose.yml). The image holds Moodle code
# at a pinned commit, the plugin from this repository, and the provisioning scripts. It holds no
# secrets: every credential arrives as an environment variable at run time.

# ---- stage 1: Moodle source at one pinned commit -------------------------------------------------
# git comes with the image, so this stage needs no package mirror.
FROM alpine/git:2.47.2 AS moodle-src
ARG MOODLE_REPO=https://github.com/moodle/moodle.git
# MOODLE_502_STABLE, "weekly release 5.2.1+". This is the build the plugin was developed and
# tested on. Change it deliberately, then re-run the plugin's PHPUnit suite.
ARG MOODLE_COMMIT=519caca657e51b66970e00d45ab073de0c1b4b9c
RUN git init -q /moodle \
 && git -C /moodle remote add origin "$MOODLE_REPO" \
 && git -C /moodle fetch -q --depth 1 origin "$MOODLE_COMMIT" \
 && git -C /moodle checkout -q FETCH_HEAD \
 && test "$(git -C /moodle rev-parse HEAD)" = "$MOODLE_COMMIT" \
 && rm -rf /moodle/.git

# ---- stage 2: runtime ----------------------------------------------------------------------------
FROM php:8.3-apache-bookworm

# PHP extensions Moodle needs beyond the ones the base image already has. The development
# packages are removed again; the run-time libraries of what was built are kept.
RUN set -eux; \
    retry() { n=0; until "$@"; do n=$((n + 1)); [ "$n" -ge 40 ] && return 1; echo "retry $n: $*" >&2; sleep 5; done; }; \
    lists() { apt-get update >/dev/null 2>&1; ls /var/lib/apt/lists/*_Packages >/dev/null 2>&1 || ls /var/lib/apt/lists/*_Packages.* >/dev/null 2>&1; }; \
    retry lists; \
    retry apt-get install -y --no-install-recommends \
        libfreetype6-dev libjpeg62-turbo-dev libpng-dev libicu-dev libzip-dev libpq-dev libxml2-dev; \
    docker-php-ext-configure gd --with-freetype --with-jpeg; \
    docker-php-ext-install -j"$(nproc)" gd intl zip pgsql soap exif; \
    apt-mark auto '.*' >/dev/null; \
    find /usr/local -type f -executable -exec ldd '{}' ';' 2>/dev/null \
      | awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); print so }' \
      | sort -u | xargs -r dpkg-query --search | cut -d: -f1 | sort -u | xargs -r apt-mark manual; \
    apt-mark manual ca-certificates >/dev/null; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*; \
    php -m | tr '\n' ' ' | grep -q pgsql

# Apache: serve Moodle 5.2's public/ directory, let the router handle unknown paths, take the
# visitor's address from the reverse proxy, and say nothing about versions.
RUN a2enmod remoteip headers >/dev/null \
 && a2dismod -f status autoindex >/dev/null 2>&1 || true
COPY deploy/pilot/moodle/apache/moodle.conf /etc/apache2/conf-available/moodle.conf
RUN a2enconf moodle >/dev/null \
 && sed -ri 's#DocumentRoot /var/www/html#DocumentRoot /var/www/html/public#' /etc/apache2/sites-available/000-default.conf \
 && sed -ri 's#^ServerTokens .*#ServerTokens Prod#; s#^ServerSignature .*#ServerSignature Off#' /etc/apache2/conf-available/security.conf

COPY deploy/pilot/moodle/php/pilot.ini /usr/local/etc/php/conf.d/zz-pilot.ini

# Moodle, then the plugin on top of it.
COPY --from=moodle-src /moodle /var/www/html
COPY moodle-plugin/compalign /var/www/html/public/local/compalign
# The plugin's tests are not needed to run it. They stay in the repository.
RUN rm -rf /var/www/html/public/local/compalign/tests

COPY deploy/pilot/moodle/config.php /var/www/html/config.php
COPY deploy/pilot/moodle/provision /opt/pilot/provision
COPY deploy/pilot/moodle/data /opt/pilot/data
COPY data/processed/competencies.jsonl /opt/pilot/data/competencies.jsonl
COPY deploy/pilot/content/pages /opt/pilot/content/pages
COPY deploy/pilot/moodle/entrypoint.sh /usr/local/bin/pilot-entrypoint
COPY deploy/pilot/moodle/cron.sh /usr/local/bin/pilot-cron
RUN chmod 0755 /usr/local/bin/pilot-entrypoint /usr/local/bin/pilot-cron \
 && mkdir -p /var/www/moodledata \
 && chown -R www-data:www-data /var/www/moodledata \
 && chmod 0640 /var/www/html/config.php && chown root:www-data /var/www/html/config.php

WORKDIR /var/www/html
EXPOSE 80
# Healthy means "Apache and PHP answer": any reply below 500, redirects not followed (Moodle
# redirects a request whose Host is not the site address). 503 during an upgrade counts as down.
HEALTHCHECK --interval=30s --timeout=8s --start-period=180s --retries=5 \
  CMD ["php", "-r", "$c = stream_context_create(['http' => ['timeout' => 6, 'ignore_errors' => true, 'follow_location' => 0]]); @file_get_contents('http://127.0.0.1/login/index.php', false, $c); $l = $http_response_header[0] ?? ''; exit(preg_match('#^HTTP/\\S+ [1-4][0-9][0-9]#', $l) ? 0 : 1);"]

ENTRYPOINT ["/usr/local/bin/pilot-entrypoint"]
CMD ["web"]
