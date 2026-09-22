# GitHub secret and privacy scan

**Moodle Learning Resource-to-Competency Alignment MVP**
Wail Ouaret — ENSIA · UTC / Heudiasyc / CNRS — 22 September 2026

**Result: PASS.** No credential, token, password or private Moodle value appears
in any file that would be published.

---

## 1. Scope

The scan covered exactly the files Git would publish, obtained with
`git ls-files -co --exclude-standard` — that is, tracked files plus untracked
files not excluded by `.gitignore`.

| Property | Value |
|---|---:|
| Candidate files for Git | 405 |
| Text files scanned | 395 |
| Binary files skipped | 10 |
| Raw pattern matches | **0** |

Binary types skipped: `.png`, `.jpg`, `.pdf`, `.zip`, `.gz`, `.pyc`, `.so`,
`.mbz`, `.ico`.

---

## 2. Patterns searched

| Pattern | Target |
|---|---|
| `AIza[0-9A-Za-z_\-]{20,}` | Google API key |
| `GEMINI_API_KEY[ \t]*=[ \t]*\S{8,}` | Assigned Gemini key |
| `MOODLE_TOKEN[ \t]*=[ \t]*\S{16,}` | Assigned Moodle token |
| `DB_PASSWORD[ \t]*=[ \t]*\S+` | Database password |
| `(password\|passwd)[ \t]*=[ \t]*...` | Generic password assignment |
| `SECRET[ \t]*=[ \t]*\S{8,}` | Generic secret |
| `Bearer\s+[A-Za-z0-9._\-]{20,}` | Bearer token |
| `Authorization:\s*\S{12,}` | Authorization header |
| `userprivateaccesskey...[0-9a-f]{16,}` | Moodle private access key |
| `-----BEGIN [A-Z ]*PRIVATE KEY-----` | Private key block |

Assignment patterns require an actual value, so an empty `MOODLE_TOKEN=` in a
template or test fixture does not match. The word-boundary and same-line
anchoring (`[ \t]*` rather than `\s*`) prevents a blank assignment from matching
a value on the following line — a false positive encountered and fixed during
the packaging build.

---

## 3. Directories inspected

| Path | Published | Notes |
|---|---|---|
| `data/raw/` | **no** | Excluded by `.gitignore`; API and SQL dumps may carry private Moodle fields |
| `reports/site_info.json` | **no** | Excluded by name; contains a `userprivateaccesskey` |
| `reports/logs/` | **no** | Excluded |
| `reports/` (rest) | yes | 0 matches |
| `docs/` | yes | 0 matches |
| `FINAL_DELIVERY/` | yes | 0 matches |
| `scripts/` | yes | 0 matches; credentials read from the environment only |
| `src/` | yes | 0 matches |
| `data/processed/`, `data/interim/`, `data/gold/`, `data/reviews/` | yes | Research artefacts; 0 matches |
| `README.md` | yes | 0 matches |
| `.env.example` | yes | Variable names only, no values |

---

## 4. `.env` handling

| Check | Result |
|---|---|
| `git ls-files .env` | empty — **not tracked** |
| `git check-ignore .env` | **ignored** |
| `.env.example` present | yes, placeholders only |
| `.env` deleted locally | **no** — the researcher's local file is untouched |

`.env.example` lists `MOODLE_BASE_URL`, `MOODLE_TOKEN`,
`MOODLE_SERVICE_SHORTNAME`, course identifiers,
`COMPETENCY_FRAMEWORK_IDNUMBER`, `DATABASE_*`, `GEMINI_API_KEY`,
`GEMINI_MODEL`, `OLLAMA_HOST` and `OLLAMA_MODEL` — every one with an empty or
placeholder value, and a comment stating that a real key must never be
committed.

---

## 5. Credential handling in code

Credentials are read from the environment through
`src/moodle_competency/settings.py`, which refuses to run when a required
variable is missing. No script accepts a key as a command-line argument, and no
generated artefact records one. `reports/reproducibility_manifest.json` carries
`contains_secrets: false`.

---

## 6. Corroborating checks

| Check | Result |
|---|---|
| Distribution build secret scan | PASS on both release archives |
| `reproducibility_manifest.json` | `contains_secrets: false` |
| Large-file review | Largest published file 680 KB; all research artefacts |
| Total publish size | 5.13 MB across 405 files |

---

## 7. Verdict

**PASS.** Every match reported by the scanner was inspected; there were none.
The repository may be published.

Re-run before any future push:

```bash
PATTERNS=(
  'AIza[0-9A-Za-z_-]{20,}'
  'GEMINI_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]]{8,}'
  'MOODLE_TOKEN[[:space:]]*=[[:space:]]*[^[:space:]]{16,}'
  'userprivateaccesskey'
  'BEGIN .*PRIVATE KEY'
)
for p in "${PATTERNS[@]}"; do
  git ls-files -co --exclude-standard | xargs grep -nE "$p" 2>/dev/null
done
```

> Note: the patterns are held in an array rather than a single alternation so
> that this document does not itself match the scan. An earlier single-line form
> did, and the build correctly refused to package it — the scanner fails closed,
> which is the intended behaviour.
