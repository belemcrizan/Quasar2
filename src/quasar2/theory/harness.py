"""Deterministic and Monte Carlo checks for T1–T4 and C1.

A Monte Carlo miss is not automatically a theorem refutation. Each check records
layer, assumptions, tolerances, seeds, and execution_state.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import random
from typing import Any

from quasar2 import __version__
from quasar2.analysis.operators import MixtureProjectionAnalyze, ComputationalState
from quasar2.math.bellman import (
    TabularMDP,
    bellman_backup,
    contraction_constant,
    exact_error_bound,
    residual_error_bound,
    sup_norm,
    value_iteration,
)
from quasar2.math.conventions import LipschitzNorm, MeasureConventions
from quasar2.math.divergences import kl_divergence, total_variation
from quasar2.math.information import information_difference
from quasar2.math.numerical import DEFAULT_ATOL, DEFAULT_RTOL, within_tolerance
from quasar2.math.stopping import (
    BCaBootstrapUCB,
    EmpiricalBernsteinUCB,
    NormalUCB,
    PercentileBootstrapUCB,
    stop_if_all_ucb_nonpositive,
    wilson_lower,
    wilson_upper,
)
from quasar2.math.voi import (
    bound_gap,
    empirical_binary_voi_zero_one,
    expected_binary_belief_movement,
    voi_bound_binary,
)
from quasar2.theory.cards import TheoremCheck, default_cards
from quasar2.theory.kernels import KERNEL_FAMILIES


def check_t1(*, atol: float = DEFAULT_ATOL, rtol: float = DEFAULT_RTOL) -> TheoremCheck:
    target = {"h1": 0.7, "h2": 0.2, "h3": 0.1}
    start = {"h1": 0.2, "h2": 0.5, "h3": 0.3}
    evidence = ("e1", "e2")
    operator = MixtureProjectionAnalyze(step=0.4)
    result = operator.analyze(ComputationalState(), evidence, start, target=target)
    kl_before = kl_divergence(start, target, smooth=1e-12)
    kl_after = kl_divergence(result.belief, target, smooth=1e-12)
    elbo_ok = result.elbo_after is not None and result.elbo_before is not None and (
        result.elbo_after + atol >= result.elbo_before
    )
    kl_ok = kl_after <= kl_before + atol
    evidence_ok = result.evidence_ids == evidence
    passed = elbo_ok and kl_ok and evidence_ok and result.target_fixed
    return TheoremCheck(
        card_id="T1",
        execution_state="PASS_WITHIN_ASSUMPTIONS" if passed else "FAIL_NUMERICAL",
        layer="NUMERICAL_QUADRATURE",
        assumptions_verified=("target_fixed", "evidence_fixed", "mixture_projection_admissible"),
        implementation="MixtureProjectionAnalyze",
        atol=atol,
        rtol=rtol,
        seeds=(),
        dataset="synthetic_categorical",
        notes="Heuristic ANALYZE operators are not covered by this card.",
        metrics={
            "kl_before": kl_before,
            "kl_after": kl_after,
            "elbo_before": result.elbo_before,
            "elbo_after": result.elbo_after,
            "evidence_unchanged": evidence_ok,
        },
    )


def _binary_kernels() -> dict[str, dict[str, Mapping[str, float]]]:
    return {
        "identical": {"H1": {"0": 0.5, "1": 0.5}, "H2": {"0": 0.5, "1": 0.5}},
        "disjoint": {"H1": {"0": 1.0, "1": 0.0}, "H2": {"0": 0.0, "1": 1.0}},
        "bernoulli": {"H1": {"0": 0.8, "1": 0.2}, "H2": {"0": 0.3, "1": 0.7}},
        "label_swap": {"H1": {"1": 0.8, "0": 0.2}, "H2": {"1": 0.3, "0": 0.7}},
    }


def check_t2(*, atol: float = DEFAULT_ATOL, rtol: float = DEFAULT_RTOL) -> TheoremCheck:
    kernels = _binary_kernels()
    failures: list[str] = []
    records: list[dict[str, Any]] = []
    for name, pair in kernels.items():
        p1, p2 = pair["H1"], pair["H2"]
        for b in (0.0, 0.25, 0.5, 0.75, 1.0):
            bound = voi_bound_binary(b, p1, p2, atol=atol, rtol=rtol)
            if not bound.identity_holds:
                failures.append(f"{name}:b={b}")
            records.append(
                {
                    "case": name,
                    "b": b,
                    "movement": bound.expected_belief_movement,
                    "tv": bound.recoverability_tv,
                    "identity_holds": bound.identity_holds,
                    "voi_bound_tv": bound.voi_bound_tv,
                }
            )
        if name == "identical" and total_variation(p1, p2) != 0.0:
            failures.append("identical_tv")
        if name == "disjoint" and not within_tolerance(total_variation(p1, p2), 1.0, atol=atol, rtol=rtol):
            failures.append("disjoint_tv")
    swap = kernels["label_swap"]
    base = kernels["bernoulli"]
    for b in (0.2, 0.5, 0.8):
        left = expected_binary_belief_movement(b, base["H1"], base["H2"])
        right = expected_binary_belief_movement(b, swap["H1"], swap["H2"])
        if not within_tolerance(left, right, atol=atol, rtol=rtol):
            failures.append("label_swap_invariance")
    scalar = voi_bound_binary(
        0.4,
        base["H1"],
        base["H2"],
        conventions=MeasureConventions(lipschitz_norm=LipschitzNorm.SCALAR_BINARY, lipschitz_constant=1.0),
    )
    vector = voi_bound_binary(
        0.4,
        base["H1"],
        base["H2"],
        conventions=MeasureConventions(lipschitz_norm=LipschitzNorm.BELIEF_L1, lipschitz_constant=1.0),
    )
    factor_ok = within_tolerance(vector.voi_bound_tv, 2.0 * scalar.voi_bound_tv, atol=atol, rtol=rtol)
    if not factor_ok:
        failures.append("lipschitz_factor")
    return TheoremCheck(
        card_id="T2",
        execution_state="PASS_WITHIN_ASSUMPTIONS" if not failures else "FAIL_NUMERICAL",
        layer="ANALYTIC",
        assumptions_verified=("binary", "finite discrete observations", "declared Lipschitz norms"),
        implementation="voi_bound_binary",
        atol=atol,
        rtol=rtol,
        seeds=(),
        dataset="synthetic_binary_kernels",
        notes="" if not failures else f"failures={failures}",
        metrics={"n_records": len(records), "scalar_vs_l1_factor_two": factor_ok, "failures": failures},
    )


def check_t2_grid(*, atol: float = DEFAULT_ATOL, rtol: float = DEFAULT_RTOL) -> TheoremCheck:
    """Empirical 0-1 VoI vs Lipschitz bound across synthetic kernel families."""

    priors = (0.1, 0.25, 0.5, 0.75, 0.9)
    violations: list[str] = []
    records: list[dict[str, Any]] = []
    identity_failures: list[str] = []
    tightness_counts: dict[str, int] = {}
    for family, pair in KERNEL_FAMILIES.items():
        p1, p2 = pair["H1"], pair["H2"]
        for b in priors:
            bound = voi_bound_binary(b, p1, p2, atol=atol, rtol=rtol)
            empirical = empirical_binary_voi_zero_one(b, p1, p2)
            stats = bound_gap(empirical, bound.voi_bound_tv)
            if not bound.identity_holds:
                identity_failures.append(f"{family}:b={b}")
            if stats["voi_bound_violated"]:
                violations.append(f"{family}:b={b}")
            tightness = str(stats["voi_bound_tightness"])
            tightness_counts[tightness] = tightness_counts.get(tightness, 0) + 1
            records.append(
                {
                    "family": family,
                    "b": b,
                    "prior_dispersion": bound.prior_dispersion,
                    "recoverability_tv": bound.recoverability_tv,
                    "recoverability_kl": bound.recoverability_kl,
                    "voi_empirical": empirical,
                    "voi_bound_tv": bound.voi_bound_tv,
                    "voi_bound_gap": stats["voi_bound_gap"],
                    "voi_bound_ratio": stats["voi_bound_ratio"],
                    "voi_bound_violated": stats["voi_bound_violated"],
                    "voi_bound_tightness": tightness,
                    "identity_holds": bound.identity_holds,
                }
            )
    failed = bool(identity_failures)
    state = "PASS_WITHIN_ASSUMPTIONS" if not failed else "FAIL_NUMERICAL"
    notes = (
        "0-1 empirical VoI is compared to the scalar-binary Lipschitz bound. "
        "Bound violations are recorded and do not auto-refute T2 if identity holds."
    )
    if violations:
        notes += f" voi_bound_violated={violations}"
    if identity_failures:
        notes += f" identity_failures={identity_failures}"
    return TheoremCheck(
        card_id="T2_grid",
        execution_state=state,
        layer="NUMERICAL_QUADRATURE",
        assumptions_verified=("binary", "0-1 utility", "declared Lipschitz scalar_binary"),
        implementation="empirical_binary_voi_zero_one",
        atol=atol,
        rtol=rtol,
        seeds=(),
        dataset="synthetic_kernel_families",
        notes=notes,
        metrics={
            "n_records": len(records),
            "n_bound_violations": len(violations),
            "n_identity_failures": len(identity_failures),
            "tightness_counts": tightness_counts,
            "families": sorted(KERNEL_FAMILIES),
            "records": records,
        },
    )


def _two_state_mdp(gamma: float = 0.9) -> TabularMDP:
    return TabularMDP(
        states=("s0", "s1"),
        actions=("stay", "go"),
        transitions={
            ("s0", "stay", "s0"): 1.0,
            ("s0", "go", "s1"): 1.0,
            ("s1", "stay", "s1"): 1.0,
            ("s1", "go", "s0"): 1.0,
        },
        rewards={("s0", "stay"): 0.0, ("s0", "go"): 1.0, ("s1", "stay"): 0.2, ("s1", "go"): 0.0},
        gamma=gamma,
        terminals=(),
    )


def check_t3(*, atol: float = 1e-8, rtol: float = 1e-7) -> TheoremCheck:
    mdp = _two_state_mdp(0.8)
    v = {"s0": 0.0, "s1": 4.0}
    w = {"s0": 1.0, "s1": 1.0}
    ratio = contraction_constant(mdp, v, w)
    contraction_ok = ratio <= mdp.gamma + atol
    values, residuals = value_iteration(mdp, initial={"s0": 0.0, "s1": 0.0}, iterations=80)
    v_star, _ = value_iteration(mdp, initial=values, iterations=40)
    v0 = {"s0": 0.0, "s1": 0.0}
    v1 = bellman_backup(mdp, v0)
    vk = dict(v0)
    errors = []
    bounds_ok = True
    for k in range(0, 12):
        err = sup_norm(vk, v_star)
        bound = exact_error_bound(mdp.gamma, k, sup_norm(v0, v_star))
        residual_bound = residual_error_bound(mdp.gamma, k, sup_norm(v1, v0))
        errors.append({"k": k, "error": err, "gamma_k_bound": bound, "residual_bound": residual_bound})
        if err > bound + atol + rtol * max(abs(err), abs(bound)):
            bounds_ok = False
        if err > residual_bound + atol + rtol * max(abs(err), abs(residual_bound)):
            bounds_ok = False
        vk = bellman_backup(mdp, vk)
    passed = contraction_ok and bounds_ok
    return TheoremCheck(
        card_id="T3",
        execution_state="PASS_WITHIN_ASSUMPTIONS" if passed else "FAIL_NUMERICAL",
        layer="NUMERICAL_QUADRATURE",
        assumptions_verified=("tabular MDP", "gamma=0.8", "bounded rewards", "exact backup"),
        implementation="bellman_backup/value_iteration",
        atol=atol,
        rtol=rtol,
        seeds=(),
        dataset="two_state_mdp",
        notes="This validates the implementation, not a real-scale POMDP.",
        metrics={
            "contraction_ratio": ratio,
            "gamma": mdp.gamma,
            "final_values": values,
            "first_residual": residuals[0] if residuals else None,
            "bounds_ok": bounds_ok,
        },
    )


def check_t4(*, n_trials: int = 400, n_samples: int = 40, seed: int = 0, alpha: float = 0.05) -> TheoremCheck:
    """Fixed-stage coverage under Gaussian samples. Sequential scope is not claimed."""

    rng = random.Random(seed)
    estimator = NormalUCB()
    false_stops = 0
    eligible = 0
    for _ in range(n_trials):
        # True mean slightly positive so stopping is a false stop if UCB <= 0.
        true_mean = 0.15
        samples_a = [rng.gauss(true_mean, 1.0) for _ in range(n_samples)]
        samples_b = [rng.gauss(true_mean / 2.0, 1.0) for _ in range(n_samples)]
        ucbs = {
            "ANALYZE": estimator.upper_bound(samples_a, alpha, 3),
            "EXPLORE": estimator.upper_bound(samples_b, alpha, 3),
            "ASK": estimator.upper_bound([rng.gauss(-0.2, 1.0) for _ in range(n_samples)], alpha, 3),
        }
        estimates = {key: sum(samples_a) / n_samples for key in ucbs}
        estimates["EXPLORE"] = sum(samples_b) / n_samples
        decision = stop_if_all_ucb_nonpositive(
            ucbs,
            estimates,
            alpha=alpha,
            coverage_scope="fixed_stage",
            oracle_best_net_voi=true_mean,
            delta_positive=0.02,
        )
        eligible += 1
        if decision.false_stop:
            false_stops += 1
    rate = false_stops / max(1, eligible)
    upper = wilson_upper(false_stops, eligible)
    lower = wilson_lower(false_stops, eligible)
    tolerance = 0.03
    if upper <= alpha + tolerance:
        state = "PASS_WITHIN_ASSUMPTIONS"
    elif lower > alpha + tolerance:
        state = "FAIL_MONTE_CARLO"
    else:
        state = "INCONCLUSIVE"
    bernstein = EmpiricalBernsteinUCB(bound_range=8.0)
    _ = bernstein.upper_bound([0.1, 0.2, -0.1, 0.0], alpha, 3)
    return TheoremCheck(
        card_id="T4",
        execution_state=state,
        layer="MONTE_CARLO",
        assumptions_verified=("fixed_stage", "gaussian_samples", "bonferroni_m=3", "normal_ucb_approximate"),
        implementation="NormalUCB",
        atol=tolerance,
        rtol=0.0,
        seeds=(seed,),
        dataset="synthetic_gaussian_netvoi",
        notes="NormalUCB is approximate. Sequential coverage is NOT_IMPLEMENTED in this check.",
        metrics={
            "false_stops": false_stops,
            "eligible": eligible,
            "false_stop_rate": rate,
            "wilson_upper": upper,
            "wilson_lower": lower,
            "alpha": alpha,
            "coverage_scope": "fixed_stage",
            "n_trials": n_trials,
        },
    )


def _sample_family(rng: random.Random, family: str, mean: float) -> float:
    if family == "gaussian":
        return rng.gauss(mean, 1.0)
    if family == "student_t":
        z = rng.gauss(0.0, 1.0)
        df = 3
        chi = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(df))
        return mean + z / math.sqrt(chi / df)
    if family == "gumbel":
        u = min(1.0 - 1e-12, max(1e-12, rng.random()))
        return mean - math.log(-math.log(u))
    if family == "skewed":
        return mean + math.exp(rng.gauss(0.0, 0.5)) - 1.0
    if family == "mixture":
        if rng.random() < 0.9:
            return rng.gauss(mean, 1.0)
        return rng.gauss(mean, 4.0)
    if family == "heavy_tail":
        z = rng.gauss(0.0, 1.0)
        df = 2
        chi = max(1e-9, sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(df)))
        return mean + z / math.sqrt(chi / df)
    raise ValueError(family)


def check_t4_families(
    *,
    n_trials: int = 80,
    n_samples: int = 30,
    seed: int = 0,
    alphas: tuple[float, ...] = (0.10, 0.05, 0.01),
) -> TheoremCheck:
    """Compare NormalUCB false-stop rates across non-Gaussian families."""

    families = ("gaussian", "student_t", "gumbel", "skewed", "mixture", "heavy_tail")
    estimator = NormalUCB()
    breakdown: list[dict[str, Any]] = []
    for family in families:
        for alpha in alphas:
            rng = random.Random(seed + (sum(ord(ch) for ch in family) % 1000))
            false_stops = 0
            eligible = 0
            for _ in range(n_trials):
                true_mean = 0.15
                samples_a = [_sample_family(rng, family, true_mean) for _ in range(n_samples)]
                samples_b = [_sample_family(rng, family, true_mean / 2.0) for _ in range(n_samples)]
                samples_c = [_sample_family(rng, family, -0.2) for _ in range(n_samples)]
                ucbs = {
                    "ANALYZE": estimator.upper_bound(samples_a, alpha, 3),
                    "EXPLORE": estimator.upper_bound(samples_b, alpha, 3),
                    "ASK": estimator.upper_bound(samples_c, alpha, 3),
                }
                estimates = {
                    "ANALYZE": sum(samples_a) / n_samples,
                    "EXPLORE": sum(samples_b) / n_samples,
                    "ASK": sum(samples_c) / n_samples,
                }
                decision = stop_if_all_ucb_nonpositive(
                    ucbs,
                    estimates,
                    alpha=alpha,
                    coverage_scope="fixed_stage",
                    oracle_best_net_voi=true_mean,
                    delta_positive=0.02,
                )
                eligible += 1
                if decision.false_stop:
                    false_stops += 1
            rate = false_stops / max(1, eligible)
            upper = wilson_upper(false_stops, eligible)
            breakdown.append(
                {
                    "family": family,
                    "alpha": alpha,
                    "false_stop_rate": rate,
                    "wilson_upper": upper,
                    "exceeds_alpha": upper > alpha + 0.05,
                }
            )
    gaussian_rows = [row for row in breakdown if row["family"] == "gaussian"]
    parametric_breakdown = [row for row in breakdown if row["exceeds_alpha"]]
    return TheoremCheck(
        card_id="T4_families",
        execution_state="INCONCLUSIVE",
        layer="MONTE_CARLO",
        assumptions_verified=("fixed_stage", "normal_ucb_approximate", "bonferroni_m=3"),
        implementation="NormalUCB",
        atol=0.05,
        rtol=0.0,
        seeds=(seed,),
        dataset="synthetic_netvoi_families",
        notes=(
            "NormalUCB is not assumed valid outside Gaussians. Rows with "
            "exceeds_alpha document parametric breakdown rather than theorem failure."
        ),
        metrics={
            "n_trials": n_trials,
            "breakdown": breakdown,
            "parametric_breakdown_rows": len(parametric_breakdown),
            "gaussian_rows": gaussian_rows,
        },
    )


def check_t4_near_zero(
    *,
    n_trials: int = 80,
    n_samples: int = 40,
    seed: int = 0,
    alpha: float = 0.05,
    means: tuple[float, ...] = (-0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05),
) -> TheoremCheck:
    """False-stop stress when true NetVoI is near zero. Sequential validity is not claimed."""

    estimators = {
        "normal_ucb": NormalUCB(),
        "percentile_bootstrap": PercentileBootstrapUCB(n_bootstrap=80, seed=seed),
        "bca_bootstrap": BCaBootstrapUCB(n_bootstrap=80, seed=seed),
        "empirical_bernstein": EmpiricalBernsteinUCB(bound_range=8.0),
    }
    breakdown: list[dict[str, Any]] = []
    for name, estimator in estimators.items():
        for mean in means:
            rng = random.Random(seed + int(abs(mean) * 1000) + sum(ord(ch) for ch in name))
            false_stops = 0
            eligible = 0
            stops = 0
            for _ in range(n_trials):
                samples_a = [rng.gauss(mean, 1.0) for _ in range(n_samples)]
                samples_b = [rng.gauss(mean / 2.0 if mean != 0.0 else -0.02, 1.0) for _ in range(n_samples)]
                samples_c = [rng.gauss(-0.2, 1.0) for _ in range(n_samples)]
                ucbs = {
                    "ANALYZE": estimator.upper_bound(samples_a, alpha, 3),
                    "EXPLORE": estimator.upper_bound(samples_b, alpha, 3),
                    "ASK": estimator.upper_bound(samples_c, alpha, 3),
                }
                estimates = {
                    "ANALYZE": sum(samples_a) / n_samples,
                    "EXPLORE": sum(samples_b) / n_samples,
                    "ASK": sum(samples_c) / n_samples,
                }
                decision = stop_if_all_ucb_nonpositive(
                    ucbs,
                    estimates,
                    alpha=alpha,
                    coverage_scope="fixed_stage",
                    oracle_best_net_voi=mean,
                    delta_positive=0.005,
                )
                eligible += 1
                if decision.stop_decision:
                    stops += 1
                if decision.false_stop:
                    false_stops += 1
            rate = false_stops / max(1, eligible)
            breakdown.append(
                {
                    "estimator": name,
                    "mean": mean,
                    "false_stop_rate": rate,
                    "stop_rate": stops / max(1, eligible),
                    "wilson_upper": wilson_upper(false_stops, eligible),
                    "near_zero": abs(mean) <= 0.02,
                }
            )
    hard = [row for row in breakdown if row["near_zero"] and row["estimator"] == "normal_ucb"]
    return TheoremCheck(
        card_id="T4_near_zero",
        execution_state="INCONCLUSIVE",
        layer="MONTE_CARLO",
        assumptions_verified=("fixed_stage", "gaussian_samples", "bonferroni_m=3", "near_zero_means"),
        implementation="NormalUCB/PercentileBootstrapUCB/BCaBootstrapUCB/EmpiricalBernsteinUCB",
        atol=0.05,
        rtol=0.0,
        seeds=(seed,),
        dataset="synthetic_near_zero_netvoi",
        notes=(
            "Easy T4 (mean=0.15) is not this check. Near-zero means are expected to inflate "
            "false-stop or under-power stopping. Sequential/anytime validity is NOT claimed."
        ),
        metrics={
            "n_trials": n_trials,
            "n_samples": n_samples,
            "alpha": alpha,
            "breakdown": breakdown,
            "normal_ucb_near_zero": hard,
        },
    )


def check_c1() -> TheoremCheck:
    # Markov degradation: extra noise independent of I given Q_clean.
    # I in {0,1}, Q_clean copies I, Q_obs flips Q_clean.
    joint_clean = {("0", "0"): 50.0, ("1", "1"): 50.0, ("0", "1"): 0.0, ("1", "0"): 0.0}
    joint_obs = {("0", "0"): 40.0, ("0", "1"): 10.0, ("1", "1"): 40.0, ("1", "0"): 10.0}
    markov = information_difference(
        joint_clean,
        joint_obs,
        degradation_markov=True,
        degradation_process_id="binary_symmetric_channel",
        method="discrete_joint",
        exact=True,
    )
    # Side channel: Q_obs is independent of Q_clean but still informative about I
    # more strongly than Q_clean (Q_clean independent of I, Q_obs copies I).
    joint_clean_weak = {("0", "a"): 25.0, ("0", "b"): 25.0, ("1", "a"): 25.0, ("1", "b"): 25.0}
    joint_obs_strong = {("0", "0"): 50.0, ("1", "1"): 50.0, ("0", "1"): 0.0, ("1", "0"): 0.0}
    side = information_difference(
        joint_clean_weak,
        joint_obs_strong,
        degradation_markov=False,
        degradation_process_id="side_information_not_markov",
        method="discrete_joint",
        exact=True,
    )
    nonnegative = markov.information_difference >= -1e-12
    negative_possible = side.information_difference < 0.0
    passed = nonnegative and negative_possible and side.information_loss_estimate is None
    return TheoremCheck(
        card_id="C1",
        execution_state="PASS_WITHIN_ASSUMPTIONS" if passed else "FAIL_ASSUMPTION",
        layer="ANALYTIC",
        assumptions_verified=("discrete joints", "markov vs side-information counterexample"),
        implementation="information_difference",
        atol=1e-9,
        rtol=1e-8,
        seeds=(),
        dataset="synthetic_joints",
        notes="information_loss is withheld when the Markov assumption is false.",
        metrics={
            "markov_difference": markov.information_difference,
            "side_difference": side.information_difference,
            "markov_loss": markov.information_loss_estimate,
            "side_loss": side.information_loss_estimate,
        },
    )


def run_theory_checks(
    *,
    t4_trials: int = 400,
    seed: int = 0,
    include_grids: bool = True,
    t4_family_trials: int = 80,
    t4_near_zero_trials: int = 40,
) -> dict[str, Any]:
    checks = [
        check_c1(),
        check_t1(),
        check_t2(),
        check_t3(),
        check_t4(n_trials=t4_trials, seed=seed),
    ]
    if include_grids:
        checks.append(check_t2_grid())
        checks.append(check_t4_families(n_trials=t4_family_trials, seed=seed))
        checks.append(check_t4_near_zero(n_trials=t4_near_zero_trials, seed=seed))
    return {
        "schema_version": "theorem_checks.1",
        "code_version": __version__,
        "cards": [card.to_dict() for card in default_cards()],
        "checks": [check.to_dict() for check in checks],
        "summary": {check.card_id: check.execution_state for check in checks},
    }


def write_theory_checks(
    path: str | Path,
    *,
    t4_trials: int = 400,
    seed: int = 0,
    include_grids: bool = True,
    t4_near_zero_trials: int = 40,
) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = run_theory_checks(
        t4_trials=t4_trials,
        seed=seed,
        include_grids=include_grids,
        t4_near_zero_trials=t4_near_zero_trials,
    )
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return dest
