# Changelog

## Unreleased

- Added V2.4 WDI snapshot sync, five-action policy path, neural profiles (E5, BGE-M3, MiniLM), and a 600-intent WDI pilot. Historical v0.1.1 sanity results are unchanged.
- Added M0 repository audit (`docs/V2_REPOSITORY_AUDIT.md`) and a frozen copy of the v0.1.1 sanity benchmark artifacts under `experiments/results/frozen/v0.1.1/`. No inference-loop or metric change.

## 0.2.0 — 2026-08-25

- Froze the v0.1.1 inference loop as the experimental treatment.
- Demoted the 80-document astronomy/AI set to a sanity / CI mechanism test.
- Added a matched retriever factory: BM25, hashing dense (debug), hybrid, optional neural.
- Added an isolated ops-runbook fixture (overlapping incident classes).
- Added a factorial regime experiment \(Q=(A,L,P,U,D)\) with a sampled design.
- Added `full+R` methods so \(\Delta_{loop}\) is estimated on the same backend \(R\).
- Report ranking recall, evidence recall, and interpretation quality separately.
- Report a severity-bin crossover table; do not fit an adaptive \(\tau\) on the same run.
- Deferred \(H_{unknown}\), DEFER, and receding-horizon policy to v0.3.

## 0.1.1 — 2026-08-25


- Added stable SHA-256 identities for every hypothesis-conditioned retrieval query.
- Added a pre-retrieval gate that rejects repeated exploration queries.
- Added a zero-novel-evidence gate that prevents a further acquisition round.
- Added per-step document novelty, belief total variation, and observed entropy
  reduction to structured traces.
- Added avoided-call, pruning, and termination-reason fields to pipeline and
  benchmark telemetry.
- Added regression tests proving that pruning preserves the canonical demo's
  final action and predicted hypothesis while reducing retrieval calls.
- Froze the v0.2 experimental protocol with separate policy, calibration, and
  blind-test boundaries.

## 0.1.0 — 2026-08-25

- Implemented the frozen observation/hypothesis/evidence/belief/decision loop.
- Added offline Mode A and a typed Mode-B boundary.
- Added BM25, hashing-vector, hybrid, and single-rewrite baselines.
- Added five pipeline variants and a 120-query canonical benchmark.
- Added evidence deduplication, full trace serialization, paired bootstrap
  comparison, validation, tests, and scientific documentation.
