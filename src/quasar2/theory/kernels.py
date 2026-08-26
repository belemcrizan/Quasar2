"""Synthetic observation kernels for T2 grids. Not WDI models."""

from __future__ import annotations

import math
from typing import Mapping


def _normalize(mass: Mapping[str, float]) -> dict[str, float]:
    total = sum(mass.values())
    if total <= 0.0:
        raise ValueError("mass must be positive")
    return {key: value / total for key, value in mass.items()}


def bernoulli_pair(p: float = 0.8) -> dict[str, dict[str, float]]:
    p = min(1.0, max(0.0, p))
    return {"H1": {"0": 1.0 - p, "1": p}, "H2": {"0": p, "1": 1.0 - p}}


def categorical_pair(overlap: float = 0.4) -> dict[str, dict[str, float]]:
    overlap = min(1.0, max(0.0, overlap))
    shared = overlap / 3.0
    return {
        "H1": _normalize({"a": 1.0 - overlap, "b": shared, "c": shared}),
        "H2": _normalize({"a": shared, "b": 1.0 - overlap, "c": shared}),
    }


def heavy_overlap_pair() -> dict[str, dict[str, float]]:
    return {"H1": {"0": 0.52, "1": 0.48}, "H2": {"0": 0.48, "1": 0.52}}


def near_identical_pair() -> dict[str, dict[str, float]]:
    return {"H1": {"0": 0.501, "1": 0.499}, "H2": {"0": 0.499, "1": 0.501}}


def mixture_pair() -> dict[str, dict[str, float]]:
    h1 = _normalize({"a": 0.7, "b": 0.2, "c": 0.1})
    h2 = _normalize({"a": 0.1, "b": 0.2, "c": 0.7})
    return {"H1": h1, "H2": h2}


def gaussian_pair(*, mean_gap: float = 2.0, bins: int = 9) -> dict[str, dict[str, float]]:
    """Discretized N(-gap/2,1) vs N(+gap/2,1) on a fixed grid."""

    edges = [(-3.0 + 6.0 * i / (bins - 1)) for i in range(bins)]

    def dens(mean: float) -> dict[str, float]:
        raw = {}
        for x in edges:
            raw[f"{x:.2f}"] = math.exp(-0.5 * (x - mean) ** 2)
        return _normalize(raw)

    return {"H1": dens(-0.5 * mean_gap), "H2": dens(0.5 * mean_gap)}


KERNEL_FAMILIES: dict[str, dict[str, dict[str, float]]] = {
    "Bernoulli": bernoulli_pair(),
    "Categorical": categorical_pair(),
    "HeavyOverlap": heavy_overlap_pair(),
    "NearIdentical": near_identical_pair(),
    "Mixture": mixture_pair(),
    "Gaussian": gaussian_pair(),
}
