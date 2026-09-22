# Setup

## Requirements

- Python 3.10+ (development used 3.12.3)
- Local Moodle 5.2 with PostgreSQL if you need to **re-extract** content
- A Gemini API key only if you resume constrained alignment (not required for annotation or offline software)

Moodle does not need to be running to use already extracted `data/processed/` files.

## Python environment

```bash
cd ~/projects/moodle_competency_mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

Copy environment placeholders:

```bash
cp .env.example .env
```

Fill Moodle and database values only if you will call REST or SQL extraction. Fill `GEMINI_API_KEY` only if you are authorized to resume Gemini. Never commit `.env`.

## Tests

```bash
python -m pytest -q
python -m compileall -q src scripts tests
```

## Annotation helper

```bash
python scripts/manual_annotate_fragments.py
```

## Notes for WSL2 / Docker Moodle

The recorded development stack is Windows 11 + WSL2 Ubuntu + Docker Desktop + PostgreSQL 16 + Moodle 5.2.1+. Course shortnames are `MVP-SW` and `MVP-DATA`. Framework idnumber is `UTC_GI_MVP_2026`.
