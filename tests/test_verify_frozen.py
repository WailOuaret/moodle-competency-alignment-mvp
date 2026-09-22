"""Tests for scripts/verify_frozen.py.

Every test builds a throw-away repository in ``tmp_path``.  The real repository
is never snapshotted, modified or checked here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_frozen.py"


def build_fixture_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "__pycache__").mkdir()
    (root / "src" / "module.py").write_text("TEST_VALUE = 1\n", encoding="utf-8")
    (root / "data" / "frozen.jsonl").write_text('{"fragment_id": "TEST-FRAG-001"}\n', encoding="utf-8")
    (root / "pyproject.toml").write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']\n", encoding="utf-8")
    # Must be ignored by the walker.
    (root / "__pycache__" / "junk.pyc").write_bytes(b"\x00\x01")


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--root", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=300,
    )


def manifest_path(root: Path) -> Path:
    return root / "reports" / "frozen_manifest_strengthening.json"


def test_snapshot_then_check_is_all_ok(tmp_path: Path) -> None:
    build_fixture_repo(tmp_path)
    snapshot = run(tmp_path, "--snapshot")
    assert snapshot.returncode == 0, snapshot.stderr
    assert manifest_path(tmp_path).exists()

    payload = json.loads(manifest_path(tmp_path).read_text(encoding="utf-8"))
    assert "src/module.py" in payload["files"]
    assert "data/frozen.jsonl" in payload["files"]
    # Excluded directories never enter the manifest.
    assert not any(name.startswith("__pycache__") for name in payload["files"])

    check = run(tmp_path, "--check")
    assert check.returncode == 0, check.stdout
    assert "RESULT: ALL OK" in check.stdout
    # No per-file CHANGED/MISSING report line (the summary line mentions the words).
    assert not any(line.startswith(("CHANGED", "MISSING")) for line in check.stdout.splitlines())
    assert "3 OK, 0 CHANGED, 0 MISSING" in check.stdout


def test_changed_byte_is_detected(tmp_path: Path) -> None:
    build_fixture_repo(tmp_path)
    assert run(tmp_path, "--snapshot").returncode == 0

    (tmp_path / "src" / "module.py").write_text("TEST_VALUE = 2\n", encoding="utf-8")

    check = run(tmp_path, "--check")
    assert check.returncode == 1
    assert "CHANGED  src/module.py" in check.stdout
    assert "RESULT: FAIL" in check.stdout


def test_missing_file_is_detected(tmp_path: Path) -> None:
    build_fixture_repo(tmp_path)
    assert run(tmp_path, "--snapshot").returncode == 0

    (tmp_path / "data" / "frozen.jsonl").unlink()

    check = run(tmp_path, "--check")
    assert check.returncode == 1
    assert "MISSING  data/frozen.jsonl" in check.stdout
    assert "RESULT: FAIL" in check.stdout


def test_second_snapshot_is_refused_and_manifest_untouched(tmp_path: Path) -> None:
    build_fixture_repo(tmp_path)
    assert run(tmp_path, "--snapshot").returncode == 0
    original = manifest_path(tmp_path).read_bytes()

    # Change the tree so a fresh snapshot would differ if it were taken.
    (tmp_path / "src" / "module.py").write_text("TEST_VALUE = 999\n", encoding="utf-8")

    second = run(tmp_path, "--snapshot")
    assert second.returncode == 1
    assert "REFUSED" in second.stdout
    assert manifest_path(tmp_path).read_bytes() == original


def test_allowed_modified_file_does_not_fail_the_check(tmp_path: Path) -> None:
    build_fixture_repo(tmp_path)
    assert run(tmp_path, "--snapshot").returncode == 0

    # Registering pytest markers is the single permitted edit (R1).
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = ['tests']\nmarkers = ['frozen_data', 'slow']\n",
        encoding="utf-8",
    )

    check = run(tmp_path, "--check")
    assert check.returncode == 0, check.stdout
    assert "ALLOWED  pyproject.toml (CHANGED)" in check.stdout
    assert "RESULT: ALL OK" in check.stdout
    # It must NOT be reported as a plain CHANGED failure line.
    assert "CHANGED  pyproject.toml" not in check.stdout


def test_added_file_is_reported_but_does_not_fail(tmp_path: Path) -> None:
    build_fixture_repo(tmp_path)
    assert run(tmp_path, "--snapshot").returncode == 0

    (tmp_path / "src" / "new_module.py").write_text("TEST_NEW = True\n", encoding="utf-8")

    check = run(tmp_path, "--check", "--verbose")
    assert check.returncode == 0
    assert "ADDED    src/new_module.py" in check.stdout
