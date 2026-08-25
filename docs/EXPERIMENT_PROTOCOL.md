# Experiment protocol

## Purpose of the included benchmark

The bundled benchmark is a diagnostic fixture for implementation and mechanism
tests. It is intentionally small enough to run locally in seconds. It verifies
that all methods see the same queries and corpus, that the complete loop can be
ablated, and that favorable and unfavorable outcomes are retained.

It is not a substitute for a preregistered, leakage-controlled external study.

## Frozen unit of comparison

Each intent has three manually frozen observations:

- `Q0`: explicit domain terminology and mechanism;
- `Q1`: moderately paraphrased or partially underspecified;
- `Q2`: colloquial, compressed, or ambiguous wording that retains a weak signal.

There are 20 intents per domain across astronomy and AI: 40 intents and 120
canonical queries. Every method uses the same query text, corpus version, domain
filter, relevance labels, and cutoff.

## Methods

### Retrieval baselines

- `bm25`: direct sparse retrieval;
- `dense`: local hashing-vector cosine proxy;
- `hybrid`: weighted reciprocal-rank fusion;
- `rewrite_hybrid`: catalog-selected single interpretation, expanded query,
  then hybrid retrieval.

### Mechanism variants

- `full`: all mechanisms enabled;
- `noHyp`: only the first hypothesis survives;
- `noExplore`: no autonomous follow-up retrieval;
- `noUpdate`: belief remains at hypothesis-generation scores;
- `noAsk`: exploration may run, but the final action must answer.

The strong rewrite baseline and `noHyp` are not identical: the baseline ranks
the returned documents directly, while `noHyp` still applies evidence scoring,
belief, and decision gates to its single candidate.

## Primary endpoints

For this POC, report both:

1. **Intent Recovery Rate**: final leading hypothesis equals the frozen intent;
2. **Correct Autonomous Resolution Rate**: action is ANSWER and leading
   hypothesis is correct, divided by all queries.

Intent recovery measures interpretation even when the system abstains. Correct
ARR measures useful automatic coverage. Neither alone is sufficient.

Secondary endpoints are Recall@10, MRR, nDCG@10, ASK fraction, retrieval calls,
EXPLORE rounds, p50/p95 latency, and condition robustness ratio.

## Pairing and uncertainty

Comparisons must be paired by `(intent_id, condition)`. The included code
bootstraps those pairs with a fixed seed and reports the 2.5th and 97.5th
percentiles of the Full-minus-Hybrid intent-recovery difference.

For a paper-grade study:

- choose a smallest effect size of interest before looking at test results;
- report effect sizes and confidence intervals, not only p-values;
- retain every seed, including crashes and unfavorable runs;
- correct or hierarchically model multiple primary comparisons;
- use enough test units for the desired interval width.

## Controlled degradation stress suite

`QueryDegrader` implements deterministic removal, colloquial substitution, and
distractor injection for levels:

\[
d \in \{0.10, 0.25, 0.50, 0.75, 0.90\}.
\]

The generator always preserves at least two original tokens and records every
transformation. The canonical benchmark does not silently mix generated and
manually authored queries. A stress study should save a separate manifest with:

- base query id;
- level and seed;
- removed tokens;
- substitutions;
- distractors;
- final query.

Use at least 30 predeclared seeds before making a robustness claim.

## Leakage-control protocol for the next stage

1. Freeze a document snapshot and hash it.
2. Partition intents into train/calibration/validation/test before tuning.
3. Use train only for learned components.
4. Use calibration for evidence weights, probabilities, and action thresholds.
5. Use validation for model-family selection.
6. Open test once for the frozen comparison.
7. Keep query authors or annotators blind to method outputs where possible.
8. Audit whether catalog terms or aliases copy test wording.
9. Report a label-agnostic evidence-scorer sensitivity run.

Chronological or prequential evaluation is required when documents or intents
have timestamps. Random splits are not adequate for claims under drift.

## Real-domain extension

The next evaluation should use precisely named, versioned, legally usable
datasets and a reproducible relevance construction. Candidate examples must be
selected only after checking that they represent degraded latent-intent
retrieval rather than an unrelated anomaly-detection problem.

Synthetic data diagnoses the mechanism. Real data tests external validity. The
two roles must not be conflated.

## Reproduction commands

```bash
quasar2 validate
python -m unittest discover -s tests -v
quasar2 benchmark --config configs/poc.yaml
```

Record Python version, operating system, git commit, configuration hash, corpus
hash, runtime, and complete output artifacts for every reportable run.
