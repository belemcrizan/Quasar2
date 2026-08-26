"""Crossed retriever × policy evaluation on QUASAR-Bench-WDI."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Sequence

from quasar2.benchmarks.wdi_bench import build_benchmark
from quasar2.retrieval.base import Retriever
from quasar2.retrieval.factory import build_retriever
from quasar2.v24.pipeline import V24Pipeline
from quasar2.wdi.evaluator import evaluate_answer
from quasar2.wdi.source import WDIEvidenceSource


def _user_from_truth(instance: dict) -> callable:
    def reply(question: str, options: tuple[str, ...]) -> str | None:
        acceptable = instance.get("acceptable_intents") or []
        if not acceptable:
            return None
        wanted = acceptable[0].get("indicator_id")
        return wanted if wanted in options else (options[0] if options else None)

    return reply


def run_wdi_experiment(
    snapshot_dir: str | Path,
    *,
    stage: str = "ci",
    policies: Sequence[str] = ("top1", "threshold", "v24"),
    backends: Sequence[str] = ("bm25",),
    output_dir: str | Path | None = None,
    limit: int | None = None,
    retrieval: dict | None = None,
) -> dict:
    source = WDIEvidenceSource(snapshot_dir)
    bench = build_benchmark(snapshot_dir, stage=stage)
    instances = list(bench["instances"])
    if limit is not None:
        instances = instances[:limit]
    documents = source.documents()
    records: list[dict] = []
    for backend in backends:
        retriever: Retriever = build_retriever(documents, backend, retrieval)
        for policy in policies:
            for instance in instances:
                pipeline = V24Pipeline(
                    source,
                    retriever=retriever,
                    policy=policy,
                    user_reply=_user_from_truth(instance),
                )
                result = pipeline.run(
                    instance["query_text"],
                    language=instance.get("language", "en"),
                    period_hint=instance.get("period"),
                )
                predicted = {
                    **result.structured_answer,
                    "final_action": result.final_action,
                    "period": result.structured_answer.get("disclosed_period")
                    or result.structured_answer.get("period"),
                }
                evaluation = evaluate_answer(predicted, instance)
                records.append(
                    {
                        "backend": backend,
                        "policy": policy,
                        "query_id": instance["query_id"],
                        "canonical_intent_id": instance["canonical_intent_id"],
                        "language": instance["language"],
                        "recoverability": instance["recoverability"],
                        "split": instance["split"],
                        "action": result.final_action,
                        "reason_code": result.reason_code,
                        "intent_exact": evaluation.intent_exact,
                        "committed_wrong": evaluation.committed_wrong,
                        "retrieval_calls": result.retrieval_calls,
                        "source_calls": result.source_calls,
                        "steps": result.steps,
                        "unknown_score": result.unknown_score,
                    }
                )
    summaries = _summarize(records)
    payload = {
        "schema_version": "2.4.0",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "snapshot_id": bench["snapshot_id"],
        "stage": stage,
        "n_instances": len(instances),
        "n_canonical": bench["n_canonical"],
        "benchmark_hash": bench["hash"],
        "methods": {"backends": list(backends), "policies": list(policies)},
        "summaries": summaries,
        "records": records,
        "status": "COMPLETE",
        "claim_boundary": "Pilot/CI descriptive results. Not a sealed-test claim.",
    }
    if output_dir is not None:
        dest = Path(output_dir)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        with (dest / "raw_results.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]) if records else ["backend"])
            writer.writeheader()
            writer.writerows(records)
        (dest / "manifest.json").write_text(
            json.dumps(
                {
                    "run_kind": "wdi_v24",
                    "snapshot_id": bench["snapshot_id"],
                    "stage": stage,
                    "n_records": len(records),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return payload


def _summarize(records: Iterable[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        key = f"{record['backend']}|{record['policy']}"
        grouped.setdefault(key, []).append(record)
    out: dict[str, dict[str, float]] = {}
    for key, rows in grouped.items():
        n = len(rows)
        committed = [row for row in rows if row["action"] == "ANSWER"]
        out[key] = {
            "n": n,
            "intent_exact": sum(row["intent_exact"] for row in rows) / n if n else 0.0,
            "wrong_answer_rate": (
                sum(row["committed_wrong"] for row in committed) / len(committed) if committed else 0.0
            ),
            "answer_coverage": len(committed) / n if n else 0.0,
            "ask_rate": sum(row["action"] == "ASK" for row in rows) / n if n else 0.0,
            "defer_rate": sum(row["action"] == "DEFER" for row in rows) / n if n else 0.0,
            "mean_retrieval_calls": sum(row["retrieval_calls"] for row in rows) / n if n else 0.0,
        }
    return out
