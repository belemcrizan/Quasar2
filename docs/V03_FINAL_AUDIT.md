# v03 delivery audit

The implementation is an experimental substrate, not fulfillment of every item in
the proposed research program. Scores below are engineering judgment (0–5), not
empirical measurements; no dimension is assigned a perfect score.

| Dimension | Score | Evidence / remaining gap |
|---|---:|---|
| Baseline preservation | 4 | 92 locally available historical files hashed; remote history preserved |
| Utility contracts | 4 | Explicit costs/actions, monotonic trajectories; ASK not evaluated |
| Preregistration | 3 | Locked design; exploratory runs, not independent registration |
| Runtime/gold boundary | 4 | Immutable allowlist and tests; semantic leakage not certified |
| Split integrity | 3 | Groups/queries audited; transfer experiments missing |
| R* models | 3 | Logistic/calibration/stump/ablations; only simple proxies tested |
| Budget comparisons | 3 | Exact retrieval count; no full compute matching |
| Statistical reporting | 3 | Cluster intervals/calibration; power and multi-dataset claims unresolved |
| External data | 2 | NASA/INSPIRE bounded real snapshots; BEIR download failed |
| Query validity | 1 | Generated queries only; native external evaluation missing |
| Human evidence | 1 | Schema and agreement code; no annotations |
| Agent evidence | 1 | Execution ledger fixture; no live model benchmark |
| Reproducibility | 3 | Frozen inputs/full run archives/offline commands; Docker not run |
| Scale | 1 | Small datasets; no meaningful large-scale characterization |
| Release readiness | 1 | Version remains 0.2.0; v03 scientific release blocked |

## Unfinished work and concrete blockers

- SciFact/NFCorpus: attempted remote downloads failed with URL errors. FiQA and
  TREC-COVID: NOT_RUN. Source adapters and explicit acquisition commands exist.
- Native external confirmation, WDI-Hard full tuple families, cross-domain,
  retriever and cost transfer: NOT_IMPLEMENTED in this PR. Existing WDI hardening
  remains intact but is not relabeled as these new experiments.
- Human annotation/adjudication: NOT_RUN; requires actual independent annotators.
- Strong neural/reranker runs and live LLM/RAG: NOT_RUN; no model artifacts or
  provider execution were supplied. The ledger is not a completed agent framework.
- Scale, Docker execution and paper/manuscript release: NOT_RUN. No container
  executable was available; no Docker-success claim or version bump is made.
- Runtime cockpit integration and publication figure suite: NOT_IMPLEMENTED;
  only a directly data-driven diagnostic comparison figure is included.

These gaps remain visible instead of assigning unsupported scientific claims.
The PR can be reviewed as an engineering increment; accepting it does not accept
an empirical claim that R* generalizes or authorize publishing v0.3 as validated.

Publication verification: 36 local hydration files did not match upstream Git blob hashes. They are explicitly excluded from the local freeze set; their authoritative upstream blobs remain unchanged. The remaining 92 frozen files match upstream bytes.
