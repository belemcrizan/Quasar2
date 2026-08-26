"""Probability floors, simplex projection, and numeric tolerances."""

from __future__ import annotations

from typing import Mapping

PROBABILITY_FLOOR = 1e-12
DEFAULT_ATOL = 1e-9
DEFAULT_RTOL = 1e-8


def within_tolerance(lhs: float, rhs: float, *, atol: float = DEFAULT_ATOL, rtol: float = DEFAULT_RTOL) -> bool:
    return abs(lhs - rhs) <= atol + rtol * max(abs(lhs), abs(rhs))


def normalize_mass(
    mass: Mapping[str, float],
    *,
    floor: float = 0.0,
) -> dict[str, float]:
    clipped = {key: max(floor, float(value)) for key, value in mass.items()}
    total = sum(clipped.values())
    if total <= 0.0:
        raise ValueError("Cannot normalize a non-positive mass")
    return {key: value / total for key, value in clipped.items()}


def aligned_vectors(
    left: Mapping[str, float],
    right: Mapping[str, float],
    *,
    fill: float = 0.0,
) -> tuple[list[str], list[float], list[float]]:
    keys = sorted(set(left) | set(right))
    return keys, [float(left.get(key, fill)) for key in keys], [float(right.get(key, fill)) for key in keys]
