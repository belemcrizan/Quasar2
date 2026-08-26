"""Clustered association helpers and low-base-rate metrics."""

from __future__ import annotations

from typing import Sequence

from quasar2.math.association import auprc, auroc, brier, pearson, reliability_bins, r_squared, spearman
from quasar2.math.bootstrap import cluster_bootstrap_spearman_difference
from quasar2.math.linear import dot, ridge_fit


def ece(scores: Sequence[float], targets: Sequence[float], *, bins: int = 8) -> float | None:
    table = reliability_bins(scores, targets, bins=bins)
    n = sum(int(row["n"]) for row in table)
    if n == 0:
        return None
    return sum(abs(float(row["calibration_gap"])) * int(row["n"]) for row in table) / n


def precision_at_k(scores: Sequence[float], labels: Sequence[int], k: int) -> float | None:
    if k <= 0 or not scores:
        return None
    ordered = sorted(zip(scores, labels), key=lambda item: -item[0])[:k]
    if not ordered:
        return None
    return sum(int(lab) for _, lab in ordered) / len(ordered)


def recall_at_k(scores: Sequence[float], labels: Sequence[int], k: int) -> float | None:
    total = sum(int(lab) for lab in labels)
    if total == 0 or k <= 0:
        return None
    ordered = sorted(zip(scores, labels), key=lambda item: -item[0])[:k]
    return sum(int(lab) for _, lab in ordered) / total


def topk_uplift(
    scores: Sequence[float],
    utilities: Sequence[float],
    k: int,
) -> dict[str, float | None]:
    if k <= 0 or not scores:
        return {"k": k, "mean_selected": None, "mean_all": None, "uplift": None}
    ordered = sorted(zip(scores, utilities), key=lambda item: -item[0])[:k]
    mean_sel = sum(u for _, u in ordered) / len(ordered)
    mean_all = sum(utilities) / len(utilities)
    return {"k": k, "mean_selected": mean_sel, "mean_all": mean_all, "uplift": mean_sel - mean_all}


def prevalence(values: Sequence[float], delta: float) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if v > delta) / len(values)


def incremental_models(
    train: Sequence[dict],
    test: Sequence[dict],
    *,
    y_key: str,
    extra: Sequence[str],
) -> dict[str, object]:
    if not train or not test:
        return {"status": "empty"}
    y_train = [float(row[y_key]) for row in train]
    m0_tr = [[1.0, float(row["entropy"]), float(row["belief_margin"])] for row in train]
    m1_tr = [m0 + [float(row[name]) for name in extra] for row, m0 in zip(train, m0_tr)]
    w0 = ridge_fit(m0_tr, y_train, lam=1e-2)
    w1 = ridge_fit(m1_tr, y_train, lam=1e-2)
    m0_te = [[1.0, float(row["entropy"]), float(row["belief_margin"])] for row in test]
    m1_te = [m0 + [float(row[name]) for name in extra] for row, m0 in zip(test, m0_te)]
    p0 = [dot(w0, f) for f in m0_te]
    p1 = [dot(w1, f) for f in m1_te]
    y = [float(row[y_key]) for row in test]
    clusters = [str(row["cluster_id"]) for row in test]
    return {
        "m0_spearman": spearman(p0, y),
        "m1_spearman": spearman(p1, y),
        "m0_r2": r_squared(p0, y),
        "m1_r2": r_squared(p1, y),
        "delta_spearman": None
        if spearman(p0, y) is None or spearman(p1, y) is None
        else spearman(p1, y) - spearman(p0, y),
        "cluster_bootstrap_delta_spearman": cluster_bootstrap_spearman_difference(
            p1, p0, y, clusters, samples=400, seed=0
        ),
        "weights_m0": w0,
        "weights_m1": w1,
        "n_train": len(train),
        "n_test": len(test),
    }


def interaction_fit(train: Sequence[dict], test: Sequence[dict], *, y_key: str) -> dict[str, object]:
    """DeltaU ~ U + R + U*R + M + R*M. Observational; not a causal claim."""

    def design(row: dict) -> list[float]:
        u = float(row["entropy"])
        r = float(row["R_hat"])
        m = float(row.get("mismatch_mu_true") or 0.0)
        return [1.0, u, r, u * r, m, r * m]

    if not train or not test:
        return {"status": "empty"}
    y_train = [float(row[y_key]) for row in train]
    w = ridge_fit([design(row) for row in train], y_train, lam=1e-2)
    pred = [dot(w, design(row)) for row in test]
    y = [float(row[y_key]) for row in test]
    return {
        "coefficients": {
            "intercept": w[0],
            "entropy": w[1],
            "R_hat": w[2],
            "entropy_x_R": w[3],
            "mismatch": w[4],
            "R_x_mismatch": w[5],
        },
        "test_spearman": spearman(pred, y),
        "test_r2": r_squared(pred, y),
        "causal_claim": False,
    }


__all__ = [
    "auprc",
    "auroc",
    "brier",
    "pearson",
    "r_squared",
    "spearman",
    "ece",
    "precision_at_k",
    "recall_at_k",
    "topk_uplift",
    "prevalence",
    "incremental_models",
    "interaction_fit",
]
