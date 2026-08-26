# Milestone A — selective compute (current cycle)

Hypothesis **C1**: Selective reasoning is more compute-efficient than universal reasoning.

This cycle adds a cheap deterministic complexity gate, stage latency telemetry, and a matched comparison:

| Method | Policy names | Behavior |
|---|---|---|
| FAST_ONLY | `fast_only` (alias of top-1 commit) | One retrieval, then ANSWER |
| QUASAR_ALWAYS | `quasar_always` (alias of `v24`) | Existing V2.4 deliberation |
| GATED_QUASAR | `gated_quasar` | Probe retrieval → FAST / QUASAR / DEFER_EARLY |

C1 is **not** supported until a preregistered sealed WDI run with frozen margins exists. Current artifacts are labeled `INCONCLUSIVE` / exploratory.

Executed BM25 pilot (`n=3036`, snapshot `wdi-pilot-2026-08-26-b6ddb672`, local hardware, not sealed):

| Policy | intent_exact | wrong_answer_rate | coverage | mean retrieval | compute proxy | P50/P95/P99 ms |
|---|---:|---:|---:|---:|---:|---|
| FAST_ONLY (`fast_only`) | 0.643 | 0.357 | 1.000 | 1.00 | 1.10 | 1.17 / 1.85 / 2.40 |
| QUASAR_ALWAYS (`quasar_always`) | 0.525 | 0.323 | 0.776 | 2.91 | 3.54 | 1.82 / 3.08 / 4.15 |
| GATED_QUASAR | 0.531 | 0.320 | 0.782 | 2.78 | 3.37 | 1.82 / 2.93 / 3.73 |

`fast_only` matches frozen V2.4 `top1` intent_exact (0.642951). `quasar_always` matches frozen `v24` (0.525362). GATED vs ALWAYS: paired intent_exact Δ +0.0059, 95% CI [0.0033, 0.0089]; compute_proxy Δ −0.165, 95% CI [−0.187, −0.144]. GATED vs FAST: intent_exact Δ −0.112, CI [−0.123, −0.100]. Exploratory only. FAST remains stronger on intent exact at lower compute.

## Reproduce

Offline CI smoke:

```text
quasar2 gate-experiment --snapshot <offline-or-ci-snapshot> --stage ci --output experiments/results/gate_ci --limit 24
```

Preserved 3,036-query pilot (historical semantics unchanged; new policies are additional):

```text
quasar2 gate-experiment --snapshot data/wdi/snapshots/pilot-live --stage pilot --backends bm25 --output experiments/results/gate_pilot_bm25
```

Matched historical V2.4 policies remain:

```text
quasar2 wdi-experiment --snapshot data/wdi/snapshots/pilot-live --stage pilot --backends bm25 --policies top1,threshold,v24 --output experiments/results/v24_r3_pilot_bm25_rerun
```

Do not overwrite frozen files under `experiments/results/frozen/`.

## What this cycle does not claim

- JWST/CERN metadata fixtures are **not** completed scientific benchmarks.
- Neural full-pilot numbers are not invented if models are unavailable.
- Cost figures are compute proxies unless calibrated hardware accounting is attached.
