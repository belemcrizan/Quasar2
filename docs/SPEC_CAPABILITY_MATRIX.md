# Spec capability matrix (P0 cycle)

Statuses: `EXISTS` | `PARTIAL` | `MISSING` | `CONFLICTING` | `NOT_APPLICABLE`.

This is an audit against the top-tier acceleration spec. Implementation ≠ scientific support.

| capability | status | notes |
|---|---|---|
| Frozen v0.1.1 loop | EXISTS | Unchanged; shadow is additive |
| WDI / astronomy / V2.4 / claim ledger | EXISTS | Preserved |
| Recoverability estimators | PARTIAL | TV/KL/JSD/MI/DRS/learned; not validated on WDI |
| Recoverability → empirical VoI | PARTIAL | Synthetic bench + Gate 1 registered_test; 96% label not claimed |
| Learned recoverability | PARTIAL | Ridge on synthetic VoI; fit on development/model_selection only |
| Decision Recoverability Score | EXISTS | Flip probability; hypothesis-level |
| Legacy/Threshold/Myopic/RecedingHorizon | PARTIAL | Receding horizon>1 NOT_IMPLEMENTED (falls back) |
| TabularOracle / Learned / SPRT-inspired | PARTIAL | Synthetic only; SPRT not classical |
| Policy gap decomposition | PARTIAL | Diagnostic, explicitly non-additive |
| Discriminative vs relevance scorer | PARTIAL | Protocol + bag-of-words LLR; not in frozen retrieval |
| ASK VoI question selection | PARTIAL | Cycle 7A user simulator; not a deployed ASK policy |
| ANALYZE depth k | PARTIAL | Operators exist; no cost ladder experiment |
| Open-set competitive track | PARTIAL | H_unknown on V2.4; no AUROC_OOD suite |
| Budget frontiers | PARTIAL | Synthetic equal-cost slices; no full Active-RAG tournament |
| Retrieval harm | PARTIAL | Bayes 0-1 harm ~0 (expected); operational harm not audited |
| Crossover ρ-κ | MISSING | Sensitivity still incomplete |
| Phase diagrams | PARTIAL | Shadow grid; no multi-seed stability |
| Standard QA benches | MISSING | License/practical |
| QUASAR-Bench | PARTIAL | WDI JSON exists; not a full action-selection bench |
| 120-query shadow | PARTIAL | CLI added; run artifacts under experiments/runs |
| T2 tightness | PARTIAL | Labels on synthetic grid |
| T4 near-zero | PARTIAL | Harness INCONCLUSIVE |
| Anytime stopping / e-values | MISSING | Separate track |
| Shift / threshold transfer | MISSING | |
| Strong external adaptive baselines | MISSING | Related-work matrix only |
| Reproduce CLI | MISSING | Registry + manifests only |
| VERIFY source model | MISSING | Enum only |

Highest remaining threat: recoverability that works on synthetic kernels may fail under proxy Bernoulli supports and WDI heuristic belief.
