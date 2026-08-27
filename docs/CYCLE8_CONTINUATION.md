# Cycle 8 continuation checkpoint

Last completed: AERA marketplace, independent VERIFY, provenance scoring, fleet cap, EROI/MVC, planner d=2 vs greedy (twin), offline IPS, discovery replay, API `/v1/plan|/v1/verify|/v1/fleet|/v1/decision`, cockpit market section.

Frozen: v0.1.1 loop, Gate 1 FAIL, Cycle 4 `experiments/results/cycle4_rescue`, WDI A1 Rescue=0.

## Commands to resume

```text
$env:PYTHONPATH = "src"
python -m pytest tests/test_aera.py tests/test_rescue_cycle.py -q
python -m quasar2.cli aera-evaluate --output experiments/results/aera_c8 --overwrite --limit 8
python -m quasar2.cli rescue-cycle --output experiments/results/cycle4_rescue --overwrite --seed 42
```

Do **not** overwrite Cycle 4 unless reproducing that exact confirmatory run.

## Next falsifiable experiment

Recoverability-gated **falsification EXPLORE** only on pre-action high-entropy states, holdout by `intent_id`, success = NetRescueRate>0 **and** ΔU>0 with cluster bootstrap. If FAIL, diagnose Overthinking vs cost vs missing H* in generation (`astro-02:q1`).

Do not train a learned policy until that gate passes.

## Blocked without new data

- Official NASA/ESA/ALMA TAP confirmatory dumps
- Neural CrossEncoder full protocol (optional extra)
- Human ASK study
- Online bandit
- Multi-agent
