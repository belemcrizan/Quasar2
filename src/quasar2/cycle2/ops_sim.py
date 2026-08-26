"""Deployment-like OPS sequential simulator. Not a UI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from quasar2.cycle2.observation import finite_entropy
from quasar2.config import discover_project_root
from quasar2.datasets.ops_runbook import HYPOTHESES
from quasar2.retrieval.base import Document, load_corpus
from quasar2.retrieval.factory import build_retriever


ASK_SLOTS = ("region", "timestamp", "endpoint", "recent_deploy", "reproducible")

USER_MODELS = ("truthful", "incomplete", "noisy", "ambiguous", "refusal")


def _root() -> Path:
    return discover_project_root()


def load_ops_bundle(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    intents = json.loads((root / "data" / "ops" / "intents.json").read_text(encoding="utf-8"))
    documents = load_corpus(root / "data" / "ops" / "corpus")
    return {"intents": intents["intents"], "documents": documents, "hypotheses": HYPOTHESES}


def _hyp_ids() -> tuple[str, ...]:
    return tuple(str(h["id"]) for h in HYPOTHESES)


def _belief_from_hits(hits, hyp_ids: tuple[str, ...]) -> dict[str, float]:
    scores = {hid: 0.0 for hid in hyp_ids}
    for hit in hits:
        for hid in hit.document.hypothesis_ids:
            if hid in scores:
                scores[hid] += float(hit.score)
    total = sum(scores.values())
    if total <= 0.0:
        n = len(hyp_ids)
        return {hid: 1.0 / n for hid in hyp_ids}
    return {hid: val / total for hid, val in scores.items()}


def _utility(*, correct: bool, action: str, rho: float, retrieval_calls: int, ask: int, latency_ms: float) -> float:
    u_correct = 1.0
    value = u_correct if correct else 0.0
    if action == "ANSWER" and not correct:
        value -= rho * u_correct
    if action == "DEFER":
        value = -0.05 if not correct else 0.2
    value -= 0.08 * retrieval_calls
    value -= 0.12 * ask
    value -= min(0.2, latency_ms / 5000.0)
    return value


def _ask_reply(model: str, gold: str, question: str) -> str | None:
    if model == "refusal":
        return None
    if model == "truthful":
        return gold
    if model == "incomplete":
        return gold.split(".")[-1]
    if model == "ambiguous":
        return "intermittent 500 at the gateway"
    if model == "noisy":
        return "maybe tls" if "tls" not in gold else "maybe dns"
    return gold


def simulate_ops(
    *,
    backend: str = "bm25",
    rho: float = 1.4,
    budget_calls: int = 1,
    inject: str | None = None,
    user_model: str = "noisy",
    root: Path | None = None,
    neural_optional: bool = True,
) -> dict[str, Any]:
    bundle = load_ops_bundle(root)
    documents: list[Document] = list(bundle["documents"])
    hyp_ids = _hyp_ids()
    backend_status = {"requested": backend, "executed": backend, "skip_reason": None}
    try:
        retriever = build_retriever(documents, backend)
    except Exception as exc:  # neural missing
        if backend not in {"bm25", "hybrid", "dense", "dense_hash"} and neural_optional:
            retriever = build_retriever(documents, "bm25")
            backend_status = {
                "requested": backend,
                "executed": "bm25",
                "skip_reason": f"backend_unavailable:{type(exc).__name__}:{exc}",
            }
        else:
            raise
    records = []
    for intent in bundle["intents"]:
        query = str(intent["q0"])
        gold = str(intent["correct_hypothesis"])
        t0 = time.perf_counter()
        if inject == "empty_index":
            hits = []
        elif inject == "timeout":
            hits = retriever.search(query, top_k=5, domain="ops")
            latency_ms = 1e9
        else:
            hits = retriever.search(query, top_k=5, domain="ops")
            latency_ms = (time.perf_counter() - t0) * 1000.0
        if inject != "timeout":
            latency_ms = (time.perf_counter() - t0) * 1000.0
        if inject == "duplicate_burst" and hits:
            hits = list(hits) + list(hits)
        if inject == "contradictory" and hits:
            # keep hits; contradiction is in mixed hypothesis_ids across ranks
            pass
        belief_answer = _belief_from_hits(hits[:1], hyp_ids)
        belief_explore = _belief_from_hits(hits[: max(1, budget_calls + 1)], hyp_ids)
        pred_answer = max(belief_answer, key=lambda k: (belief_answer[k], k))
        pred_explore = max(belief_explore, key=lambda k: (belief_explore[k], k))
        u_answer = _utility(
            correct=pred_answer == gold,
            action="ANSWER",
            rho=rho,
            retrieval_calls=1 if hits else 0,
            ask=0,
            latency_ms=latency_ms,
        )
        u_explore = _utility(
            correct=pred_explore == gold,
            action="ANSWER",
            rho=rho,
            retrieval_calls=min(len(hits), budget_calls + 1),
            ask=0,
            latency_ms=latency_ms,
        )
        ask_reply = _ask_reply(user_model, gold, "which region?")
        ask_correct = ask_reply == gold
        u_ask = _utility(
            correct=ask_correct or pred_explore == gold,
            action="ASK",
            rho=rho,
            retrieval_calls=1,
            ask=1,
            latency_ms=latency_ms + 50.0,
        )
        entropy = finite_entropy(belief_answer)
        selected = "EXPLORE" if entropy >= 0.5 else "ANSWER"
        if inject in {"empty_index", "timeout"}:
            selected = "DEFER"
        if inject == "poisoned_instruction":
            # Document text must not become a control-plane command.
            selected = "DEFER" if any("ignore previous" in (h.document.text.lower()) for h in hits) else selected
        u_policy = {"ANSWER": u_answer, "EXPLORE": u_explore, "ASK": u_ask, "DEFER": -0.05}[selected]
        records.append(
            {
                "query_id": intent["id"],
                "gold": gold,
                "backend_executed": backend_status["executed"],
                "inject": inject,
                "user_model": user_model,
                "pred_force_answer": pred_answer,
                "pred_force_explore": pred_explore,
                "correct_force_answer": pred_answer == gold,
                "correct_force_explore": pred_explore == gold,
                "delta_u_explore": u_explore - u_answer,
                "u_force_answer": u_answer,
                "u_force_explore": u_explore,
                "u_policy": u_policy,
                "selected": selected,
                "entropy": entropy,
                "retrieval_calls_answer": 1 if hits else 0,
                "retrieval_calls_explore": min(len(hits), budget_calls + 1) if hits else 0,
                "latency_ms": latency_ms if inject != "timeout" else None,
                "timeout": inject == "timeout",
                "empty": not hits,
                "ask_reply": ask_reply,
                "cluster_id": gold,
                "evidence_rung": "D3",
            }
        )
    n = len(records) or 1
    return {
        "backend": backend_status,
        "n": len(records),
        "inject": inject,
        "mean_delta_u_explore": sum(r["delta_u_explore"] for r in records) / n,
        "mean_u_answer": sum(r["u_force_answer"] for r in records) / n,
        "mean_u_explore": sum(r["u_force_explore"] for r in records) / n,
        "mean_u_policy": sum(r["u_policy"] for r in records) / n,
        "answer_accuracy": sum(r["correct_force_answer"] for r in records) / n,
        "explore_accuracy": sum(r["correct_force_explore"] for r in records) / n,
        "defer_on_fault": sum(1 for r in records if r["selected"] == "DEFER") / n,
        "records": records,
    }


def run_ops_matrix(root: Path | None = None) -> dict[str, Any]:
    faults = (None, "empty_index", "timeout", "duplicate_burst", "contradictory")
    backends = ("bm25", "hybrid")
    out: dict[str, Any] = {"runs": [], "neural": None}
    for backend in backends:
        paired = simulate_ops(backend=backend, inject=None, root=root)
        out["runs"].append({"backend": backend, "inject": None, "summary": {k: v for k, v in paired.items() if k != "records"}, "records": paired["records"]})
        for fault in faults:
            if fault is None:
                continue
            payload = simulate_ops(backend=backend, inject=fault, root=root)
            out["runs"].append(
                {
                    "backend": backend,
                    "inject": fault,
                    "summary": {k: v for k, v in payload.items() if k != "records"},
                }
            )
    neural = simulate_ops(backend="neural", inject=None, root=root)
    out["neural"] = {
        "backend": neural["backend"],
        "summary": {k: v for k, v in neural.items() if k != "records"},
        "executed": neural["backend"]["executed"] == "neural",
    }
    return out
