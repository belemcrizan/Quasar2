# QUASAR2 V2 claim ledger

Statuses: `PROPOSED` | `TESTABLE` | `TESTED` | `SUPPORTED` | `PARTIALLY_SUPPORTED` | `NOT_SUPPORTED` | `REFUTED` | `BLOCKED` | `UNKNOWN`

The historical V2.4 ledger remains at [docs/CLAIM_LEDGER.md](docs/CLAIM_LEDGER.md). Entries below are additive. No claim is promoted to `SUPPORTED` by implementation alone.

| claim_id | text | status | scope | evidence | limitations |
|---|---|---|---|---|---|
| H-uncertainty-retrieval | Uncertainty alone does not justify retrieval. | PARTIALLY_SUPPORTED | synthetic holdout `p0-recoverability` | DRS Spearman 0.620 vs entropy 0.545 vs JSD 0.602 vs TV 0.443 (N=88 states) | Modest gap; not WDI; entropy still predicts VoI |
| T1-variational-analyze | Admissible ANALYZE decreases KL(q\|\|p*) for a fixed target. | UNKNOWN | synthetic mixture projection only | harness T1 covers mixture projection, not heuristics | heuristic ANALYZE is not T1 |
| T2-binary-voi | E\|b'-b\| = 2b(1-b)TV; VoI Lipschitz bounds. | TESTED | synthetic discrete kernels | identity holds on T2_grid; tightness on 88 states: vacuous 40, useful 32, tight 8, loose 8 | Lipschitz constant must be declared; vacuous is common |
| T3-contraction | Bellman operator is a γ-contraction on tabular MDPs. | UNKNOWN | tiny tabular MDP | implementation check only | not a POMDP at scale |
| T4-false-stop | Fixed-stage Bonferroni UCB has P(false stop) ≤ α. | TESTED | Gaussian synthetic, easy mean | T4 easy case historically PASS; `T4_near_zero` INCONCLUSIVE | sequential looks not covered |
| C1-information-loss | Information loss is nonnegative iff Markov degradation holds. | UNKNOWN | synthetic joints | counterexample with side information is encoded as a test | real queries may have side channels |
| JSD-best-predictor | Weighted JSD is the best predictor of empirical VoI. | NOT_SUPPORTED | `p0-recoverability` holdout | DRS 0.620 > JSD/MI 0.602; learned 0.544 ≈ entropy | N=88 deterministic states; DRS is 0-1 specific |
| H-myopic-voi-shadow | V2 shadow recommendations diverge from legacy execution on some queries. | PARTIALLY_SUPPORTED | `p0-shadow-120` | Quadrant vs legacy 76/120 agree (0.633); 44 ANSWER→ASK; 0 EXPLORE recs | proxy kernels; no counterfactual correctness |
| H-phase-topology | Ambiguity×recoverability phase diagram matches quadrants A–D. | UNKNOWN | synthetic shadow grid | `quasar2 phase-diagram` | topology is not imposed |
| H-analyze-value | ANALYZE improves decision utility on some regimes. | UNKNOWN | v24 heuristic ANALYZE exists | no sealed utility table | may worsen calibration |
| H-wdi-transfer | WDI results transfer to JWST/CERN. | UNKNOWN | fixtures only | metadata snapshots, not full benches | domain shift unmeasured |
| H10-simple-baseline | Simple baselines can beat QUASAR2. | PARTIALLY_SUPPORTED | BM25 WDI pilot (legacy ledger) | top-1 BM25 > V2.4 policy on intent exact | does not refute theorems |
| H-bayes-voi-nonnegative | Under true kernels and 0-1 Bayes updates, retrieval cannot harm V*. | TESTED | `p0-recoverability` | harm rate 0.0 | operational heuristic updates can still harm |
| H-learned-beats-voi | Learned epistemic policy beats myopic VoI on synthetic regret. | PARTIALLY_SUPPORTED | `p0-policy-compare` n_test=400 | learned regret 0.006 vs myopic 0.279 vs threshold 0.218; oracle 0; learned agreement 0.87 | imitation of oracle, not RL; myopic uses Lipschitz bound as VoI; not WDI |
| H-discriminative-recall-decouple | Discriminative scoring can change decision LLR without Recall@10 gains. | PROPOSED | bag-of-words diagnostic only | not connected to frozen retrieval | concept-inspired, not a neural cross-encoder |

Promotion gate: versioned hypothesis, passing implementation tests, checked assumptions, reproducible run id, pre-specified CI/effect, cost/risk, no known leakage, matching claim scope.
