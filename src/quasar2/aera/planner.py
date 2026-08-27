"""Receding-horizon planner d=1/2. Must beat greedy under equal budget or be refuted."""

from __future__ import annotations

from itertools import product
from typing import Sequence

from quasar2.aera.twin import TwinEstimate, simulate_outcomes


TERMINAL = frozenset({"ANSWER", "DEFER", "ASK"})


def greedy_one_step(
    *,
    entropy: float,
    margin: float,
    actions: Sequence[str],
    remaining_budget: float,
    costs: dict[str, float],
) -> TwinEstimate:
    eligible = [name for name in actions if costs.get(name, 0.1) <= remaining_budget]
    if not eligible:
        return simulate_outcomes(entropy=entropy, margin=margin, action="ANSWER")
    scored = [
        simulate_outcomes(entropy=entropy, margin=margin, action=name)
        for name in eligible
    ]
    return max(scored, key=lambda row: row.expected_u - costs.get(row.action, 0.1))


def plan_horizon2(
    *,
    entropy: float,
    margin: float,
    actions: Sequence[str],
    remaining_budget: float,
    costs: dict[str, float],
) -> dict[str, object]:
    """Enumerate length-2 plans. No MCTS."""

    names = [name for name in actions if costs.get(name, 0.1) <= remaining_budget]
    best: dict[str, object] | None = None
    for first, second in product(names, names):
        c1 = costs.get(first, 0.1)
        c2 = 0.0 if first in TERMINAL else costs.get(second, 0.1)
        if c1 + c2 > remaining_budget + 1e-9:
            continue
        e1 = simulate_outcomes(entropy=entropy, margin=margin, action=first)
        entropy2 = max(0.0, entropy - 0.25 * max(0.0, e1.expected_u))
        e2 = (
            simulate_outcomes(entropy=entropy2, margin=min(1.0, margin + 0.1), action="ANSWER")
            if first in TERMINAL
            else simulate_outcomes(entropy=entropy2, margin=margin, action=second)
        )
        value = e1.expected_u + (0.0 if first in TERMINAL else 0.85 * e2.expected_u) - c1 - c2
        row = {
            "plan": (first,) if first in TERMINAL else (first, second),
            "value": value,
            "cost": c1 + c2,
            "first": e1,
            "second": e2,
        }
        if best is None or float(row["value"]) > float(best["value"]):
            best = row
    greedy = greedy_one_step(
        entropy=entropy, margin=margin, actions=actions, remaining_budget=remaining_budget, costs=costs
    )
    greedy_value = greedy.expected_u - costs.get(greedy.action, 0.1)
    beats = best is not None and float(best["value"]) > greedy_value + 1e-9
    return {
        "best_plan": None if best is None else best["plan"],
        "best_value": None if best is None else best["value"],
        "best_cost": None if best is None else best["cost"],
        "greedy_action": greedy.action,
        "greedy_value": greedy_value,
        "multi_step_beats_one_step": beats,
        "equal_budget": True,
        "horizon": 2,
    }
