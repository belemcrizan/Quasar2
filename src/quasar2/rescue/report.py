"""Markdown / JSON cycle report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, default=str) + "\n")


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str), encoding="utf-8")


def render_report(payload: Mapping[str, Any]) -> str:
    metrics = payload.get("confirmatory_metrics") or {}
    gates = payload.get("gates") or {}
    ceiling = payload.get("oracle_ceiling") or {}
    anatomy = payload.get("anatomy_distribution") or {}
    claims = payload.get("claims") or []
    lines = [
        f"# QUASAR2 Cycle 4–7A — rescue chain ({payload.get('schema_version')})",
        "",
        f"run_id: `{payload.get('run_id')}`",
        f"git_sha: `{payload.get('git_sha')}`",
        f"seed: `{payload.get('seed')}`",
        f"N: `{payload.get('n_queries')}`",
        "",
        "## Primary question",
        "",
        "Can additional information actually rescue a decision?",
        "",
        "## Gates",
        "",
    ]
    for name, status in gates.items():
        lines.append(f"- `{name}`: **{status}**")
    lines.extend(["", "## Confirmatory metrics (sanity fixture)", ""])
    for arm, block in (metrics.items() if isinstance(metrics, dict) else []):
        if not isinstance(block, dict):
            continue
        rr = block.get("RescueRate_FW") or {}
        ot = block.get("OverthinkingRate_FC") or {}
        net = block.get("NetRescueRate") or {}
        du = block.get("DeltaU_EXPLORE") or {}
        lines.append(
            f"- **{arm}**: RescueRate_FW={rr.get('rate')} (k={rr.get('k')}/n={rr.get('n')}); "
            f"OverthinkingRate_FC={ot.get('rate')} (k={ot.get('k')}/n={ot.get('n')}); "
            f"NetRescueRate={net.get('rate')}; ΔU={du.get('mean')}"
        )
    lines.extend(["", "## OracleRescueCeiling", ""])
    lines.append(json.dumps(ceiling, indent=2, default=str))
    lines.extend(["", "## Anatomy (primary failures)", ""])
    for key, value in anatomy.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Claims", "", "| Claim | Evidence | Scope | Limitation | Status |", "| --- | --- | --- | --- | --- |"])
    for claim in claims:
        lines.append(
            "| {id} | {evidence} | {scope} | {limitation} | {status} |".format(
                id=claim.get("claim_id"),
                evidence=claim.get("evidence"),
                scope=claim.get("scope"),
                limitation=claim.get("limitation"),
                status=claim.get("status"),
            )
        )
    lines.extend(
        [
            "",
            "## Stop / next falsifiable test",
            "",
            str(payload.get("next_test") or ""),
            "",
            "QUASAR2 remains research software. Negative and blocked gates are retained.",
            "",
        ]
    )
    return "\n".join(lines)
