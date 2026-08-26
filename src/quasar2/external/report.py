"""48-section external-validity report plus final A–H answers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _j(value: object) -> str:
    return json.dumps(value, indent=2, default=str)


def write_report(dest: Path, payload: Mapping[str, Any]) -> Path:
    a = payload["answers"]
    selected = _j(
        [
            {"source": r["source"], "recommendation": r["recommendation"], "rationale": r["rationale"]}
            for r in payload.get("selected_sources") or ()
        ]
    )
    rejected = _j(
        [{"source": r["source"], "rationale": r["rationale"]} for r in payload.get("rejected_sources") or ()]
    )
    md = f"""# QUASAR2 — External validity, scale, replication, and regime discovery

schema_version: {payload.get("schema_version")}
run_id: {payload.get("run_id")}
git_sha: {payload.get("git_sha")}
seed: {payload.get("seed")}
snapshot_id: {payload.get("snapshot_id")}
timestamp: {payload.get("timestamp")}
smoke: {payload.get("smoke")}
policy_stage: SHADOW
gate1: FAIL (locked)
T2_is_not_Q: true
live_official_dump: false

This cycle does **not** replace the frozen v0.1.1 loop, does not retune Gate 1, and does not promote the experimental policy.

Negative results remain visible. Schema-faithful snapshots are **not** live NASA/ESA TAP dumps.

---

## 1. Repository Audit

Preserved: frozen v0.1.1 sanity table; Gate 1 FAIL; Cycle 2 recoverability/action-value path; WDI snapshots; OPS fixture; BM25/hybrid/hashing; V2.4 WDI policy; JWST/CERN/INSPIRE metadata fixtures; claim ledger.

Added: `src/quasar2/external/` source audit, schema snapshots, leakage tests, scale/budget/regime/transfer, `external-validity` and `reproduce-paper` CLI, Dockerfile.

Not modified: `experiments/results/frozen/v0.1.1/`.

---

## 2. Existing Evidence Preserved

- Gate 1 FAIL: deployment-observable recoverability did not add stable incremental value beyond uncertainty.
- Recoverability is a matched-kernel mechanism variable more than a deployment router.
- T2 bound is not Q(s, EXPLORE).
- Experimental policy remains shadow.
- Entropy, BM25, and Hybrid remain serious baselines.
- Extra retrieval can reduce utility (sanity FULL vs noExplore; Cycle 2 OPS equal-budget).
- Anti-QUASAR regimes remain in Cycle 2 families.
- Synthetic evidence is already strong; deployment-like evidence remains limited.

---

## 3. External Source Audit

Counts: `{_j(payload.get("source_audit_counts"))}`

Full table: `source_audit.json` in this artifact directory.

---

## 4. NASA Source Assessment

HIGH_PRIORITY selected: NASA Exoplanet Archive TAP schema (KOI/TOI dispositions) and MAST metadata (in-repo JWST fixture).

ADS: USEFUL, not selected (token; abstracts ≠ claims).

HEASARC / IRSA: USEFUL, deferred to keep 2–3 sources.

Image of the Day: NOT_SUITABLE.

**This run did not fetch TAP.** Records are `SCHEMA_FAITHFUL_SYNTHETIC` with `SYN-` ids, plus official fixture overlay for JWST.

---

## 5. ESA Source Assessment

HIGH_PRIORITY selected: Gaia Archive TAP schema (single vs binary vs spurious).

XMM-Newton: USEFUL, not selected in the first trio.

**Not a live Gaia dump.**

---

## 6. Observatory Source Assessment

HIGH_PRIORITY selected: ALMA Science Archive schema (disk/envelope/outflow/artifact).

ESO SAF: USEFUL; ALMA chosen as the first independent observatory family because metadata-scale ambiguity is closer to the scientific question.

---

## 7. Selected Sources and Rationale

`{selected}`

---

## 8. Rejected Sources and Rationale

`{rejected}`

---

## 9. Data Provenance

snapshot_id: `{payload.get("snapshot_id")}`

manifests: `{_j(payload.get("snapshots"))}`

Every derived state carries `source_record_id`, archive, timestamp, URL, transformation, hypotheses, ground-truth method, available vs hidden evidence, ambiguity/recoverability/open-set labels.

SYN- identifiers must not be cited as official catalog rows.

---

## 10. Data Cards

`{_j(payload.get("data_cards"))}`

---

## 11. Natural Ambiguity Taxonomy

Multi-label: lexical, semantic, observational degeneracy, missing/conflicting/incomplete, temporal, cross-source disagreement, open-set, recoverable/non-recoverable, misleading proxy.

Performance by label: `{_j(payload.get("ambiguity"))}`

---

## 12. Controlled Degradation Design

Kinds: clean, lexical, missing_context, entity_removed, temporal_removed, conflicting, partial, severe with eta in [0,1]. Parent object `cluster_id` is shared so variants are not independent N.

---

## 13. External Benchmark Construction

n_states: {payload.get("n_states")}
n_clusters: {payload.get("n_clusters")}
splits: development (NASA Kepler clean, year<=2020), temporal holdout (year>2020), cross-instrument (TESS), external ESA, external observatory, MAST fixture, adversarial constructs, OPS structured.

Zero-shot is recorded before any adaptation (adaptation rungs marked NOT_RUN).

---

## 14. Leakage Audit

`{_j(payload.get("leakage"))}`

Document issues: `{_j(payload.get("leakage_docs_issues"))}`

---

## 15. Baselines

Retrieval: BM25, hashing-dense (not neural), hybrid, query-expansion BM25. HyDE NOT_RUN. Neural: `{_j(payload.get("neural"))}`

Decision: immediate ANSWER, entropy-only, empirical myopic (shadow). Oracle action is a bound, not a competitor.

Retrieval table: `{_j(payload.get("retrieval"))}`

Query expansion: `{_j(payload.get("query_expansion"))}`

---

## 16. Scale Design

Axes: documents, |H|, queries (clustered), eta, p_unknown, calls/cost. 10^5 TAP protocol is documented, not executed.

Power: `{_j(payload.get("power"))}`

Query scale: `{_j(payload.get("query_scale"))}`

---

## 17. Corpus-Scale Results

`{_j(payload.get("corpus_scale"))}`

---

## 18. Hypothesis-Scale Results

`{_j(payload.get("hypothesis_scale"))}`

---

## 19. Query-Scale Results

Cluster-aware N is `n_clusters={payload.get("n_clusters")}`, not the degradation-expanded row count.

OPS historical N=12 remains underpowered and is not re-interpreted as confirmatory.

---

## 20. Ambiguity-Scale Results

`{_j(payload.get("ambiguity_scale"))}`

Monotonicity is not assumed.

---

## 21. Open-Set Results

`{_j(payload.get("open_set_scale"))}`

---

## 22. Equal-Call Results

`{_j(payload.get("budget", {}).get("equal_call_budget_1"))}`

---

## 23. Equal-Latency Results

Offline stdlib run: hashing/BM25 latencies only. Neural/cross-encoder equal-latency matching NOT_RUN. Composite cost keeps latency as a raw component (`budget.composite_cost_example`).

---

## 24. Equal-Cost Results

Monetary tokens are zero unless a billed API is used. Lambdas are explicit. Cloud cost: NOT_RUN.

---

## 25. Pareto Frontier

`{_j(payload.get("budget", {}).get("pareto_calls"))}`

---

## 26. NASA Results

See transfer matrix rows `development`, `external_nasa`, `cross_instrument`, `temporal_holdout`.

`{_j(payload.get("transfer", {}).get("zero_shot", {}).get("matrix"))}`

---

## 27. ESA Results

Split `external_esa` in the transfer matrix. Schema-faithful only.

---

## 28. Observatory Results

Split `external_observatory` (ALMA schema). JWST fixture is overlay-only and too small for H_EXT.

---

## 29. Cross-Source Transfer

Shifts: `{_j(payload.get("transfer", {}).get("zero_shot", {}).get("shifts_from_development"))}`

Adaptation ladder: calibration_only / limited / full are NOT_RUN after recording zero-shot.

---

## 30. OPS Cross-Domain Results

`{_j(payload.get("ops_delta"))}`

Summaries: `{_j(payload.get("ops_eval"))}`

The framework (uncertainty × recoverability × cost) can transfer while a specific R_hat estimator does not. Cycle 2 OPS equal-budget negative result is retained.

---

## 31. Regime Discovery

`{_j(payload.get("regime"))}`

Boundaries fit on `development` only.

---

## 32. Regime Validation

Held-out cell in the same object. Cross-source qualitative structure is the scientific target, not coefficient equality.

---

## 33. Crossover Surface

`{_j(payload.get("neu_surface", {}).get("crossover_rho_star"))}`

Grid: `{_j(payload.get("neu_surface", {}).get("grid"))}`

---

## 34. Failure Regions

Adversarial summaries: `{_j(payload.get("adversarial"))}`

Expected losses: clear/cheap ANSWER; non-recoverable EXPLORE waste; mismatch; open-set false ANSWER; high kappa.

---

## 35. Strongest Baseline

On clear/low-eta states: immediate ANSWER / BM25-style top-1. Entropy remains the serious uncertainty baseline. Do not declare myopic globally strongest.

---

## 36. Cases Where Baselines Win

Clear query, perfect top-1, high retrieval cost, anti-QUASAR cost-dominated, sanity Hybrid IRR, WDI BM25 top-1, Cycle 2 OPS equal-budget.

---

## 37. Cases Where QUASAR2 Wins

Only where held-out ΔQ in predicted R* is positive under clustered intervals. Region characterization: {payload.get("region_characterization")}

---

## 38. Negative Results

- Live official dumps were **not** used (claim C3-live-official-dumps REFUTED as a completed confirmatory test).
- HyDE / strong neural / cross-encoder full N NOT_RUN.
- Cloud replication NOT_RUN.
- Gate 1 remains FAIL.
- Cycle 2 G-R recoverability beyond uncertainty remains NOT_SUPPORTED.
- Schema transfer is weaker evidence than catalog-version transfer.

---

## 39. Statistical Inference

Cluster bootstrap on `cluster_id` (object / incident class). Pooled and source-specific summaries both reported. Effect sizes are ΔNEU, not p-values. Seeds: {payload.get("seed")}.

---

## 40. Replication Results

Environment: `{_j(payload.get("environment"))}`

Cloud: `{_j(payload.get("cloud"))}`

Frozen reconstruct: `{_j(payload.get("frozen_v011"))}`

Cycle 2 reconstruct: `{_j(payload.get("cycle2_preserved"))}`

Levels: this checkout supports computational reproducibility of the **offline** program. That is **not** external replication of NASA/ESA science archives.

---

## 41. Reproducibility Audit

- `quasar2 reproduce-paper` reconstructs frozen tables from immutable JSON and reruns the offline external program without silent mutable downloads.
- Dockerfile provided for independent Linux execution.
- Clean-checkout: `pip install -e .` then `quasar2 validate` and `quasar2 reproduce-paper`.

---

## 42. Claim Ledger Changes

New hypothesis ids H_EXT…H_REPLICATION registered as HYPOTHESIS. No SUPPORTED_IN_SCOPE promotions. C3-live-official-dumps REFUTED as completed.

`{_j(payload.get("claims"))}`

---

## 43. New Supported Claims

None at SUPPORTED_IN_SCOPE. Schema-offline results may be PARTIALLY_SUPPORTED only as mechanism maps, not as NASA/ESA confirmation.

---

## 44. Claims Not Supported

H_EXT, H_DOMAIN, H_SCALE, H_BUDGET, H_REGIME, H_MISMATCH, H_REPLICATION as confirmatory scientific claims on official dumps.

---

## 45. Refuted Claims

"Live NASA/ESA/ALMA TAP dumps were used as confirmatory evidence in this cycle."

Universal average superiority of QUASAR2 is still not claimed and remains inconsistent with frozen sanity Hybrid and WDI top-1.

---

## 46. Remaining Threats

Leakage via constructed language overlap; schema ≠ live catalog; pseudo-replication if cluster_id ignored; compute advantage if neural added later without budget match; tuning on holdout; observation-model mismatch reversing R_hat; weak hashing-dense "neural" confusion (explicitly not neural).

---

## 47. Scientific Maturity Assessment

Moved from internally mature prototype toward an **auditable external-validity protocol**. Confirmatory external validity on official dumps is **not** complete. Quality bar in the program statement is not met by "NASA schema loaded successfully."

---

## 48. Highest-Information Next Experiment

Frozen TAP/ADQL snapshots of a **versioned** KOI/TOI slice and a **versioned** Gaia NSS/source slice, with pre-registered clustered ΔNEU vs BM25+entropy under equal retrieval-call budget, zero-shot from Kepler-era development to TESS-era and Gaia, **before** any source-specific threshold search.

---

## Final questions

A. Does QUASAR2 generalize across independent public scientific sources? **{a.get("A")}**

B. Does the decision principle transfer outside astronomy? **{a.get("B")}**

C. Does QUASAR2 retain useful behavior as corpus/hypothesis/query scale grows? **{a.get("C")}**

D. Can the main results be reproduced from a clean independent environment? **{a.get("D")}**

E. Does QUASAR2 beat strong baselines anywhere under equal budget? **{a.get("E")}**

F. If YES/PARTIAL, region: {a.get("F")}

G. If NO, failed assumption: {a.get("G") or "See negative results; schema-offline R* may be empty or unstable."}

H. Does a stable empirical advantage regime exist? **{a.get("H")}**

Formal target: R* = {{ s : E[U_QUASAR2(s) - U_best_baseline(s) | s] > 0 }}. Identifiable in development features: attempted. Stable across official dumps: **not demonstrated**. Economically meaningful: **unknown** without monetary traces.

Every important cell should be read with: source, snapshot `{payload.get("snapshot_id")}`, N / clustered N, regime, policy, baseline, budget, utility (rho/kappa), effect size, CI, seed `{payload.get("seed")}`, run_id `{payload.get("run_id")}`, git SHA `{payload.get("git_sha")}`, artifact `{dest}`.
"""
    path = dest / "REPORT.md"
    path.write_text(md, encoding="utf-8")
    return path
