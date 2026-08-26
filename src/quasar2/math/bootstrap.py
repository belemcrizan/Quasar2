"""Cluster-aware bootstrap. Clusters are the unit of resampling, not rows."""

from __future__ import annotations

import math
import random
from typing import Callable, Sequence

from quasar2.math.association import spearman


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    position = (len(ordered) - 1) * percentile
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def cluster_indices(clusters: Sequence[str]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for index, cluster in enumerate(clusters):
        grouped.setdefault(str(cluster), []).append(index)
    return grouped


def cluster_bootstrap_stat(
    stat: Callable[[list[int]], float | None],
    clusters: Sequence[str],
    *,
    samples: int,
    seed: int,
) -> dict[str, float | int | None]:
    grouped = cluster_indices(clusters)
    keys = list(grouped)
    if not keys:
        return {"point": None, "ci_low": None, "ci_high": None, "n_clusters": 0, "samples": samples}
    observed = stat(list(range(len(clusters))))
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(samples):
        chosen = [keys[rng.randrange(len(keys))] for _ in keys]
        indices: list[int] = []
        for key in chosen:
            indices.extend(grouped[key])
        value = stat(indices)
        if value is not None and not math.isnan(value):
            draws.append(float(value))
    if not draws:
        return {
            "point": observed,
            "ci_low": None,
            "ci_high": None,
            "n_clusters": len(keys),
            "samples": samples,
        }
    return {
        "point": observed,
        "ci_low": _percentile(draws, 0.025),
        "ci_high": _percentile(draws, 0.975),
        "n_clusters": len(keys),
        "samples": samples,
        "n_successful_draws": len(draws),
    }


def cluster_bootstrap_mean(
    values: Sequence[float],
    clusters: Sequence[str],
    *,
    samples: int = 400,
    seed: int = 0,
) -> dict[str, float | int | None]:
    stored = [float(value) for value in values]

    def stat(indices: list[int]) -> float | None:
        if not indices:
            return None
        return sum(stored[i] for i in indices) / len(indices)

    return cluster_bootstrap_stat(stat, clusters, samples=samples, seed=seed)


def cluster_bootstrap_mean_difference(
    left: Sequence[float],
    right: Sequence[float],
    clusters: Sequence[str],
    *,
    samples: int = 400,
    seed: int = 0,
) -> dict[str, float | int | None]:
    stored_left = [float(value) for value in left]
    stored_right = [float(value) for value in right]

    def stat(indices: list[int]) -> float | None:
        if not indices:
            return None
        mean_left = sum(stored_left[i] for i in indices) / len(indices)
        mean_right = sum(stored_right[i] for i in indices) / len(indices)
        return mean_left - mean_right

    return cluster_bootstrap_stat(stat, clusters, samples=samples, seed=seed)


def cluster_bootstrap_spearman(
    x: Sequence[float],
    y: Sequence[float],
    clusters: Sequence[str],
    *,
    samples: int = 400,
    seed: int = 0,
) -> dict[str, float | int | None]:
    xs = [float(value) for value in x]
    ys = [float(value) for value in y]

    def stat(indices: list[int]) -> float | None:
        return spearman([xs[i] for i in indices], [ys[i] for i in indices])

    return cluster_bootstrap_stat(stat, clusters, samples=samples, seed=seed)


def cluster_bootstrap_spearman_difference(
    x_a: Sequence[float],
    x_b: Sequence[float],
    y: Sequence[float],
    clusters: Sequence[str],
    *,
    samples: int = 400,
    seed: int = 0,
) -> dict[str, float | int | None]:
    a = [float(value) for value in x_a]
    b = [float(value) for value in x_b]
    ys = [float(value) for value in y]

    def stat(indices: list[int]) -> float | None:
        left = spearman([a[i] for i in indices], [ys[i] for i in indices])
        right = spearman([b[i] for i in indices], [ys[i] for i in indices])
        if left is None or right is None:
            return None
        return left - right

    return cluster_bootstrap_stat(stat, clusters, samples=samples, seed=seed)
