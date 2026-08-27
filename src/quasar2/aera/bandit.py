"""Offline contextual-bandit evaluation. No live exploration on consequential decisions."""

from __future__ import annotations

from typing import Sequence


def inverse_propensity(reward: float, propensity: float, *, clip: float = 20.0) -> float:
    p = min(max(propensity, 1.0 / clip), 1.0)
    return reward / p


def ips_value(rows: Sequence[dict[str, float | str]], target_action: str) -> dict[str, float | int | str]:
    weighted: list[float] = []
    for row in rows:
        if str(row["action"]) != target_action:
            continue
        weighted.append(inverse_propensity(float(row["reward"]), float(row["propensity"])))
    if not weighted:
        return {"status": "NO_OVERLAP", "n": 0, "value": None}
    return {"status": "IPS", "n": len(weighted), "value": sum(weighted) / len(weighted)}


def doubly_robust(
    rows: Sequence[dict[str, float | str]],
    *,
    q_hat: dict[str, float],
    target_action: str,
) -> dict[str, float | int | str]:
    total = 0.0
    n = 0
    for row in rows:
        baseline = q_hat.get(target_action, 0.0)
        if str(row["action"]) == target_action:
            total += baseline + inverse_propensity(float(row["reward"]) - baseline, float(row["propensity"]))
        else:
            total += baseline
        n += 1
    if not n:
        return {"status": "EMPTY", "value": None, "n": 0}
    return {"status": "DR", "value": total / n, "n": n}


def guardrails() -> dict[str, str]:
    return {
        "online_exploration": "DISABLED",
        "consequential_decisions": "SHADOW_ONLY",
        "rollback": "restore last logged policy snapshot",
        "drift": "not estimated in this package; flag UNKNOWN",
    }
