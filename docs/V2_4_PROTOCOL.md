# QUASAR2 V2.4 protocol

**Status:** developmental (R0–R3 executed). Not a sealed test.  
**Access date for primary references:** 2026-08-26  
**Supersedes:** V2.3 Phase-A-only planning. V2.3 remains historical.

## Question

Does adaptive epistemic action selection improve intent recovery, commitment risk, coverage, and information efficiency on frozen World Bank WDI data when compared with strong retrieval and simple selective baselines?

## Tracks

- P: five-action policy (`ANSWER|ANALYZE|EXPLORE|ASK|DEFER`) beside the frozen v0.1.1 loop
- W: WDI API V2 source 2 snapshot-first evidence
- N: genuine neural profiles (MiniLM smoke, E5, BGE-M3) vs hashing debug control
- B: QUASAR-Bench-WDI staged generation
- E: crossed retriever × policy evaluation

## Primary contrasts (pre-registered for later sealed test)

1. V2.4 policy vs top-1, same retriever, paired by canonical intent  
2. V2.4 vs uncertainty threshold, same retriever  
3. Discriminative EXPLORE vs ordinary retrieve-more (R4+)  
4. BGE-M3 vs BM25 evidence recall (R2+/R5)  
5. Open-set DEFER vs always-answer on unsupported queries  

Non-inferiority on clear D0 English queries: intent exact within 0.03 of the strongest single-shot backend, coverage not below that backend minus 0.05.

Holm correction applies to this family only after R6 authorization.

## Cost scenarios (frozen coefficients, not claimed optimal)

Low / medium / high risk weights: λ_r ∈ {0.4, 0.9, 1.6}. Current code uses medium (`PolicyConfig.lambda_risk=0.90`).

## Promotion rule

See the V2.4 master prompt §23. R6 is **not** authorized by this document.

## Isolation rule

Do not overwrite `experiments/results/benchmark.json` (v0.1.1 sanity table) or mutate a COMPLETE WDI snapshot.
