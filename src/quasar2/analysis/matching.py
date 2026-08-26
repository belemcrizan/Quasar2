"""Join FAST_ONLY and QUASAR_ALWAYS runs without silently dropping mismatches."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from quasar2.analysis.io_util import parse_bool, parse_float

FAST_POLICIES = frozenset({"fast_only", "top1"})
QUASAR_POLICIES = frozenset({"quasar_always", "v24"})
GATED_POLICIES = frozenset({"gated_quasar"})

ANALYSIS_SPLITS = frozenset({"calibration", "development"})
PROPOSAL_SPLITS = frozenset({"calibration"})
SEALED_SPLITS = frozenset({"sealed_test"})

MatchKey = tuple[str, str, str]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: row[key] for key in row} for row in csv.DictReader(handle)]


def load_run_directory(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    csv_path = root / "per_query_results.csv"
    if not csv_path.exists():
        csv_path = root / "raw_results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No per-query CSV in {root}")
    records = load_records_csv(csv_path)
    metrics: dict[str, Any] = {}
    for name in ("metrics.json", "manifest.json", "run_manifest.json"):
        candidate = root / name
        if candidate.exists():
            payload = load_json(candidate)
            metrics.update(payload)
    return {
        "run_dir": str(root.resolve()),
        "records": records,
        "snapshot_id": metrics.get("snapshot_id") or metrics.get("snapshot"),
        "stage": metrics.get("stage"),
        "benchmark_hash": metrics.get("benchmark_hash"),
        "n_instances": metrics.get("n_instances"),
        "methods": metrics.get("methods") or {},
        "summaries": metrics.get("summaries") or {},
        "schema_version": metrics.get("schema_version"),
        "metrics": metrics,
    }


def load_benchmark(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = load_json(Path(path))
    instances = payload.get("instances") or []
    return {str(item["query_id"]): item for item in instances}


def _index_policy(
    records: Sequence[Mapping[str, Any]],
    policies: frozenset[str],
    *,
    run_snapshot: str | None,
    run_dir: str,
) -> tuple[dict[MatchKey, dict[str, Any]], list[dict[str, Any]]]:
    indexed: dict[MatchKey, dict[str, Any]] = {}
    unmatched: list[dict[str, Any]] = []
    seen: dict[MatchKey, int] = {}
    snap_key = str(run_snapshot or "")
    for row in records:
        policy = str(row.get("policy") or "")
        if policy not in policies:
            continue
        backend = str(row.get("backend") or "")
        query_id = str(row.get("query_id") or "")
        key: MatchKey = (backend, snap_key, query_id)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            unmatched.append(
                {
                    "query_id": query_id,
                    "backend": backend,
                    "policy": policy,
                    "reason": "DUPLICATE_QUERY_ID",
                    "run_dir": run_dir,
                    "snapshot_id": snap_key,
                }
            )
            continue
        indexed[key] = dict(row)
        indexed[key]["_run_snapshot"] = run_snapshot
        indexed[key]["_run_dir"] = run_dir
        indexed[key]["_benchmark_hash"] = None
    return indexed, unmatched


def match_fast_quasar(
    runs: Sequence[Mapping[str, Any]],
    *,
    benchmark: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """One-to-one join on (backend, snapshot_id, query_id)."""

    unmatched: list[dict[str, Any]] = []
    fast: dict[MatchKey, dict[str, Any]] = {}
    quasar: dict[MatchKey, dict[str, Any]] = {}
    gated: dict[MatchKey, dict[str, Any]] = {}

    for run in runs:
        records = list(run["records"])
        snap = run.get("snapshot_id")
        run_dir = str(run.get("run_dir") or "")
        bench_hash = run.get("benchmark_hash")
        f_idx, f_bad = _index_policy(records, FAST_POLICIES, run_snapshot=snap, run_dir=run_dir)
        q_idx, q_bad = _index_policy(records, QUASAR_POLICIES, run_snapshot=snap, run_dir=run_dir)
        g_idx, g_bad = _index_policy(records, GATED_POLICIES, run_snapshot=snap, run_dir=run_dir)
        unmatched.extend(f_bad + q_bad + g_bad)
        for key, row in f_idx.items():
            row["_benchmark_hash"] = bench_hash
            if key in fast:
                unmatched.append(
                    {
                        "query_id": key[2],
                        "backend": key[0],
                        "snapshot_id": key[1],
                        "reason": "DUPLICATE_QUERY_ID",
                        "policy": "FAST_ONLY",
                        "run_dir": run_dir,
                    }
                )
                continue
            fast[key] = row
        for key, row in q_idx.items():
            row["_benchmark_hash"] = bench_hash
            if key in quasar:
                unmatched.append(
                    {
                        "query_id": key[2],
                        "backend": key[0],
                        "snapshot_id": key[1],
                        "reason": "DUPLICATE_QUERY_ID",
                        "policy": "QUASAR_ALWAYS",
                        "run_dir": run_dir,
                    }
                )
                continue
            quasar[key] = row
        for key, row in g_idx.items():
            row["_benchmark_hash"] = bench_hash
            gated[key] = row

    matched: list[dict[str, Any]] = []
    keys = set(fast) | set(quasar) | set(gated)
    bench = benchmark or {}
    for key in sorted(keys):
        backend, snapshot_id, query_id = key
        f_row = fast.get(key)
        q_row = quasar.get(key)
        g_row = gated.get(key)
        if f_row is None or q_row is None:
            unmatched.append(
                {
                    "query_id": query_id,
                    "backend": backend,
                    "snapshot_id": snapshot_id,
                    "reason": "MISSING_FAST" if f_row is None else "MISSING_QUASAR",
                    "fast_present": f_row is not None,
                    "quasar_present": q_row is not None,
                    "gated_present": g_row is not None,
                }
            )
            continue
        f_snap = f_row.get("_run_snapshot")
        q_snap = q_row.get("_run_snapshot")
        if f_snap and q_snap and f_snap != q_snap:
            unmatched.append(
                {
                    "query_id": query_id,
                    "backend": backend,
                    "reason": "SNAPSHOT_MISMATCH",
                    "fast_snapshot": f_snap,
                    "quasar_snapshot": q_snap,
                }
            )
            continue
        f_hash = f_row.get("_benchmark_hash")
        q_hash = q_row.get("_benchmark_hash")
        if f_hash and q_hash and f_hash != q_hash:
            unmatched.append(
                {
                    "query_id": query_id,
                    "backend": backend,
                    "reason": "SCHEMA_CONFLICT",
                    "detail": "benchmark_hash mismatch",
                    "fast_hash": f_hash,
                    "quasar_hash": q_hash,
                }
            )
            continue
        if str(f_row.get("canonical_intent_id") or "") != str(q_row.get("canonical_intent_id") or ""):
            unmatched.append(
                {
                    "query_id": query_id,
                    "backend": backend,
                    "reason": "SCHEMA_CONFLICT",
                    "detail": "canonical_intent_id mismatch",
                }
            )
            continue
        instance = bench.get(query_id) or {}
        value_ref = str((instance.get("expected_observation") or {}).get("value_ref") or "")
        pair_snap = str(f_snap or q_snap or snapshot_id or "")
        if instance and value_ref and pair_snap and pair_snap not in value_ref:
            instance = {}
        matched.append(
            {
                "backend": backend,
                "query_id": query_id,
                "snapshot_id": f_snap or q_snap or snapshot_id or "",
                "fast": f_row,
                "quasar": q_row,
                "gated": g_row,
                "instance": instance,
            }
        )
    fast_snaps: dict[tuple[str, str], set[str]] = {}
    quasar_snaps: dict[tuple[str, str], set[str]] = {}
    for backend, snapshot_id, query_id in fast:
        fast_snaps.setdefault((backend, query_id), set()).add(snapshot_id)
    for backend, snapshot_id, query_id in quasar:
        quasar_snaps.setdefault((backend, query_id), set()).add(snapshot_id)
    for pair, fsnaps in fast_snaps.items():
        qsnaps = quasar_snaps.get(pair, set())
        if fsnaps and qsnaps and fsnaps.isdisjoint(qsnaps):
            unmatched.append(
                {
                    "query_id": pair[1],
                    "backend": pair[0],
                    "reason": "SNAPSHOT_MISMATCH",
                    "fast_snapshot": ",".join(sorted(fsnaps)),
                    "quasar_snapshot": ",".join(sorted(qsnaps)),
                }
            )
    return {"matched": matched, "unmatched": unmatched}


def as_correct(row: Mapping[str, Any]) -> bool:
    return parse_bool(row.get("intent_exact"))


def numeric_feature(row: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return parse_float(row[name])
    return None


def iter_backends(matched: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(sorted({str(row["backend"]) for row in matched}))
