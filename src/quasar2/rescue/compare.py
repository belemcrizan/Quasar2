"""Compare two rescue-cycle run manifests without claiming improvement on overlapping CIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _load(path: Path) -> dict[str, Any]:
    manifest = path / "run_manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))


def _ci_excludes_zero(block: Mapping[str, Any] | None) -> bool | None:
    if not block:
        return None
    boot = block.get("cluster_bootstrap") or {}
    low, high = boot.get("ci_low"), boot.get("ci_high")
    if low is None or high is None:
        return None
    return not (low <= 0 <= high)


def compare_run_dirs(run_a: Path, run_b: Path) -> dict[str, Any]:
    a = _load(Path(run_a))
    b = _load(Path(run_b))
    arms = sorted(set(a.get("confirmatory_metrics", {})) & set(b.get("confirmatory_metrics", {})))
    deltas = []
    for arm in arms:
        ma = a["confirmatory_metrics"][arm]
        mb = b["confirmatory_metrics"][arm]
        du_a = (ma.get("DeltaU_EXPLORE") or {}).get("mean") or 0.0
        du_b = (mb.get("DeltaU_EXPLORE") or {}).get("mean") or 0.0
        net_a = (ma.get("NetRescueRate") or {}).get("rate") or 0.0
        net_b = (mb.get("NetRescueRate") or {}).get("rate") or 0.0
        rescue_a = ((ma.get("counts") or {}).get("RESCUE") or 0)
        rescue_b = ((mb.get("counts") or {}).get("RESCUE") or 0)
        supported = _ci_excludes_zero(mb.get("DeltaU_EXPLORE"))
        deltas.append(
            {
                "arm": arm,
                "delta_u_abs": du_b - du_a,
                "net_rescue_abs": net_b - net_a,
                "rescue_count_abs": rescue_b - rescue_a,
                "improvement_supported_by_delta_u_ci": bool(supported) and (du_b - du_a) > 0,
                "note": "CI overlap with zero means do not display as improvement",
            }
        )
    return {
        "run_a": {"path": str(run_a), "run_id": a.get("run_id"), "gates": a.get("gates")},
        "run_b": {"path": str(run_b), "run_id": b.get("run_id"), "gates": b.get("gates")},
        "deltas": deltas,
        "claim_rule": "A change is not an improvement when the 95% CI includes zero.",
    }
