# QUASAR2 V2.1 — M0 repository audit

**Milestone:** M0 — Audit and freeze v0.1.1  
**Status:** COMPLETE for audit/repro/freeze; scientific loop **unchanged**  
**Audit date:** 2026-08-25  
**Inspected commit:** `c99eba2a305c3f8efdbb62eb1d9e98c189ccf288` (`main`, merge of `v0.2-regime-experiment`)  
**Package version:** `0.2.0` (`pyproject.toml`, `quasar2.__version__`)  
**Loop identity:** v0.1.1 decision/belief/exploration treatment, frozen inside 0.2.0

This document records what exists. It does **not** treat V2.1 hypotheses as demonstrated.

---

## 1. Discrepancies versus the V2.1 master prompt

The prompt assumes a v0.1.1-only prototype as the starting point. The GitHub `main` branch already moved past that. Adaptations required later (do not rewrite now):

| Prompt assumption | Repository fact | Adaptation |
|---|---|---|
| Start from QUASAR2 v0.1.1 | Package is **0.2.0**. CHANGELOG: v0.1.1 loop frozen; v0.2 adds matched-backend regime experiment and ops fixture. | Treat **0.2.0 + frozen v0.1.1 loop** as the empirical baseline. Preserve both the sanity table and the v0.2 harness. |
| Actions `{ANSWER, ANALYZE, EXPLORE, ASK, DEFER}` | `Action` has only `ANSWER`, `EXPLORE`, `ASK` (`src/quasar2/models/decision.py`). Belief update is fused into every retrieval round. No `ANALYZE`, no `DEFER`, no `H_unknown`. | Add actions in M1 as a thin contract around the existing loop. Do not claim ANALYZE exists today. |
| Policy is one-step utility argmax over legal actions | `DecisionEngine.decide` applies **hard gates** (confidence, margin, evidence), then EXPLORE if information-gain proxy ≥ threshold, else ASK, else forced ANSWER. Utilities are **recorded**, not selected by argmax. | M1 skeleton can compute utilities; changing selection rule is a scientific behavior change and needs versioned traces. |
| WDI is the exclusive V2 evidence source | No World Bank / WDI code, snapshot, or adapter. v0.2 scientific fixture is an **ops runbook** (`data/ops/`, `configs/v02_regime.yaml`). Sanity fixture is astronomy/AI. | Keep WDI out of M1. Introduce WDI in M3 behind `Retriever` / a new `EvidenceSource` protocol. Do not delete ops/sanity fixtures. |
| Prompt “V2” vs repo “v0.2” / deferred “v0.3” | Repo **v0.2** = regime experiment (implemented harness). Repo **v0.3** (file `docs/V0.2_EXPERIMENT_PROTOCOL.md`) = deferred H_unknown / DEFER / receding-horizon policy. Prompt **V2.1** ≈ that deferred policy **plus** WDI + QUASAR-Bench. | Call the prompt program **research V2.1**. Leave package `0.2.0` frozen until M1. Next implementation version should be `0.3.0` or `2.1.0-alpha`, never a silent overwrite of 0.2.0 results. |
| JSON Schema / schema 2.1 DecisionResult | Traces are dataclasses → `to_dict()`. Benchmark JSON `schema_version` is `"1.1"`; regime experiment `"2.0"`. No JSON Schema files. | Add versioned schemas in M1 without breaking `quasar2 demo --json`. |
| Ground truth never enters policy input | `QuasarPipeline.run` does not take `correct_hypothesis`. Observation metadata is caller-supplied. **Risk:** `Observation.estimated_degradation` is derived from query signal quality and is visible in traces. Corpus `hypothesis_ids` feed the foreign-document penalty in `EvidenceScorer`. Evaluation code (`benchmark.py`, `experiment.py`) holds `correct_hypothesis`. | Keep pipeline/eval split. M1 must add a guard that policy-facing state cannot serialize hidden labels. Do not pass `estimated_degradation` into the V2.1 policy. |
| Belief scores, not posteriors | Code and docs say “posterior-like” / `probabilities` (`belief/updater.py`, `models/belief.py`). No calibration split or ECE. | Rename to `belief_score` in V2.1 contracts; keep v0.1.1 field names in frozen traces. |
| ANALYZE: zero acquisition | Every loop iteration retrieves. There is no evidence-only deliberation action. | Split ANALYZE from EXPLORE in M2; M1 can stub ANALYZE as illegal-or-no-op until the pipeline exists. |
| Budgets (latency, tokens, money, retrieval) | Soft limits: `max_explore_rounds`, call counters, novelty/repeat gates. No remaining-budget object; remaining budget cannot go negative because it is not modeled. | Add `BudgetState` in M1 with conservative defaults. |
| Sealed test / claim ledger | Not implemented. No `claim_ledger.json`. | M5–M6. |
| CLI `wdi sync`, `dataset build`, `calibrate`, `report`, `trace` | CLI: `validate`, `demo`, `benchmark`, `experiment`, `materialize-ops`. | Extend CLI later; keep current subcommands stable. |

**Prompt vs repo on “do not implement policy until regime experiment answers Δ_loop>0”:**  
`docs/V0.2_EXPERIMENT_PROTOCOL.md` says the deferred policy should wait until the regime experiment answers whether Δ_loop(Q)>0 anywhere. The V2.1 master prompt instructs sequential M0→M7 including that policy. **M0 does not resolve this conflict.** Recommendation: keep v0.2 regime runs as a parallel evidence track; implement V2.1 contracts (M1) without claiming they supersede the frozen loop until both are compared under matched budgets.

---

## 2. Observed architecture

```text
src/quasar2/
  cli.py                 validate | demo | benchmark | experiment | materialize-ops
  pipeline.py            OBSERVE → H → retrieve → score → belief → ANSWER|EXPLORE|ASK
  config.py              YAML-as-JSON ProjectConfig
  baselines.py           bm25, dense hash, hybrid, rewrite_hybrid, multi_query
  benchmark.py           120-query sanity table, paired bootstrap
  experiment.py          v0.2 factorial regime + crossover
  regimes.py             sampled Q=(A,L,P,U,D) cells
  degradation.py         older q0/q1/q2-style degrader
  retrieval/             BM25, hashing dense, hybrid, optional neural, factory
  hypotheses/            Mode A catalog; Mode B injection boundary
  signals/               tokens, quality, estimated_degradation = 1 - quality
  evidence/scorer.py     weighted features + foreign-hypothesis penalty
  belief/updater.py      log-space normalize after evidence_strength * support
  decision/              gates + UtilityModel (ANSWER/EXPLORE/ASK)
  exploration/           discriminator terms + follow-up queries
  models/                observation, hypothesis, evidence, belief, decision, telemetry
  datasets/ops_runbook.py isolated overlapping incident fixture
```

**Legal transitions today (implicit):**

```text
OBSERVE + seed retrieval (charged) → DECISION
  ANSWER → terminal
  ASK    → terminal
  EXPLORE → retrieval → belief → DECISION
  repeated_query or zero_novel_evidence → re-decide with exploration_enabled=False
```

Seed retrieval is **not free** (initial per-candidate searches increment `retrieval_calls`).

---

## 3. CLI, configs, data, tests, results

| Surface | Location | Notes |
|---|---|---|
| Config sanity | `configs/poc.yaml` | seed 42, hybrid backend, hand-set thresholds |
| Config regime | `configs/v02_regime.yaml` | ops paths; experiment methods include `full+R` |
| Domains | `configs/domains.yaml`, `domains_ops.yaml` | clarification templates |
| Sanity data | `data/corpus/*.jsonl`, `data/hypotheses_catalog/`, `data/intents/intents.json` | 80 docs, 40 hypotheses, 40 intents |
| Ops data | `data/ops/**` | generated/written by `materialize-ops` / tests |
| Tests | `tests/test_components.py`, `test_pipeline.py`, `test_v02.py` | 22 unittest cases; stdlib; pytest optional |
| Canonical sanity results | `experiments/results/benchmark.json` / `.csv` | schema 1.1, seed 42 |
| Regime results | **not checked in** | harness exists; no frozen `regime.json` on `main` |
| Formatter | ruff in `[dev]`; not run as a CI gate in-repo (no `.github/workflows` in this clone) |

---

## 4. Observed results (preserved; not V2 claims)

### 4.1 Sanity fixture (v0.1.1 table, package 0.2.0)

Copied without overwrite to `experiments/results/frozen/v0.1.1/`. SHA-256 of JSON: `78084ace9907e300f923c65109debe242e7d53a88d670148dc93c982f29c8c83`.

From `paired_comparisons` in the frozen JSON:

- Full − Hybrid IRR: **−0.0083**, 95% bootstrap CI **[−0.0417, 0.0167]**, 120 pairs (includes zero).
- Full − noHyp IRR: **+0.0167**, CI **[0.0000, 0.0417]**.
- Full − noExplore correct ARR: **+0.0500**, CI **[0.0167, 0.0917]**.

README interpretation is consistent with the JSON: internal exploration signal; **no superiority vs hybrid** on this easy corpus.

### 4.2 Canonical demo (re-run 2026-08-25, this environment)

Query: `The starlight keeps dipping when something crosses the disk` / domain `astronomy`.

- action: **ASK**
- predicted: `astro.exoplanet_transit`
- retrieval_calls: 5; avoided: 2; explore_rounds: 1; termination: `repeated_query`
- Matches `tests/test_pipeline.py` regression expectations.

### 4.3 M0 smoke (descriptive only; not a sealed test)

`quasar2 benchmark --limit 3 --methods hybrid,full --conditions q2`  
→ `experiments/results/m0_smoke/benchmark.json`

On this 3-query slice: hybrid IRR 1.0 / ASK 0; full IRR 1.0 / ASK 1.0 / cARR 0.0. This is a **tiny slice**, not a contradiction of the 120-query table.

`quasar2 experiment --methods bm25,full+bm25 --seeds 42 --limit 3`  
→ `experiments/results/m0_smoke/regime.json`

Headline on this bounded run: bm25 IRR 0.481 vs full+bm25 IRR 0.889; ASK 0.444 for full+bm25. **Preliminary smoke only.** No V2.1 or WDI claim.

---

## 5. Implementation map (existing → V2.1)

| Existing component | V2.1 change | Scientific purpose | Tests | Compatibility risk |
|---|---|---|---|---|
| `models/decision.Action` | Add `ANALYZE`, `DEFER` | Distinct epistemic actions; H3, H4, open-set | Five path tests | CLI/tests that enumerate three actions |
| `DecisionEngine` gates | Legal-set filter + documented utility; **do not silently replace gates in frozen ablation** | H6; cost-sensitive selection | Tie-break, leakage guard | Changing argmax vs gates changes every demo/benchmark |
| `pipeline.py` fused retrieve+update | Split seed retrieval, ANALYZE, EXPLORE | ANALYZE invariants; H2 vs ordinary retrieve | evidence_ids frozen on ANALYZE | Default call counts / traces |
| `belief/updater.py` | Keep math; expose `belief_score`; no posterior claim | Calibration honesty | Normalization properties | JSON field rename vs v0.1.1 goldens |
| `exploration/discriminator.py` | `discrimination_score` + ordinary/random controls | H2 | Paired gain telemetry | Explorer query strings |
| `retrieval/*` | Keep; add `EvidenceSource` protocol later | Source-neutral core | Offline unit tests | Neural extra dep |
| `benchmark.py` 120-query | Freeze as CI sanity; do not use as V2 evidence | Regression | Existing pipeline tests | Overwriting `benchmark.json` |
| `experiment.py` ops regime | Keep as parallel v0.2 track | Existing Δ_loop question | `test_v02.py` | Confounding with WDI V2-alpha |
| Intents `correct_hypothesis` | Eval-only; leakage tests | H1–H6 validity | Reject forbidden policy fields | Metadata passthrough |
| None / WDI | M3 snapshot + adapter | Real structured GT | Offline fixture | Policy WDI heuristics |
| None / QUASAR-Bench | M4 group splits | Ambiguity families | Deterministic generation | Template leakage |
| None / oracle regret | M5 | Action quality without expected-action labels | Tie sets | Gaming via deferral |
| `cli.py` | Additive subcommands | Repro | Migration tests if flags change | Breaking `quasar2 demo` |

---

## 6. Smallest vertical slice (M1 only)

**In scope:** typed five-action enum; `State` / `Budget` / hypothesis+`H_unknown` / evidence / `DecisionResult` schema 2.1 / epistemic trace fields; legal transitions; deterministic policy **skeleton** (legal filter + frozen coefficients + tie-break); reason codes; in-memory fixture; wrap or adapt the existing loop without WDI; keep `quasar2 validate|demo|benchmark` green.

**Out of scope for M1:** WDI, QUASAR-Bench scale, ANALYZE matrix (M2), oracle, calibration artifacts, demonstrator UI, RL/MCTS, extra data providers, changing the frozen 120-query scientific numbers.

**Exact files likely to change in M1:**

```text
src/quasar2/models/decision.py
src/quasar2/models/belief.py          # additive fields only if needed
src/quasar2/models/telemetry.py       # or new models/trace.py, models/state.py, models/budget.py
src/quasar2/decision/engine.py        # legal transitions module may be new: decision/transitions.py
src/quasar2/decision/utility.py
src/quasar2/pipeline.py               # thin adapter; freeze v0.1.1 path behind a flag if behavior would change
tests/test_v21_core.py                # new
docs/ARCHITECTURE.md                  # after slice exists
CHANGELOG.md
```

Prefer a **parallel V2.1 runner** (`QuasarV21Pipeline`) calling shared retrieval, with `QuasarPipeline` left as the frozen treatment, if any decision-rule change would alter demo/benchmark goldens.

---

## 7. Migration hazards

1. Expanding `Action` without a compatibility alias breaks anything matching `{"ANSWER","ASK","EXPLORE"}` only (pipeline tests already use that set).
2. Replacing gates with utility argmax will change the canonical demo (currently ASK after prune) and the 1,080-row sanity table.
3. Overwriting `experiments/results/benchmark.json` destroys v0.1.1 evidence — always write new run IDs.
4. `write_fixture` mutates `data/ops/` during tests; V2 snapshots must be immutable and separate.
5. Version name collision (`0.2.0` vs research V2.1).
6. `estimated_degradation` and corpus hypothesis labels are leakage-adjacent.
7. Docs still say “posterior-like”; V2.1 text must not upgrade that to calibrated posteriors.

---

## 8. Environment record (M0 execution)

```text
git_commit     c99eba2a305c3f8efdbb62eb1d9e98c189ccf288
dirty          clean at clone; M0 added audit/freeze/smoke files after inspection
python         3.13.3 (MSC v.1943 64-bit)
platform       Windows-11-10.0.26200-SP0 AMD64
package        quasar2==0.2.0 (editable)
lockfile       none (pyproject dependencies = []; [dev] pytest, ruff)
neural extra   not installed
network        not required for validate/tests/demo/sanity smoke
```

Commands and outcomes are in the M0 completion report in the accompanying session log and in §4.

---

## 9. Claim ledger (M0)

No V2.1 hypothesis is upgraded. Existing statuses:

| claim_id | text | status | scope |
|---|---|---|---|
| C-sanity-001 | On the 120-query astronomy/AI fixture, Full does not beat Hybrid on IRR (CI includes 0 / negative point estimate). | OBSERVED | sanity fixture, seed 42, commit above |
| C-sanity-002 | Full vs noExplore correct ARR is positive on that fixture. | OBSERVED | same; mechanism signal, not generality |
| C-v02-001 | Ops regime harness exists and smoke-runs. | IMPLEMENTED harness; scientific Δ_loop **UNKNOWN** at paper grade | no frozen full regime.json on main |
| H1–H6 V2.1 | Competing hypotheses, discriminative EXPLORE, ANALYZE, ASK, D0 non-inferiority, regime dependence | HYPOTHESIS | not tested on WDI |

---

## 10. Next smallest step

Execute **M1** only: five-action typed contracts, legal transitions, budget non-negativity, schema-valid traces, in-memory fixture covering ANSWER / ANALYZE (stub or split) / EXPLORE / ASK / DEFER, leakage test that hidden GT fields cannot enter policy input, existing CLI tests remain green via frozen `QuasarPipeline`.
