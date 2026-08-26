# Theorem execution status

Updated by `quasar2 theory-check`. This file records the **intended** cards.
A run artifact is `artifacts/theorem_checks.json`. Never read a missing artifact
as PASS.

| id | kind | last execution_state | layer | assumptions checked in harness | notes |
|---|---|---|---|---|---|
| C1 | proposition | PASS_WITHIN_ASSUMPTIONS | ANALYTIC | Markov vs side-information joints | information_loss withheld without Markov |
| T1 | theorem | PASS_WITHIN_ASSUMPTIONS | NUMERICAL | mixture projection, fixed target | heuristics not covered |
| T2 | theorem | PASS_WITHIN_ASSUMPTIONS | ANALYTIC + T2_grid tightness labels | binary finite kernels, both Lipschitz norms | tightness is operational; WDI empirical VoI not run |
| T3 | theorem | PASS_WITHIN_ASSUMPTIONS | NUMERICAL | two-state MDP, \(\gamma=0.8\) | not a POMDP |
| T4 | proposition | PASS_WITHIN_ASSUMPTIONS | MONTE_CARLO | fixed_stage Gaussian NormalUCB | 0/400 false stops at mean 0.15; easy case |
| T4_near_zero | diagnostic | INCONCLUSIVE | MONTE_CARLO | near-zero means, four UCB estimators | not a coverage theorem; sequential NOT_IMPLEMENTED |

States: `NOT_IMPLEMENTED` | `IMPLEMENTED_NOT_RUN` | `PASS_WITHIN_ASSUMPTIONS` |
`FAIL_NUMERICAL` | `FAIL_MONTE_CARLO` | `FAIL_ASSUMPTION` | `COUNTEREXAMPLE_FOUND` |
`INCONCLUSIVE`.
