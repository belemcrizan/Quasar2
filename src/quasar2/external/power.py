"""Power / precision before expensive external runs.

Cluster-aware sample size for a mean difference, not a p-value fetish.
"""

from __future__ import annotations

import math


def design_effect(mean_cluster_size: float, icc: float) -> float:
    m = max(1.0, float(mean_cluster_size))
    rho = min(0.99, max(0.0, float(icc)))
    return 1.0 + (m - 1.0) * rho


def n_for_ci_width(
    *,
    desired_half_width: float,
    sigma: float,
    mean_cluster_size: float,
    icc: float,
    z: float = 1.96,
) -> dict[str, float | int]:
    """Rows needed so a 95% CI half-width is about ``desired_half_width``."""

    deff = design_effect(mean_cluster_size, icc)
    hw = max(1e-6, float(desired_half_width))
    n_eff = (z * float(sigma) / hw) ** 2
    n_rows = int(math.ceil(n_eff * deff))
    n_clusters = int(math.ceil(n_rows / max(1.0, mean_cluster_size)))
    return {
        "desired_half_width": desired_half_width,
        "sigma": sigma,
        "icc": icc,
        "mean_cluster_size": mean_cluster_size,
        "design_effect": deff,
        "n_effective_independent": int(math.ceil(n_eff)),
        "n_rows": n_rows,
        "n_clusters": n_clusters,
        "z": z,
    }


def n_for_min_effect(
    *,
    min_effect: float,
    sigma: float,
    power: float = 0.8,
    alpha: float = 0.05,
    mean_cluster_size: float = 8.0,
    icc: float = 0.2,
) -> dict[str, float | int]:
    """Two-sided z approximation for detecting min_effect on a mean."""

    # z_{1-a/2} + z_{power}
    z_a = 1.96 if abs(alpha - 0.05) < 1e-9 else 1.96
    z_b = 0.8416 if abs(power - 0.8) < 1e-9 else 0.8416
    deff = design_effect(mean_cluster_size, icc)
    delta = max(1e-6, abs(min_effect))
    n_eff = ((z_a + z_b) * float(sigma) / delta) ** 2
    n_rows = int(math.ceil(n_eff * deff))
    return {
        "min_effect": min_effect,
        "sigma": sigma,
        "power": power,
        "alpha": alpha,
        "design_effect": deff,
        "n_effective_independent": int(math.ceil(n_eff)),
        "n_rows": n_rows,
        "n_clusters": int(math.ceil(n_rows / max(1.0, mean_cluster_size))),
        "note": "Approximation; not a sequential design. N=12 OPS is underpowered for |ΔU|=0.05.",
    }


def default_justification() -> dict[str, object]:
    ci = n_for_ci_width(desired_half_width=0.04, sigma=0.35, mean_cluster_size=6.0, icc=0.25)
    effect = n_for_min_effect(min_effect=0.05, sigma=0.35, mean_cluster_size=6.0, icc=0.25)
    return {
        "minimum_effect_size_utility": 0.05,
        "desired_ci_half_width": 0.04,
        "clustering": "object_or_intent family, not degradation variants",
        "ops_n12": "underpowered; variants of the same intent are not independent",
        "ci_width_plan": ci,
        "min_effect_plan": effect,
        "executed_this_cycle": "schema-faithful hundreds of states with clustered inference; not live TAP 10^5",
    }
