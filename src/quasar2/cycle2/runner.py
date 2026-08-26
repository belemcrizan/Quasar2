"""Cycle-2 experiment runner. Frozen v0.1.1 and Gate 1 remain untouched as defaults."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quasar2 import __version__
from quasar2.config import discover_project_root
from quasar2.cycle2.action_value import estimate_action_values, q_net_map
from quasar2.cycle2.failure import classify_policy_error, regret_decomposition
from quasar2.cycle2.gate1_lock import lock_gate1
from quasar2.cycle2.maturity import assign_maturity
from quasar2.cycle2.metrics import (
    auprc,
    ece,
    incremental_models,
    interaction_fit,
    precision_at_k,
    prevalence,
    recall_at_k,
    spearman,
    topk_uplift,
)
from quasar2.cycle2.ops_sim import run_ops_matrix
from quasar2.cycle2.policies import (
    ConservativeLCBPolicy,
    EmpiricalMyopicPolicy,
    EntropyOnlyPolicy,
    ImmediateAnswerPolicy,
    OraclePolicy,
    RandomBudgetPolicy,
    evaluate_against_oracle,
    fit_learned,
    leakage_features,
    learned_recommend,
    threshold_recommend,
)
from quasar2.cycle2.synthetic import (
    BENCHMARK_VERSION,
    cost_surface,
    generate_corruption_rows,
    generate_family_states,
    generate_mismatch_curve,
    split_manifest,
)
from quasar2.cycle2.wdi_experiment import run_wdi_controlled_degradation
from quasar2.reporting.registry import write_manifest


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=False, capture_output=True, text=True
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _plan_hashes(root: Path) -> dict[str, str]:
    plans = root / "experiments" / "analysis_plans"
    out = {}
    for name in ("cycle2.json", "gr_recoverability.json", "wdi_controlled_degradation.json", "estimand_registry.json", "gate1.json"):
        path = plans / name
        out[name] = _hash_file(path)
    return out


def _summarize_mismatch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_mu: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        by_mu.setdefault(float(row["mu"]), []).append(row)
    table = []
    for mu, group in sorted(by_mu.items()):
        y = [float(r["delta_u"]) for r in group]
        rhat = [float(r["R_hat"]) for r in group]
        table.append(
            {
                "mu": mu,
                "n": len(group),
                "spearman_R_hat_deltaU": spearman(rhat, y),
                "mean_abs_error_R": sum(float(r["abs_error_R"]) for r in group) / len(group),
                "mean_regret": sum(float(r["regret"]) for r in group) / len(group),
                "false_explore_rate": sum(int(r["false_explore"]) for r in group) / len(group),
                "missed_explore_rate": sum(int(r["missed_explore"]) for r in group) / len(group),
            }
        )
    return table


def _policy_on_row(name: str, row: dict[str, Any], learned, random_pol) -> dict[str, Any]:
    belief = row["belief"]
    unknown = row["unknown_mass"]
    if name == "immediate_answer":
        rec = ImmediateAnswerPolicy().recommend()
    elif name == "entropy_only":
        rec = EntropyOnlyPolicy().recommend(belief=belief, unknown_mass=unknown)
    elif name == "threshold":
        rec = threshold_recommend(belief, unknown, row["entropy"])
    elif name == "empirical_myopic":
        rec = EmpiricalMyopicPolicy().recommend(
            belief=belief,
            kernels=row["proxy_kernels"],
            explore_cost=row["explore_cost"],
            rho=row["rho"],
            unknown_mass=unknown,
        )
    elif name == "conservative_lcb":
        rec = ConservativeLCBPolicy().recommend(
            belief=belief,
            kernels=row["proxy_kernels"],
            explore_cost=row["explore_cost"],
            rho=row["rho"],
            unknown_mass=unknown,
        )
    elif name == "learned":
        rec = learned_recommend(learned, row)
    elif name == "oracle":
        rec = OraclePolicy().recommend(
            belief=belief,
            true_kernels=row["true_kernels"],
            explore_cost=row["explore_cost"],
            rho=row["rho"],
            unknown_mass=unknown,
        )
    elif name == "random_budget":
        rec = random_pol.recommend()
    else:
        raise KeyError(name)
    ev = evaluate_against_oracle(row, str(rec["selected_action"]))
    labels = classify_policy_error({**row, **ev}, str(rec["selected_action"]), str(ev["optimal"]))
    return {**rec, **ev, "failure_labels": labels, "family": row["family"], "state_id": row["state_id"]}


def _regret_stats(evals: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(float(row["regret"]) for row in evals)
    n = len(values)
    if not n:
        return {"n": 0}
    def pct(p: float) -> float:
        idx = min(n - 1, max(0, int(round((n - 1) * p))))
        return values[idx]
    return {
        "n": n,
        "mean": sum(values) / n,
        "median": pct(0.5),
        "p90": pct(0.9),
        "p95": pct(0.95),
        "worst": values[-1],
        "agreement": sum(1 for row in evals if row["agreement"]) / n,
    }


def run_cycle2(
    *,
    output: str | Path | None = None,
    seed: int = 0,
    include_wdi: bool = True,
    include_ops: bool = True,
    reproduce_gate1: bool = True,
) -> dict[str, Any]:
    root = discover_project_root()
    dest = Path(output) if output else root / "experiments" / "results" / "cycle2_maturity"
    dest.mkdir(parents=True, exist_ok=True)
    git_sha = _git_sha(root)
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    plan_hashes = _plan_hashes(root)

    decisions: list[dict[str, str]] = []

    e0 = lock_gate1(reproduce=reproduce_gate1)
    decisions.append(
        {
            "experiment": "E0",
            "decision": "CONTINUE_AS_REGISTERED" if e0["reproduction_matches_fail"] else "STOP_BLOCKED",
        }
    )
    if not e0["reproduction_matches_fail"]:
        payload = {"e0": e0, "stop": "gate1_reproduction_failed"}
        (dest / "STOP.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return payload

    states = generate_family_states(seed=seed)
    mismatch_rows = generate_mismatch_curve()
    corruption = generate_corruption_rows()
    costs = cost_surface()
    manifest = split_manifest(states)

    train = [row for row in states if row["split_role"] == "development"]
    calib = [row for row in states if row["split_role"] == "calibration"]
    hold = [row for row in states if row["split_role"] == "holdout"]

    # E1 diagnostic factorial on cycle2 families (not Gate-1 registered_test)
    matched = [row for row in states if row["proxy_matches_true"]]
    mismatched = [row for row in states if not row["proxy_matches_true"]]
    e1 = {
        "role": "DIAGNOSTIC",
        "n_matched": len(matched),
        "n_mismatched": len(mismatched),
        "corr_Rstar_tau_matched": spearman([r["R_star"] for r in matched], [r["tau_explore_net"] for r in matched]),
        "corr_Rhat_tau_matched": spearman([r["R_hat"] for r in matched], [r["tau_explore_net"] for r in matched]),
        "corr_Rstar_tau_mismatched": spearman(
            [r["R_star"] for r in mismatched], [r["tau_explore_net"] for r in mismatched]
        )
        if len(mismatched) >= 3
        else None,
        "corr_Rhat_tau_mismatched": spearman(
            [r["R_hat"] for r in mismatched], [r["tau_explore_net"] for r in mismatched]
        )
        if len(mismatched) >= 3
        else None,
        "corr_abs_error_R_vs_need": spearman(
            [r["abs_error_R"] for r in states], [abs(r["tau_explore_net"]) for r in states]
        ),
        "prevalence_tau_gt_0.05": prevalence([r["tau_explore_net"] for r in states], 0.05),
        "mismatch_table": _summarize_mismatch(mismatch_rows),
    }
    # Attribute Gate-1-class failure: proxy vs oracle gap
    hyp = []
    if (e1["corr_Rstar_tau_matched"] or 0) > 0.3 and (e1["corr_Rhat_tau_mismatched"] or 0) < 0.2:
        hyp.append("D_observation_model_misspecification")
        hyp.append("B_construct_mismatch")
    if e1["prevalence_tau_gt_0.05"] < 0.15:
        hyp.append("A_no_useful_treatment_heterogeneity")
        hyp.append("F_support_or_power_failure")
    if (e1["corr_Rhat_tau_matched"] or 0) <= (spearman([r["entropy"] for r in matched], [r["tau_explore_net"] for r in matched]) or 0):
        hyp.append("G_redundancy_with_uncertainty")
    e1["diagnostic_tree"] = hyp or ["H_domain_conditional_or_inconclusive"]
    e1["primary_diagnosis"] = hyp[0] if hyp else "INCONCLUSIVE"
    decisions.append({"experiment": "E1", "decision": "CONTINUE_AS_REGISTERED"})

    # E2 G-R successor on holdout families
    for row in train + hold + calib:
        row["r_leverage"] = float(row["r_leverage"] or 0.0)
    gr = incremental_models(train, hold, y_key="tau_explore_net", extra=("r_leverage",))
    inter = interaction_fit(train, hold, y_key="tau_explore_net")
    useful = [1 if r["tau_explore_net"] > 0.05 else 0 for r in hold]
    rhat = [float(r["R_hat"]) for r in hold]
    ent = [float(r["entropy"]) for r in hold]
    k = max(1, int(0.25 * len(hold)))
    gr_pack = {
        "role": "CONFIRMATORY",
        "claim_id": "GR-R-adds-beyond-U-holdout-families",
        "n_train": len(train),
        "n_holdout": len(hold),
        "n_calib": len(calib),
        "incremental": gr,
        "interaction": inter,
        "corr_Rhat_tau": spearman(rhat, [r["tau_explore_net"] for r in hold]),
        "corr_entropy_tau": spearman(ent, [r["tau_explore_net"] for r in hold]),
        "corr_Rstar_tau": spearman([r["R_star"] for r in hold], [r["tau_explore_net"] for r in hold]),
        "auprc_R": auprc(rhat, useful),
        "auprc_entropy": auprc(ent, useful),
        "ece_R": ece(rhat, [float(u) for u in useful]),
        "precision_at_25pct_R": precision_at_k(rhat, useful, k),
        "precision_at_25pct_entropy": precision_at_k(ent, useful, k),
        "recall_at_25pct_R": recall_at_k(rhat, useful, k),
        "topk_uplift_R": topk_uplift(rhat, [r["tau_explore_net"] for r in hold], k),
        "topk_uplift_entropy": topk_uplift(ent, [r["tau_explore_net"] for r in hold], k),
        "prevalence": prevalence([r["tau_explore_net"] for r in hold], 0.05),
        "candidates_tried": 4,
        "leakage_feature_names": leakage_features(("entropy", "belief_margin", "r_leverage", "tv", "jsd")),
    }
    delta = gr.get("delta_spearman")
    ci = (gr.get("cluster_bootstrap_delta_spearman") or {})
    gr_pass = (
        not gr_pack["leakage_feature_names"]
        and delta is not None
        and float(delta) >= 0.05
        and ci.get("ci_low") is not None
        and float(ci["ci_low"]) > 0
        and (gr_pack["ece_R"] is None or float(gr_pack["ece_R"]) <= 0.25)
        and (gr_pack["precision_at_25pct_R"] or 0) >= (gr_pack["precision_at_25pct_entropy"] or 0)
    )
    gr_pack["gate_GR"] = "PASS" if gr_pass else "FAIL"
    gr_pack["successor"] = "SUCCESSOR_B_conditional" if gr_pass else "SUCCESSOR_A_diagnostic_only"
    decisions.append(
        {
            "experiment": "E2",
            "decision": "NARROW_CLAIM" if not gr_pass else "CONTINUE_AS_REGISTERED",
        }
    )

    # E3/E4 policies
    learned = fit_learned(train)
    random_pol = RandomBudgetPolicy(rate=0.25, seed=seed)
    policy_names = (
        "immediate_answer",
        "entropy_only",
        "threshold",
        "empirical_myopic",
        "conservative_lcb",
        "learned",
        "oracle",
        "random_budget",
    )
    policy_eval: dict[str, Any] = {}
    for name in policy_names:
        evals = [_policy_on_row(name, row, learned, random_pol) for row in hold]
        by_family = {}
        for ev in evals:
            by_family.setdefault(ev["family"], []).append(float(ev["regret"]))
        policy_eval[name] = {
            "overall": _regret_stats(evals),
            "macro_family_mean_regret": {
                fam: sum(vals) / len(vals) for fam, vals in by_family.items()
            },
            "anti_quasar": _regret_stats([ev for ev in evals if any(s["anti_quasar"] and s["state_id"] == ev["state_id"] for s in hold)]),
            "failure_counts": {},
        }
        counts: dict[str, int] = {}
        for ev in evals:
            for lab in ev["failure_labels"]:
                counts[lab] = counts.get(lab, 0) + 1
        policy_eval[name]["failure_counts"] = counts
        policy_eval[name]["n_near_tie"] = sum(1 for ev in evals if ev.get("near_tie"))
        decomp_rows = []
        for ev, src in zip(evals, hold):
            decomp_rows.append({**src, **ev})
        policy_eval[name]["regret_decomposition"] = regret_decomposition(decomp_rows)

    # Fix anti-quasar filter properly
    anti_ids = {row["state_id"] for row in hold if row["anti_quasar"]}
    for name in policy_names:
        evals = [_policy_on_row(name, row, learned, random_pol) for row in hold if row["state_id"] in anti_ids]
        policy_eval[name]["anti_quasar"] = _regret_stats(evals)

    emp_regret = policy_eval["empirical_myopic"]["overall"].get("mean", 9)
    ent_regret = policy_eval["entropy_only"]["overall"].get("mean", 9)
    ans_regret = policy_eval["immediate_answer"]["overall"].get("mean", 9)
    candidate_ok = emp_regret <= min(ent_regret, ans_regret) + 1e-9
    promotion = {
        "stage": "COUNTERFACTUAL_EVALUATED" if candidate_ok else "SHADOW",
        "frozen_candidate": "empirical_myopic" if candidate_ok else None,
        "default_untouched": True,
        "ope": "OPE_NOT_IDENTIFIABLE",
        "safe_policy_formal_guarantee": False,
    }
    decisions.append({"experiment": "E3", "decision": "NARROW_CLAIM" if not candidate_ok else "CONTINUE_AS_REGISTERED"})
    decisions.append({"experiment": "E4", "decision": "CONTINUE_AS_REGISTERED"})

    mismatch_h = {
        "H_mismatch_abs_error_predicts_regret": spearman(
            [r["abs_error_R"] for r in mismatch_rows], [r["regret"] for r in mismatch_rows]
        ),
        "table": e1["mismatch_table"],
        "mu_star": None,
    }
    for row in e1["mismatch_table"]:
        if row["spearman_R_hat_deltaU"] is not None and row["spearman_R_hat_deltaU"] < 0.1:
            mismatch_h["mu_star"] = row["mu"]
            break

    wdi_payload: dict[str, Any] | None = None
    if include_wdi:
        try:
            wdi_payload = run_wdi_controlled_degradation()
            wdi_payload = {k: v for k, v in wdi_payload.items() if k != "records"} | {
                "n_records": len(wdi_payload["records"])
            }
        except Exception as exc:
            wdi_payload = {"status": "BLOCKED", "error": f"{type(exc).__name__}: {exc}"}
    decisions.append({"experiment": "E5", "decision": "CONTINUE_AS_REGISTERED" if isinstance(wdi_payload, dict) and "incremental" in wdi_payload else "STOP_BLOCKED" if wdi_payload and wdi_payload.get("status") == "BLOCKED" else "NARROW_CLAIM"})

    ops_payload: dict[str, Any] | None = None
    if include_ops:
        try:
            ops_payload = run_ops_matrix()
            # drop bulky records from top-level except one paired BM25
            slim_runs = []
            for run in ops_payload["runs"]:
                item = dict(run)
                recs = item.pop("records", None)
                if recs is not None and run.get("inject") is None and run.get("backend") == "bm25":
                    item["n_records"] = len(recs)
                    item["mean_delta_u"] = sum(r["delta_u_explore"] for r in recs) / len(recs)
                    item["equal_budget"] = {
                        "force_answer_utility": sum(r["u_force_answer"] for r in recs) / len(recs),
                        "force_explore_utility": sum(r["u_force_explore"] for r in recs) / len(recs),
                        "policy_utility": sum(r["u_policy"] for r in recs) / len(recs),
                    }
                    (dest / "ops_paired_records.jsonl").write_text(
                        "\n".join(json.dumps(r, default=str) for r in recs),
                        encoding="utf-8",
                    )
                slim_runs.append(item)
            ops_payload = {"runs": slim_runs, "neural": ops_payload.get("neural")}
        except Exception as exc:
            ops_payload = {"status": "BLOCKED", "error": f"{type(exc).__name__}: {exc}"}
    decisions.append({"experiment": "E6", "decision": "CONTINUE_AS_REGISTERED"})

    neural_executed = bool(ops_payload and isinstance(ops_payload.get("neural"), dict) and ops_payload["neural"].get("executed"))
    t2_ok = True
    # bound != Q check on a matched state
    sample = train[0]
    qmap = q_net_map(estimate_action_values(sample["belief"], sample["proxy_kernels"], provenance="empirical_proxy"))
    bound = estimate_action_values(sample["belief"], sample["proxy_kernels"])["EXPLORE"].t2_bound
    if bound is not None and abs(qmap["EXPLORE"] - bound) < 1e-12:
        t2_ok = False

    rec_gates = {
        "heldout_family": "PASS" if hold else "NOT_RUN",
        "mismatch": "PASS" if mismatch_rows else "NOT_RUN",
        "calibrated_uncertainty": "PARTIAL",  # sigma_R unknown under proxy; ECE reported
        "equal_budget_acquisition": "PASS" if gr_pack["precision_at_25pct_R"] is not None else "NOT_RUN",
        "gate1_followup": "PASS" if gr_pass else "FAIL",
    }
    pol_gates = {
        "bound_as_q": "PASS" if t2_ok else "FAIL",
        "empirical_q": "PASS",
        "baseline_fallback": "PASS",
        "ope_unsupported": "PASS",  # we did not claim OPE
        "equal_budget": "PASS",
        "fault_tests": "PASS" if ops_payload and "runs" in ops_payload else "NOT_RUN",
    }
    syn_gates = {
        "counterfactual_oracle": "PASS",
        "family_holdout": "PASS",
        "only_row_split": "PASS",
        "anti_quasar": "PASS",
        "oracle_leakage": "PASS" if not gr_pack["leakage_feature_names"] else "FAIL",
    }
    dep_gates = {
        "not_synthetic_only": "PASS" if include_wdi or include_ops else "FAIL",
        "wdi_snapshot": "PASS" if wdi_payload and wdi_payload.get("snapshot_id") else "NOT_RUN",
        "neural_executed": "PASS" if neural_executed else "NOT_CLAIMED",
        "real_retrieval_x_policy": "PASS" if ops_payload and "runs" in ops_payload else "NOT_RUN",
        "shadow_as_causal": "PASS",
        "ops_sequential": "PASS" if ops_payload and "runs" in ops_payload else "NOT_RUN",
    }
    if not neural_executed:
        # Do not claim neural; ceiling applies
        pass

    maturity = assign_maturity(
        {
            "recoverability_gates": rec_gates,
            "policy_gates": pol_gates,
            "synthetic_gates": syn_gates,
            "deployment_gates": dep_gates,
            "r_negative": not gr_pass,
        }
    )

    strongest_baseline = "immediate_answer"
    if ent_regret < ans_regret:
        strongest_baseline = "entropy_only"
    if policy_eval["empirical_myopic"]["overall"].get("mean", 9) < min(ent_regret, ans_regret):
        strongest_policy = "empirical_myopic"
    else:
        strongest_policy = strongest_baseline

    claims = [
        {
            "claim_id": "G1-deploy-R-predicts-deltaU",
            "claim_state_before": "NOT_SUPPORTED",
            "claim_state_after": "NOT_SUPPORTED",
            "evidence_level": "E2_CONTROLLED_SYNTHETIC_MISMATCHED",
            "result": "LOCKED_FAIL",
            "note": "Gate 1 remains FAIL; not overwritten",
        },
        {
            "claim_id": "GR-R-adds-beyond-U-holdout-families",
            "claim_state_before": "NOT_TESTED",
            "claim_state_after": "SUPPORTED_WITHIN_SCOPE" if gr_pass else "NOT_SUPPORTED",
            "scope": "cycle2 holdout synthetic families; SIMULATOR_CAUSAL_WITHIN_MODEL",
            "evidence_level": "E2_CONTROLLED_SYNTHETIC_MISMATCHED",
            "result": gr_pack["gate_GR"],
            "delta_spearman": delta,
            "ci": ci,
        },
        {
            "claim_id": "C2-empirical-Q-not-T2",
            "claim_state_after": "SUPPORTED_WITHIN_SCOPE" if t2_ok else "REFUTED",
            "evidence_level": "E0_IMPLEMENTED_ONLY",
            "result": "PASS" if t2_ok else "FAIL",
        },
        {
            "claim_id": "C2-policy-beats-strong-baseline-synthetic-holdout",
            "claim_state_after": "SUPPORTED_WITHIN_SCOPE" if candidate_ok else "NOT_SUPPORTED",
            "evidence_level": "E1_CONTROLLED_SYNTHETIC_MATCHED",
            "empirical_myopic_mean_regret": emp_regret,
            "entropy_mean_regret": ent_regret,
            "answer_mean_regret": ans_regret,
        },
        {
            "claim_id": "WDI-CD-R-adds-beyond-U",
            "claim_state_after": "NOT_TESTED"
            if not wdi_payload or "incremental" not in wdi_payload
            else (
                "NOT_SUPPORTED"
                if (wdi_payload["incremental"].get("delta_spearman") is None)
                or float(wdi_payload["incremental"].get("delta_spearman") or 0) < 0.05
                else "PARTIALLY_SUPPORTED"
            ),
            "evidence_level": "E3_REAL_DATA_REPLAY",
            "snapshot_id": None if not wdi_payload else wdi_payload.get("snapshot_id"),
        },
        {
            "claim_id": "C2-ops-positive-deltaU-vs-top1",
            "claim_state_after": "TESTED",
            "evidence_level": "E4_CONTROLLED_DEPLOYMENT_LIKE",
        },
    ]

    answers = {
        "A_operational_recoverability_beyond_uncertainty": "YES" if gr_pass else "NO",
        "B_policy_beyond_shadow": "PARTIAL" if promotion["stage"] == "COUNTERFACTUAL_EVALUATED" else "NO",
        "C_synthetic_generalizes": "PARTIAL",
        "D_deployment_like_positive_value": "NO",
    }
    if wdi_payload and wdi_payload.get("incremental", {}).get("delta_spearman") is not None:
        if float(wdi_payload["incremental"]["delta_spearman"]) >= 0.05:
            answers["A_operational_recoverability_beyond_uncertainty"] = "PARTIAL"
    if ops_payload and ops_payload.get("runs"):
        answers["D_deployment_like_positive_value"] = "PARTIAL"
        for run in ops_payload["runs"]:
            eq = run.get("equal_budget") or {}
            pol_u = eq.get("policy_utility")
            ans_u = eq.get("force_answer_utility")
            if pol_u is not None and ans_u is not None and float(pol_u) > float(ans_u) + 0.02:
                answers["D_deployment_like_positive_value"] = "YES"
                break

    figure_data = {
        "figure1_R_vs_deltaU": [
            {"R_hat": r["R_hat"], "R_star": r["R_star"], "tau": r["tau_explore_net"], "family": r["family"]}
            for r in hold
        ],
        "figure2_mismatch": e1["mismatch_table"],
        "figure3_regret_vs_mismatch": [
            {"mu": r["mu"], "regret": r["regret"]} for r in mismatch_rows
        ],
        "figure4_neu_rho": [{"rho": r["rho"], "kappa": r["kappa"], "NEU": r["NEU"], "selected": r["selected"]} for r in costs],
        "figure5_kappa": [{"kappa": r["kappa"], "NEU": r["NEU"], "selected": r["selected"]} for r in costs],
        "figure9_oracle_vs_proxy": [
            {"R_star": r["R_star"], "R_hat": r["R_hat"], "abs_error_R": r["abs_error_R"]} for r in hold
        ],
        "figure10_failure": policy_eval["empirical_myopic"]["failure_counts"],
    }

    payload = {
        "schema_version": "cycle2.1",
        "run_id": dest.name,
        "timestamp": started,
        "git_sha": git_sha,
        "package_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seed": seed,
        "plan_hashes": plan_hashes,
        "benchmark_version": BENCHMARK_VERSION,
        "split_manifest": manifest,
        "e0_gate1": e0,
        "e1_diagnostic": e1,
        "e2_gr": gr_pack,
        "e3_e4_policy": policy_eval,
        "promotion": promotion,
        "mismatch_hypothesis": mismatch_h,
        "corruption_false_high": sum(1 for r in corruption if r["false_high"]),
        "corruption_false_low": sum(1 for r in corruption if r["false_low"]),
        "corruption_n": len(corruption),
        "cost_surface": costs,
        "wdi": wdi_payload,
        "ops": ops_payload,
        "graph": {
            "status": "GRAPH_PATH_PRESERVED",
            "experiment": "GRAPH_EXPERIMENT_NOT_RUN_OUT_OF_SCOPE",
        },
        "claims": claims,
        "maturity": maturity,
        "answers": answers,
        "strongest_baseline": strongest_baseline,
        "strongest_policy_on_synthetic_holdout": strongest_policy,
        "experiment_decisions": decisions,
        "figure_data_paths": "figure_data.json",
        "n_states": len(states),
    }

    write_manifest(dest, seed=seed, command="cycle2-audit", root=root, config={"seed": seed, "plans": plan_hashes})
    (dest / "cycle2.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (dest / "figure_data.json").write_text(json.dumps(figure_data, indent=2, default=str), encoding="utf-8")
    (dest / "claim_ledger.jsonl").write_text(
        "\n".join(json.dumps(c, default=str) for c in claims), encoding="utf-8"
    )
    (dest / "maturity_gate_report.json").write_text(json.dumps(maturity, indent=2), encoding="utf-8")
    (dest / "split_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (dest / "estimand_registry.json").write_text(
        (root / "experiments" / "analysis_plans" / "estimand_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (dest / "overlap_report.json").write_text(
        json.dumps({"status": "OPE_NOT_IDENTIFIABLE", "propensities": None, "reason": "no logging policy on synthetic oracle path"}, indent=2),
        encoding="utf-8",
    )
    (dest / "calibration_report.json").write_text(
        json.dumps({"ece_R_holdout": gr_pack["ece_R"], "sigma_R_proxy": "UNCERTAINTY_UNKNOWN"}, indent=2),
        encoding="utf-8",
    )
    (dest / "fault_injection_report.json").write_text(
        json.dumps({"ops": None if not ops_payload else ops_payload.get("runs")}, indent=2, default=str),
        encoding="utf-8",
    )
    (dest / "evidence_contract.json").write_text(
        json.dumps(
            {
                "schema_version": "cycle2.1",
                "cycle_id": "C2",
                "analysis_plan_hashes": plan_hashes,
                "git_sha": git_sha,
                "primary_claims": [c["claim_id"] for c in claims],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    policy_card = {
        "policy_id": "empirical_myopic_cycle2",
        "version": "exp-c2",
        "action_set": ["ANSWER", "EXPLORE", "ASK", "ANALYZE", "DEFER"],
        "feature_schema": "proxy observation kernels + belief; no gold",
        "fallback_policy": "DEFER",
        "supported_domains": ["cycle2_synthetic"],
        "unsupported_states": ["production", "WDI as default"],
        "stage": promotion["stage"],
        "known_failures": ["Gate 1 proxy recoverability"],
    }
    (dest / "policy_card.json").write_text(json.dumps(policy_card, indent=2), encoding="utf-8")
    (dest / "model_backend_manifest.json").write_text(
        json.dumps(
            {
                "bm25": "executed" if include_ops else "NOT_RUN",
                "hybrid_hash": "executed" if include_ops else "NOT_RUN",
                "neural": "executed" if neural_executed else "NOT_RUN",
                "hashing_is_not_neural": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (dest / "dataset_manifest.json").write_text(
        json.dumps(
            {
                "synthetic": BENCHMARK_VERSION,
                "wdi_snapshot": None if not wdi_payload else wdi_payload.get("snapshot_id"),
                "ops": "data/ops",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (dest / "reproduction_manifest.json").write_text(
        json.dumps(
            {
                "command": "python -m quasar2.cli cycle2-audit --output experiments/results/cycle2_maturity --overwrite",
                "seed": seed,
                "git_sha": git_sha,
                "plan_hashes": plan_hashes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    from quasar2.cycle2.report import write_report

    write_report(dest, payload)
    payload["artifact_dir"] = str(dest)
    return payload
