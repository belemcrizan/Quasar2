# Baselines

The executable implementations live in `src/quasar2/baselines.py` so they are
available after package installation. The benchmark compares:

1. `bm25`: direct sparse retrieval;
2. `dense`: deterministic hashing-vector proxy (not a neural DPR claim);
3. `hybrid`: BM25 + hashing vectors with weighted reciprocal-rank fusion;
4. `rewrite_hybrid`: single catalog commitment, deterministic rewrite, hybrid retrieval.

All methods share the same corpus, relevance labels, cutoff, and query split.

