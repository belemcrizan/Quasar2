# Semantic ambiguities (canonical resolutions)

Historical prompt text that concatenated symbols is preserved in the master
prompt. Canonical mathematics lives in `docs/THEORY.md`.

| id | term | possible interpretations | canonical interpretation | reason | affected_modules | test | status |
|---|---|---|---|---|---|---|---|
| AMB-001 | raw VoI vs NetVoI | information value vs value minus cost/risk | `raw_voi` is expected decision-value gain; `net_voi` subtracts declared utility-cost and \(\lambda_R R\) without double counting | incompatible units otherwise | `math/voi.py`, `math/stopping.py` | `tests/test_v2_math.py` | resolved |
| AMB-002 | predicted vs realized utility | model estimate vs trajectory outcome | `voi_estimate` vs `voi_realized`; estimates must not validate themselves | circular evaluation | `models/telemetry.py` | telemetry field names | resolved |
| AMB-003 | scalar vs vector Lipschitz | \(L_b\) on \(|b'-b|\) vs \(L_1\) on \(\|\mathbf b'-\mathbf b\|_1\) | record `lipschitz_norm`; factors 2 and 4 are not interchangeable | T2 C2 | `math/voi.py` | `test_lipschitz_factor_two` | resolved |
| AMB-004 | fixed-stage vs sequential UCB | one look vs many looks | `coverage_scope`; Bonferroni is fixed-stage only | T4 C6 | `math/stopping.py` | `check_t4` notes | resolved |
| AMB-005 | cost vs risk double counting | risk inside C(a) vs extra \(\lambda_R R\) | must declare; default treats them as separate only when units match | NetVoI | cost config | deferred (no live NetVoI policy) | deferred |
| AMB-006 | ANALYZE vs VERIFY | reprocess evidence vs targeted external check | ANALYZE does not change EvidenceSet; VERIFY may if it queries a source | action ontology | `analysis/operators.py`, `v24/actions.py` | `test_analyze_does_not_change_evidence` | resolved |
| AMB-007 | EXPLORE vs VERIFY | broad acquisition vs targeted test | EXPLORE may expand candidates; VERIFY names a target | action ontology | `v24/actions.py` | v24 legal transitions | resolved |
| AMB-008 | unknown class vs empty conformal set | open-set mass vs \(\Gamma=\emptyset\) | they are distinct signals | conformal / H_unknown | v24 unknown_score | deferred | deferred |
| AMB-009 | DEFER utility | abstention reward vs downstream human | DEFER is terminal unless an explicit post-process mode is configured | terminal invariant | `v24/actions.py` | `test_answer_defer_terminal` | resolved |
| AMB-010 | ASK no-response | user answers vs timeout | not modeled in P0 | pipeline ASK | — | deferred | deferred |
| AMB-011 | terminal vs post-process | extra logging after ANSWER | logging is allowed; new evidence/actions are not | pipeline | `test_answer_defer_terminal` | resolved |
| AMB-012 | gold vs acceptable answers | exact string vs tolerance set | WDI uses evaluator tolerances; synthetic uses intent id | `wdi/evaluator.py` | existing WDI tests | resolved |
| AMB-013 | exact vs estimated kernel | oracle P(O\|H,a) vs fitted kernel | bounds using fitted kernels must report kernel error separately | recoverability | recoverability estimators | deferred | deferred |
| AMB-014 | oracle vs estimated regret | \(V^{oracle}-V^\pi\) vs noisy estimate | `oracle_regret_true` vs `regret_estimate`; sample estimates MAY be negative | evaluation | not wired to WDI yet | deferred | deferred |
| AMB-015 | information loss name | always nonnegative vs signed | `information_loss` only with Markov degradation; else `information_difference` | C1 | `math/information.py` | `test_side_information_negative_difference` | resolved |
