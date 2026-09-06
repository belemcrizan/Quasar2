# v03 evidence program — experimental substrate

See [frozen results](V03_RESULTS.md) for measured outcomes and negative findings.

This is a scoped implementation of the evidence program, not a completed v0.3
scientific release. Package version remains **0.2.0**. The earlier engineering
hardening is merged in #17; this work preserves its tests and historical outputs.

## Reproduce without a network connection

From a checkout, install `python -m pip install '.[dev]'`, then:

```sh
quasar2 v03 audit
python -m pytest
quasar2 reproduce-v03 --input experiments/v03/datasets/control.json.gz --output /tmp/quasar-control
quasar2 reproduce-v03 --input experiments/v03/datasets/nasa.json.gz --output /tmp/quasar-nasa
quasar2 reproduce-v03 --input experiments/v03/datasets/inspire.json.gz --output /tmp/quasar-inspire
quasar2 v03 validate-run /tmp/quasar-control/RUN_ID
```

Use the printed run directory in the last command. Each invocation creates an
exclusive new directory. Frozen input costs include measured retrieval latency;
replaying the evaluation does not remeasure retrieval. Statistical output is
seeded; timestamps, environment and run IDs intentionally differ. The run archives
under `artifacts/v03` retain the full models, split IDs, predictions and hashes.
Extract an archive into an empty directory using Python's tarfile `filter='data'`
on Python 3.12+ before validating its contained run directory.

## Explicit acquisition

```sh
quasar2 v03 sync --dataset scifact --output /tmp/scifact
quasar2 v03 sync --dataset nasa-exoplanet --output /tmp/nasa --execute
quasar2 v03 validate /tmp/nasa
quasar2 v03 build --dataset nasa-exoplanet --snapshot /tmp/nasa --output /tmp/nasa-cases.json
```

Sync defaults to a dry run. Execute performs bounded HTTPS acquisition with
timeouts, retries, compressed/expanded size limits and content hashes. Destinations
must not already exist. A failed directory is preserved with `NOT_RUN.json`;
retry into a new path. Mutable endpoints can return different content later.
Offline reproduction uses the committed derived snapshots, not a new download.
Raw abstracts and source archives are not redistributed here.

BEIR adapters preserve official test queries and reject duplicate/orphan qrels.
A test-only dataset cannot fit this gate by itself: provide separate training,
development and calibration data through an explicit cross-domain design. No
implicit repartition of an official test set occurs.

## What is measured

Runtime features are an immutable, exact allowlist created before the second
retrieval. Gold relevance and realized outcomes live in a separate evaluation
record. Every additional outcome includes total trajectory costs. The primary
comparison uses one initial BM25 retrieval and one optional hashing retrieval,
fusing cached initial hits with the new hits. Hashing is a debug proxy, not a
neural embedding model. Retrieval correctness means top-1 document relevance,
not correctness of a scientific answer or numerical tuple.

A train-only standardized logistic model predicts positive net utility. Calibration
uses only calibration labels; a discrete threshold is selected on development
utility. Test outcomes never fit these components. Models serialize their split
IDs, coefficients and content hash. Ablations, a stump, confidence/margin/entropy,
recoverability, STOP, ALWAYS, five seeded random policies and an explicitly
nondeployable oracle are included. Budget matching fixes the exact number of extra
retrievals; it does not match latency, tokens, wall time or monetary expense.

Four preregistered retrieval prices are evaluated. Each price refits only on the
permitted training/development/calibration partitions. This is sensitivity
analysis, **not** a held-out cost-transfer result. Estimated-cost features are
constant in these inputs, so their ablation is not an informative cost experiment.
The recoverability and relevance features for real-source queries are heuristics.

Paired cluster bootstrap resamples complete query groups. Two primary comparisons
use 97.5% marginal intervals. Reports include probability calibration, rank metrics,
tie-aware selective risk and utility/accuracy/cost tables. Shared documents are
permitted; entity/template/domain transfer is not established. Lexical contamination
screening covers at most 500 unique queries and is not a semantic contamination
certificate. Warnings remain visible and prohibit a scientific support claim.

## Source cards

- **NASA**: 500 rows of `pscomppars`, ordered by planet name; 1,369 generated
  identity/host/Portuguese queries after deduplication; host-group splits.
  Real measurements, generated queries, no human annotations. Composite parameters
  can come from different publications and must not be treated as a homogeneous
  solution. See [TAP documentation](https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html),
  [column documentation](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html)
  and [acknowledgment requirements](https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html).
  These generated identity queries are easier than open scientific questions.
- **INSPIRE**: first page of up to 250 neutrino-related records after 2020; 247
  generated title-prefix queries after deduplication. This bounded, changing slice
  is not a representative literature benchmark. Abstract text is used locally;
  only derived states and query snippets are committed. Consult the
  [official API and field-specific metadata terms](https://github.com/inspirehep/rest-api-doc).
- **BEIR**: SciFact and NFCorpus downloads were attempted and failed; FiQA and
  TREC-COVID were not acquired. The loader is tested with an explicitly labeled
  fixture. [BEIR's official catalog](https://github.com/beir-cellar/beir) links the
  original dataset licenses; a format adapter does not confer redistribution rights.
- **Control**: 600 synthetic cases, four uncertainty/recovery regimes, seeded noisy
  pre-action recovery proxy. Open-set cases have no correct forced answer. This is
  a mechanism diagnostic and cannot establish external validity.

## Human and model boundaries

`v03.annotations` defines independent annotation batches, exact acceptable-answer
sets, abstention, rationales and disagreement lists for adjudication. Agreement
rejects FIXTURE inputs. HUMAN is a declared provenance field, not identity proof.
No human labels or human-agreement result were produced. Annotators should work
independently, blinded to gate predictions; adjudication must be a separate record,
retaining both original judgments and the adjudicator's rationale.

`v03.agent.execute` is a provider-independent execution ledger with explicit model
revision, prompt/input/output hashes and usage counters. It reserves a unique
request directory before invoking a supplied adapter, so retrying cannot silently
repeat a paid call. It is tested with a fixture. No live LLM evaluation, independent
VERIFY tool or full multi-step agent benchmark ran. ANALYZE is forbidden from
changing evidence or increasing acquisition calls. ASK and DEFER have separate
utility terms but are not experimentally evaluated here.

## Integrity and threat model

Hashes detect accidental modification relative to a trusted expected hash; a local
manifest plus its local hash is not a signature or protection from an attacker who
can replace both. Git history supplies the publication anchor. Runtime allowlists
do not establish semantic absence of leakage in natural-language evidence.
Remote ZIP members are allowlisted rather than blindly extracted. The model
ledger is not a prompt-injection defense. Models and source content are untrusted;
no generated tool call is automatically executed. No credentials are stored.

The local checkout was hydrated through the GitHub connector, so its local git SHA
is not an upstream commit. Manifests disclose local SHA, dirty state, Python,
dependencies and source-tree hash; the baseline records the actual upstream SHA.
All published runs are diagnostic, and no clean confirmatory execution is claimed.
