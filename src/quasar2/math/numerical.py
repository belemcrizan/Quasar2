"""Probability floors, simplex projection, and numeric tolerances."""

from __future__ import annotations

import math
from typing import Mapping

PROBABILITY_FLOOR = 1e-12
DEFAULT_ATOL = 1e-9
DEFAULT_RTOL = 1e-8


def within_tolerance(
    lhs: float, rhs: float, *, atol: float = DEFAULT_ATOL, rtol: float = DEFAULT_RTOL
) -> bool:
    if not math.isfinite(atol) or not math.isfinite(rtol) or atol < 0 or rtol < 0:
        raise ValueError("Tolerances must be finite and non-negative")
    if not math.isfinite(lhs) or not math.isfinite(rhs):
        return lhs == rhs
    return abs(lhs - rhs) <= atol + rtol * max(abs(lhs), abs(rhs))


def normalize_mass(
    mass: Mapping[str, float],
    *,
    floor: float = 0.0,
) -> dict[str, float]:
    if not math.isfinite(floor) or floor < 0:
        raise ValueError("floor must be finite and non-negative")
    values = {key: float(value) for key, value in mass.items()}
    if any(not math.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("Mass values must be finite and non-negative")
    clipped = {key: max(floor, value) for key, value in values.items()}
    scale = max(clipped.values(), default=0.0)
    if scale == 0:
        raise ValueError("Cannot normalize a non-positive mass")
    scaled = {key: value / scale for key, value in clipped.items()}
    total = math.fsum(scaled.values())
    return {key: value / total for key, value in scaled.items()}


def aligned_vectors(
    left: Mapping[str, float],
    right: Mapping[str, float],
    *,
    fill: float = 0.0,
) -> tuple[list[str], list[float], list[float]]:
    keys = sorted(set(left) | set(right))
    return (
        keys,
        [float(left.get(key, fill)) for key in keys],
        [float(right.get(key, fill)) for key in keys],
    )
