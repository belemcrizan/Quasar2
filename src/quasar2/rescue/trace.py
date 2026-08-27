"""Canonical decision trace with isolated runtime / evaluation / oracle namespaces."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from quasar2.rescue.leakage import LeakageError, scan_mapping_for_gold

SCHEMA_VERSION = "trace.1"


def new_trace_id() -> str:
    return str(uuid.uuid4())


def build_trace(
    *,
    trace_id: str | None = None,
    run_id: str,
    runtime: Mapping[str, Any],
    evaluation: Mapping[str, Any] | None = None,
    oracle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace_id or new_trace_id(),
        "run_id": run_id,
        "trace": {
            "runtime": dict(runtime),
            "evaluation": dict(evaluation or {}),
            "oracle": dict(oracle or {}),
        },
    }
    leaks = scan_mapping_for_gold(payload["trace"]["runtime"])
    if leaks:
        raise LeakageError(f"runtime namespace contains gold fields: {leaks}")
    return payload


def runtime_only(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": trace.get("schema_version", SCHEMA_VERSION),
        "trace_id": trace.get("trace_id"),
        "run_id": trace.get("run_id"),
        "trace": {"runtime": dict((trace.get("trace") or {}).get("runtime") or {})},
    }


def compact_runtime_from_run(
    *,
    query: str,
    domain: str,
    arm: str,
    mode: str,
    predicted_id: str,
    action: str,
    retrieval_calls: int,
    seed_calls: int,
    explore_rounds: int,
    belief_top: str | None,
    entropy: float,
    margin: float,
    selected_action: str,
    executed_action: str,
    document_ids: tuple[str, ...] = (),
    costs: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "query": query,
        "domain": domain,
        "dataset": "sanity_catalog",
        "arm": arm,
        "mode": mode,
        "hypotheses_top": belief_top,
        "belief": {"entropy": entropy, "margin": margin, "top": belief_top},
        "candidate_actions": ["ANSWER", "BM25", "DENSE", "HYBRID", "DISCRIMINATIVE", "ANALYZE", "ASK", "DEFER", "VERIFY"],
        "selected_action": selected_action,
        "executed_action": executed_action,
        "action_match": selected_action == executed_action,
        "backend": arm,
        "retrieved_document_ids": list(document_ids),
        "decision": {"predicted_id": predicted_id, "action": action},
        "costs": dict(costs or {}),
        "calls": {"retrieval": retrieval_calls, "seed": seed_calls, "explore_rounds": explore_rounds},
    }
