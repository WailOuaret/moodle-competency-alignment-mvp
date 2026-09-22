"""Regression guards for frozen core experimental artefacts.

These tests load hashes only. They must not call Gemini and must not
mutate live experimental files.
"""

from __future__ import annotations

from pathlib import Path

from moodle_competency.reproducibility import file_sha256


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROTECTED_SHA256 = {
    "data/processed/resources.jsonl": (
        "fbfb90a87f330cfd8d3571023501f5e0b416b58aa4833310967e132003d4d40e"
    ),
    "data/processed/fragments.jsonl": (
        "6380f43b95628be59d028d0fcc5d55096448d49514ee42bce651082ba5568aa2"
    ),
    "data/processed/competencies.jsonl": (
        "27ef8064e5eecc27b2baf0964a9c978a47de3b63338bd6642f658c1578650436"
    ),
    "data/interim/bm25_candidates.jsonl": (
        "4e4e1ec030d8f1bfd17865690c83d66cec24fb256d8dc5e3dd523a27325bcaee"
    ),
    "data/interim/llm_tasks.jsonl": (
        "32bc724db8aea5bd11a91bbe7788e839e853d6b726035fab78e5578b5924b66d"
    ),
    "data/interim/gemini_responses.jsonl": (
        "0d8095dd1d320504ceeafad30a00eaf02b1a8f58b147a4f9f3ac275d18700602"
    ),
    "data/interim/gemini_validated.jsonl": (
        "4ec9abf4aa1d3b4cdab2b1a5b367bc8ed9512b6b85616d053809dd6770e03a03"
    ),
    "data/gold/manual_fragment_annotations.csv": (
        "3f96afd974db96394ee22239f0293bf1b641548836072839909b3992cf92fd53"
    ),
    "reports/metrics/bm25_metrics.json": (
        "f24ff968200a6ceacaee67986dabef19bc08eb04a026696232a91924c3366ab2"
    ),
    "reports/metrics/constrained_llm_metrics.json": (
        "5ab206050828ec31f3b0cf9e45f7f889060c666e489d666fe2d1a36789e43248"
    ),
}


def test_protected_core_artefacts_keep_measured_hashes() -> None:
    for relative, expected in PROTECTED_SHA256.items():
        path = PROJECT_ROOT / relative
        assert path.exists(), relative
        assert file_sha256(path) == expected, relative
