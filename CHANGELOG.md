# Changelog

## Unreleased

- Cycle 8 AERA: epistemic action marketplace with robust Q, independent structured VERIFY (zero retrieval), ASK question selection, provenance graph that downweights duplicates, receding-horizon d=2 vs greedy on a heuristic twin, Recoverability 3.0 per-action (in-sample), fleet global-budget simulator, EROI/MVC/equal-budget accounting, offline IPS/DR (online disabled), scientific discovery replay, security URL/secret guards. CLI: `aera-evaluate`, `planner-evaluate`, `bandit-replay`, `fleet-simulate`, `audit`. API: `/v1/decision`, `/v1/plan`, `/v1/verify`, `/v1/fleet`. Frozen v0.1.1 and Cycle 4 confirmatory table unchanged. Cycle 6 remains BLOCKED (historical NetRescueRate=0, ΔU<0). NASA/ESA/ALMA remain SCHEMA_FAITHFUL.

- Cycle 4–7A plus observability: canonical `trace.runtime|evaluation|oracle` split, experimental action contract (`policy-evaluate` fails if selected≠executed), stdlib Research Cockpit/API (`quasar2 serve`), Docker non-root image, local load probe. Frozen v0.1.1 unchanged. Cycle 6 policy remains BLOCKED (NetRescueRate and ΔU not positive). Neural CrossEncoder full protocol remains NOT_RUN without extras. NASA/ESA/ALMA remain SCHEMA_FAITHFUL, not confirmatory TAP dumps.

- Cycle 4–7A rescue chain (`quasar2 rescue-cycle` and aliases): Evidence Oracle, causal-order error anatomy, predicted vs oracle discriminative acquisition, recoverability-v2 pre-action features, ANALYZE/ASK/DEFER diagnostics. Frozen v0.1.1 loop unchanged. On the 120-query sanity fixture FastWrong=2/120, OracleRescueCeiling=2/2, falsification Rescue=1/2, NetRescueRate=0 and ΔU<0 so Cycle 6 policy is BLOCKED. Historical WDI A1 Rescue=0 is preserved (n_matched=3116, not the ~400 cited in some notes).

- Cycle 3 external-validity program (`quasar2 external-validity`, `quasar2 reproduce-paper`): official NASA/ESA/observatory source audit, schema-faithful snapshots (not live TAP dumps), clustered transfer/scale/equal-budget/regime maps, Dockerfile. Frozen v0.1.1, Gate 1 FAIL, and Cycle 2 negative results are unchanged. No claim promoted to SUPPORTED_IN_SCOPE.

- Cycle 2 scientific path (`quasar2 cycle2-audit`): recoverability state, mismatch/corruption tests, empirical action values (T2 is not Q), family-holdout synthetic oracle, WDI controlled-degradation card, OPS sequential/fault simulator. Frozen v0.1.1 and Gate 1 FAIL are unchanged. Recoverability remains diagnostic (G-R FAIL; Gate 1 locked). Equal-budget OPS: BM25 top-1/ANSWER matched the entropy policy and beat forced extra retrieval.

- Added a synthetic recoverability-vs-VoI benchmark, Decision Recoverability Score, optional learned recoverability estimator, T2 tightness labels, T4 near-zero stress, tabular oracle / SPRT-inspired / learned shadow policies, and `shadow-study` / `policy-compare` CLIs. The v0.1.1 executed loop is unchanged. Frozen sanity JSON is not overwritten by these commands.
- Added V2 math utilities, recoverability estimators, ANALYZE operators, theorem harness T1–T4/C1, and optional `--v2-shadow` telemetry. The v0.1.1 loop is unchanged unless shadow mode is enabled, and even then only diagnostics are added.
- Added MyopicVoIPolicy and ThresholdPolicy as **shadow recommenders**, proxy recoverability from evidence support, `quasar2 phase-diagram`, and a non-overwriting `experiments/runs/` registry. Executed legacy actions are unchanged.

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
