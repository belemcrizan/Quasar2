# Extending QUASAR2 without breaking the experiment

## Add a domain

1. Add the domain to `configs/domains.yaml`.
2. Create `data/hypotheses_catalog/<domain>.json`.
3. Add JSONL documents with globally unique ids.
4. Add intents with Q0/Q1/Q2 and a valid catalog id.
5. Run `quasar2 validate` and the tests.

Do not tune catalog wording against held-out test failures. Version the catalog
and regenerate an untouched test set when its semantics change.

## Add a neural retriever

Implement the `Retriever` protocol:

```python
class MyRetriever:
    def search(self, query: str, *, top_k: int, domain: str | None = None):
        return tuple_of_search_hits
```

Return a score where larger means more relevant and preserve stable document ids.
The pipeline consumes only the protocol. For fair comparison, freeze embedding
model name, revision, pooling, normalization, chunking, and index parameters.

## Add a Mode-B hypothesis backend

Implement `DynamicHypothesisBackend.propose(observation, limit)`. The adapter
will reject cross-domain and duplicate ids. The backend should additionally be
wrapped with:

- schema validation;
- timeout and retry accounting;
- prompt and model version recording;
- PII and policy controls appropriate to the data;
- a cache for reproducible experiment reruns;
- cost and token telemetry.

Never send the benchmark's `correct_hypothesis` to the backend.

## Replace evidence scoring

A cross-encoder or entailment model can replace `EvidenceScorer`, but it must
preserve:

- per-item provenance;
- independent features or rationale for audit;
- duplicate-evidence suppression;
- a documented calibration split;
- an explicit treatment of contradiction and correlated sources.

## Change the decision policy

Decision costs belong in configuration, not hidden conditionals. Fit thresholds
on calibration data and publish coverage versus wrong-answer curves. A business
domain with high consequence should assign a larger wrong-answer cost and may
prefer ASK even when accuracy is unchanged.

## Scale the corpus

The POC builds in-memory indices. Scaling toward \(10^3\)–\(10^6\) documents
requires separate index construction, persistence, batching, and memory/latency
measurements. Do not infer scalability from the current 80-document latency.

