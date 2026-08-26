# Claim ledger (V2.4 developmental)

Statuses: HYPOTHESIS | SUPPORTED_IN_SCOPE | PARTIALLY_SUPPORTED | UNSUPPORTED | REFUTED | UNKNOWN

| claim_id | text | status | scope | run | limitations |
|---|---|---|---|---|---|
| C-sanity-hybrid | Full does not beat Hybrid IRR on astronomy/AI fixture | OBSERVED / UNSUPPORTED superiority | 120 queries seed 42 | frozen v0.1.1 JSON | synthetic |
| H1 | Competing hypotheses improve WDI intent recovery vs budget-matched top-1 | UNSUPPORTED in BM25 pilot | 3036 instances, 600 canonical | v24_r3_pilot_bm25 | V2.4 intent exact 0.525 vs top-1 0.643; no clustered CI |
| H2 | Neural dense improves evidence recall vs BM25 | UNKNOWN / exploratory | CI metadata smoke | E5/BGE/MiniLM smokes | no full nDCG table |
| H3 | Policy beats threshold at matched retriever | PARTIALLY_SUPPORTED | BM25 pilot | v24_r3_pilot_bm25 | V2.4 > threshold on intent exact and coverage; still loses to top-1 |
| H4 | Discriminative EXPLORE vs random/ordinary | UNKNOWN | — | not isolated | EXPLORE fires but no ordinaryExplore ablation table |
| H5 | ANALYZE/ASK/DEFER each add value in a regime | PARTIALLY_SUPPORTED | DEFER used; ASK unused | pilot | ASK rate 0 |
| H6 | H_unknown helps open-set | UNKNOWN | open-set items present | no stratified table in metrics.json |
| H7 | Distinguish missingness vs ambiguity | HYPOTHESIS | snapshot has both statuses | evaluator distinguishes statuses; policy mix not fully stratified |
| H8 | EN/PT consistency | UNKNOWN | PT variants in bench | BGE-M3 PT ranked GDP per capita first in smoke only |
| H9 | Hold-out generalization | UNKNOWN | splits exist | no hold-out report |
| H10 | Simple baseline matches QUASAR at lower cost | PARTIALLY_SUPPORTED against full policy | BM25 pilot | top-1 cheaper and higher intent exact |
| C1 | Selective (gated) reasoning is more compute-efficient than always-on QUASAR | INCONCLUSIVE / exploratory | gate experiment + A1 decomposition | No sealed preregistered margins; A1 is descriptive rescue/overthinking only |
| G1-deploy-R-predicts-deltaU | Deployment-observable recoverability predicts realized EXPLORE ΔU | NOT_SUPPORTED (LOCKED) | Gate 1 registered_test | gate1_cycle1 | Do not retune DRS on this set |
| GR-R-adds-beyond-U-holdout-families | Proxy R_leverage adds Spearman info for tau_EXPLORE beyond entropy on new holdout families | NOT_SUPPORTED | cycle2 holdout N=85, 8 families, seed 0 | cycle2_maturity | ΔSpearman 0.191; cluster CI −0.229 to 0.492 includes 0 |
| C2-empirical-Q-not-T2 | T2 bound is not Q(s,EXPLORE) | SUPPORTED_WITHIN_SCOPE | cycle2 action-value contract | cycle2_maturity | implementation + tests |
| C2-policy-beats-strong-baseline-synthetic-holdout | Empirical myopic beats entropy/ANSWER on holdout regret | NOT_SUPPORTED | cycle2 holdout | cycle2_maturity | empirical mean regret 0.073 vs entropy 0.068 |
| WDI-CD-R-adds-beyond-U | Recoverability adds info beyond uncertainty on WDI controlled degradation | NOT_SUPPORTED | validation split; sealed_test excluded | cycle2_maturity | snapshot wdi-ci-offline-fixture |
| C2-ops-positive-deltaU-vs-top1 | Adaptive EXPLORE beats BM25 top-1 under equal budget in OPS sim | NOT_SUPPORTED / TESTED | 12 OPS intents, BM25 paired | cycle2_maturity | mean ΔU_EXPLORE −0.08 (cost); policy utility = force ANSWER 0.52 |
| H_EXT | Adaptive epistemic action transfers across independent scientific sources | HYPOTHESIS | schema-faithful NASA/ESA/ALMA snapshots | external_validity | Not live TAP dumps |
| H_DOMAIN | Decision principle transfers astronomy ↔ OPS | HYPOTHESIS | ops_structured clustered states | external_validity | Cycle 2 OPS equal-budget negative retained |
| H_SCALE | Advantage region remains detectable as corpus/|H| scale | HYPOTHESIS | offline scale sweeps | external_validity | 10^5 TAP not executed |
| H_BUDGET | Occupies part of utility-cost Pareto frontier under equal budget | HYPOTHESIS | equal-call NEU | external_validity | Neural/HyDE not run |
| H_REGIME | Advantage predictable from observable regime variables | HYPOTHESIS | development-fit, held-out check | external_validity | Coefficients are not expected to transfer |
| H_MISMATCH | Observation-model mismatch explains recoverability/policy failure | HYPOTHESIS | channel shifts | external_validity | Connects to Cycle 2 mismatch result |
| H_REPLICATION | Major findings reproduce on independent compute | NOT_TESTED / protocol ready | Dockerfile + reproduce-paper | external_validity | Cloud NOT_RUN; not archive replication |
| C3-live-official-dumps | Live NASA/ESA/ALMA TAP dumps used as confirmatory evidence | REFUTED | this cycle | external_validity | Schema-faithful SYN- snapshots only |

No claim is upgraded to SUPPORTED_IN_SCOPE without a pre-specified clustered interval.

No claim is upgraded to SUPPORTED_IN_SCOPE without a pre-specified clustered interval.

No claim is upgraded to SUPPORTED_IN_SCOPE without a pre-specified clustered interval.
