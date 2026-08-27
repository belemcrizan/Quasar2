"""Load scientific artifacts. No scientific rules live only in the UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATASET_MATURITY = {
    "sanity_catalog": "SYNTHETIC",
    "ops_runbook": "SCHEMA_FAITHFUL",
    "wdi": "OFFICIAL_DERIVED",
    "nasa_exoplanet": "SCHEMA_FAITHFUL",
    "esa_gaia": "SCHEMA_FAITHFUL",
    "alma": "SCHEMA_FAITHFUL",
    "jwst": "SCHEMA_FAITHFUL",
    "cern": "SCHEMA_FAITHFUL",
}


def project_root(start: Path | None = None) -> Path:
    here = start or Path.cwd()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "quasar2").exists():
            return candidate
    return here


def default_rescue_dir(root: Path | None = None) -> Path:
    base = project_root(root)
    return base / "experiments" / "results" / "cycle4_rescue"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        return {
            "available": False,
            "reason": f"missing {manifest_path}",
            "run_dir": str(run_dir),
        }
    manifest = load_json(manifest_path)
    anatomy = load_jsonl(run_dir / "anatomy.jsonl")
    traces = load_jsonl(run_dir / "traces.jsonl")
    return {
        "available": True,
        "run_dir": str(run_dir),
        "manifest": manifest,
        "anatomy": anatomy,
        "traces": traces,
        "analyze": load_json(run_dir / "analyze.json") if (run_dir / "analyze.json").exists() else {},
        "ask": load_json(run_dir / "ask.json") if (run_dir / "ask.json").exists() else {},
        "defer": load_json(run_dir / "defer.json") if (run_dir / "defer.json").exists() else {},
        "failure_examples": load_json(run_dir / "failure_examples.json")
        if (run_dir / "failure_examples.json").exists()
        else {},
    }


def list_runs(results_root: Path | None = None) -> list[dict[str, str]]:
    root = results_root or (project_root() / "experiments" / "results")
    runs = []
    if not root.exists():
        return runs
    for path in sorted(root.iterdir()):
        if path.is_dir() and (path / "run_manifest.json").exists():
            manifest = load_json(path / "run_manifest.json")
            runs.append(
                {
                    "run_id": str(manifest.get("run_id") or path.name),
                    "path": str(path),
                    "schema_version": str(manifest.get("schema_version") or ""),
                }
            )
    return runs


def four_way_from_anatomy(anatomy: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets = {"BOTH_CORRECT": [], "OVERTHINKING": [], "RESCUE": [], "BOTH_WRONG": []}
    for row in anatomy:
        label = str(row.get("four_way_class") or "")
        buckets.setdefault(label, []).append(row)
    return buckets


def claims_table(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return list(manifest.get("claims") or [])


def datasets_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": key,
            "maturity": value,
            "confirmatory": "yes" if value == "CONFIRMATORY_BENCHMARK" else "no",
            "note": "schema-faithful and snapshots are not live TAP confirmatory evidence"
            if value == "SCHEMA_FAITHFUL"
            else "",
        }
        for key, value in DATASET_MATURITY.items()
    ]
