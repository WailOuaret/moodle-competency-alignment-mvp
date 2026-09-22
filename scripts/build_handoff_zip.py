"""Build the Part A handoff zip: the pack plus a clean snapshot of the code.

    python scripts/build_handoff_zip.py [--out-dir _handoff_dist] [--max-mb 25] [--suffix ""]

Layout inside the archive::

    handoff/     everything in docs/handoff/
    code/        the repository snapshot (secrets redacted, see rules below)
    MANIFEST.csv path, size_bytes, sha256_in_zip, included, reason, uncommitted, redacted
    REDACTION_LOG.md

The repository itself is never modified: redaction happens on the copy that goes
into the archive (R1).  Two runs produce byte-identical archives (R7): entries are
sorted, timestamps fixed at 1980-01-01 and permissions constant.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN_MANIFEST = ROOT / "reports" / "frozen_manifest_strengthening.json"
HANDOFF_DIR = ROOT / "docs" / "handoff"

FIXED_DATE = (1980, 1, 1, 0, 0, 0)
FIXED_MODE = 0o644 << 16

EXCLUDED_DIR_NAMES = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "ENV", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints",
    "node_modules", "_handoff_dist", ".idea", ".vscode",
}

MAX_SINGLE_FILE_MB = 5

BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".xz", ".bz2",
                     ".pack", ".idx", ".rev", ".pyc", ".so", ".dll", ".woff", ".woff2", ".ico", ".mbz"}

#: Files excluded because they carry personal data (learner / account holder).
PERSONAL_DATA_FILES = {
    "reports/site_info.json",
    "data/raw/api/site_info.json",
    "reports/sql_raw/completion_information.csv",
}

PERSONAL_DATA_COLUMNS = {"firstname", "lastname", "username", "user_id", "userid", "email", "student_id"}

SECRET_PATTERNS = [
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("huggingface_token", re.compile(r"hf_[A-Za-z0-9]{30,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|passw(?:or)?d|access[_-]?key|private[_-]?access[_-]?key)\b"
    r"\s*[:=]\s*(\"|')([^\"']{8,})(\2)"
)

URL_CREDENTIAL_PATTERN = re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.\-]*://)(?P<cred>[^/@\s\"']+:[^/@\s\"']+)@")

PLACEHOLDER_HINTS = ("<", "your-", "your_", "xxx", "changeme", "change-me", "placeholder", "example",
                     "dummy", "redacted", "fill", "todo", "none", "null")

ENV_VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_lines(args: list[str]) -> list[str]:
    try:
        done = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode != 0:
        return []
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if ENV_VAR_NAME.match(value.strip()):
        return True
    return any(hint in lowered for hint in PLACEHOLDER_HINTS)


def redact_text(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Return (redacted_text, [(line_number, pattern_name), ...]).

    Values that are merely an environment-variable NAME or an obvious
    placeholder are never redacted.
    """
    hits: list[tuple[int, str]] = []
    out_lines = []
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        new_line = line
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(new_line):
                new_line = pattern.sub("<REDACTED>", new_line)
                hits.append((number, name))

        def kv_sub(match: re.Match) -> str:
            value = match.group(3)
            if is_placeholder(value):
                return match.group(0)
            hits.append((number, "key_value_assignment"))
            return f"{match.group(1)}{match.group(0)[len(match.group(1)):match.group(0).index(match.group(2))]}" \
                   f"{match.group(2)}<REDACTED>{match.group(4)}"

        new_line = KEY_VALUE_PATTERN.sub(kv_sub, new_line)

        def url_sub(match: re.Match) -> str:
            hits.append((number, "url_credentials"))
            return f"{match.group('scheme')}<REDACTED>@"

        new_line = URL_CREDENTIAL_PATTERN.sub(url_sub, new_line)
        out_lines.append(new_line)
    return "".join(out_lines), hits


def classify(relpath: str, size: int) -> str | None:
    """Return an exclusion reason, or None when the file may be included."""
    parts = Path(relpath).parts
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return "build/cache/vcs directory"
    if relpath.startswith("docs/handoff/"):
        return "already shipped under handoff/"
    name = Path(relpath).name
    if name.startswith(".env") and name != ".env.example":
        return "environment file: may contain secrets"
    if Path(relpath).suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".jks"}:
        return "credential material"
    if re.match(r"(?i)^(credentials|secrets|service[_-]?account).*", name):
        return "credential material"
    if relpath in PERSONAL_DATA_FILES:
        return "contains personal data (account holder / learner fields)"
    if relpath.startswith("data/source/"):
        return "external reference repository, not part of this MVP (see .gitignore)"
    if Path(relpath).suffix.lower() == ".mbz":
        return "Moodle backup archive"
    if Path(relpath).suffix.lower() in {".zip", ".tar", ".gz", ".xz", ".7z"}:
        return "pre-existing archive artifact"
    if Path(relpath).suffix.lower() in {".bin", ".pt", ".onnx", ".safetensors", ".npy", ".faiss"}:
        return "model weights / embedding cache / vector index"
    if size > MAX_SINGLE_FILE_MB * 1024 * 1024:
        return f"single file larger than {MAX_SINGLE_FILE_MB} MB"
    return None


def looks_like_personal_csv(path: Path) -> bool:
    if path.suffix.lower() != ".csv":
        return False
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            columns = {c.strip().lower() for c in header}
            if not (columns & PERSONAL_DATA_COLUMNS):
                return False
            indexes = [i for i, c in enumerate(header) if c.strip().lower() in PERSONAL_DATA_COLUMNS]
            for row in reader:
                if any(i < len(row) and row[i].strip() for i in indexes):
                    return True
    except OSError:
        return False
    return False


def gather_candidates() -> tuple[list[str], set[str]]:
    candidates: set[str] = set()
    tracked = set(git_lines(["ls-files"]))
    untracked = set(git_lines(["ls-files", "-o", "--exclude-standard"]))
    candidates |= tracked | untracked

    if FROZEN_MANIFEST.exists():
        import json
        candidates |= set(json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))["files"])

    # Files created after the snapshot (the pack tooling itself).
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(ROOT).parts):
            continue
        candidates.add(rel)

    existing = sorted(c for c in candidates if (ROOT / c).is_file())
    return existing, tracked


def build_entries(max_mb: int):
    candidates, tracked = gather_candidates()
    rows = []
    payloads: dict[str, bytes] = {}
    redactions: list[dict] = []

    for relpath in candidates:
        path = ROOT / relpath
        size = path.stat().st_size
        reason = classify(relpath, size)
        if reason is None and looks_like_personal_csv(path):
            reason = "contains personal data (non-empty personal columns)"

        uncommitted = relpath not in tracked
        if reason is not None:
            rows.append({"path": relpath, "size_bytes": size, "sha256_in_zip": "",
                         "included": "no", "reason": reason,
                         "uncommitted": str(uncommitted).lower(), "redacted": "no"})
            continue

        raw = path.read_bytes()
        redacted_flag = False
        if path.suffix.lower() not in BINARY_EXTENSIONS:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None
            if text is not None:
                new_text, hits = redact_text(text)
                if hits:
                    redacted_flag = True
                    raw = new_text.encode("utf-8")
                    for line_number, pattern_name in hits:
                        redactions.append({"file": f"code/{relpath}", "line": line_number, "pattern": pattern_name})

        arc = f"code/{relpath}"
        payloads[arc] = raw
        rows.append({"path": relpath, "size_bytes": size, "sha256_in_zip": sha256_bytes(raw),
                     "included": "yes", "reason": "included",
                     "uncommitted": str(uncommitted).lower(), "redacted": "yes" if redacted_flag else "no"})

    # handoff/ : everything in docs/handoff
    if HANDOFF_DIR.is_dir():
        for path in sorted(HANDOFF_DIR.rglob("*")):
            if not path.is_file():
                continue
            relpath = path.relative_to(HANDOFF_DIR).as_posix()
            raw = path.read_bytes()
            redacted_flag = False
            if path.suffix.lower() not in BINARY_EXTENSIONS:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text is not None:
                    new_text, hits = redact_text(text)
                    if hits:
                        redacted_flag = True
                        raw = new_text.encode("utf-8")
                        for line_number, pattern_name in hits:
                            redactions.append({"file": f"handoff/{relpath}", "line": line_number, "pattern": pattern_name})
            arc = f"handoff/{relpath}"
            payloads[arc] = raw
            rows.append({"path": f"docs/handoff/{relpath}", "size_bytes": path.stat().st_size,
                         "sha256_in_zip": sha256_bytes(raw), "included": "yes",
                         "reason": "handoff pack", "uncommitted": "true",
                         "redacted": "yes" if redacted_flag else "no"})

    return rows, payloads, redactions


def render_manifest(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["path", "size_bytes", "sha256_in_zip", "included", "reason", "uncommitted", "redacted"])
    for row in sorted(rows, key=lambda r: r["path"]):
        writer.writerow([row["path"], row["size_bytes"], row["sha256_in_zip"], row["included"],
                         row["reason"], row["uncommitted"], row["redacted"]])
    return buffer.getvalue().encode("utf-8")


def render_redaction_log(redactions: list[dict]) -> bytes:
    lines = [
        "# Redaction log",
        "",
        "Values matching a secret pattern were replaced with `<REDACTED>` **in the archived copy only**.",
        "The repository files themselves are byte-identical to the frozen snapshot.",
        "Secret values are never printed here: only file, line and the pattern that matched.",
        "",
    ]
    if not redactions:
        lines.append("No redaction was necessary: no secret pattern matched any archived file.")
    else:
        lines.append("| file | line | pattern |")
        lines.append("| --- | --- | --- |")
        for row in sorted(redactions, key=lambda r: (r["file"], r["line"], r["pattern"])):
            lines.append(f"| `{row['file']}` | {row['line']} | {row['pattern']} |")
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_zip(target: Path, payloads: dict[str, bytes]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for arc in sorted(payloads):
            info = zipfile.ZipInfo(arc, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = FIXED_MODE
            info.create_system = 3
            archive.writestr(info, payloads[arc])


def self_check(target: Path, rows: list[dict]) -> list[str]:
    problems = []
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            problems.append(f"{target.name}: corrupt entry {archive.testzip()}")
        names = set(archive.namelist())
        expected = {f"code/{r['path']}" if not r["path"].startswith("docs/handoff/")
                    else f"handoff/{r['path'][len('docs/handoff/'):]}"
                    for r in rows if r["included"] == "yes"}
        for row in rows:
            if row["included"] != "yes":
                continue
            arc = (f"handoff/{row['path'][len('docs/handoff/'):]}" if row["path"].startswith("docs/handoff/")
                   else f"code/{row['path']}")
            if arc not in names:
                continue  # split archive: checked in its own part
            if sha256_bytes(archive.read(arc)) != row["sha256_in_zip"]:
                problems.append(f"sha256 mismatch for {arc}")
        for row in rows:
            if row["included"] == "no":
                arc = f"code/{row['path']}"
                if arc in names:
                    problems.append(f"excluded path present in archive: {arc}")
        for arc in sorted(names):
            if Path(arc).suffix.lower() in BINARY_EXTENSIONS or arc.endswith("/"):
                continue
            try:
                text = archive.read(arc).decode("utf-8")
            except (UnicodeDecodeError, KeyError):
                continue
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    problems.append(f"secret pattern {name} still present in {arc}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default="_handoff_dist")
    parser.add_argument("--max-mb", type=int, default=25)
    parser.add_argument("--suffix", default="")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    head = (git_lines(["rev-parse", "--short=12", "HEAD"]) or ["nocommit"])[0]
    date = (git_lines(["log", "-1", "--format=%cd", "--date=format:%Y%m%d"]) or [""])[0]
    if not date:
        # No commits: fall back to the frozen snapshot's own creation date.
        run_info = ROOT / "reports" / "frozen_manifest_strengthening_run_info.json"
        if run_info.exists():
            import json
            date = json.loads(run_info.read_text(encoding="utf-8"))["created_utc"][:10].replace("-", "")
        else:
            date = "00000000"

    stem = f"moodle_competency_handoff_{head}_{date}"
    if args.suffix:
        stem += f"_{args.suffix}"

    rows, payloads, redactions = build_entries(args.max_mb)
    manifest_bytes = render_manifest(rows)
    redaction_bytes = render_redaction_log(redactions)

    payloads["MANIFEST.csv"] = manifest_bytes
    payloads["REDACTION_LOG.md"] = redaction_bytes

    single = out_dir / f"{stem}.zip"
    write_zip(single, payloads)
    written = [single]

    limit = args.max_mb * 1024 * 1024
    if single.stat().st_size > limit:
        single.unlink()
        docs_payloads = {k: v for k, v in payloads.items() if k.startswith("handoff/")}
        docs_payloads["MANIFEST.csv"] = manifest_bytes
        docs_payloads["REDACTION_LOG.md"] = redaction_bytes
        code_payloads = {k: v for k, v in payloads.items() if k.startswith("code/")}
        code_payloads["MANIFEST.csv"] = manifest_bytes
        docs_zip = out_dir / f"{stem}_docs.zip"
        code_zip = out_dir / f"{stem}_code.zip"
        write_zip(docs_zip, docs_payloads)
        write_zip(code_zip, code_payloads)
        written = [docs_zip, code_zip]
        oversized = [z for z in written if z.stat().st_size > limit]
        if oversized:
            largest = sorted(((len(v), k) for k, v in payloads.items()), reverse=True)[:10]
            print("STOP: a part is still larger than the limit. Largest entries:")
            for size, name in largest:
                print(f"  {size/1024/1024:8.2f} MB  {name}")
            return 1

    problems = []
    for target in written:
        problems.extend(self_check(target, rows))

    included = sum(1 for r in rows if r["included"] == "yes")
    excluded = len(rows) - included
    print(f"included: {included} files, excluded: {excluded} files, redactions: {len(redactions)}")
    for target in written:
        print(f"  {target.relative_to(ROOT).as_posix()}  {target.stat().st_size/1024/1024:.2f} MB")
    if problems:
        print("SELF-CHECK FAILED:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("self-check: OK (testzip clean, sha256 match, no excluded path, no secret pattern)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
