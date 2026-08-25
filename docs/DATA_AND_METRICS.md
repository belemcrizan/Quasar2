# Data schema and metrics

## Intent schema

`data/intents/intents.json` contains:

```json
{
  "id": "astro-01",
  "domain": "astronomy",
  "q0": "clear query",
  "q1": "moderately degraded query",
  "q2": "strongly degraded query",
  "correct_hypothesis": "astro.exoplanet_transit"
}
```

`correct_hypothesis` is read by the benchmark only. It is never put in an
`Observation` or passed to `QuasarPipeline.run`.

## Hypothesis schema

Each catalog item contains:

- `id`, `domain`, `label`, and `description`;
- `anchors`: terms expected across ordinary supporting material;
- `discriminators`: terms intended to distinguish neighboring hypotheses;
- `aliases`: paraphrases and colloquial descriptions;
- optional positive `prior` (default 1.0).

Catalog language is part of the experimental treatment. A catalog that copies
test queries can leak the answer; therefore future catalogs must be frozen before
test-query authoring or audited by independent annotators.

## Document schema

Each JSONL line contains:

```json
{
  "id": "ai-doc-01-core",
  "domain": "ai",
  "title": "...",
  "text": "...",
  "hypothesis_ids": ["ai.rag_grounding"],
  "tags": ["RAG", "citation support"],
  "metadata": {"kind": "core"}
}
```

The bundled corpus has two documents per intent: one core explanation and one
discriminative item. This supports a direct novelty test during exploration.

## Retrieval metrics

Let \(rel_k\in\{0,1\}\) indicate whether rank \(k\) has the correct relevance
label.

### Recall@10

\[
Recall@10 = \frac{\sum_{k=1}^{10} rel_k}{\#\text{ relevant corpus documents}}.
\]

The frozen corpus has two relevant documents per intent. A separate binary hit
rate can be derived if needed, but it is not mislabeled as recall.

### Reciprocal rank

\[
RR = \begin{cases}
1/r, & r = \min\{k:rel_k=1\},\\
0, & \text{no relevant hit.}
\end{cases}
\]

MRR is mean RR across observations.

### nDCG@10

The POC uses binary gain and logarithmic discount. A publication dataset may use
graded expert relevance if annotation quality supports it.

## Intent and action metrics

- **IRR**: fraction whose final top hypothesis matches the frozen intent;
- **ARR**: fraction returned with action `ANSWER`;
- **correct ARR**: fraction both answered and correct;
- **ASK fraction**: fraction requiring clarification;
- **wrong autonomous rate**: `ARR - correct ARR` (derivable from output).

Report correct ARR together with wrong autonomous rate. A forced-answer system
can increase ARR without improving decision quality.

## Efficiency metrics

- retrieval calls per observation;
- EXPLORE rounds per observation;
- p50 and p95 local latency.

The POC latency is not production latency: corpus size is 80 and all computation
is in-process. Its purpose is regression detection and relative accounting.

## Robustness ratio

For condition \(c\), the result file reports:

\[
R(c)=\frac{IRR(c)}{IRR(Q0)}.
\]

If the Q0 denominator is zero the implementation reports zero. Always inspect
the absolute numerator and denominator; a ratio can hide low base performance.
