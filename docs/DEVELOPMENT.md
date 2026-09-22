# Development notes

For anyone extending the project.

---

## Conventions

**Frozen artefacts are immutable.** Anything under `data/processed/`,
`data/interim/` or `data/gold/` belongs to the reported experiment. A script
that writes near them must snapshot checksums before and after and abort on
change — follow the `PROTECTED_PATHS` / `snapshot_protected()` pattern used in
scripts 22 onward.

**Human input is never synthesised.** No annotation, rating or review decision
may be pre-filled, defaulted or suggested. Where no human decision exists, a
rate is reported as `null`, not `0.0` — zero asserts that reviewers declined,
which is a finding.

**Optional work is isolated.** Post-hoc and optional experiments write only
under `data/experiments/` and must not be able to overwrite a core artefact.

**Cost is gated.** Any script that spends API quota must refuse to run without
an explicit authorisation flag and must offer a free `--dry-run`.

---

## Testing

```bash
python -m pytest -q
python -m pytest tests/test_metrics.py -q          # one module
```

Rules:

- Tests build their own fixtures in `tmp_path`. Never read or write real
  experimental data.
- No test contacts an external API. The model client is exercised through a
  fake session; the unconstrained condition through hand-written fixtures.
- Regression tests assert the frozen headline metrics, so an accidental change
  to evaluation code fails the suite rather than silently moving a result.

Add a test module for every new module. Name it `tests/test_<module>.py`.

---

## Adding a pipeline script

1. Take the next free number in `scripts/`.
2. Declare `PROTECTED_PATHS` covering everything the script could affect.
3. Snapshot checksums before and after; return a non-zero exit code on change.
4. Write outputs to a new path — never overwrite a frozen artefact.
5. Add it to `docs/PROJECT_STRUCTURE.md` with its classification
   (OFFLINE / REPRODUCIBLE, LIVE API / COST RISK, MOODLE ACCESS, HUMAN INPUT).
6. Add its outputs to `src/moodle_competency/reproducibility.py` so they are
   hashed in the manifest.

---

## Working on the interfaces

Logic belongs in `src/moodle_competency/corpus_app.py`, which has no Streamlit
import; pages under `app/pages/` stay thin renderers. This keeps interface
behaviour unit-testable without a browser.

After any interface change:

```bash
python scripts/ui_smoke_check.py
```

It renders all 14 pages with outbound sockets patched to raise, so a page that
tries to reach an external service fails loudly rather than succeeding quietly.

---

## Documentation

Current public-facing documentation must stay internally consistent. When a
measured value changes, update it everywhere it appears, and check:

```bash
grep -rn "<the old value>" --include='*.md' README.md FINAL_DELIVERY docs reports
```

Terminology is fixed:

| Use | Not |
|---|---|
| human-reviewed reference annotations | gold standard, blinded gold |
| post-hoc ablation | part of the system |
| precision errors are dominated by… | precision is caused solely by… |

Superseded documents move to `archive/`; nothing is deleted.

---

## Secrets

Credentials are read from the environment and never written to any generated
artefact. `.env` is git-ignored. The distribution build scans every staged text
file for credential patterns and aborts on a match — see
`scripts/build_final_package_zip.py`.
