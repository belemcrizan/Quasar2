"""Rank/linear association and classification scores. Stdlib only."""

from __future__ import annotations

import math
from typing import Sequence


def _finite_pairs(
    x: Sequence[float],
    y: Sequence[float],
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for left, right in zip(x, y):
        if left is None or right is None:
            continue
        if math.isnan(left) or math.isnan(right):
            continue
        if math.isinf(left) or math.isinf(right):
            continue
        xs.append(float(left))
        ys.append(float(right))
    return xs, ys


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    xs, ys = _finite_pairs(x, y)
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if dx <= 0.0 or dy <= 0.0:
        return None
    return num / (dx * dy)


def _ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = average
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    xs, ys = _finite_pairs(x, y)
    if len(xs) < 3:
        return None
    return pearson(_ranks(xs), _ranks(ys))


def r_squared(x: Sequence[float], y: Sequence[float]) -> float | None:
    r = pearson(x, y)
    if r is None:
        return None
    return r * r


def brier(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    pairs = [
        (max(0.0, min(1.0, float(score))), int(label))
        for score, label in zip(scores, labels)
        if not math.isnan(score) and not math.isinf(score)
    ]
    if not pairs:
        return None
    return sum((score - label) ** 2 for score, label in pairs) / len(pairs)


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    pos = [float(score) for score, label in zip(scores, labels) if int(label) == 1 and not math.isinf(score)]
    neg = [float(score) for score, label in zip(scores, labels) if int(label) == 0 and not math.isinf(score)]
    if not pos or not neg:
        return None
    better = 0.0
    ties = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                better += 1.0
            elif p == n:
                ties += 1.0
    return (better + 0.5 * ties) / (len(pos) * len(neg))


def auprc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    pairs = [
        (float(score), int(label))
        for score, label in zip(scores, labels)
        if not math.isnan(score) and not math.isinf(score)
    ]
    positives = sum(label for _, label in pairs)
    if positives == 0 or positives == len(pairs):
        return None
    ordered = sorted(pairs, key=lambda item: -item[0])
    captured = 0
    area = 0.0
    prev_recall = 0.0
    for index, (_, label) in enumerate(ordered, start=1):
        captured += label
        recall = captured / positives
        precision = captured / index
        area += precision * (recall - prev_recall)
        prev_recall = recall
    return area


def reliability_bins(
    scores: Sequence[float],
    targets: Sequence[float],
    *,
    bins: int = 8,
) -> list[dict[str, float | int]]:
    clipped = []
    for score, target in zip(scores, targets):
        if math.isnan(score) or math.isinf(score) or math.isnan(target) or math.isinf(target):
            continue
        clipped.append((max(0.0, min(1.0, float(score))), float(target)))
    if not clipped:
        return []
    width = 1.0 / bins
    out: list[dict[str, float | int]] = []
    for index in range(bins):
        low = index * width
        high = 1.0 if index == bins - 1 else (index + 1) * width
        members = [pair for pair in clipped if (pair[0] >= low and pair[0] < high) or (index == bins - 1 and pair[0] == 1.0)]
        if not members:
            continue
        mean_score = sum(item[0] for item in members) / len(members)
        mean_target = sum(item[1] for item in members) / len(members)
        out.append(
            {
                "bin": index,
                "low": low,
                "high": high,
                "n": len(members),
                "mean_score": mean_score,
                "mean_target": mean_target,
                "calibration_gap": abs(mean_score - mean_target),
            }
        )
    return out
