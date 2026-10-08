# Current project state

**Read this first.** It is the cold-start briefing for a new session: enough to
work correctly without any prior conversation. `docs/SUPERVISOR_HANDOFF.md`
remains the longer historical record.

**Last verified:** 2026-10-08
**Contains no credentials, hostnames or IP addresses.** Connection details live
outside the repository.

---

## A. Research purpose

Propose links between Moodle learning resources and competencies of a formal
framework, and present each proposal with a verbatim quotation from the source
so a teacher can verify it. The emphasis is verifiability, not autonomy: the
teacher decides, and the system must show its evidence.

## B. Frozen experiment — do not re-run or retune

The offline research phase is complete and its artefacts are frozen.

| Item | Value |
|---|---|
| Corpus | 20 resources, 35 fragments, 13 UTC GI competencies |
| Reference labels | 38, single annotator, no inter-annotator agreement |
| BM25 Recall@1/@3/@5 | 0.6842 / 0.8684 / 0.9737 |
| Constrained model micro P/R/F1 | 0.7255 / 0.9737 / 0.8315 |
| Evidence | 83/83 exact substrings; 65 rated 2, 16 rated 1, 2 rated 0 |

Also frozen: the controlled 8-resource multi-resource live Gemini check
(8/8 calls, 18/18 exact quotations). **Do not re-run it.**

Do not change BM25, the tokenizer, Top-K (5), the Gemini prompt (1.0), the
schema (1.0), max suggestions (3), or aggregation. Do not tune anything to make
the UI look better.

## C. Current Moodle architecture

```
Moodle resource
  → normalization / extraction
  → BM25 Top-5
  → constrained Gemini (gemini-3.5-flash, temp 0, ≤3 selections)
  → exact evidence validation
  → aggregation
  → teacher review
```

Analyses run as Moodle ad-hoc tasks, so **Moodle cron must be running** for
suggestions to appear. The Python alignment engine is the backend; it is not
reimplemented in PHP.

## D. Plugin release

| | |
|---|---|
| In the repository | **0.3.1 / 2026100701** |
| Deployed on the pilot | **0.3.1 / 2026100701**, commit `db1b859`, image tag `gdb1b859a348a` |
| Deployed at | 2026-10-08 18:15 UTC (0.3.1 first went live at 13:23 UTC as `048fbf9`) |
| Consistent? | The pilot runs exactly `origin/feature/moodle-plugin`. One local commit, `a3c0e22`, is not deployed. |

The deployed code includes the display fix `642a83d`: in the Competencies tab a
model proposal the teacher has decided now reads Accepted, Rejected or
Modified to X, never "Not reviewed". Verified on the live pilot against
teacher01's two acceptances.

**`a3c0e22` — committed locally, not pushed, not deployed.** Two small UI bugs
found by real-browser testing, both present on the pilot now:

1. On a phone the Competencies table hides its header but its cells had no
   labels, so a teacher saw "Reviewed" or "No" without the column name.
2. Add competency opened with the first competency of the framework already
   chosen, and saved it if the teacher submitted without picking one.

Neither affects stored data. Both fixes are tested (section Q) and wait for
Wail's go-ahead (section U). Neither changes the schema or a string, so the
version stays `2026100701`; the image tag identifies the code.

## E. Git

| | |
|---|---|
| Working branch | `feature/moodle-plugin` |
| `origin/feature/moodle-plugin` | `db1b859` — deployed on the pilot |
| Local, not pushed | `a3c0e22` (two UI fixes) and the commit updating this file |
| Do not modify | `main`, `public-clean-2026-09-30` |
| Pushing | only with Wail's explicit say-so; never force-push |
| Commits | authored by Wail Ouaret; **no assistant attribution trailers** |

## F. Hosted pilot

A persistent hosted Moodle on a VPS, reachable over HTTPS. The same server also
runs a **live production Academy site** that must stay online — never reboot the
server, never touch the Academy app, its database, its port or its nginx.

Access is via a dedicated deployment account (not root) with a key held outside
the repository. See the private deployment notes.

> **Known connection quirk.** The network path drops large packets, so the
> default SSH key exchange hangs after the banner. Pin a single algorithm:
> `KexAlgorithms curve25519-sha256`, `Ciphers aes128-ctr`, `AddressFamily inet`.
> An `~/.ssh/config` entry already does this, with connection multiplexing.
> **Do not retry SSH rapidly on failure** — fail2ban will ban the client IP
> (this has happened). With the pinned settings and multiplexing, the whole
> 0.3.1 deployment ran over one connection without a drop.

## G. Supported resource types

Page · Quiz question · PDF · DOCX · PPTX · TXT · Markdown · VTT/SRT ·
Book chapter · Assignment instructions · Lesson page · Folder child file ·
selected teacher-authored descriptions.

Quiz questions, book chapters and folder files stay as **individual** resources
with stable IDs. Do not collapse them into their parent activity.

## H. Resource → Competencies

The Resources tab shows three **separate** things per resource. They must never
be merged or visually equated:

| Column | Meaning |
|---|---|
| Model proposals | What the model suggested |
| Teacher-reviewed competencies | What a human confirmed |
| Official Moodle competencies | Moodle's own competency links |

Official links read "None — write-back disabled for this pilot", with helper
text. A resource marked "Reviewed" with no official links is correct, not a bug.

## I. Competency → Resources

A first-class **Competencies** tab (Moodle `tabtree`, not a SPA) listing the
configured framework; selecting a competency shows its associated resources.

It is a **deterministic inverse view over stored data — it never calls Gemini.**
Origins stay distinguishable: `MODEL_PROPOSED`, `TEACHER_ACCEPTED`,
`TEACHER_MODIFIED`, `TEACHER_ADDED`, `OFFICIAL_MOODLE`.

## J. Accept / Reject / Modify

| Decision | Resulting teacher-reviewed relationship |
|---|---|
| ACCEPT | the proposed competency |
| MODIFY | the **replacement** competency |
| REJECT | **none** |

A MODIFY shows the original model quotation labelled "Evidence shown with
original proposal" — it must not claim the quote was validated for the
replacement.

## K. Add competency

A teacher can add a competency the model never proposed, **independently** of
accept/reject/modify — so they can accept `GI_C1_3` *and* add `GI_C1_2` without
replacing anything.

Stored in `local_compalign_manualrel` with origin `TEACHER_ADDED`. Model output
stays immutable; teacher additions are never written back as fake suggestions.
Validation is server-side: framework membership, no duplicate active row,
capability, course/resource ownership, resource fingerprint and user recorded.
Removal is a status change (`active` → `removed`), preserving the audit trail.

## L. Show in source

Every evidence quotation offers "Show in source", opening the surrounding text
with the quote highlighted, plus resource title, type and provenance.

- Context is escaped with Moodle's `s()` **before** `<mark>` is added — only the
  literal tags are raw. No XSS.
- Evidence is bound to `cmid` **and** `courseid` **and** `resourceid` in SQL, so
  a cross-course evidence ID cannot be read. No IDOR.
- Matching is whitespace-normalised, so a quote spanning a line break still
  resolves.
- It never calls Gemini and never shows student data.

## M. Official write-back

**OFF, and it must stay off.** ACCEPT, MODIFY and TEACHER_ADDED create no
official Moodle competency link. The plugin only *displays* the distinction.
No Moodle competency write API is called anywhere in the codebase.

## N. Privacy boundaries

No student data enters the model payload. The source viewer never exposes quiz
attempts, answers, grades, submissions, forum posts, lesson attempts or student
identity. Study export is pseudonymised with no raw Moodle user ID. Gemini
credentials stay server-side and never reach Moodle, the browser, Git or logs.

## O. Docker / VPS architecture

```
         VPS
          │
   ┌──────┴──────┐
 Moodle      PostgreSQL
   │
   │ ad-hoc tasks
   ▼
Alignment service  ──►  Gemini
```

Verified 2026-10-08 18:47 UTC, after the display-fix deployment:

| Property | State |
|---|---|
| Docker enabled at boot | yes |
| Restart policy, all four pilot containers | `unless-stopped`, all `healthy` |
| Healthcheck | 20/20 PASS |
| Running images | `gdb1b859a348a` (alignment service, Moodle, cron) |
| Rollback images | `g048fbf987d33` (0.3.1 before the fix) and `g013c4c986e21` (0.3.0) retained |
| PostgreSQL data | persistent named volume |
| Moodledata | persistent named volume |
| Alignment service | **no host port** — private Docker network only |
| Moodle | bound to localhost, nginx in front |
| Moodle cron | dedicated container, healthy |

**Wail's PC is not required for the pilot to run.** Containers have survived
multi-day unattended operation.

A separate isolated stack also exists on the VPS, kept away from pilot data:
PHPUnit, plus a browser-test Moodle site with its own database and the
non-study test account `teacher.local`. See the workflow document.

## P. Deployment workflow

Local machine: edit code, Git, Python tests, static checks.
VPS: Moodle, PostgreSQL, alignment service, cron, integration and browser
testing, the persistent pilot.

**Do not build a local Moodle Docker environment for routine integration work.**

1. Edit locally, commit to `feature/moodle-plugin`, push (with approval).
2. `deploy/pilot/scripts/package-pilot-build.sh` → a tarball of one commit.
3. Copy it to the server and verify its checksum.
4. `scripts/update.sh` — checks env and health, takes a labelled backup, keeps
   the old images for rollback, builds the new tag, recreates containers, then
   runs the healthcheck. It uses `set -euo pipefail`.
5. Moodle upgrades its database on start-up when the plugin version increases.
6. Verify health, then smoke-test.
7. `scripts/rollback.sh` returns to the retained images.

The production build **excludes `tests/`** by design. The PHPUnit stack needs
the full plugin including tests — copy those separately.

## Q. Test baseline

Verified 2026-10-08. PHPUnit and the browser tests ran on the isolated VPS stack.

| Check | Deployed `db1b859` | Local `a3c0e22` |
|---|---|---|
| Moodle PHPUnit (`local_compalign`) | **340 tests, 1293 assertions** | **343 tests, 1300 assertions** |
| Upgrade test 0.3.0 → 0.3.1 | OK | OK |
| PHP syntax | 83 files, 0 errors | 85 files, 0 errors |
| Real-browser checks, teacher flows (desktop 1440px + 390px) | **52/52** | **52/52** |
| Real-browser checks, form widgets | **14/14** | **14/14** |
| Real-browser checks, study export download | **9/9** | not re-run (export unchanged) |
| Real-browser checks of the two fixes | — | **10/10** |
| Python | **577 passed** | unchanged, no Python touched |
| Protected scientific files | **21/21 unchanged** | **21/21 unchanged** |

Every regression test added on 2026-10-08 was confirmed to fail on the code it
fixes. The 0.3.0 → 0.3.1 upgrade also ran on the populated browser-test site
(41 analyses, 4 reviews): every existing row hashed identical before and after.

The two UI bugs fixed in `a3c0e22` were found by reviewing the browser
screenshots, not by a failing check: automated checks do not judge layout.

Report actual counts; do not quote older numbers (the suite was 321/1159 before
0.3.1).

## R. Teacher-study state — read carefully

**The study has started. Do not clean the pilot database to a zero baseline.**

| Fact | |
|---|---|
| Study accounts | `teacher01` … `teacher07` — **not** `T001`–`T007` |
| `teacher01` | last access 2026-10-07; produced real pilot data |
| Pilot rows as of 2026-10-08 | 1 analysis, 2 suggestions, 4 evidence, 2 `accept` reviews, 0 teacher-added |
| Status | Confirmed by Wail as **real study data — preserve** |
| After both 2026-10-08 deployments | Every row byte-identical to the pre-deployment state (last checked 18:47 UTC) |
| Study export on the pilot | Never run yet; its pseudonymisation secret is created on first use |
| Development accounts | `devteacher`, `devstudent`, both suspended |

Older briefs instruct cleaning analyses/suggestions/evidence/reviews to 0 before
teachers begin. **That instruction is obsolete.** Use `devteacher` for any
development check; never a `teacherNN` account. Always take a verified database
backup before a deployment or schema migration.

## S. Protected scientific files

21 files — frozen corpus, retrieval and model artefacts, human reference
annotations, evidence review, and the core metric files. Enumerated with
checksums in `reports/PROTECTED_ARTIFACT_CANONICAL_LIST.md`.

If any differs: **stop.** Do not overwrite the reference hashes.

## T. Known limitations

- Small corpus; single annotator; no inter-annotator agreement.
- The evidence review was done by the same person who produced the reference,
  so it is internal consistency rather than independent validation.
- No `NONE` fragments, so abstention is untested.
- Micro precision is substantially a measure of agreement with a granularity
  convention: 10 of 14 false positives are parent competencies predicted
  alongside their correct child.
- The hierarchy ablation is **post-hoc** and reference-specific.
- Confidence scores are uncalibrated.
- No significance testing; the design does not support it.
- Browser testing used the isolated test site and a non-study account. On the
  live pilot the features were verified through the plugin's own services,
  reading teacher01's decisions without logging in as or acting for teacher01.
- Until `a3c0e22` is deployed, the pilot has the two UI bugs in section D.

## U. Next unfinished work

Done on 2026-10-08: 0.3.1 deployed (`048fbf9`), then the display fix deployed
(`db1b859`), each after a verified backup and with every study row compared
before and after. Backups: `PRE_0_3_1_UPGRADE`, `POST_0_3_1_DEPLOY`,
`PRE_0_3_1_DISPLAY_FIX`, plus the automatic `before-update` backups. Real-browser
testing on desktop and at 390px is done.

Remaining, in order:

1. **Wail's decision:** push `a3c0e22` and this file's update, then deploy
   them. Follow section P: verified backup, `update.sh`, then compare every
   study row with the pre-deployment state.
2. Optional: a quick look on a real phone. Automated checks confirm labels,
   widths and behaviour, not how comfortable the pages feel to use.
