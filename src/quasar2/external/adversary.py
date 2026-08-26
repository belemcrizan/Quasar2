"""Adversarial and baseline-favorable regimes. Failure should be predictable."""

from __future__ import annotations

from typing import Any

from quasar2.cycle2.observation import finite_entropy
from quasar2.external.benchmark import proxy_kernels, true_kernels


def _base(**kwargs: Any) -> dict[str, Any]:
    hyps = ["H1", "H2"]
    gold = kwargs.get("gold_hypothesis", "H1")
    if gold == "H_unknown" or kwargs.get("open_set_status"):
        hyps = ["H1", "H2", "H_unknown"]
    belief = kwargs.get("belief") or {h: 1.0 / len(hyps) for h in hyps}
    recov = kwargs.get("recoverability_class", "recoverable")
    mismatch = float(kwargs.get("mismatch_mu", 0.0))
    return {
        "state_id": kwargs["state_id"],
        "source": "adversarial_construct",
        "split_role": kwargs.get("split_role", "adversarial"),
        "cluster_id": kwargs.get("cluster_id", kwargs["state_id"]),
        "channel": "construct",
        "year": 2019,
        "belief": belief,
        "entropy": finite_entropy(belief),
        "unknown_mass": float(belief.get("H_unknown", 0.0)),
        "proxy_kernels": proxy_kernels(recov, mismatch, len(hyps), hyps=hyps, gold=gold),
        "true_kernels": true_kernels(recov, gold, len(hyps), hyps=hyps),
        "mismatch_mu": mismatch,
        "eta": kwargs.get("eta", 0.2),
        "gold_hypothesis": gold,
        "open_set_status": gold == "H_unknown" or kwargs.get("open_set_status", False),
        "recoverability_class": recov,
        "ambiguity_class": list(kwargs.get("ambiguity_class", ["observational_degeneracy"])),
        "transformation": "clean",
        "q_obs": kwargs.get("q_obs", "construct"),
        "candidate_hypotheses": list(hyps),
        "attack": kwargs.get("attack"),
        "baseline_favorable": kwargs.get("baseline_favorable"),
    }


def adversarial_suite() -> list[dict[str, Any]]:
    return [
        _base(
            state_id="adv-clear",
            belief={"H1": 0.96, "H2": 0.04},
            gold_hypothesis="H1",
            recoverability_class="recoverable",
            eta=0.0,
            q_obs="unambiguous catalog identifier",
            attack="clear_query",
            baseline_favorable="immediate_ANSWER",
            ambiguity_class=["lexical_ambiguity"],
        ),
        _base(
            state_id="adv-perfect-top1",
            belief={"H1": 0.91, "H2": 0.09},
            gold_hypothesis="H1",
            attack="perfect_top1",
            baseline_favorable="BM25",
        ),
        _base(
            state_id="adv-nonrecov",
            belief={"H1": 0.5, "H2": 0.5},
            gold_hypothesis="H1",
            recoverability_class="non_recoverable",
            eta=0.8,
            attack="nonrecoverable_ambiguity",
            ambiguity_class=["non_recoverable_ambiguity"],
        ),
        _base(
            state_id="adv-misleading-R",
            belief={"H1": 0.5, "H2": 0.5},
            recoverability_class="recoverable",
            mismatch_mu=0.8,
            attack="misleading_recoverability",
            ambiguity_class=["misleading_proxy_evidence"],
        ),
        _base(
            state_id="adv-mismatch",
            belief={"H1": 0.52, "H2": 0.48},
            recoverability_class="mismatch_sensitive",
            mismatch_mu=0.7,
            attack="observation_model_mismatch",
        ),
        _base(
            state_id="adv-high-cost",
            belief={"H1": 0.5, "H2": 0.5},
            eta=0.4,
            attack="very_high_retrieval_cost",
        ),
        _base(
            state_id="adv-open",
            belief={"H1": 0.4, "H2": 0.2, "H_unknown": 0.4},
            gold_hypothesis="H_unknown",
            open_set_status=True,
            recoverability_class="non_recoverable",
            attack="open_set",
            ambiguity_class=["open_set", "non_recoverable_ambiguity"],
        ),
        _base(
            state_id="adv-false-conf",
            belief={"H1": 0.88, "H2": 0.12},
            gold_hypothesis="H2",
            attack="false_confidence_evidence",
            ambiguity_class=["misleading_proxy_evidence"],
        ),
    ]


def ops_structured_states(n: int = 96) -> list[dict[str, Any]]:
    """OPS-domain structured states. Cluster by incident class, not by degradation clone."""

    classes = (
        "ops.secret_rotation_mismatch",
        "ops.tls_cert_expired",
        "ops.dns_cache_stale",
        "ops.db_connection_pool",
        "ops.deploy_bad_canary",
        "ops.rate_limit_cascade",
        "ops.queue_backlog",
        "ops.cpu_throttle",
    )
    queries = {
        classes[0]: "intermittent 401 after rotation",
        classes[1]: "clients fail handshake edge healthy",
        classes[2]: "wrong ip after failover",
        classes[3]: "timeouts pool wait",
        classes[4]: "errors after partial rollout",
        classes[5]: "429 retry storm",
        classes[6]: "lag growing producers ok",
        classes[7]: "latency when noisy neighbor",
    }
    states = []
    for i in range(n):
        gold = classes[i % len(classes)]
        recov = "non_recoverable" if i % 9 == 0 else "recoverable"
        belief = {c: 0.08 for c in classes}
        belief[gold] = 0.44
        total = sum(belief.values())
        belief = {k: v / total for k, v in belief.items()}
        states.append(
            {
                "state_id": f"ops-struct-{i}",
                "source": "ops_structured",
                "split_role": "ops_cross_domain",
                "cluster_id": gold,
                "channel": "runbook",
                "year": 2024,
                "belief": belief,
                "entropy": finite_entropy(belief),
                "unknown_mass": 0.0,
                "proxy_kernels": proxy_kernels(recov, 0.1 if i % 5 == 0 else 0.0, len(classes), hyps=list(classes), gold=gold),
                "true_kernels": true_kernels(recov, gold, len(classes), hyps=list(classes)),
                "mismatch_mu": 0.1 if i % 5 == 0 else 0.0,
                "eta": 0.3 + 0.05 * (i % 4),
                "gold_hypothesis": gold,
                "open_set_status": False,
                "recoverability_class": recov,
                "ambiguity_class": ["semantic_ambiguity", "incomplete_context"],
                "transformation": "clean",
                "q_obs": queries[gold],
                "candidate_hypotheses": list(classes),
            }
        )
    return states
