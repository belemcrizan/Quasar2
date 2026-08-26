"""Operational recoverability R*(s) from pre-action observables only."""

from __future__ import annotations

import math
from typing import Sequence

from quasar2.rescue.leakage import FORBIDDEN_DEPLOYMENT_FIELDS, LeakageError


LABELS = (
    "RECOVERABLE_RESCUED",
    "RECOVERABLE_NOT_RESCUED",
    "NON_RECOVERABLE",
    "OPEN_SET",
)


def outcome_label(
    *,
    catalog_has_h_star: bool,
    sufficient: bool,
    fast_correct: bool,
    deliberative_correct: bool,
) -> str:
    if not catalog_has_h_star:
        return "OPEN_SET"
    if not sufficient:
        return "NON_RECOVERABLE"
    if fast_correct:
        return "NON_RECOVERABLE"
    if deliberative_correct:
        return "RECOVERABLE_RESCUED"
    return "RECOVERABLE_NOT_RESCUED"


def preaction_features(row: dict[str, object]) -> dict[str, float]:
    allowed = {
        "entropy": float(row.get("fast_entropy") or 0.0),
        "margin": float(row.get("fast_margin") or 0.0),
        "unknown_mass": float(row.get("fast_unknown_mass") or 0.0),
        "top_generation_score": float(row.get("top_generation_score") or 0.0),
        "seed_calls": float(row.get("fast_retrieval_calls") or 0.0),
        "signal_quality": float(row.get("signal_quality") or 0.0),
    }
    leak = FORBIDDEN_DEPLOYMENT_FIELDS.intersection(allowed)
    if leak:
        raise LeakageError(f"recoverability features saw gold fields {sorted(leak)}")
    return allowed


def _sigmoid(z: float) -> float:
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def fit_logreg(
    x_rows: Sequence[Sequence[float]],
    y: Sequence[int],
    *,
    steps: int = 250,
    lr: float = 0.15,
) -> tuple[list[float], float]:
    if not x_rows:
        return [], 0.0
    dim = len(x_rows[0])
    weights = [0.0] * dim
    bias = 0.0
    n = max(1, len(x_rows))
    for _ in range(steps):
        grad_w = [0.0] * dim
        grad_b = 0.0
        for x, label in zip(x_rows, y):
            z = bias + sum(w * v for w, v in zip(weights, x))
            p = _sigmoid(z)
            err = p - label
            for i in range(dim):
                grad_w[i] += err * x[i]
            grad_b += err
        for i in range(dim):
            weights[i] -= lr * grad_w[i] / n
        bias -= lr * grad_b / n
    return weights, bias


def predict_logreg(x: Sequence[float], weights: Sequence[float], bias: float) -> float:
    return _sigmoid(bias + sum(w * v for w, v in zip(weights, x)))


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return None
    rank_sum = 0.0
    for index, (_, label) in enumerate(pairs, start=1):
        if label:
            rank_sum += index
    return (rank_sum - pos * (pos + 1) / 2.0) / (pos * neg)


def auprc(scores: Sequence[float], labels: Sequence[int]) -> float:
    ordered = [label for _, label in sorted(zip(scores, labels), key=lambda item: -item[0])]
    if not ordered or sum(ordered) == 0:
        return 0.0
    tp = 0
    area = 0.0
    for index, label in enumerate(ordered, start=1):
        if label:
            tp += 1
            precision = tp / index
            area += precision
    return area / sum(ordered)


def brier(scores: Sequence[float], labels: Sequence[int]) -> float:
    if not scores:
        return 0.0
    return sum((s - y) ** 2 for s, y in zip(scores, labels)) / len(scores)


def threshold_predict(entropy: Sequence[float], cut: float) -> list[float]:
    return [1.0 if value >= cut else 0.0 for value in entropy]


def median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])
