# Cycle 4–7A — from deliberation without rescue to measured recoverability

**Status:** mechanism implemented and measured. Frozen v0.1.1 loop unchanged. Package remains **0.2.0**.

**Primary question:** Can additional information actually rescue a decision?

**Confirmatory fixture:** 120-query sanity catalog (`configs/poc.yaml`), clustered by `intent_id`. Not WDI.

**Reproduce:**

```text
$env:PYTHONPATH = "src"
python -m quasar2.cli validate
python -m pytest tests/test_rescue_cycle.py tests/test_pipeline.py -q
python -m quasar2.cli rescue-cycle --output experiments/results/cycle4_rescue --overwrite --seed 42
```

Use `PYTHONPATH=src` if an older `quasar2` console script shadows this tree.

Canonical run artifacts: `experiments/results/cycle4_rescue/` (`REPORT.md`, `anatomy.jsonl`, `run_manifest.json`).

This document does not replace `REPORT.md`. Numbers below match that run.

## Historical starting point (preserved, not re-coded)

| Source | Observation | Divergence vs prompt memory |
|---|---|---|
| A1 `experiments/results/milestone_a1/metrics.json` | RescueRate = 0, BothWrong = 1103 / 3116 (0.354) | Prompt cited ~153/400 BothWrong. The checked-in A1 table is larger and is **not overwritten**. |
| Gate 1 | FAIL (locked) | Unchanged |
| Frozen v0.1.1 Full−noExplore ARR | +0.05 on intent recovery in the frozen JSON | Availability ≠ Rescue under the costed utility used here |
| This cycle, sanity Fast vs Full | FastWrong = **2 / 120**; Full Rescue = **0 / 2** | Easy fixture: Fast is already correct on 118/120 |

## Gates

| Gate | Status | Meaning |
|---|---|---|
| Cycle 4 anatomy | **PASS** | 2/2 FastWrong classified; INDETERMINATE = 0 |
| Cycle 5 NonOracleRescueCount > 0 | **PASS** | Falsification arm: 1 rescue (`astro-03:q1`) |
| Cycle 5 NetRescueRate > 0 and ΔU > 0 | **FAIL** | Best arm NetRescueRate = 0; ΔU = −0.040 (cluster CI includes 0 on the high side, mean negative) |
| Cycle 6 policy / ΔNEU | **BLOCKED** | Default policy not rewritten |
| Cycle 7A ANALYZE/ASK/DEFER | **TESTED** | Diagnostic only |
| Leakage contract | **PASS** | Predicted path rejects gold inputs |

## Anatomy of the two FastWrong cases

| query_id | Fast prediction | H* | Primary failure | Oracle hyp | Oracle retrieval | Falsification (predicted) |
|---|---|---|---|---|---|---|
| `astro-02:q1` | brown_dwarf_atmosphere | stellar_flare (not in top-4) | `HYPOTHESIS_FAILURE` | true | false | false |
| `astro-03:q1` | cepheid_variable | microlensing (in top-4) | `RETRIEVAL_FAILURE` | false | true | **true** |

OracleRescueCeiling = 2/2 (Wilson CI [0.34, 1.00]). Ceiling is high; the live pairwise disc arm still rescued **zero**. The single non-oracle rescue is **falsification retrieval**, not the frozen Full loop.

## Claims allowed vs forbidden

Allowed: the chain *can* break at hypothesis generation or at retrieval; falsification queries can rescue one catalog error; extra always-on acquisition has negative mean ΔU on this easy fixture; WDI A1 Rescue remains 0 in the historical table.

Forbidden: QUASAR2 is operationally superior; EXPLORE should be the default policy; recoverability v2 is calibrated (holdout positives = 0, AUROC undefined); A1 153/400 is the current N; ANALYZE improves decisions (0/12 prediction changes).

## Next falsifiable test

Do **not** promote a new default policy.

Target **recoverability-gated falsification EXPLORE** only on pre-action states that look like FastWrong (high entropy, H* possibly missing from top-k). Hold out intents. Success criterion remains NetRescueRate > 0 **and** ΔU > 0. Separately, raise hypothesis-generation recall so `astro.stellar_flare` enters the candidate set for `astro-02:q1` without using gold.
