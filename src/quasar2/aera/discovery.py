"""Scientific discovery mode: choose observations by discrimination/cost, not relevance."""

from __future__ import annotations

from typing import Sequence


def select_observation(
    observations: Sequence[dict[str, float | str]],
) -> dict[str, object]:
    scored = []
    for row in observations:
        disc = float(row["discrimination"])
        cost = max(1e-6, float(row["cost"]))
        relevance = float(row.get("relevance") or 0.0)
        scored.append(
            {
                "id": row["id"],
                "score": disc / cost,
                "discrimination": disc,
                "relevance": relevance,
                "cost": cost,
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["id"]))
    winner = scored[0]
    relevance_winner = max(scored, key=lambda item: (item["relevance"], -item["cost"]))
    return {
        "chosen": winner["id"],
        "score": winner["score"],
        "differs_from_relevance": winner["id"] != relevance_winner["id"],
        "relevance_choice": relevance_winner["id"],
        "ranking": scored,
        "mode": "replay_simulation",
    }
