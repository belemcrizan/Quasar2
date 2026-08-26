# Milestone A1 — RESCUE / OVERTHINKING decomposition

Hypothesis: additional QUASAR compute is not uniformly helpful. Matched FAST vs
QUASAR labels identify where deliberation rescues FAST and where it overthinks.

Claim **C1 remains INCONCLUSIVE**. This analysis is exploratory. Feature
associations are not causal. Threshold proposals are calibration-only candidates
for PHASE A2. `sealed_test` is never used for ranking or fitting.

## Reproduce

```text
quasar2 repository-audit --output experiments/results/repository_state

quasar2 a1-decompose ^
  --run-dir experiments/results/gate_pilot_bm25 ^
  --run-dir experiments/results/v24_r2_ci_bm25_minilm ^
  --benchmark data/wdi/benchmarks/pilot.json ^
  --output experiments/results/milestone_a1
```

Required artifacts live under `experiments/results/milestone_a1/`.

## Scientific answers for this phase

| Question | Answer |
|---|---|
| Hypothesis | C1: selective compute can beat always-on reasoning on risk × compute. A1 tests the descriptive decomposition, not C1 itself. |
| Failure | OVERTHINKING vs RESCUE vs BOTH_WRONG |
| Cost | Offline join of existing artifacts; no extra retrieval unless features were missing |
| Metric that improves | Explainability of matched outcomes; candidate gate features |
| Metric that may worsen | Apparent QUASAR quality once overthinking is visible |
| When not to use | Do not use these associations as a production gate |
| Ablation | FAST_ONLY vs QUASAR_ALWAYS vs optional GATED |
| Generalize | Unknown; neural full-pilot is BLOCKED_RESOURCE_LIMIT |
| Pareto | Not claimed; rates only |

## Blocked

A matched 3,036-query neural FAST/QUASAR pilot does not exist. CI neural
`top1`/`v24` (n=40, different snapshot) is decomposed separately when that run
directory is supplied. Dense hashing is not used as a neural substitute.

## Observed rates (exploratory, not sealed)

BM25 WDI pilot (`n=3036`, snapshot `wdi-pilot-2026-08-26-b6ddb672`):

| Rate | Value | 95% CI |
|---|---:|---|
| OverthinkingRate | 0.1176 | [0.1061, 0.1291] |
| RescueRate | 0.0000 | [0.0000, 0.0000] |
| BothCorrectRate | 0.5254 | |
| BothWrongRate | 0.3570 | |

QUASAR never corrected a FAST error on intent_exact in this matched table
(`BeneficialReasoningRate = 0`). That is a preserved negative result, not a C1
confirmation.

Neural CI (`n=40`): RescueRate = OverthinkingRate = 0. Full-pilot neural remains
`BLOCKED_RESOURCE_LIMIT`.
