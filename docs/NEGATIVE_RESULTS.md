# Negative results ledger

Negative results are part of the contribution. This ledger is additive: historical
observations remain even when a later run disagrees. A newer run does not
"supersede" an older run unless the estimand, data relationship, and code/config
delta are documented.

Statuses: `RETAINED` | `RECOMPUTED` | `UNVERIFIED_HISTORICAL_OBSERVATION`.

| id | result | status | scope | notes |
|---|---|---|---|---|
| NR-jsd-not-best | Weighted JSD was not the best holdout Spearman predictor of synthetic VoI | RETAINED | CLAIM_LEDGER `JSD-best-predictor` | DRS ranked higher in the historical observation |
| NR-learned-ridge-overfit | Ridge recoverability overfit train and did not win holdout | RECOMPUTED | `gate1_cycle1` evidence_trace | Train Spearman 0.979 vs holdout 0.544 (N=88 kernel families) |
| NR-t2-vacuous | T2 Lipschitz bound was vacuous on a large fraction of synthetic states | UNVERIFIED_HISTORICAL_OBSERVATION | 88-state historical table | Bound remains valid as a certificate |
| NR-t2-as-point-policy | Using the T2 bound as point-estimated VoI produced worse policy regret than a crude threshold | UNVERIFIED_HISTORICAL_OBSERVATION | `p0-policy-compare` | Canonical: bound ≠ Q(s, EXPLORE) |
| NR-shadow-zero-explore | Quadrant shadow recommended 0 EXPLORE on the easy 120-query fixture | UNVERIFIED_HISTORICAL_OBSERVATION | `p0-shadow-120` | Fixture retained as regression, not EXPLORE validation |
| NR-wdi-top1 | BM25 top-1 beat V2.4 policy on WDI intent exact in the BM25 pilot | RETAINED | `v24_r3_pilot_bm25` | Strong simple baseline |
| NR-gate1-proxy-failure | Gate 1 FAIL: deployment proxy R did not add registered-test information beyond uncertainty; M1 Spearman worse than M0 | RETAINED | `experiments/results/gate1_cycle1` | DRS−entropy ΔSpearman −0.180 (CI −0.414, 0); M1−M0 ΔSpearman −0.715 (CI −1.135, −0.100). Allowed R3 exit via high-quality negative result. |
| NR-gate1-quadrant-reversed | High-H high-R mean ΔU (0.243) < high-H low-R (0.360) on registered_test | RETAINED | `gate1_cycle1` quadrant | Operational recoverability hypothesis weakened under proxy mismatch |
| NR-fixture-explore-availability-harm | FULL vs noExplore mean ΔU −0.049 (query-clustered CI excludes 0) on the 120-query sanity fixture | RETAINED | `gate1_cycle1` fixture arm | 6/120 pairs useful at δ=0.05; not confirmatory |

| NR-c3-not-live-dumps | Cycle 3 confirmatory evidence is schema-faithful SYN- snapshots, not live NASA/ESA TAP | RETAINED | external_validity | Do not advertise SYN- ids as archive rows |

Do not delete rows to make the thesis look stronger.
