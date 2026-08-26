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

No claim is upgraded to SUPPORTED_IN_SCOPE without a pre-specified clustered interval.
