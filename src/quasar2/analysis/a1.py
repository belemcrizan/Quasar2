"""Run PHASE A1 decomposition from existing matched experiment artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

from quasar2.analysis.decomposition import (
    DECOMP_FIELDS,
    decompose_pair,
    feature_associations,
    propose_backend_gate,
    rates_by_backend_and_split,
    reconcile_intent_exact,
    split_manifest,
    summarize_rows,
)
from quasar2.analysis.io_util import write_csv, write_json, write_text
from quasar2.analysis.matching import load_benchmark, load_run_directory, match_fast_quasar
from quasar2.audit.repository_state import build_repository_state_manifest
from quasar2.wdi.normalize import sha256_canonical_text
from quasar2.v24.artifacts import environment_text


DATA_DICTIONARY = """# A1 data dictionary

All rates are descriptive. Feature associations are exploratory. They are not
causal effects and MUST NOT be used to declare C1 supported.

## Identity

| field | meaning |
|---|---|
| backend | Retriever family (`bm25`, `neural`, ...). Score distributions are not pooled. |
| snapshot_id | Immutable WDI snapshot identity from the source run. |
| query_id | Stable instance id. Join key with `backend` and `snapshot_id`. |
| canonical_intent_id / split_family_id | Semantic family. Aliases and paraphrases share one split. |
| split | `calibration`, `development`, `validation`, or `sealed_test`. |
| used_for_feature_ranking | True only for calibration+development. |
| used_for_threshold_proposal | True only for calibration. Never sealed_test. |

## Outcomes

| field | meaning |
|---|---|
| fast_correct / quasar_correct / gated_correct | `intent_exact` from the source run. |
| four_way_class | BOTH_CORRECT, OVERTHINKING, RESCUE, BOTH_WRONG. Mutually exclusive and exhaustive for matched rows. |
| OVERTHINKING | FAST correct AND QUASAR wrong. |
| RESCUE | FAST wrong AND QUASAR correct. |
| failure_class | Four-way label (primary). |
| secondary_labels | Optional heuristic tags. Not a sealed diagnosis. |

## Features

Probe `top1_score`/`top2_score` were not persisted in historical CSVs. Empty
values are listed in `missing_feature_flags` rather than imputed.

Complexity, ambiguity, and open-set scores are taken from the FAST row when
present (those used the original probe). Query-only gate features fill gaps
and are marked missing when retrieval scores are absent.

## Leakage

Threshold proposals and feature ranking ignore `sealed_test`. Re-ranking many
features on sealed_test is forbidden.
"""


def _candidate_features(associations: Sequence[dict[str, Any]], *, target: str, backend: str, k: int = 8) -> list[dict[str, Any]]:
    ranked = [
        row
        for row in associations
        if row["target"] == target and row["backend"] == backend and row.get("cohens_d") is not None
    ]
    ranked.sort(key=lambda item: abs(float(item["cohens_d"])), reverse=True)
    return ranked[:k]


def _report_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Rescue / overthinking report (PHASE A1)",
        "",
        "Status: **EXPLORATORY**. Not a sealed confirmatory claim.",
        "",
        "Hypothesis tested: additional QUASAR compute is not uniformly helpful;",
        "matched FAST vs QUASAR labels identify rescue and overthinking regions.",
        "",
        f"Generated: `{payload['created_at']}`",
        "",
        "## Rates",
        "",
    ]
    for key, summary in payload["rates"].items():
        if not key.endswith("|ALL"):
            continue
        if key.count("|") < 2:
            continue
        lines.append(f"### `{key}`")
        lines.append("")
        lines.append(f"- n = {summary['n']}")
        lines.append(
            f"- OverthinkingRate = {summary['OverthinkingRate']:.4f} "
            f"(CI {summary['Overthinking']['ci_low']:.4f}, {summary['Overthinking']['ci_high']:.4f})"
        )
        lines.append(
            f"- RescueRate = {summary['RescueRate']:.4f} "
            f"(CI {summary['Rescue']['ci_low']:.4f}, {summary['Rescue']['ci_high']:.4f})"
        )
        lines.append(f"- BothCorrectRate = {summary['BothCorrectRate']:.4f}")
        lines.append(f"- BothWrongRate = {summary['BothWrongRate']:.4f}")
        lines.append(
            f"- BeneficialReasoningRate = P(RESCUE | FAST wrong) = {summary['BeneficialReasoningRate']:.4f}"
        )
        lines.append(f"- snapshots = {summary.get('snapshots')}")
        lines.append("")
    blocked = payload.get("blocked") or {}
    if blocked:
        lines.append("## Blocked backends")
        lines.append("")
        for name, reason in blocked.items():
            lines.append(f"- `{name}`: {reason}")
        lines.append("")
    lines.append("## Candidate features (calibration+development, not causal)")
    lines.append("")
    for backend in sorted({str(row["backend"]) for row in payload.get("feature_associations") or []}):
        lines.append(f"### {backend}")
        lines.append("")
        for target in ("RESCUE", "OVERTHINKING"):
            lines.append(f"**{target}**")
            lines.append("")
            rows = _candidate_features(payload["feature_associations"], target=target, backend=backend)
            if not rows:
                lines.append("- none with both arms populated")
                lines.append("")
                continue
            for row in rows:
                lines.append(
                    f"- `{row['feature']}`: Δ={row['difference']:.4f}, "
                    f"d={row['cohens_d']:.3f}, CI [{row['ci_low']:.4f}, {row['ci_high']:.4f}]"
                )
            lines.append("")
    lines.append("## Proposed A2 gate (calibration only)")
    lines.append("")
    lines.append("Do not treat these numbers as fitted production thresholds.")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload["gate_proposal"], indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## What this does not claim")
    lines.append("")
    lines.append("- Associations are not causal component effects.")
    lines.append("- C1 remains INCONCLUSIVE until a preregistered sealed run.")
    lines.append("- Neural full-pilot FAST/QUASAR matching is not invented if absent.")
    lines.append("")
    return "\n".join(lines)


def run_a1(
    run_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    benchmark_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    runs = [load_run_directory(path) for path in run_dirs]
    benchmark = load_benchmark(benchmark_path)
    joined = match_fast_quasar(runs, benchmark=benchmark)
    rows = [decompose_pair(pair) for pair in joined["matched"]]
    unmatched = joined["unmatched"]
    associations = feature_associations(rows)
    proposal = propose_backend_gate(rows)
    splits = split_manifest(rows)
    rates = rates_by_backend_and_split(rows)
    overall = summarize_rows(rows)
    summaries_by_snapshot: dict[str, Any] = {}
    for run in runs:
        snap = str(run.get("snapshot_id") or "")
        summaries_by_snapshot[snap] = run.get("summaries") or {}
    recon = reconcile_intent_exact(rows, summaries_by_snapshot)
    backends_present = sorted({str(row["backend"]) for row in rows})
    blocked = {}
    neural_rows = [row for row in rows if row["backend"] == "neural"]
    if not neural_rows:
        blocked["neural"] = (
            "BLOCKED_RESOURCE_LIMIT: no matched FAST_ONLY/QUASAR_ALWAYS neural "
            "rows. Dense hashing was not substituted."
        )
    elif not any("pilot" in str(row.get("snapshot_id") or "") for row in neural_rows):
        blocked["neural_pilot"] = (
            "BLOCKED_RESOURCE_LIMIT: neural matched rows are not the 3036-query "
            "WDI pilot. CI-scale neural decomposition is recorded separately."
        )
    if "bm25" not in backends_present:
        blocked["bm25"] = "MISSING: no matched BM25 FAST/QUASAR rows."

    sealed_ranked = any(row.get("used_sealed_test") for row in associations)
    if sealed_ranked:
        raise RuntimeError("Sealed-test feature ranking leaked into A1 analysis")
    if any(row.get("used_for_threshold_proposal") and row.get("split") == "sealed_test" for row in rows):
        raise RuntimeError("sealed_test marked for threshold proposal")

    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    validation = {
        "ok": not recon and not any(item.get("reason") == "SNAPSHOT_MISMATCH" and item.get("query_id") for item in unmatched),
        "n_matched": len(rows),
        "n_unmatched": len(unmatched),
        "duplicate_query_ids": sum(1 for item in unmatched if item.get("reason") == "DUPLICATE_QUERY_ID"),
        "snapshot_mismatches": sum(1 for item in unmatched if item.get("reason") == "SNAPSHOT_MISMATCH"),
        "schema_conflicts": sum(1 for item in unmatched if item.get("reason") == "SCHEMA_CONFLICT"),
        "one_sided_missing": sum(
            1 for item in unmatched if item.get("reason") in {"MISSING_FAST", "MISSING_QUASAR"}
        ),
        "reconciliation_issues": recon,
        "four_way_exhaustive": overall["n"] == sum(overall["counts"].values()),
        "sealed_test_used_for_fitting": False,
        "claim_status": "EXPLORATORY",
    }
    metrics = {
        "schema_version": "a1.0.0",
        "created_at": created,
        "phase": "A1",
        "claim": "C1",
        "claim_status": "EXPLORATORY",
        "n_matched": len(rows),
        "overall": overall,
        "rates": rates,
        "gate_proposal": proposal,
        "blocked": blocked,
        "backends": backends_present,
        "run_dirs": [str(Path(path)) for path in run_dirs],
        "benchmark_path": str(benchmark_path) if benchmark_path else None,
        "note": "Feature associations are exploratory. Do not promote C1.",
    }
    payload = {
        **metrics,
        "feature_associations": associations,
        "created_at": created,
    }
    write_csv(dest / "per_query_decomposition.csv", rows, DECOMP_FIELDS)
    write_csv(
        dest / "unmatched_queries.csv",
        unmatched,
        sorted({key for row in unmatched for key in row} | {"query_id", "backend", "reason"}),
    )
    write_csv(
        dest / "feature_analysis.csv",
        associations,
        (
            "backend",
            "target",
            "feature",
            "n_positive",
            "n_other",
            "mean_positive",
            "mean_other",
            "difference",
            "cohens_d",
            "ci_low",
            "ci_high",
            "split_scope",
            "status",
            "used_sealed_test",
        ),
    )
    write_json(dest / "metrics.json", metrics)
    write_json(dest / "validation_report.json", validation)
    write_json(dest / "split_manifest.json", splits)
    write_text(dest / "data_dictionary.md", DATA_DICTIONARY)
    write_text(dest / "rescue_overthinking_report.md", _report_markdown(payload))
    write_text(dest / "environment.txt", environment_text())
    repo_root = Path(repo_root) if repo_root else Path.cwd()
    repo_manifest = build_repository_state_manifest(repo_root)
    write_json(dest / "repository_state_manifest.json", repo_manifest)
    csv_bytes = (dest / "per_query_decomposition.csv").read_bytes()
    manifest = {
        "run_kind": "milestone_a1",
        "created_at": created,
        "n_matched": len(rows),
        "n_unmatched": len(unmatched),
        "backends": backends_present,
        "per_query_sha256_canonical": sha256_canonical_text(csv_bytes),
        "claim_status": "EXPLORATORY",
        "sealed_test_used_for_fitting": False,
    }
    write_json(dest / "manifest.json", manifest)
    write_json(
        dest / "claim_status.json",
        {
            "C1": {
                "status": "INCONCLUSIVE",
                "analysis": "A1_EXPLORATORY",
                "text": "Selective reasoning can outperform universal reasoning on risk x compute utility.",
                "note": "A1 explains rescue/overthinking. It does not confirm C1.",
                "n_matched": len(rows),
                "sealed": False,
            }
        },
    )
    return {
        "metrics": metrics,
        "validation": validation,
        "rows": rows,
        "unmatched": unmatched,
        "output_dir": str(dest),
        "manifest": manifest,
        "repository_state": repo_manifest,
    }
