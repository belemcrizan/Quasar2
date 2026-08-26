# A1 data dictionary

All rates are descriptive. Feature associations are exploratory. They are not
causal effects and MUST NOT be used to declare C1 supported.

## Identity

| field | meaning |
|---|---|
| backend | Retriever family (`bm25`, `neural`, ...). Score distributions are not pooled. |
| snapshot_id | Immutable WDI snapshot identity from the source run. |
| query_id | Stable instance id. Join key with `backend` and `snapshot_id`. |
| canonical_intent_id / split_family_id | Semantic family. Aliases and paraphrases share one split. |
| split | `calibration`, `development`, `validation`, or `sealed_test`. |
| used_for_feature_ranking | True only for calibration+development. |
| used_for_threshold_proposal | True only for calibration. Never sealed_test. |

## Outcomes

| field | meaning |
|---|---|
| fast_correct / quasar_correct / gated_correct | `intent_exact` from the source run. |
| four_way_class | BOTH_CORRECT, OVERTHINKING, RESCUE, BOTH_WRONG. Mutually exclusive and exhaustive for matched rows. |
| OVERTHINKING | FAST correct AND QUASAR wrong. |
| RESCUE | FAST wrong AND QUASAR correct. |
| failure_class | Four-way label (primary). |
| secondary_labels | Optional heuristic tags. Not a sealed diagnosis. |

## Features

Probe `top1_score`/`top2_score` were not persisted in historical CSVs. Empty
values are listed in `missing_feature_flags` rather than imputed.

Complexity, ambiguity, and open-set scores are taken from the FAST row when
present (those used the original probe). Query-only gate features fill gaps
and are marked missing when retrieval scores are absent.

## Leakage

Threshold proposals and feature ranking ignore `sealed_test`. Re-ranking many
features on sealed_test is forbidden.
