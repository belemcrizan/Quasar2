"""Recoverability 3.0: per-action P(ΔU>0 | pre-action state)."""

from __future__ import annotations

from typing import Mapping, Sequence

from quasar2.rescue.leakage import FORBIDDEN_DEPLOYMENT_FIELDS, LeakageError
from quasar2.rescue.recoverability import auprc, auroc, brier, fit_logreg, predict_logreg


ALLOWED = (
    "entropy",
    "margin",
    "disagreement",
    "hypothesis_stability",
    "open_set_mass",
    "source_coverage",
    "cost",
    "deadline_slack",
    "domain_signal",
    "channel_available",
)


def features_v3(row: Mapping[str, object]) -> dict[str, float]:
    leak = FORBIDDEN_DEPLOYMENT_FIELDS.intersection(row)
    if leak:
        raise LeakageError(f"R3 features saw gold keys {sorted(leak)}")
    packed = {
        "entropy": float(row.get("entropy") or row.get("fast_entropy") or 0.0),
        "margin": float(row.get("margin") or row.get("fast_margin") or 0.0),
        "disagreement": float(row.get("disagreement") or 0.0),
        "hypothesis_stability": float(row.get("hypothesis_stability") or 1.0),
        "open_set_mass": float(row.get("open_set_mass") or row.get("fast_unknown_mass") or 0.0),
        "source_coverage": float(row.get("source_coverage") or 0.5),
        "cost": float(row.get("cost") or 0.1),
        "deadline_slack": float(row.get("deadline_slack") or 1.0),
        "domain_signal": float(row.get("domain_signal") or row.get("signal_quality") or 0.0),
        "channel_available": float(row.get("channel_available") or 1.0),
    }
    if FORBIDDEN_DEPLOYMENT_FIELDS.intersection(packed):
        raise LeakageError("gold leaked into packed R3 features")
    return packed


def vector(feats: Mapping[str, float]) -> list[float]:
    return [float(feats[name]) for name in ALLOWED]


def fit_action_models(
    rows: Sequence[Mapping[str, object]],
    *,
    actions: Sequence[str],
) -> dict[str, dict[str, object]]:
    models: dict[str, dict[str, object]] = {}
    for action in actions:
        xs: list[list[float]] = []
        ys: list[int] = []
        for row in rows:
            if str(row.get("action")) != action:
                continue
            xs.append(vector(features_v3(row)))
            ys.append(1 if float(row.get("delta_u") or 0.0) > 0 else 0)
        if len(xs) < 4 or sum(ys) == 0 or sum(ys) == len(ys):
            models[action] = {"status": "UNDERPOWERED", "n": len(xs), "positives": sum(ys)}
            continue
        weights, bias = fit_logreg(xs, ys)
        scores = [predict_logreg(x, weights, bias) for x in xs]
        models[action] = {
            "status": "FIT_IN_SAMPLE_ONLY",
            "n": len(xs),
            "positives": sum(ys),
            "weights": weights,
            "bias": bias,
            "auroc": auroc(scores, ys),
            "auprc": auprc(scores, ys),
            "brier": brier(scores, ys),
            "note": "In-sample diagnostics. Confirmatory AUROC requires a held-out intent split.",
        }
    return models


def estimate_r(
    feats: Mapping[str, float],
    model: Mapping[str, object],
) -> dict[str, float | str]:
    if model.get("status") != "FIT_IN_SAMPLE_ONLY":
        entropy = float(feats.get("entropy") or 0.0)
        hat = max(0.05, min(0.6, 0.4 * entropy))
        return {"r_hat": hat, "sigma_r": 0.25, "m_r": 0.4, "status": str(model.get("status") or "PRIOR")}
    r_hat = predict_logreg(vector(feats), list(model["weights"]), float(model["bias"]))
    return {"r_hat": r_hat, "sigma_r": 0.12, "m_r": 0.2, "status": "MODEL"}
