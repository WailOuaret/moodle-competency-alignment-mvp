"""Offline scaling checks. No model calls and no frozen-file writes."""

from __future__ import annotations

import ast
from pathlib import Path

import scaling_checks
from moodle_competency.reproducibility import file_sha256
from moodle_competency.resource_contract import validate_competency_record
from moodle_competency.runtime_storage import FROZEN_RELATIVE_PATHS
from tests.test_core_result_regression import PROTECTED_SHA256


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_scaling_script_does_not_import_gemini_or_network_clients() -> None:
    source = (PROJECT_ROOT / "scaling_checks.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden = {
        "google",
        "requests",
        "httpx",
        "urllib",
        "ollama",
        "socket",
    }
    assert imported.isdisjoint(forbidden)
    assert "GeminiAlignmentClient" not in source
    assert "OllamaAlignmentClient" not in source


def test_scaling_output_path_is_not_a_frozen_artefact() -> None:
    output = PROJECT_ROOT / scaling_checks.OUTPUT_NAME
    frozen = {(PROJECT_ROOT / relative).resolve() for relative in FROZEN_RELATIVE_PATHS}
    frozen.update((PROJECT_ROOT / relative).resolve() for relative in PROTECTED_SHA256)
    assert output.resolve() not in frozen


def test_framework_adapter_returns_valid_competency_records() -> None:
    records = scaling_checks.utc_records(PROJECT_ROOT)
    adapted = scaling_checks.framework_from_utc(records)
    assert len(adapted) == 22
    assert {record["idnumber"] for record in adapted} == {
        str(record["competency_id"]) for record in records
    }
    for record in adapted:
        assert validate_competency_record(record) == []
        assert "aliases_fr" not in record
        assert "aliases_en" not in record


def test_lbg_adapter_preserves_fragment_and_gold_counts() -> None:
    corpus = scaling_checks.lbg_corpus(PROJECT_ROOT)
    assert corpus["course_units"] == 26
    assert corpus["fragment_count"] == 432
    assert corpus["fragments_with_gold"] == 347
    assert corpus["gold_labels"] == 352
    assert corpus["source_files_rewritten"] is False


def test_stopword_and_alias_variants_are_deterministic() -> None:
    utc = scaling_checks.utc_records(PROJECT_ROOT)
    corpus = scaling_checks.lbg_corpus(PROJECT_ROOT)
    fragments = corpus["fragments"]
    gold = corpus["gold"]
    current = scaling_checks.framework_from_utc(utc, include_aliases=False)
    aliased = scaling_checks.framework_from_utc(utc, include_aliases=True)
    stopped_a, fragments_a = scaling_checks.apply_stopwords(
        current,
        fragments,
        scaling_checks.DIAGNOSTIC_STOPWORDS,
    )
    stopped_b, fragments_b = scaling_checks.apply_stopwords(
        current,
        fragments,
        scaling_checks.DIAGNOSTIC_STOPWORDS,
    )
    first = scaling_checks.retrieval_metrics(stopped_a, fragments_a, gold)
    second = scaling_checks.retrieval_metrics(stopped_b, fragments_b, gold)
    assert first == second
    alias_first = scaling_checks.retrieval_metrics(aliased, fragments, gold)
    alias_second = scaling_checks.retrieval_metrics(
        scaling_checks.framework_from_utc(utc, include_aliases=True),
        fragments,
        gold,
    )
    assert alias_first == alias_second
    assert alias_first["recall_at_5"] != first["recall_at_5"]


def test_synthetic_framework_does_not_alter_original_records() -> None:
    original = scaling_checks.framework_from_utc(
        scaling_checks.utc_records(PROJECT_ROOT)
    )
    before = [dict(record) for record in original]
    before_ids = [record["idnumber"] for record in original]
    scaled = scaling_checks.synthetic_framework(original, 220)
    assert [record["idnumber"] for record in original] == before_ids
    assert original == before
    assert len(scaled) == 220
    assert scaled[0]["idnumber"] == before_ids[0]
    assert scaled[-1]["idnumber"].startswith("SYN_")
    assert sum(1 for record in scaled if record["idnumber"].startswith("SYN_")) == 198


def test_importing_scaling_checks_does_not_change_protected_hashes() -> None:
    for relative, expected in PROTECTED_SHA256.items():
        assert file_sha256(PROJECT_ROOT / relative) == expected
