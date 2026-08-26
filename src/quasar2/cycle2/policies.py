"""Experimental policies. Legacy executed policy is never replaced."""

from __future__ import annotations

from typing import Any, Mapping

from quasar2.cycle2.action_value import estimate_action_values, select_action
from quasar2.cycle2.observation import finite_entropy
from quasar2.cycle2.recoverability_state import belief_margin
from quasar2.recoverability import router_features
from quasar2.decision.policies import LearnedEpistemicPolicy, ThresholdPolicy
from quasar2.math.linear import ridge_fit


FORBIDDEN_FEATURE_TOKENS = (
    "gold",
    "correct_hypothesis",
    "future",
    "oracle_q",
    "delta_u",
    "voi_oracle",
    "r_star",
    "true_kernel",
    "family",
    "mismatch_mu_true",
)


def leakage_features(names: tuple[str, ...]) -> list[str]:
    joined = [n.lower() for n in names]
    return [n for n in joined if any(tok in n for tok in FORBIDDEN_FEATURE_TOKENS)]


class ImmediateAnswerPolicy:
    name = "immediate_answer"

    def recommend(self, **_: object) -> dict[str, Any]:
        return {
            "policy_name": self.name,
            "selected_action": "ANSWER",
            "second_action": None,
            "action_margin": 0.0,
            "policy_confidence": 1.0,
            "estimated_q": {"ANSWER": 0.0},
            "notes": "Strong baseline: never acquire.",
        }


class EntropyOnlyPolicy:
    name = "entropy_only"

    def recommend(self, *, belief: Mapping[str, float], unknown_mass: float = 0.0, **_: object) -> dict[str, Any]:
        ent = finite_entropy(belief)
        if unknown_mass >= 0.45:
            action = "DEFER"
        elif ent >= 0.5:
            action = "EXPLORE"
        else:
            action = "ANSWER"
        return {
            "policy_name": self.name,
            "selected_action": action,
            "second_action": None,
            "action_margin": abs(ent - 0.5),
            "policy_confidence": min(1.0, abs(ent - 0.5) * 2),
            "estimated_q": {action: ent},
            "notes": "Uncertainty-only acquisition.",
        }


class RandomBudgetPolicy:
    name = "random_budget"

    def __init__(self, *, rate: float = 0.25, seed: int = 0) -> None:
        self.rate = rate
        self.seed = seed
        self._n = 0

    def recommend(self, **_: object) -> dict[str, Any]:
        self._n += 1
        # Deterministic hashed coin, not Python hash randomization.
        token = f"{self.seed}:{self._n}".encode("utf-8")
        import hashlib

        draw = int(hashlib.sha256(token).hexdigest()[:8], 16) / 2**32
        action = "EXPLORE" if draw < self.rate else "ANSWER"
        return {
            "policy_name": self.name,
            "selected_action": action,
            "second_action": None,
            "action_margin": abs(draw - self.rate),
            "policy_confidence": 0.0,
            "estimated_q": {action: 0.0},
            "notes": "Equal-budget random acquisition.",
        }


class EmpiricalMyopicPolicy:
    name = "empirical_myopic"

    def recommend(
        self,
        *,
        belief: Mapping[str, float],
        kernels: Mapping[str, Mapping[str, float]] | None,
        explore_cost: float = 0.10,
        ask_cost: float = 0.28,
        rho: float = 1.4,
        unknown_mass: float = 0.0,
        inference_error: float | None = None,
        **_: object,
    ) -> dict[str, Any]:
        estimates = estimate_action_values(
            belief,
            kernels,
            explore_cost=explore_cost,
            ask_cost=ask_cost,
            rho=rho,
            unknown_mass=unknown_mass,
            inference_error=inference_error,
            provenance="empirical_proxy",
        )
        choice = select_action(estimates, mode="mean")
        return {
            "policy_name": self.name,
            "selected_action": choice["selected_action"],
            "second_action": choice["second_action"],
            "action_margin": choice["action_margin"],
            "policy_confidence": choice["policy_confidence"],
            "near_tie": choice["near_tie"],
            "estimated_q": choice.get("estimated_q"),
            "t2_bound": estimates["EXPLORE"].t2_bound,
            "t2_is_not_q": True,
            "notes": "Empirical one-step Q from proxy kernels; T2 bound is diagnostic only.",
        }


class ConservativeLCBPolicy:
    name = "conservative_lcb"

    def recommend(
        self,
        *,
        belief: Mapping[str, float],
        kernels: Mapping[str, Mapping[str, float]] | None,
        explore_cost: float = 0.10,
        rho: float = 1.4,
        unknown_mass: float = 0.0,
        **_: object,
    ) -> dict[str, Any]:
        estimates = estimate_action_values(
            belief,
            kernels,
            explore_cost=explore_cost,
            rho=rho,
            unknown_mass=unknown_mass,
            provenance="empirical_proxy_lcb",
        )
        # Without validated intervals, LCB discounts by a declared conservative gap, not a fake CI.
        discounted = {}
        for name, est in estimates.items():
            gap = 0.05 + 0.1 * (0.0 if est.uncertainty is None else est.uncertainty)
            discounted[name] = est.net_value - gap
        ranked = sorted(discounted, key=lambda n: (-discounted[n], n))
        return {
            "policy_name": self.name,
            "selected_action": ranked[0],
            "second_action": ranked[1] if len(ranked) > 1 else None,
            "action_margin": discounted[ranked[0]] - discounted[ranked[1]] if len(ranked) > 1 else 0.0,
            "policy_confidence": 0.0,
            "estimated_q": discounted,
            "notes": "Conservative empirical rule, not a formal SPI guarantee.",
        }


class OraclePolicy:
    name = "oracle"

    def recommend(
        self,
        *,
        belief: Mapping[str, float],
        true_kernels: Mapping[str, Mapping[str, float]] | None,
        explore_cost: float = 0.10,
        rho: float = 1.4,
        unknown_mass: float = 0.0,
        **_: object,
    ) -> dict[str, Any]:
        estimates = estimate_action_values(
            belief,
            true_kernels,
            explore_cost=explore_cost,
            rho=rho,
            unknown_mass=unknown_mass,
            provenance="ORACLE_ONLY",
        )
        choice = select_action(estimates)
        return {
            "policy_name": self.name,
            "selected_action": choice["selected_action"],
            "second_action": choice["second_action"],
            "action_margin": choice["action_margin"],
            "policy_confidence": choice["policy_confidence"],
            "estimated_q": choice.get("estimated_q"),
            "notes": "True-kernel counterfactual oracle. Not deployment-safe.",
        }


def threshold_recommend(belief: Mapping[str, float], unknown_mass: float, entropy: float) -> dict[str, Any]:
    rec = ThresholdPolicy().recommend(
        top_probability=max(belief.values()) if belief else 0.0,
        margin=belief_margin(belief),
        unknown_mass=unknown_mass,
        entropy=entropy,
    )
    return {
        "policy_name": "threshold",
        "selected_action": rec.selected_action,
        "second_action": rec.second_best_action,
        "action_margin": rec.action_margin,
        "policy_confidence": 0.0,
        "estimated_q": dict(rec.estimated_q),
        "notes": rec.notes,
    }


def fit_learned(train_rows: list[Mapping[str, Any]]) -> LearnedEpistemicPolicy:
    policy = LearnedEpistemicPolicy()
    features = []
    labels = []
    for row in train_rows:
        features.append(
            router_features(
                row["belief"],
                tuple(row["belief"]),
                row["proxy_kernels"],
                entropy=float(row["entropy"]),
                unknown_mass=float(row["unknown_mass"]),
                inference_error=None,
                explore_cost=float(row["explore_cost"]),
                ask_cost=0.28,
                evidence_present=True,
            )
        )
        labels.append(max(row["oracle_q"], key=lambda k: (row["oracle_q"][k], k)))
    if features:
        policy.fit(features, labels)
    return policy


def learned_recommend(policy: LearnedEpistemicPolicy, row: Mapping[str, Any]) -> dict[str, Any]:
    rec = policy.recommend(
        belief=row["belief"],
        kernels=row["proxy_kernels"],
        entropy=row["entropy"],
        unknown_mass=row["unknown_mass"],
        inference_error=None,
        evidence_present=True,
        explore_cost=row["explore_cost"],
        ask_cost=0.28,
    )
    return {
        "policy_name": "learned",
        "selected_action": rec.selected_action,
        "second_action": rec.second_best_action,
        "action_margin": rec.action_margin,
        "estimated_q": dict(rec.estimated_q),
        "notes": rec.notes,
    }


def evaluate_against_oracle(row: Mapping[str, Any], selected: str) -> dict[str, float | str | bool]:
    q = row["oracle_q"]
    optimal = max(q, key=lambda k: (q[k], k))
    regret = float(q[optimal]) - float(q.get(selected, q["ANSWER"]))
    ranked = sorted(q, key=lambda k: (-q[k], k))
    near = abs(q[ranked[0]] - q[ranked[1]]) <= 0.01 if len(ranked) > 1 else False
    return {
        "optimal": optimal,
        "selected": selected,
        "regret": regret,
        "agreement": selected == optimal,
        "near_tie": near,
        "wrong_answer": selected == "ANSWER" and row.get("open_set") and selected == "ANSWER",
    }
