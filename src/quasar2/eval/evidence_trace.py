"""Section-2 historical observations: versioned, not treated as timeless."""

from __future__ import annotations

from typing import Any

from quasar2.eval.recoverability_bench import run_recoverability_benchmark


HISTORICAL_SECTION2: tuple[dict[str, Any], ...] = (
    {
        "metric_name": "DRS holdout Spearman vs synthetic empirical VoI",
        "point_estimate": 0.620,
        "run_id": None,
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
        "note": "Cited from CLAIM_LEDGER H-uncertainty-retrieval; no immutable recoverability_bench.json in-repo.",
    },
    {
        "metric_name": "JSD/MI holdout Spearman",
        "point_estimate": 0.602,
        "run_id": None,
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
    },
    {
        "metric_name": "entropy holdout Spearman",
        "point_estimate": 0.545,
        "run_id": None,
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
    },
    {
        "metric_name": "learned ridge holdout Spearman",
        "point_estimate": 0.544,
        "run_id": None,
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
        "note": "Ledger also records train overfit relative to holdout.",
    },
    {
        "metric_name": "TV holdout Spearman",
        "point_estimate": 0.443,
        "run_id": None,
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
    },
    {
        "metric_name": "T2 bound vacuous on substantial fraction of synthetic states",
        "point_estimate": None,
        "run_id": None,
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
        "note": "CLAIM_LEDGER T2-binary-voi: vacuous 40 / useful 32 / tight 8 / loose 8 of 88 states.",
    },
    {
        "metric_name": "T2-as-point-policy worse than crude threshold",
        "point_estimate": None,
        "run_id": "p0-policy-compare",
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
        "note": "Ledger H-learned-beats-voi: myopic 0.279 regret vs threshold 0.218; myopic used bound as VoI.",
    },
    {
        "metric_name": "shadow 120 agreement",
        "point_estimate": 0.633,
        "run_id": "p0-shadow-120",
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
        "note": "76/120 agree; 0 EXPLORE recommendations.",
    },
    {
        "metric_name": "shadow recommended EXPLORE count on easy 120 fixture",
        "point_estimate": 0,
        "run_id": "p0-shadow-120",
        "artifact_path": None,
        "status": "UNVERIFIED_HISTORICAL_OBSERVATION",
    },
)


def _summary_value(payload: dict[str, Any], method: str, field: str) -> float | None:
    for row in payload["summaries"]:
        if row["method"] == method and row["split"] == "holdout":
            value = row.get(field)
            return None if value is None else float(value)
    return None


def trace_section2_metrics() -> dict[str, Any]:
    recomputed = run_recoverability_benchmark()
    current = {
        "drs_holdout_spearman": recomputed["drs_holdout_spearman"],
        "entropy_holdout_spearman": recomputed["entropy_holdout_spearman"],
        "best_holdout_spearman": recomputed["best_holdout_spearman"],
        "jsd_holdout_spearman": _summary_value(recomputed, "jsd", "spearman_voi"),
        "tv_holdout_spearman": _summary_value(recomputed, "tv", "spearman_voi"),
        "learned_holdout_spearman": _summary_value(recomputed, "learned", "spearman_voi"),
        "learned_train_spearman": next(
            (
                row["spearman_voi"]
                for row in recomputed["summaries"]
                if row["method"] == "learned" and row["split"] == "train"
            ),
            None,
        ),
        "tightness_counts": recomputed["tightness_counts"],
        "n": recomputed["n"],
        "schema_version": recomputed["schema_version"],
        "label": "RECOMPUTED_THIS_CYCLE",
        "does_not_supersede_historical": True,
    }
    return {
        "historical": list(HISTORICAL_SECTION2),
        "recomputed_recoverability_bench": current,
        "graph_assisted_retrieval": "NOT_IMPLEMENTED",
        "neural_retrieval": "OPTIONAL / IMPLEMENTED PATH, subject to repository verification",
        "n4_reranker_evaluation": "NOT_EXECUTED, subject to repository verification",
    }
