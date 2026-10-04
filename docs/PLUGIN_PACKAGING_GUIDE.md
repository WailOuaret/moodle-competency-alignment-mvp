# Packaging the plugin (private pilot build)

**Status: DRAFT.** The packaging script exists and was tried locally (see the end of this page for the
result). The package has **not** been installed through Moodle's "Install plugins" screen, and it has
installed inside the private pilot image on the VPS. The zip is not published.

**PUBLIC DISTRIBUTION REQUIRES LICENSING/IP CONFIRMATION.** The package is for the private pilot. Do not
upload it to the Moodle Plugins Directory, Packagist, GitHub Releases or anywhere public, and do not add a
repository-wide LICENSE, until the licensing question is settled (see docs/MOODLE_PLUGIN_ARCHITECTURE.md,
"Release blockers"). The plugin's own source files carry GPL v3 headers because Moodle plugins are conventionally
GPL; that is not a decision to publish.

## What the package is

The hosted pilot package is `dist/local_compalign-0.2.0-pilot.zip`. A later local package may be `dist/local_compalign-0.3.0-pilot.zip` from branch `feature/moodle-multiresource`. Do not install the 0.3.0 zip on the hosted pilot.

`dist/local_compalign-0.2.0-pilot.zip`: the plugin folder `compalign/`, as Git has it at the current commit,
without its tests. It is what Moodle's **Site administration, Plugins, Install plugins** accepts, and what
the pilot's Docker image copies into `public/local/compalign`.

| In the package | Not in the package |
|---|---|
| `version.php`, `settings.php`, `lib.php`, `index.php`, `review.php` | `tests/` (kept in the repository; `--with-tests` adds them) |
| `classes/`, `db/`, `lang/`, `templates/` | `.git`, `.env` and anything like it |
| | keys, tokens, credentials, notes (`prombt.md`), logs, caches |
| | anything about the VPS |
| | the alignment service and the research engine (they are separate: the plugin only talks to the service over HTTP) |

## Building it

```bash
scripts/package-plugin.sh                 # from deploy/pilot; writes dist/local_compalign-<release>-pilot.zip and a .sha256
scripts/package-plugin.sh --with-tests    # includes tests/, for a developer's own site
```

`<release>` is read from `$plugin->release` in `moodle-plugin/compalign/version.php` (now `0.2.0`).

The script:

1. refuses to run if the plugin directory has uncommitted changes (the package is built from `HEAD`, so what you tested is what you ship);
2. builds the zip with `git archive`, so only tracked files can get in, with `compalign/` as the single top-level folder;
3. refuses to finish if the file names look private (`.env*`, `*.pem`, `*.key`, `id_*`, anything with `credentials` or `secret` in the name) or any file's text looks
   like a Google API key, a private key block or a service token;
4. checks that `compalign/version.php` is present, and, where PHP is installed, that every PHP file parses;
5. writes `dist/<name>.zip.sha256` next to it.

`dist/` is ignored by Git on purpose. The package is a build product, not source.

## Checking a package by hand

```bash
unzip -l dist/local_compalign-0.2.0-pilot.zip | less        # every file; the first entry is compalign/
sha256sum -c dist/local_compalign-0.2.0-pilot.zip.sha256
unzip -p dist/local_compalign-0.2.0-pilot.zip compalign/version.php | grep -E 'component|version|release|maturity|requires'
```

Then, on a scratch Moodle 5.2 site (never on the pilot): upload it under Install plugins, confirm that Moodle
validates it as `local_compalign`, install it, and open the plugin's settings page.

## Version policy

| Field | Now | Rule |
|---|---|---|
| `$plugin->release` | `0.2.0` | the human-readable version. The package name carries it, with `-pilot` to say what it is for |
| `$plugin->version` | `2026100301` | date-stamped build number. **It must go up on every change that touches `db/`** so that Moodle upgrades the database |
| `$plugin->maturity` | `MATURITY_ALPHA` | stays ALPHA until a person has checked the screens in a browser and teachers have used it |
| `$plugin->requires` | `2026042001` | Moodle 5.2 |

Bump `version` and `release` only deliberately, in their own commit. A bump during the pilot changes the system the
study is measuring: the operations runbook says to avoid it.

## What a package does not tell you

A package that builds is not a plugin that works. What has actually been shown, and what has not:

| Claim | Evidence |
|---|---|
| The code behaves as designed | 295 PHPUnit tests on Moodle 5.2.1+ |
| The screens look and read right | **not shown.** The browser checklist (docs/MOODLE_PLUGIN_BROWSER_CHECKLIST.md) is pending a person |
| It installs through the Install plugins screen | **not shown** |
| It works on other Moodle versions | **not claimed** |
| It works with a real model | **not shown.** Only the mock backend has run |

## Result of the local trial

`scripts/package-plugin.sh` was run on 4 October 2026 against commit `d2ea82f` (the plugin directory had no uncommitted changes). It wrote `dist/local_compalign-0.2.0-pilot.zip`: 35 files, 80K, tests excluded, sha256 `01c91614e8dbe1a72b43cbf83b56df61545463818b0d32692483e6607f9957be`. The archive is gitignored. It has not been uploaded through Moodle's Install plugins screen.
