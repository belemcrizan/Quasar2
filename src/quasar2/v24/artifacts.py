"""Machine-readable cycle artifacts. Claims stay exploratory until a sealed run."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import platform
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    index = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return float(ordered[index])


def paired_mean_ci(
    left: Sequence[float],
    right: Sequence[float],
    *,
    samples: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    pairs = list(zip(left, right))
    if not pairs:
        return {"n": 0.0, "difference": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    observed = statistics.fmean(a - b for a, b in pairs)
    rng = random.Random(seed)
    diffs = []
    for _ in range(samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        diffs.append(statistics.fmean(a - b for a, b in sample))
    return {
        "n": float(len(pairs)),
        "difference": observed,
        "ci_low": percentile(diffs, 0.025),
        "ci_high": percentile(diffs, 0.975),
    }


def environment_text() -> str:
    lines = [
        f"python={sys.version.split()[0]}",
        f"platform={platform.platform()}",
        f"implementation={platform.python_implementation()}",
    ]
    try:
        import importlib.metadata as metadata

        for name in ("sentence-transformers", "torch", "numpy"):
            try:
                lines.append(f"{name}={metadata.version(name)}")
            except metadata.PackageNotFoundError:
                lines.append(f"{name}=absent")
    except Exception as error:
        lines.append(f"metadata_error={error}")
    return "\n".join(lines) + "\n"


def write_cycle_artifacts(
    dest: Path,
    *,
    payload: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    source_manifest: Mapping[str, Any],
    model_manifest: Mapping[str, Any],
    paired: Sequence[Mapping[str, Any]],
    claim_status: Mapping[str, Any],
    latency_summary: Mapping[str, Any],
    run_kind: str,
) -> dict[str, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    paths = {
        "metrics": dest / "metrics.json",
        "run_manifest": dest / "run_manifest.json",
        "source_manifest": dest / "source_manifest.json",
        "model_manifest": dest / "model_manifest.json",
        "per_query": dest / "per_query_results.csv",
        "paired": dest / "paired_comparisons.csv",
        "latency": dest / "latency_summary.json",
        "claim_status": dest / "claim_status.json",
        "environment": dest / "environment.txt",
        "manifest": dest / "manifest.json",
    }
    paths["metrics"].write_text(json.dumps(dict(payload), indent=2), encoding="utf-8")
    paths["source_manifest"].write_text(json.dumps(dict(source_manifest), indent=2), encoding="utf-8")
    paths["model_manifest"].write_text(json.dumps(dict(model_manifest), indent=2), encoding="utf-8")
    paths["latency"].write_text(json.dumps(dict(latency_summary), indent=2), encoding="utf-8")
    paths["claim_status"].write_text(json.dumps(dict(claim_status), indent=2), encoding="utf-8")
    paths["environment"].write_text(environment_text(), encoding="utf-8")
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    paths["run_manifest"].write_text(
        json.dumps(
            {
                "run_kind": run_kind,
                "created_at": created,
                "schema_version": payload.get("schema_version"),
                "snapshot_id": payload.get("snapshot_id"),
                "n_instances": payload.get("n_instances"),
                "n_records": len(records),
                "methods": payload.get("methods"),
                "status": payload.get("status"),
                "claim_boundary": payload.get("claim_boundary"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["manifest"].write_text(
        json.dumps(
            {
                "run_kind": run_kind,
                "snapshot_id": payload.get("snapshot_id"),
                "stage": payload.get("stage"),
                "n_records": len(records),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if records:
        with paths["per_query"].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    else:
        paths["per_query"].write_text("", encoding="utf-8")
    if paired:
        with paths["paired"].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(paired[0].keys()))
            writer.writeheader()
            writer.writerows(paired)
    else:
        paths["paired"].write_text("comparison\n", encoding="utf-8")
    return paths


def latency_summary_from_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = f"{record.get('backend')}|{record.get('policy')}"
        grouped.setdefault(key, []).append(dict(record))
    out: dict[str, Any] = {}
    for key, rows in grouped.items():
        lat = [float(row.get("latency_ms") or 0.0) for row in rows]
        out[key] = {
            "n": len(rows),
            "mean_ms": statistics.fmean(lat) if lat else 0.0,
            "p50_ms": percentile(lat, 0.50),
            "p95_ms": percentile(lat, 0.95),
            "p99_ms": percentile(lat, 0.99),
            "mean_gate_ms": statistics.fmean(float(row.get("gate_ms") or 0.0) for row in rows) if rows else 0.0,
            "mean_retrieval_ms": statistics.fmean(float(row.get("retrieval_ms") or 0.0) for row in rows) if rows else 0.0,
            "mean_compute_proxy": statistics.fmean(float(row.get("compute_proxy") or 0.0) for row in rows) if rows else 0.0,
        }
    return out
