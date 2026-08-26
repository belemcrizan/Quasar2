"""Equal-budget evaluation, composite cost, Pareto frontier, NEU surfaces."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from quasar2.external.evaluate import evaluate_states, paired_delta


def composite_cost(
    *,
    retrieval_calls: float,
    latency_ms: float,
    tokens: float = 0.0,
    monetary: float = 0.0,
    user_interaction: float = 0.0,
    lambda_r: float = 1.0,
    lambda_l: float = 0.001,
    lambda_t: float = 0.0,
    lambda_m: float = 1.0,
    lambda_u: float = 1.0,
) -> dict[str, float]:
    total = (
        lambda_r * retrieval_calls
        + lambda_l * latency_ms
        + lambda_t * tokens
        + lambda_m * monetary
        + lambda_u * user_interaction
    )
    return {
        "C_total": total,
        "retrieval_calls": retrieval_calls,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "monetary": monetary,
        "user_interaction": user_interaction,
        "lambda_r": lambda_r,
        "lambda_l": lambda_l,
        "lambda_t": lambda_t,
        "lambda_m": lambda_m,
        "lambda_u": lambda_u,
    }


def match_call_budget(rows: Sequence[Mapping[str, Any]], budget: float) -> list[dict[str, Any]]:
    """Keep policies whose mean calls are <= budget; flag others as over-budget."""

    by_policy: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_policy.setdefault(str(row["policy"]), []).append(row)
    out = []
    for policy, group in by_policy.items():
        mean_calls = sum(float(r["budget_calls"]) for r in group) / len(group)
        mean_neu = sum(float(r["neu"]) for r in group) / len(group)
        out.append(
            {
                "policy": policy,
                "budget": budget,
                "mean_calls": mean_calls,
                "mean_neu": mean_neu,
                "within_budget": mean_calls <= budget + 1e-9,
            }
        )
    return out


def utility_vs_budget(rows: Sequence[Mapping[str, Any]], budgets: Sequence[float]) -> list[dict[str, Any]]:
    return [item for b in budgets for item in match_call_budget(rows, b)]


def pareto_frontier(points: Sequence[Mapping[str, Any]], *, cost_key: str, util_key: str) -> list[dict[str, Any]]:
    """Maximize utility, minimize cost."""

    ordered = sorted(points, key=lambda p: (float(p[cost_key]), -float(p[util_key])))
    frontier = []
    best_u = float("-inf")
    for point in ordered:
        u = float(point[util_key])
        if u > best_u:
            frontier.append({**dict(point), "on_frontier": True})
            best_u = u
    return frontier


def neu_surface(
    states: Sequence[Mapping[str, Any]],
    *,
    rhos: Sequence[float] = (0.5, 1.0, 1.4, 2.0, 4.0),
    kappas: Sequence[float] = (0.02, 0.10, 0.25, 0.50),
    seed: int = 0,
) -> dict[str, Any]:
    grid = []
    crossovers = []
    for kappa in kappas:
        for rho in rhos:
            pack = evaluate_states(states, rho=float(rho), kappa=float(kappa), seed=seed, bootstrap_samples=40)
            by_pol = {}
            for row in pack["rows"]:
                by_pol.setdefault(row["policy"], []).append(float(row["neu"]))
            means = {k: sum(v) / len(v) for k, v in by_pol.items() if v}
            grid.append({"rho": rho, "kappa": kappa, "mean_neu": means})
        # rho*(kappa): inf rho where myopic NEU > immediate ANSWER
        rho_star = None
        for rho in rhos:
            cell = next(c for c in grid if c["kappa"] == kappa and c["rho"] == rho)
            m = cell["mean_neu"]
            if m.get("empirical_myopic", -999) > m.get("immediate_answer", 999):
                rho_star = rho
                break
        crossovers.append({"kappa": kappa, "rho_star_myopic_gt_answer": rho_star})
    return {"grid": grid, "crossover_rho_star": crossovers}


def equal_budget_report(rows: Sequence[Mapping[str, Any]], *, seed: int) -> dict[str, Any]:
    call_points = match_call_budget(rows, 1.0)
    frontier = pareto_frontier(call_points, cost_key="mean_calls", util_key="mean_neu")
    delta = paired_delta(rows, "empirical_myopic", "immediate_answer", seed=seed)
    delta_ent = paired_delta(rows, "empirical_myopic", "entropy_only", seed=seed)
    return {
        "equal_call_budget_1": call_points,
        "pareto_calls": frontier,
        "delta_myopic_minus_answer": delta,
        "delta_myopic_minus_entropy": delta_ent,
        "composite_cost_example": composite_cost(retrieval_calls=1.0, latency_ms=12.0),
        "note": "Token and monetary costs are zero in this offline stdlib run; lambdas are explicit.",
    }
