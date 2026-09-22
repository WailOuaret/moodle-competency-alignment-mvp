"""Tests for reproducibility manifests (no secrets)."""

from __future__ import annotations

from pathlib import Path

from moodle_competency.reproducibility import (
    build_reproducibility_manifest,
    file_sha256,
)


def test_manifest_has_counts_and_no_secret_keys(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "resources.jsonl").write_text(
        '{"resource_id":"page:1"}\n',
        encoding="utf-8",
    )
    manifest = build_reproducibility_manifest(tmp_path)

    assert manifest["resource_count"] == 1
    assert manifest["contains_secrets"] is False
    assert ".env" not in str(manifest)
    assert "GEMINI_API_KEY" not in str(manifest)
    assert file_sha256(processed / "resources.jsonl")


def test_manifest_reference_counts_are_unambiguous(tmp_path: Path) -> None:
    gold_dir = tmp_path / "data" / "gold"
    gold_dir.mkdir(parents=True)
    (gold_dir / "manual_fragment_annotations.csv").write_text(
        "fragment_id,resource_id,course_id,course_shortname,resource_type,"
        "activity_name,resource_title,fragment_text,gold_competency_ids,"
        "gold_evidence,no_competency,ambiguous,ambiguity_reason,comment,"
        "annotator,annotation_date\n"
        "page:1#f001,page:1,2,MVP-SW,page,P,T,text,GI_C1_1;GI_C1_2,"
        ",false,false,,,Wail Ouaret,2026-09-18\n"
        "page:1#f002,page:1,2,MVP-SW,page,P,T,text,GI_C1_3,"
        ",false,true,borderline,,Wail Ouaret,2026-09-18\n"
        "page:1#f003,page:1,2,MVP-SW,page,P,T,text,,"
        ",true,false,,,Wail Ouaret,2026-09-18\n",
        encoding="utf-8",
    )
    manifest = build_reproducibility_manifest(tmp_path)

    assert manifest["reference_annotation_row_count"] == 3
    assert manifest["reference_annotation_complete_count"] == 3
    assert manifest["reference_label_count"] == 3
    assert manifest["multi_label_fragment_count"] == 1
    assert manifest["ambiguous_fragment_count"] == 1
    assert manifest["none_fragment_count"] == 1
    assert manifest["gold_annotation_count"] == 3
    assert manifest["gold_annotation_row_count"] == 3
    assert manifest["hashes"]["evidence_review.csv"] is None
    assert manifest["hashes"]["teacher_reviews.csv"] is None
    assert manifest["hashes"]["graph_warnings.jsonl"] is None
