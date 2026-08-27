# AERA Cycle 8 report

schema: aera.1 · git: 37e18c92e02595e0124a4ad4a2b55a5175311663 · python: 3.13.3

Frozen v0.1.1 loop was not modified. Cycle 4 artifacts were not overwritten.

## Historical Cycle 4 (preserved)

{
  "available": true,
  "n_queries": 120,
  "non_oracle_rescue_count": 1,
  "gates": {
    "cycle4_anatomy": "PASS",
    "cycle5_non_oracle_rescue": "PASS",
    "cycle5_net_utility": "FAIL",
    "cycle6_policy": "BLOCKED",
    "cycle7a_analyze_ask_defer": "TESTED",
    "leakage_contract": "PASS"
  }
}

## Engine smoke

n=8 Rescue=0 Overthinking=0 meanΔU=-0.01

Smoke on 8 intents (q1 only). Not a replacement for the 120-query Cycle 4 confirmatory table.

## Gates

- `R0_ceiling_known`: **PASS**
- `R3_non_oracle_rescue_historical`: **PASS**
- `R4_net_rescue_historical`: **FAIL**
- `R5_delta_u_historical`: **FAIL**
- `marketplace_executes`: **PASS**
- `verify_independent`: **PASS**
- `analyze_no_retrieval`: **PASS**
- `fleet_budget_cap`: **PASS**
- `planner_vs_onestep`: **REFUTED_IN_TESTED_REGIME**
- `ssrf_default`: **PASS**
- `cycle6_product_policy`: **BLOCKED_BY_GATE**
- `external_official_dumps`: **REFUTED_IN_TESTED_REGIME**
- `neural_cross_encoder_full`: **NOT_STARTED_WITH_REASON**

## Allowed claims

- VERIFY can run against an independent structured source with zero retrieval calls.
- Selected marketplace action is executed on the experimental pipeline.
- Fleet allocators respect a global cap in simulation.
- Discovery mode can prefer a high-discrimination cheap observation over a high-relevance one.

## Forbidden claims

- Product policy improved (Cycle 6 remains BLOCKED).
- ΔNEU>0 on the 120-query confirmatory fixture (historical FAIL).
- NASA/ESA/ALMA official dumps (schema-faithful only).
- Neural CrossEncoder full protocol without extras.
- Online bandit on consequential decisions.

Reproduce: `python -m quasar2.cli aera-evaluate --output experiments/results/aera_c8 --overwrite --limit 8 --seed 42`

