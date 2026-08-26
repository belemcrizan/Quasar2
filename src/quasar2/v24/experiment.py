"""Crossed retriever × policy evaluation on QUASAR-Bench-WDI."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from quasar2.benchmarks.wdi_bench import build_benchmark
from quasar2.retrieval.base import Retriever
from quasar2.retrieval.factory import build_retriever
from quasar2.v24.artifacts import latency_summary_from_records, paired_mean_ci, write_cycle_artifacts
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


def _task_type(instance: dict) -> str:
    if instance.get("recoverability") == "OPEN_SET":
        return "OPEN_SET_DETECTION"
    if instance.get("degradation_level") == 0:
        return "NUMERIC_LOOKUP"
    return "INTENT_IDENTIFICATION"


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
                        "task_type": _task_type(instance),
                        "domain": "wdi",
                        "action": result.final_action,
                        "reason_code": result.reason_code,
                        "intent_exact": evaluation.intent_exact,
                        "committed_wrong": evaluation.committed_wrong,
                        "retrieval_calls": result.retrieval_calls,
                        "source_calls": result.source_calls,
                        "steps": result.steps,
                        "unknown_score": result.unknown_score,
                        "gate_route": result.gate_route,
                        "complexity_score": result.complexity_score,
                        "ambiguity_score": result.ambiguity_score,
                        "open_set_score": result.open_set_score,
                        "latency_ms": result.latency_ms,
                        "gate_ms": result.gate_ms,
                        "retrieval_ms": result.retrieval_ms,
                        "candidate_generation_ms": result.candidate_generation_ms,
                        "belief_update_ms": result.belief_update_ms,
                        "policy_ms": result.policy_ms,
                        "compute_proxy": result.compute_proxy,
                    }
                )
    summaries = _summarize(records)
    latency_summary = latency_summary_from_records(records)
    paired_rows = _paired_comparisons(records)
    claim_status = _claim_status(summaries, paired_rows, n_instances=len(instances), sealed=False)
    payload = {
        "schema_version": "2.4.1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "snapshot_id": bench["snapshot_id"],
        "stage": stage,
        "n_instances": len(instances),
        "n_canonical": bench["n_canonical"],
        "benchmark_hash": bench["hash"],
        "methods": {"backends": list(backends), "policies": list(policies)},
        "summaries": summaries,
        "latency_summary": latency_summary,
        "paired_comparisons": paired_rows,
        "records": records,
        "status": "COMPLETE",
        "claim_boundary": "Pilot/CI descriptive results. Not a sealed-test claim.",
        "claim_status": claim_status,
    }
    if output_dir is not None:
        dest = Path(output_dir)
        dest.mkdir(parents=True, exist_ok=True)
        write_cycle_artifacts(
            dest,
            payload={k: v for k, v in payload.items() if k != "records"},
            records=records,
            source_manifest={
                "source_id": "worldbank_wdi",
                "snapshot_id": bench["snapshot_id"],
                "stage": stage,
                "snapshot_dir": str(Path(snapshot_dir)),
                "official_base_url": "https://api.worldbank.org/v2",
                "terms": "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
            },
            model_manifest={
                "backends": list(backends),
                "retrieval": retrieval or {},
                "silent_hashing_fallback": False,
                "note": "dense_hash is debug-only and is never a neural substitute",
            },
            paired=paired_rows,
            claim_status=claim_status,
            latency_summary=latency_summary,
            run_kind="wdi_v24",
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
            "mean_compute_proxy": sum(row.get("compute_proxy", 0.0) for row in rows) / n if n else 0.0,
            "mean_latency_ms": sum(row.get("latency_ms", 0.0) for row in rows) / n if n else 0.0,
        }
    return out


def _index_by_query(records: Sequence[dict], backend: str, policy: str) -> dict[str, dict]:
    return {
        row["query_id"]: row
        for row in records
        if row["backend"] == backend and row["policy"] == policy
    }


def _paired_comparisons(records: Sequence[dict]) -> list[dict]:
    backends = sorted({row["backend"] for row in records})
    policies = sorted({row["policy"] for row in records})
    rows: list[dict] = []
    pairs = (
        ("gated_quasar", "v24"),
        ("gated_quasar", "quasar_always"),
        ("gated_quasar", "top1"),
        ("gated_quasar", "fast_only"),
        ("v24", "top1"),
        ("quasar_always", "fast_only"),
    )
    for backend in backends:
        for left_name, right_name in pairs:
            if left_name not in policies or right_name not in policies:
                continue
            left = _index_by_query(records, backend, left_name)
            right = _index_by_query(records, backend, right_name)
            keys = sorted(set(left) & set(right))
            if not keys:
                continue
            intent = paired_mean_ci(
                [float(left[k]["intent_exact"]) for k in keys],
                [float(right[k]["intent_exact"]) for k in keys],
            )
            compute = paired_mean_ci(
                [float(left[k]["compute_proxy"]) for k in keys],
                [float(right[k]["compute_proxy"]) for k in keys],
            )
            retrieval = paired_mean_ci(
                [float(left[k]["retrieval_calls"]) for k in keys],
                [float(right[k]["retrieval_calls"]) for k in keys],
            )
            wrong = paired_mean_ci(
                [float(left[k]["committed_wrong"]) for k in keys],
                [float(right[k]["committed_wrong"]) for k in keys],
            )
            rows.append(
                {
                    "backend": backend,
                    "left": left_name,
                    "right": right_name,
                    "n": int(intent["n"]),
                    "intent_exact_diff": intent["difference"],
                    "intent_exact_ci_low": intent["ci_low"],
                    "intent_exact_ci_high": intent["ci_high"],
                    "compute_proxy_diff": compute["difference"],
                    "compute_proxy_ci_low": compute["ci_low"],
                    "compute_proxy_ci_high": compute["ci_high"],
                    "retrieval_calls_diff": retrieval["difference"],
                    "wrong_answer_diff": wrong["difference"],
                    "comparison_label": "EXPLORATORY",
                }
            )
    return rows


def _claim_status(
    summaries: dict[str, dict[str, float]],
    paired_rows: Sequence[dict],
    *,
    n_instances: int,
    sealed: bool,
) -> dict:
    """C1 is not confirmatory unless margins were frozen before a sealed run."""

    status = "INCONCLUSIVE"
    note = "No matched GATED_QUASAR vs QUASAR_ALWAYS pair in this run."
    gated_keys = [key for key in summaries if key.endswith("|gated_quasar")]
    always_keys = [key for key in summaries if key.endswith("|v24") or key.endswith("|quasar_always")]
    if gated_keys and always_keys and not sealed:
        status = "INCONCLUSIVE"
        note = (
            "C1 remains exploratory: thresholds were not frozen against a sealed test set "
            "before viewing these results. Descriptive paired CIs are recorded."
        )
    return {
        "C1": {
            "status": status,
            "text": "Selective reasoning is more compute-efficient than universal reasoning.",
            "n": n_instances,
            "sealed": sealed,
            "note": note,
            "paired_rows": len(paired_rows),
        }
    }
