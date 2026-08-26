# QUASAR-Bench-WDI

Generator: `quasar2.benchmarks.wdi_bench.build_benchmark`  
Artifacts: `data/wdi/benchmarks/ci.json`, `data/wdi/benchmarks/pilot.json`

## Pilot scale (this run)

- 600 canonical intents (30 indicators × 20 countries)
- 3036 query instances (D0/D2/D3/D5/PT + some entity counterfactuals + open-set)
- Split: SHA-256 of canonical id → development / calibration / validation / sealed_test buckets; **all variants of one canonical stay together**

## Policy isolation

Instances store hidden `acceptable_intents` and `expected_observation`. `BenchInstance.policy_query()` exposes only `query_text` and `language`. Automated tests reject forbidden fields on `PolicyState`.

## Natural set

The 300-question independently authored natural set is **not** in this developmental dump. Open-set items are template near-domain negatives. Human annotation protocol: `docs/AMBIGUITY_ANNOTATION_GUIDE.md`.
