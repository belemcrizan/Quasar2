"""Cross-source / cross-instrument / temporal / cross-domain transfer."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from quasar2.external.evaluate import evaluate_states, paired_delta


def _subset(rows: Sequence[Mapping[str, Any]], role: str) -> list[Mapping[str, Any]]:
    return [r for r in rows if r["split_role"] == role]


def shift_metrics(dev: Sequence[Mapping[str, Any]], other: Sequence[Mapping[str, Any]], policy: str) -> dict[str, Any]:
    def mean_for(block: Sequence[Mapping[str, Any]], key: str) -> float | None:
        vals = [float(r[key]) for r in block if r["policy"] == policy]
        if not vals:
            return None
        return sum(vals) / len(vals)

    keys = {
        "neu": "neu",
        "entropy": "entropy",
        "R_hat": "R_hat",
    }
    out = {"policy": policy, "n_dev": sum(1 for r in dev if r["policy"] == policy), "n_other": sum(1 for r in other if r["policy"] == policy)}
    for name, key in keys.items():
        a = mean_for(dev, key)
        b = mean_for(other, key)
        out[f"{name}_dev"] = a
        out[f"{name}_other"] = b
        out[f"{name}_shift"] = None if a is None or b is None else b - a
    def rate(block, action):
        sel = [r for r in block if r["policy"] == policy]
        if not sel:
            return None
        return sum(1 for r in sel if r["action"] == action) / len(sel)
    out["explore_rate_shift"] = None if rate(dev, "EXPLORE") is None or rate(other, "EXPLORE") is None else rate(other, "EXPLORE") - rate(dev, "EXPLORE")
    out["false_answer_shift"] = None
    fa_d = [float(r["false_answer"]) for r in dev if r["policy"] == policy]
    fa_o = [float(r["false_answer"]) for r in other if r["policy"] == policy]
    if fa_d and fa_o:
        out["false_answer_shift"] = sum(fa_o) / len(fa_o) - sum(fa_d) / len(fa_d)
    return out


def transfer_matrix(rows: Sequence[Mapping[str, Any]], *, seed: int) -> dict[str, Any]:
    roles = sorted({str(r["split_role"]) for r in rows})
    matrix = []
    for role in roles:
        block = _subset(rows, role)
        delta = paired_delta(block, "empirical_myopic", "immediate_answer", seed=seed)
        delta_e = paired_delta(block, "empirical_myopic", "entropy_only", seed=seed)
        matrix.append(
            {
                "split_role": role,
                "n": len({r["state_id"] for r in block}),
                "n_clusters": len({r["cluster_id"] for r in block}),
                "delta_vs_answer": delta,
                "delta_vs_entropy": delta_e,
            }
        )
    dev = _subset(rows, "development")
    shifts = {}
    for role in roles:
        if role == "development":
            continue
        shifts[role] = shift_metrics(dev, _subset(rows, role), "empirical_myopic")
        shifts[role]["performance_drop_neu"] = shifts[role].get("neu_shift")
        shifts[role]["recoverability_shift"] = shifts[role].get("R_hat_shift")
        shifts[role]["regret_shift_proxy"] = shifts[role].get("neu_shift")
        shifts[role]["action_distribution_shift_explore"] = shifts[role].get("explore_rate_shift")
        shifts[role]["calibration_shift_entropy"] = shift_metrics(dev, _subset(rows, role), "entropy_only").get("entropy_shift")
    return {"roles": roles, "matrix": matrix, "shifts_from_development": shifts}


def adaptation_ladder(
    states: Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    """Zero-shot is the primary number. Calibration/limited/full are labeled separately."""

    pack = evaluate_states(states, seed=seed, bootstrap_samples=80)
    rows = pack["rows"]
    zero_shot = transfer_matrix(rows, seed=seed)
    return {
        "zero_shot": zero_shot,
        "calibration_only": {"status": "NOT_RUN_PRIMARY_IS_ZERO_SHOT", "note": "No threshold retuned on ESA/ALMA."},
        "limited_adaptation": {"status": "NOT_RUN"},
        "full_adaptation": {"status": "NOT_RUN", "note": "Would leak if done before zero-shot; blocked."},
        "summaries": pack["summaries"],
        "rows": rows,
    }
