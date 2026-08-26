# Rescue / overthinking report (PHASE A1)

Status: **EXPLORATORY**. Not a sealed confirmatory claim.

Hypothesis tested: additional QUASAR compute is not uniformly helpful;
matched FAST vs QUASAR labels identify rescue and overthinking regions.

Generated: `2026-08-26T13:00:29+00:00`

## Rates

### `bm25|wdi-ci-2026-08-26-6ead85fe|ALL`

- n = 40
- OverthinkingRate = 0.0000 (CI 0.0000, 0.0000)
- RescueRate = 0.0000 (CI 0.0000, 0.0000)
- BothCorrectRate = 0.7750
- BothWrongRate = 0.2250
- BeneficialReasoningRate = P(RESCUE | FAST wrong) = 0.0000
- snapshots = ['wdi-ci-2026-08-26-6ead85fe']

### `bm25|wdi-pilot-2026-08-26-b6ddb672|ALL`

- n = 3036
- OverthinkingRate = 0.1176 (CI 0.1061, 0.1291)
- RescueRate = 0.0000 (CI 0.0000, 0.0000)
- BothCorrectRate = 0.5254
- BothWrongRate = 0.3570
- BeneficialReasoningRate = P(RESCUE | FAST wrong) = 0.0000
- snapshots = ['wdi-pilot-2026-08-26-b6ddb672']

### `neural|wdi-ci-2026-08-26-6ead85fe|ALL`

- n = 40
- OverthinkingRate = 0.0000 (CI 0.0000, 0.0000)
- RescueRate = 0.0000 (CI 0.0000, 0.0000)
- BothCorrectRate = 0.7500
- BothWrongRate = 0.2500
- BeneficialReasoningRate = P(RESCUE | FAST wrong) = 0.0000
- snapshots = ['wdi-ci-2026-08-26-6ead85fe']

## Blocked backends

- `neural_pilot`: BLOCKED_RESOURCE_LIMIT: neural matched rows are not the 3036-query WDI pilot. CI-scale neural decomposition is recorded separately.

## Candidate features (calibration+development, not causal)

### bm25|wdi-ci-2026-08-26-6ead85fe

**RESCUE**

- none with both arms populated

**OVERTHINKING**

- none with both arms populated

### bm25|wdi-pilot-2026-08-26-b6ddb672

**RESCUE**

- none with both arms populated

**OVERTHINKING**

- `missingness`: Δ=0.1653, d=0.955, CI [0.1517, 0.1797]
- `complexity_score`: Δ=-0.1079, d=-0.621, CI [-0.1241, -0.0903]
- `hypothesis_disagreement`: Δ=-0.0073, d=-0.515, CI [-0.0086, -0.0061]
- `unknown_score`: Δ=-0.0136, d=-0.439, CI [-0.0165, -0.0107]
- `latency_ms`: Δ=0.1196, d=0.325, CI [0.0732, 0.1713]
- `ambiguity_score`: Δ=-0.0331, d=-0.236, CI [-0.0495, -0.0172]
- `open_set_score`: Δ=-0.0026, d=-0.073, CI [-0.0053, -0.0005]
- `retrieval_calls`: Δ=0.0000, d=0.000, CI [0.0000, 0.0000]

### neural|wdi-ci-2026-08-26-6ead85fe

**RESCUE**

- none with both arms populated

**OVERTHINKING**

- none with both arms populated

## Proposed A2 gate (calibration only)

Do not treat these numbers as fitted production thresholds.

```json
{
  "bm25|wdi-ci-2026-08-26-6ead85fe": {
    "n_calibration": 10,
    "n_rescue": 0,
    "n_overthinking": 0,
    "n_both_correct": 8,
    "suggested_fast_if": {
      "ambiguity_score_max": 0.6,
      "complexity_score_max": 0.5675,
      "missingness_max": 0.175,
      "note": "Escalate toward QUASAR when ambiguity/complexity exceed BOTH_CORRECT medians."
    },
    "suggested_quasar_if": {
      "ambiguity_score_min": null,
      "unknown_score_min": null,
      "missingness_min": null
    },
    "overthinking_profile": {
      "ambiguity_median": null,
      "complexity_median": null,
      "unknown_median": null
    },
    "model_family_next": [
      "logistic_regression",
      "decision_tree"
    ],
    "do_not_fit_on": [
      "sealed_test"
    ],
    "status": "EXPLORATORY_CANDIDATE",
    "claim": "Not a fitted gate. Calibration-only descriptive thresholds for PHASE A2."
  },
  "bm25|wdi-pilot-2026-08-26-b6ddb672": {
    "n_calibration": 591,
    "n_rescue": 0,
    "n_overthinking": 91,
    "n_both_correct": 302,
    "suggested_fast_if": {
      "ambiguity_score_max": 0.6526055,
      "complexity_score_max": 0.220103,
      "missingness_max": 0.0,
      "note": "Escalate toward QUASAR when ambiguity/complexity exceed BOTH_CORRECT medians."
    },
    "suggested_quasar_if": {
      "ambiguity_score_min": null,
      "unknown_score_min": null,
      "missingness_min": null
    },
    "overthinking_profile": {
      "ambiguity_median": 0.663941,
      "complexity_median": 0.244204,
      "unknown_median": 0.05479452054794521
    },
    "model_family_next": [
      "logistic_regression",
      "decision_tree"
    ],
    "do_not_fit_on": [
      "sealed_test"
    ],
    "status": "EXPLORATORY_CANDIDATE",
    "claim": "Not a fitted gate. Calibration-only descriptive thresholds for PHASE A2."
  },
  "neural|wdi-ci-2026-08-26-6ead85fe": {
    "n_calibration": 10,
    "n_rescue": 0,
    "n_overthinking": 0,
    "n_both_correct": 7,
    "suggested_fast_if": {
      "ambiguity_score_max": 0.6,
      "complexity_score_max": 0.5675,
      "missingness_max": 0.0,
      "note": "Escalate toward QUASAR when ambiguity/complexity exceed BOTH_CORRECT medians."
    },
    "suggested_quasar_if": {
      "ambiguity_score_min": null,
      "unknown_score_min": null,
      "missingness_min": null
    },
    "overthinking_profile": {
      "ambiguity_median": null,
      "complexity_median": null,
      "unknown_median": null
    },
    "model_family_next": [
      "logistic_regression",
      "decision_tree"
    ],
    "do_not_fit_on": [
      "sealed_test"
    ],
    "status": "EXPLORATORY_CANDIDATE",
    "claim": "Not a fitted gate. Calibration-only descriptive thresholds for PHASE A2."
  }
}
```

## What this does not claim

- Associations are not causal component effects.
- C1 remains INCONCLUSIVE until a preregistered sealed run.
- Neural full-pilot FAST/QUASAR matching is not invented if absent.
