"""Synthetic oracle environment for one-step epistemic action values."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping

from quasar2.decision.gap import decompose_from_scenarios
from quasar2.decision.policies import (
    LearnedEpistemicPolicy,
    MyopicVoIPolicy,
    SPRTInspiredPolicy,
    TabularOraclePolicy,
    ThresholdPolicy,
)
from quasar2.math.voi import binary_zero_one_value, empirical_binary_voi_zero_one
from quasar2.recoverability import router_features
from quasar2.theory.kernels import KERNEL_FAMILIES, bernoulli_pair


def learned_features(
    belief: Mapping[str, float],
    kernels: Mapping[str, Mapping[str, float]],
    *,
    entropy: float,
    unknown_mass: float,
    inference_error: float | None,
    explore_cost: float,
    ask_cost: float,
    evidence_present: bool,
) -> list[float]:
    return router_features(
        dict(belief),
        tuple(belief),
        kernels,
        entropy=entropy,
        unknown_mass=unknown_mass,
        inference_error=inference_error,
        explore_cost=explore_cost,
        ask_cost=ask_cost,
        evidence_present=evidence_present,
    )


def _binary_entropy(b: float) -> float:
    if b <= 0.0 or b >= 1.0:
        return 0.0
    return -(b * math.log(b) + (1.0 - b) * math.log(1.0 - b)) / math.log(2.0)


def sample_states(n: int, *, seed: int = 0) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    families = list(KERNEL_FAMILIES)
    states = []
    for index in range(n):
        family = families[index % len(families)]
        pair = KERNEL_FAMILIES[family]
        b = rng.uniform(0.05, 0.95)
        explore_cost = rng.choice([0.02, 0.10, 0.25, 0.40])
        ask_cost = rng.choice([0.08, 0.28, 0.50])
        unknown = rng.choice([0.0, 0.0, 0.1, 0.5])
        inference = rng.choice([None, 0.0, 0.2, 0.5])
        belief = {"H1": b, "H2": 1.0 - b}
        if unknown > 0.0:
            scale = 1.0 - unknown
            belief = {"H1": b * scale, "H2": (1.0 - b) * scale, "H_unknown": unknown}
        states.append(
            {
                "family": family,
                "belief": belief,
                "kernels": pair,
                "entropy": _binary_entropy(b),
                "unknown_mass": unknown,
                "inference_error": inference,
                "explore_cost": explore_cost,
                "ask_cost": ask_cost,
                "evidence_present": True,
            }
        )
    return states


def _recommend(policy: Any, state: dict[str, Any]):
    kwargs = dict(
        belief=state["belief"],
        kernels=state["kernels"],
        entropy=state["entropy"],
        unknown_mass=state["unknown_mass"],
        inference_error=state["inference_error"],
        evidence_present=state["evidence_present"],
        explore_cost=state["explore_cost"],
        ask_cost=state["ask_cost"],
        top_probability=max(state["belief"].values()) if state["belief"] else 0.0,
        margin=0.0,
    )
    if isinstance(policy, TabularOraclePolicy):
        policy = TabularOraclePolicy(
            explore_cost=state["explore_cost"],
            ask_cost=state["ask_cost"],
        )
    if isinstance(policy, MyopicVoIPolicy):
        policy = MyopicVoIPolicy(
            explore_cost=state["explore_cost"],
            ask_cost=state["ask_cost"],
        )
    return policy.recommend(**kwargs)


def oracle_q(state: dict[str, Any]) -> dict[str, float]:
    return dict(
        TabularOraclePolicy(
            explore_cost=state["explore_cost"],
            ask_cost=state["ask_cost"],
        ).recommend(
            belief=state["belief"],
            kernels=state["kernels"],
            entropy=state["entropy"],
            unknown_mass=state["unknown_mass"],
            inference_error=state["inference_error"],
            evidence_present=state["evidence_present"],
        ).estimated_q
    )


def compare_policies(n: int = 400, *, seed: int = 0) -> dict[str, Any]:
    states = sample_states(n, seed=seed)
    train = states[: n // 2]
    test = states[n // 2 :]
    oracle = TabularOraclePolicy()
    learned = LearnedEpistemicPolicy()
    feature_rows = [
        learned_features(
            state["belief"],
            state["kernels"],
            entropy=state["entropy"],
            unknown_mass=state["unknown_mass"],
            inference_error=state["inference_error"],
            explore_cost=state["explore_cost"],
            ask_cost=state["ask_cost"],
            evidence_present=True,
        )
        for state in train
    ]
    labels = [_recommend(oracle, state).selected_action for state in train]
    learned.fit(feature_rows, labels)
    policies = {
        "threshold": ThresholdPolicy(),
        "myopic_voi": MyopicVoIPolicy(),
        "sprt_inspired": SPRTInspiredPolicy(),
        "learned_epistemic": learned,
        "tabular_oracle": oracle,
    }
    table = []
    for name, policy in policies.items():
        agree = 0
        regret = 0.0
        neu = 0.0
        costs = 0.0
        answers = 0
        explores = 0
        for state in test:
            rec = _recommend(policy, state)
            q = oracle_q(state)
            oracle_action = max(q, key=lambda key: (q[key], key))
            if rec.selected_action == oracle_action:
                agree += 1
            regret += q[oracle_action] - q.get(rec.selected_action, q[oracle_action] - 1.0)
            neu += q.get(rec.selected_action, 0.0)
            if rec.selected_action == "EXPLORE":
                costs += state["explore_cost"]
                explores += 1
            if rec.selected_action == "ANSWER":
                answers += 1
        size = max(1, len(test))
        table.append(
            {
                "policy": name,
                "n": len(test),
                "agreement": agree / size,
                "regret": regret / size,
                "neu": neu / size,
                "mean_explore_cost": costs / size,
                "answer_rate": answers / size,
                "explore_rate": explores / size,
            }
        )
    equal_budget = []
    for budget in (0.02, 0.10, 0.25, 0.40):
        for name, policy in policies.items():
            slice_states = [state for state in test if abs(state["explore_cost"] - budget) < 1e-12]
            if not slice_states:
                continue
            neu = 0.0
            for state in slice_states:
                rec = _recommend(policy, state)
                neu += oracle_q(state).get(rec.selected_action, 0.0)
            equal_budget.append(
                {
                    "explore_cost": budget,
                    "policy": name,
                    "n": len(slice_states),
                    "neu": neu / len(slice_states),
                }
            )
    scenarios = {
        "oracle": 1.0,
        "no_hypotheses": 0.72,
        "no_retrieval": 0.80,
        "proxy_recoverability": 0.88,
        "degraded_inference": 0.90,
        "routing_only": 0.86,
        "forced_stop": 0.83,
        "open_set_blind": 0.91,
        "misspecified_cost": 0.89,
        "shifted": 0.84,
        "evaluated": 0.82,
    }
    # Replace placeholder gaps with measured routing/stopping pieces from this run.
    oracle_neu = next(row["neu"] for row in table if row["policy"] == "tabular_oracle")
    myopic_neu = next(row["neu"] for row in table if row["policy"] == "myopic_voi")
    threshold_neu = next(row["neu"] for row in table if row["policy"] == "threshold")
    scenarios["oracle"] = oracle_neu
    scenarios["routing_only"] = myopic_neu
    scenarios["evaluated"] = threshold_neu
    scenarios["forced_stop"] = next(row["neu"] for row in table if row["policy"] == "sprt_inspired")
    gap = decompose_from_scenarios(scenarios)
    winners = {}
    for item in equal_budget:
        key = item["explore_cost"]
        current = winners.get(key)
        if current is None or item["neu"] > current["neu"]:
            winners[key] = item
    winner_names = {item["policy"] for item in winners.values()}
    return {
        "schema_version": "policy_compare.1",
        "n_train": len(train),
        "n_test": len(test),
        "seed": seed,
        "table": table,
        "equal_budget": equal_budget,
        "ranking_changes_across_budgets": len(winner_names) > 1,
        "budget_winners": {str(key): value["policy"] for key, value in winners.items()},
        "gap_decomposition": gap.to_dict(),
        "notes": (
            "Oracle Q is one-step 0-1 value under true kernels. "
            "Learned policy is imitation on the train split. "
            "Gap decomposition mixes measured routing/stopping NEU with illustrative nested gaps."
        ),
    }


def counterfactual_dataset(n: int = 200, *, seed: int = 1) -> list[dict[str, Any]]:
    rows = []
    for state in sample_states(n, seed=seed):
        q = oracle_q(state)
        oracle_action = max(q, key=lambda key: (q[key], key))
        b = float(state["belief"].get("H1", 0.5))
        pair = state["kernels"]
        voi = empirical_binary_voi_zero_one(b, pair["H1"], pair["H2"])
        for action, value in q.items():
            rows.append(
                {
                    "family": state["family"],
                    "action": action,
                    "oracle_q": value,
                    "oracle_action": oracle_action,
                    "reward": value,
                    "terminal": action in {"ANSWER", "DEFER"},
                    "voi_empirical": voi,
                    "v_now": binary_zero_one_value(b),
                    "explore_cost": state["explore_cost"],
                }
            )
    return rows
