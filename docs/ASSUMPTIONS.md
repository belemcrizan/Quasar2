# Assumptions

Each scientific claim must name which of these are in force.

| id | assumption | needed for | default in live system |
|---|---|---|---|
| A-bounded-utility | utilities are bounded | Lipschitz VoI bounds, MDP contraction | not verified on WDI |
| A-finite-H | hypothesis set is finite | discrete belief simplex | catalog and v24 candidates are finite |
| A-gamma | \(\gamma\in[0,1)\) | T3 | config `decision.gamma` in v2 only |
| A-finite-A | finite action set | argmax Q | yes |
| A-exchangeability | calibration/test exchangeable | conformal guarantee | **not** assumed on drifting WDI |
| A-ucb-valid | UCB tail inequality holds for the sample class | T4 coverage | NormalUCB: approximate |
| A-kernel | observation kernels used in JSD/TV match the sampling mechanism | T2 bounds on real data | false on WDI unless oracle kernels; shadow uses labeled proxy kernels |
| A-vi-t1 | ANALYZE is an admissible variational update on a fixed target | T1 | heuristic operators: **false** |
| A-markov-degradation | \(I\to Q_{\mathrm{clean}}\to Q_{\mathrm{obs}}\) | nonnegative information loss | only controlled degradations |
| A-markov-state | \(S_t\) is sufficient | exact Bellman | **HYPOTHESIS**; may fail |
| A-no-double-count | risk is not already inside \(C(a)\) | NetVoI subtraction | must be declared per cost model |
| A-lipschitz-norm | `scalar_binary` vs `belief_l1` is declared | T2 factor 2 vs 4 | config `voi.lipschitz_norm` |
| A-tv-half-l1 | TV is half L1 | T2 identity | code default |
| A-fixed-stage | a single look | Bonferroni T4 | sequential is separate |

If an assumption is false, record `FAIL_ASSUMPTION` or `theory_failure` vs
`estimator_failure` vs `domain_transfer_failure` rather than silently weakening
the theorem statement.
