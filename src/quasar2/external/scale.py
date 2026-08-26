"""Multidimensional scale sweeps. Scale is not query count alone."""

from __future__ import annotations

from typing import Any, Sequence

from quasar2.cycle2.observation import finite_entropy
from quasar2.external.benchmark import assign_splits, corpus_for_records, expand_states, proxy_kernels, true_kernels
from quasar2.external.evaluate import evaluate_states, retrieval_table
from quasar2.external.snapshots import nasa_exo_records


def _state_with_h(n_h: int, *, recov: str = "recoverable", open_p: float = 0.0, i: int = 0) -> dict[str, Any]:
    hyps = [f"H{k}" for k in range(1, n_h + 1)]
    if open_p > 0:
        hyps.append("H_unknown")
    gold = "H_unknown" if (i % 20) / 20.0 < open_p else "H1"
    belief = {h: 1.0 / len(hyps) for h in hyps}
    if gold != "H_unknown":
        belief[gold] = 0.45
        rest = (1.0 - 0.45) / (len(hyps) - 1)
        for h in hyps:
            if h != gold:
                belief[h] = rest
    return {
        "state_id": f"scale-h{n_h}-{i}",
        "source": "scale_synthetic",
        "split_role": "scale",
        "cluster_id": f"scale-family-{i // 8}",
        "channel": "synthetic",
        "year": 2018,
        "belief": belief,
        "entropy": finite_entropy(belief),
        "unknown_mass": float(belief.get("H_unknown", 0.0)),
        "proxy_kernels": proxy_kernels(recov, 0.0, max(2, n_h), hyps=hyps, gold=gold),
        "true_kernels": true_kernels(recov, gold, max(2, n_h), hyps=hyps),
        "mismatch_mu": 0.0,
        "eta": 0.3,
        "gold_hypothesis": gold,
        "open_set_status": gold == "H_unknown",
        "recoverability_class": recov,
        "ambiguity_class": ["observational_degeneracy"],
        "transformation": "clean",
        "q_obs": "synthetic scale query",
        "candidate_hypotheses": hyps,
    }


def hypothesis_scale(*, sizes: Sequence[int] = (2, 5, 10, 20), n_per: int = 40, seed: int = 0) -> dict[str, Any]:
    table = []
    for n_h in sizes:
        states = [_state_with_h(n_h, i=i) for i in range(n_per)]
        pack = evaluate_states(states, seed=seed, bootstrap_samples=80)
        for row in pack["summaries"]:
            table.append({**row, "n_hypotheses": n_h})
    return {"table": table, "note": "Do not force |H|=100 when candidates would be artificial."}


def open_set_scale(*, rates: Sequence[float] = (0.0, 0.05, 0.10, 0.25, 0.50), n: int = 80, seed: int = 0) -> dict[str, Any]:
    table = []
    for p in rates:
        states = [_state_with_h(5, open_p=p, i=i) for i in range(n)]
        pack = evaluate_states(states, seed=seed, bootstrap_samples=80)
        for row in pack["summaries"]:
            table.append({**row, "p_unknown": p})
    return {"table": table}


def ambiguity_scale(*, etas: Sequence[float] = (0.1, 0.35, 0.65, 0.9), n: int = 60, seed: int = 0) -> dict[str, Any]:
    table = []
    for eta in etas:
        states = []
        recov = "non_recoverable" if eta >= 0.85 else "recoverable"
        for i in range(n):
            s = _state_with_h(4, recov=recov, i=i)
            s["eta"] = eta
            s["entropy"] = min(1.5, 0.4 + eta)
            states.append(s)
        pack = evaluate_states(states, seed=seed, bootstrap_samples=80)
        for row in pack["summaries"]:
            table.append({**row, "eta": eta, "band": _band(eta)})
    return {"table": table, "note": "Monotonicity of EXPLORE vs eta is tested, not assumed."}


def _band(eta: float) -> str:
    if eta < 0.25:
        return "low"
    if eta < 0.5:
        return "moderate"
    if eta < 0.8:
        return "high"
    return "extreme"


def corpus_scale(*, sizes: Sequence[int] = (50, 200, 800), seed: int = 0) -> dict[str, Any]:
    base = nasa_exo_records(n_objects=24)
    states = [s for s in assign_splits(expand_states(base, degradations=("clean",))) if s["transformation"] == "clean"]
    table = []
    for n_docs in sizes:
        docs = corpus_for_records(base, distractors=max(0, n_docs - 40))
        docs = docs[:n_docs] if len(docs) >= 8 else docs
        if len(docs) < 8:
            continue
        pack = retrieval_table(states[:40], docs)
        row = {"n_documents": len(docs), "retrieval": pack.get("table")}
        # Decision advantage vs distractors: BM25 top-1 vs myopic on same states (decision not corpus-coupled here)
        table.append(row)
    return {
        "table": table,
        "note": "10^5 protocol-ready via TAP snapshot; this run stays offline and bounded.",
        "latency_is_not_the_only_question": True,
    }


def query_scale_justification(n_states: int, n_clusters: int) -> dict[str, Any]:
    return {
        "n_states": n_states,
        "n_clusters": n_clusters,
        "pseudo_replication": "degradations share cluster_id with the parent object",
        "ops_note": "OPS N=12 remains underpowered; variants are clustered, not independent.",
    }
