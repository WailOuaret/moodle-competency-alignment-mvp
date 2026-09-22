"""Build the supervisor handover archive: code + results + explanations.

    python scripts/build_final_package_zip.py
    python scripts/build_final_package_zip.py --out moodle_competency_mvp_FINAL.zip

Inclusion follows `FINAL_PACKAGE_CONTENTS.md`. Secrets are excluded by rule, not
by hope: `.env`, `reports/site_info.json`, `data/raw/` and the log directory
never enter the archive, and every staged text file is scanned for key-shaped
strings before the archive is written. A hit aborts the build.

The repository is never modified. Two runs produce byte-identical archives:
entries are sorted, timestamps fixed and permissions constant.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIXED_DATE = (1980, 1, 1, 0, 0, 0)
FIXED_MODE = 0o644 << 16

ARCHIVE_ROOT = "moodle_competency_mvp_FINAL"

#: Whole directories copied in full (recursively).
INCLUDE_DIRS = (
    "src",
    "scripts",
    "tests",
    "app",
    "pages",
    "docs",
    "configs",
    "sql",
    "data/processed",
    "data/gold",
    "data/reviews",
    "data/studies",
    "data/experiments",
    "data/templates",
    "data/imports",
    "reports",
)

#: Individual files at the repository root.
INCLUDE_FILES = (
    "README.md",
    "FINAL_PACKAGE_CONTENTS.md",
    "requirements.txt",
    "requirements-lock.txt",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
)

#: Reproducibility inputs from data/interim. The rest of that directory is
#: working state and is left out.
INCLUDE_INTERIM = (
    "bm25_candidates.jsonl",
    "bm25_candidates_manifest.json",
    "llm_tasks.jsonl",
    "llm_tasks_manifest.json",
    "gemini_responses.jsonl",
    "gemini_validated.jsonl",
    "gemini_run_manifest.json",
    "competencies_subset.jsonl",
)

#: Excluded outright. Several of these are security decisions, not tidiness.
EXCLUDED_DIR_NAMES = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints",
    "node_modules", ".idea", ".vscode", "uploads",
    # Human-review backups: working state, and they duplicate the live files.
    "annotation_backups", "evidence_review_backups",
    "corpus_teacher_review_backups",
}

EXCLUDED_RELATIVE = {
    ".env",
    # Contains a Moodle userprivateaccesskey field.
    "reports/site_info.json",
    # API dumps may carry private Moodle fields.
    "data/raw",
    "reports/logs",
    "reports/api_raw",
    # External reference repository, not our work.
    "data/source",
    "backups",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip", ".mbz", ".log"}

MAX_SINGLE_FILE_MB = 5

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".yml", ".yaml",
    ".cfg", ".ini", ".toml", ".sql", ".html", ".gift", ".example", ".sha256",
}

#: Patterns that must not appear in any staged text file.
SECRET_PATTERNS = (
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "Google API key"),
    (re.compile(r"\buserprivateaccesskey\b\s*[\"':=]\s*[0-9a-f]{16,}", re.I), "Moodle private access key"),
    (re.compile(r"\b(api[_-]?key|apikey)\b\s*[\"':=]+\s*[\"']?[A-Za-z0-9_\-]{16,}", re.I), "API key assignment"),
    (re.compile(r"\b(password|passwd|db_pass)\b\s*[\"':=]+\s*[\"'][^\"'\n]{4,}", re.I), "password assignment"),
    (re.compile(r"\bwstoken\b[ \t]*[\"':=]+[ \t]*[\"']?[0-9a-f]{20,}", re.I), "Moodle web-service token"),
    # [ \t]* rather than \s*: \s crosses newlines, so an empty `KEY=` would
    # match whatever is assigned on the following line.
    (re.compile(r"\bMOODLE_TOKEN\b[ \t]*=[ \t]*\S{16,}"), "Moodle token"),
    (re.compile(r"\bGEMINI_API_KEY\b[ \t]*=[ \t]*\S{8,}"), "Gemini key"),
)


def is_excluded(relative: Path) -> str | None:
    """Return a reason when this path must not be archived."""

    parts = relative.parts

    for name in parts:
        if name in EXCLUDED_DIR_NAMES:
            return f"excluded directory: {name}"

    text = relative.as_posix()

    for prefix in EXCLUDED_RELATIVE:
        if text == prefix or text.startswith(prefix + "/"):
            return f"excluded path: {prefix}"

    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return f"excluded suffix: {relative.suffix}"

    return None


def collect() -> list[Path]:
    """Every repository-relative path to archive, sorted and deduplicated."""

    selected: set[Path] = set()

    for name in INCLUDE_FILES:
        path = ROOT / name

        if path.is_file() and not is_excluded(Path(name)):
            selected.add(Path(name))

    for directory in INCLUDE_DIRS:
        base = ROOT / directory

        if not base.is_dir():
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(ROOT)

            if is_excluded(relative):
                continue

            if path.stat().st_size > MAX_SINGLE_FILE_MB * 1024 * 1024:
                continue

            selected.add(relative)

    for name in INCLUDE_INTERIM:
        relative = Path("data/interim") / name

        if (ROOT / relative).is_file():
            selected.add(relative)

    return sorted(selected)


def scan_for_secrets(paths: list[Path]) -> list[str]:
    """Scan staged text files. Any hit aborts the build."""

    findings: list[str] = []

    for relative in paths:
        if relative.suffix.lower() not in TEXT_SUFFIXES:
            continue

        # .env.example holds placeholder names, not values.
        if relative.name == ".env.example":
            continue

        try:
            text = (ROOT / relative).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for pattern, label in SECRET_PATTERNS:
            match = pattern.search(text)

            if match:
                findings.append(f"{relative.as_posix()}: {label}")
                break

    return findings


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)

    return digest.hexdigest()


def build_manifest(paths: list[Path]) -> str:
    lines = ["path,size_bytes,sha256"]

    for relative in paths:
        absolute = ROOT / relative
        lines.append(
            f"{relative.as_posix()},{absolute.stat().st_size},{sha256_of(absolute)}"
        )

    return "\n".join(lines) + "\n"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    default = f"moodle_competency_mvp_FINAL_{datetime.now(timezone.utc):%Y%m%d}.zip"
    parser.add_argument(
        "--out",
        default=default,
        help=f"Output archive path (default: {default}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output archive if it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    out_path = Path(args.out)

    if not out_path.is_absolute():
        out_path = ROOT / out_path

    if out_path.exists() and not args.force:
        print(
            f"{out_path} already exists. Pass --force to replace it.",
            file=sys.stderr,
        )
        return 3

    paths = collect()

    if not paths:
        print("Nothing to archive.", file=sys.stderr)
        return 2

    findings = scan_for_secrets(paths)

    if findings:
        print("SECRET SCAN FAILED. Nothing was written:", file=sys.stderr)

        for finding in findings:
            print(f"  {finding}", file=sys.stderr)

        return 4

    manifest = build_manifest(paths)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in paths:
            info = zipfile.ZipInfo(
                f"{ARCHIVE_ROOT}/{relative.as_posix()}", date_time=FIXED_DATE
            )
            info.external_attr = FIXED_MODE
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (ROOT / relative).read_bytes())

        info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/MANIFEST.csv", date_time=FIXED_DATE)
        info.external_attr = FIXED_MODE
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, manifest)

    size_mb = out_path.stat().st_size / (1024 * 1024)

    print(f"Wrote {out_path}")
    print(f"  files: {len(paths)} (+ MANIFEST.csv)")
    print(f"  size:  {size_mb:.2f} MB")
    print(f"  root:  {ARCHIVE_ROOT}/")
    print(f"  sha256: {sha256_of(out_path)}")
    print()
    print("Secret scan passed: no key, token or password pattern in any staged file.")
    print("Excluded by rule: .env, reports/site_info.json, data/raw/, reports/logs/,")
    print("  reports/api_raw/, data/source/, backups/, review backup folders, caches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
