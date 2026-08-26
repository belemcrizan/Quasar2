"""Observation-model mismatch and proxy corruption. True kernels stay oracle-only."""

from __future__ import annotations

import math
import random
from typing import Mapping

from quasar2.math.divergences import total_variation


def _normalize(mass: Mapping[str, float]) -> dict[str, float]:
    total = sum(float(v) for v in mass.values())
    if total <= 0.0:
        raise ValueError("mass must be positive")
    return {str(k): float(v) / total for k, v in mass.items()}


def mix_distribution(
    true: Mapping[str, float],
    other: Mapping[str, float],
    mu: float,
) -> dict[str, float]:
    if not 0.0 <= mu <= 1.0:
        raise ValueError("mu must be in [0, 1]")
    keys = set(true) | set(other)
    mixed = {
        key: (1.0 - mu) * float(true.get(key, 0.0)) + mu * float(other.get(key, 0.0)) for key in keys
    }
    return _normalize(mixed)


def mix_kernels(
    true_kernels: Mapping[str, Mapping[str, float]],
    other_kernels: Mapping[str, Mapping[str, float]],
    mu: float,
) -> dict[str, dict[str, float]]:
    return {
        hyp: mix_distribution(true_kernels[hyp], other_kernels[hyp], mu) for hyp in true_kernels
    }


def invert_kernels(kernels: Mapping[str, Mapping[str, float]]) -> dict[str, dict[str, float]]:
    hyps = list(kernels)
    if len(hyps) < 2:
        return {k: dict(v) for k, v in kernels.items()}
    swapped = dict(kernels)
    swapped[hyps[0]], swapped[hyps[1]] = dict(kernels[hyps[1]]), dict(kernels[hyps[0]])
    return swapped


def mismatch_severity(
    model: Mapping[str, Mapping[str, float]],
    true: Mapping[str, Mapping[str, float]],
) -> float:
    hyps = [h for h in true if h in model]
    if len(hyps) < 2:
        return 0.0
    return 0.5 * (
        total_variation(model[hyps[0]], true[hyps[0]]) + total_variation(model[hyps[1]], true[hyps[1]])
    )


def corrupt_kernels(
    kernels: Mapping[str, Mapping[str, float]],
    *,
    kind: str,
    severity: float,
    seed: int = 0,
) -> dict[str, dict[str, float]]:
    """Apply a named proxy corruption. severity in [0, 1]."""

    if not 0.0 <= severity <= 1.0:
        raise ValueError("severity must be in [0, 1]")
    rng = random.Random(seed)
    hyps = list(kernels)
    if kind == "identity":
        return {h: dict(kernels[h]) for h in hyps}
    if kind == "ranking_inversion":
        return invert_kernels(kernels) if severity >= 0.5 else {h: dict(kernels[h]) for h in hyps}
    if kind == "support_inflation":
        out = {}
        for hyp, dist in kernels.items():
            hit = float(dist.get("1", dist.get("hit", max(dist.values(), default=0.5))))
            hit = hit + (1.0 - hit) * severity
            out[hyp] = {"0": 1.0 - hit, "1": hit}
        return out
    if kind == "support_compression":
        out = {}
        for hyp, dist in kernels.items():
            hit = float(dist.get("1", dist.get("hit", max(dist.values(), default=0.5))))
            hit = 0.5 + (hit - 0.5) * (1.0 - severity)
            out[hyp] = {"0": 1.0 - hit, "1": hit}
        return out
    if kind == "score_saturation":
        out = {}
        for hyp, dist in kernels.items():
            hit = float(dist.get("1", dist.get("hit", max(dist.values(), default=0.5))))
            hit = hit + (0.99 - hit) * severity
            out[hyp] = {"0": 1.0 - hit, "1": hit}
        return out
    if kind == "missing_observations":
        out = {}
        for hyp, dist in kernels.items():
            items = list(dist.items())
            drop = max(0, int(round((len(items) - 1) * severity)))
            keep = items[drop:] or items[-1:]
            out[hyp] = _normalize({k: v for k, v in keep})
        return out
    if kind == "noisy_similarity":
        out = {}
        for hyp, dist in kernels.items():
            noisy = {}
            for key, value in dist.items():
                noisy[key] = max(1e-9, float(value) + rng.gauss(0.0, 0.15 * severity))
            out[hyp] = _normalize(noisy)
        return out
    if kind == "confidence_overstatement":
        inverted = invert_kernels(kernels)
        # Push model TV *up* by mixing away from the midpoint, not toward truth.
        mid = {h: {k: 1.0 / len(dist) for k in dist} for h, dist in kernels.items()}
        return mix_kernels(mid, kernels, min(1.0, 0.35 + 0.65 * severity))
    if kind == "confidence_underestimation":
        mid = {h: {k: 1.0 / max(1, len(dist)) for k in dist} for h, dist in kernels.items()}
        return mix_kernels(kernels, mid, severity)
    if kind == "correlated_errors":
        shift = 0.2 * severity
        out = {}
        for hyp, dist in kernels.items():
            noisy = {k: max(1e-9, float(v) + shift) for k, v in dist.items()}
            out[hyp] = _normalize(noisy)
        return out
    if kind == "stale_evidence":
        return mix_kernels(kernels, invert_kernels(kernels), 0.4 * severity)
    if kind == "domain_shift":
        other = {h: {k: 1.0 / max(1, len(dist)) for k in dist} for h, dist in kernels.items()}
        return mix_kernels(kernels, other, severity)
    if kind == "adversarial_false_high":
        # Proxy looks separable while we will pair with near-identical truth elsewhere.
        return mix_kernels(kernels, invert_kernels(kernels), 0.0)  # identity; caller supplies truth
    raise KeyError(kind)


CORRUPTION_KINDS = (
    "identity",
    "ranking_inversion",
    "support_inflation",
    "support_compression",
    "score_saturation",
    "missing_observations",
    "noisy_similarity",
    "confidence_overstatement",
    "confidence_underestimation",
    "correlated_errors",
    "stale_evidence",
    "domain_shift",
)


def finite_entropy(belief: Mapping[str, float]) -> float:
    total = sum(float(v) for v in belief.values())
    if total <= 0.0:
        return 0.0
    ent = 0.0
    for value in belief.values():
        p = float(value) / total
        if p > 0.0:
            ent -= p * math.log(p)
    return ent / math.log(2.0)
