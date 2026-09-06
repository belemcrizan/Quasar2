# v03 baseline audit

Upstream main: `66ebbe4505d9ed88ca6b0fd4956b16428bfb9bdd`; hardening PR #17 merged,
remote CI success. Package 0.2.0; local Python 3.12. Baseline: 251 tests.
Machine inventory and local frozen-file SHA256s: `experiments/v03/manifests/baseline.json`.
The workspace was hydrated through GitHub from pinned commits; not all historical
large experiment outputs were downloaded. The remote source tree is authoritative.

Implemented: lexical/hash/neural retrieval interfaces; hypothesis catalog;
belief updates; utility/shadow decisions; WDI snapshots and structured evaluation;
V2.4; rescue cycles; AERA; theory harness; HTTP/cockpit; Docker build definitions.
Partially implemented: deployment recoverability, source transfer, calibrated
action values, independent verification, frontier comparisons.
NOT_RUN: live neural/reranker evaluation, human annotation, agent-provider study,
independent Docker reproduction. NOT_FOUND at baseline: v03 namespace,
preregistered external R* program, generic BEIR adapter, live NASA TAP snapshot builder.

Historical strongest negatives remain: Gate 1 deployment recoverability failure;
recoverability features hurt held-out ranking; always-on exploration costs utility;
WDI matched rescue was zero; the policy gate remains BLOCKED. The hardening suite
is engineering evidence, not external scientific support. Preserve CLAIM_LEDGER.md
history and all v0.1.1/v0.2 artifacts. No old command is removed or repurposed.

Current commands are inventoried by `quasar2 --help`; source inventory lists every
module's top-level classes/functions. Baseline docs inspected include README in
both languages, CLAIM_LEDGER, theory/external/WDI protocols, configuration, test
suite, Docker and observability surfaces. Existing adapters contain schema-faithful
fixtures that must never be relabeled as externally validated observations.

Publication verification: 36 local hydration files did not match upstream Git blob hashes. They are explicitly excluded from the local freeze set; their authoritative upstream blobs remain unchanged. The remaining 92 frozen files match upstream bytes.
