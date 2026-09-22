"""Reusable multi-label and retrieval metrics.

Definitions used throughout evaluation:

Instance-level sets
    gold G and prediction P are sets of competency IDs.

    If G and P are both empty (correct abstention / no-competency):
        precision = recall = F1 = 1.0
    Otherwise:
        precision = |G ∩ P| / |P| if P else 0.0
        recall    = |G ∩ P| / |G| if G else 0.0
        F1        = harmonic mean, or 0.0 if precision+recall = 0

Micro metrics
    Sum true positives, false positives and false negatives over all
    instances, then compute precision/recall/F1 once.

Macro metrics
    Compute precision/recall/F1 for each label in ``label_set`` from
    binary presence per instance, then unweighted mean. Labels that
    never occur in gold or prediction contribute zeros unless both
    sides are empty for that label on every instance.

Exact-set match
    Fraction of instances where G == P.

Coverage
    Fraction of instances with |P| >= 1.

Abstention rate
    Fraction of instances with |P| == 0.

Average predicted label count
    Mean of |P| over instances.

Recall@K (label-level)
    Among gold labels on instances with |G| > 0, the fraction that
    appear in the ranked Top-K candidate list. No-competency instances
    are excluded from the denominator.

Hit@K (fragment-level)
    Fraction of instances with |G| > 0 for which at least one gold
    label appears in Top-K.

MRR
    Mean reciprocal rank of the first gold label in the ranked list,
    over instances with |G| > 0. Missing gold yields 0 for that
    instance.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence


def _as_set(values: Iterable[str] | None) -> set[str]:
    return {str(value).strip() for value in (values or []) if str(value).strip()}


def f1_score(precision: float, recall: float) -> float:
    """Harmonic mean of precision and recall."""

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


def instance_prf(
    gold: Iterable[str],
    predicted: Iterable[str],
) -> dict[str, float]:
    """Precision, recall and F1 for one multi-label instance."""

    gold_set = _as_set(gold)
    predicted_set = _as_set(predicted)

    if not gold_set and not predicted_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    overlap = gold_set & predicted_set
    precision = (
        len(overlap) / len(predicted_set) if predicted_set else 0.0
    )
    recall = len(overlap) / len(gold_set) if gold_set else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1_score(precision, recall),
    }


def confusion_counts(
    gold: Iterable[str],
    predicted: Iterable[str],
) -> tuple[int, int, int]:
    """Return (tp, fp, fn) for one instance."""

    gold_set = _as_set(gold)
    predicted_set = _as_set(predicted)
    tp = len(gold_set & predicted_set)
    fp = len(predicted_set - gold_set)
    fn = len(gold_set - predicted_set)
    return tp, fp, fn


def micro_prf(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
) -> dict[str, float]:
    """Micro-averaged precision, recall and F1."""

    total_tp = total_fp = total_fn = 0

    for gold, predicted in zip(gold_sets, predicted_sets, strict=True):
        tp, fp, fn = confusion_counts(gold, predicted)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision = (
        total_tp / (total_tp + total_fp)
        if total_tp + total_fp
        else 1.0
    )
    recall = (
        total_tp / (total_tp + total_fn)
        if total_tp + total_fn
        else 1.0
    )
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1_score(precision, recall),
        "true_positives": float(total_tp),
        "false_positives": float(total_fp),
        "false_negatives": float(total_fn),
    }


def macro_prf(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
    label_set: Sequence[str],
) -> dict[str, float]:
    """Unweighted mean of per-label binary precision/recall/F1."""

    labels = [str(label).strip() for label in label_set if str(label).strip()]

    if not labels:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    precision_values: list[float] = []
    recall_values: list[float] = []
    f1_values: list[float] = []

    for label in labels:
        gold_flags = [
            label in _as_set(gold) for gold in gold_sets
        ]
        pred_flags = [
            label in _as_set(predicted)
            for predicted in predicted_sets
        ]
        tp = sum(
            gold and pred
            for gold, pred in zip(gold_flags, pred_flags, strict=True)
        )
        fp = sum(
            pred and not gold
            for gold, pred in zip(gold_flags, pred_flags, strict=True)
        )
        fn = sum(
            gold and not pred
            for gold, pred in zip(gold_flags, pred_flags, strict=True)
        )

        if not gold_flags and not pred_flags:
            precision = recall = 1.0
        else:
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0

        precision_values.append(precision)
        recall_values.append(recall)
        f1_values.append(f1_score(precision, recall))

    count = len(labels)
    return {
        "precision": sum(precision_values) / count,
        "recall": sum(recall_values) / count,
        "f1": sum(f1_values) / count,
    }


def exact_set_match(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
) -> float:
    """Fraction of instances whose gold and predicted sets are identical."""

    if not gold_sets:
        return 0.0

    matches = [
        _as_set(gold) == _as_set(predicted)
        for gold, predicted in zip(
            gold_sets,
            predicted_sets,
            strict=True,
        )
    ]
    return sum(matches) / len(matches)


def coverage_rate(
    predicted_sets: Sequence[Iterable[str]],
) -> float:
    """Fraction of instances with at least one predicted label."""

    if not predicted_sets:
        return 0.0

    return sum(1 for predicted in predicted_sets if _as_set(predicted)) / len(
        predicted_sets
    )


def abstention_rate(
    predicted_sets: Sequence[Iterable[str]],
) -> float:
    """Fraction of instances with zero predicted labels."""

    if not predicted_sets:
        return 0.0

    return sum(1 for predicted in predicted_sets if not _as_set(predicted)) / len(
        predicted_sets
    )


def average_predicted_labels(
    predicted_sets: Sequence[Iterable[str]],
) -> float:
    """Mean number of predicted labels per instance."""

    if not predicted_sets:
        return 0.0

    return sum(len(_as_set(predicted)) for predicted in predicted_sets) / len(
        predicted_sets
    )


def recall_at_k(
    gold_sets: Sequence[Iterable[str]],
    ranked_candidates: Sequence[Sequence[str]],
    k: int,
) -> float:
    """Label-level Recall@K over instances that have at least one gold label."""

    hits = 0
    total = 0

    for gold, ranked in zip(gold_sets, ranked_candidates, strict=True):
        gold_set = _as_set(gold)

        if not gold_set:
            continue

        top = set(ranked[:k])
        hits += sum(1 for label in gold_set if label in top)
        total += len(gold_set)

    if total == 0:
        return 0.0

    return hits / total


def hit_at_k(
    gold_sets: Sequence[Iterable[str]],
    ranked_candidates: Sequence[Sequence[str]],
    k: int,
) -> float:
    """Fragment-level Hit@K over instances with non-empty gold."""

    eligible = 0
    hits = 0

    for gold, ranked in zip(gold_sets, ranked_candidates, strict=True):
        gold_set = _as_set(gold)

        if not gold_set:
            continue

        eligible += 1

        if gold_set & set(ranked[:k]):
            hits += 1

    if eligible == 0:
        return 0.0

    return hits / eligible


def mean_reciprocal_rank(
    gold_sets: Sequence[Iterable[str]],
    ranked_candidates: Sequence[Sequence[str]],
) -> float:
    """Mean reciprocal rank of the first gold label, empty-gold excluded."""

    scores: list[float] = []

    for gold, ranked in zip(gold_sets, ranked_candidates, strict=True):
        gold_set = _as_set(gold)

        if not gold_set:
            continue

        rank = next(
            (
                index
                for index, label in enumerate(ranked, start=1)
                if label in gold_set
            ),
            None,
        )
        scores.append(0.0 if rank is None else 1.0 / rank)

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def gold_supported_labels(
    gold_sets: Sequence[Iterable[str]],
    label_set: Sequence[str],
) -> list[str]:
    """Labels from ``label_set`` that occur at least once in gold."""

    supported: list[str] = []

    for label in label_set:
        clean = str(label).strip()

        if not clean:
            continue

        if any(clean in _as_set(gold) for gold in gold_sets):
            supported.append(clean)

    return supported


def per_label_prf(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
    label_set: Sequence[str],
) -> list[dict[str, float | int | str]]:
    """Per-label support, predicted count, TP/FP/FN, precision, recall, F1."""

    counts = per_label_counts(gold_sets, predicted_sets, label_set)
    rows: list[dict[str, float | int | str]] = []

    for label in label_set:
        clean = str(label).strip()

        if not clean:
            continue

        item = counts.get(
            clean,
            {"tp": 0, "fp": 0, "fn": 0, "gold": 0, "predicted": 0},
        )
        tp = int(item["tp"])
        fp = int(item["fp"])
        fn = int(item["fn"])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        rows.append(
            {
                "competency_id": clean,
                "support": int(item["gold"]),
                "predicted_count": int(item["predicted"]),
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1_score(precision, recall),
                "gold_supported": int(item["gold"]) > 0,
            }
        )

    return rows


def macro_prf_views(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
    label_set: Sequence[str],
) -> dict[str, object]:
    """Full-universe macro plus a second view over gold-supported labels.

    ``macro_all_13`` is the existing unweighted mean over the supplied
    label universe (13 UTC GI competencies in the live experiment).
    ``macro_gold_supported_labels`` excludes labels with zero gold
    support. Neither view replaces the other.
    """

    labels = [str(label).strip() for label in label_set if str(label).strip()]
    supported = gold_supported_labels(gold_sets, labels)
    all_macro = macro_prf(gold_sets, predicted_sets, labels)
    supported_macro = (
        macro_prf(gold_sets, predicted_sets, supported)
        if supported
        else {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    )
    return {
        "macro_all_13": all_macro,
        "macro_gold_supported_labels": supported_macro,
        "all_label_count": len(labels),
        "gold_supported_label_count": len(supported),
        "gold_supported_label_ids": supported,
        "zero_gold_support_label_ids": [
            label for label in labels if label not in set(supported)
        ],
    }


def per_label_counts(
    gold_sets: Sequence[Iterable[str]],
    predicted_sets: Sequence[Iterable[str]],
    label_set: Sequence[str],
) -> dict[str, dict[str, int]]:
    """Per-label tp/fp/fn for tables."""

    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0, "gold": 0, "predicted": 0}
    )

    for gold, predicted in zip(gold_sets, predicted_sets, strict=True):
        gold_set = _as_set(gold)
        predicted_set = _as_set(predicted)

        for label in label_set:
            in_gold = label in gold_set
            in_pred = label in predicted_set

            if in_gold:
                counts[label]["gold"] += 1

            if in_pred:
                counts[label]["predicted"] += 1

            if in_gold and in_pred:
                counts[label]["tp"] += 1
            elif in_pred and not in_gold:
                counts[label]["fp"] += 1
            elif in_gold and not in_pred:
                counts[label]["fn"] += 1

    return dict(counts)
