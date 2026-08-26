"""Retrieval vs decision evaluation. Oracle policies are bounds, not competitors."""

from __future__ import annotations

import time
from typing import Any, Mapping, Sequence

from quasar2.cycle2.action_value import estimate_action_values, q_net_map
from quasar2.cycle2.policies import (
    EmpiricalMyopicPolicy,
    EntropyOnlyPolicy,
    ImmediateAnswerPolicy,
    OraclePolicy,
)
from quasar2.cycle2.recoverability_state import estimate_recoverability_state
from quasar2.math.bootstrap import cluster_bootstrap_mean
from quasar2.retrieval.base import Document
from quasar2.retrieval.factory import build_retriever

RETRIEVAL_BASELINES = ("bm25", "dense_hash", "hybrid")
DECISION_BASELINES = ("immediate_answer", "entropy_only", "empirical_myopic")
ORACLE_BOUNDS = ("oracle_action",)


def _neu(correct: bool, action: str, *, rho: float, kappa: float, calls: int, latency_ms: float) -> float:
    u_correct = 1.0
    u_wrong = -abs(rho) * u_correct
    if action == "ANSWER":
        value = u_correct if correct else u_wrong
    elif action == "DEFER":
        value = -0.05
    elif action == "ASK":
        value = -0.12
    elif action == "EXPLORE":
        value = (0.55 * u_correct if correct else 0.15 * u_wrong) - abs(kappa) * u_correct
    elif action == "ANALYZE":
        value = (0.35 * u_correct if correct else 0.05 * u_wrong) - 0.3 * abs(kappa) * u_correct
    else:
        value = -0.2
    value -= 0.06 * calls
    value -= min(0.15, latency_ms / 8000.0)
    return value


def _top_from_hits(hits, hypotheses: Sequence[str]) -> tuple[str | None, dict[str, float], int]:
    scores = {h: 0.0 for h in hypotheses}
    for hit in hits:
        for hid in hit.document.hypothesis_ids:
            if hid in scores:
                scores[hid] += float(hit.score)
            elif hid == "shared.overlap":
                continue
    total = sum(scores.values())
    if total <= 0:
        n = max(1, len(hypotheses))
        belief = {h: 1.0 / n for h in hypotheses}
        return None, belief, 1
    belief = {h: v / total for h, v in scores.items()}
    top = max(belief, key=belief.get)
    return top, belief, 1


def retrieve_predict(
    query: str,
    domain: str,
    hypotheses: Sequence[str],
    retriever,
    *,
    top_k: int = 8,
) -> dict[str, Any]:
    started = time.perf_counter()
    hits = retriever.search(query, top_k=top_k, domain=None)
    elapsed = (time.perf_counter() - started) * 1000.0
    pred, belief, calls = _top_from_hits(hits, hypotheses)
    return {
        "predicted": pred,
        "belief": belief,
        "hits": hits,
        "retrieval_calls": calls,
        "latency_ms": elapsed,
        "recall_at_k": _recall(hits, hypotheses),
    }


def _recall(hits, hypotheses: Sequence[str]) -> float:
    found = {hid for hit in hits for hid in hit.document.hypothesis_ids}
    labeled = [h for h in hypotheses if h != "H_unknown"]
    if not labeled:
        return 0.0
    return sum(1 for h in labeled if h in found) / len(labeled)


def decide(name: str, state: Mapping[str, Any], *, rho: float, explore_cost: float) -> dict[str, Any]:
    belief = state["belief"]
    unknown = float(state.get("unknown_mass") or belief.get("H_unknown", 0.0))
    if name == "immediate_answer":
        rec = ImmediateAnswerPolicy().recommend()
    elif name == "entropy_only":
        rec = EntropyOnlyPolicy().recommend(belief=belief, unknown_mass=unknown)
    elif name == "empirical_myopic":
        try:
            rec = EmpiricalMyopicPolicy().recommend(
                belief=belief,
                kernels=state["proxy_kernels"],
                explore_cost=explore_cost,
                rho=rho,
                unknown_mass=unknown,
            )
        except AssertionError:
            rec = {
                "policy_name": "empirical_myopic",
                "selected_action": "DEFER",
                "notes": "Q_UNAVAILABLE_T2_DEGENERATE",
            }
    elif name == "oracle_action":
        try:
            rec = OraclePolicy().recommend(
                belief=belief,
                true_kernels=state["true_kernels"],
                explore_cost=explore_cost,
                rho=rho,
                unknown_mass=unknown,
            )
        except AssertionError:
            rec = {
                "policy_name": "oracle",
                "selected_action": "DEFER",
                "notes": "ORACLE_UNAVAILABLE_T2_DEGENERATE",
            }
    else:
        raise KeyError(name)
    return rec


def evaluate_states(
    states: Sequence[Mapping[str, Any]],
    *,
    rho: float = 1.4,
    kappa: float = 0.10,
    seed: int = 0,
    bootstrap_samples: int = 200,
) -> dict[str, Any]:
    rows = []
    for state in states:
        gold = state["gold_hypothesis"]
        recov = estimate_recoverability_state(state["belief"], state["proxy_kernels"], oracle_run=False)
        for policy in DECISION_BASELINES:
            rec = decide(policy, state, rho=rho, explore_cost=kappa)
            action = rec["selected_action"]
            pred = max(state["belief"], key=state["belief"].get)
            correct = pred == gold and gold != "H_unknown" and action == "ANSWER"
            if action != "ANSWER":
                correct = False
            neu = _neu(pred == gold and gold != "H_unknown", action, rho=rho, kappa=kappa, calls=0 if action != "EXPLORE" else 1, latency_ms=0.0)
            if action == "EXPLORE" and state["recoverability_class"] == "recoverable" and gold != "H_unknown":
                neu += 0.25
            if action == "EXPLORE" and state["recoverability_class"] == "non_recoverable":
                neu -= 0.2
            if action == "DEFER" and (state["open_set_status"] or gold == "H_unknown"):
                neu += 0.18
            if action == "ANSWER" and gold == "H_unknown":
                neu -= 0.4
            oracle = decide("oracle_action", state, rho=rho, explore_cost=kappa)
            try:
                q_map = q_net_map(
                    estimate_action_values(
                        state["belief"],
                        state["true_kernels"],
                        explore_cost=kappa,
                        rho=rho,
                        unknown_mass=state["unknown_mass"],
                    )
                )
            except AssertionError:
                q_map = {}
            rows.append(
                {
                    "state_id": state["state_id"],
                    "source": state["source"],
                    "split_role": state["split_role"],
                    "cluster_id": state["cluster_id"],
                    "policy": policy,
                    "action": action,
                    "oracle_action": oracle["selected_action"],
                    "predicted": pred,
                    "gold": gold,
                    "correct_answer": bool(pred == gold and action == "ANSWER" and gold != "H_unknown"),
                    "false_answer": bool(action == "ANSWER" and pred != gold),
                    "false_explore": bool(action == "EXPLORE" and state["recoverability_class"] == "non_recoverable"),
                    "neu": neu,
                    "entropy": state["entropy"],
                    "R_hat": recov.r_hat,
                    "mismatch_mu": state["mismatch_mu"],
                    "eta": state["eta"],
                    "open_set": state["open_set_status"],
                    "recoverability_class": state["recoverability_class"],
                    "ambiguity_class": list(state["ambiguity_class"]),
                    "channel": state["channel"],
                    "year": state["year"],
                    "oracle_q_answer": q_map.get("ANSWER"),
                    "budget_calls": 0 if action != "EXPLORE" else 1,
                    "rho": rho,
                    "kappa": kappa,
                    "seed": seed,
                }
            )
    return {"rows": rows, "summaries": summarize_rows(rows, bootstrap_samples=bootstrap_samples, seed=seed)}


def summarize_rows(rows: Sequence[Mapping[str, Any]], *, bootstrap_samples: int, seed: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        key = (str(row["source"]), str(row["split_role"]), str(row["policy"]))
        groups.setdefault(key, []).append(row)
    table = []
    for (source, split, policy), group in sorted(groups.items()):
        neus = [float(r["neu"]) for r in group]
        clusters = [str(r["cluster_id"]) for r in group]
        ci = cluster_bootstrap_mean(neus, clusters, samples=bootstrap_samples, seed=seed)
        n_clusters = len(set(clusters))
        table.append(
            {
                "source": source,
                "split_role": split,
                "policy": policy,
                "n": len(group),
                "effective_clustered_n": n_clusters,
                "mean_neu": sum(neus) / len(neus),
                "neu_ci": ci,
                "false_answer_rate": sum(int(r["false_answer"]) for r in group) / len(group),
                "false_explore_rate": sum(int(r["false_explore"]) for r in group) / len(group),
                "explore_rate": sum(1 for r in group if r["action"] == "EXPLORE") / len(group),
                "defer_rate": sum(1 for r in group if r["action"] == "DEFER") / len(group),
                "ask_rate": sum(1 for r in group if r["action"] == "ASK") / len(group),
                "mean_calls": sum(float(r["budget_calls"]) for r in group) / len(group),
            }
        )
    return table


def paired_delta(
    rows: Sequence[Mapping[str, Any]],
    left_policy: str,
    right_policy: str,
    *,
    seed: int,
    samples: int = 200,
) -> dict[str, Any]:
    left = {r["state_id"]: r for r in rows if r["policy"] == left_policy}
    right = {r["state_id"]: r for r in rows if r["policy"] == right_policy}
    ids = sorted(set(left) & set(right))
    if not ids:
        return {"status": "empty"}
    d = [float(left[i]["neu"]) - float(right[i]["neu"]) for i in ids]
    clusters = [str(left[i]["cluster_id"]) for i in ids]
    ci = cluster_bootstrap_mean(d, clusters, samples=samples, seed=seed)
    return {
        "left": left_policy,
        "right": right_policy,
        "n": len(ids),
        "n_clusters": len(set(clusters)),
        "mean_delta": sum(d) / len(d),
        "ci": ci,
    }


def retrieval_table(
    states: Sequence[Mapping[str, Any]],
    documents: Sequence[Document],
    *,
    backends: Sequence[str] = RETRIEVAL_BASELINES,
    top_k: int = 8,
) -> dict[str, Any]:
    if not documents or not states:
        return {"status": "empty"}
    table = []
    for backend in backends:
        retriever = build_retriever(documents, backend)
        latencies = []
        hits_acc = []
        irr = []
        for state in states:
            if state.get("transformation") not in {None, "clean"} and state.get("transformation") != "clean":
                continue
            pack = retrieve_predict(state["q_obs"], state["source"], state["candidate_hypotheses"], retriever, top_k=top_k)
            latencies.append(pack["latency_ms"])
            hits_acc.append(pack["recall_at_k"])
            irr.append(int(pack["predicted"] == state["gold_hypothesis"]))
        n = len(latencies)
        if not n:
            continue
        table.append(
            {
                "backend": backend,
                "class": "retrieval_baseline",
                "n": n,
                "intent_top1": sum(irr) / n,
                "mean_label_recall_at_k": sum(hits_acc) / n,
                "mean_latency_ms": sum(latencies) / n,
                "note": "dense_hash is hashing cosine, not neural",
            }
        )
    return {"table": table}


def query_expansion_baseline(
    states: Sequence[Mapping[str, Any]],
    documents: Sequence[Document],
) -> dict[str, Any]:
    if not documents:
        return {"status": "empty"}
    retriever = build_retriever(documents, "bm25")
    n = 0
    acc = 0
    calls = 0
    for state in states:
        if state.get("transformation") != "clean":
            continue
        expanded = state["q_obs"] + " " + " ".join(state["candidate_hypotheses"][:3])
        pack = retrieve_predict(expanded, state["source"], state["candidate_hypotheses"], retriever)
        n += 1
        acc += int(pack["predicted"] == state["gold_hypothesis"])
        calls += 1
    if not n:
        return {"status": "empty"}
    return {
        "baseline": "query_expansion_bm25",
        "class": "retrieval_baseline",
        "n": n,
        "intent_top1": acc / n,
        "mean_calls": calls / n,
        "note": "HyDE not run (requires a generator model).",
    }
