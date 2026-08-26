"""Empirical advantage region R* without leaking gold into the boundary model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from quasar2.math.linear import ridge_fit, dot


DEPLOYMENT_FEATURES = ("entropy", "R_hat", "mismatch_mu", "eta", "open_set", "unknown_mass")


def per_state_delta(
    rows: Sequence[Mapping[str, Any]],
    *,
    treatment: str = "empirical_myopic",
    baseline: str = "immediate_answer",
) -> list[dict[str, Any]]:
    left = {r["state_id"]: r for r in rows if r["policy"] == treatment}
    right = {r["state_id"]: r for r in rows if r["policy"] == baseline}
    out = []
    for sid in sorted(set(left) & set(right)):
        a = left[sid]
        b = right[sid]
        out.append(
            {
                "state_id": sid,
                "cluster_id": a["cluster_id"],
                "source": a["source"],
                "split_role": a["split_role"],
                "delta_q": float(a["neu"]) - float(b["neu"]),
                "entropy": float(a["entropy"]),
                "R_hat": float(a["R_hat"]),
                "mismatch_mu": float(a["mismatch_mu"]),
                "eta": float(a["eta"]),
                "open_set": 1.0 if a["open_set"] else 0.0,
                "unknown_mass": 1.0 if a["gold"] == "H_unknown" else 0.0,
                "recoverability_class": a["recoverability_class"],
            }
        )
    return out


def _x(row: Mapping[str, Any]) -> list[float]:
    return [
        1.0,
        float(row["entropy"]),
        float(row["R_hat"]),
        float(row["mismatch_mu"]),
        float(row["eta"]),
        float(row["open_set"]),
        float(row.get("unknown_mass", 0.0)),
        float(row["entropy"]) * float(row["R_hat"]),
        float(row["R_hat"]) * (1.0 - float(row["mismatch_mu"])),
    ]


def fit_interpretable(train: Sequence[Mapping[str, Any]]) -> list[float] | None:
    if len(train) < 12:
        return None
    y = [float(r["delta_q"]) for r in train]
    x = [_x(r) for r in train]
    return ridge_fit(x, y, lam=1e-2)


def simple_rule(row: Mapping[str, Any]) -> float:
    """Advantage if ambiguous, recoverable, cheap mismatch, not open-set junk."""

    if row["open_set"] >= 0.5:
        return -0.05
    if row["mismatch_mu"] >= 0.4:
        return -0.1
    if row["entropy"] < 0.35:
        return -0.15
    if row["R_hat"] > 0.15 and row["entropy"] >= 0.45:
        return 0.2
    return 0.0


def discover_regime(
    rows: Sequence[Mapping[str, Any]],
    *,
    train_roles: Sequence[str] = ("development",),
) -> dict[str, Any]:
    deltas = per_state_delta(rows)
    train = [d for d in deltas if d["split_role"] in set(train_roles)]
    held = [d for d in deltas if d["split_role"] not in set(train_roles)]
    weights = fit_interpretable(train)
    def score(row: Mapping[str, Any]) -> float:
        if weights is None:
            return simple_rule(row)
        return float(dot(weights, _x(row)))

    def metrics(block: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not block:
            return {"n": 0}
        pred = [score(r) for r in block]
        y = [float(r["delta_q"]) for r in block]
        simple = [simple_rule(r) for r in block]
        region = [r for r, p in zip(block, pred) if p > 0]
        outside = [r for r, p in zip(block, pred) if p <= 0]
        return {
            "n": len(block),
            "n_predicted_Rstar": len(region),
            "mean_delta_in_Rstar": (sum(r["delta_q"] for r in region) / len(region)) if region else None,
            "mean_delta_outside": (sum(r["delta_q"] for r in outside) / len(outside)) if outside else None,
            "mean_delta_all": sum(y) / len(y),
            "simple_rule_mean_signed_error": sum(abs(s - t) for s, t in zip(simple, y)) / len(y),
            "flexible_mean_signed_error": sum(abs(s - t) for s, t in zip(pred, y)) / len(y),
        }

    return {
        "features": list(DEPLOYMENT_FEATURES) + ["entropy*R_hat", "R_hat*(1-mismatch)"],
        "train_roles": list(train_roles),
        "weights": weights,
        "train": metrics(train),
        "heldout": metrics(held),
        "n_delta_states": len(deltas),
        "leakage": "gold/true_kernels not in features",
        "qualitative_structure": (
            "Candidate R*: high entropy AND sufficient R_hat AND low mismatch AND not open-set. "
            "Clear queries and high-mismatch channels are baseline-favoring."
        ),
    }


def by_ambiguity(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[float]] = {}
    myopic = [r for r in rows if r["policy"] == "empirical_myopic"]
    answer = {r["state_id"]: r for r in rows if r["policy"] == "immediate_answer"}
    for row in myopic:
        other = answer.get(row["state_id"])
        if other is None:
            continue
        delta = float(row["neu"]) - float(other["neu"])
        for label in row.get("ambiguity_class") or ["unlabeled"]:
            buckets.setdefault(str(label), []).append(delta)
    table = []
    for label, vals in sorted(buckets.items()):
        table.append({"ambiguity_label": label, "n": len(vals), "mean_delta_myopic_minus_answer": sum(vals) / len(vals)})
    return table
