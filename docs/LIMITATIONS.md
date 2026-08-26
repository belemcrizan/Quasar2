# Limitations and known failure modes

## Current limitations

- The corpus and intents are synthetic, authored together, and lexically aligned.
- Only two domains and 40 intents are represented.
- The hashing-vector retriever is not a semantic neural dense retriever.
- Evidence weights and decision thresholds are hand-set, not calibrated.
- Corpus relevance labels contribute a foreign-document penalty.
- The information-gain value is a proxy based on entropy and vocabulary
  separation, not an estimated conditional distribution over future evidence.
- Mode B defines an interface but no bundled LLM integration.
- Latency and scalability results apply only to an 80-document in-memory corpus.
- There is no human evaluation of clarification usefulness or answer quality.
- The current benchmark has one frozen fixture, not 30+ perturbation seeds.
- The astronomy/AI table is a sanity test; v0.2 ops still is not an external IR collection.
- The complexity gate is a cheap heuristic. FAST vs QUASAR routing is not a sealed C1 result.
- Milestone A1 rescue/overthinking associations are exploratory and not causal.
- JWST/CERN fixtures are metadata-only and are not completed domain benchmarks.
- VoI Lipschitz bounds can be loose even when the binary belief-movement identity holds.
- Weighted JSD is not assumed to be the best predictor of empirical VoI.
- The ideal posterior \(b^*\) is unavailable on ordinary WDI queries; the live system uses \(\hat b\).
- Heuristic ANALYZE does not inherit the T1 variational guarantee.
- UCB false-stop control is stated for a fixed stage; sequential stopping is unimplemented.
- Conformal coverage, when used, is marginal under exchangeability, not per-query.
- Exact POMDP optimality is intractable; T3 checks a tiny tabular MDP.
- World Bank results do not imply JWST/CERN transfer.
- Mode `v2_shadow` records `recommended_action_v2` without changing executed legacy actions.
- Highest-mass prediction sets in shadow telemetry are heuristics, not split-conformal coverage.
- Proxy Bernoulli kernels from evidence support are not oracle \(P(O\mid H,a)\).
- MyopicVoIPolicy uses the Lipschitz bound as a point UCB; that is not a statistical tail inequality.
- Decision Recoverability Score and the learned recoverability estimator are synthetic until a WDI paired study exists. Gate 1 tests proxy R on frozen stress regimes; that is not WDI.
- Section-2 Spearman values in the claim ledger are UNVERIFIED_HISTORICAL_OBSERVATION until a run-addressable artifact exists; Gate 1 recomputes them without silently superseding the ledger.
- SPRTInspiredPolicy is not Wald SPRT.
- TabularOraclePolicy must not be applied to WDI proxy kernels as if they were true observation models.
- `PolicyGapDecomposition` is a nested diagnostic, not an additive accounting identity.


## Mechanism failure modes

### Self-confirming retrieval

A hypothesis-conditioned query can retrieve material merely because it repeats
the hypothesis label. Original-query coverage, document novelty, and ablations
reduce but do not eliminate this risk.

### Correlated evidence

Two documents can repeat the same source. Deduplicating document ids is not the
same as modeling source dependence. Future evidence records need source identity,
timestamp, and provenance graph.

### Catalog omission

Mode A cannot recover an intent absent from its catalog. The current decision
space has no explicit `UNKNOWN_HYPOTHESIS`; low-confidence ASK is only a partial
fallback.

### Early candidate pruning

The generator keeps at most four candidates. If the true interpretation ranks
fifth, exploration cannot recover it. Candidate-recall must be reported as its
own diagnostic.

### Repeated useless exploration

The v0.1 baseline could generate an identical follow-up query on later rounds.
v0.1.1 rejects an identical hypothesis-conditioned query before retrieval and
stops after an acquisition round with zero novel evidence. This removes the
observed exact-repeat failure but does not detect paraphrastic or semantically
equivalent queries. It is a redundancy gate, not a learned value-of-information
model.

### Forced answer artifact

`noAsk` can look strong when the top hypothesis is usually correct, but it hides
the cost of wrong automatic actions. Accuracy without a consequence-weighted
coverage curve is insufficient.

## Claim policy

Do not describe v0.1 as a general discovery engine, state-of-the-art retrieval,
Bayesian calibration, causal reasoning, or production-ready agent architecture.
Valid wording is:

> a reproducible mechanism-testing POC for competing-hypothesis intent recovery
> with discriminative retrieval and explicit abstention.

Novelty should remain an open question until a systematic prior-art and related-
work review is completed.
