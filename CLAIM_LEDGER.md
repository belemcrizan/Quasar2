# QUASAR2 V2 claim ledger

Statuses: `PROPOSED` | `TESTABLE` | `TESTED` | `SUPPORTED` | `PARTIALLY_SUPPORTED` | `NOT_SUPPORTED` | `REFUTED` | `BLOCKED` | `UNKNOWN`

The historical V2.4 ledger remains at [docs/CLAIM_LEDGER.md](docs/CLAIM_LEDGER.md). Entries below are additive. No claim is promoted to `SUPPORTED` by implementation alone.

| claim_id | text | status | scope | evidence | limitations |
|---|---|---|---|---|---|
| H-uncertainty-retrieval | Uncertainty alone does not justify retrieval. | PARTIALLY_SUPPORTED | synthetic kernel-matched holdout `p0-recoverability` / recomputed in `gate1_cycle1` | DRS Spearman 0.620 vs entropy 0.545 vs JSD 0.602 vs TV 0.443 (N=88) | Does **not** survive Gate 1 proxy-failure registered_test, where entropy Spearman 0.508 > DRS 0.328 |
| G1-deploy-R-predicts-deltaU | Deployment-observable recoverability predicts realized EXPLORE ΔU. | NOT_SUPPORTED | Gate 1 registered_test (N=36, 4 regimes) | DRS Spearman 0.328 vs entropy 0.508; ΔSpearman DRS−entropy −0.180 (cluster bootstrap CI −0.414 to 0.000) | SIMULATOR_CAUSAL_WITHIN_MODEL; proxy mismatch is the confirmatory stress |
| G1-R-adds-beyond-uncertainty | Recoverability adds out-of-sample information beyond entropy/margin. | NOT_SUPPORTED | M0 vs M1 on registered_test | M0 Spearman 0.517, M1 −0.198; Δ −0.715 (CI −1.135 to −0.100) | Adding DRS/JSD/TV *hurt* ranking; R² rose (0.026→0.176) but is not the primary endpoint |
| G1-quadrant-effect-modification | E[ΔU \| H high, R high] > E[ΔU \| H high, R low] | NOT_SUPPORTED | secondary quadrant, train-frozen cuts | contrast −0.117 (0.243 vs 0.360) | Direction opposite to the operational recoverability hypothesis |
| G1-fixture-availability-explore-gain | FULL vs noExplore availability raises utility on the 120-query fixture | NOT_SUPPORTED | 120 pairs, query-clustered | mean ΔU −0.049 (CI −0.078 to −0.024); 6/120 useful at δ=0.05; 31 pairs with explore_rounds>0 | Exploratory availability arm; EXPLORE availability slightly harmful on this easy fixture |
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
| H_EXT | Adaptive epistemic action transfers across independent scientific sources. | PROPOSED | schema-faithful NASA/ESA/ALMA snapshots | `external-validity` | Not live TAP dumps; SYN- ids |
| H_DOMAIN | Decision-theoretic acquisition transfers astronomy ↔ OPS. | PROPOSED | ops_structured | `external-validity` | Cycle 2 OPS equal-budget negative retained |
| H_SCALE | Advantage region detectable as corpus/|H| scale. | PROPOSED | offline sweeps | `external-validity` | 10^5 TAP not executed |
| H_BUDGET | Occupies part of utility-cost Pareto frontier under equal budget. | PROPOSED | equal-call NEU | `external-validity` | Neural/HyDE not run |
| H_REGIME | Advantage predictable from observable regime variables. | PROPOSED | development-fit | `external-validity` | Coefficients not expected to transfer |
| H_MISMATCH | Observation-model mismatch explains recoverability/policy failure. | PROPOSED | channel shifts | `external-validity` | Connects to Cycle 2 |
| H_REPLICATION | Major findings reproduce on independent compute. | UNKNOWN | Dockerfile + reproduce-paper | cloud NOT_RUN | Not archive replication |
| C3-live-official-dumps | Live NASA/ESA/ALMA TAP dumps used as confirmatory evidence. | REFUTED | this cycle | schema-faithful SYN- snapshots only | Do not cite SYN- ids as archive rows |

Promotion gate: versioned hypothesis, passing implementation tests, checked assumptions, reproducible run id, pre-specified CI/effect, cost/risk, no known leakage, matching claim scope.
