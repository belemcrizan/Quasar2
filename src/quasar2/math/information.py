"""Mutual information and signed information difference under degradation.

Delta_eta = I(I; Q_clean) - I(I; Q_obs) is called information_loss only when a
Markov degradation chain I -> Q_clean -> Q_obs is justified. Otherwise it is a
signed information_difference and may be negative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from quasar2.math.conventions import DivergenceUnits
from quasar2.math.divergences import entropy, weighted_jsd
from quasar2.math.numerical import normalize_mass


JointCount = Mapping[tuple[str, str], float]


def _marginals(joint: JointCount) -> tuple[dict[str, float], dict[str, float], dict[tuple[str, str], float]]:
    total = sum(joint.values())
    if total <= 0.0:
        raise ValueError("joint must have positive mass")
    normalized = {key: value / total for key, value in joint.items()}
    p_x: dict[str, float] = {}
    p_y: dict[str, float] = {}
    for (x, y), mass in normalized.items():
        p_x[x] = p_x.get(x, 0.0) + mass
        p_y[y] = p_y.get(y, 0.0) + mass
    return p_x, p_y, normalized


def mutual_information_from_joint(
    joint: JointCount,
    *,
    units: DivergenceUnits = DivergenceUnits.NATS,
) -> float:
    p_x, p_y, normalized = _marginals(joint)
    conditionals: dict[str, dict[str, float]] = {}
    for (x, y), mass in normalized.items():
        bucket = conditionals.setdefault(x, {})
        bucket[y] = bucket.get(y, 0.0) + mass
    for x, dist in list(conditionals.items()):
        conditionals[x] = normalize_mass(dist)
    return weighted_jsd(conditionals, p_x, units=units)


def mutual_information_from_samples(
    pairs: Sequence[tuple[str, str]],
    *,
    units: DivergenceUnits = DivergenceUnits.NATS,
) -> float:
    counts: dict[tuple[str, str], float] = {}
    for left, right in pairs:
        counts[(left, right)] = counts.get((left, right), 0.0) + 1.0
    return mutual_information_from_joint(counts, units=units)


@dataclass(frozen=True, slots=True)
class InformationDifferenceResult:
    information_difference: float
    information_loss_estimate: float | None
    information_loss_is_exact: bool
    information_loss_method: str
    information_loss_nonnegative_assumption_met: bool
    degradation_markov_testable: bool
    degradation_process_id: str
    i_clean: float
    i_obs: float


def information_difference(
    joint_clean: JointCount,
    joint_obs: JointCount,
    *,
    degradation_markov: bool,
    degradation_process_id: str,
    method: str = "discrete_joint",
    exact: bool = True,
    units: DivergenceUnits = DivergenceUnits.NATS,
) -> InformationDifferenceResult:
    i_clean = mutual_information_from_joint(joint_clean, units=units)
    i_obs = mutual_information_from_joint(joint_obs, units=units)
    delta = i_clean - i_obs
    loss = delta if degradation_markov else None
    return InformationDifferenceResult(
        information_difference=delta,
        information_loss_estimate=loss,
        information_loss_is_exact=exact and degradation_markov,
        information_loss_method=method,
        information_loss_nonnegative_assumption_met=degradation_markov,
        degradation_markov_testable=True,
        degradation_process_id=degradation_process_id,
        i_clean=i_clean,
        i_obs=i_obs,
    )


def surprisal(probability: float, *, floor: float = 1e-15) -> float:
    """-log p; not a distance."""

    import math

    return -math.log(max(probability, floor))
