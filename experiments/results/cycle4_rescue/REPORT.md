# QUASAR2 Cycle 4–7A — rescue chain (rescue.1)

run_id: `cycle4_rescue`
git_sha: `0622a0ced622b90b0ca2a06da0d1e1c347fcf18e`
seed: `42`
N: `120`

## Primary question

Can additional information actually rescue a decision?

## Gates

- `cycle4_anatomy`: **PASS**
- `cycle5_non_oracle_rescue`: **PASS**
- `cycle5_net_utility`: **FAIL**
- `cycle6_policy`: **BLOCKED**
- `cycle7a_analyze_ask_defer`: **TESTED**
- `leakage_contract`: **PASS**

## Confirmatory metrics (sanity fixture)

- **legacy_full**: RescueRate_FW=0.0 (k=0/n=2); OverthinkingRate_FC=0.00847457627118644 (k=1/n=118); NetRescueRate=-0.008333333333333333; ΔU=-0.09583333333333334
- **disc_predicted**: RescueRate_FW=0.0 (k=0/n=2); OverthinkingRate_FC=0.0 (k=0/n=118); NetRescueRate=0.0; ΔU=-0.1634166666666667
- **relevance**: RescueRate_FW=0.0 (k=0/n=2); OverthinkingRate_FC=0.00847457627118644 (k=1/n=118); NetRescueRate=-0.008333333333333333; ΔU=-0.03341666666666664
- **bm25**: RescueRate_FW=0.0 (k=0/n=2); OverthinkingRate_FC=0.01694915254237288 (k=2/n=118); NetRescueRate=-0.016666666666666666; ΔU=-0.026916666666666644
- **dense**: RescueRate_FW=0.0 (k=0/n=2); OverthinkingRate_FC=0.0 (k=0/n=118); NetRescueRate=0.0; ΔU=-0.04849999999999998
- **falsification**: RescueRate_FW=0.5 (k=1/n=2); OverthinkingRate_FC=0.00847457627118644 (k=1/n=118); NetRescueRate=0.0; ΔU=-0.03991666666666664
- **no_disc_update**: RescueRate_FW=0.0 (k=0/n=2); OverthinkingRate_FC=0.0 (k=0/n=118); NetRescueRate=0.0; ΔU=-0.18841666666666673

## OracleRescueCeiling

{
  "overall": {
    "k": 2,
    "n": 2,
    "rate": 1.0,
    "ci_low": 0.34237195288961925,
    "ci_high": 1.0
  },
  "by_regime": {
    "astronomy:q1": {
      "k": 2,
      "n": 2,
      "rate": 1.0,
      "ci_low": 0.34237195288961925,
      "ci_high": 1.0
    }
  },
  "OracleRecoverability": {
    "k": 2,
    "n": 2,
    "rate": 1.0,
    "ci_low": 0.34237195288961925,
    "ci_high": 1.0
  }
}

## Anatomy (primary failures)

- `HYPOTHESIS_FAILURE`: 1
- `RETRIEVAL_FAILURE`: 1

## Claims

| Claim | Evidence | Scope | Limitation | Status |
| --- | --- | --- | --- | --- |
| C4-oracle-ceiling-known | OracleRescueCeiling k=2 n=2 | sanity fixture FastWrong | gold uses document.hypothesis_ids; not a human adjudication | demonstrada |
| C5-non-oracle-rescue | Rescue count=1 on best predicted arm=falsification (pairwise disc=0) | sanity 120 queries, clustered by intent_id | small catalog; lexical discrimination only | demonstrada |
| C5-net-utility | NetRescueRate=0.0; DeltaU=-0.03991666666666664; CI={'point': -0.03991666666666664, 'ci_low': -0.0935520833333333, 'ci_high': 0.018187499999999926, 'n_clusters': 40, 'samples': 400, 'n_successful_draws': 400} | same confirmatory fixture | utility uses pre-registered costs, not production money | não demonstrada |
| C6-policy-neu | default v0.1.1 policy unchanged; Cycle 6 blocked unless Cycle 5 net-utility PASS | operational policy | no silent policy promotion | ainda não testada |
| A1-wdi-rescue-zero | {'source': 'experiments/results/milestone_a1/metrics.json', 'n_matched': 3116, 'RescueRate': 0.0, 'BothWrongRate': 0.35397946084724, 'BothWrong_count': 1103, 'note': 'Preserved historical WDI/A1 observation. Prompt cited ~153/400; this artifact differs and is not overwritten.'} | historical WDI A1 matched table | not re-run in this cycle; preserved artifact | demonstrada |

## Stop / next falsifiable test

Rescue exists but NetRescueRate or ΔU is non-positive (overthinking/cost). Next falsifiable test: recoverability-gated EXPLORE on holdout, not always-explore.

QUASAR2 remains research software. Negative and blocked gates are retained.
