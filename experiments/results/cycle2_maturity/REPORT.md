# QUASAR2 Cycle 2 — maturity report

schema_version: cycle2.1
run_id: cycle2_maturity
git_sha: 624926faa22722c913a9436367910090629c4a0d
seed: 0
timestamp: 2026-08-26T20:04:48+00:00
analysis_plan_hashes: `{'cycle2.json': '2ace3810fc5400ba71f0319417dd3390aab82e9e6649ac7e5b9aff36d9aad6ec', 'gr_recoverability.json': '101c54decf7455573bf0160195383111f27476f5b56d4a3ce3d33723be394495', 'wdi_controlled_degradation.json': '1de1496c1a7f8c3208831a08f0f8e9011c5542391d7b28d1506d4b0e14cd201b', 'estimand_registry.json': 'fcfcef46a49cd143c0ea9451b169227406e26b767147f4e604de851346b39645', 'gate1.json': '5f92bd6bbcd66d65f02273e94713e0513335761480a91cd8ac8efb92b4bbfaec'}`

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

Gate 1 FAIL is a locked scientific result, not an implementation bug. Recoverability was previously a single scalar conflating separability with treatment effect. Action-value code now refuses T2=Q. Proxy corruption can produce R_hat high / R_star low (`false_high=0`) and the reverse (`false_low=4`).

---

## 6. Recoverability Changes

RecoverabilityEstimate stores R_hat, sigma_R (0 under oracle kernels; UNCERTAINTY_UNKNOWN under proxy), M_R (TV mismatch when oracle_run else unknown), and unaggregated components R_available/accessible/relevant/novel/leverage/net.

Uncertainty, recoverability, decision-flip, and DeltaU remain distinct. Recoverability is a predictor of tau_EXPLORE, not tau itself.

Successor: SUCCESSOR_A_diagnostic_only (Gate 1 not retuned).

---

## 7. Recoverability Results

dataset: cycle2 synthetic holdout families
N_holdout: 102
N_train: 62
seed: 0
G-R: FAIL
corr(R_hat, tau): 0.4038144980235418
corr(entropy, tau): -0.06491875161446571
corr(R_star, tau): 0.6796989946551878
M0 vs M1: {
  "m0_spearman": 0.2092564960096081,
  "m1_spearman": 0.39992837371009066,
  "m0_r2": 0.11441371050213915,
  "m1_r2": 0.19598226179498196,
  "delta_spearman": 0.19067187770048255,
  "cluster_bootstrap_delta_spearman": {
    "point": 0.19067187770048255,
    "ci_low": -0.2289426033663058,
    "ci_high": 0.49229374643702917,
    "n_clusters": 8,
    "samples": 400,
    "n_successful_draws": 400
  },
  "weights_m0": [
    0.8242546592632667,
    -0.43364573316313715,
    -0.9254357700506359
  ],
  "weights_m1": [
    -0.0012252524176890045,
    -0.09810641050781449,
    -0.17349905594403892,
    1.2604888760776056
  ],
  "n_train": 62,
  "n_test": 102
}
prevalence(tau>0.05): 0.4019607843137255
AUPRC R: 0.6044888700567242 vs entropy 0.34334834248937346
ECE R: 0.1876372549019608
precision@25% R vs entropy: 0.6 vs 0.32
run_id: cycle2_maturity
git SHA: 624926faa22722c913a9436367910090629c4a0d
artifact: cycle2.json / e2_gr

---

## 8. Oracle vs Proxy Gap

On holdout: corr(R_star, tau)=0.6796989946551878 vs corr(R_hat, tau)=0.4038144980235418.
Matched vs mismatched (E1): {
  "role": "DIAGNOSTIC",
  "n_matched": 149,
  "n_mismatched": 30,
  "corr_Rstar_tau_matched": 0.6390520697139723,
  "corr_Rhat_tau_matched": 0.6390520697139723,
  "corr_Rstar_tau_mismatched": 0.6888365093025152,
  "corr_Rhat_tau_mismatched": -0.30241602847427496,
  "corr_abs_error_R_vs_need": -0.020763615605763067,
  "prevalence_tau_gt_0.05": 0.3575418994413408,
  "diagnostic_tree": [
    "D_observation_model_misspecification",
    "B_construct_mismatch"
  ],
  "primary_diagnosis": "D_observation_model_misspecification"
}

H_mismatch |R_hat-R_star| vs policy regret (mismatch sweep Spearman): 0.7662224051759047

---

## 9. Observation-Model Mismatch Results

{
  "H_mismatch_abs_error_predicts_regret": 0.7662224051759047,
  "table": [
    {
      "mu": 0.0,
      "n": 3,
      "spearman_R_hat_deltaU": 1.0000000000000002,
      "mean_abs_error_R": 0.0,
      "mean_regret": 0.0,
      "false_explore_rate": 0.0,
      "missed_explore_rate": 0.0
    },
    {
      "mu": 0.25,
      "n": 3,
      "spearman_R_hat_deltaU": 1.0000000000000002,
      "mean_abs_error_R": 0.04,
      "mean_regret": 0.0,
      "false_explore_rate": 0.0,
      "missed_explore_rate": 0.0
    },
    {
      "mu": 0.5,
      "n": 3,
      "spearman_R_hat_deltaU": null,
      "mean_abs_error_R": 0.42,
      "mean_regret": 0.57,
      "false_explore_rate": 0.0,
      "missed_explore_rate": 1.0
    },
    {
      "mu": 0.75,
      "n": 3,
      "spearman_R_hat_deltaU": 1.0000000000000002,
      "mean_abs_error_R": 0.04,
      "mean_regret": 0.0,
      "false_explore_rate": 0.0,
      "missed_explore_rate": 0.0
    },
    {
      "mu": 1.0,
      "n": 3,
      "spearman_R_hat_deltaU": 1.0000000000000002,
      "mean_abs_error_R": 0.0,
      "mean_regret": 0.0,
      "false_explore_rate": 0.0,
      "missed_explore_rate": 0.0
    }
  ],
  "mu_star": null
}

μ* (first μ with Spearman(R_hat, ΔU)<0.1, if any): None

---

## 10. Treatment-Effect Results

tau_EXPLORE is Q*(EXPLORE)-Q*(ANSWER) under asymmetric utility. Interaction model (observational, not causal): {
  "coefficients": {
    "intercept": -0.19077308133041873,
    "entropy": 0.05438295797339081,
    "R_hat": 0.3835563437965155,
    "entropy_x_R": 0.9558154815494644,
    "mismatch": 0.0,
    "R_x_mismatch": 0.0
  },
  "test_spearman": 0.29119523374051837,
  "test_r2": 0.1654974029278838,
  "causal_claim": false
}

---

## 11. Action-Value Implementation

ActionValueEstimate for ANSWER, EXPLORE, ASK, ANALYZE, DEFER with gross/cost/risk/net. ASK uses noisy/incomplete/refusal user models. ANALYZE is a charged heuristic, not T1. DEFER has explicit utility. T2 bound stored separately; t2_is_not_q=true.

---

## 12. Policy Candidates

immediate_answer, entropy_only, threshold, empirical_myopic, conservative_lcb, learned, oracle, random_budget.
Promotion: {
  "stage": "SHADOW",
  "frozen_candidate": null,
  "default_untouched": true,
  "ope": "OPE_NOT_IDENTIFIABLE",
  "safe_policy_formal_guarantee": false
}

Holdout regret: {
  "immediate_answer": {
    "n": 102,
    "mean": 0.3106519607843137,
    "median": 0.14999999999999997,
    "p90": 0.8354999999999999,
    "p95": 0.8919999999999999,
    "worst": 0.9975,
    "agreement": 0.30392156862745096
  },
  "entropy_only": {
    "n": 102,
    "mean": 0.06809411764705882,
    "median": 0.0,
    "p90": 0.25,
    "p95": 0.25,
    "worst": 0.39999999999999997,
    "agreement": 0.5392156862745098
  },
  "threshold": {
    "n": 102,
    "mean": 0.07134901960784312,
    "median": 0.0,
    "p90": 0.2476,
    "p95": 0.25,
    "worst": 0.39999999999999997,
    "agreement": 0.5980392156862745
  },
  "empirical_myopic": {
    "n": 102,
    "mean": 0.07287058823529412,
    "median": 0.0,
    "p90": 0.25,
    "p95": 0.49999999999999994,
    "worst": 0.79,
    "agreement": 0.7450980392156863
  },
  "conservative_lcb": {
    "n": 102,
    "mean": 0.07287058823529412,
    "median": 0.0,
    "p90": 0.25,
    "p95": 0.49999999999999994,
    "worst": 0.79,
    "agreement": 0.7450980392156863
  },
  "learned": {
    "n": 102,
    "mean": 0.2113225490196078,
    "median": 0.01000000000000012,
    "p90": 0.72,
    "p95": 0.8354999999999999,
    "worst": 1.0174999999999998,
    "agreement": 0.37254901960784315
  },
  "oracle": {
    "n": 102,
    "mean": 0.0,
    "median": 0.0,
    "p90": 0.0,
    "p95": 0.0,
    "worst": 0.0,
    "agreement": 1.0
  },
  "random_budget": {
    "n": 102,
    "mean": 0.31243235294117644,
    "median": 0.14999999999999997,
    "p90": 0.8354999999999999,
    "p95": 0.9355,
    "worst": 0.9975,
    "agreement": 0.30392156862745096
  }
}

---

## 13. Policy Regret

See section 12. Macro-by-family for empirical_myopic: {
  "MissingEvidence": 0.0,
  "OpenSet": 0.0,
  "ProxyMismatch": 0.37599999999999995,
  "CorrelatedEvidence": 0.0,
  "AdversarialProxy": 0.11952,
  "AntiClear": 0.0,
  "NonRecoverableAmbiguity": 0.0,
  "Multimodal": 0.0
}

---

## 14. Policy Calibration

Near-ties counted per policy (`n_near_tie`). sigma on Q is UNCERTAINTY_UNKNOWN unless oracle. ECE is reported for R vs useful-acquisition, not claimed as a conformal guarantee.

---

## 15. Synthetic Stress Results

benchmark_version: cycle2-synth-v1
n_states: 179
cost surface: [
  {
    "rho": 0.5,
    "kappa": 0.02,
    "selected": "EXPLORE",
    "Q_ANSWER": 0.25,
    "Q_EXPLORE": 0.8,
    "Q_ASK": 0.23249999999999993,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": 0.21,
    "NEU": 0.8
  },
  {
    "rho": 0.5,
    "kappa": 0.1,
    "selected": "EXPLORE",
    "Q_ANSWER": 0.25,
    "Q_EXPLORE": 0.7200000000000001,
    "Q_ASK": 0.23249999999999993,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": 0.21,
    "NEU": 0.7200000000000001
  },
  {
    "rho": 0.5,
    "kappa": 0.4,
    "selected": "EXPLORE",
    "Q_ANSWER": 0.25,
    "Q_EXPLORE": 0.42000000000000004,
    "Q_ASK": 0.23249999999999993,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": 0.21,
    "NEU": 0.42000000000000004
  },
  {
    "rho": 1.4,
    "kappa": 0.02,
    "selected": "EXPLORE",
    "Q_ANSWER": -0.19999999999999996,
    "Q_EXPLORE": 0.692,
    "Q_ASK": -0.05999999999999994,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": -0.23999999999999996,
    "NEU": 0.692
  },
  {
    "rho": 1.4,
    "kappa": 0.1,
    "selected": "EXPLORE",
    "Q_ANSWER": -0.19999999999999996,
    "Q_EXPLORE": 0.612,
    "Q_ASK": -0.05999999999999994,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": -0.23999999999999996,
    "NEU": 0.612
  },
  {
    "rho": 1.4,
    "kappa": 0.4,
    "selected": "EXPLORE",
    "Q_ANSWER": -0.19999999999999996,
    "Q_EXPLORE": 0.31199999999999994,
    "Q_ASK": -0.05999999999999994,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": -0.23999999999999996,
    "NEU": 0.31199999999999994
  },
  {
    "rho": 3.0,
    "kappa": 0.02,
    "selected": "EXPLORE",
    "Q_ANSWER": -1.0,
    "Q_EXPLORE": 0.5,
    "Q_ASK": -0.58,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": -1.04,
    "NEU": 0.5
  },
  {
    "rho": 3.0,
    "kappa": 0.1,
    "selected": "EXPLORE",
    "Q_ANSWER": -1.0,
    "Q_EXPLORE": 0.42000000000000004,
    "Q_ASK": -0.58,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": -1.04,
    "NEU": 0.42000000000000004
  },
  {
    "rho": 3.0,
    "kappa": 0.4,
    "selected": "EXPLORE",
    "Q_ANSWER": -1.0,
    "Q_EXPLORE": 0.12,
    "Q_ASK": -0.58,
    "Q_DEFER": -0.05,
    "Q_ANALYZE": -1.04,
    "NEU": 0.12
  }
]

---

## 16. Family-Holdout Results

split_manifest: {
  "schema_version": "cycle2.1",
  "benchmark_version": "cycle2-synth-v1",
  "n": 179,
  "by_role": {
    "development": [
      "AnswerDominated",
      "AskDominated",
      "CostDominated",
      "EasySeparable",
      "ExploreDominated",
      "HeavyOverlap"
    ],
    "calibration": [
      "NearIdentical"
    ],
    "holdout": [
      "AdversarialProxy",
      "AntiClear",
      "CorrelatedEvidence",
      "MissingEvidence",
      "Multimodal",
      "NonRecoverableAmbiguity",
      "OpenSet",
      "ProxyMismatch"
    ]
  },
  "state_id_hash": "d1e9c62db2b0b4dc7daf19e619224509523d76f95cd90043d5b8aaab7b322de7"
}
Learned and G-R fit only on development families. Holdout includes OpenSet, ProxyMismatch, CorrelatedEvidence, AdversarialProxy, AntiClear, NonRecoverableAmbiguity, MissingEvidence, Multimodal.

---

## 17. Anti-QUASAR Results

empirical_myopic anti-QUASAR regret: {
  "n": 42,
  "mean": 0.042685714285714285,
  "median": 0.0,
  "p90": 0.16759999999999997,
  "p95": 0.25,
  "worst": 0.3976,
  "agreement": 0.6904761904761905
}
entropy_only anti-QUASAR: {
  "n": 42,
  "mean": 0.16165714285714283,
  "median": 0.12199999999999987,
  "p90": 0.3519999999999999,
  "p95": 0.3976,
  "worst": 0.39999999999999997,
  "agreement": 0.023809523809523808
}
immediate_answer anti-QUASAR: {
  "n": 42,
  "mean": 0.04747619047619046,
  "median": 0.0,
  "p90": 0.14999999999999997,
  "p95": 0.14999999999999997,
  "worst": 0.14999999999999997,
  "agreement": 0.5952380952380952
}

A mature policy should approach simple ANSWER/DEFER here. If empirical_myopic regret exceeds immediate_answer, that is reported as a negative.

---

## 18. WDI Controlled-Degradation Results

evidence rung: D2 (paired retrieval depth on frozen snapshot)
sealed_test: never loaded into analysis rows
payload (records stripped): {
  "analysis_plan_hash": "3cd0bff6c2a3567686e4a471aa4bfd2eb33a3b84fd7cd329ceb01fac474407fb",
  "snapshot_id": "wdi-ci-offline-fixture",
  "snapshot_hashes": {
    "entities": "5957cfb0e5071b737b3683850081258db0acb805d3f562fc444c2a90bd8cb02e",
    "indicators": "31c20253daac4a97b3ef9335242e8c0c7699a623a35eb57a7542ecb7b1ac9af8",
    "observations": "984ff624b860fb1fe0ff65c2a6722a205509a46a11bc45d0a6d0cb0a5a87b18e",
    "attribution": "99abc8d76864ed0284eaae05eaae5988614e39749579e180c97ffb2093a11a94"
  },
  "sealed_instances_excluded": true,
  "sealed_count_in_benchmark_not_loaded": 59,
  "n_total_used": 80,
  "n_train": 59,
  "n_test": 5,
  "prevalence_useful": 0.4,
  "incremental": {
    "m0_spearman": 1.0,
    "m1_spearman": 1.0,
    "m0_r2": 1.0,
    "m1_r2": 1.0000000000000004,
    "delta_spearman": 0.0,
    "cluster_bootstrap_delta_spearman": {
      "point": 0.0,
      "ci_low": 0.0,
      "ci_high": 0.0,
      "n_clusters": 1,
      "samples": 400,
      "n_successful_draws": 400
    },
    "weights_m0": [
      0.4763285242743434,
      -0.5041384170330979,
      -0.07516022460716615
    ],
    "weights_m1": [
      1.49619611930059,
      -1.4980596369779975,
      -0.004797811561287252,
      -1.4708953430171412
    ],
    "n_train": 59,
    "n_test": 5
  },
  "spearman_R_test": -1.0,
  "spearman_entropy_test": 1.0,
  "natural": {
    "n": 2,
    "spearman_R": null,
    "spearman_entropy": null
  },
  "degraded": {
    "n": 3,
    "spearman_R": -1.0000000000000002,
    "spearman_entropy": 1.0000000000000002
  },
  "evidence_rung": "D2",
  "identification": "paired_forced_retrieval_depth_on_frozen_snapshot",
  "n_records": 80
}

---

## 19. Deployment-Like OPS Results

evidence rung: D3 sequential simulator with faults
neural claim: only if executed
{
  "runs": [
    {
      "backend": "bm25",
      "inject": null,
      "summary": {
        "backend": {
          "requested": "bm25",
          "executed": "bm25",
          "skip_reason": null
        },
        "n": 12,
        "inject": null,
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.519906483333325,
        "mean_u_explore": 0.43990648333332505,
        "mean_u_policy": 0.519906483333325,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 0.0
      },
      "n_records": 12,
      "mean_delta_u": -0.08000000000000003,
      "equal_budget": {
        "force_answer_utility": 0.519906483333325,
        "force_explore_utility": 0.43990648333332505,
        "policy_utility": 0.519906483333325
      }
    },
    {
      "backend": "bm25",
      "inject": "empty_index",
      "summary": {
        "backend": {
          "requested": "bm25",
          "executed": "bm25",
          "skip_reason": null
        },
        "n": 12,
        "inject": "empty_index",
        "mean_delta_u_explore": 0.0,
        "mean_u_answer": -1.2000000583337773,
        "mean_u_explore": -1.2000000583337773,
        "mean_u_policy": -0.05000000000000001,
        "answer_accuracy": 0.08333333333333333,
        "explore_accuracy": 0.08333333333333333,
        "defer_on_fault": 1.0
      }
    },
    {
      "backend": "bm25",
      "inject": "timeout",
      "summary": {
        "backend": {
          "requested": "bm25",
          "executed": "bm25",
          "skip_reason": null
        },
        "n": 12,
        "inject": "timeout",
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.32,
        "mean_u_explore": 0.23999999999999996,
        "mean_u_policy": -0.05000000000000001,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 1.0
      }
    },
    {
      "backend": "bm25",
      "inject": "duplicate_burst",
      "summary": {
        "backend": {
          "requested": "bm25",
          "executed": "bm25",
          "skip_reason": null
        },
        "n": 12,
        "inject": "duplicate_burst",
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.5199820616658933,
        "mean_u_explore": 0.4399820616658932,
        "mean_u_policy": 0.5199820616658933,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 0.0
      }
    },
    {
      "backend": "bm25",
      "inject": "contradictory",
      "summary": {
        "backend": {
          "requested": "bm25",
          "executed": "bm25",
          "skip_reason": null
        },
        "n": 12,
        "inject": "contradictory",
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.5199586250012119,
        "mean_u_explore": 0.43995862500121197,
        "mean_u_policy": 0.5199586250012119,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 0.0
      }
    },
    {
      "backend": "hybrid",
      "inject": null,
      "summary": {
        "backend": {
          "requested": "hybrid",
          "executed": "hybrid",
          "skip_reason": null
        },
        "n": 12,
        "inject": null,
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.5196126699979262,
        "mean_u_explore": 0.43961266999792614,
        "mean_u_policy": 0.5196126699979262,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 0.0
      }
    },
    {
      "backend": "hybrid",
      "inject": "empty_index",
      "summary": {
        "backend": {
          "requested": "hybrid",
          "executed": "hybrid",
          "skip_reason": null
        },
        "n": 12,
        "inject": "empty_index",
        "mean_delta_u_explore": 0.0,
        "mean_u_answer": -1.200000046667022,
        "mean_u_explore": -1.200000046667022,
        "mean_u_policy": -0.05000000000000001,
        "answer_accuracy": 0.08333333333333333,
        "explore_accuracy": 0.08333333333333333,
        "defer_on_fault": 1.0
      }
    },
    {
      "backend": "hybrid",
      "inject": "timeout",
      "summary": {
        "backend": {
          "requested": "hybrid",
          "executed": "hybrid",
          "skip_reason": null
        },
        "n": 12,
        "inject": "timeout",
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.32,
        "mean_u_explore": 0.23999999999999996,
        "mean_u_policy": -0.05000000000000001,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 1.0
      }
    },
    {
      "backend": "hybrid",
      "inject": "duplicate_burst",
      "summary": {
        "backend": {
          "requested": "hybrid",
          "executed": "hybrid",
          "skip_reason": null
        },
        "n": 12,
        "inject": "duplicate_burst",
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.5196879633322048,
        "mean_u_explore": 0.4396879633322048,
        "mean_u_policy": 0.5196879633322048,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 0.0
      }
    },
    {
      "backend": "hybrid",
      "inject": "contradictory",
      "summary": {
        "backend": {
          "requested": "hybrid",
          "executed": "hybrid",
          "skip_reason": null
        },
        "n": 12,
        "inject": "contradictory",
        "mean_delta_u_explore": -0.08000000000000003,
        "mean_u_answer": 0.5198728466705264,
        "mean_u_explore": 0.4398728466705264,
        "mean_u_policy": 0.5198728466705264,
        "answer_accuracy": 0.8333333333333334,
        "explore_accuracy": 0.8333333333333334,
        "defer_on_fault": 0.0
      }
    }
  ],
  "neural": {
    "backend": {
      "requested": "neural",
      "executed": "neural",
      "skip_reason": null
    },
    "summary": {
      "backend": {
        "requested": "neural",
        "executed": "neural",
        "skip_reason": null
      },
      "n": 12,
      "inject": null,
      "mean_delta_u_explore": -0.08000000000000006,
      "mean_u_answer": 0.7144974349966894,
      "mean_u_explore": 0.6344974349966893,
      "mean_u_policy": 0.7144974349966894,
      "answer_accuracy": 0.9166666666666666,
      "explore_accuracy": 0.9166666666666666,
      "defer_on_fault": 0.0
    },
    "executed": true
  }
}

---

## 20. Equal-Budget Results

Synthetic: precision@25% acquisition budget (R vs entropy) in section 7; random_budget policy regret in section 12.
OPS paired force-ANSWER vs force-EXPLORE vs entropy policy on the same queries (see ops equal_budget if present).

---

## 21. Strongest Baseline

synthetic holdout strongest simple baseline: entropy_only
strongest among evaluated policies: entropy_only

---

## 22. Negative Results

- Gate 1 FAIL locked: deployment-observable recoverability did not add stable predictive information for realized EXPLORE gain beyond uncertainty on the registered test.
- G-R on new families: FAIL (SUCCESSOR_A_diagnostic_only).
- OPE_NOT_IDENTIFIABLE for shadow logs.
- Graph experiment not run (out of scope).
- Neural: NOT_RUN unless backend executed.

---

## 23. Failure Taxonomy

empirical_myopic failure_counts: {
  "anti_quasar_expected_simple_behavior": 27,
  "observation_model_mismatch": 26,
  "recoverability_estimation_failure": 20,
  "policy_selection_failure": 26,
  "action_value_estimation_failure": 13,
  "near_tie": 3
}
regret_decomposition (diagnostic, not exact additive identity): {
  "total_policy_regret": 7.432799999999997,
  "recoverability_error_share": 4.559999999999999,
  "mismatch_share": 7.432799999999997,
  "open_set_share": 0.0,
  "cost_share": 0.0,
  "residual_share": 0.0,
  "n": 102.0,
  "additive_identity_claimed": 0.0
}

Gate 1 diagnostic tree (E1): ['D_observation_model_misspecification', 'B_construct_mismatch'] primary=D_observation_model_misspecification

---

## 24. Claim Ledger Changes

[
  {
    "claim_id": "G1-deploy-R-predicts-deltaU",
    "claim_state_before": "NOT_SUPPORTED",
    "claim_state_after": "NOT_SUPPORTED",
    "evidence_level": "E2_CONTROLLED_SYNTHETIC_MISMATCHED",
    "result": "LOCKED_FAIL",
    "note": "Gate 1 remains FAIL; not overwritten"
  },
  {
    "claim_id": "GR-R-adds-beyond-U-holdout-families",
    "claim_state_before": "NOT_TESTED",
    "claim_state_after": "NOT_SUPPORTED",
    "scope": "cycle2 holdout synthetic families; SIMULATOR_CAUSAL_WITHIN_MODEL",
    "evidence_level": "E2_CONTROLLED_SYNTHETIC_MISMATCHED",
    "result": "FAIL",
    "delta_spearman": 0.19067187770048255,
    "ci": {
      "point": 0.19067187770048255,
      "ci_low": -0.2289426033663058,
      "ci_high": 0.49229374643702917,
      "n_clusters": 8,
      "samples": 400,
      "n_successful_draws": 400
    }
  },
  {
    "claim_id": "C2-empirical-Q-not-T2",
    "claim_state_after": "SUPPORTED_WITHIN_SCOPE",
    "evidence_level": "E0_IMPLEMENTED_ONLY",
    "result": "PASS"
  },
  {
    "claim_id": "C2-policy-beats-strong-baseline-synthetic-holdout",
    "claim_state_after": "NOT_SUPPORTED",
    "evidence_level": "E1_CONTROLLED_SYNTHETIC_MATCHED",
    "empirical_myopic_mean_regret": 0.07287058823529412,
    "entropy_mean_regret": 0.06809411764705882,
    "answer_mean_regret": 0.3106519607843137
  },
  {
    "claim_id": "WDI-CD-R-adds-beyond-U",
    "claim_state_after": "NOT_SUPPORTED",
    "evidence_level": "E3_REAL_DATA_REPLAY",
    "snapshot_id": "wdi-ci-offline-fixture"
  },
  {
    "claim_id": "C2-ops-positive-deltaU-vs-top1",
    "claim_state_after": "TESTED",
    "evidence_level": "E4_CONTROLLED_DEPLOYMENT_LIKE"
  }
]

Statuses used: NOT_TESTED / TESTED / NOT_SUPPORTED / PARTIALLY_SUPPORTED / SUPPORTED_WITHIN_SCOPE / REFUTED.
No generic SUPPORTED without scope. Failed Gate 1 claims are not overwritten.

---

## 25. Tests

`tests/test_cycle2.py` plus legacy suite. Bound≠Q, leakage, family holdout, sealed WDI exclusion, ASK noise, DEFER utility, mismatch mixing monotonicity where constructed.

---

## 26. Reproducibility

command: `python -m quasar2.cli cycle2-audit --output experiments/results/cycle2_maturity --overwrite`
seed: 0
git SHA: 624926faa22722c913a9436367910090629c4a0d
plan hashes: {
  "cycle2.json": "2ace3810fc5400ba71f0319417dd3390aab82e9e6649ac7e5b9aff36d9aad6ec",
  "gr_recoverability.json": "101c54decf7455573bf0160195383111f27476f5b56d4a3ce3d33723be394495",
  "wdi_controlled_degradation.json": "1de1496c1a7f8c3208831a08f0f8e9011c5542391d7b28d1506d4b0e14cd201b",
  "estimand_registry.json": "fcfcef46a49cd143c0ea9451b169227406e26b767147f4e604de851346b39645",
  "gate1.json": "5f92bd6bbcd66d65f02273e94713e0513335761480a91cd8ac8efb92b4bbfaec"
}
artifacts: evidence_contract.json, estimand_registry.json, claim_ledger.jsonl, split_manifest.json, dataset_manifest.json, model_backend_manifest.json, policy_card.json, overlap_report.json, calibration_report.json, fault_injection_report.json, maturity_gate_report.json, reproduction_manifest.json

---

## 27. Maturity Gates

{
  "Operational Recoverability": 7.0,
  "Deployment-Ready Policy": 8.8,
  "Controlled Synthetic Evidence": 9.6,
  "Deployment-Like Evidence": 8.6,
  "notes": {
    "recoverability": [
      "no calibrated uncertainty PASS -> <=7.0",
      "Gate 1 remains failed without decisive operational follow-up -> <=7.0",
      "explicit negative/narrowing conclusion recorded; not operational utility"
    ],
    "policy": [],
    "synthetic": [],
    "deployment": []
  },
  "gates": {
    "recoverability": {
      "heldout_family": "PASS",
      "mismatch": "PASS",
      "calibrated_uncertainty": "PARTIAL",
      "equal_budget_acquisition": "PASS",
      "gate1_followup": "FAIL"
    },
    "policy": {
      "bound_as_q": "PASS",
      "empirical_q": "PASS",
      "baseline_fallback": "PASS",
      "ope_unsupported": "PASS",
      "equal_budget": "PASS",
      "fault_tests": "PASS"
    },
    "synthetic": {
      "counterfactual_oracle": "PASS",
      "family_holdout": "PASS",
      "only_row_split": "PASS",
      "anti_quasar": "PASS",
      "oracle_leakage": "PASS"
    },
    "deployment": {
      "not_synthetic_only": "PASS",
      "wdi_snapshot": "PASS",
      "neural_executed": "PASS",
      "real_retrieval_x_policy": "PASS",
      "shadow_as_causal": "PASS",
      "ops_sequential": "PASS"
    }
  }
}

Hard ceilings from Section 84 applied. Scores above 8.5 require all hard gates PASS.

---

## 28. Remaining Threats

Proxy kernels remain a model of retrieval, not retrieval. WDI CI snapshot is small. OPS gold labels are fixture-authoritative, not independently adjudicated. ASK user models are synthetic. Neural may be NOT_RUN. Cluster n for families is small. No live shadow (D4) and no canary dossier (D5).

---

## 29. Highest-Information Next Experiment

D_observation_model_misspecification suggests the highest-information follow-up is a **new sealed snapshot** successor test of a **pre-registered R_leverage | mismatch-aware** construct, or retirement from policy inputs if WDI validation remains null. Do not retune on Gate 1 registered_test.

---

## Final decision (Section 59)

A. Can operational recoverability now predict useful information acquisition beyond uncertainty?
**NO**

B. Is the experimental policy ready to move beyond shadow evaluation?
**NO**

C. Does the synthetic evidence generalize across unseen environment families and model mismatch?
**PARTIAL**

D. Does QUASAR2 demonstrate positive decision value under at least one deployment-like environment against strong equal-budget baselines?
**PARTIAL**

Maturity (evidence-based, ceilings applied):

- Operational Recoverability: 7.0/10
- Deployment-Ready Policy: 8.8/10
- Controlled Synthetic Evidence: 9.6/10
- Deployment-Like Evidence: 8.6/10

Experiment stop/continue decisions: [
  {
    "experiment": "E0",
    "decision": "CONTINUE_AS_REGISTERED"
  },
  {
    "experiment": "E1",
    "decision": "CONTINUE_AS_REGISTERED"
  },
  {
    "experiment": "E2",
    "decision": "NARROW_CLAIM"
  },
  {
    "experiment": "E3",
    "decision": "NARROW_CLAIM"
  },
  {
    "experiment": "E4",
    "decision": "CONTINUE_AS_REGISTERED"
  },
  {
    "experiment": "E5",
    "decision": "CONTINUE_AS_REGISTERED"
  },
  {
    "experiment": "E6",
    "decision": "CONTINUE_AS_REGISTERED"
  }
]
