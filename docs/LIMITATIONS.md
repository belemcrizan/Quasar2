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

The discriminator may generate an identical follow-up query on later rounds. The
evidence deduplicator prevents false confidence, but calls are still wasted. A
production planner should stop when expected novel yield is low.

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

