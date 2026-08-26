# QUASAR2 Cycle 1 — Gate 1 report

## 1. Repository Audit
Frozen v0.1.1 loop, recoverability estimators, synthetic recoverability-bench, shadow study, WDI tracks, and claim ledger were already present. No recoverability_bench artifact existed for section-2 numbers; those remain UNVERIFIED_HISTORICAL_OBSERVATION and were recomputed this cycle.

## 2. Scientific Question
Does deployment-observable recoverability predict realized EXPLORE gain beyond uncertainty?

## 3. Hypothesis
H1: A deployment-safe recoverability score improves registered-test Spearman/R2/AUROC for Delta U beyond entropy and belief margin.
H0: Deployment-safe recoverability does not add out-of-sample predictive information for Delta U_EXPLORE beyond uncertainty predictors.
Estimand: forced-action tau_action(s) = U(force EXPLORE) - U(force ANSWER) inside the synthetic observation model (SIMULATOR_CAUSAL_WITHIN_MODEL). Secondary: availability tau_avail on the 120-query sanity fixture.
Identification: SIMULATOR_CAUSAL_WITHIN_MODEL (synthetic); availability pairing on the sanity fixture is not a randomized trial.
Analysis-plan hash: `8b1c9bb04a2b7cea3fc24bd75e4a7df534e9093eff591fdf9aaac02081386aff`
Split/test-access: registered_test used once for the gate; sealed_replication stored unused.
Unit of inference: synthetic state clustered by `regime_id`. Minimum practical effect δ=0.05.
Label: confirmatory on synthetic registered_test; fixture arm exploratory.

## 4. Changes
Added Gate-1 protocol, stress regimes, paired analysis, leakage audit, negative-result ledger, notation registry, CLI `gate1-audit`. Legacy executed policy unchanged.

## 5. Bugs Found
No seed/config no-op found in Gate-1 path. Section-2 metrics lacked run artifacts (traceability bug of the research record, not of the frozen loop).

## 6. Tests
See `tests/test_gate1.py` and legacy goldens. Reproduction command: `quasar2 gate1-audit --output experiments/results/gate1_cycle1`.

## 7. Experimental Design
Synthetic N_train=45 N_registered=36 N_sealed=18; intervention=forced EXPLORE vs ANSWER under true kernels; predictors from proxy kernels only; seeds=[0, 1, 2].

## 8. Results
Gate-1 status: **FAIL** (no_stable_incremental_information_on_registered_test).
DRS−entropy Spearman difference: {'point': -0.18019170319294608, 'ci_low': -0.41403933560541256, 'ci_high': 0.0, 'n_clusters': 4, 'samples': 400, 'n_successful_draws': 400}.
Incremental M1−M0: {'fit_split': 'development+model_selection', 'eval_split': 'registered_test', 'm0_features': ['intercept', 'entropy', 'belief_margin'], 'm1_features': ['intercept', 'entropy', 'belief_margin', 'drs', 'jsd', 'tv'], 'spearman_m0': 0.5174492805105512, 'spearman_m1': -0.19788480034140055, 'r2_m0': 0.025970923242735162, 'r2_m1': 0.17611520324436308, 'auroc_m0': 0.5436363636363636, 'auroc_m1': 0.24909090909090909, 'delta_spearman': -0.7153340808519517, 'delta_r2': 0.1501442800016279, 'cluster_bootstrap_delta_spearman': {'point': -0.7153340808519517, 'ci_low': -1.1352343008766146, 'ci_high': -0.09989647489487663, 'n_clusters': 4, 'samples': 400, 'n_successful_draws': 400}, 'preprocessing_inside_train': True, 'test_untouched_until_eval': True}.
Per-regime: [{'regime_id': 'false_recoverability', 'n': 9, 'mean_delta_u': -0.12299999999999997, 'spearman_drs': 0.8660254037844386, 'spearman_entropy': 0.8660254037844386, 'spearman_jsd': 0.5}, {'regime_id': 'hidden_recoverability', 'n': 9, 'mean_delta_u': 0.25000000000000006, 'spearman_drs': 0.8660254037844386, 'spearman_entropy': 0.8660254037844386, 'spearman_jsd': 0.5}, {'regime_id': 'misspecified_observation', 'n': 9, 'mean_delta_u': 0.16333333333333344, 'spearman_drs': 0.8660254037844386, 'spearman_entropy': 0.8660254037844386, 'spearman_jsd': 1.0}, {'regime_id': 'heldout_family_true_proxy', 'n': 9, 'mean_delta_u': 0.25, 'spearman_drs': 1.0, 'spearman_entropy': 1.0, 'spearman_jsd': 0.8660254037844386}].
Quadrant (secondary): {'thresholds_fit_on': 'development+model_selection', 'entropy_cut': 0.9709505944546688, 'drs_cut': 0.19599999999999998, 'n_high_H_high_R': 24, 'n_high_H_low_R': 6, 'mean_delta_u_high_H_high_R': 0.242625, 'mean_delta_u_high_H_low_R': 0.36000000000000004, 'contrast': -0.11737500000000003, 'ci_high_H_high_R': {'point': 0.242625, 'ci_low': 0.04230000000000003, 'ci_high': 0.41, 'n_clusters': 4, 'samples': 400, 'n_successful_draws': 400}, 'ci_high_H_low_R': {'point': 0.36000000000000004, 'ci_low': 0.36000000000000004, 'ci_high': 0.36000000000000004, 'n_clusters': 1, 'samples': 400, 'n_successful_draws': 400}, 'secondary_not_primary': True}.
Raw per-unit artifacts: `records.csv` in the run directory.

## 9. Strongest Baseline
Uncertainty baseline: {'method': 'entropy', 'n': 36, 'spearman': 0.5082941956424876, 'pearson': 0.11539784572574809, 'r2': 0.013316662798143556, 'auroc_useful': 0.5436363636363636, 'auprc_useful': 0.62160207909732, 'brier_useful': 0.2931844562582644, 'reliability': [{'bin': 7, 'low': 0.875, 'high': 1.0, 'n': 36, 'mean_score': 0.9779043692818951, 'mean_target': 0.6944444444444444, 'calibration_gap': 0.28345992483745064}]}. Entropy remains the required comparator. Simple threshold/BM25 remain operational threats on WDI (unchanged historical).

## 10. Negative Results
See `docs/NEGATIVE_RESULTS.md`. Sealed set was not mined. 120-query EXPLORE rarity is retained as a limitation.

## 11. Claim Ledger Changes
[
  {
    "claim_id": "G1-deploy-R-predicts-deltaU",
    "from_status": "PROPOSED",
    "to_status": "NOT_SUPPORTED",
    "scope": "synthetic registered_test regimes; SIMULATOR_CAUSAL_WITHIN_MODEL",
    "reason": "no_stable_incremental_information_on_registered_test",
    "supporting_run_ids": [
      "gate1-audit"
    ],
    "assumptions": [
      "proxy Bernoulli/true kernels as specified",
      "0-1 Bayes value"
    ],
    "confirmatory": true
  },
  {
    "claim_id": "G1-R-adds-beyond-uncertainty",
    "from_status": "PROPOSED",
    "to_status": "NOT_SUPPORTED",
    "scope": "M0 entropy+margin vs M1 + DRS/JSD/TV on registered_test",
    "reason": "no_stable_incremental_information_on_registered_test",
    "supporting_run_ids": [
      "gate1-audit"
    ],
    "confirmatory": true
  },
  {
    "claim_id": "G1-quadrant-effect-modification",
    "from_status": "PROPOSED",
    "to_status": "TESTED",
    "scope": "secondary quadrant contrast; thresholds frozen on train",
    "reason": "secondary_not_primary",
    "confirmatory": false
  },
  {
    "claim_id": "G1-fixture-availability-explore-gain",
    "from_status": "PROPOSED",
    "to_status": "TESTED",
    "scope": "120-query sanity fixture FULL vs noExplore",
    "reason": "Easy 120-query fixture is a regression/availability sanity test, not the confirmatory Gate-1 holdout. Zero or rare EXPLORE under the legacy loop is an expected limitation, not a reason to force EXPLORE.",
    "confirmatory": false
  }
]

## 12. Theory Impact
T2 bound remains a certificate, not Q(s,EXPLORE). Recoverability is treated as a predictor/effect-modifier candidate, not a manipulated cause.

## 13. Maturity Gates
{
  "theory": {
    "state": "TESTED",
    "evidence_ids": [
      "docs/THEORY.md",
      "T2-binary-voi"
    ]
  },
  "measurement": {
    "state": "FAILED",
    "evidence_ids": [
      "G1",
      "8b1c9bb04a2b7cea3fc24bd75e4a7df534e9093eff591fdf9aaac02081386aff"
    ]
  },
  "causal": {
    "state": "TESTED",
    "evidence_ids": [
      "SIMULATOR_CAUSAL_WITHIN_MODEL"
    ],
    "note": "not real-world causal"
  },
  "policy": {
    "state": "SPECIFIED",
    "evidence_ids": [
      "H-learned-beats-voi"
    ]
  },
  "retrieval": {
    "state": "SPECIFIED",
    "evidence_ids": [
      "H-discriminative-recall-decouple"
    ]
  },
  "external": {
    "state": "TESTED",
    "evidence_ids": [
      "H10-simple-baseline"
    ]
  },
  "statistics": {
    "state": "TESTED",
    "evidence_ids": [
      "G1-cluster-bootstrap"
    ]
  },
  "reproducibility": {
    "state": "IMPLEMENTED",
    "evidence_ids": [
      "quasar2 gate1-audit"
    ]
  },
  "replication": {
    "state": "NOT_STARTED",
    "evidence_ids": []
  }
}

## 14. Largest Threat
Deployment recoverability may be a restatement of the true kernel, or a misleading proxy under misspecification. The strongest simple baseline this cycle is entropy/belief-margin. The strongest modern operational threat remains BM25/hybrid one-shot on WDI (historical). Registered-test entropy Spearman=0.5082941956424876.

## 15. Highest-Information Next Experiment
Cycle 2 confirmatory: freeze the current analysis card and measure whether recoverability adds incremental information for paired FULL vs forced-NOEXPLORE on a WDI controlled-degradation slice that is not the sealed replication set, using query-family clustered inference.

### Fixture availability arm (exploratory)
n_pairs=120 useful=6 full_explore_rounds>0: 31 mean_delta_u=-0.04933333333333335
Easy 120-query fixture is a regression/availability sanity test, not the confirmatory Gate-1 holdout. Zero or rare EXPLORE under the legacy loop is an expected limitation, not a reason to force EXPLORE.
