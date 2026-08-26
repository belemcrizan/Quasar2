"""Prespecified recoverability-stress regimes.

Regimes are generated from frozen parameters. They are not tuned after seeing
which cases make Decision Recoverability Score win.
"""

from __future__ import annotations

from typing import Any, Mapping

from quasar2.math.voi import empirical_binary_voi_zero_one
from quasar2.theory.kernels import (
    bernoulli_pair,
    categorical_pair,
    gaussian_pair,
    heavy_overlap_pair,
    mixture_pair,
    multimodal_pair,
    near_identical_pair,
)


def _entropy_bits(b: float) -> float:
    import math

    if b <= 0.0 or b >= 1.0:
        return 0.0
    return -(b * math.log(b) + (1.0 - b) * math.log(1.0 - b)) / math.log(2.0)


# Frozen generative parameters. Do not edit after Gate-1 confirmatory access.
REGIME_SPECS: tuple[dict[str, Any], ...] = (
    {
        "regime_id": "high_H_high_R",
        "split_role": "development",
        "belief_grid": (0.46, 0.50, 0.54),
        "true": "bernoulli_0.90",
        "proxy": "bernoulli_0.90",
        "purpose": "pro-QUASAR: high uncertainty, discriminative evidence",
    },
    {
        "regime_id": "high_H_low_R",
        "split_role": "development",
        "belief_grid": (0.46, 0.50, 0.54),
        "true": "near_identical",
        "proxy": "near_identical",
        "purpose": "anti-QUASAR: high uncertainty, uninformative evidence",
    },
    {
        "regime_id": "low_H_high_R",
        "split_role": "model_selection",
        "belief_grid": (0.12, 0.18, 0.88),
        "true": "bernoulli_0.90",
        "proxy": "bernoulli_0.90",
        "purpose": "EXPLORE often unnecessary despite recoverable evidence",
    },
    {
        "regime_id": "low_H_low_R",
        "split_role": "model_selection",
        "belief_grid": (0.12, 0.18, 0.88),
        "true": "near_identical",
        "proxy": "near_identical",
        "purpose": "ANSWER/DEFER should dominate",
    },
    {
        "regime_id": "near_zero_treatment",
        "split_role": "model_selection",
        "belief_grid": (0.40, 0.50, 0.60),
        "true": "heavy_overlap",
        "proxy": "heavy_overlap",
        "purpose": "near-zero treatment effect; label noise stress",
    },
    {
        "regime_id": "false_recoverability",
        "split_role": "registered_test",
        "belief_grid": (0.46, 0.50, 0.54),
        "true": "near_identical",
        "proxy": "bernoulli_0.90",
        "purpose": "proxy-failure: proxy says discriminative, true kernels are not",
    },
    {
        "regime_id": "hidden_recoverability",
        "split_role": "registered_test",
        "belief_grid": (0.46, 0.50, 0.54),
        "true": "bernoulli_0.90",
        "proxy": "near_identical",
        "purpose": "proxy-failure: proxy is weak, useful evidence exists",
    },
    {
        "regime_id": "misspecified_observation",
        "split_role": "registered_test",
        "belief_grid": (0.30, 0.50, 0.70),
        "true": "bernoulli_0.92",
        "proxy": "heavy_overlap",
        "purpose": "misspecified observation model",
    },
    {
        "regime_id": "heldout_family_true_proxy",
        "split_role": "registered_test",
        "belief_grid": (0.46, 0.50, 0.54),
        "true": "multimodal",
        "proxy": "multimodal",
        "purpose": "held-out generative family with matched proxy",
    },
    {
        "regime_id": "sealed_pro",
        "split_role": "sealed_replication",
        "belief_grid": (0.48, 0.50, 0.52),
        "true": "gaussian_gap_2",
        "proxy": "gaussian_gap_2",
        "purpose": "sealed; not used for Gate-1 decision this cycle",
    },
    {
        "regime_id": "sealed_anti",
        "split_role": "sealed_replication",
        "belief_grid": (0.48, 0.50, 0.52),
        "true": "categorical_overlap_0.85",
        "proxy": "bernoulli_0.90",
        "purpose": "sealed anti-QUASAR / proxy mismatch; unused this cycle",
    },
)

KERNEL_LIBRARY: dict[str, dict[str, dict[str, float]]] = {
    "bernoulli_0.90": bernoulli_pair(0.90),
    "bernoulli_0.92": bernoulli_pair(0.92),
    "near_identical": near_identical_pair(),
    "heavy_overlap": heavy_overlap_pair(),
    "multimodal": multimodal_pair(),
    "mixture": mixture_pair(),
    "gaussian_gap_2": gaussian_pair(mean_gap=2.0),
    "categorical_overlap_0.85": categorical_pair(0.85),
}

COSTS: tuple[float, ...] = (0.02, 0.10, 0.25)


def kernels_named(name: str) -> dict[str, dict[str, float]]:
    if name not in KERNEL_LIBRARY:
        raise KeyError(name)
    return KERNEL_LIBRARY[name]


def generate_regime_states() -> list[dict[str, Any]]:
    """Every state is determined by frozen specs. No post-hoc case insertion."""

    rows: list[dict[str, Any]] = []
    for spec in REGIME_SPECS:
        true_kernels = kernels_named(str(spec["true"]))
        proxy_kernels = kernels_named(str(spec["proxy"]))
        for b in spec["belief_grid"]:
            for cost in COSTS:
                belief = {"H1": float(b), "H2": 1.0 - float(b)}
                voi_oracle = empirical_binary_voi_zero_one(float(b), true_kernels["H1"], true_kernels["H2"])
                rows.append(
                    {
                        "state_id": f"{spec['regime_id']}|b={b}|c={cost}",
                        "cluster_id": spec["regime_id"],
                        "regime_id": spec["regime_id"],
                        "split_role": spec["split_role"],
                        "purpose": spec["purpose"],
                        "belief": belief,
                        "b": float(b),
                        "entropy": _entropy_bits(float(b)),
                        "true_kernels": true_kernels,
                        "proxy_kernels": proxy_kernels,
                        "true_kernel_name": spec["true"],
                        "proxy_kernel_name": spec["proxy"],
                        "proxy_matches_true": spec["true"] == spec["proxy"],
                        "explore_cost": float(cost),
                        "voi_oracle_raw": voi_oracle,
                        "delta_u_force_explore": voi_oracle - float(cost),
                    }
                )
    return rows


def split_counts(states: list[Mapping[str, Any]] | None = None) -> dict[str, int]:
    rows = states if states is not None else generate_regime_states()
    counts: dict[str, int] = {}
    for row in rows:
        role = str(row["split_role"])
        counts[role] = counts.get(role, 0) + 1
    return counts
