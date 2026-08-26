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


def bound_gap(empirical: float, bound: float) -> dict[str, float | bool]:
    gap = bound - empirical
    violated = empirical > bound
    ratio = empirical / bound if bound not in (0.0, math.inf) else math.inf
    return {
        "voi_empirical": empirical,
        "voi_bound": bound,
        "voi_bound_gap": gap,
        "voi_bound_ratio": ratio,
        "voi_bound_violated": violated,
    }
