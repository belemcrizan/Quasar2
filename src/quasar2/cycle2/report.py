"""Section-58 report. Integrates addendum statuses into the 29 required sections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _j(value: object) -> str:
    return json.dumps(value, indent=2, default=str)


def write_report(dest: Path, payload: Mapping[str, Any]) -> Path:
    m = payload["maturity"]
    e0 = payload["e0_gate1"]
    e1 = payload["e1_diagnostic"]
    gr = payload["e2_gr"]
    pol = payload["e3_e4_policy"]
    wdi = payload.get("wdi") or {}
    ops = payload.get("ops") or {}
    answers = payload["answers"]
    md = f"""# QUASAR2 Cycle 2 — maturity report

schema_version: cycle2.1
run_id: {payload.get("run_id")}
git_sha: {payload.get("git_sha")}
seed: {payload.get("seed")}
timestamp: {payload.get("timestamp")}
analysis_plan_hashes: `{payload.get("plan_hashes")}`

This cycle does not replace the frozen v0.1.1 executed loop. Gate 1 remains FAIL.

---

## 1. Repository Audit

EXISTING: recoverability estimators (TV/KL/JSD/MI/DRS/learned), proxy kernels, true synthetic kernels, empirical VoI, T2 bounds, Gate 1 protocol + locked FAIL artifacts, shadow policies (legacy/threshold/myopic/SPRT/learned/oracle), V2.4 WDI policy, phase diagrams, WDI snapshots, OPS runbook fixture, claim ledger, run registry, leakage audit, tests.

PARTIAL: action values mixed recoverability with heuristic utilities; T2 bound labeled but myopic policy could still be misread as Q; OPS fixture existed without sequential fault/cost pairing; WDI lacked a registered controlled-degradation recoverability card.

MISSING (before this cycle): RecoverabilityState (R_hat, sigma_R, M_R), mismatch μ curves, proxy corruption suite, tau_EXPLORE as distinct estimand, ActionValueEstimate contract, promotion ladder artifacts, full counterfactual Q* vector per family, family-holdout generator governance, deployment simulation layer, evidence contracts, estimand registry.

INCORRECT: none newly promoted. Historical section-2 Spearman numbers remain UNVERIFIED_HISTORICAL_OBSERVATION.

SCIENTIFICALLY UNSAFE (guarded): using T2 as Q; using gold/true kernels in deployment features; retuning DRS on Gate-1 registered_test; claiming OPE without propensities.

READY TO REUSE: Gate 1 synthesizer, association/bootstrap, ridge, BM25/hybrid/neural factory, WDI snapshot `wdi-ci-offline-fixture`, OPS corpus.

GRAPH_PATH_PRESERVED. GRAPH_EXPERIMENT_NOT_RUN_OUT_OF_SCOPE.

---

## 2. Scientific Questions

Observation model -> recoverability estimation -> action-effect estimation -> action-value estimation -> policy -> deployment-like evaluation.

Primary: can deployment-observable recoverability predict useful acquisition beyond uncertainty? Can empirical action values choose among ANSWER/EXPLORE/ASK/ANALYZE/DEFER without using T2 as Q? Do results survive family holdout and mismatch? Does any policy beat equal-budget baselines in OPS/WDI?

---

## 3. Files Changed

Cycle-2 package under `src/quasar2/cycle2/`, CLI `cycle2-audit`, tests `tests/test_cycle2.py`, analysis plans, claim ledger and changelog notes. Frozen v0.1.1 artifacts and `experiments/analysis_plans/gate1.json` are not rewritten as a new Gate 1.

---

## 4. New Files

`src/quasar2/cycle2/*`, `experiments/analysis_plans/cycle2.json`, `gr_recoverability.json`, `wdi_controlled_degradation.json`, `estimand_registry.json`, `tests/test_cycle2.py`, this report directory.

---

## 5. Bugs / Scientific Errors Found

Gate 1 FAIL is a locked scientific result, not an implementation bug. Recoverability was previously a single scalar conflating separability with treatment effect. Action-value code now refuses T2=Q. Proxy corruption can produce R_hat high / R_star low (`false_high={payload.get("corruption_false_high")}`) and the reverse (`false_low={payload.get("corruption_false_low")}`).

---

## 6. Recoverability Changes

RecoverabilityEstimate stores R_hat, sigma_R (0 under oracle kernels; UNCERTAINTY_UNKNOWN under proxy), M_R (TV mismatch when oracle_run else unknown), and unaggregated components R_available/accessible/relevant/novel/leverage/net.

Uncertainty, recoverability, decision-flip, and DeltaU remain distinct. Recoverability is a predictor of tau_EXPLORE, not tau itself.

Successor: {gr.get("successor")} (Gate 1 not retuned).

---

## 7. Recoverability Results

dataset: cycle2 synthetic holdout families
N_holdout: {gr.get("n_holdout")}
N_train: {gr.get("n_train")}
seed: {payload.get("seed")}
G-R: {gr.get("gate_GR")}
corr(R_hat, tau): {gr.get("corr_Rhat_tau")}
corr(entropy, tau): {gr.get("corr_entropy_tau")}
corr(R_star, tau): {gr.get("corr_Rstar_tau")}
M0 vs M1: {_j(gr.get("incremental"))}
prevalence(tau>0.05): {gr.get("prevalence")}
AUPRC R: {gr.get("auprc_R")} vs entropy {gr.get("auprc_entropy")}
ECE R: {gr.get("ece_R")}
precision@25% R vs entropy: {gr.get("precision_at_25pct_R")} vs {gr.get("precision_at_25pct_entropy")}
run_id: {payload.get("run_id")}
git SHA: {payload.get("git_sha")}
artifact: cycle2.json / e2_gr

---

## 8. Oracle vs Proxy Gap

On holdout: corr(R_star, tau)={gr.get("corr_Rstar_tau")} vs corr(R_hat, tau)={gr.get("corr_Rhat_tau")}.
Matched vs mismatched (E1): {_j({k: e1[k] for k in e1 if k != "mismatch_table"})}

H_mismatch |R_hat-R_star| vs policy regret (mismatch sweep Spearman): {payload.get("mismatch_hypothesis", {}).get("H_mismatch_abs_error_predicts_regret")}

---

## 9. Observation-Model Mismatch Results

{_j(payload.get("mismatch_hypothesis"))}

μ* (first μ with Spearman(R_hat, ΔU)<0.1, if any): {payload.get("mismatch_hypothesis", {}).get("mu_star")}

---

## 10. Treatment-Effect Results

tau_EXPLORE is Q*(EXPLORE)-Q*(ANSWER) under asymmetric utility. Interaction model (observational, not causal): {_j(gr.get("interaction"))}

---

## 11. Action-Value Implementation

ActionValueEstimate for ANSWER, EXPLORE, ASK, ANALYZE, DEFER with gross/cost/risk/net. ASK uses noisy/incomplete/refusal user models. ANALYZE is a charged heuristic, not T1. DEFER has explicit utility. T2 bound stored separately; t2_is_not_q=true.

---

## 12. Policy Candidates

immediate_answer, entropy_only, threshold, empirical_myopic, conservative_lcb, learned, oracle, random_budget.
Promotion: {_j(payload.get("promotion"))}

Holdout regret: {_j({k: v.get("overall") for k, v in pol.items()})}

---

## 13. Policy Regret

See section 12. Macro-by-family for empirical_myopic: {_j(pol.get("empirical_myopic", {}).get("macro_family_mean_regret"))}

---

## 14. Policy Calibration

Near-ties counted per policy (`n_near_tie`). sigma on Q is UNCERTAINTY_UNKNOWN unless oracle. ECE is reported for R vs useful-acquisition, not claimed as a conformal guarantee.

---

## 15. Synthetic Stress Results

benchmark_version: {payload.get("benchmark_version")}
n_states: {payload.get("n_states")}
cost surface: {_j(payload.get("cost_surface"))}

---

## 16. Family-Holdout Results

split_manifest: {_j(payload.get("split_manifest"))}
Learned and G-R fit only on development families. Holdout includes OpenSet, ProxyMismatch, CorrelatedEvidence, AdversarialProxy, AntiClear, NonRecoverableAmbiguity, MissingEvidence, Multimodal.

---

## 17. Anti-QUASAR Results

empirical_myopic anti-QUASAR regret: {_j(pol.get("empirical_myopic", {}).get("anti_quasar"))}
entropy_only anti-QUASAR: {_j(pol.get("entropy_only", {}).get("anti_quasar"))}
immediate_answer anti-QUASAR: {_j(pol.get("immediate_answer", {}).get("anti_quasar"))}

A mature policy should approach simple ANSWER/DEFER here. If empirical_myopic regret exceeds immediate_answer, that is reported as a negative.

---

## 18. WDI Controlled-Degradation Results

evidence rung: D2 (paired retrieval depth on frozen snapshot)
sealed_test: never loaded into analysis rows
payload (records stripped): {_j(wdi)}

---

## 19. Deployment-Like OPS Results

evidence rung: D3 sequential simulator with faults
neural claim: only if executed
{_j(ops)}

---

## 20. Equal-Budget Results

Synthetic: precision@25% acquisition budget (R vs entropy) in section 7; random_budget policy regret in section 12.
OPS paired force-ANSWER vs force-EXPLORE vs entropy policy on the same queries (see ops equal_budget if present).

---

## 21. Strongest Baseline

synthetic holdout strongest simple baseline: {payload.get("strongest_baseline")}
strongest among evaluated policies: {payload.get("strongest_policy_on_synthetic_holdout")}

---

## 22. Negative Results

- Gate 1 FAIL locked: deployment-observable recoverability did not add stable predictive information for realized EXPLORE gain beyond uncertainty on the registered test.
- G-R on new families: {gr.get("gate_GR")} ({gr.get("successor")}).
- OPE_NOT_IDENTIFIABLE for shadow logs.
- Graph experiment not run (out of scope).
- Neural: NOT_RUN unless backend executed.

---

## 23. Failure Taxonomy

empirical_myopic failure_counts: {_j(pol.get("empirical_myopic", {}).get("failure_counts"))}
regret_decomposition (diagnostic, not exact additive identity): {_j(pol.get("empirical_myopic", {}).get("regret_decomposition"))}

Gate 1 diagnostic tree (E1): {e1.get("diagnostic_tree")} primary={e1.get("primary_diagnosis")}

---

## 24. Claim Ledger Changes

{_j(payload.get("claims"))}

Statuses used: NOT_TESTED / TESTED / NOT_SUPPORTED / PARTIALLY_SUPPORTED / SUPPORTED_WITHIN_SCOPE / REFUTED.
No generic SUPPORTED without scope. Failed Gate 1 claims are not overwritten.

---

## 25. Tests

`tests/test_cycle2.py` plus legacy suite. Bound≠Q, leakage, family holdout, sealed WDI exclusion, ASK noise, DEFER utility, mismatch mixing monotonicity where constructed.

---

## 26. Reproducibility

command: `python -m quasar2.cli cycle2-audit --output experiments/results/cycle2_maturity --overwrite`
seed: {payload.get("seed")}
git SHA: {payload.get("git_sha")}
plan hashes: {_j(payload.get("plan_hashes"))}
artifacts: evidence_contract.json, estimand_registry.json, claim_ledger.jsonl, split_manifest.json, dataset_manifest.json, model_backend_manifest.json, policy_card.json, overlap_report.json, calibration_report.json, fault_injection_report.json, maturity_gate_report.json, reproduction_manifest.json

---

## 27. Maturity Gates

{_j(m)}

Hard ceilings from Section 84 applied. Scores above 8.5 require all hard gates PASS.

---

## 28. Remaining Threats

Proxy kernels remain a model of retrieval, not retrieval. WDI CI snapshot is small. OPS gold labels are fixture-authoritative, not independently adjudicated. ASK user models are synthetic. Neural may be NOT_RUN. Cluster n for families is small. No live shadow (D4) and no canary dossier (D5).

---

## 29. Highest-Information Next Experiment

{e1.get("primary_diagnosis")} suggests the highest-information follow-up is a **new sealed snapshot** successor test of a **pre-registered R_leverage | mismatch-aware** construct, or retirement from policy inputs if WDI validation remains null. Do not retune on Gate 1 registered_test.

---

## Final decision (Section 59)

A. Can operational recoverability now predict useful information acquisition beyond uncertainty?
**{answers.get("A_operational_recoverability_beyond_uncertainty")}**

B. Is the experimental policy ready to move beyond shadow evaluation?
**{answers.get("B_policy_beyond_shadow")}**

C. Does the synthetic evidence generalize across unseen environment families and model mismatch?
**{answers.get("C_synthetic_generalizes")}**

D. Does QUASAR2 demonstrate positive decision value under at least one deployment-like environment against strong equal-budget baselines?
**{answers.get("D_deployment_like_positive_value")}**

Maturity (evidence-based, ceilings applied):

- Operational Recoverability: {m.get("Operational Recoverability")}/10
- Deployment-Ready Policy: {m.get("Deployment-Ready Policy")}/10
- Controlled Synthetic Evidence: {m.get("Controlled Synthetic Evidence")}/10
- Deployment-Like Evidence: {m.get("Deployment-Like Evidence")}/10

Experiment stop/continue decisions: {_j(payload.get("experiment_decisions"))}
"""
    path = dest / "REPORT.md"
    path.write_text(md, encoding="utf-8")
    return path
