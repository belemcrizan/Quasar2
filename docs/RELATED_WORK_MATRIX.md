# Related work matrix

Labels: `official implementation` | `faithful reimplementation` | `approximate reproduction` | `concept-inspired baseline` | `not implemented`.

QUASAR2 does not currently include official or faithful reimplementations of the methods below.

| method | retrieval trigger | query strategy | policy learned? | cost-aware? | ASK? | ANALYZE? | DEFER? | open-set? | utility objective? | budget frontier? | datasets in QUASAR2 | limitations | fidelity in this repo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QUASAR2 frozen v0.1.1 | gates + IG proxy | hypothesis-conditioned | no | recorded, not argmax | yes | no | no | no | utilities recorded | no | sanity 120, ops | Hybrid can match or beat IRR | n/a (this system) |
| QUASAR2 V2.4 | heuristic five-action | WDI slots | no | partial | legal, rate 0 on BM25 pilot | heuristic | yes | H_unknown | developmental | no | WDI pilot | BM25 top-1 beats intent exact | n/a |
| QUASAR2 myopic VoI (shadow) | NetVoI proxy | unchanged executed retrieval | no | yes in recommender | recommended | recommended | recommended | unknown mass | 0-1 Lipschitz / empirical | synthetic equal-cost slices | synthetic kernels; sanity shadow | proxy kernels | this repo |
| SmartRAG (joint retrieve/rewrite/generate) | learned | learned rewrite | yes | performance vs retrieval cost | no (typical RAG) | no | no | no | reward | not always | none here | different object (RAG policy) | not implemented |
| CtrlA (representation routing) | honesty/confidence directions | standard | optional | optional | no | no | optional abstain | related | routing | no | none here | not entropy/recoverability | not implemented |
| ACL adaptive-retrieval survey (35 methods / 6 datasets) | various | various | mixed | mixed | rare | rare | mixed | mixed | mixed | efficiency metrics | none of the 6 here | QUASAR2 breadth is far smaller | not implemented |
| LeReT | trial feedback | learned queries | yes | retrieval outcome | no | no | no | no | downstream retrieval | no | none here | query policy ≠ action policy | not implemented |
| Active-RAG utility/budget eval | routers vs uncertainty | various | mixed | yes | no | no | no | no | utility | yes; harm; threshold transfer | none here | ranking can flip with budget | concept-inspired (equal-budget slices, harm rate under Bayes) |
| Selective prediction gap analysis | n/a | n/a | n/a | n/a | n/a | n/a | abstain | related | risk-coverage | coverage curves | none here | oracle-gap sources | concept-inspired (`PolicyGapDecomposition`, diagnostic) |
| AbstentionBench | n/a | n/a | n/a | n/a | underspecification etc. | n/a | abstain | yes | abstention quality | no | none here | 20 LLMs × 20 datasets | not implemented |

Differentiation under test, not marketing: unified action set {ANSWER, ANALYZE, EXPLORE, ASK, VERIFY, DEFER} under one currency. VERIFY remains unselected without a source model.
