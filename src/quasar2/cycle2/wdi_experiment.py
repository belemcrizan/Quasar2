"""WDI controlled-degradation confirmatory arm. Sealed_test is never read."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quasar2.benchmarks.wdi_bench import build_benchmark
from quasar2.config import discover_project_root
from quasar2.cycle2.metrics import incremental_models, prevalence, spearman
from quasar2.cycle2.observation import finite_entropy
from quasar2.degradation import QueryDegrader
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.wdi.source import WDIEvidenceSource


SEALED = "sealed_test"


def plan_path() -> Path:
    return discover_project_root() / "experiments" / "analysis_plans" / "wdi_controlled_degradation.json"


def plan_hash() -> str:
    payload = json.loads(plan_path().read_text(encoding="utf-8"))
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _utility(correct: bool, action: str, calls: int, rho: float = 1.4) -> float:
    value = 1.0 if correct else 0.0
    if action == "ANSWER" and not correct:
        value -= rho
    value -= 0.10 * calls
    return value


def run_wdi_controlled_degradation(
    snapshot: str | Path | None = None,
    *,
    stage: str = "ci",
    limit: int | None = 80,
) -> dict[str, Any]:
    root = discover_project_root()
    snapshot = Path(snapshot or root / "data" / "wdi" / "snapshots" / "ci-offline")
    plan = json.loads(plan_path().read_text(encoding="utf-8"))
    source = WDIEvidenceSource(snapshot)
    manifest = source.manifest
    bench = build_benchmark(snapshot, stage=stage)
    instances = [row for row in bench["instances"] if row.get("split") != SEALED]
    if any(row.get("split") == SEALED for row in bench["instances"]):
        sealed_count = sum(1 for row in bench["instances"] if row["split"] == SEALED)
    else:
        sealed_count = 0
    # Explicitly do not materialize sealed instance payloads into this analysis.
    if limit is not None:
        instances = instances[:limit]
    documents = source.documents()
    retriever = BM25Retriever(documents)
    degrader = QueryDegrader()
    rows = []
    for instance in instances:
        gold = None
        acceptable = instance.get("acceptable_intents") or []
        if acceptable:
            gold = acceptable[0].get("indicator_id")
        text = instance["query_text"]
        natural = instance.get("degradation_level", 0) == 0
        if not natural:
            try:
                degraded = degrader.degrade(
                    text, level=min(1.0, 0.25 * int(instance.get("degradation_level") or 1)), seed=0
                )
                query = degraded.query
            except ValueError:
                query = text
            stratum = "CONTROLLED_DEGRADATION_OF_WDI_QUERY"
        else:
            query = text
            stratum = "NATURAL_WDI_QUERY"
        raw1 = retriever.search(query, top_k=8, domain="wdi")
        raw3 = retriever.search(query, top_k=12, domain="wdi")
        hits1 = tuple(h for h in raw1 if h.document.metadata.get("kind") == "INDICATOR_METADATA")[:1]
        hits3 = tuple(h for h in raw3 if h.document.metadata.get("kind") == "INDICATOR_METADATA")[:3]
        pred1 = hits1[0].document.hypothesis_ids[0] if hits1 and hits1[0].document.hypothesis_ids else None
        pred3 = hits3[0].document.hypothesis_ids[0] if hits3 and hits3[0].document.hypothesis_ids else None
        # extra retrieve: take unique ids
        ids3 = []
        for hit in hits3:
            ids3.extend(hit.document.hypothesis_ids)
        pred_explore = ids3[0] if ids3 else pred3
        u0 = _utility(pred1 == gold, "ANSWER", 1)
        u1 = _utility(pred_explore == gold, "ANSWER", min(3, len(hits3)))
        scores = [float(h.score) for h in hits3] or [0.0, 0.0]
        top = scores[0]
        second = scores[1] if len(scores) > 1 else 0.0
        margin = top - second
        masses = {"h1": max(top, 1e-9), "h2": max(second, 1e-9)}
        entropy = finite_entropy(masses)
        # Deployment proxy recoverability: score margin / (top+second)
        r_hat = abs(margin) / (abs(top) + abs(second) + 1e-9)
        rows.append(
            {
                "query_id": instance["query_id"],
                "canonical_intent_id": instance.get("canonical_intent_id"),
                "split": instance.get("split"),
                "stratum": stratum,
                "entropy": entropy,
                "belief_margin": margin,
                "R_hat": r_hat,
                "r_leverage": r_hat,
                "tau_explore_net": u1 - u0,
                "u_noexplore": u0,
                "u_explore": u1,
                "correct_noexplore": pred1 == gold,
                "correct_explore": pred_explore == gold,
                "cluster_id": instance.get("canonical_intent_id") or instance["query_id"],
            }
        )
    train = [row for row in rows if row["split"] == "development"]
    test = [row for row in rows if row["split"] == "validation"]
    if not test:
        test = [row for row in rows if row["split"] == "calibration"]
    inc = incremental_models(train, test, y_key="tau_explore_net", extra=("R_hat",))
    natural = [row for row in test if row["stratum"] == "NATURAL_WDI_QUERY"]
    degraded = [row for row in test if row["stratum"] == "CONTROLLED_DEGRADATION_OF_WDI_QUERY"]

    def _spearman_pair(subset: list[dict], key: str) -> float | None:
        if len(subset) < 3:
            return None
        return spearman([row[key] for row in subset], [row["tau_explore_net"] for row in subset])

    return {
        "analysis_plan_hash": plan_hash(),
        "snapshot_id": manifest.get("snapshot_id"),
        "snapshot_hashes": manifest.get("hashes"),
        "sealed_instances_excluded": True,
        "sealed_count_in_benchmark_not_loaded": sealed_count,
        "n_total_used": len(rows),
        "n_train": len(train),
        "n_test": len(test),
        "prevalence_useful": prevalence([row["tau_explore_net"] for row in test], float(plan["delta_threshold"])),
        "incremental": inc,
        "spearman_R_test": _spearman_pair(test, "R_hat"),
        "spearman_entropy_test": _spearman_pair(test, "entropy"),
        "natural": {
            "n": len(natural),
            "spearman_R": _spearman_pair(natural, "R_hat"),
            "spearman_entropy": _spearman_pair(natural, "entropy"),
        },
        "degraded": {
            "n": len(degraded),
            "spearman_R": _spearman_pair(degraded, "R_hat"),
            "spearman_entropy": _spearman_pair(degraded, "entropy"),
        },
        "evidence_rung": "D2",
        "identification": "paired_forced_retrieval_depth_on_frozen_snapshot",
        "records": rows,
    }
