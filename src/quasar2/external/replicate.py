"""Repeatability vs computational reproducibility vs independent execution vs external replication."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


LEVELS = (
    "repeatability",
    "computational_reproducibility",
    "independent_execution",
    "external_replication",
)


def git_sha(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=False, capture_output=True, text=True
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def environment_lock(root: Path) -> dict[str, Any]:
    pkgs = {}
    for name in ("numpy", "torch", "sentence_transformers", "pytest"):
        try:
            mod = __import__(name)
            pkgs[name] = getattr(mod, "__version__", "present")
        except Exception:
            pkgs[name] = None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "os": sys.platform,
        "package_versions": pkgs,
        "embedding_models": "NOT_LOADED_IN_DEFAULT_STDLIB_RUN",
        "git_sha": git_sha(root),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": platform.processor(),
        "note": "Hashing dense is not a neural encoder. Neural extras absent unless installed.",
    }


def reconstruct_frozen_sanity(root: Path) -> dict[str, Any]:
    path = root / "experiments" / "results" / "frozen" / "v0.1.1" / "benchmark.json"
    if not path.exists():
        return {"status": "MISSING_FROZEN_ARTIFACT"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "status": "RECONSTRUCTED_FROM_IMMUTABLE_SNAPSHOT",
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": digest,
        "n_records": len(payload) if isinstance(payload, list) else payload.get("n"),
        "note": "Not a new run. Frozen v0.1.1 is not modified.",
    }


def reconstruct_cycle2(root: Path) -> dict[str, Any]:
    path = root / "experiments" / "results" / "cycle2_maturity" / "cycle2.json"
    if not path.exists():
        return {"status": "CYCLE2_ARTIFACT_NOT_CHECKED_IN_OR_MISSING"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "status": "RECONSTRUCTED_FROM_EXISTING_ARTIFACT",
        "path": "experiments/results/cycle2_maturity/cycle2.json",
        "answers": payload.get("answers"),
        "gate1": "FAIL locked",
        "note": "Reproduction of Cycle 2 numbers uses existing artifacts; this command does not retune Gate 1.",
    }


def cloud_replication_stub() -> dict[str, Any]:
    return {
        "status": "NOT_RUN",
        "reason": "No cloud credentials in this research checkout. Independent Linux container is the provided path.",
        "compare": None,
        "level": "independent_execution_ready_not_external_replication",
    }


def paper_tables(frozen: Mapping[str, Any], cycle2: Mapping[str, Any], external: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "frozen_v011": frozen,
        "cycle2_preserved": cycle2,
        "external_validity": {
            "run_id": external.get("run_id"),
            "answers": external.get("answers"),
            "claims": external.get("claims"),
        },
        "claim_ledger_policy": "No claim upgraded to SUPPORTED without pre-registered clustered interval on live official dumps.",
    }
