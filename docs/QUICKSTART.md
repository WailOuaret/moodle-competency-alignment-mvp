# Quickstart

Getting the project running and verifying it works. Detailed reproduction steps
are in `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md`.

---

## 1. Clone

```bash
git clone https://github.com/WailOuaret/moodle-competency-alignment-mvp.git
cd moodle-competency-alignment-mvp
```

## 2. Create a virtual environment

```bash
python -m venv .venv
```

**Linux / WSL / macOS**

```bash
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

## 3. Install

```bash
pip install -r requirements.txt
pip install -e .
```

For the exact versions used to produce the reported results, use
`requirements-lock.txt` instead of `requirements.txt`.

**No Moodle access or API key is needed** to reproduce the reported results. The
frozen experimental artefacts are in the repository. Credentials are required
only to extract a new corpus or run a new model experiment.

## 4. Verify

```bash
python -m pytest -q
```

Expect `435 passed`. No test contacts an external API.

Three further checks:

```bash
python scripts/12_validate_manual_annotations.py --mode final   # PASSED, 35/35
python -m compileall -q src scripts tests app                   # silent
python scripts/ui_smoke_check.py                                # 14 pages OK
```

---

## 5. Open an interface

### Research validation interface — the reported corpus

```bash
streamlit run app/Home.py
```

Browses the fixed 20-resource corpus behind the published results, shows each
suggested competency with its evidence quotation and BM25 rank, and collects
accept / reject / modify decisions. Makes **no** model calls.

Opens at <http://localhost:8501>. Guide: `docs/TEACHER_INTERFACE_GUIDE.md`.

### Runtime analysis interface — arbitrary new material

```bash
streamlit run app.py
```

Analyses a new Moodle resource on demand. Requires credentials in `.env`, makes
live model calls, and is **not** part of the reported experiment.

---

## 6. Where to read next

| You want | Go to |
|---|---|
| The results in one page | `FINAL_DELIVERY/00_READ_ME_FIRST.md` |
| The full report | `FINAL_DELIVERY/01_FINAL_TECHNICAL_REPORT.md` |
| What each file does | `docs/PROJECT_STRUCTURE.md` |
| How to reproduce anything | `FINAL_DELIVERY/05_REPRODUCIBILITY_GUIDE.md` |
| Dataset field definitions | `docs/DATA_DICTIONARY.md` |

---

## 7. Optional — configure credentials

Only needed for new extraction or a new model run.

```bash
cp .env.example .env
```

Then edit `.env`. It is excluded from version control and from every
distribution archive.

| Variable | Purpose |
|---|---|
| `MOODLE_BASE_URL` | Moodle instance URL |
| `MOODLE_TOKEN` | Web-service token |
| `MOODLE_SERVICE_SHORTNAME` | External service short name |
| `MOODLE_SW_COURSE_ID`, `MOODLE_DATA_COURSE_ID` | Course identifiers |
| `GEMINI_API_KEY` | Only for a new model experiment |

---

## Troubleshooting

| Symptom | Remedy |
|---|---|
| `python: command not found` | Activate the virtual environment, or use `.venv/bin/python` |
| `MOODLE_TOKEN is not configured` | Expected without `.env`; not needed to reproduce results |
| Streamlit port already in use | `streamlit run app/Home.py --server.port 8502` |
| Interface shows no teacher decisions | Correct — none has been recorded yet |
| `REFUSED: this experiment is optional` | Correct — the unconstrained run requires an explicit authorisation flag |
