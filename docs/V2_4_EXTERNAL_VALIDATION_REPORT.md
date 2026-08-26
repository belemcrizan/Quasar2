# V2.4 external validation report (developmental)

**Run date:** 2026-08-26  
**Sealed test:** not executed  
**Promotion:** REVISE (see claim ledger)

## Dataset / snapshot

| Snapshot | ID | Indicators | Country entities | Observations | Observed / missing |
|---|---|---:|---:|---:|---|
| CI live | `wdi-ci-2026-08-26-6ead85fe` | 12 | 8 + LCN | 1152 | 981 / 171 |
| Pilot live | `wdi-pilot-2026-08-26-b6ddb672` | 30 | 20 + aggregate | 15120 | 12889 / 2231 |

Source 2, API v2. Offline after sync. Attribution in each snapshot `LICENSE_AND_ATTRIBUTION.md`.

## Neural environment

Python 3.13.3, torch 2.13.0+cpu, sentence-transformers 6.0.0, no CUDA.

- MiniLM: WDI metadata retrieval smoke OK  
- E5: `ind:NY.GDP.PCAP.CD` ranked first for “GDP per capita Brazil” (score 0.857)  
- BGE-M3: EN top hit `ent:BRA` then GDP per capita; PT top hit `ind:NY.GDP.PCAP.CD`  
- Hashing is debug-only  
- Reranker class exists; N4 full run **not** executed (CPU CrossEncoder over 3036 queries × candidate pool is the cost bottleneck)

## Retriever × policy (pilot BM25, n=3036)

From `experiments/results/v24_r3_pilot_bm25/metrics.json`:

| Method | Intent exact | WAR among ANSWER | Coverage | ASK | DEFER | Calls |
|---|---:|---:|---:|---:|---:|---:|
| BM25 top-1 | 0.643 | 0.357 | 1.000 | 0 | 0 | 1.00 |
| BM25 threshold | 0.146 | 0.594 | 0.360 | 0 | 0.640 | 1.00 |
| BM25 V2.4 | 0.525 | 0.323 | 0.776 | 0 | 0.224 | 2.91 |

CI MiniLM smoke n=40: BM25 top-1 0.775 vs MiniLM top-1 0.750 intent exact.

## Negative / mixed findings (first-class)

- On this BM25 WDI pilot, **top-1 beats V2.4 on intent exact** and uses fewer calls. V2.4’s WAR is only modestly lower with lower coverage. H10 (simplicity challenge) is **not rejected**.
- ASK never fired in these runs (rate 0). Structured clarification is implemented but unused by the current utility coefficients.
- MiniLM Portuguese “acesso a eletricidade” did not rank the electricity indicator first.
- Full E5/BGE-M3 × all policies on 3036 instances was not run (index+query cost on CPU).
- Clustered confidence intervals were not computed in R3.
- Frozen v0.1.1 astronomy/AI table is unchanged and still shows Full 0.975 vs Hybrid 0.983 IRR (CI includes 0).

## Representative traces

Deterministic selection rule: first CI live query for Brazil GDP-style D0, first open-set instance, first missingness instance in the generator. Traces live inside pipeline JSON for individual `V24Result.trace` (not exported as jsonl in this run — limitation).

## Promotion decision

**REVISE.** Real WDI + neural encoding work. The policy does not yet justify itself against top-1 BM25 on the pilot. Next causal repair: make ASK/ANALYZE fire on user-resolvable and multi-indicator cases, then recross with BGE-M3 hybrid under a call-matched budget.
