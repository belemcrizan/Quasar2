"""Simulation-before-action. Approximate P(o|s,a); not exact EIG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


OUTCOMES = ("rescue", "no_change", "overthink", "abstain")


@dataclass(frozen=True, slots=True)
class TwinEstimate:
    action: str
    expected_u: float
    sigma: float
    misspecification: float
    calibrated: bool
    outcomes: dict[str, float]


def simulate_outcomes(
    *,
    entropy: float,
    margin: float,
    action: str,
    historical: Mapping[str, Sequence[float]] | None = None,
) -> TwinEstimate:
    """Heuristic twin. Historical frequencies override priors when present."""

    priors = {
        "ANSWER": {"rescue": 0.0, "no_change": 0.85, "overthink": 0.05, "abstain": 0.10},
        "BM25": {"rescue": 0.08 * entropy, "no_change": 0.7, "overthink": 0.15 * (1 - margin), "abstain": 0.05},
        "DISCRIMINATIVE": {
            "rescue": 0.20 * entropy * (1.0 - margin),
            "no_change": 0.55,
            "overthink": 0.20 * (1 - entropy),
            "abstain": 0.05,
        },
        "ANALYZE": {"rescue": 0.02 * entropy, "no_change": 0.9, "overthink": 0.05, "abstain": 0.03},
        "ASK": {"rescue": 0.25 * entropy, "no_change": 0.4, "overthink": 0.05, "abstain": 0.1},
        "VERIFY": {"rescue": 0.12 * (1.0 - margin), "no_change": 0.6, "overthink": 0.05, "abstain": 0.1},
        "DEFER": {"rescue": 0.0, "no_change": 0.2, "overthink": 0.0, "abstain": 0.8},
    }
    table = dict(priors.get(action, priors["ANSWER"]))
    if historical and action in historical and historical[action]:
        mean = sum(historical[action]) / len(historical[action])
        table["rescue"] = max(0.0, min(1.0, 0.5 * table["rescue"] + 0.5 * max(0.0, mean)))
    total = sum(table.values()) or 1.0
    probs = {key: value / total for key, value in table.items()}
    payoffs = {"rescue": 1.0, "no_change": 0.0, "overthink": -0.6, "abstain": -0.05}
    expected = sum(probs[key] * payoffs[key] for key in payoffs)
    sigma = 0.15 + 0.25 * entropy
    miss = 0.35 if not historical else 0.15
    return TwinEstimate(
        action=action,
        expected_u=expected,
        sigma=sigma,
        misspecification=miss,
        calibrated=bool(historical and action in historical and len(historical[action]) >= 8),
        outcomes=probs,
    )


def predicted_versus_realized(predicted: Sequence[float], realized: Sequence[float]) -> dict[str, float | bool]:
    if not predicted:
        return {"n": 0, "mae": 0.0, "calibrated": False}
    mae = sum(abs(p - r) for p, r in zip(predicted, realized)) / len(predicted)
    return {"n": len(predicted), "mae": mae, "calibrated": mae < 0.25}
