"""EROI, MVC, and equal-budget accounting. Do not hide small denominators."""

from __future__ import annotations

from typing import Mapping, Sequence


PRE_REGISTERED_COSTS = {
    "u_correct": 1.0,
    "wrong_answer_cost": 1.4,
    "exploration_cost": 0.10,
    "ask_cost": 0.28,
    "defer_cost": 0.05,
    "verify_cost": 0.12,
    "analyze_cost": 0.02,
    "interaction_fatigue_step": 0.08,
}


def eroi(*, delta_u: float, delta_c: float, eps: float = 1e-9) -> dict[str, object]:
    """Return-on-investment only when extra cost is strictly positive."""

    if delta_c > eps:
        return {
            "status": "DEFINED",
            "eroi": delta_u / delta_c,
            "delta_u": delta_u,
            "delta_c": delta_c,
        }
    if abs(delta_c) <= eps:
        if delta_u > eps:
            return {"status": "DOMINANCE", "eroi": None, "delta_u": delta_u, "delta_c": delta_c}
        if delta_u < -eps:
            return {"status": "DOMINATED", "eroi": None, "delta_u": delta_u, "delta_c": delta_c}
        return {"status": "UNDEFINED_ZERO_COST", "eroi": None, "delta_u": delta_u, "delta_c": delta_c}
    return {
        "status": "UNDEFINED_NEGATIVE_COST",
        "eroi": None,
        "delta_u": delta_u,
        "delta_c": delta_c,
        "note": "adaptive spent less than fast; report ΔU and ΔC separately",
    }


def marginal_value_of_compute(utilities: Sequence[float], costs: Sequence[float]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for index in range(len(utilities) - 1):
        mvc = float(utilities[index + 1]) - float(utilities[index])
        mc = float(costs[index + 1]) - float(costs[index])
        stop = mvc <= mc
        rows.append({"k": index, "mvc": mvc, "mc": mc, "stop": stop})
    return rows


def equal_budget_table(
    systems: Mapping[str, Mapping[str, float]],
    *,
    budget_key: str = "calls",
    utility_key: str = "utility",
) -> dict[str, object]:
    """Compare systems that spent the same budget; refuse silent unequal comparisons."""

    budgets = {name: float(row[budget_key]) for name, row in systems.items()}
    unique = {round(value, 6) for value in budgets.values()}
    equal = len(unique) == 1
    ranking = sorted(systems.items(), key=lambda item: (-float(item[1][utility_key]), item[0]))
    return {
        "equal_budget": equal,
        "budgets": budgets,
        "winner": ranking[0][0] if ranking and equal else None,
        "ranking": [(name, float(row[utility_key])) for name, row in ranking],
        "note": None if equal else "Budgets differ; do not claim global superiority.",
    }


def cost_per_event(*, numerator_cost: float, count: int) -> dict[str, object]:
    if count <= 0:
        return {"status": "UNDEFINED", "value": None, "count": count, "cost": numerator_cost}
    return {"status": "DEFINED", "value": numerator_cost / count, "count": count, "cost": numerator_cost}
