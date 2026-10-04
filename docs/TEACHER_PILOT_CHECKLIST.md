# Teacher pilot: gates and checklist

**Status: DRAFT. Every box below is unchecked. No teacher may be invited until every gate in section 1 is met and a person has signed it
off.** Each item names the command or the evidence that proves it. "Done" without that evidence does not count.

PUBLIC DISTRIBUTION REQUIRES LICENSING/IP CONFIRMATION. This is a private pilot of seven named teachers.

Companion documents: docs/VPS_DEPLOYMENT_GUIDE.md, docs/PILOT_OPERATIONS_RUNBOOK.md, docs/TEACHER_PILOT_GUIDE.md.

## Where things stand (4 October 2026)

| Phase | What | State |
|---|---|---|
| V1 | Audit the VPS, read-only | **BLOCKED**: the assistant could not log in (key not accepted). Only an outside-in look was possible. A live production site shares the server |
| V2 | Deployment files and documents | written and tried locally (a local trial on a development machine, not on the server) |
| V3 | Checkpoint E: a person checks the screens in a browser | **PENDING** (docs/MOODLE_PLUGIN_BROWSER_CHECKLIST.md). PHPUnit passed (295 tests) |
| V4 | Checkpoint F (write-back) or keep write-back off | **write-back stays off for the pilot.** F has not started, and only starts after V3 passes |
| V5 | Install on the VPS | not started |
| V6 | HTTPS, cron, backup, firewall, reboot test | not started |
| V7 | One authorised live-model test | **not authorised**, preconditions not met |
| V8 | Clear test records, record the start | not started |
| V9 | Create the seven teacher accounts, test access | not started |
| V10 | Readiness review, then invite | not started |

## 1. Gates: all must be true before the first invitation

**Safety and privacy**

- [ ] The site is reached over **HTTPS** with a valid certificate (`scripts/healthcheck.sh --readiness`: "public HTTPS answers with a valid certificate").
- [ ] Plain http redirects to https (same command).
- [ ] The firewall allows only 22, 80 and 443, and 5432, 8001 and the Moodle port are not on a public address (same command; and `sudo ufw status verbose`).
- [ ] The existing production site on the server still works, checked after every nginx reload.
- [ ] The site requires login, has no sign-up and no guest access (`report.php --check` passes: "site requires login", "self registration is off").
- [ ] Debug is off and errors are not shown (check "debug is off"; and open a nonexistent page: Moodle's plain error, no stack trace).
- [ ] No email is sent (`MOODLE_ALLOW_EMAIL=0`; the placeholder addresses end in `.invalid`).
- [ ] Write-back is off and no role holds the write-back capability (check "write-back is off"; `access_test.php` confirms teachers lack it).
- [ ] **A teacher cannot see anything that looks like an answer key** (checklist item 13 of the browser checklist).
- [ ] The service's `/docs`, `/openapi.json` and `/redoc` are not reachable (`curl` from inside the network answers 404). Done locally for the image; repeat on the server.
- [ ] The service runs as a non-root user (`scripts/compose.sh exec alignment-api id` shows uid 10001).
- [ ] No secret is in Git, in the package, in a log, or on a command line. `git grep -nE 'AIza|BEGIN .*PRIVATE KEY|ALIGNMENT_SERVICE_TOKEN=[A-Za-z0-9_-]{16,}'` returns nothing; `grep -c <token> <logs>` is 0.
- [ ] The consent statement, the data-retention period, the contact for withdrawal and the contact address in the teachers' guide are **written and approved** (the guide has marked gaps for them).
- [ ] The names of the people behind T001 to T007 are held only in the organiser's private list, not on the server and not in the repository.

**Does it work**

- [ ] **Checkpoint E browser checklist: all 24 items PASS**, reported by a person, with screenshots for any FAIL fixed and re-checked.
- [ ] The four containers come back by themselves after a **reboot**, cron runs again, and a new analysis is picked up (done once, on the server, at an agreed time).
- [ ] Cron runs at least once a minute: `scripts/compose.sh logs --since 5m moodle-cron` shows a run line about every three minutes with the loop restarting within 20 seconds, and the healthcheck's "cron ran in the last 5 minutes" passes.
- [ ] A backup was taken, **and a restore was done from it onto a scratch project**, and the restored site showed the saved decisions (`scripts/backup.sh` verifies the dump loads; the drill proves the whole thing).
- [ ] `scripts/update.sh` then `scripts/rollback.sh` were run once on the server, and the site came back healthy (do this before the live test, not after).
- [ ] **The model backend is not the mock** (`ALIGNMENT_BACKEND=gemini`), and the one authorised live test (V7) passed.
- [ ] A **spending cap and an alert** are set on the model key at the provider, before the live test.
- [ ] `scripts/healthcheck.sh --readiness` ends in `HEALTHY`.

**Control of the study**

- [ ] The test records are cleared (`scripts/clear-test-data.sh --delete`) and the plugin tables are empty.
- [ ] `PILOT_RECORD.json` exists: start time (UTC), commit, engine hash, versions, settings (`scripts/record-pilot-start.sh`).
- [ ] The research files that are frozen are unchanged: the 21 protected files hash exactly as they did before this work; `src/moodle_competency` and `runtime_analysis.py` are untouched.
- [ ] Top-K is 5. Write-back is off. The study export (Checkpoint H) is **not** needed to start, but its absence is understood: the raw data is preserved in backups only.

## 2. Phase V7: the one authorised live-model test

**Do not run this until the owner says so, in words.** Preconditions, all of them:

- [ ] PHPUnit passes (done: 295 tests, 955 assertions).
- [ ] The browser checklist passes (V3).
- [ ] The site is on the server, over HTTPS, healthy.
- [ ] The test records so far are development records, and the owner knows they will be deleted at V8.
- [ ] No student data can be in the payload: the payload is the text of one sample Page and the 13 competencies. The sample Pages contain no personal data.
- [ ] Token handling is right: the token is stored encrypted, and appears in no log.
- [ ] The mock flow is stable (the checklist's mock runs passed).
- [ ] A spending cap and alert are set at the provider.
- [ ] The model key was entered with `scripts/set-secret.sh GEMINI_API_KEY`, never in a command line or a chat.

The test: as the administrator, open the pilot course, analyse **one** sample Page (for example "Testing and Continuous Delivery of Software"),
and read the result. Check: it completes; the evidence quotations appear word for word in the Page; the suggestions are among the 13 competencies;
nothing in the page looks like raw model output or a stack trace; the model name in the stored analysis is the one you expect. Then stop: one
analysis, no repeats. Record the result, the model name, and the duration. Do not press Reanalyse.

## 3. Phase V8: before the first teacher

```bash
scripts/clear-test-data.sh --delete        # backup first, then confirm by typing
scripts/healthcheck.sh --readiness         # HEALTHY
scripts/record-pilot-start.sh              # PILOT_RECORD.json
```

## 4. Phase V9: the seven accounts

```bash
scripts/provision-teachers.sh              # creates teacher01..teacher07 (T001..T007); credentials go to a private file, not the screen
scripts/test-teacher-access.sh             # 7 PASS lines, then "ALL 7 ACCOUNTS PASS"
```

- [ ] Seven accounts, each `teacher0N` with ID number `T00N`, each a **Teacher in COMPALIGN-PILOT only** and no system-wide role.
- [ ] Each has its own random password, 20 characters, and must change it at first login.
- [ ] The credentials are in `private/teacher_credentials.csv`, mode 600, and nowhere else: not in Git, not in a log, not in this checklist.
- [ ] The placeholder addresses end in `.invalid`. No email was sent.
- [ ] `test-teacher-access.sh` printed ALL 7 ACCOUNTS PASS.
- [ ] One teacher account was logged into **by a person in a browser**, the password changed, and the plugin used (do this with an account you will then reset: `scripts/teacher-account.sh reset-password teacher07`).
- [ ] The operations runbook's account commands (status, suspend, unsuspend, reset-password) were each tried once.

## 5. Onboarding each teacher

- [ ] The teacher has read docs/TEACHER_PILOT_GUIDE.md and the consent statement, and agreed.
- [ ] You told them their code (T00N) and gave them the address, username and temporary password **separately from each other**, by a channel that is not the same email thread.
- [ ] They logged in, changed the password, and reviewed one Page with you or the guide.
- [ ] You told them who to contact, and that they may stop at any time.

## 6. During the pilot

Daily: `scripts/healthcheck.sh`. Weekly: model-call count, disk, newest backup, accounts. The system is **frozen**: no update unless a defect requires it, and
every change is written down with the date and the reason, because the study treats the system as fixed. Nobody touches the data except through the
documented commands.

## 7. Report template: "UTC TEACHER PILOT ACCOUNTS"

To be produced when V9 is done. It states facts only, and contains no password.

```
UTC TEACHER PILOT ACCOUNTS
  created (UTC):        <time>
  accounts:             teacher01..teacher07  ->  T001..T007 (ID number)
  role:                 Teacher in COMPALIGN-PILOT only; no system-wide role
  passwords:            random, 20 characters, CSPRNG; change forced at first login; stored only in <path>, mode 600
  email:                placeholder addresses at .invalid; no email sent
  access test:          <ALL 7 ACCOUNTS PASS | failures>
  credentials in Git:   no (verified: git grep)
  credentials printed:  no
  pilot start record:   <path, time>
  not done:             <anything left>
```
