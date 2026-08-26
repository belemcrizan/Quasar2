"""Recoverability vs empirical VoI. Synthetic kernels; not a WDI claim."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from quasar2.math.association import auprc, auroc, brier, pearson, reliability_bins, r_squared, spearman
from quasar2.math.voi import (
    bound_gap,
    empirical_binary_voi_zero_one,
    empirical_decision_flip_probability,
    voi_bound_binary,
)
from quasar2.recoverability import COMPARISON_PREDICTORS, ESTIMATORS, LearnedRecoverabilityEstimator
from quasar2.theory.kernels import KERNEL_FAMILIES, PROXY_KERNELS


PRIORS = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
TRAIN_FAMILIES = ("Bernoulli", "Categorical", "Gaussian", "Mixture")
HOLD_FAMILIES = ("HeavyOverlap", "NearIdentical", "Multimodal", "MisspecifiedTrue")
METHODS = (
    "tv",
    "kl",
    "symmetric_kl",
    "jsd",
    "mutual_information",
    "empirical_discrimination",
    "decision_recoverability",
    "belief_margin",
    "entropy",
    "retriever_score_margin",
    "embedding_separation",
    "learned",
)


def _kernels_for_estimate(family: str, true_pair: Mapping[str, Mapping[str, float]]) -> Mapping[str, Mapping[str, float]]:
    return PROXY_KERNELS.get(family, true_pair)


def _records(*, priors: tuple[float, ...] = PRIORS) -> list[dict[str, Any]]:
    learned = LearnedRecoverabilityEstimator()
    train_rows = []
    train_targets = []
    for family in TRAIN_FAMILIES:
        pair = KERNEL_FAMILIES[family]
        for b in priors:
            belief = {"H1": b, "H2": 1.0 - b}
            train_rows.append((belief, ("H1", "H2"), pair))
            train_targets.append(empirical_binary_voi_zero_one(b, pair["H1"], pair["H2"]))
    learned.fit(train_rows, train_targets)

    estimators = dict(ESTIMATORS)
    estimators.update(COMPARISON_PREDICTORS)
    estimators["learned"] = learned
    rows: list[dict[str, Any]] = []
    for family, pair in KERNEL_FAMILIES.items():
        used = _kernels_for_estimate(family, pair)
        for b in priors:
            belief = {"H1": b, "H2": 1.0 - b}
            voi = empirical_binary_voi_zero_one(b, pair["H1"], pair["H2"])
            flip = empirical_decision_flip_probability(b, pair["H1"], pair["H2"])
            bound = voi_bound_binary(b, pair["H1"], pair["H2"])
            stats = bound_gap(voi, bound.voi_bound_tv)
            harm = 1 if voi < -1e-12 else 0
            helps = 1 if voi > 1e-9 else 0
            row: dict[str, Any] = {
                "family": family,
                "split": "train" if family in TRAIN_FAMILIES else "holdout",
                "proxy_kernels": family in PROXY_KERNELS,
                "b": b,
                "voi_empirical": voi,
                "delta_decision_utility": voi,
                "p_explore_helps": helps,
                "p_retrieval_harms": harm,
                "decision_flip": flip,
                "voi_bound_tv": bound.voi_bound_tv,
                "voi_bound_tightness": stats["voi_bound_tightness"],
                "voi_bound_ratio": stats["voi_bound_ratio"],
                "identity_holds": bound.identity_holds,
            }
            for name in METHODS:
                result = estimators[name].estimate(belief, ("H1", "H2"), "EXPLORE", used)
                row[f"R_{name}"] = result.score
            rows.append(row)
    return rows


def _method_metrics(rows: list[dict[str, Any]], method: str, split: str | None) -> dict[str, Any]:
    subset = [row for row in rows if split is None or row["split"] == split]
    scores = [row[f"R_{method}"] for row in subset]
    voi = [row["voi_empirical"] for row in subset]
    helps = [row["p_explore_helps"] for row in subset]
    harms = [row["p_retrieval_harms"] for row in subset]
    max_voi = max((abs(value) for value in voi), default=1.0) or 1.0
    scaled = [0.0 if math_inf(score) else max(0.0, min(1.0, float(score) / max(1e-9, max_voi))) for score in scores]
    return {
        "method": method,
        "split": split or "all",
        "n": len(subset),
        "spearman_voi": spearman(scores, voi),
        "pearson_voi": pearson(scores, voi),
        "r2_voi": r_squared(scores, voi),
        "spearman_delta_u": spearman(scores, [row["delta_decision_utility"] for row in subset]),
        "auroc_helps": auroc(scores, helps),
        "auprc_helps": auprc(scores, helps),
        "brier_helps": brier(scaled, helps),
        "auroc_harm": auroc(scores, harms),
        "mean_voi": sum(voi) / len(voi) if voi else None,
        "reliability": reliability_bins(scaled, [float(v) for v in helps]),
    }


def math_inf(value: float) -> bool:
    return value != value or value in (float("inf"), float("-inf"))


def run_recoverability_benchmark(*, priors: tuple[float, ...] = PRIORS) -> dict[str, Any]:
    rows = _records(priors=priors)
    summaries = []
    for method in METHODS:
        for split in ("train", "holdout", None):
            summaries.append(_method_metrics(rows, method, split))
    holdout = [row for row in summaries if row["split"] == "holdout" and row["spearman_voi"] is not None]
    holdout_sorted = sorted(holdout, key=lambda item: -(item["spearman_voi"] or -2.0))
    tightness = {}
    for row in rows:
        key = str(row["voi_bound_tightness"])
        tightness[key] = tightness.get(key, 0) + 1
    bayes_harm_rate = sum(row["p_retrieval_harms"] for row in rows) / max(1, len(rows))
    best = holdout_sorted[0]["method"] if holdout_sorted else None
    entropy_row = next((item for item in holdout_sorted if item["method"] == "entropy"), None)
    drs_row = next((item for item in holdout_sorted if item["method"] == "decision_recoverability"), None)
    return {
        "schema_version": "recoverability_bench.1",
        "dataset": "synthetic_kernel_families",
        "n": len(rows),
        "priors": list(priors),
        "train_families": list(TRAIN_FAMILIES),
        "holdout_families": list(HOLD_FAMILIES),
        "tightness_counts": tightness,
        "bayes_retrieval_harm_rate": bayes_harm_rate,
        "best_holdout_spearman": best,
        "entropy_holdout_spearman": None if entropy_row is None else entropy_row["spearman_voi"],
        "drs_holdout_spearman": None if drs_row is None else drs_row["spearman_voi"],
        "summaries": summaries,
        "records": rows,
        "notes": (
            "Learned estimator is fit on TRAIN_FAMILIES only. "
            "Bayes 0-1 VoI is nonnegative, so retrieval harm under the true kernel is ~0. "
            "Proxy kernels for MisspecifiedTrue are HeavyOverlap."
        ),
    }


def write_recoverability_benchmark(dest: Path, payload: dict[str, Any] | None = None) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    payload = payload or run_recoverability_benchmark()
    json_path = dest / "recoverability_bench.json"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md = dest / "recoverability_bench.md"
    lines = [
        "# Recoverability vs empirical VoI",
        "",
        f"N={payload['n']} synthetic binary states. Seed aggregation: none (deterministic kernels).",
        f"Best holdout Spearman: `{payload['best_holdout_spearman']}`.",
        f"Entropy holdout Spearman: {payload['entropy_holdout_spearman']}.",
        f"DRS holdout Spearman: {payload['drs_holdout_spearman']}.",
        f"Bayes retrieval harm rate: {payload['bayes_retrieval_harm_rate']}.",
        f"T2 tightness counts: {payload['tightness_counts']}.",
        "",
        "| method | split | Spearman VoI | Pearson | AUROC helps | Brier |",
        "|---|---|---|---|---|---|",
    ]
    for row in payload["summaries"]:
        if row["split"] not in {"holdout", "train"}:
            continue
        lines.append(
            f"| {row['method']} | {row['split']} | {row['spearman_voi']} | {row['pearson_voi']} | "
            f"{row['auroc_helps']} | {row['brier_helps']} |"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    csv_path = dest / "recoverability_bench.csv"
    records = payload["records"]
    if records:
        keys = list(records[0])
        csv_path.write_text(
            ",".join(keys) + "\n" + "\n".join(",".join(json.dumps(row[key]) for key in keys) for row in records),
            encoding="utf-8",
        )
    return json_path
