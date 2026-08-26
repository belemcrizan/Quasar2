"""Recoverability state: R_hat, sigma_R, M_R, and un-aggregated components."""

from __future__ import annotations

from typing import Mapping

from quasar2.cycle2.observation import finite_entropy, mismatch_severity
from quasar2.cycle2.types import RecoverabilityEstimate
from quasar2.math.divergences import total_variation
from quasar2.math.voi import empirical_decision_flip_probability
from quasar2.recoverability import ESTIMATORS, deployment_features


COMPONENT_NAMES = (
    "R_available",
    "R_accessible",
    "R_relevant",
    "R_novel",
    "R_leverage",
    "R_net",
)


def _top_pair(
    belief: Mapping[str, float],
    kernels: Mapping[str, Mapping[str, float]],
) -> tuple[str, str] | None:
    ranked = sorted(
        (h for h in belief if h in kernels),
        key=lambda h: (-float(belief[h]), h),
    )
    if len(ranked) < 2:
        return None
    return ranked[0], ranked[1]


def belief_margin(belief: Mapping[str, float]) -> float:
    ranked = sorted((float(v) for v in belief.values()), reverse=True)
    if len(ranked) < 2:
        return 1.0
    return ranked[0] - ranked[1]


def component_scores(
    belief: Mapping[str, float],
    *,
    proxy_kernels: Mapping[str, Mapping[str, float]],
    true_kernels: Mapping[str, Mapping[str, float]] | None,
    explore_cost: float,
    redundancy: float = 0.0,
    accessible: float | None = None,
) -> dict[str, float | None]:
    """Do not average these unless a registered aggregation is tested."""

    pair_proxy = _top_pair(belief, proxy_kernels)
    r_leverage = 0.0
    r_relevant = 0.0
    if pair_proxy is not None:
        left, right = pair_proxy
        b = float(belief.get(left, 0.0))
        r_leverage = empirical_decision_flip_probability(b, proxy_kernels[left], proxy_kernels[right])
        r_relevant = total_variation(proxy_kernels[left], proxy_kernels[right])
    r_available = None
    if true_kernels is not None:
        pair_true = _top_pair(belief, true_kernels)
        if pair_true is not None:
            left, right = pair_true
            r_available = total_variation(true_kernels[left], true_kernels[right])
    r_novel = max(0.0, 1.0 - redundancy)
    r_access = accessible
    r_net = None if r_available is None else max(0.0, float(r_available) - explore_cost)
    return {
        "R_available": r_available,
        "R_accessible": r_access,
        "R_relevant": r_relevant,
        "R_novel": r_novel,
        "R_leverage": r_leverage,
        "R_net": r_net,
    }


def estimate_recoverability_state(
    belief: Mapping[str, float],
    proxy_kernels: Mapping[str, Mapping[str, float]],
    *,
    estimator_name: str = "decision_recoverability",
    true_kernels: Mapping[str, Mapping[str, float]] | None = None,
    explore_cost: float = 0.10,
    redundancy: float = 0.0,
    accessible: float | None = None,
    oracle_run: bool = False,
) -> RecoverabilityEstimate:
    estimator = ESTIMATORS.get(estimator_name, ESTIMATORS["decision_recoverability"])
    result = estimator.estimate(belief, tuple(belief), "EXPLORE", proxy_kernels)
    components = component_scores(
        belief,
        proxy_kernels=proxy_kernels,
        true_kernels=true_kernels if oracle_run else None,
        explore_cost=explore_cost,
        redundancy=redundancy,
        accessible=accessible,
    )
    m_r = None
    if oracle_run and true_kernels is not None:
        m_r = mismatch_severity(proxy_kernels, true_kernels)
    # Kernel DRS is deterministic given the observation model: sampling sigma is 0,
    # but observation-model uncertainty is unknown unless oracle mismatch is available.
    sigma = 0.0 if oracle_run else None
    return RecoverabilityEstimate(
        point_estimate=float(result.score),
        uncertainty=sigma,
        calibration=None,
        misspecification_risk=m_r,
        estimator_family=estimator_name,
        provenance="proxy_kernels" if not oracle_run else "oracle_and_proxy",
        components=components,
    )


def deployment_observable_vector(
    belief: Mapping[str, float],
    proxy_kernels: Mapping[str, Mapping[str, float]],
) -> list[float]:
    return deployment_features(belief, tuple(belief), proxy_kernels)


def uncertainty_only(belief: Mapping[str, float]) -> dict[str, float]:
    return {
        "entropy": finite_entropy(belief),
        "belief_margin": belief_margin(belief),
        "top1": max((float(v) for v in belief.values()), default=0.0),
    }
