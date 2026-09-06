# Engineering hardening: correctness before stronger claims

This change repairs reproducible failures in the shared retrieval, statistical,
runtime and WDI evaluation layers. It does not establish external validity or
promote the project's historical research gates.

## Correctness changes

- **BM25:** an inverted index scores only documents containing a query term;
  token-empty corpora return no hits instead of dividing by zero. Query limits,
  document identities and model parameters are validated.
- **Hashing:** bucket and sign now use disjoint hash bits. Previously every
  feature in an even-dimensional bucket had the same sign, preventing signed
  collision cancellation. This changes proxy rankings; rerun benchmarks.
- **Fusion and construction:** disabled fusion paths are not called and cannot
  insert zero-weight hits. The factory builds only the indexes needed by the
  selected backend. Empty result limits do no encoding/retrieval work.
- **Neural cache:** keys include encoded document text, order, model revision,
  prefixes and normalization. Writes use atomic replacement; malformed,
  non-finite and incorrectly shaped matrices are rebuilt. Persistent reuse
  requires `neural_revision`; use an immutable model commit hash. Unpinned models
  still work but re-encode documents. Tests use fake encoders, not downloaded models.
- **Numerics:** probability normalization rejects negative/non-finite inputs and
  scales before summation to avoid overflow. Zero-probability joint states no
  longer break mutual information. Bootstrap series must align with cluster labels;
  undefined statistics remain unavailable instead of producing infinite intervals.
- **Conformal prediction:** use the ceiling order statistic and the infinity atom
  when the requested rank is larger than the calibration sample. The previous
  floor and maximum-score clamp could under-cover. Coverage remains conditional on
  the documented exchangeability assumption, not a per-query guarantee. See
  [Angelopoulos and Bates](https://arxiv.org/abs/2107.07511).
- **HTTP:** zero budgets/entropy/margin are preserved. Malformed JSON, non-object
  bodies, invalid UTF-8, non-finite plan inputs and malformed framing are client
  errors. Both transports limit bodies to 32,000 bytes; the stdlib server also
  checks incomplete bodies and applies a socket timeout. Internal exceptions are
  logged rather than exposed to clients. FastAPI correctly injects `Request` and
  dispatches blocking work to its worker pool.
- **Runtime isolation:** gold-field detection traverses nested dictionaries,
  lists and tuples, including on runtime trace export. Negative budget charges
  cannot replenish counters; non-finite costs and invalid counters are rejected.
- **WDI:** NaN, infinity and booleans are malformed observations. Exact intent
  matches require a complete acceptable tuple, including unit and entity type.
  `latest` is checked against the reference period. Zero tolerances are respected;
  fabricated values cannot be hidden behind a missing-data status. Empty source
  units fall back to the public indicator catalog with explicit provenance; fetch
  requests cannot relabel values as a different unit without conversion.
- **Packaging/CI:** the build requires setuptools 77+ for the existing PEP 639
  license metadata. CI runs the core suite on Python 3.10/3.12/3.13, plus an optional
  NumPy/FastAPI integration and package-build job. Missing typing imports found by
  static checks are repaired.

## Verification on Python 3.12

Upstream commit: `18462e26f1bb8dc3383060c0ee41b42eff37ec18`.
The upstream suite passed **197 tests**. The revised suite passes **251 tests**
(**54 added**), plus 77 unittest subcases as reported by pytest 9.1.1.
The added suites were first run against the old implementations to reproduce
failures; positive controls also cover preserved behavior.

```sh
python -m pip install '.[dev]' numpy fastapi httpx build
python -m pytest
python -m ruff check --select E9,F63,F7,F82 src tests
quasar2 validate
quasar2 theorem-benchmark --output /tmp/quasar-theorems.json
python -m build
quasar2 benchmark --methods bm25,dense,hybrid,full --output /tmp/quasar-benchmark.json
quasar2 wdi-experiment --snapshot data/wdi/snapshots/ci-live \
  --backends bm25,hybrid --policies top1,threshold,v24 --limit 120 \
  --output /tmp/quasar-wdi-smoke
```

The WDI smoke run exercises 720 backend/policy/query combinations. It is an
integration check, not a new confirmatory result. The theorem harness reports
PASS_WITHIN_ASSUMPTIONS for C1, T1, T2, T2_grid, T3 and T4; T4_families and
T4_near_zero remain INCONCLUSIVE. Wheel and source distribution build successfully.

### Sanity fixture: 120 queries per method

| Method | Before IRR | After IRR | Interpretation |
| --- | ---: | ---: | --- |
| BM25 | 0.9833 | 0.9833 | Retrieval results preserved |
| Hashing dense | 0.9417 | 0.9750 | Four more correct predictions |
| Hybrid | 0.9833 | 0.9750 | One fewer correct prediction |
| Full pipeline | 0.9750 | 0.9750 | Same intent recovery rate |

The hashing correction is not a universal quality improvement. Full-pipeline ASK
frequency changes from 0.2083 to 0.2167. Existing frozen reports are historical
records and are not overwritten by this PR. New WDI evaluations use stricter
exactness criteria and should not be compared to old scores without re-evaluation.

### BM25 sparse-query microbenchmark

On 10,000 synthetic documents, 40 rare-term queries and five repeats, median
latency per query fell from **2.646 ms to 0.0199 ms** (about **133×**). Document text
was `star galaxy term{i % 1000}`, alternating two domains; queries were a
`random.Random(42).sample(range(1000), 40)` selection of those terms. Rank and exact
score equivalence were checked for those queries plus three common/unseen/mixed
queries across all documents and two domain filters: 129 comparisons.

This measures sparse-query search after index construction. Index memory and
construction cost increase; common-term queries and end-to-end pipelines should
not be expected to show the same speedup. The small sanity fixture did not show
an end-to-end latency improvement. Timing is environment-dependent.

## Remaining limits

Neural integration tests mock the encoder and require no model download. Actual
MiniLM/E5/BGE accuracy, GPU execution, live World Bank sync and production load
were not validated. The research HTTP service still requires deployment-level
access controls and capacity planning. CI configuration is supplied; remote CI
status must be checked on the PR. No frozen claim ledger or research gate is changed.
