"""Freeze and verify the pre-existing state of the repository.

Usage
-----
    python scripts/verify_frozen.py --snapshot     # write the manifest once
    python scripts/verify_frozen.py --check        # default: recompute and compare

The snapshot records SHA-256 + byte size of every pre-existing file so that any
later phase can prove it changed nothing.  ``--check`` exits 1 as soon as a file
is CHANGED or MISSING.  Files listed under ``allowed_modified`` (the pytest
configuration file, which may legitimately gain the ``frozen_data`` / ``slow``
marker registration) are reported separately and never fail the check.

Determinism (R7): the manifest itself holds no timestamp and is written with
``sort_keys=True``; run metadata goes to a sibling ``*_run_info.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_RELPATH = "reports/frozen_manifest_strengthening.json"
RUN_INFO_RELPATH = "reports/frozen_manifest_strengthening_run_info.json"

#: Directory names skipped anywhere in the tree.
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "ENV",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".ipynb_checkpoints",
        "node_modules",
        "_handoff_dist",
        ".idea",
    }
)

#: Files that later phases are allowed to modify (R1 exception).
ALLOWED_MODIFIED = ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")

#: Paths produced by this tool itself; never part of the frozen set.
SELF_PRODUCED = (MANIFEST_RELPATH, RUN_INFO_RELPATH)

CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_repo_files(root: Path):
    """Yield every pre-existing file, as POSIX paths relative to ``root``."""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in EXCLUDED_DIR_NAMES:
                    continue
                stack.append(entry)
                continue
            if not entry.is_file():
                continue
            rel = entry.relative_to(root).as_posix()
            if rel in SELF_PRODUCED:
                continue
            yield rel


def git_info(root: Path) -> dict:
    """Read-only git facts.  Never raises; never runs through a shell."""
    info = {"available": False, "head": None, "branch": None, "has_commits": False}

    def run(args: list[str]) -> str | None:
        try:
            done = subprocess.run(
                ["git", *args],
                cwd=str(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if done.returncode != 0:
            return None
        return done.stdout.strip()

    if run(["rev-parse", "--is-inside-work-tree"]) != "true":
        return info
    info["available"] = True
    head = run(["rev-parse", "HEAD"])
    if head:
        info["head"] = head
        info["has_commits"] = True
    branch = run(["rev-parse", "--abbrev-ref", "HEAD"])
    if branch:
        info["branch"] = branch
    return info


def build_snapshot(root: Path) -> dict:
    files = {}
    for rel in sorted(iter_repo_files(root)):
        path = root / rel
        try:
            files[rel] = {"sha256": sha256_of(path), "size": path.stat().st_size}
        except OSError as exc:  # pragma: no cover - unreadable file
            files[rel] = {"sha256": None, "size": None, "error": str(exc)}
    return {
        "schema": "frozen_manifest/1",
        "allowed_modified": list(ALLOWED_MODIFIED),
        "excluded_dir_names": sorted(EXCLUDED_DIR_NAMES),
        "file_count": len(files),
        "files": files,
        "git": git_info(root),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def cmd_snapshot(root: Path, manifest_path: Path, run_info_path: Path) -> int:
    if manifest_path.exists():
        print(f"REFUSED: manifest already exists at {manifest_path}")
        print("Delete it deliberately if you really mean to re-freeze.")
        return 1
    started = datetime.now(timezone.utc)
    manifest = build_snapshot(root)
    write_json(manifest_path, manifest)
    write_json(
        run_info_path,
        {
            "created_utc": started.isoformat(),
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "root": str(root),
        },
    )
    print(f"SNAPSHOT written: {manifest_path}")
    print(f"files frozen: {manifest['file_count']}")
    git = manifest["git"]
    print(f"git available={git['available']} has_commits={git['has_commits']} head={git['head']}")
    return 0


def cmd_check(root: Path, manifest_path: Path, verbose: bool) -> int:
    if not manifest_path.exists():
        print(f"MISSING MANIFEST: {manifest_path}  (run --snapshot first)")
        return 1
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    allowed = set(manifest.get("allowed_modified", ()))
    recorded = manifest["files"]

    ok, changed, missing, allowed_changed = [], [], [], []
    for rel, meta in sorted(recorded.items()):
        path = root / rel
        if not path.is_file():
            (allowed_changed if rel in allowed else missing).append((rel, "MISSING", None, None))
            continue
        actual = sha256_of(path)
        if actual == meta.get("sha256"):
            ok.append(rel)
        elif rel in allowed:
            allowed_changed.append((rel, "CHANGED", meta.get("sha256"), actual))
        else:
            changed.append((rel, "CHANGED", meta.get("sha256"), actual))

    added = sorted(set(iter_repo_files(root)) - set(recorded))

    for rel, _, old, new in changed:
        print(f"CHANGED  {rel}")
        print(f"         frozen={old}")
        print(f"         actual={new}")
    for rel, *_ in missing:
        print(f"MISSING  {rel}")
    for rel, state, old, new in allowed_changed:
        print(f"ALLOWED  {rel} ({state})")
        if new:
            print(f"         frozen={old}")
            print(f"         actual={new}")
    if verbose:
        for rel in ok:
            print(f"OK       {rel}")
        for rel in added:
            print(f"ADDED    {rel}")

    print(
        f"\nsummary: {len(ok)} OK, {len(changed)} CHANGED, {len(missing)} MISSING, "
        f"{len(allowed_changed)} allowed-modified, {len(added)} added-since-snapshot"
    )
    failed = bool(changed or missing)
    print("RESULT: FAIL" if failed else "RESULT: ALL OK")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=None, help="repository root (default: parent of this script's folder)")
    parser.add_argument("--snapshot", action="store_true", help="write the frozen manifest (refuses to overwrite)")
    parser.add_argument("--check", action="store_true", help="verify the working tree against the manifest (default)")
    parser.add_argument("--manifest", default=None, help="manifest path (default: reports/frozen_manifest_strengthening.json)")
    parser.add_argument("--verbose", action="store_true", help="also print OK and ADDED lines")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    manifest_path = Path(args.manifest).resolve() if args.manifest else root / MANIFEST_RELPATH
    run_info_path = root / RUN_INFO_RELPATH

    if args.snapshot:
        return cmd_snapshot(root, manifest_path, run_info_path)
    return cmd_check(root, manifest_path, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
