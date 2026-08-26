# QUASAR2 V2 claim ledger

Statuses: `PROPOSED` | `SUPPORTED` | `PARTIALLY_SUPPORTED` | `NOT_SUPPORTED` | `REFUTED` | `UNKNOWN`

The historical V2.4 ledger remains at [docs/CLAIM_LEDGER.md](docs/CLAIM_LEDGER.md). Entries below are additive. No claim is promoted to `SUPPORTED` by implementation alone.

| claim_id | text | status | scope | evidence | limitations |
|---|---|---|---|---|---|
| H-uncertainty-retrieval | Uncertainty alone does not justify retrieval. | PROPOSED | theory + future paired experiments | not tested on WDI/sanity as a pre-registered endpoint | operational hypothesis |
| T1-variational-analyze | Admissible ANALYZE decreases KL(q\|\|p*) for a fixed target. | UNKNOWN | synthetic mixture projection only | harness T1 covers mixture projection, not heuristics | heuristic ANALYZE is not T1 |
| T2-binary-voi | E\|b'-b\| = 2b(1-b)TV; VoI Lipschitz bounds. | UNKNOWN | synthetic discrete kernels | implementation tests exist; empirical VoI vs bound not run on WDI | Lipschitz constant must be declared |
| T3-contraction | Bellman operator is a γ-contraction on tabular MDPs. | UNKNOWN | tiny tabular MDP | implementation check only | not a POMDP at scale |
| T4-false-stop | Fixed-stage Bonferroni UCB has P(false stop) ≤ α. | UNKNOWN | Gaussian synthetic | NormalUCB is approximate | sequential looks not covered |
| C1-information-loss | Information loss is nonnegative iff Markov degradation holds. | UNKNOWN | synthetic joints | counterexample with side information is encoded as a test | real queries may have side channels |
| JSD-best-predictor | Weighted JSD is the best predictor of empirical VoI. | PROPOSED | recoverability comparison not yet run | none | other divergences may win |
| H-analyze-value | ANALYZE improves decision utility on some regimes. | UNKNOWN | v24 heuristic ANALYZE exists | no sealed utility table | may worsen calibration |
| H-wdi-transfer | WDI results transfer to JWST/CERN. | UNKNOWN | fixtures only | metadata snapshots, not full benches | domain shift unmeasured |
| H10-simple-baseline | Simple baselines can beat QUASAR2. | PARTIALLY_SUPPORTED | BM25 WDI pilot (legacy ledger) | top-1 BM25 > V2.4 policy on intent exact | does not refute theorems |

Promotion gate: versioned hypothesis, passing implementation tests, checked assumptions, reproducible run id, pre-specified CI/effect, cost/risk, no known leakage, matching claim scope.
