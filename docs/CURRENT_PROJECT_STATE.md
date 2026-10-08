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
| Deployed on the pilot | **0.3.1 / 2026100701**, commit `048fbf9`, image tag `g048fbf987d33` |
| Deployed at | 2026-10-08 13:23 UTC |
| Consistent? | Same release. The pilot lacks one display fix, `642a83d` (below). |

**`642a83d` — not yet deployed.** In the Competencies tab, a model proposal the
teacher had already accepted still read "Not reviewed", beside the
teacher-reviewed row that contradicted it. The model row now shows the decision
(Accepted / Rejected / Modified to X). It changes display logic only: no schema,
string, template or stored-data change, so the plugin version stays
`2026100701` and the image tag identifies the code. It is committed locally,
validated on the isolated VPS stack, and waits for Wail's go-ahead to push and
redeploy (section U).

## E. Git

| | |
|---|---|
| Working branch | `feature/moodle-plugin` |
| `origin/feature/moodle-plugin` | `048fbf9` — the deployed release |
| Local, not pushed | `642a83d` (display fix) and the commit adding this file |
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

Verified 2026-10-08, after the 0.3.1 deployment:

| Property | State |
|---|---|
| Docker enabled at boot | yes |
| Restart policy, all four pilot containers | `unless-stopped`, all `healthy` |
| Healthcheck | 20/20 PASS |
| Rollback images | `g013c4c986e21` (0.3.0) retained |
| PostgreSQL data | persistent named volume |
| Moodledata | persistent named volume |
| Alignment service | **no host port** — private Docker network only |
| Moodle | bound to localhost, nginx in front |
| Moodle cron | dedicated container, healthy |

**Wail's PC is not required for the pilot to run.** Containers have survived
multi-day unattended operation.

A separate isolated PHPUnit stack also exists on the VPS for upgrade and
integration testing, kept away from pilot data.

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

Verified 2026-10-08 on commit `642a83d`, PHPUnit on the isolated VPS stack:

| Check | Result |
|---|---|
| Python | **577 passed** |
| Moodle PHPUnit (`local_compalign`) | **340 tests, 1293 assertions, 0 failures, 0 errors** |
| Upgrade test 0.3.0 → 0.3.1 | **2 tests, 7 assertions, OK** |
| PHP syntax | **83 files, 0 errors** |
| Protected scientific files | **21/21 unchanged** |

The deployed commit `048fbf9` measured 339 tests / 1280 assertions; `642a83d`
adds one regression test, which was confirmed to fail on `048fbf9`. The
annotation validator, compileall and UI smoke passed on `048fbf9`; `642a83d`
touches no Python.

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
| After the 0.3.1 deployment | Every row byte-identical to the pre-deployment backup |
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
- 0.3.1 is deployed and was verified against live data through the plugin's
  own services, but has **not** been tested in a real browser.

## U. Next unfinished work

Done on 2026-10-08: tests restored to the isolated stack, the full suite and
upgrade test passed there, a verified pre-deployment backup was taken
(`PRE_0_3_1_UPGRADE`), `048fbf9` was deployed, the deployed views were
verified against live data, and a verified post-deployment backup was taken
(`POST_0_3_1_DEPLOY`).

Remaining, in order:

1. **Wail's decision:** push `642a83d` and redeploy it. The redeploy follows
   section P: take a verified backup, run `update.sh`, then check that every
   study row still matches the backup.
2. **Browser test** on desktop and at ~390px: tabs, filters, empty states,
   Show in source, and no console errors. Use an account that is not a study
   participant.
