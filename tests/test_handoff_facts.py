"""Tests for scripts/collect_handoff_facts.py (Part A handoff pack).

The real repository is never written to: fixtures live in ``tmp_path`` and use
obviously synthetic identifiers (R4).
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "collect_handoff_facts.py"


def load_module():
    """Load the numbered/standalone script by path (R5)."""
    spec = importlib.util.spec_from_file_location("collect_handoff_facts", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


facts_mod = load_module()


# ---------------------------------------------------------------------------
# 1. LOC on a hand-counted fixture
# ---------------------------------------------------------------------------

def test_loc_counts_match_hand_count(tmp_path: Path) -> None:
    # 10 lines: 2 blank, 3 comment, 5 code (the docstring counts as CODE).
    python_file = tmp_path / "sample.py"
    python_file.write_text(
        '"""Doc line one.\n'          # 1 code (docstring)
        'Doc line two."""\n'          # 2 code (docstring)
        "\n"                          # 3 blank
        "# a comment\n"               # 4 comment
        "    # an indented comment\n" # 5 comment
        "import os\n"                 # 6 code
        "\n"                          # 7 blank
        "def f():\n"                  # 8 code
        "    return os  # trailing comment is NOT a comment line\n"  # 9 code
        "#last\n",                    # 10 comment
        encoding="utf-8",
    )
    counts = facts_mod.count_lines(python_file, ".py")
    assert counts == {"total": 10, "blank": 2, "comment": 3, "code": 5}

    # SQL uses "--" as the line-comment marker, not "#".
    sql_file = tmp_path / "sample.sql"
    sql_file.write_text(
        "-- header comment\n"   # comment
        "SELECT 1\n"            # code
        "\n"                    # blank
        "# not a sql comment\n" # code (for SQL, '#' is not a comment marker)
        "FROM t;\n",            # code
        encoding="utf-8",
    )
    assert facts_mod.count_lines(sql_file, ".sql") == {"total": 5, "blank": 1, "comment": 1, "code": 3}

    # A file with no comment marker defined (HTML) counts everything non-blank as code.
    html_file = tmp_path / "sample.html"
    html_file.write_text("<p>x</p>\n\n<p>y</p>\n", encoding="utf-8")
    assert facts_mod.count_lines(html_file, ".html") == {"total": 3, "blank": 1, "comment": 0, "code": 2}


def test_group_of_separates_handoff_tooling_from_mvp() -> None:
    assert facts_mod.group_of("src/moodle_competency/retrieval.py") == "src"
    assert facts_mod.group_of("scripts/06_retrieve_bm25_candidates.py") == "scripts"
    assert facts_mod.group_of("app.py") == "ui"
    assert facts_mod.group_of("pages/2_Review_Suggestions.py") == "ui"
    assert facts_mod.group_of("tests/test_metrics.py") == "tests"
    # Part A tooling must not inflate the MVP line count.
    assert facts_mod.group_of("scripts/collect_handoff_facts.py") == "handoff_tooling"
    assert facts_mod.group_of("scripts/verify_frozen.py") == "handoff_tooling"


# ---------------------------------------------------------------------------
# 2. license fallback order
# ---------------------------------------------------------------------------

def test_license_fallback_order() -> None:
    # License-Expression wins.
    assert facts_mod.select_license("MIT", "Apache-2.0", ["License :: OSI Approved :: BSD License"]) == ("MIT", "License-Expression")
    # Then a short License field.
    assert facts_mod.select_license(None, "Apache-2.0", ["License :: OSI Approved :: BSD License"]) == ("Apache-2.0", "License")
    # Then the classifiers.
    value, source = facts_mod.select_license(None, None, ["License :: OSI Approved :: BSD License"])
    assert value == "BSD License"
    assert source == "License :: classifier"
    # No metadata at all -> UNKNOWN.
    assert facts_mod.select_license(None, None, []) == ("UNKNOWN", "none")
    # A License field holding the full license text is not usable, and with no
    # classifier to fall back on the result is still UNKNOWN.
    value, source = facts_mod.select_license(None, "Permission is hereby granted, " + "x" * 300, [])
    assert value.startswith("UNKNOWN")


def test_gpl_classifier_is_flagged_copyleft() -> None:
    value, _ = facts_mod.select_license(None, None, ["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"])
    assert facts_mod.is_copyleft(value) is True
    assert facts_mod.is_copyleft("MIT") is False
    assert facts_mod.is_copyleft("MPL 2.0") is True
    assert facts_mod.is_copyleft("Apache-2.0") is False


# ---------------------------------------------------------------------------
# 3 & 4. secrets and personal data never reach the outputs
# ---------------------------------------------------------------------------

def test_remote_url_credentials_are_stripped() -> None:
    token = "ghp_TESTTOKENVALUE0123456789abcdefghij"
    assert facts_mod.sanitize_url(f"https://TEST-USER:{token}@example.invalid/team/repo.git") == "https://example.invalid/team/repo.git"
    assert facts_mod.sanitize_url("https://TEST-USER@example.invalid/team/repo.git") == "https://example.invalid/team/repo.git"
    assert facts_mod.sanitize_url("ssh://TEST-USER:pw@example.invalid/x") == "ssh://example.invalid/x"
    # A clean URL is left untouched.
    assert facts_mod.sanitize_url("https://example.invalid/team/repo.git") == "https://example.invalid/team/repo.git"


def test_no_token_and_no_email_in_generated_outputs() -> None:
    """The real generated pack must contain no credential and no e-mail address."""
    out_dir = PROJECT_ROOT / "docs" / "handoff"
    facts_path = out_dir / "facts.json"
    if not facts_path.exists():
        pytest.skip("facts.json not generated yet")

    email_pattern = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
    secret_patterns = [
        re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
        re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
        re.compile(r"://[^/@\s\"']+:[^/@\s\"']+@"),
    ]

    for name in ("facts.json", "licenses_direct.csv", "loc_by_file.csv"):
        path = out_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in secret_patterns:
            assert not pattern.search(text), f"secret-like value in {name}"
        # Package homepages may legitimately contain no e-mail; author e-mails
        # are never collected at all.
        found = [m for m in email_pattern.findall(text) if not m.endswith(".png")]
        assert not found, f"e-mail address in {name}: {found[:3]}"


# ---------------------------------------------------------------------------
# 5. determinism
# ---------------------------------------------------------------------------

def test_two_runs_produce_identical_facts(tmp_path: Path) -> None:
    first = tmp_path / "a" / "facts.json"
    second = tmp_path / "b" / "facts.json"
    for target in (first, second):
        done = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--out", str(target), "--skip-tests"],
            capture_output=True, text=True, encoding="utf-8", timeout=900,
        )
        assert done.returncode == 0, done.stderr
    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / "loc_by_file.csv").read_bytes() == (second.parent / "loc_by_file.csv").read_bytes()
    assert (first.parent / "licenses_direct.csv").read_bytes() == (second.parent / "licenses_direct.csv").read_bytes()


# ---------------------------------------------------------------------------
# 6. regression anchor against the frozen files (R6)
# ---------------------------------------------------------------------------

@pytest.mark.frozen_data
def test_frozen_metrics_match_r6_anchors() -> None:
    metrics_dir = PROJECT_ROOT / "reports" / "metrics"
    gemini = metrics_dir / "constrained_llm_metrics.json"
    graph = metrics_dir / "graph_child_preference_fragment_metrics.json"
    if not gemini.exists() or not graph.exists():
        pytest.skip("frozen metric files are absent")

    parsed = facts_mod.collect_metrics()
    by_system = {entry["system"]: entry for entry in parsed["systems"]}

    gemini_values = by_system["gemini_top5_constrained"]["values"]
    assert gemini_values["micro_precision"]["value"] == pytest.approx(0.7255, abs=1e-4)
    assert gemini_values["micro_recall"]["value"] == pytest.approx(0.9737, abs=1e-4)
    assert gemini_values["micro_f1"]["value"] == pytest.approx(0.8315, abs=1e-4)

    graph_values = by_system["graph_posthoc"]["values"]
    assert graph_values["micro_f1"]["value"] == pytest.approx(0.9367, abs=1e-4)

    # Every anchor the collector checks must pass.
    assert all(row["within_1e-4"] for row in parsed["r6_anchor_check"]), parsed["r6_anchor_check"]

    # The parsed values must equal the raw JSON, i.e. nothing is recomputed.
    raw = json.loads(gemini.read_text(encoding="utf-8"))
    assert gemini_values["micro_f1"]["value"] == round(raw["micro_f1"], 6)


@pytest.mark.frozen_data
def test_ollama_metrics_reported_as_not_present() -> None:
    """R6 lists Ollama anchors, but no frozen Ollama metric file exists.

    The collector must say so explicitly rather than inventing the numbers.
    """
    parsed = facts_mod.collect_metrics()
    assert parsed["ollama"]["status"] == "NOT_PRESENT"
    assert parsed["ollama"]["metric_files_found"] == []
    # The checkpoints do exist; only the evaluated metrics are missing.
    assert parsed["ollama"]["checkpoints_present"]


@pytest.mark.frozen_data
def test_corpus_counts_from_existing_loaders() -> None:
    corpus = facts_mod.collect_corpus()
    assert corpus["fragment_count"] == 35
    assert corpus["resource_count"] == 20
    assert corpus["competency_count"] == 13
    assert corpus["reference_label_total"] == 38
    assert corpus["hierarchy_roots"] == ["GI_C1", "GI_C2", "GI_C3"]
    assert corpus["hierarchy_max_depth"] == 2
