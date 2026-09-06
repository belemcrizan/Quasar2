"""Offline, partition-aware evidence evaluation. No implicit acquisition."""

from __future__ import annotations
import random
from collections import Counter
from quasar2.v03.contracts import IntegrityError
from quasar2.v03.datasets import load_cases
from quasar2.v03.gate import FEATURE_SETS, RStarEstimator, Stump, simple_score, tune_simple
from quasar2.v03.leakage import audit, require_clean
from quasar2.v03.metrics import classification, paired_interval, pareto, risk_coverage
from quasar2.v03.registry import check_preregistration, check_frozen, digest, register
from quasar2.v03.utility import Utility, require_extra_budget


def evaluate(cases, *, price=0.05, samples=1000, seed=42):
    leakage = audit(cases)
    require_clean(leakage)
    parts = {
        name: [c for c in cases if c.split == name]
        for name in ("train", "development", "calibration", "test")
    }
    if any(not value for value in parts.values()):
        raise IntegrityError("All four partitions must be nonempty")
    for case in cases:
        require_extra_budget(case.stop, case.additional)
    utility = Utility(retrieval_price=price)
    train, dev, cal, test = (parts[k] for k in parts)
    models = {}
    choices = {}
    thresholds = {}
    for name in FEATURE_SETS:
        model = RStarEstimator(name).fit(train, utility).calibrate(cal, utility).tune(dev, utility)
        models[name] = model.to_dict()
        choices["rstar_" + name] = [model.selected(c.state) for c in test]
    for name in ("confidence", "entropy", "margin", "recoverability", "uncertainty_recoverability"):
        threshold = tune_simple(dev, utility, name)
        thresholds[name] = threshold
        choices[name] = [simple_score(c.state, name) >= threshold for c in test]
    stump = Stump().fit(train, utility)
    threshold = max(
        (0, 0.25, 0.5, 0.75, 1.01),
        key=lambda t: (
            sum(
                utility.delta(c.stop, c.additional) for c in dev if stump.probability(c.state) >= t
            ),
            t,
        ),
    )
    choices["stump"] = [stump.probability(c.state) >= threshold for c in test]
    thresholds["stump"] = {"threshold": threshold, **vars(stump)}
    choices["stop"] = [False] * len(test)
    choices["always"] = [True] * len(test)
    quota = sum(choices["rstar_full"])
    for name in ("entropy", "confidence", "margin", "recoverability"):
        indices = sorted(
            range(len(test)), key=lambda i: (-simple_score(test[i].state, name), test[i].query_id)
        )[:quota]
        chosen = set(indices)
        choices[name + "_matched"] = [i in chosen for i in range(len(test))]
    for random_seed in (11, 29, 42, 73, 101):
        chosen = set(random.Random(random_seed).sample(range(len(test)), quota))
        choices[f"random_{random_seed}_matched"] = [i in chosen for i in range(len(test))]
    best = set(
        sorted(
            range(len(test)),
            key=lambda i: utility.delta(test[i].stop, test[i].additional),
            reverse=True,
        )[:quota]
    )
    choices["oracle_matched_NONDEPLOYABLE"] = [i in best for i in range(len(test))]
    values = {}
    rows = []
    for name, selected in choices.items():
        outcomes = [c.additional if take else c.stop for c, take in zip(test, selected)]
        values[name] = [utility.value(o) for o in outcomes]
        rows.append(
            {
                "policy": name,
                "n": len(test),
                "additional_calls": sum(selected),
                "accuracy": sum(o.correct for o in outcomes) / len(test),
                "cost": sum(utility.cost(o.costs) for o in outcomes) / len(test),
                "utility": sum(values[name]) / len(test),
            }
        )
    random_values = [
        sum(values[f"random_{s}_matched"][i] for s in (11, 29, 42, 73, 101)) / 5
        for i in range(len(test))
    ]
    comparisons = {
        name: paired_interval(
            values["rstar_full"],
            other,
            [c.group_id for c in test],
            samples=samples,
            seed=seed,
            alpha=0.025,
        )
        for name, other in [
            ("entropy_matched", values["entropy_matched"]),
            ("random_matched_mean", random_values),
        ]
    }
    estimator = RStarEstimator.from_dict(models["full"])
    predictions = [
        {
            "query_id": c.query_id,
            "group_id": c.group_id,
            "probability": estimator.probability(c.state),
            "delta_u": utility.delta(c.stop, c.additional),
            "selected": take,
            "regime": c.regime,
            "open_set": c.open_set,
        }
        for c, take in zip(test, choices["rstar_full"])
    ]
    return (
        {
            "schema_version": "v03.1",
            "split_counts": dict(Counter(c.split for c in cases)),
            "retrieval_price": price,
            "budget_match": "exact additional retrieval count only; latency/tokens are not matched",
            "policies": rows,
            "comparisons": comparisons,
            "pareto": pareto([r for r in rows if "NONDEPLOYABLE" not in r["policy"]]),
            "rstar_classification": classification(
                [p["probability"] for p in predictions],
                [int(p["delta_u"] > 0) for p in predictions],
            ),
            "open_set_detection": classification(
                [c.state.features["unknown_mass"] for c in test], [int(c.open_set) for c in test]
            ),
            "risk_coverage": risk_coverage(
                [c.state.features["confidence"] for c in test], [c.stop.correct for c in test]
            ),
            "thresholds": thresholds,
        },
        models,
        predictions,
        leakage,
    )


def run(dataset, output, root, *, samples=1000):
    cases, metadata, data_hash = load_cases(dataset)
    prereg = check_preregistration(root)
    check_frozen(root)
    artifacts = {}
    primary = None
    for price in (0.01, 0.05, 0.10, 0.25):
        report, models, predictions, leakage = evaluate(cases, price=price, samples=samples)
        key = f"cost-{price:.2f}"
        artifacts[key + "/metrics.json"] = report
        artifacts[key + "/models.json"] = models
        artifacts[key + "/predictions.json"] = predictions
        if price == 0.05:
            primary = report
    artifacts["leakage.json"] = leakage
    artifacts["claims.json"] = {
        "status": "INCONCLUSIVE",
        "claim": "A pre-action R* gate improves utility on independent native external queries.",
        "reason": "Diagnostic program; native external confirmation and independent human labels are not established.",
        "evidence": "cost-0.05/metrics.json",
        "release_0_3": "BLOCKED",
    }
    return register(
        output,
        artifacts,
        dataset_hash=data_hash,
        config_hash=digest({"prices": [0.01, 0.05, 0.1, 0.25], "samples": samples, "seed": 42}),
        preregistration_hash=prereg,
        seed=42,
        metadata={
            "dataset": metadata,
            "primary": primary["comparisons"],
            "scope": "diagnostic; no confirmatory claim",
            "protocol_path": "experiments/v03/protocol.json",
        },
    )
