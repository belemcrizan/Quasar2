# AERA Cycle 8 — Adaptive Epistemic Resource Allocation

**Status:** experimental mechanisms on top of Cycle 4–7A. Frozen **v0.1.1** loop unchanged. Package **0.2.0**. Cycle 6 product policy remains **BLOCKED**.

This cycle operationalizes the controller equation as a **marketplace of epistemic actions** with explicit cost, latency, risk, and model-uncertainty penalties. Retrieval is one purchasable channel, not the product.

## What is demonstrated

| Claim | Status |
|---|---|
| Falsification retrieval rescued 1/2 FastWrong on the sanity fixture (historical Cycle 4) | PARTIALLY_SUPPORTED |
| Always-on extra acquisition has NetRescueRate=0 and ΔU<0 on that fixture | NOT_SUPPORTED (negative result retained) |
| Selected experimental action is executed | TESTED |
| VERIFY against an independent structured source uses 0 retrieval calls | TESTED (experimental path only) |
| ANALYZE does not fetch documents | TESTED |
| Provenance graph duplicate/supersede changes scores | TESTED |
| Fleet allocators respect a global cap in simulation | TESTED |
| EROI undefined when ΔC≤0 | TESTED |
| ΔNEU>0 / product policy promotion | BLOCKED |
| Official NASA/ESA/ALMA TAP dumps | REFUTED (schema-faithful SYN- only) |
| Neural CrossEncoder full protocol | NOT_RUN without extras |
| Online bandit on consequential decisions | DISABLED |

## Reproduce

```text
$env:PYTHONPATH = "src"
python -m quasar2.cli validate
python -m pytest tests/test_aera.py tests/test_rescue_cycle.py tests/test_observability.py -q
python -m quasar2.cli aera-evaluate --output experiments/results/aera_c8 --overwrite --limit 8 --seed 42
python -m quasar2.cli audit --output experiments/results/aera_c8
```

Cycle 4 confirmatory table is **not** overwritten: `experiments/results/cycle4_rescue/`.

## Continuation

See `docs/CYCLE8_CONTINUATION.md`. Next falsifiable test remains recoverability-gated falsification EXPLORE on holdout intents with NetRescueRate>0 **and** ΔU>0, without rewriting the default policy.
