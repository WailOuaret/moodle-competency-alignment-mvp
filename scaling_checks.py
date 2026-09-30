"""Offline retrieval scaling checks.

No Gemini calls, no Ollama calls, no Moodle network calls, and no writes
to the frozen experiment. Synthetic framework copies are timing and
prompt-size checks only.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from moodle_competency.annotation import parse_competency_ids, read_csv
from moodle_competency.llm_tasks import build_alignment_task
from moodle_competency.metrics import (
    hit_at_k,
    mean_reciprocal_rank,
    recall_at_k,
)
from moodle_competency.resource_contract import validate_competency_record
from moodle_competency.retrieval import (
    BM25CompetencyRetriever,
    build_competency_document,
    load_jsonl,
    tokenize,
)
from moodle_competency.runtime_storage import (
    assert_not_frozen_write,
    frozen_file_hashes,
)


OUTPUT_NAME = "scaling_results.json"
FRAMEWORK_SHORTNAME = "UTC GI"
RECALL_KS = (1, 3, 5, 10)
MRR_K = 5
PROMPT_K = 5
SCALING_SIZES = (22, 220, 2_200, 22_000)

# Post-hoc diagnostic only. Chosen after the LBG current-implementation
# run, to test whether function words with document frequency 1 were
# dominating BM25. This is not a new system ranker.
DIAGNOSTIC_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "au",
        "aux",
        "avec",
        "be",
        "but",
        "by",
        "ce",
        "ces",
        "cette",
        "dans",
        "de",
        "des",
        "dont",
        "du",
        "en",
        "et",
        "for",
        "from",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "la",
        "le",
        "les",
        "moins",
        "ne",
        "no",
        "not",
        "of",
        "on",
        "or",
        "ou",
        "our",
        "par",
        "pas",
        "plus",
        "pour",
        "que",
        "qui",
        "sans",
        "se",
        "son",
        "sa",
        "ses",
        "sur",
        "than",
        "that",
        "the",
        "their",
        "then",
        "these",
        "they",
        "this",
        "those",
        "to",
        "un",
        "une",
        "we",
        "with",
        "you",
        "your",
    }
)
FOCUS_STOPWORDS = ("the", "that", "with")


def _round(value: float) -> float:
    return round(float(value), 4)


def load_jsonl_lenient(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Load JSONL, repairing trailing commas in memory only."""

    text = path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    repaired = 0
    buffer = ""
    depth = 0

    for line in text.splitlines(True):
        if not line.strip() and depth == 0:
            continue

        buffer += line
        depth += line.count("{") - line.count("}")

        if depth != 0 or not buffer.strip():
            continue

        raw = buffer
        buffer = ""

        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            record = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            repaired += 1

        if not isinstance(record, dict):
            raise ValueError(f"{path} contains a non-object JSON value.")

        records.append(record)

    if buffer.strip():
        raise ValueError(f"Unclosed JSON object in {path}.")

    return records, repaired


def utc_records(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / "data" / "processed" / "competencies_utc.jsonl"
    return load_jsonl(path)


def moodle_oriented_competency(
    record: Mapping[str, Any],
    *,
    by_id: Mapping[str, Mapping[str, Any]],
    include_aliases: bool = False,
) -> dict[str, Any]:
    """Map one UTC source record into the retriever's profile fields.

    Aliases are omitted unless this is an explicit post-hoc diagnostic.
    The Moodle export used by the frozen experiment does not store them.
    """

    competency_id = str(record["competency_id"])
    parent_ids = (record.get("neighbors") or {}).get("parent") or []
    parent_id = str(parent_ids[0]) if parent_ids else ""
    parent = by_id.get(parent_id)
    description = str(record.get("description") or "")
    label_en = str(record.get("label_en") or "")
    description_text = (
        f"{description} English label: {label_en} "
        f"UTC competency ID: {competency_id} "
        f"Source URI: {record.get('uri') or ''}"
    ).strip()
    search_parts = [
        competency_id,
        str(record.get("label") or ""),
        description,
        label_en,
    ]

    if include_aliases:
        search_parts.extend(str(alias) for alias in record.get("aliases_fr") or [])
        search_parts.extend(str(alias) for alias in record.get("aliases_en") or [])

    adapted = {
        "competency_id": competency_id,
        "idnumber": competency_id,
        "shortname": str(record.get("label") or ""),
        "description_text": description_text,
        "search_text": " ".join(part for part in search_parts if part),
        "framework_shortname": FRAMEWORK_SHORTNAME,
        "parent_idnumber": parent_id,
        "parent_shortname": str(parent.get("label") or "") if parent else "",
    }
    errors = validate_competency_record(adapted)

    if errors:
        raise ValueError(
            f"{competency_id} is not a valid competency record: {errors}"
        )

    return adapted


def framework_from_utc(
    records: Sequence[Mapping[str, Any]],
    *,
    only_ids: set[str] | None = None,
    include_aliases: bool = False,
) -> list[dict[str, Any]]:
    by_id = {str(record["competency_id"]): record for record in records}
    selected = [
        record
        for record in records
        if only_ids is None or str(record["competency_id"]) in only_ids
    ]
    return [
        moodle_oriented_competency(
            record,
            by_id=by_id,
            include_aliases=include_aliases,
        )
        for record in selected
    ]


def apply_stopwords(
    competencies: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    stopwords: frozenset[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop diagnostic stop words from profiles and queries only."""

    def filtered(text: object) -> str:
        return " ".join(
            token for token in tokenize(str(text or "")) if token not in stopwords
        )

    cleaned_competencies: list[dict[str, Any]] = []

    for competency in competencies:
        clone = dict(competency)

        for field in (
            "shortname",
            "description_text",
            "search_text",
            "framework_shortname",
            "parent_shortname",
        ):
            clone[field] = filtered(clone.get(field))

        cleaned_competencies.append(clone)

    cleaned_fragments: list[dict[str, Any]] = []

    for fragment in fragments:
        clone = dict(fragment)

        for field in (
            "course_fullname",
            "section_name",
            "activity_name",
            "title",
            "search_text",
            "text",
        ):
            clone[field] = filtered(clone.get(field))

        cleaned_fragments.append(clone)

    return cleaned_competencies, cleaned_fragments


def synthetic_framework(
    competencies: Sequence[Mapping[str, Any]],
    size: int,
) -> list[dict[str, Any]]:
    """Return `size` profiles. Copies beyond the real catalogue are synthetic.

    The input records are not mutated. Synthetic ids are not retrieval-quality
    labels.
    """

    if size < 1:
        raise ValueError("Framework size must be positive.")

    base = [dict(record) for record in competencies]

    if not base:
        raise ValueError("Cannot scale an empty framework.")

    scaled: list[dict[str, Any]] = []
    index = 0

    while len(scaled) < size:
        for record in base:
            clone = dict(record)

            if index >= len(base):
                synthetic_id = f"SYN_{index:05d}"
                clone["idnumber"] = synthetic_id
                clone["competency_id"] = synthetic_id

            scaled.append(clone)
            index += 1

            if len(scaled) == size:
                return scaled

    return scaled


def mvp_fragments(project_root: Path) -> list[dict[str, Any]]:
    return load_jsonl(project_root / "data" / "processed" / "fragments.jsonl")


def mvp_gold(project_root: Path) -> dict[str, list[str]]:
    rows = read_csv(project_root / "data" / "gold" / "manual_fragment_annotations.csv")
    gold: dict[str, list[str]] = {}

    for row in rows:
        labels, _ambiguous = parse_competency_ids(row.get("gold_competency_ids"))
        gold[row["fragment_id"]] = labels

    return gold


def lbg_corpus(
    project_root: Path,
) -> dict[str, Any]:
    """Adapt the local LBG source corpus. Does not rewrite those files."""

    root = project_root / "data" / "source" / "competency-tagging" / "data"
    fragment_dir = root / "resources_fragments"
    gold_dir = root / "golds_fragments"

    if not fragment_dir.is_dir() or not gold_dir.is_dir():
        raise FileNotFoundError(
            "Local LBG corpus is not present under data/source/competency-tagging/data."
        )

    fragments: list[dict[str, Any]] = []
    repaired = 0

    for path in sorted(fragment_dir.glob("*_fragments.jsonl")):
        records, bad = load_jsonl_lenient(path)
        repaired += bad

        for record in records:
            uv_id = str(record.get("uv_id") or path.name.split("_")[0])
            fragment_id = f"{uv_id}:{record['fragment_id']}"
            text = str(record.get("text") or "")
            fragments.append(
                {
                    "fragment_id": fragment_id,
                    "uv_id": uv_id,
                    "course_fullname": uv_id,
                    "title": str(record.get("section_title") or ""),
                    "text": text,
                    "search_text": text,
                    "activity_name": "",
                    "section_name": "",
                    "resource_id": str(record.get("resource_id") or ""),
                    "fragment_type": str(record.get("fragment_type") or ""),
                }
            )

    gold: dict[str, list[str]] = {}

    for path in sorted(gold_dir.glob("*_gold_fragments.jsonl")):
        records, bad = load_jsonl_lenient(path)
        repaired += bad

        for record in records:
            uv_id = str(record.get("uv_id") or path.name.split("_")[0])
            fragment_id = f"{uv_id}:{record['fragment_id']}"
            labels = [
                str(item["competency_id"])
                for item in record.get("gold") or []
                if isinstance(item, dict) and item.get("competency_id")
            ]
            gold[fragment_id] = labels

    course_units = sorted({fragment["uv_id"] for fragment in fragments})
    gold_labels = sum(len(gold.get(fragment["fragment_id"], [])) for fragment in fragments)
    with_gold = sum(
        1 for fragment in fragments if gold.get(fragment["fragment_id"])
    )

    return {
        "fragments": fragments,
        "gold": gold,
        "course_units": len(course_units),
        "fragment_count": len(fragments),
        "fragments_with_gold": with_gold,
        "gold_labels": gold_labels,
        "repaired_json_values_in_memory": repaired,
        "source_files_rewritten": False,
    }


def ranked_ids(
    competencies: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    *,
    top_k: int,
) -> tuple[list[list[str]], list[str], BM25CompetencyRetriever]:
    retriever = BM25CompetencyRetriever(competencies)
    ranked: list[list[str]] = []
    rank1: list[str] = []

    for fragment in fragments:
        candidates = retriever.retrieve(fragment, top_k=top_k)["candidates"]
        ids = [str(candidate["idnumber"]) for candidate in candidates]
        ranked.append(ids)
        rank1.append(ids[0] if ids else "")

    return ranked, rank1, retriever


def retrieval_metrics(
    competencies: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    gold: Mapping[str, Sequence[str]],
    *,
    top_k: int = 10,
) -> dict[str, Any]:
    ranked, rank1, _retriever = ranked_ids(
        competencies,
        fragments,
        top_k=top_k,
    )
    gold_sets = [list(gold.get(str(fragment["fragment_id"]), [])) for fragment in fragments]
    metrics: dict[str, Any] = {}

    for k in RECALL_KS:
        metrics[f"recall_at_{k}"] = _round(recall_at_k(gold_sets, ranked, k))
        metrics[f"hit_at_{k}"] = _round(hit_at_k(gold_sets, ranked, k))

    metrics["mrr_at_5"] = _round(
        mean_reciprocal_rank(gold_sets, [row[:MRR_K] for row in ranked])
    )
    metrics["gold_labels"] = sum(len(labels) for labels in gold_sets if labels)
    metrics["fragments"] = len(fragments)
    metrics["fragments_with_gold"] = sum(1 for labels in gold_sets if labels)
    counts = Counter(rank1)
    top_id, top_count = counts.most_common(1)[0]
    metrics["rank1_most_frequent"] = {
        "idnumber": top_id,
        "fragments": top_count,
        "fragment_count": len(fragments),
    }
    return metrics


def compare_candidate_lists(
    project_root: Path,
    competencies: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    frozen_rows = {
        row["fragment_id"]: row
        for row in load_jsonl(project_root / "data" / "interim" / "bm25_candidates.jsonl")
    }
    retriever = BM25CompetencyRetriever(competencies)
    identical = 0
    differences: list[dict[str, Any]] = []

    for fragment in fragments:
        fragment_id = str(fragment["fragment_id"])
        produced = [
            str(candidate["idnumber"])
            for candidate in retriever.retrieve(fragment, top_k=5)["candidates"]
        ]
        frozen = [
            str(candidate["idnumber"])
            for candidate in frozen_rows[fragment_id]["candidates"]
        ]

        if produced == frozen:
            identical += 1
        else:
            differences.append(
                {
                    "fragment_id": fragment_id,
                    "frozen_top5": frozen,
                    "adapter_top5": produced,
                }
            )

    return {
        "fragments_compared": len(fragments),
        "identical_candidate_lists": identical,
        "different_candidate_lists": len(differences),
        "differences": differences,
        "cause": (
            "The adapter builds profiles from competencies_utc.jsonl with "
            "framework shortname 'UTC GI' and does not repeat the description "
            "inside search_text. The frozen BM25 file was built from "
            "data/processed/competencies.jsonl, whose framework shortname is "
            "'UTC GI Competency Framework - MVP' and whose search_text repeats "
            "the description, so BM25 term frequencies differ. The swaps are "
            "adjacent ranks, not a different retriever."
            if differences
            else "Adapter profiles produced the same Top-5 order as the frozen file."
        ),
    }


def stopword_document_frequency(
    competencies: Sequence[Mapping[str, Any]],
    words: Sequence[str],
) -> dict[str, Any]:
    owners: dict[str, list[str]] = {word: [] for word in words}

    for competency in competencies:
        tokens = set(tokenize(build_competency_document(competency)))

        for word in words:
            if word in tokens:
                owners[word].append(str(competency["idnumber"]))

    return {
        word: {
            "profiles": len(owners[word]),
            "idnumbers": owners[word],
            "occurs_in_only_one_profile": len(owners[word]) == 1,
        }
        for word in words
    }


def alias_diagnostic(
    project_root: Path,
    utc: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    processed = load_jsonl(project_root / "data" / "processed" / "competencies.jsonl")
    processed_has_alias_fields = any(
        "aliases_fr" in record or "aliases_en" in record for record in processed
    )
    source_alias_strings = 0
    missing_from_processed_documents = 0
    processed_by_id = {str(record["idnumber"]): record for record in processed}

    for record in utc:
        aliases = [
            str(alias)
            for alias in list(record.get("aliases_fr") or [])
            + list(record.get("aliases_en") or [])
            if str(alias).strip()
        ]
        source_alias_strings += len(aliases)
        processed_record = processed_by_id.get(str(record["competency_id"]))

        if processed_record is None:
            continue

        document = build_competency_document(processed_record).casefold()

        for alias in aliases:
            if alias.casefold() not in document:
                missing_from_processed_documents += 1

    return {
        "source_records": len(utc),
        "source_alias_strings": source_alias_strings,
        "moodle_processed_records": len(processed),
        "moodle_processed_records_have_alias_fields": processed_has_alias_fields,
        "alias_strings_absent_from_processed_retrieval_documents": (
            missing_from_processed_documents
        ),
        "aliases_dropped_from_moodle_oriented_profiles": (
            not processed_has_alias_fields and missing_from_processed_documents > 0
        ),
    }


def computational_scaling(
    competencies: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for size in SCALING_SIZES:
        scaled = synthetic_framework(competencies, size)
        started = time.perf_counter()
        retriever = BM25CompetencyRetriever(scaled)
        index_seconds = time.perf_counter() - started
        lookup = {str(record["idnumber"]): record for record in scaled}
        lengths: list[int] = []
        retrieval_seconds = 0.0

        for fragment in fragments:
            started = time.perf_counter()
            retrieved = retriever.retrieve(fragment, top_k=PROMPT_K)
            retrieval_seconds += time.perf_counter() - started
            task = build_alignment_task(
                candidate_set=retrieved,
                competency_lookup=lookup,
            )
            lengths.append(len(str(task["prompt"])))

        elapsed = retrieval_seconds
        prompts = {
            "fragments_measured": len(lengths),
            "top_k": PROMPT_K,
            "min_prompt_chars": min(lengths),
            "max_prompt_chars": max(lengths),
            "mean_prompt_chars": _round(sum(lengths) / len(lengths)),
            "prompt_built_from_top_k_candidates_only": True,
        }
        rows.append(
            {
                "framework_size": size,
                "synthetic_copies": size > len(competencies),
                "retrieval_quality_measured": False,
                "index_build_seconds": round(index_seconds, 6),
                "fragments_timed": len(fragments),
                "mean_retrieval_milliseconds_per_fragment": round(
                    (elapsed / len(fragments)) * 1000,
                    3,
                ),
                **prompts,
            }
        )

    return rows


def run_checks(project_root: Path) -> dict[str, Any]:
    before = frozen_file_hashes(project_root)
    utc = utc_records(project_root)
    fragments = mvp_fragments(project_root)
    gold = mvp_gold(project_root)
    frozen_profiles = load_jsonl(
        project_root / "data" / "processed" / "competencies.jsonl"
    )
    frozen_ids = {str(record["idnumber"]) for record in frozen_profiles}
    adapter_13 = framework_from_utc(utc, only_ids=frozen_ids)
    adapter_22 = framework_from_utc(utc, include_aliases=False)
    current_13 = retrieval_metrics(frozen_profiles, fragments, gold)
    adapter_13_metrics = retrieval_metrics(adapter_13, fragments, gold)
    comparison = compare_candidate_lists(project_root, adapter_13, fragments)
    reproduction = compare_candidate_lists(project_root, frozen_profiles, fragments)

    section_a_13 = {
        "corpus": "MVP",
        "framework": "UTC GI frozen 13-competency subset",
        "competencies": len(frozen_profiles),
        "uses_frozen_processed_profiles": True,
        "model_called": False,
        **{key: current_13[key] for key in current_13 if key != "rank1_most_frequent"},
        "current_retriever_vs_frozen_candidate_file": {
            "identical_candidate_lists": reproduction["identical_candidate_lists"],
            "different_candidate_lists": reproduction["different_candidate_lists"],
        },
        "adapter_based_13": {
            "competencies": len(adapter_13),
            "recall_at_1": adapter_13_metrics["recall_at_1"],
            "recall_at_3": adapter_13_metrics["recall_at_3"],
            "recall_at_5": adapter_13_metrics["recall_at_5"],
            "recall_at_10": adapter_13_metrics["recall_at_10"],
            "mrr_at_5": adapter_13_metrics["mrr_at_5"],
            "candidate_list_comparison_to_frozen_bm25": comparison,
        },
    }
    section_a_22 = {
        "corpus": "MVP",
        "framework": "UTC GI 22 competencies, aliases omitted",
        "competencies": len(adapter_22),
        "model_called": False,
        "overwrites_frozen_bm25_file": False,
        **retrieval_metrics(adapter_22, fragments, gold),
    }

    lbg = lbg_corpus(project_root)
    lbg_fragments = lbg.pop("fragments")
    lbg_gold = lbg.pop("gold")
    current_lbg = retrieval_metrics(adapter_22, lbg_fragments, lbg_gold)
    section_b = {
        "corpus": "LBG source corpus",
        "framework": "UTC GI 22, current retrieval implementation, aliases omitted",
        "model_called": False,
        "final_precision_recall_f1": None,
        "teacher_validation": None,
        "reason_no_end_to_end_scores": (
            "No Gemini run was performed on the LBG corpus. "
            "These figures are retrieval Recall/Hit/MRR only."
        ),
        **lbg,
        **current_lbg,
    }

    section_c = computational_scaling(adapter_22, fragments)
    alias_22 = framework_from_utc(utc, include_aliases=True)
    variants = {
        "D1_current_implementation": {
            "status": "current retrieval implementation",
            "post_hoc_diagnostic": False,
            "stopwords": False,
            "aliases": False,
            **retrieval_metrics(adapter_22, lbg_fragments, lbg_gold),
        }
    }
    stopped_competencies, stopped_fragments = apply_stopwords(
        adapter_22,
        lbg_fragments,
        DIAGNOSTIC_STOPWORDS,
    )
    variants["D2_stopword_filter"] = {
        "status": "POST-HOC DIAGNOSTIC",
        "post_hoc_diagnostic": True,
        "designed_after_inspecting_the_current_lbg_result": True,
        "not_the_improved_system_accuracy": True,
        "stopwords": True,
        "aliases": False,
        **retrieval_metrics(stopped_competencies, stopped_fragments, lbg_gold),
    }
    variants["D3_restore_aliases"] = {
        "status": "POST-HOC DIAGNOSTIC",
        "post_hoc_diagnostic": True,
        "designed_after_inspecting_the_current_lbg_result": True,
        "not_the_improved_system_accuracy": True,
        "stopwords": False,
        "aliases": True,
        **retrieval_metrics(alias_22, lbg_fragments, lbg_gold),
    }
    both_competencies, both_fragments = apply_stopwords(
        alias_22,
        lbg_fragments,
        DIAGNOSTIC_STOPWORDS,
    )
    variants["D4_stopwords_and_aliases"] = {
        "status": "POST-HOC DIAGNOSTIC",
        "post_hoc_diagnostic": True,
        "designed_after_inspecting_the_current_lbg_result": True,
        "not_the_improved_system_accuracy": True,
        "interpretation": (
            "LBG retrieval Recall in a post-hoc diagnostic variant. "
            "No Gemini model run was performed on the LBG corpus, so there "
            "is no LBG precision, recall, F1, or teacher validation."
        ),
        "stopwords": True,
        "aliases": True,
        **retrieval_metrics(both_competencies, both_fragments, lbg_gold),
    }
    section_d = {
        "corpus": "LBG",
        "changes_limited_to_retrieval_profiles_and_tokenization": True,
        "llm_validator_aggregation_and_human_reference_unchanged": True,
        "focus_stopwords_in_current_22_profiles": stopword_document_frequency(
            adapter_22,
            FOCUS_STOPWORDS,
        ),
        "alias_comparison": alias_diagnostic(project_root, utc),
        "variants": variants,
    }
    after = frozen_file_hashes(project_root)

    if before != after:
        changed = [
            relative
            for relative, digest in before.items()
            if after.get(relative) != digest
        ]
        raise RuntimeError(f"Frozen artefacts changed: {changed}")

    return {
        "note": (
            "Offline scaling checks added after the frozen experiment. "
            "No Gemini, Ollama, Moodle, or other external calls. "
            "Frozen scientific artefacts were not modified. "
            "Synthetic framework sizes are timing and prompt-size checks, "
            "not retrieval-quality experiments. "
            "Stop-word and alias variants are post-hoc diagnostics, "
            "not a replacement of the published BM25 or Gemini metrics. "
            "There is no LBG precision, recall, F1, or teacher validation."
        ),
        "frozen_artifact_hashes_before": before,
        "frozen_artifact_hashes_after": after,
        "frozen_artifacts_unchanged": True,
        "A_mvp_corpus_utc_gi_13_subset": section_a_13,
        "A_mvp_corpus_utc_gi_22_full": section_a_22,
        "B_lbg_corpus_utc_gi_22": section_b,
        "C_computational_scaling": section_c,
        "D_posthoc_retrieval_diagnostics": section_d,
    }


def write_results(project_root: Path, payload: Mapping[str, Any]) -> Path:
    destination = project_root / OUTPUT_NAME
    assert_not_frozen_write(destination, project_root)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(destination)
    return destination


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Repository root containing data/ and src/.",
    )
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    payload = run_checks(project_root)
    destination = write_results(project_root, payload)
    after_write = frozen_file_hashes(project_root)

    if after_write != payload["frozen_artifact_hashes_before"]:
        raise RuntimeError("Frozen artefacts changed while writing scaling results.")

    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
