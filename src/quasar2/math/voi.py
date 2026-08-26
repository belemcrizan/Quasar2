"""Value-of-information identities and Lipschitz bounds (canonical C2/C3).

The scalar-binary and belief-L1 Lipschitz conventions are not interchangeable.
Bounds are labeled THEOREM under their stated assumptions; empirical VoI is not
used to validate the bound against itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from quasar2.math.conventions import LipschitzNorm, MeasureConventions
from quasar2.math.divergences import (
    kl_divergence,
    pinsker_tv_from_kl,
    prior_dispersion_binary,
    total_variation,
    weighted_jsd,
)
from quasar2.math.numerical import DEFAULT_ATOL, DEFAULT_RTOL, within_tolerance


@dataclass(frozen=True, slots=True)
class BinaryVoIBound:
    prior_b: float
    prior_dispersion: float
    recoverability_tv: float
    recoverability_kl: float
    lipschitz_norm: str
    lipschitz_constant: float
    voi_bound_tv: float
    voi_bound_pinsker: float
    expected_belief_movement: float
    identity_holds: bool
    pinsker_orientation: str


@dataclass(frozen=True, slots=True)
class GeneralVoIBound:
    recoverability_jsd: float
    conditional_mutual_information: float
    lipschitz_norm: str
    lipschitz_constant: float
    voi_bound_general: float


def expected_binary_belief_movement(
    b: float,
    p1: Mapping[str, float],
    p2: Mapping[str, float],
) -> float:
    """E_{o ~ m} |b'(o) - b| for two hypotheses, computed by finite sum."""

    outcomes = sorted(set(p1) | set(p2))
    movement = 0.0
    for outcome in outcomes:
        p1_o = float(p1.get(outcome, 0.0))
        p2_o = float(p2.get(outcome, 0.0))
        m_o = b * p1_o + (1.0 - b) * p2_o
        if m_o <= 0.0:
            continue
        b_prime = b * p1_o / m_o
        movement += m_o * abs(b_prime - b)
    return movement


def binary_identity_rhs(b: float, p1: Mapping[str, float], p2: Mapping[str, float]) -> float:
    return 2.0 * prior_dispersion_binary(b) * total_variation(p1, p2)


def voi_bound_binary(
    b: float,
    p1: Mapping[str, float],
    p2: Mapping[str, float],
    *,
    conventions: MeasureConventions | None = None,
    atol: float = DEFAULT_ATOL,
    rtol: float = DEFAULT_RTOL,
) -> BinaryVoIBound:
    conventions = conventions or MeasureConventions()
    tv = total_variation(p1, p2)
    kl_12 = kl_divergence(p1, p2)
    kl_21 = kl_divergence(p2, p1)
    finite = [value for value in (kl_12, kl_21) if not math.isinf(value)]
    if finite:
        kl_used = min(finite)
        orientation = "min_finite_direction"
    else:
        kl_used = math.inf
        orientation = "both_infinite"
    dispersion = prior_dispersion_binary(b)
    movement = expected_binary_belief_movement(b, p1, p2)
    identity_rhs = 2.0 * dispersion * tv
    identity_holds = within_tolerance(movement, identity_rhs, atol=atol, rtol=rtol)
    l_const = conventions.lipschitz_constant
    if conventions.lipschitz_norm is LipschitzNorm.SCALAR_BINARY:
        factor = 2.0 * l_const
    elif conventions.lipschitz_norm is LipschitzNorm.BELIEF_L1:
        factor = 4.0 * l_const
    else:
        raise ValueError(f"Unsupported Lipschitz norm {conventions.lipschitz_norm}")
    bound_tv = factor * dispersion * tv
    pinsker = pinsker_tv_from_kl(kl_used)
    bound_pinsker = factor * dispersion * pinsker if not math.isinf(pinsker) else math.inf
    return BinaryVoIBound(
        prior_b=b,
        prior_dispersion=dispersion,
        recoverability_tv=tv,
        recoverability_kl=kl_used,
        lipschitz_norm=conventions.lipschitz_norm.value,
        lipschitz_constant=l_const,
        voi_bound_tv=bound_tv,
        voi_bound_pinsker=bound_pinsker,
        expected_belief_movement=movement,
        identity_holds=identity_holds,
        pinsker_orientation=orientation,
    )


def voi_bound_general(
    components: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float],
    *,
    conventions: MeasureConventions | None = None,
) -> GeneralVoIBound:
    """VoI(a) <= L_U sqrt(2 JSD_b(a)) when V* is L_U-Lipschitz in L1 on the simplex."""

    conventions = conventions or MeasureConventions(lipschitz_norm=LipschitzNorm.BELIEF_L1)
    jsd = weighted_jsd(components, weights, units=conventions.divergence_units)
    l_u = conventions.lipschitz_constant
    bound = l_u * math.sqrt(2.0 * jsd) if not math.isinf(jsd) else math.inf
    return GeneralVoIBound(
        recoverability_jsd=jsd,
        conditional_mutual_information=jsd,
        lipschitz_norm=conventions.lipschitz_norm.value,
        lipschitz_constant=l_u,
        voi_bound_general=bound,
    )


def classify_bound_tightness(
    empirical: float,
    bound: float,
    *,
    ratio: float | None = None,
) -> str:
    """Operational tightness of a valid Lipschitz bound. Not a theorem label.

    tight: ratio >= 0.8; useful: >= 0.3; loose: >= 0.05; vacuous otherwise.
    Violations are recorded separately and never relabeled as tightness.
    """

    if empirical > bound + 1e-12:
        return "violated"
    if math.isinf(bound):
        return "vacuous"
    if abs(bound) <= 1e-15:
        return "tight" if abs(empirical) <= 1e-12 else "violated"
    if ratio is None:
        ratio = empirical / bound if bound else math.inf
    if math.isinf(ratio):
        return "vacuous"
    if ratio >= 0.8:
        return "tight"
    if ratio >= 0.3:
        return "useful"
    if ratio >= 0.05:
        return "loose"
    return "vacuous"


def bound_gap(empirical: float, bound: float) -> dict[str, float | bool | str]:
    gap = bound - empirical
    violated = empirical > bound + 1e-12
    if bound in (0.0, math.inf) or math.isinf(bound):
        ratio = math.inf
    else:
        ratio = empirical / bound
    tightness = classify_bound_tightness(empirical, bound, ratio=ratio)
    return {
        "voi_empirical": empirical,
        "voi_bound": bound,
        "voi_bound_gap": gap,
        "voi_bound_ratio": ratio,
        "voi_bound_violated": violated,
        "voi_bound_tightness": tightness,
        "tightness": tightness,
    }


def binary_zero_one_value(b: float) -> float:
    """V*(b) for two hypotheses under 0-1 utility: max(b, 1-b). Lipschitz L_b = 1."""

    return max(b, 1.0 - b)


def empirical_binary_voi_zero_one(
    b: float,
    p1: Mapping[str, float],
    p2: Mapping[str, float],
) -> float:
    """E_o[V*(b'(o)) - V*(b)] for 0-1 utility. Independent of the Lipschitz bound."""

    value_now = binary_zero_one_value(b)
    outcomes = sorted(set(p1) | set(p2))
    expected = 0.0
    for outcome in outcomes:
        p1_o = float(p1.get(outcome, 0.0))
        p2_o = float(p2.get(outcome, 0.0))
        m_o = b * p1_o + (1.0 - b) * p2_o
        if m_o <= 0.0:
            continue
        b_prime = b * p1_o / m_o
        expected += m_o * binary_zero_one_value(b_prime)
    return expected - value_now


def empirical_decision_flip_probability(
    b: float,
    p1: Mapping[str, float],
    p2: Mapping[str, float],
) -> float:
    """P_o(argmax_{0-1} changes) under a Bayes update. Decision Recoverability Score.

    This is not SPRT optimality and not a Lipschitz bound. It estimates whether
    available observations can change the committed 0-1 decision.
    """

    current = 1 if b >= 0.5 else 0
    outcomes = sorted(set(p1) | set(p2))
    flip = 0.0
    for outcome in outcomes:
        p1_o = float(p1.get(outcome, 0.0))
        p2_o = float(p2.get(outcome, 0.0))
        m_o = b * p1_o + (1.0 - b) * p2_o
        if m_o <= 0.0:
            continue
        b_prime = b * p1_o / m_o
        after = 1 if b_prime >= 0.5 else 0
        if after != current:
            flip += m_o
    return flip


def binary_zero_one_q_explore(
    b: float,
    p1: Mapping[str, float],
    p2: Mapping[str, float],
    *,
    cost: float,
) -> float:
    """One-step expected 0-1 value of EXPLORE minus declared cost."""

    return binary_zero_one_value(b) + empirical_binary_voi_zero_one(b, p1, p2) - cost
