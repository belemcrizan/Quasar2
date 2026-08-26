"""Marginal prediction sets. Highest-mass sets are heuristics, not conformal.

Split conformal requires a calibration sample and exchangeability. The live
legacy pipeline has neither by default, so shadow telemetry records the
heuristic set size and leaves coverage None unless calibration scores are given.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class PredictionSet:
    members: tuple[str, ...]
    alpha: float
    method: str
    nonconformity_score: float | None
    coverage_guaranteed: bool


def highest_mass_set(
    probabilities: Mapping[str, float],
    *,
    alpha: float = 0.1,
) -> PredictionSet:
    """Include top hypotheses until cumulative mass >= 1 - alpha.

    This is a credible-set heuristic. It is not a split-conformal guarantee.
    """

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    target = 1.0 - alpha
    ordered = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
    chosen: list[str] = []
    mass = 0.0
    score = None
    for name, value in ordered:
        chosen.append(name)
        mass += value
        score = float(value)
        if mass >= target:
            break
    return PredictionSet(
        members=tuple(chosen),
        alpha=alpha,
        method="highest_mass_heuristic",
        nonconformity_score=None if score is None else 1.0 - score,
        coverage_guaranteed=False,
    )


def split_conformal_set(
    candidate_scores: Mapping[str, float],
    calibration_scores: Sequence[float],
    *,
    alpha: float = 0.1,
) -> PredictionSet:
    """Include candidates whose nonconformity is <= the split-conformal quantile.

    Scores are nonconformity (larger = less conforming). Coverage is marginal
    under exchangeability of calibration and the test point; it is not
    per-query.
    """

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    n = len(calibration_scores)
    if n == 0:
        return PredictionSet(
            members=(),
            alpha=alpha,
            method="split_conformal_empty_calibration",
            nonconformity_score=None,
            coverage_guaranteed=False,
        )
    ordered = sorted(calibration_scores)
    rank = min(n, max(1, int(((n + 1) * (1.0 - alpha)))))
    qhat = ordered[rank - 1]
    members = tuple(
        name
        for name, score in sorted(candidate_scores.items(), key=lambda item: (item[1], item[0]))
        if score <= qhat
    )
    return PredictionSet(
        members=members,
        alpha=alpha,
        method="split_conformal",
        nonconformity_score=qhat,
        coverage_guaranteed=True,
    )
