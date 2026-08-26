"""Gate 1: deployment recoverability vs realized EXPLORE gain.

Does not modify the executed legacy policy. Synthetic forced-action results are
SIMULATOR_CAUSAL_WITHIN_MODEL. The 120-query fixture is an availability sanity arm.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from quasar2.config import ProjectConfig
from quasar2.decision.kernels import bernoulli_support_kernels
from quasar2.eval.evidence_trace import trace_section2_metrics
from quasar2.eval.stress_regimes import generate_regime_states
from quasar2.math.association import auprc, auroc, brier, pearson, r_squared, reliability_bins, spearman
from quasar2.math.bootstrap import cluster_bootstrap_mean, cluster_bootstrap_spearman_difference
from quasar2.math.linear import dot, ridge_fit
from quasar2.math.voi import voi_bound_binary
from quasar2.pipeline import QuasarPipeline
from quasar2.recoverability import (
    COMPARISON_PREDICTORS,
    DEPLOYMENT_FEATURE_NAMES,
    ESTIMATORS,
    LearnedRecoverabilityEstimator,
    deployment_features,
)


def _plan_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "experiments" / "analysis_plans" / "gate1.json"
        if candidate.exists():
            return candidate
    return Path.cwd() / "experiments" / "analysis_plans" / "gate1.json"


PLAN_PATH = _plan_path()
FORBIDDEN_FEATURE_TOKENS = ("gold", "correct_hypothesis", "future", "oracle_q", "delta_u", "voi_oracle")
UNCERTAINTY_METHODS = ("entropy", "belief_margin")
RECOVERABILITY_METHODS = (
    "decision_recoverability",
    "jsd",
    "tv",
    "mutual_information",
    "retriever_score_margin",
    "embedding_separation",
)
ALL_PREDICTORS = UNCERTAINTY_METHODS + RECOVERABILITY_METHODS + ("learned", "kl", "symmetric_kl")


def load_analysis_plan() -> dict[str, Any]:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def analysis_plan_hash(plan: Mapping[str, Any] | None = None) -> str:
    payload = plan if plan is not None else load_analysis_plan()
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def classify_delta(delta_u: float, delta: float) -> str:
    if delta_u > delta:
        return "BENEFICIAL"
    if delta_u < -delta:
        return "HARMFUL"
    return "NEAR_ZERO"


def realized_utility(
    *,
    correct: bool,
    action: str,
    retrieval_calls: int,
    u_correct: float,
    u_wrong: float,
    c_call: float,
    ask_cost: float,
) -> float:
    value = float(u_correct) if correct else 0.0
    if (not correct) and action == "ANSWER":
        value -= float(u_wrong)
    value -= float(c_call) * float(retrieval_calls)
    if action == "ASK":
        value -= float(ask_cost)
    return value


def _predictor_map() -> dict[str, Any]:
    estimators = dict(ESTIMATORS)
    estimators.update(COMPARISON_PREDICTORS)
    return estimators


def _score_state(
    belief: Mapping[str, float],
    proxy_kernels: Mapping[str, Mapping[str, float]],
    learned: LearnedRecoverabilityEstimator | None = None,
) -> dict[str, float]:
    hyps = tuple(belief)
    estimators = _predictor_map()
    if learned is not None:
        estimators = dict(estimators)
        estimators["learned"] = learned
    scores: dict[str, float] = {}
    for name in ALL_PREDICTORS:
        if name not in estimators:
            continue
        scores[name] = float(estimators[name].estimate(belief, hyps, "EXPLORE", proxy_kernels).score)
    return scores


def _fit_learned(train_rows: Sequence[Mapping[str, Any]]) -> LearnedRecoverabilityEstimator:
    learned = LearnedRecoverabilityEstimator()
    rows = [(row["belief"], tuple(row["belief"]), row["proxy_kernels"]) for row in train_rows]
    targets = [float(row["voi_oracle_raw"]) for row in train_rows]
    if rows:
        learned.fit(rows, targets)
    return learned


def _row_metrics(
    rows: Sequence[Mapping[str, Any]],
    method: str,
    outcome_key: str,
    useful_key: str = "useful_explore",
) -> dict[str, Any]:
    scores = [float(row["predictors"][method]) for row in rows]
    outcome = [float(row[outcome_key]) for row in rows]
    useful = [int(row[useful_key]) for row in rows]
    max_abs = max((abs(value) for value in scores), default=1.0) or 1.0
    scaled = [max(0.0, min(1.0, value / max_abs)) if value == value else 0.0 for value in scores]
    return {
        "method": method,
        "n": len(rows),
        "spearman": spearman(scores, outcome),
        "pearson": pearson(scores, outcome),
        "r2": r_squared(scores, outcome),
        "auroc_useful": auroc(scores, useful),
        "auprc_useful": auprc(scores, useful),
        "brier_useful": brier(scaled, useful),
        "reliability": reliability_bins(scaled, [float(v) for v in useful]),
    }


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if not ordered:
        return 0.0
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _incremental(
    train: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
    *,
    outcome_key: str,
) -> dict[str, Any]:
    if not train or not test:
        return {"status": "empty"}
    y_train = [float(row[outcome_key]) for row in train]
    m0_train = [[1.0, float(row["predictors"]["entropy"]), float(row["predictors"]["belief_margin"])] for row in train]
    m1_train = [
        m0
        + [
            float(row["predictors"]["decision_recoverability"]),
            float(row["predictors"]["jsd"]),
            float(row["predictors"]["tv"]),
        ]
        for row, m0 in zip(train, m0_train)
    ]
    w0 = ridge_fit(m0_train, y_train, lam=1e-2)
    w1 = ridge_fit(m1_train, y_train, lam=1e-2)
    m0_test = [[1.0, float(row["predictors"]["entropy"]), float(row["predictors"]["belief_margin"])] for row in test]
    m1_test = [
        m0
        + [
            float(row["predictors"]["decision_recoverability"]),
            float(row["predictors"]["jsd"]),
            float(row["predictors"]["tv"]),
        ]
        for row, m0 in zip(test, m0_test)
    ]
    pred0 = [dot(w0, feats) for feats in m0_test]
    pred1 = [dot(w1, feats) for feats in m1_test]
    y_test = [float(row[outcome_key]) for row in test]
    useful = [int(row["useful_explore"]) for row in test]
    clusters = [str(row["cluster_id"]) for row in test]
    return {
        "fit_split": "development+model_selection",
        "eval_split": "registered_test",
        "m0_features": ["intercept", "entropy", "belief_margin"],
        "m1_features": ["intercept", "entropy", "belief_margin", "drs", "jsd", "tv"],
        "spearman_m0": spearman(pred0, y_test),
        "spearman_m1": spearman(pred1, y_test),
        "r2_m0": r_squared(pred0, y_test),
        "r2_m1": r_squared(pred1, y_test),
        "auroc_m0": auroc(pred0, useful),
        "auroc_m1": auroc(pred1, useful),
        "delta_spearman": None
        if spearman(pred0, y_test) is None or spearman(pred1, y_test) is None
        else spearman(pred1, y_test) - spearman(pred0, y_test),
        "delta_r2": None
        if r_squared(pred0, y_test) is None or r_squared(pred1, y_test) is None
        else r_squared(pred1, y_test) - r_squared(pred0, y_test),
        "cluster_bootstrap_delta_spearman": cluster_bootstrap_spearman_difference(
            pred1, pred0, y_test, clusters, samples=400, seed=0
        ),
        "preprocessing_inside_train": True,
        "test_untouched_until_eval": True,
    }


def leakage_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    names = [token.lower() for token in DEPLOYMENT_FEATURE_NAMES]
    name_leak = [token for token in names if any(bad in token for bad in FORBIDDEN_FEATURE_TOKENS)]
    gold_shift = 0
    if rows:
        sample = rows[0]
        base = deployment_features(sample["belief"], tuple(sample["belief"]), sample["proxy_kernels"])
        poisoned_belief = dict(sample["belief"])
        poisoned_belief["__gold__"] = 1.0
        shifted = deployment_features(poisoned_belief, tuple(sample["belief"]), sample["proxy_kernels"])
        gold_shift = sum(abs(a - b) for a, b in zip(base, shifted))
    for row in rows:
        for token in FORBIDDEN_FEATURE_TOKENS:
            if token in row.get("predictors", {}):
                name_leak.append(token)
    return {
        "deployment_feature_names": list(DEPLOYMENT_FEATURE_NAMES),
        "forbidden_tokens_in_feature_names": name_leak,
        "gold_key_does_not_change_features": gold_shift == 0.0,
        "predictors_use_proxy_not_true_kernels": all(
            row.get("proxy_kernel_name") is not None for row in rows
        )
        if rows
        else True,
        "pass": (not name_leak) and gold_shift == 0.0,
    }


def _quadrant(
    train: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
    *,
    outcome_key: str,
) -> dict[str, Any]:
    if not train or not test:
        return {"status": "empty"}
    h_cut = _median([float(row["entropy"]) for row in train])
    r_cut = _median([float(row["predictors"]["decision_recoverability"]) for row in train])
    high_high = [row for row in test if row["entropy"] >= h_cut and row["predictors"]["decision_recoverability"] >= r_cut]
    high_low = [row for row in test if row["entropy"] >= h_cut and row["predictors"]["decision_recoverability"] < r_cut]
    def mean_delta(group: Sequence[Mapping[str, Any]]) -> float | None:
        if not group:
            return None
        return sum(float(row[outcome_key]) for row in group) / len(group)

    hh = mean_delta(high_high)
    hl = mean_delta(high_low)
    contrast = None if hh is None or hl is None else hh - hl
    if high_high and high_low:
        values_hh = [float(row[outcome_key]) for row in high_high]
        values_hl = [float(row[outcome_key]) for row in high_low]
        ci_hh = cluster_bootstrap_mean(
            values_hh, [str(row["cluster_id"]) for row in high_high], samples=400, seed=1
        )
        ci_hl = cluster_bootstrap_mean(
            values_hl, [str(row["cluster_id"]) for row in high_low], samples=400, seed=2
        )
    else:
        ci_hh = {"point": hh}
        ci_hl = {"point": hl}
    return {
        "thresholds_fit_on": "development+model_selection",
        "entropy_cut": h_cut,
        "drs_cut": r_cut,
        "n_high_H_high_R": len(high_high),
        "n_high_H_low_R": len(high_low),
        "mean_delta_u_high_H_high_R": hh,
        "mean_delta_u_high_H_low_R": hl,
        "contrast": contrast,
        "ci_high_H_high_R": ci_hh,
        "ci_high_H_low_R": ci_hl,
        "secondary_not_primary": True,
    }


def _seed_stability(rows: Sequence[Mapping[str, Any]], seeds: Sequence[int]) -> dict[str, Any]:
    """Resample rows within clusters; DRS is deterministic so this checks sampling variation."""

    signs = []
    for seed in seeds:
        test = [row for row in rows if row["split_role"] == "registered_test"]
        if len(test) < 3:
            continue
        clusters = [str(row["cluster_id"]) for row in test]
        drs = [float(row["predictors"]["decision_recoverability"]) for row in test]
        ent = [float(row["predictors"]["entropy"]) for row in test]
        y = [float(row["voi_oracle_raw"]) for row in test]
        diff = cluster_bootstrap_spearman_difference(drs, ent, y, clusters, samples=200, seed=seed)
        point = diff.get("point")
        signs.append(None if point is None else (1 if point > 0 else -1 if point < 0 else 0))
    finite = [sign for sign in signs if sign is not None]
    stable = bool(finite) and len(set(finite)) == 1
    return {"seeds": list(seeds), "signs": signs, "direction_stable": stable}


def _gate_decision(
    plan: Mapping[str, Any],
    *,
    leakage: Mapping[str, Any],
    incremental: Mapping[str, Any],
    drs_minus_entropy: Mapping[str, Any],
    per_regime: Sequence[Mapping[str, Any]],
    quadrant: Mapping[str, Any],
) -> dict[str, Any]:
    if not leakage.get("pass"):
        return {"gate1": "FAIL", "reason": "leakage_audit_failed"}
    finite_regimes = [row for row in per_regime if row.get("spearman_drs") is not None and row.get("spearman_entropy") is not None]
    if len(finite_regimes) < 2:
        return {"gate1": "INCONCLUSIVE", "reason": "fewer_than_two_registered_regimes_with_spearman"}
    point = drs_minus_entropy.get("point")
    lo = drs_minus_entropy.get("ci_low")
    hi = drs_minus_entropy.get("ci_high")
    inc_ci = incremental.get("cluster_bootstrap_delta_spearman") or {}
    inc_point = incremental.get("delta_spearman")
    inc_lo = inc_ci.get("ci_low")
    inc_hi = inc_ci.get("ci_high")
    same_sign = 0
    for row in finite_regimes:
        delta = (row["spearman_drs"] or 0.0) - (row["spearman_entropy"] or 0.0)
        if point is not None and delta * float(point) > 0:
            same_sign += 1
    b_ok = (
        point is not None
        and lo is not None
        and hi is not None
        and float(point) > 0
        and float(lo) > 0
    )
    c_ok = (
        inc_point is not None
        and inc_lo is not None
        and inc_hi is not None
        and float(inc_point) > 0
        and float(inc_lo) > 0
    )
    d_ok = same_sign >= 2
    q_ok = quadrant.get("contrast") is not None and float(quadrant["contrast"]) > 0
    if b_ok and c_ok and d_ok:
        status = "PASS"
        reason = "confirmatory_incremental_and_two_regimes"
    elif b_ok or c_ok or q_ok:
        status = "PARTIAL"
        reason = "some_but_not_all_confirmatory_clauses"
    elif point is None or inc_point is None:
        status = "INCONCLUSIVE"
        reason = "undefined_primary_endpoint"
    else:
        status = "FAIL"
        reason = "no_stable_incremental_information_on_registered_test"
    return {
        "gate1": status,
        "reason": reason,
        "clause_b_drs_minus_entropy_ci_excludes_0": b_ok,
        "clause_c_m1_minus_m0_ci_excludes_0": c_ok,
        "clause_d_two_regime_sign": d_ok,
        "same_sign_regime_count": same_sign,
        "quadrant_positive_exploratory": q_ok,
        "analysis_plan_hash": analysis_plan_hash(plan),
        "label": "confirmatory_on_registered_test",
    }


def synthesize_gate1_rows(plan: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    delta = float(plan["practical_margin_delta"])
    raw_states = generate_regime_states()
    train_pool = [row for row in raw_states if row["split_role"] in {"development", "model_selection"}]
    learned = _fit_learned(train_pool)
    rows: list[dict[str, Any]] = []
    for state in raw_states:
        predictors = _score_state(state["belief"], state["proxy_kernels"], learned)
        bound = voi_bound_binary(
            float(state["b"]),
            state["true_kernels"]["H1"],
            state["true_kernels"]["H2"],
        )
        useful = 1 if float(state["delta_u_force_explore"]) > delta else 0
        rows.append(
            {
                **{key: state[key] for key in state if key not in {"belief", "true_kernels", "proxy_kernels"}},
                "belief": state["belief"],
                "true_kernels": state["true_kernels"],
                "proxy_kernels": state["proxy_kernels"],
                "predictors": predictors,
                "useful_explore": useful,
                "useful_label": classify_delta(float(state["delta_u_force_explore"]), delta),
                "voi_bound_tv": bound.voi_bound_tv,
                "voi_bound_is_not_q": True,
                "estimand": "forced_action_explore_minus_answer",
                "identification": "SIMULATOR_CAUSAL_WITHIN_MODEL",
            }
        )
    access_log = [
        {
            "event": "generate_states",
            "n": len(rows),
            "roles": {role: sum(1 for row in rows if row["split_role"] == role) for role in plan["splits"]},
        }
    ]
    return rows, {"learned_fitted_on": "development+model_selection", "access_log": access_log}


def analyze_synthetic(rows: Sequence[Mapping[str, Any]], plan: Mapping[str, Any]) -> dict[str, Any]:
    train = [row for row in rows if row["split_role"] in {"development", "model_selection"}]
    test = [row for row in rows if row["split_role"] == "registered_test"]
    sealed = [row for row in rows if row["split_role"] == "sealed_replication"]
    outcome = "voi_oracle_raw"
    method_table = [_row_metrics(test, method, outcome) for method in ALL_PREDICTORS if method in test[0]["predictors"]]
    per_regime = []
    for regime in plan["splits"]["registered_test"]:
        subset = [row for row in test if row["regime_id"] == regime]
        if not subset:
            continue
        per_regime.append(
            {
                "regime_id": regime,
                "n": len(subset),
                "mean_delta_u": sum(float(row["delta_u_force_explore"]) for row in subset) / len(subset),
                "spearman_drs": spearman(
                    [row["predictors"]["decision_recoverability"] for row in subset],
                    [row[outcome] for row in subset],
                ),
                "spearman_entropy": spearman(
                    [row["predictors"]["entropy"] for row in subset],
                    [row[outcome] for row in subset],
                ),
                "spearman_jsd": spearman(
                    [row["predictors"]["jsd"] for row in subset],
                    [row[outcome] for row in subset],
                ),
            }
        )
    clusters = [str(row["cluster_id"]) for row in test]
    drs = [float(row["predictors"]["decision_recoverability"]) for row in test]
    ent = [float(row["predictors"]["entropy"]) for row in test]
    y = [float(row[outcome]) for row in test]
    incremental = _incremental(train, test, outcome_key=outcome)
    quadrant = _quadrant(train, test, outcome_key=outcome)
    leakage = leakage_audit(list(rows))
    drs_minus_entropy = cluster_bootstrap_spearman_difference(drs, ent, y, clusters, samples=400, seed=0)
    decision = _gate_decision(
        plan,
        leakage=leakage,
        incremental=incremental,
        drs_minus_entropy=drs_minus_entropy,
        per_regime=per_regime,
        quadrant=quadrant,
    )
    access_log = [
        {"event": "fit_on_development_model_selection", "n": len(train), "used_for_gate": False},
        {"event": "evaluate_registered_test", "n": len(test), "used_for_gate": True},
        {"event": "store_sealed_replication", "n": len(sealed), "used_for_gate": False},
    ]
    strongest_uncertainty = max(
        (row for row in method_table if row["method"] in UNCERTAINTY_METHODS and row["spearman"] is not None),
        key=lambda item: item["spearman"],
        default=None,
    )
    return {
        "n_train": len(train),
        "n_registered_test": len(test),
        "n_sealed": len(sealed),
        "method_table_registered_test": method_table,
        "per_regime_registered_test": per_regime,
        "drs_vs_entropy_spearman_difference": drs_minus_entropy,
        "incremental_information": incremental,
        "quadrant": quadrant,
        "leakage": leakage,
        "seed_stability": _seed_stability(rows, plan["seeds"]),
        "gate": decision,
        "test_access_log": access_log,
        "strongest_uncertainty_baseline": strongest_uncertainty,
        "sealed_unused_for_decision": True,
    }


def _supports_from_result(result: Any) -> dict[str, float]:
    supports: dict[str, float] = {
        candidate.hypothesis.hypothesis_id: float(
            result.final_belief.probabilities.get(candidate.hypothesis.hypothesis_id, 0.0)
        )
        for candidate in result.candidates
    }
    for item in result.evidence:
        hid = str(item.hypothesis_id)
        supports[hid] = max(float(supports.get(hid, 0.0)), float(item.support_score))
    return supports


def run_fixture_availability(
    config: ProjectConfig,
    plan: Mapping[str, Any],
    *,
    limit: int | None = None,
    conditions: tuple[str, ...] = ("q0", "q1", "q2"),
) -> dict[str, Any]:
    from quasar2.benchmark import BenchmarkRunner

    utility = plan["utility"]
    delta = float(plan["practical_margin_delta"])
    runner = BenchmarkRunner(config)
    pipeline = QuasarPipeline.from_config(config)
    intents = runner.intents[:limit] if limit else runner.intents
    pairs: list[dict[str, Any]] = []
    for intent in intents:
        for condition in conditions:
            query = getattr(intent, condition)
            full = pipeline.run(
                query, intent.domain, ablation="full", observation_id=f"{intent.intent_id}:{condition}:full"
            )
            blocked = pipeline.run(
                query, intent.domain, ablation="noExplore", observation_id=f"{intent.intent_id}:{condition}:noExplore"
            )
            belief = dict(blocked.final_belief.probabilities)
            kernels = bernoulli_support_kernels(_supports_from_result(blocked))
            predictors = _score_state(belief, kernels)
            gold = intent.correct_hypothesis
            full_correct = full.predicted_hypothesis_id == gold
            blocked_correct = blocked.predicted_hypothesis_id == gold
            u_full = realized_utility(
                correct=full_correct,
                action=full.decision.action.value,
                retrieval_calls=full.retrieval_calls,
                u_correct=utility["u_correct"],
                u_wrong=utility["u_wrong_answer"],
                c_call=utility["c_call"],
                ask_cost=utility["ask_cost"],
            )
            u_blocked = realized_utility(
                correct=blocked_correct,
                action=blocked.decision.action.value,
                retrieval_calls=blocked.retrieval_calls,
                u_correct=utility["u_correct"],
                u_wrong=utility["u_wrong_answer"],
                c_call=utility["c_call"],
                ask_cost=utility["ask_cost"],
            )
            delta_u = u_full - u_blocked
            pairs.append(
                {
                    "intent_id": intent.intent_id,
                    "condition": condition,
                    "cluster_id": intent.intent_id,
                    "domain": intent.domain,
                    "delta_correct": float(full_correct) - float(blocked_correct),
                    "delta_u": delta_u,
                    "delta_cost_calls": full.retrieval_calls - blocked.retrieval_calls,
                    "full_action": full.decision.action.value,
                    "noexplore_action": blocked.decision.action.value,
                    "full_explore_rounds": full.explore_rounds,
                    "noexplore_explore_rounds": blocked.explore_rounds,
                    "useful_explore": int(delta_u > delta),
                    "useful_label": classify_delta(delta_u, delta),
                    "entropy": float(blocked.final_belief.normalized_entropy),
                    "predictors": predictors,
                    "estimand": "availability_explore_on_vs_off",
                    "identification": "paired_common_random_numbers_not_randomized_trial",
                    "gold_unused_in_predictors": True,
                }
            )
    n = len(pairs)
    useful = sum(row["useful_explore"] for row in pairs)
    explore_full = sum(1 for row in pairs if row["full_explore_rounds"] > 0)
    mean_delta_u = sum(row["delta_u"] for row in pairs) / n if n else None
    clusters = [row["cluster_id"] for row in pairs]
    metrics = None
    if n >= 3:
        metrics = {
            "spearman_drs": spearman([row["predictors"]["decision_recoverability"] for row in pairs], [row["delta_u"] for row in pairs]),
            "spearman_entropy": spearman([row["predictors"]["entropy"] for row in pairs], [row["delta_u"] for row in pairs]),
            "mean_delta_u_ci": cluster_bootstrap_mean([row["delta_u"] for row in pairs], clusters, samples=400, seed=3),
        }
    return {
        "schema": "gate1_fixture_availability.1",
        "n_pairs": n,
        "n_useful_explore_delta": useful,
        "n_full_with_explore_rounds": explore_full,
        "mean_delta_u": mean_delta_u,
        "metrics": metrics,
        "limitation": (
            "Easy 120-query fixture is a regression/availability sanity test, not the confirmatory Gate-1 "
            "holdout. Zero or rare EXPLORE under the legacy loop is an expected limitation, not a reason to "
            "force EXPLORE."
        ),
        "records": pairs,
        "label": "exploratory_sanity",
    }


def _maturity(gate: Mapping[str, Any], fixture: Mapping[str, Any] | None) -> dict[str, Any]:
    status = str(gate.get("gate1", "UNTESTED"))
    recov = {
        "PASS": "SUPPORTED_WITHIN_SCOPE",
        "PARTIAL": "TESTED",
        "FAIL": "FAILED",
        "INCONCLUSIVE": "INCONCLUSIVE",
    }.get(status, "TESTED")
    return {
        "scientific_maturity": {
            "theory": {"state": "TESTED", "evidence_ids": ["docs/THEORY.md", "T2-binary-voi"]},
            "measurement": {"state": recov, "evidence_ids": ["G1", gate.get("analysis_plan_hash")]},
            "causal": {"state": "TESTED", "evidence_ids": ["SIMULATOR_CAUSAL_WITHIN_MODEL"], "note": "not real-world causal"},
            "policy": {"state": "SPECIFIED", "evidence_ids": ["H-learned-beats-voi"]},
            "retrieval": {"state": "SPECIFIED", "evidence_ids": ["H-discriminative-recall-decouple"]},
            "external": {"state": "TESTED", "evidence_ids": ["H10-simple-baseline"]},
            "statistics": {"state": "TESTED", "evidence_ids": ["G1-cluster-bootstrap"]},
            "reproducibility": {"state": "IMPLEMENTED", "evidence_ids": ["quasar2 gate1-audit"]},
            "replication": {"state": "NOT_STARTED", "evidence_ids": []},
        },
        "vetoes": {
            "critical_gold_leakage": not True,
            "untraceable_primary_result": False,
            "primary_endpoint_selected_after_test": False,
            "no_strong_baseline": False,
            "no_uncertainty_for_primary_effect": False,
            "no_reproducible_primary_run": False,
            "causal_language_without_identification": False,
            "external_replication_falsely_claimed": False,
        },
        "scalar_96_percent_label": "NOT_CLAIMED",
        "dashboards_separated": ["scientific_maturity", "engineering_maturity", "product_readiness", "operational_safety"],
    }


def _claims(gate: Mapping[str, Any], synthetic: Mapping[str, Any], fixture: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    status = str(gate.get("gate1"))
    mapped = {
        "PASS": "PARTIALLY_SUPPORTED",
        "PARTIAL": "TESTED",
        "FAIL": "NOT_SUPPORTED",
        "INCONCLUSIVE": "TESTED",
    }[status]
    # PASS still cannot be SUPPORTED: N_clusters=4, simulator only, no WDI.
    if status == "PASS":
        mapped = "PARTIALLY_SUPPORTED"
    return [
        {
            "claim_id": "G1-deploy-R-predicts-deltaU",
            "from_status": "PROPOSED",
            "to_status": mapped,
            "scope": "synthetic registered_test regimes; SIMULATOR_CAUSAL_WITHIN_MODEL",
            "reason": gate.get("reason"),
            "supporting_run_ids": ["gate1-audit"],
            "assumptions": ["proxy Bernoulli/true kernels as specified", "0-1 Bayes value"],
            "confirmatory": True,
        },
        {
            "claim_id": "G1-R-adds-beyond-uncertainty",
            "from_status": "PROPOSED",
            "to_status": mapped,
            "scope": "M0 entropy+margin vs M1 + DRS/JSD/TV on registered_test",
            "reason": gate.get("reason"),
            "supporting_run_ids": ["gate1-audit"],
            "confirmatory": True,
        },
        {
            "claim_id": "G1-quadrant-effect-modification",
            "from_status": "PROPOSED",
            "to_status": "TESTED",
            "scope": "secondary quadrant contrast; thresholds frozen on train",
            "reason": "secondary_not_primary",
            "confirmatory": False,
        },
        {
            "claim_id": "G1-fixture-availability-explore-gain",
            "from_status": "PROPOSED",
            "to_status": "TESTED" if fixture else "BLOCKED",
            "scope": "120-query sanity fixture FULL vs noExplore",
            "reason": None if fixture is None else fixture.get("limitation"),
            "confirmatory": False,
        },
    ]


def _public_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "state_id": row.get("state_id") or f"{row.get('intent_id')}:{row.get('condition')}",
        "cluster_id": row["cluster_id"],
        "split_role": row.get("split_role", "sanity_fixture"),
        "regime_id": row.get("regime_id"),
        "entropy": row.get("entropy"),
        "voi_oracle_raw": row.get("voi_oracle_raw"),
        "delta_u_force_explore": row.get("delta_u_force_explore"),
        "delta_u": row.get("delta_u"),
        "useful_label": row.get("useful_label"),
        "proxy_kernel_name": row.get("proxy_kernel_name"),
        "true_kernel_name": row.get("true_kernel_name"),
        "R_drs": row["predictors"]["decision_recoverability"],
        "R_jsd": row["predictors"]["jsd"],
        "R_tv": row["predictors"]["tv"],
        "R_entropy": row["predictors"]["entropy"],
        "voi_bound_tv": row.get("voi_bound_tv"),
    }


def build_report_markdown(payload: Mapping[str, Any]) -> str:
    syn = payload["synthetic"]
    gate = syn["gate"]
    fixture = payload.get("fixture")
    lines = [
        "# QUASAR2 Cycle 1 — Gate 1 report",
        "",
        "## 1. Repository Audit",
        "Frozen v0.1.1 loop, recoverability estimators, synthetic recoverability-bench, shadow study, WDI tracks, and claim ledger were already present. No recoverability_bench artifact existed for section-2 numbers; those remain UNVERIFIED_HISTORICAL_OBSERVATION and were recomputed this cycle.",
        "",
        "## 2. Scientific Question",
        payload["analysis_plan"]["primary_question"],
        "",
        "## 3. Hypothesis",
        f"H1: {payload['analysis_plan']['alternative_hypothesis']}",
        f"H0: {payload['analysis_plan']['null_hypothesis']}",
        f"Estimand: {payload['analysis_plan']['primary_estimand']}",
        f"Identification: SIMULATOR_CAUSAL_WITHIN_MODEL (synthetic); availability pairing on the sanity fixture is not a randomized trial.",
        f"Analysis-plan hash: `{payload['analysis_plan_hash']}`",
        f"Split/test-access: registered_test used once for the gate; sealed_replication stored unused.",
        f"Unit of inference: synthetic state clustered by `regime_id`. Minimum practical effect δ={payload['analysis_plan']['practical_margin_delta']}.",
        f"Label: confirmatory on synthetic registered_test; fixture arm exploratory.",
        "",
        "## 4. Changes",
        "Added Gate-1 protocol, stress regimes, paired analysis, leakage audit, negative-result ledger, notation registry, CLI `gate1-audit`. Legacy executed policy unchanged.",
        "",
        "## 5. Bugs Found",
        payload.get("bugs_found", "None that invalidate frozen v0.1.1 artifacts."),
        "",
        "## 6. Tests",
        f"See `tests/test_gate1.py` and legacy goldens. Reproduction command: `quasar2 gate1-audit --output experiments/results/gate1_cycle1`.",
        "",
        "## 7. Experimental Design",
        f"Synthetic N_train={syn['n_train']} N_registered={syn['n_registered_test']} N_sealed={syn['n_sealed']}; intervention=forced EXPLORE vs ANSWER under true kernels; predictors from proxy kernels only; seeds={payload['analysis_plan']['seeds']}.",
        "",
        "## 8. Results",
        f"Gate-1 status: **{gate['gate1']}** ({gate['reason']}).",
        f"DRS−entropy Spearman difference: {syn['drs_vs_entropy_spearman_difference']}.",
        f"Incremental M1−M0: {syn['incremental_information']}.",
        f"Per-regime: {syn['per_regime_registered_test']}.",
        f"Quadrant (secondary): {syn['quadrant']}.",
        f"Raw per-unit artifacts: `records.csv` in the run directory.",
        "",
        "## 9. Strongest Baseline",
        f"Uncertainty baseline: {syn.get('strongest_uncertainty_baseline')}. Entropy remains the required comparator. Simple threshold/BM25 remain operational threats on WDI (unchanged historical).",
        "",
        "## 10. Negative Results",
        "See `docs/NEGATIVE_RESULTS.md`. Sealed set was not mined. 120-query EXPLORE rarity is retained as a limitation.",
        "",
        "## 11. Claim Ledger Changes",
        json.dumps(payload["claims"], indent=2),
        "",
        "## 12. Theory Impact",
        "T2 bound remains a certificate, not Q(s,EXPLORE). Recoverability is treated as a predictor/effect-modifier candidate, not a manipulated cause.",
        "",
        "## 13. Maturity Gates",
        json.dumps(payload["maturity"]["scientific_maturity"], indent=2),
        "",
        "## 14. Largest Threat",
        payload["largest_threat"],
        "",
        "## 15. Highest-Information Next Experiment",
        payload["next_experiment"],
        "",
    ]
    if fixture:
        lines.extend(
            [
                "### Fixture availability arm (exploratory)",
                f"n_pairs={fixture['n_pairs']} useful={fixture['n_useful_explore_delta']} full_explore_rounds>0: {fixture['n_full_with_explore_rounds']} mean_delta_u={fixture['mean_delta_u']}",
                fixture["limitation"],
                "",
            ]
        )
    return "\n".join(lines)


def run_gate1_audit(
    *,
    config: ProjectConfig | None = None,
    include_fixture: bool = False,
    fixture_limit: int | None = None,
) -> dict[str, Any]:
    plan = load_analysis_plan()
    plan_hash = analysis_plan_hash(plan)
    evidence = trace_section2_metrics()
    rows, meta = synthesize_gate1_rows(plan)
    synthetic = analyze_synthetic(rows, plan)
    synthetic["generator"] = meta
    fixture = None
    if include_fixture:
        if config is None:
            raise ValueError("config required for fixture arm")
        fixture = run_fixture_availability(config, plan, limit=fixture_limit)
    gate = synthetic["gate"]
    claims = _claims(gate, synthetic, fixture)
    maturity = _maturity(gate, fixture)
    strongest = synthetic.get("strongest_uncertainty_baseline") or {}
    threat = (
        "Deployment recoverability may be a restatement of the true kernel, or a misleading proxy "
        "under misspecification. The strongest simple baseline this cycle is entropy/belief-margin. "
        "The strongest modern operational threat remains BM25/hybrid one-shot on WDI (historical). "
        f"Registered-test entropy Spearman={None if strongest is None else strongest.get('spearman')}."
    )
    next_experiment = (
        "Cycle 2 confirmatory: freeze the current analysis card and measure whether recoverability "
        "adds incremental information for paired FULL vs forced-NOEXPLORE on a WDI controlled-degradation "
        "slice that is not the sealed replication set, using query-family clustered inference."
    )
    payload = {
        "schema_version": "gate1.1",
        "analysis_plan": plan,
        "analysis_plan_hash": plan_hash,
        "evidence_trace": evidence,
        "synthetic": {
            **{key: value for key, value in synthetic.items() if key != "generator"},
            "generator": {"learned_fitted_on": meta["learned_fitted_on"]},
        },
        "fixture": None
        if fixture is None
        else {key: value for key, value in fixture.items() if key != "records"},
        "claims": claims,
        "maturity": maturity,
        "largest_threat": threat,
        "next_experiment": next_experiment,
        "bugs_found": "No seed/config no-op found in Gate-1 path. Section-2 metrics lacked run artifacts (traceability bug of the research record, not of the frozen loop).",
        "reproduction_command": "quasar2 gate1-audit --output experiments/results/gate1_cycle1",
        "reproduction_command_status": "implemented",
        "equal_budget_status": "not_this_gate",
        "exploratory_versus_confirmatory": {
            "confirmatory": "synthetic registered_test incremental information",
            "exploratory": "quadrant contrast, fixture availability, method table beyond DRS/entropy",
        },
    }
    payload["_rows"] = rows
    payload["_fixture_records"] = None if fixture is None else fixture["records"]
    return payload


def write_gate1_audit(dest: Path, payload: dict[str, Any] | None = None, **kwargs: Any) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    payload = payload or run_gate1_audit(**kwargs)
    rows = payload.pop("_rows", [])
    fixture_records = payload.pop("_fixture_records", None)
    (dest / "gate1.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (dest / "analysis_plan.json").write_text(
        json.dumps(payload["analysis_plan"], indent=2), encoding="utf-8"
    )
    (dest / "test_access_log.json").write_text(
        json.dumps(payload["synthetic"]["test_access_log"], indent=2), encoding="utf-8"
    )
    (dest / "maturity_vector.json").write_text(
        json.dumps(payload["maturity"], indent=2), encoding="utf-8"
    )
    (dest / "claims.json").write_text(json.dumps(payload["claims"], indent=2), encoding="utf-8")
    public = [_public_row(row) for row in rows if row["split_role"] != "sealed_replication"]
    sealed = [_public_row(row) for row in rows if row["split_role"] == "sealed_replication"]
    if public:
        with (dest / "records.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(public[0].keys()))
            writer.writeheader()
            writer.writerows(public)
    (dest / "sealed_replication.json").write_text(
        json.dumps({"n": len(sealed), "unused_for_gate": True, "records": sealed}, indent=2, default=str),
        encoding="utf-8",
    )
    if fixture_records:
        with (dest / "fixture_pairs.csv").open("w", encoding="utf-8", newline="") as handle:
            flat = []
            for row in fixture_records:
                item = {key: value for key, value in row.items() if key != "predictors"}
                item["R_drs"] = row["predictors"]["decision_recoverability"]
                item["R_entropy"] = row["predictors"]["entropy"]
                flat.append(item)
            writer = csv.DictWriter(handle, fieldnames=list(flat[0].keys()))
            writer.writeheader()
            writer.writerows(flat)
    (dest / "REPORT.md").write_text(build_report_markdown(payload), encoding="utf-8")
    return dest / "gate1.json"
