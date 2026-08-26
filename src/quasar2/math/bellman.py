"""Discounted MDP Bellman operator, contraction, and residual error bounds (C5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

INF = float("inf")


@dataclass(frozen=True, slots=True)
class TabularMDP:
    states: tuple[str, ...]
    actions: tuple[str, ...]
    transitions: Mapping[tuple[str, str, str], float]
    rewards: Mapping[tuple[str, str], float]
    gamma: float
    terminals: tuple[str, ...] = ()


def bellman_backup(mdp: TabularMDP, values: Mapping[str, float]) -> dict[str, float]:
    if not 0.0 <= mdp.gamma < 1.0:
        raise ValueError("gamma must lie in [0, 1)")
    updated: dict[str, float] = {}
    for state in mdp.states:
        if state in mdp.terminals:
            updated[state] = 0.0
            continue
        best = -INF
        for action in mdp.actions:
            reward = float(mdp.rewards.get((state, action), 0.0))
            expected = 0.0
            for nxt in mdp.states:
                prob = float(mdp.transitions.get((state, action, nxt), 0.0))
                expected += prob * values.get(nxt, 0.0)
            q_sa = reward + mdp.gamma * expected
            if q_sa > best:
                best = q_sa
        updated[state] = 0.0 if best == -INF else best
    return updated


def sup_norm(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    return max(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys)


def contraction_constant(mdp: TabularMDP, v: Mapping[str, float], w: Mapping[str, float]) -> float:
    tv = bellman_backup(mdp, v)
    tw = bellman_backup(mdp, w)
    denom = sup_norm(v, w)
    if denom == 0.0:
        return 0.0
    return sup_norm(tv, tw) / denom


def value_iteration(
    mdp: TabularMDP,
    *,
    initial: Mapping[str, float] | None = None,
    iterations: int = 64,
) -> tuple[dict[str, float], list[float]]:
    values = {state: float((initial or {}).get(state, 0.0)) for state in mdp.states}
    residuals: list[float] = []
    previous = dict(values)
    for _ in range(iterations):
        values = bellman_backup(mdp, values)
        residuals.append(sup_norm(values, previous))
        previous = dict(values)
    return values, residuals


def residual_error_bound(gamma: float, k: int, first_residual: float) -> float:
    """||V^k - V*||_inf <= (gamma^k / (1-gamma)) ||V^1 - V^0||_inf."""

    if not 0.0 <= gamma < 1.0:
        raise ValueError("gamma must lie in [0, 1)")
    return (gamma**k / (1.0 - gamma)) * first_residual


def exact_error_bound(gamma: float, k: int, initial_error: float) -> float:
    """||V^k - V*||_inf <= gamma^k ||V^0 - V*||_inf."""

    return (gamma**k) * initial_error
