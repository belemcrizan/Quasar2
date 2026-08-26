# Metrics and splits (V2.4)

Keep retrieval, structured intent, decision, observation correctness, and cost separate.

Primary endpoints for developmental tables:

- structured intent exact match
- wrong-answer rate among ANSWER
- answer coverage
- mean retrieval calls
- ASK/DEFER rates

Splits: `development`, `calibration`, `validation`, `sealed_test` assigned by canonical-intent hash. Do not treat D-level or EN/PT variants as independent samples. Cluster by `canonical_intent_id` before intervals (not computed in the R3 BM25 table; planned for R5).

Forbidden policy inputs are listed in `quasar2.v24.actions.FORBIDDEN_POLICY_FIELDS`.
