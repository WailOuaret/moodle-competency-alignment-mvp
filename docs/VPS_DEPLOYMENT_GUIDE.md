# Private teacher pilot: VPS deployment guide

**Status: the private pilot is online at https://srv1872740.hstgr.cloud/ .** This is not a public
release and it is not claimed to be production ready. The academy site on the same VPS was left
unchanged. **REBOOT TEST: DEFERRED — REQUIRES MAINTENANCE WINDOW.**

What was checked on the server on 4 October 2026, without a reboot and without changing the academy:

- HTTPS on the pilot host answers (HTTP 303 to the login flow). The academy site answers HTTP 200.
- Host nginx is 1.24.0, so the pilot server block uses `listen 443 ssl http2` (this nginx has no `http2 on;`).
- PostgreSQL and the alignment API are not published on a host port. Moodle is published only on 127.0.0.1:8080.
- Public listeners seen: 22, 80, 443, and 3000. Port 3000 is the academy and was not changed.
- UFW could not be read: `sudo` asks for a password. No firewall rule was changed.
- Docker, nginx and MySQL are enabled at boot. The four pilot containers use `restart: unless-stopped`.

**PUBLIC DISTRIBUTION REQUIRES LICENSING/IP CONFIRMATION.** This is a private pilot for a handful of
named teachers. It is not a release, and "production ready" is not claimed anywhere.

Companion documents: docs/PILOT_OPERATIONS_RUNBOOK.md (running it), docs/TEACHER_PILOT_CHECKLIST.md
(the gates before teachers are invited), docs/PLUGIN_ADMIN_GUIDE.md, docs/PLUGIN_PACKAGING_GUIDE.md.

## 1. What is being deployed

```
                         Internet
                            |  443 / 80
                  +---------v----------+      host nginx (already on the server for another site)
                  |  nginx, TLS, rate  |      a NEW server block for the pilot's host name only
                  |  limits            |
                  +---------+----------+
                            | 127.0.0.1:8080   (never a public address)
          +-----------------v-------------------+
          |  moodle  (Apache + PHP 8.3, plugin)  |---+ compalign_data (internal, no route out)
          |  moodle-cron (loop, every 20 s)      |   |
          +-----------------+-------------------+   |    +-----------------------+
                            | compalign_internal    +----|  db  (PostgreSQL 16)  |
                            | http://172.29.80.10   |    |  Moodle's only DB     |
          +-----------------v-------------------+        +-----------------------+
          |  alignment-api (FastAPI, non-root,    |------> model provider (HTTPS, outbound)
          |  read-only, /docs off, port 80 inside)|
          +---------------------------------------+
```

- One database, PostgreSQL, **for Moodle only**. The alignment service keeps nothing (it is stateless).
- Moodle reaches the service on a **private Docker network**, at a fixed IP address. There is no
  `host.docker.internal` and no published port for the service. **8001 and 5432 are never published.**
- Only one container port is published, Moodle's web port, and only on `127.0.0.1`.
- TLS ends at the host's nginx. HTTPS is a precondition for inviting a teacher.
- Moodle's cron runs in its own container, in a loop, and restarts with Docker.
- The service runs as an unprivileged user, on a read-only file system, with no capabilities, with
  its interactive API docs switched off.
- Pilot mode: write-back off, debug off, errors hidden, no email, a private site (login required, no
  sign-up, no guests).

## 2. What has been tested, and what has not

Tested on the development machine (Docker Desktop, 4 October 2026), not on the VPS:

| What | Result |
|---|---|
| Alignment image: builds, runs as uid 10001 on a read-only file system, `/docs`, `/openapi.json` and `/redoc` answer 404, no token and a wrong token answer 401, a real mock analysis answers 200, the token does not appear in the log | PASS |
| The service's tests against the same pinned dependency set (121 tests) | PASS |
| Moodle image build, install, provisioning scripts, cron, the plugin working end to end, backup and restore | see section 12 for the current result |

Not tested at all, because it needs the real server: nginx, TLS, firewall, behaviour across a reboot,
the real model (no model call has ever been made: only the mock backend has run), anything about the
VPS's resources.

## 3. Step V1: audit the VPS first (read-only, installs nothing)

Do this before anything else. It changes nothing on the server.

What the assistant learned **from outside**, without logging in:

| Fact | Value |
|---|---|
| Host | one Hostinger KVM 2 VPS (its address and name are not written in this document on purpose: it is committed to a repository) |
| Operating system | Ubuntu 24.04, OpenSSH 9.6p1 |
| Listening ports seen from outside | 22, 80, 443 |
| Web server | nginx 1.24.0 on port 80 |
| **An existing production site** | another project's site is served from this machine on 443 with a Let's Encrypt certificate, and a default HTTPS server block answers any other host name. Its domain is deliberately not written here |
| SSH | password login is still enabled (`publickey,password`) |

**There is a live production site on this server.** Everything below is designed not to disturb it: the
pilot gets its own host name, its own nginx server block, its own certificate, its own Docker networks
and volumes, and no change to the existing site's configuration. But nginx, the firewall and Docker
are shared with it, so every step that touches them is listed in section 4 for your approval.

What still has to be learned from **inside** the server (run as the dedicated `claude` account; all
read-only):

```bash
whoami; hostname; hostnamectl; uname -a; cat /etc/os-release; uptime
df -h; free -h; lsblk; ip addr
ss -tulpn
systemctl --failed
docker --version; docker compose version; nginx -v; apache2 -v; php -v; python3 --version; git --version
sudo -n ufw status verbose          # needs sudo; if it fails, note it and ask the root console
sudo -n true && echo "sudo works without a password" || echo "no passwordless sudo"
docker ps; docker network ls; docker volume ls        # if Docker exists and the account may use it
sudo -n nginx -T 2>/dev/null | grep -nE 'server_name|listen|ssl_certificate'    # which names and ports nginx owns
```

The questions the audit has to answer, and what each answer changes:

| Question | If yes | If no |
|---|---|---|
| Is Docker (with the compose plugin) installed? | use it | installing it is privileged step P1 and is a change to the shared server: ask |
| Is the server's RAM and disk enough? The pilot needs about 3 GB of RAM at most and about 10 GB of disk to start | continue | stop and reconsider the size |
| Does anything already use port 8080 or the subnet 172.29.80.0/24? | pick another (`MOODLE_HOST_PORT`, `PILOT_SUBNET`, `ALIGNMENT_IP`) | keep the defaults |
| Which `server_name` entries does nginx own, and is the default HTTPS server block a catch-all? | the pilot's name must not be one of them | fine |
| Is the firewall active, and what does it allow? | only 22, 80 and 443 may be open | do not enable it blindly: enabling UFW on a live server can lock out SSH. Add `allow 22` first |
| Does passwordless sudo exist for `claude`? | see section 4 for how little is needed | stop and list the privileged actions (section 4): you run them |

**If the audit shows another project running that the plan would affect, stop and report before
changing ports, nginx or the firewall.**

## 4. Privileged actions, and how little sudo they need

The deployment itself needs **no root**: it runs as the `claude` account, which only needs permission to use
Docker. The privileged actions are exactly these. Each is a change to the shared server and is done
**only after you approve it**. You may do all of them yourself in the Hostinger console as root instead of
giving the assistant any sudo.

| # | Action | Why | Needed if |
|---|---|---|---|
| P1 | Install Docker Engine and the compose plugin | to run the stack | Docker is not installed |
| P2 | Let `claude` use Docker: `usermod -aG docker claude` | to run `docker compose` | not already allowed. **Docker access is equivalent to root on this machine.** Treat it as such, and remove it afterwards if the account is not needed |
| P3 | `mkdir /opt/compalign-pilot` owned by `claude` | where the pilot lives | always |
| P4 | Install the nginx server block and the proxy snippet, `nginx -t`, reload | to serve the pilot over HTTPS | always |
| P5 | Obtain a certificate for the pilot's host name (`certbot certonly --webroot`) | HTTPS | always |
| P6 | Confirm the firewall allows only 22, 80 and 443 | nothing else public | always (a read; a change only if it differs) |
| P7 | DNS record for a custom host name | only if you choose one | custom host name |
| P8 | `systemctl enable docker` | the stack comes back after a reboot | not already enabled |

**Minimal sudo, if you want the assistant to do P4 to P6.** A drop-in file limited to the commands
needed, created by you as root:

```
# /etc/sudoers.d/claude-pilot   (mode 0440; check it with: visudo -cf /etc/sudoers.d/claude-pilot)
claude ALL=(root) NOPASSWD: /usr/sbin/nginx -t, /usr/bin/systemctl reload nginx, \
    /usr/bin/certbot certonly --webroot -w /var/www/certbot -d PILOT-HOST-NAME, \
    /usr/sbin/ufw status verbose, /usr/sbin/ufw status
```

That allows testing and reloading nginx, issuing this one certificate, and *reading* the firewall. It does not allow
editing files in `/etc/nginx` (you copy the rendered configuration there yourself, or approve a one-time `install`
line), changing the firewall, installing packages, or opening a shell. Replace `PILOT-HOST-NAME` with the one you choose.

**Removing sudo again** (do this when the deployment is finished, whatever you chose):

```bash
sudo rm /etc/sudoers.d/claude-pilot       # the drop-in above, or a temporary broader one
sudo gpasswd -d claude docker             # take Docker access away if the account is not needed any more
sudo visudo -c                            # must say "parsed OK"
sudo -l -U claude                         # must show nothing you did not intend
```

If you give broader temporary sudo (for example `claude ALL=(ALL) NOPASSWD: ALL`), put an expiry on it: write down the date,
and run the commands above on that date.

**If sudo is unavailable, the assistant stops here** and you run P1 to P8 yourself, using sections 7 to 9.

## 5. Decisions needed from you

1. **The pilot's host name.** Either:
   - **The provider's own host name for the server** (`srvNNNNNNN.hstgr.cloud`, shown in the Hostinger panel): it already
     resolves to this server, needs no DNS work, and Let's Encrypt can issue for it. The name is the provider's, not yours,
     and it looks like it.
   - A host name on a domain you control, such as `pilot.example.org`: nicer for teachers, but you must create an A record
     for the server's address first. **Do not use a subdomain of the existing production site's domain**: it is a
   different project, and a subdomain shares cookies and trust with it.
2. **How the code reaches the server** (section 6): push the feature branch, or send a private build.
3. **Whether to grant sudo** (section 4) or run P1 to P8 yourself.

## 6. Getting the code onto the server

Do **not** clone from GitHub unless the branch has been pushed: the work is on `feature/moodle-plugin`, which is
**not pushed**, so a clone would give stale code.

**Option A, "PUSH FEATURE BRANCH".** You (or the assistant, only when you say so) push `feature/moodle-plugin`, and the
server runs `git clone --branch feature/moodle-plugin` into `/opt/compalign-pilot/app`. A deploy key with read-only
access is the right credential. Publishing the branch makes the code visible to whoever can see the repository, which
matters while the licensing question is open.

**Option B, "RSYNC PRIVATE PILOT BUILD".** Nothing is pushed. The build is a tarball of exactly the files
the images need, taken from one commit:

```bash
scripts/package-pilot-build.sh        # writes dist/compalign-pilot-build-<commit>.tar.gz, a file list, and a checksum
```

Read the file list it prints before anything is sent. It contains, and only contains:

- `deploy/pilot/` (compose file, Dockerfiles, scripts, templates, sample Pages, `.env.example`)
- `moodle-plugin/compalign/` (without its tests)
- `service/`
- `src/moodle_competency/` (the engine, unchanged)
- `data/processed/competencies.jsonl` (the 13 competencies)
- the pilot documents under `docs/`

It does not contain `.git`, `.env`, any key, the research data, the tests, `prombt.md`, or anything about the VPS. Then:

```bash
scp dist/compalign-pilot-build-<commit>.tar.gz claude@<server host name>:/opt/compalign-pilot/
ssh claude@<server host name> 'cd /opt/compalign-pilot && sha256sum -c compalign-pilot-build-<commit>.tar.gz.sha256 && mkdir -p app && tar -xzf compalign-pilot-build-<commit>.tar.gz -C app'
```

(The checksum file travels with it; `rsync -av` works the same way if rsync is installed.) Updates repeat the same two steps and then run
`scripts/update.sh`.

Either way, check afterwards that what is on the server is what you meant: `git rev-parse HEAD` (A), or compare the checksum (B).

## 7. Steps V2 to V6, on the server

Once the audit is understood and the approvals are given. `$HOST` is the pilot's host name.

**V2: layout.**

```bash
sudo mkdir -p /opt/compalign-pilot && sudo chown claude:claude /opt/compalign-pilot        # P3
mkdir -p /opt/compalign-pilot/{private,backups,logs,releases}
chmod 700 /opt/compalign-pilot/private /opt/compalign-pilot/backups
echo 'export PILOT_HOME=/opt/compalign-pilot' >> ~/.profile && export PILOT_HOME=/opt/compalign-pilot
```

Put the code in `/opt/compalign-pilot/app` (section 6). The scripts are in `app/deploy/pilot/scripts`.

**V3: the environment file.**

```bash
cd /opt/compalign-pilot/app/deploy/pilot
scripts/init-env.sh        # creates /opt/compalign-pilot/private/pilot.env, mode 600, secrets generated, nothing printed
```

Then edit **the non-secret values** in that file: `MOODLE_WWWROOT=https://$HOST`; `MOODLE_HOST_PORT`, `PILOT_SUBNET` and `ALIGNMENT_IP`
if the audit found a clash. `ALIGNMENT_BACKEND` stays `gemini`. **The model key stays empty until the one authorised live test**
(step V7). `MOODLE_WWWROOT` is fixed into Moodle at install time, so set it right before the first start.

**V4: build and start.**

```bash
scripts/compose.sh config --quiet && echo "compose file is valid"
scripts/compose.sh up -d --build
scripts/compose.sh logs -f moodle        # the first start installs Moodle: allow about 5 to 10 minutes
```

Wait until `scripts/compose.sh ps` shows all four containers running, and `moodle` healthy. The first start installs Moodle,
the plugin, the framework (13 competencies), the pilot course and its six Pages. Moodle answers on `127.0.0.1:8080` now, and nowhere else.

**V5: nginx and HTTPS (P4, P5).**

```bash
scripts/render-nginx.sh http     # review this
sudo install -m 0644 <(scripts/render-nginx.sh http) /etc/nginx/sites-available/compalign-pilot.conf
sudo install -m 0644 <(scripts/render-nginx.sh snippet) /etc/nginx/snippets/compalign-pilot-proxy.conf
sudo mkdir -p /var/www/certbot
sudo ln -s /etc/nginx/sites-available/compalign-pilot.conf /etc/nginx/sites-enabled/compalign-pilot.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/certbot -d "$HOST"
scripts/render-nginx.sh full     # review: this is the real configuration
sudo install -m 0644 <(scripts/render-nginx.sh full) /etc/nginx/sites-available/compalign-pilot.conf
sudo nginx -t && sudo systemctl reload nginx
```

Before the first `sudo nginx -t`, run `sudo nginx -T | grep -n server_name` and confirm that `$HOST` appears nowhere else. After
the reload, **check that the existing site still works** (`curl -I https://<the existing site's address>`). If `nginx -t` fails, do not reload:
fix the file or remove the symlink. Certificate renewal is certbot's existing timer; confirm with `systemctl list-timers | grep certbot`.

**V6: firewall, cron, backups, reboot.**

- Firewall (P6): `sudo ufw status verbose` must allow **only 22, 80 and 443**. Docker publishes ports by its own firewall rules,
  which UFW does not filter, so the real protection is that the stack publishes nothing but `127.0.0.1:8080`. `scripts/healthcheck.sh --readiness`
  checks that 5432, 8001 and the Moodle port are not on a public address.
- Moodle's cron is already running (the `moodle-cron` container). Check: `scripts/compose.sh logs --since 5m moodle-cron`.
- Backups: install the crontab in `deploy/pilot/host/crontab.example` for the `claude` account; run `scripts/backup.sh` once by hand now and
  `scripts/restore.sh` into a scratch check (the backup script does this) before relying on it.
- **Reboot test.** `sudo reboot`, wait, log in, then `scripts/compose.sh ps` and `scripts/healthcheck.sh`. All four containers must come
  back by themselves, cron must be running again, and a new analysis request must be picked up. Do it once before the pilot, in a quiet hour,
  and tell the owner of the other site first: a reboot takes it down for a minute or two.
- `scripts/healthcheck.sh --readiness` must end in `HEALTHY` before any later step.

Then continue with docs/TEACHER_PILOT_CHECKLIST.md: V7, the one authorised live-model test; V8, clearing the test records; V9, the
seven teacher accounts; V10, the readiness review.

## 8. If something goes wrong: undoing the deployment completely

Nothing the pilot does touches the existing site, so removing it is also contained:

```bash
cd /opt/compalign-pilot/app/deploy/pilot
scripts/backup.sh --label final                         # keep a copy of the data first
scripts/compose.sh down                                 # stops and removes the containers and networks, keeps the data volumes
# only when the data is no longer wanted, and you have the final backup:
scripts/compose.sh down -v                              # also deletes the database and Moodle's data
sudo rm /etc/nginx/sites-enabled/compalign-pilot.conf /etc/nginx/sites-available/compalign-pilot.conf /etc/nginx/snippets/compalign-pilot-proxy.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot delete --cert-name "$HOST"
```

Then remove sudo and Docker access (section 4).

## 9. Coexistence risks to keep in mind

| Risk | Mitigation in the design |
|---|---|
| The pilot's nginx block captures the production site's traffic | it names only the pilot's host name; check `nginx -T` for a clash before reload; test the production site straight after |
| A bad nginx file takes the production site down at reload | `nginx -t` before every reload; keep the old file; the rendered files are short and reviewed first |
| Memory pressure from the pilot slows the production site | containers have memory limits (about 4.5 GB in total, normally far less); look at `free -h` and `docker stats` during the first analyses |
| Disk fills up from images, logs and backups | Docker logs rotate at 10 MB x 5 per container; backups keep 14; `healthcheck.sh` fails at 90 % |
| Docker's firewall rules interact with the existing UFW setup | only `127.0.0.1:8080` is published; no `iptables` or UFW rule is changed by this guide |
| Docker group membership is root-equivalent | grant it deliberately, remove it afterwards (section 4) |
| A reboot interrupts the other site | do the reboot test at an agreed time |
| Password SSH login is still enabled on the server | outside the scope of this pilot, but worth fixing: it is the most likely way into the machine |
| The model key is a secret with a spending effect | enter it only with `scripts/set-secret.sh`; set a spending cap at the provider before the live test |

## 10. Host key fingerprints

The assistant pinned the server's SSH host keys on first contact, from the network. **That does not prove they are the server's**, because
nothing outside the network vouched for them. Compare them yourself, in the Hostinger console:

```bash
for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf "$f"; done
```

and check the output against the fingerprints in the assistant's report. If they differ, stop: someone is in the middle.

## 11. Rollback of an update

`scripts/update.sh` takes a backup, keeps the previous images, and checks health afterwards. `scripts/rollback.sh --yes-replace-live-data`
returns to the previous images **and** to the data as it was before the update (a Moodle upgrade cannot be undone by starting older
code). Whatever teachers saved after the update is lost on that rollback: tell them first.

## 12. Result of the local trial of the deployment files

Tried on the development machine on 4 October 2026. This is not a trial on the VPS, and it is not a trial of nginx, TLS, the firewall or a reboot.

| What | Result |
|---|---|
| `scripts/init-env.sh` | Created the env file outside the repository, mode 600, with generated secrets. Nothing was printed. |
| `scripts/compose.sh config --quiet` | The compose file is valid. |
| Alignment image | Built. Ran as uid 10001 on a read-only file system, with no published port. `/health` answered 200. `/docs`, `/openapi.json` and `/redoc` answered 404. A missing token and a wrong token answered 401. One mock analysis answered 200. The token did not appear in the container log. |
| Service tests on the pinned dependency set | 121 passed (`tests/service` and `tests/test_runtime_analysis.py`). |
| The single-address carve-out in `moodle/config.php` | The function was run on its own, against the real file, for 172.16.0.0/12, 10.0.0.0/8, 192.168.0.0/16 and 127.0.0.0/8. Each range stayed covered except the one address. An address outside a range leaves that range unchanged. |
| PHP and shell syntax | `php -l` on `config.php` and the provisioning scripts, and `sh -n` on the entrypoint and cron loop, reported no errors. `shellcheck` on the scripts reported style notes only. |
| Moodle image, install, provisioning, cron, backup and restore | **Not run.** The Moodle image build did not finish. The Debian package mirror refused a large share of connections from this machine, and then Docker Desktop's WSL data disk failed while BuildKit was writing its metadata database. Restarting Docker Desktop made it report that the data disk had no file system and try to format it. The format did not succeed, so the disk was not wiped, and Docker Desktop was stopped so the restart loop would not try again. The Moodle sandbox volumes live on that disk. Do not reset Docker to factory defaults: that would delete them. Start Docker again only after the data disk mounts. Until then the local stack cannot be brought up, and nothing in the "not run" row above has been shown. |
