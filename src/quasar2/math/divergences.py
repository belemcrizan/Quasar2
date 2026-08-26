"""Shannon entropy, KL, TV, weighted JSD, and related discrete measures.

Logs are natural by default (nats). KL(P||Q) is +inf when P is not absolutely
continuous with respect to Q. TV is the probability-metric convention
(1/2)||P-Q||_1, never the raw L1 distance.
"""

from __future__ import annotations

import math
from typing import Mapping

from quasar2.math.conventions import DivergenceUnits
from quasar2.math.numerical import PROBABILITY_FLOOR, aligned_vectors, normalize_mass

_LN2 = math.log(2.0)


def _log(value: float, units: DivergenceUnits) -> float:
    natural = math.log(value)
    if units is DivergenceUnits.BITS:
        return natural / _LN2
    return natural


def entropy(
    probabilities: Mapping[str, float],
    *,
    units: DivergenceUnits = DivergenceUnits.NATS,
    floor: float = PROBABILITY_FLOOR,
) -> float:
    return -sum(
        p * _log(p, units)
        for p in probabilities.values()
        if p > floor
    )


def kl_divergence(
    p: Mapping[str, float],
    q: Mapping[str, float],
    *,
    units: DivergenceUnits = DivergenceUnits.NATS,
    floor: float = 0.0,
    smooth: float = 0.0,
) -> float:
    """Return D_KL(P || Q). Direction is never inverted.

    ``smooth`` adds a shared floor before renormalization. When smooth is 0 and
    some p>0 has q==0, the result is +inf.
    """

    if smooth < 0.0:
        raise ValueError("smooth must be non-negative")
    if smooth > 0.0:
        keys = sorted(set(p) | set(q))
        p_use = normalize_mass({key: float(p.get(key, 0.0)) + smooth for key in keys})
        q_use = normalize_mass({key: float(q.get(key, 0.0)) + smooth for key in keys})
    else:
        p_use, q_use = dict(p), dict(q)
    keys, p_vec, q_vec = aligned_vectors(p_use, q_use, fill=0.0)
    total = 0.0
    for p_i, q_i in zip(p_vec, q_vec):
        if p_i <= floor:
            continue
        if q_i <= floor:
            return math.inf
        total += p_i * _log(p_i / q_i, units)
    return total


def total_variation(
    p: Mapping[str, float],
    q: Mapping[str, float],
) -> float:
    """TV(P,Q) = (1/2) sum |p-q| = sup_A |P(A)-Q(A)| for discrete measures."""

    _, p_vec, q_vec = aligned_vectors(p, q, fill=0.0)
    return 0.5 * sum(abs(p_i - q_i) for p_i, q_i in zip(p_vec, q_vec))


def l1_distance(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    _, p_vec, q_vec = aligned_vectors(p, q, fill=0.0)
    return sum(abs(p_i - q_i) for p_i, q_i in zip(p_vec, q_vec))


def symmetric_kl(
    p: Mapping[str, float],
    q: Mapping[str, float],
    **kwargs: object,
) -> float:
    left = kl_divergence(p, q, **kwargs)  # type: ignore[arg-type]
    right = kl_divergence(q, p, **kwargs)  # type: ignore[arg-type]
    if math.isinf(left) or math.isinf(right):
        return math.inf
    return 0.5 * (left + right)


def mixture(
    components: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float],
) -> dict[str, float]:
    outcomes: set[str] = set()
    for dist in components.values():
        outcomes.update(dist)
    mixed = {outcome: 0.0 for outcome in outcomes}
    for hyp_id, weight in weights.items():
        dist = components.get(hyp_id, {})
        for outcome, mass in dist.items():
            mixed[outcome] = mixed.get(outcome, 0.0) + float(weight) * float(mass)
    return mixed


def weighted_jsd(
    components: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float],
    *,
    units: DivergenceUnits = DivergenceUnits.NATS,
    smooth: float = 0.0,
) -> float:
    """JSD_b = sum_i b_i KL(P_i || m) = I(H; O | b) for discrete observations."""

    mixed = mixture(components, weights)
    total = 0.0
    for hyp_id, weight in weights.items():
        if weight <= 0.0:
            continue
        dist = components.get(hyp_id)
        if dist is None:
            continue
        term = kl_divergence(dist, mixed, units=units, smooth=smooth)
        if math.isinf(term):
            return math.inf
        total += float(weight) * term
    return total


def prior_dispersion_binary(b: float) -> float:
    if not 0.0 <= b <= 1.0:
        raise ValueError("binary belief mass must be in [0, 1]")
    return b * (1.0 - b)


def gini_simpson(probabilities: Mapping[str, float]) -> float:
    return 1.0 - sum(value * value for value in probabilities.values())


def pinsker_tv_from_kl(kl: float) -> float:
    """TV <= sqrt(KL / 2) when KL is finite (nats)."""

    if math.isinf(kl) or kl < 0.0:
        return math.inf
    return math.sqrt(0.5 * kl)
