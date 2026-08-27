"""Regime rules: where extra acquisition is expected to help. Interpretability over black boxes."""

from __future__ import annotations

from typing import Mapping, Sequence


def regime_label(state: Mapping[str, float]) -> str:
    entropy = float(state.get("entropy") or 0.0)
    margin = float(state.get("margin") or 0.0)
    open_set = float(state.get("open_set_mass") or 0.0)
    if open_set >= 0.4:
        return "OPEN_SET_DEFER"
    if entropy >= 0.75 and margin <= 0.15:
        return "HIGH_UNCERTAINTY_ACQUIRE"
    if entropy <= 0.35 and margin >= 0.25:
        return "FAST_ANSWER"
    return "BORDERLINE"


def fit_rules(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        label = regime_label(
            {
                "entropy": float(row.get("entropy") or 0.0),
                "margin": float(row.get("margin") or 0.0),
                "open_set_mass": float(row.get("open_set_mass") or 0.0),
            }
        )
        bucket = counts.setdefault(label, {"n": 0, "delta_u_pos": 0})
        bucket["n"] += 1
        if float(row.get("delta_u") or 0.0) > 0:
            bucket["delta_u_pos"] += 1
    return {
        "rules": {
            "OPEN_SET_DEFER": "unknown_mass >= 0.4",
            "HIGH_UNCERTAINTY_ACQUIRE": "entropy >= 0.75 and margin <= 0.15",
            "FAST_ANSWER": "entropy <= 0.35 and margin >= 0.25",
            "BORDERLINE": "otherwise",
        },
        "counts": counts,
        "note": "Rules frozen before looking at a new holdout. Slice-discovered regimes stay exploratory.",
    }
