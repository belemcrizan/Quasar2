"""Rescue / overthinking / utility metrics with explicit denominators."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from quasar2.failures.taxonomy import four_way_class
from quasar2.math.bootstrap import cluster_bootstrap_stat


def wilson_interval(k: int, n: int, *, z: float = 1.96) -> dict[str, float | int]:
    if n <= 0:
        return {"k": k, "n": n, "rate": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / den
    err = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / den
    return {
        "k": k,
        "n": n,
        "rate": p,
        "ci_low": max(0.0, center - err),
        "ci_high": min(1.0, center + err),
    }


def realized_utility(
    *,
    correct: bool,
    action: str,
    retrieval_calls: int,
    seed_calls: int,
    wrong_answer_cost: float = 1.4,
    exploration_cost: float = 0.10,
    ask_cost: float = 0.28,
    defer_cost: float = 0.05,
) -> float:
    extra = max(0, int(retrieval_calls) - int(seed_calls))
    compute = exploration_cost * extra
    label = str(action).upper()
    if label == "ASK":
        return (0.25 if correct else 0.0) - ask_cost - compute
    if label == "DEFER":
        return -defer_cost - compute
    outcome = 1.0 if correct else -wrong_answer_cost
    return outcome - compute


def four_way_counts(rows: Sequence[Mapping[str, object]]) -> dict[str, int]:
    counts = {"RESCUE": 0, "OVERTHINKING": 0, "BOTH_CORRECT": 0, "BOTH_WRONG": 0}
    for row in rows:
        outcome = four_way_class(bool(row["fast_correct"]), bool(row["deliberative_correct"]))
        counts[outcome.label] += 1
    return counts


def rescue_metrics(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    counts = four_way_counts(rows)
    n = len(rows)
    fast_wrong = counts["RESCUE"] + counts["BOTH_WRONG"]
    fast_correct = counts["OVERTHINKING"] + counts["BOTH_CORRECT"]
    rescue = counts["RESCUE"]
    overthinking = counts["OVERTHINKING"]
    delta_u = [float(row["delta_u"]) for row in rows] if rows else []
    mean_du = sum(delta_u) / n if n else 0.0
    clusters = [str(row.get("intent_id") or row.get("query_id") or i) for i, row in enumerate(rows)]

    def _mean(indices: list[int]) -> float:
        if not indices:
            return 0.0
        return sum(float(rows[i]["delta_u"]) for i in indices) / len(indices)

    def _net(indices: list[int]) -> float:
        if not indices:
            return 0.0
        r = sum(
            1
            for i in indices
            if not rows[i]["fast_correct"] and rows[i]["deliberative_correct"]
        )
        o = sum(
            1
            for i in indices
            if rows[i]["fast_correct"] and not rows[i]["deliberative_correct"]
        )
        return (r - o) / len(indices)

    return {
        "N": n,
        "counts": counts,
        "FastWrong": fast_wrong,
        "FastCorrect": fast_correct,
        "RescueRate_FW": wilson_interval(rescue, fast_wrong),
        "OverthinkingRate_FC": wilson_interval(overthinking, fast_correct),
        "BothWrongRate": wilson_interval(counts["BOTH_WRONG"], n),
        "BothCorrectRate": wilson_interval(counts["BOTH_CORRECT"], n),
        "NetRescueRate": {
            "numerator": rescue - overthinking,
            "denominator": n,
            "rate": (rescue - overthinking) / n if n else 0.0,
            "cluster_bootstrap": cluster_bootstrap_stat(_net, clusters, samples=400, seed=42)
            if n
            else {"point": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n_clusters": 0, "samples": 0},
        },
        "DeltaU_EXPLORE": {
            "mean": mean_du,
            "n": n,
            "cluster_bootstrap": cluster_bootstrap_stat(_mean, clusters, samples=400, seed=42)
            if n
            else {"point": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n_clusters": 0, "samples": 0},
        },
    }
