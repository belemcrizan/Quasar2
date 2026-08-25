# Changelog

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
