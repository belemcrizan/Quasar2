"""Controlled synthetic families, oracles, and anti-QUASAR regimes.

Generator family IDs, true mismatch, oracle R*, and oracle Q* are ORACLE_ONLY.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from quasar2.cycle2.action_value import estimate_action_values, q_net_map, tau_explore_from_q
from quasar2.cycle2.observation import (
    CORRUPTION_KINDS,
    corrupt_kernels,
    finite_entropy,
    invert_kernels,
    mismatch_severity,
    mix_kernels,
)
from quasar2.cycle2.recoverability_state import (
    belief_margin,
    estimate_recoverability_state,
)
from quasar2.theory.kernels import (
    bernoulli_pair,
    heavy_overlap_pair,
    multimodal_pair,
    near_identical_pair,
)


BENCHMARK_VERSION = "cycle2-synth-v1"

FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "EasySeparable": {
        "true": lambda: bernoulli_pair(0.92),
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "development",
        "anti_quasar": False,
    },
    "HeavyOverlap": {
        "true": heavy_overlap_pair,
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "development",
        "anti_quasar": False,
    },
    "CostDominated": {
        "true": lambda: bernoulli_pair(0.80),
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "development",
        "anti_quasar": True,
        "cost_override": 0.55,
    },
    "AnswerDominated": {
        "true": lambda: bernoulli_pair(0.90),
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "development",
        "anti_quasar": True,
        "belief_grid": (0.88, 0.92, 0.96),
    },
    "ExploreDominated": {
        "true": lambda: bernoulli_pair(0.93),
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "development",
        "anti_quasar": False,
        "belief_grid": (0.48, 0.50, 0.52),
    },
    "AskDominated": {
        "true": near_identical_pair,
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "development",
        "anti_quasar": False,
        "belief_grid": (0.48, 0.50, 0.52),
        "ask_better": True,
    },
    "NearIdentical": {
        "true": near_identical_pair,
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "calibration",
        "anti_quasar": True,
    },
    "MissingEvidence": {
        "true": lambda: {"H1": {"0": 0.5, "1": 0.5}, "H2": {"0": 0.5, "1": 0.5}},
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": True,
    },
    "OpenSet": {
        "true": lambda: bernoulli_pair(0.70),
        "proxy": "matched",
        "open_set": True,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": False,
    },
    "ProxyMismatch": {
        "true": lambda: bernoulli_pair(0.90),
        "proxy": "near_identical",
        "open_set": False,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": False,
    },
    "CorrelatedEvidence": {
        "true": lambda: bernoulli_pair(0.88),
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.85,
        "role": "holdout",
        "anti_quasar": False,
    },
    "AdversarialProxy": {
        "true": near_identical_pair,
        "proxy": "bernoulli_0.90",
        "open_set": False,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": True,
    },
    "AntiClear": {
        "true": lambda: bernoulli_pair(0.99),
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": True,
        "belief_grid": (0.97, 0.98, 0.99),
        "cost_override": 0.02,
    },
    "NonRecoverableAmbiguity": {
        "true": near_identical_pair,
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": True,
        "belief_grid": (0.48, 0.50, 0.52),
    },
    "Multimodal": {
        "true": multimodal_pair,
        "proxy": "matched",
        "open_set": False,
        "redundancy": 0.0,
        "role": "holdout",
        "anti_quasar": False,
    },
}

_PROXY_LIB = {
    "matched": None,
    "near_identical": near_identical_pair(),
    "bernoulli_0.90": bernoulli_pair(0.90),
    "heavy_overlap": heavy_overlap_pair(),
}

DEFAULT_BELIEFS = (0.20, 0.35, 0.50, 0.65, 0.80)
DEFAULT_COSTS = (0.02, 0.10, 0.25)
DEFAULT_RHOS = (0.5, 1.4, 3.0)


def _belief(b: float, open_set: bool) -> dict[str, float]:
    if open_set:
        unknown = 0.55
        scale = 1.0 - unknown
        return {"H1": b * scale, "H2": (1.0 - b) * scale, "H_unknown": unknown}
    return {"H1": float(b), "H2": 1.0 - float(b)}


def generate_family_states(
    *,
    beliefs: tuple[float, ...] = DEFAULT_BELIEFS,
    costs: tuple[float, ...] = DEFAULT_COSTS,
    rhos: tuple[float, ...] = (1.4,),
    seed: int = 0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family, spec in FAMILY_SPECS.items():
        true = spec["true"]()
        proxy_name = spec["proxy"]
        proxy = dict(true) if proxy_name == "matched" else dict(_PROXY_LIB[proxy_name])
        grid = spec.get("belief_grid", beliefs)
        cost_values = (float(spec["cost_override"]),) if "cost_override" in spec else costs
        for b in grid:
            for use_cost in cost_values:
                for rho in rhos:
                    belief = _belief(float(b), bool(spec["open_set"]))
                    unknown = float(belief.get("H_unknown", 0.0))
                    oracle_q = q_net_map(
                        estimate_action_values(
                            belief,
                            true,
                            explore_cost=use_cost,
                            rho=rho,
                            unknown_mass=unknown,
                            provenance="ORACLE_ONLY",
                            ask_model="truthful" if spec.get("ask_better") else "noisy",
                        )
                    )
                    rec_star = estimate_recoverability_state(
                        belief,
                        true,
                        true_kernels=true,
                        explore_cost=use_cost,
                        redundancy=float(spec["redundancy"]),
                        oracle_run=True,
                    )
                    rec_hat = estimate_recoverability_state(
                        belief,
                        proxy,
                        true_kernels=None,
                        explore_cost=use_cost,
                        redundancy=float(spec["redundancy"]),
                        oracle_run=False,
                    )
                    r_star = rec_star.point_estimate
                    r_hat = rec_hat.point_estimate
                    error_r = r_hat - r_star
                    state_id = f"{family}|b={b}|c={use_cost}|rho={rho}|seed={seed}"
                    rows.append(
                        {
                            "state_id": state_id,
                            "family": family,
                            "split_role": spec["role"],
                            "anti_quasar": bool(spec["anti_quasar"]),
                            "open_set": bool(spec["open_set"]),
                            "redundancy": float(spec["redundancy"]),
                            "belief": belief,
                            "b": float(b),
                            "entropy": finite_entropy(belief),
                            "belief_margin": belief_margin(belief),
                            "true_kernels": true,
                            "proxy_kernels": proxy,
                            "proxy_matches_true": proxy_name == "matched",
                            "explore_cost": use_cost,
                            "rho": float(rho),
                            "unknown_mass": unknown,
                            "oracle_q": oracle_q,
                            "tau_explore_net": tau_explore_from_q(oracle_q),
                            "R_star": r_star,
                            "R_hat": r_hat,
                            "error_R": error_r,
                            "abs_error_R": abs(error_r),
                            "relative_error_R": None if abs(r_star) < 1e-9 else error_r / r_star,
                            "mismatch_mu_true": mismatch_severity(proxy, true),
                            "components_hat": rec_hat.to_dict(),
                            "components_star": rec_star.to_dict(),
                            "r_leverage": rec_hat.components.get("R_leverage"),
                            "cluster_id": family,
                            "oracle_only_fields": ("true_kernels", "oracle_q", "R_star", "components_star"),
                            "benchmark_version": BENCHMARK_VERSION,
                        }
                    )
    return rows


def generate_mismatch_curve(
    *,
    mus: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    beliefs: tuple[float, ...] = (0.35, 0.50, 0.65),
    cost: float = 0.10,
    rho: float = 1.4,
) -> list[dict[str, Any]]:
    true = bernoulli_pair(0.90)
    other = invert_kernels(true)
    rows = []
    for mu in mus:
        proxy = mix_kernels(true, other, mu)
        for b in beliefs:
            belief = {"H1": float(b), "H2": 1.0 - float(b)}
            oracle_q = q_net_map(
                estimate_action_values(belief, true, explore_cost=cost, rho=rho, provenance="ORACLE_ONLY")
            )
            rec_star = estimate_recoverability_state(belief, true, true_kernels=true, oracle_run=True)
            rec_hat = estimate_recoverability_state(belief, proxy, oracle_run=False)
            emp_policy_q = q_net_map(
                estimate_action_values(belief, proxy, explore_cost=cost, rho=rho, provenance="empirical_proxy")
            )
            selected = max(emp_policy_q, key=lambda k: (emp_policy_q[k], k))
            optimal = max(oracle_q, key=lambda k: (oracle_q[k], k))
            regret = oracle_q[optimal] - oracle_q[selected]
            tau = tau_explore_from_q(oracle_q)
            rows.append(
                {
                    "mu": mu,
                    "constructed_mismatch": mismatch_severity(proxy, true),
                    "b": b,
                    "entropy": finite_entropy(belief),
                    "R_hat": rec_hat.point_estimate,
                    "R_star": rec_star.point_estimate,
                    "abs_error_R": abs(rec_hat.point_estimate - rec_star.point_estimate),
                    "tau_explore_net": tau,
                    "delta_u": tau,
                    "selected": selected,
                    "optimal": optimal,
                    "regret": regret,
                    "false_explore": int(selected == "EXPLORE" and tau <= 0.0),
                    "missed_explore": int(selected != "EXPLORE" and tau > 0.05),
                    "cluster_id": f"mu={mu}",
                }
            )
    return rows


def generate_corruption_rows() -> list[dict[str, Any]]:
    true_sep = bernoulli_pair(0.90)
    true_overlap = near_identical_pair()
    rows = []
    for kind in CORRUPTION_KINDS:
        for severity in (0.3, 0.8):
            for truth_name, truth in (("separable", true_sep), ("overlap", true_overlap)):
                proxy = corrupt_kernels(truth, kind=kind, severity=severity, seed=0)
                belief = {"H1": 0.5, "H2": 0.5}
                rec_star = estimate_recoverability_state(belief, truth, true_kernels=truth, oracle_run=True)
                rec_hat = estimate_recoverability_state(belief, proxy, oracle_run=False)
                tau = tau_explore_from_q(
                    q_net_map(estimate_action_values(belief, truth, provenance="ORACLE_ONLY"))
                )
                rows.append(
                    {
                        "kind": kind,
                        "severity": severity,
                        "truth": truth_name,
                        "R_hat": rec_hat.point_estimate,
                        "R_star": rec_star.point_estimate,
                        "false_high": rec_hat.point_estimate > 0.4 and rec_star.point_estimate < 0.15,
                        "false_low": rec_hat.point_estimate < 0.15 and rec_star.point_estimate > 0.4,
                        "tau_explore_net": tau,
                        "cluster_id": kind,
                    }
                )
    return rows


def cost_surface(
    *,
    rhos: tuple[float, ...] = DEFAULT_RHOS,
    kappas: tuple[float, ...] = (0.02, 0.10, 0.40),
    b: float = 0.5,
) -> list[dict[str, Any]]:
    true = bernoulli_pair(0.88)
    belief = {"H1": b, "H2": 1.0 - b}
    rows = []
    for rho in rhos:
        for kappa in kappas:
            q = q_net_map(
                estimate_action_values(belief, true, explore_cost=kappa, rho=rho, provenance="ORACLE_ONLY")
            )
            selected = max(q, key=lambda k: (q[k], k))
            rows.append(
                {
                    "rho": rho,
                    "kappa": kappa,
                    "selected": selected,
                    "Q_ANSWER": q["ANSWER"],
                    "Q_EXPLORE": q["EXPLORE"],
                    "Q_ASK": q["ASK"],
                    "Q_DEFER": q["DEFER"],
                    "Q_ANALYZE": q["ANALYZE"],
                    "NEU": q[selected],
                }
            )
    return rows


def split_manifest(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    payload = hashlib.sha256(
        "|".join(sorted(str(r["state_id"]) for r in rows)).encode("utf-8")
    ).hexdigest()
    roles: dict[str, list[str]] = {}
    for row in rows:
        roles.setdefault(str(row["split_role"]), []).append(str(row["family"]))
    return {
        "schema_version": "cycle2.1",
        "benchmark_version": BENCHMARK_VERSION,
        "n": len(rows),
        "by_role": {k: sorted(set(v)) for k, v in roles.items()},
        "state_id_hash": payload,
    }
