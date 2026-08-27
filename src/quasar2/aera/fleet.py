"""Fleet scheduler under a global budget. Never exceed the cap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class AgentBid:
    agent_id: str
    voi: float
    risk: float
    priority: float
    cost: float
    tenant: str = "default"


def robust_bid(bid: AgentBid, *, lambda_risk: float = 0.4) -> float:
    return max(0.0, bid.voi * bid.priority - lambda_risk * bid.risk)


def allocate(
    bids: Sequence[AgentBid],
    *,
    global_budget: float,
    method: str = "greedy_voi",
    reserve: float = 0.05,
) -> dict[str, object]:
    cap = max(0.0, global_budget * (1.0 - reserve))
    remaining = cap
    allocated: list[dict[str, object]] = []
    starved: list[str] = []
    ordered: list[AgentBid]
    if method == "equal":
        share = cap / max(1, len(bids))
        for bid in bids:
            take = min(share, bid.cost, remaining)
            if take + 1e-12 < bid.cost:
                starved.append(bid.agent_id)
            else:
                remaining -= take
                allocated.append({"agent_id": bid.agent_id, "spend": take, "method": method})
    elif method == "priority":
        ordered = sorted(bids, key=lambda item: (-item.priority, item.agent_id))
        for bid in ordered:
            if bid.cost <= remaining:
                remaining -= bid.cost
                allocated.append({"agent_id": bid.agent_id, "spend": bid.cost, "method": method})
            else:
                starved.append(bid.agent_id)
    elif method == "knapsack":
        # 0-1 knapsack by value/cost then fill.
        ordered = sorted(bids, key=lambda item: (-robust_bid(item) / max(item.cost, 1e-6), item.agent_id))
        for bid in ordered:
            if bid.cost <= remaining:
                remaining -= bid.cost
                allocated.append({"agent_id": bid.agent_id, "spend": bid.cost, "method": method})
            else:
                starved.append(bid.agent_id)
    elif method == "auction":
        ordered = sorted(bids, key=lambda item: (-robust_bid(item), item.agent_id))
        for bid in ordered:
            if bid.cost <= remaining:
                remaining -= bid.cost
                allocated.append({"agent_id": bid.agent_id, "spend": bid.cost, "bid": robust_bid(bid), "method": method})
            else:
                starved.append(bid.agent_id)
    else:  # greedy_voi
        ordered = sorted(bids, key=lambda item: (-robust_bid(item), item.agent_id))
        for bid in ordered:
            if bid.cost <= remaining:
                remaining -= bid.cost
                allocated.append({"agent_id": bid.agent_id, "spend": bid.cost, "method": method})
            else:
                starved.append(bid.agent_id)
    spend = sum(float(row["spend"]) for row in allocated)
    tenants = {}
    for bid in bids:
        tenants.setdefault(bid.tenant, 0.0)
    for row in allocated:
        tenant = next(b.tenant for b in bids if b.agent_id == row["agent_id"])
        tenants[tenant] = tenants.get(tenant, 0.0) + float(row["spend"])
    fairness = 0.0
    if tenants:
        mean = sum(tenants.values()) / len(tenants)
        fairness = 1.0 - (max(tenants.values()) - min(tenants.values())) / max(mean, 1e-6) / 2.0
    return {
        "method": method,
        "global_budget": global_budget,
        "cap": cap,
        "spend": spend,
        "within_cap": spend <= global_budget + 1e-9,
        "allocated": allocated,
        "starved": starved,
        "reserve_left": remaining + global_budget * reserve,
        "fairness": fairness,
        "tenants": tenants,
    }


def compare_allocators(bids: Sequence[AgentBid], *, global_budget: float) -> dict[str, object]:
    methods = ("equal", "priority", "greedy_voi", "knapsack", "auction")
    table = {method: allocate(bids, global_budget=global_budget, method=method) for method in methods}
    return {"methods": table, "all_within_cap": all(row["within_cap"] for row in table.values())}
