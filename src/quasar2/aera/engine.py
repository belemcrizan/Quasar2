"""Counterfactual Rescue Engine: FastWrong → anatomy → actions → belief/decision change."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Sequence

from quasar2.aera.ask import select_ask
from quasar2.aera.economy import eroi
from quasar2.aera.marketplace import execute_market_action, quote_actions, select_quote
from quasar2.aera.planner import plan_horizon2
from quasar2.aera.provenance import ProvenanceGraph, adjusted_evidence_score
from quasar2.aera.twin import simulate_outcomes
from quasar2.aera.verify import claim_for_hypothesis, verify_claim
from quasar2.failures.taxonomy import four_way_class
from quasar2.rescue.pipeline import RescuePipeline, RescueRun
from quasar2.rescue.metrics import realized_utility
from quasar2.rescue.taxonomy import classify_primary


COSTS = dict(wrong_answer_cost=1.4, exploration_cost=0.10, ask_cost=0.28, defer_cost=0.05)


def _u(run: RescueRun, ok: bool) -> float:
    return realized_utility(
        correct=ok,
        action=run.action,
        retrieval_calls=run.retrieval_calls,
        seed_calls=run.seed_calls,
        **COSTS,
    )


def run_engine(
    pipeline: RescuePipeline,
    *,
    query: str,
    domain: str,
    gold_id: str | None = None,
    catalog_ids: Sequence[str] = (),
    verifier_available: bool = True,
    deadline_s: float = 5.0,
) -> dict[str, Any]:
    """Gold is evaluation-only. Deployment callers must pass gold_id=None."""

    fast = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
    quotes = quote_actions(
        entropy=fast.belief.normalized_entropy,
        margin=fast.belief.margin,
        unknown_mass=fast.belief.probabilities.get("H_unknown", 0.0),
        top_generation=max((c.generation_score for c in fast.candidates), default=0.0),
        deadline_s=deadline_s,
        verifier_available=verifier_available,
    )
    chosen = select_quote(quotes)
    twin = simulate_outcomes(
        entropy=fast.belief.normalized_entropy, margin=fast.belief.margin, action=chosen.name
    )
    executed = execute_market_action(
        pipeline, query, domain, chosen.name, verifier_available=verifier_available
    )
    graph = ProvenanceGraph()
    for doc_id in fast.retrieved_ids[:8]:
        graph.add_node(doc_id, "evidence")
    if len(fast.retrieved_ids) >= 2:
        graph.add_edge(fast.retrieved_ids[0], fast.retrieved_ids[1], "duplicates")
    adj = (
        adjusted_evidence_score(graph, fast.retrieved_ids[0], 1.0, seen=())
        if fast.retrieved_ids
        else {"decision_relevant": False, "adjusted": 0.0, "base": 0.0}
    )
    plan = plan_horizon2(
        entropy=fast.belief.normalized_entropy,
        margin=fast.belief.margin,
        actions=("ANSWER", "BM25", "DISCRIMINATIVE", "ANALYZE", "VERIFY", "DEFER"),
        remaining_budget=0.40,
        costs={"ANSWER": 0.0, "BM25": 0.10, "DISCRIMINATIVE": 0.25, "ANALYZE": 0.02, "VERIFY": 0.12, "DEFER": 0.05},
    )
    ask = select_ask(query, fast.candidates)
    verify = verify_claim(claim_for_hypothesis(fast.predicted_id), predicted_id=fast.predicted_id)
    evaluation: dict[str, Any] = {}
    if gold_id is not None:
        fast_ok = fast.predicted_id == gold_id
        pred_id = executed.get("predicted_id")
        deliberative_ok = pred_id == gold_id if pred_id else False
        four = four_way_class(fast_ok, deliberative_ok)
        fast_u = _u(fast, fast_ok)
        delta_c = 0.10 * max(0, int(executed.get("retrieval_calls") or fast.retrieval_calls) - fast.seed_calls)
        if chosen.name == "VERIFY":
            delta_c = verify.cost
        if chosen.name == "ASK":
            delta_c = float(ask["cost"])
        if chosen.name == "ANALYZE":
            delta_c = 0.02
        delta_u = (1.0 if deliberative_ok else -1.4) - (1.0 if fast_ok else -1.4) - delta_c
        evaluation = {
            "four_way_class": four.label,
            "fast_correct": fast_ok,
            "deliberative_correct": deliberative_ok,
            "delta_u": delta_u,
            "eroi": eroi(delta_u=delta_u, delta_c=delta_c),
        }
        primary, _, _ = classify_primary(
            catalog_has_h_star=gold_id in set(catalog_ids) if catalog_ids else True,
            sufficient="undetermined",
            h_star_in_generated=gold_id in {c.hypothesis.hypothesis_id for c in fast.candidates},
            gold_retrieved=False,
            oracle_hypothesis_correct=False,
            oracle_retrieval_correct=False,
            oracle_evidence_correct=False,
            oracle_belief_correct=False,
            predicted_correct=deliberative_ok,
            belief_top_is_h_star=fast.belief.top_hypothesis_id == gold_id,
            delta_b_star=None,
            factorial_conflict=False,
        )
        evaluation["primary_failure"] = "NONE" if deliberative_ok else primary
    return {
        "query": query,
        "domain": domain,
        "fast_predicted": fast.predicted_id,
        "selected_action": chosen.name,
        "executed_action": executed["executed_action"],
        "quotes": [asdict(row) for row in quotes],
        "twin": asdict(twin),
        "plan": {k: v for k, v in plan.items() if k not in {"first", "second"}},
        "ask": ask,
        "verify": asdict(verify),
        "provenance_adjustment": adj,
        "evaluation": evaluation,
        "oracle_used": gold_id is not None,
        "policy_changes_execution": executed["executed_action"] == chosen.name and chosen.name != "ANSWER",
    }
