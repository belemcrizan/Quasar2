"""Comparable policies. Legacy execution is never replaced by these recommenders.

MyopicVoIPolicy is a one-step approximation of Q. RecedingHorizonPolicy with
horizon>1 is not implemented; horizon=1 delegates to myopic VoI.
TabularOraclePolicy requires an oracle value table and must not run on WDI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from quasar2.decision.ablations import V2_POLICY_ABLATIONS
from quasar2.math.stopping import StopDecision, stop_if_all_ucb_nonpositive
from quasar2.math.voi import bound_gap, empirical_binary_voi_zero_one, voi_bound_binary, voi_bound_general
from quasar2.recoverability import ESTIMATORS


@dataclass(frozen=True, slots=True)
class PolicyRecommendation:
    policy_name: str
    selected_action: str
    second_best_action: str | None
    action_margin: float
    estimated_q: Mapping[str, float]
    recoverability: float | None
    recoverability_method: str | None
    raw_voi: float | None
    voi_empirical: float | None
    voi_bound_binary: float | None
    voi_bound_general: float | None
    voi_bound_gap: float | None
    voi_bound_violated: bool | None
    net_voi: float | None
    retrieval_cost: float
    compute_cost: float
    risk_cost: float
    stop_decision: bool
    stop_reason: str
    best_info_action: str | None
    best_net_voi_ucb: float | None
    notes: str


def _top_pair_kernels(
    belief: Mapping[str, float],
    kernels: Mapping[str, Mapping[str, float]],
) -> tuple[str, str] | None:
    ranked = sorted(
        (hyp for hyp in belief if hyp in kernels),
        key=lambda hyp: (-float(belief[hyp]), hyp),
    )
    if len(ranked) < 2:
        return None
    return ranked[0], ranked[1]


class LegacyPolicy:
    name = "legacy"

    def recommend(self, executed_action: str, **_: object) -> PolicyRecommendation:
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=executed_action,
            second_best_action=None,
            action_margin=0.0,
            estimated_q={executed_action: 0.0},
            recoverability=None,
            recoverability_method=None,
            raw_voi=None,
            voi_empirical=None,
            voi_bound_binary=None,
            voi_bound_general=None,
            voi_bound_gap=None,
            voi_bound_violated=None,
            net_voi=None,
            retrieval_cost=0.0,
            compute_cost=0.0,
            risk_cost=0.0,
            stop_decision=executed_action in {"ANSWER", "DEFER"},
            stop_reason="legacy_executed",
            best_info_action=None,
            best_net_voi_ucb=None,
            notes="Copies the executed v0.1.1 action.",
        )


class ThresholdPolicy:
    name = "threshold"

    def recommend(
        self,
        *,
        top_probability: float,
        margin: float,
        unknown_mass: float,
        entropy: float,
        answer_confidence: float = 0.67,
        answer_margin: float = 0.20,
        unknown_defer: float = 0.45,
        **_: object,
    ) -> PolicyRecommendation:
        if unknown_mass >= unknown_defer:
            action = "DEFER"
        elif top_probability >= answer_confidence and margin >= answer_margin:
            action = "ANSWER"
        elif entropy >= 0.5:
            action = "EXPLORE"
        else:
            action = "ASK"
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=action,
            second_best_action=None,
            action_margin=0.0,
            estimated_q={action: 0.0},
            recoverability=None,
            recoverability_method=None,
            raw_voi=None,
            voi_empirical=None,
            voi_bound_binary=None,
            voi_bound_general=None,
            voi_bound_gap=None,
            voi_bound_violated=None,
            net_voi=None,
            retrieval_cost=0.0,
            compute_cost=0.0,
            risk_cost=0.0,
            stop_decision=action in {"ANSWER", "DEFER"},
            stop_reason="threshold_gates",
            best_info_action=None,
            best_net_voi_ucb=None,
            notes="Heuristic gates; not a VoI argmax.",
        )


class MyopicVoIPolicy:
    """One-step NetVoI recommender. Does not execute actions."""

    name = "myopic_voi"

    def __init__(
        self,
        *,
        recoverability: str = "jsd",
        lambda_cost: float = 1.0,
        lambda_risk: float = 1.0,
        explore_cost: float = 0.10,
        ask_cost: float = 0.28,
        analyze_cost: float = 0.04,
        ablation: str = "full",
    ) -> None:
        if ablation not in V2_POLICY_ABLATIONS:
            raise ValueError(f"Unknown v2 ablation {ablation!r}")
        self.recoverability_name = recoverability
        self.lambda_cost = lambda_cost
        self.lambda_risk = lambda_risk
        self.explore_cost = explore_cost
        self.ask_cost = ask_cost
        self.analyze_cost = analyze_cost
        self.ablation = ablation

    def recommend(
        self,
        *,
        belief: Mapping[str, float],
        kernels: Mapping[str, Mapping[str, float]] | None,
        entropy: float,
        unknown_mass: float,
        inference_error: float | None,
        evidence_present: bool,
        **_: object,
    ) -> PolicyRecommendation:
        no_cost = self.ablation == "noCost"
        no_risk = self.ablation == "noRisk"
        no_voi = self.ablation == "noVoI"
        no_rec = self.ablation == "noRecoverability"
        lambda_c = 0.0 if no_cost else self.lambda_cost
        lambda_r = 0.0 if no_risk else self.lambda_risk
        retrieval_cost = 0.0 if no_cost else self.explore_cost
        compute_cost = 0.0 if no_cost else self.analyze_cost
        risk_cost = 0.0 if no_risk else unknown_mass

        rec_score = None
        rec_method = None
        voi_bin = None
        voi_gen = None
        voi_emp = None
        gap = None
        violated = None
        raw_voi = 0.0
        if kernels and not no_rec and not no_voi:
            estimator = ESTIMATORS.get(self.recoverability_name, ESTIMATORS["jsd"])
            result = estimator.estimate(belief, tuple(belief), "EXPLORE", kernels)
            rec_score = result.score
            rec_method = result.method
            pair = _top_pair_kernels(belief, kernels)
            if pair is not None:
                left, right = pair
                b = float(belief.get(left, 0.0))
                bound = voi_bound_binary(b, kernels[left], kernels[right])
                voi_bin = bound.voi_bound_tv
                voi_emp = empirical_binary_voi_zero_one(b, kernels[left], kernels[right])
                stats = bound_gap(voi_emp, bound.voi_bound_tv)
                gap = float(stats["voi_bound_gap"])
                violated = bool(stats["voi_bound_violated"])
                raw_voi = bound.voi_bound_tv
            general = voi_bound_general(kernels, belief)
            voi_gen = general.voi_bound_general
            if pair is None:
                raw_voi = general.voi_bound_general

        voc = 0.0
        if inference_error is not None and evidence_present and self.ablation != "noAnalyze":
            voc = max(0.0, min(inference_error, 1.0)) * 0.5

        net_explore = raw_voi - lambda_c * retrieval_cost - lambda_r * risk_cost
        net_analyze = voc - lambda_c * compute_cost
        net_ask = (entropy * (1.0 - (rec_score or 0.0))) - lambda_c * (0.0 if no_cost else self.ask_cost)
        if self.ablation == "noExplore":
            net_explore = float("-inf")
        if self.ablation == "noAnalyze":
            net_analyze = float("-inf")
        if self.ablation == "noAsk":
            net_ask = float("-inf")

        q_answer = max(belief.values()) - lambda_r * risk_cost if belief else 0.0
        q_defer = unknown_mass - 0.08 * lambda_c
        estimated_q = {
            "ANSWER": q_answer,
            "ANALYZE": net_analyze,
            "EXPLORE": net_explore,
            "ASK": net_ask,
            "DEFER": q_defer,
        }
        info_nets = {"ANALYZE": net_analyze, "EXPLORE": net_explore, "ASK": net_ask}
        finite_info = {key: value for key, value in info_nets.items() if value != float("-inf")}
        ucbs = dict(finite_info)
        if not ucbs:
            ucbs = {"ASK": -1.0}
            finite_info = {"ASK": -1.0}
        if self.ablation == "noUCB":
            best_info = max(finite_info, key=lambda name: (finite_info[name], name))
            stop = all(value <= 0.0 for value in finite_info.values())
            stop_decision = StopDecision(
                stop_decision=stop,
                stop_reason="point_net_voi_nonpositive" if stop else "positive_point_net_voi",
                best_info_action=best_info,
                best_net_voi=finite_info[best_info],
                best_net_voi_ucb=finite_info[best_info],
                alpha=0.05,
                multiple_comparison_method="none",
                coverage_scope="fixed_stage",
                look_index=1,
                false_stop=None,
                near_zero=False,
            )
        else:
            stop_decision = stop_if_all_ucb_nonpositive(
                ucbs,
                finite_info,
                alpha=0.05,
                method="point_bound_not_ucb",
            )

        if unknown_mass >= 0.45:
            selected = "DEFER"
        elif stop_decision.stop_decision and q_answer >= q_defer:
            selected = "ANSWER"
        elif stop_decision.stop_decision:
            selected = "DEFER"
        else:
            selected = max(finite_info, key=lambda name: (finite_info[name], name))

        ranked = sorted(
            estimated_q,
            key=lambda name: (
                0 if estimated_q[name] != float("-inf") else 1,
                -estimated_q[name] if estimated_q[name] != float("-inf") else 0.0,
                name,
            ),
        )
        second = ranked[1] if len(ranked) > 1 else None
        margin = estimated_q[ranked[0]] - estimated_q[second] if second else 0.0
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=selected,
            second_best_action=second,
            action_margin=margin,
            estimated_q=estimated_q,
            recoverability=rec_score,
            recoverability_method=rec_method,
            raw_voi=raw_voi if kernels and not no_voi else None,
            voi_empirical=voi_emp,
            voi_bound_binary=voi_bin,
            voi_bound_general=voi_gen,
            voi_bound_gap=gap,
            voi_bound_violated=violated,
            net_voi=finite_info.get(selected) if selected in finite_info else None,
            retrieval_cost=retrieval_cost,
            compute_cost=compute_cost,
            risk_cost=risk_cost,
            stop_decision=bool(stop_decision.stop_decision),
            stop_reason=str(stop_decision.stop_reason),
            best_info_action=stop_decision.best_info_action,
            best_net_voi_ucb=float(stop_decision.best_net_voi_ucb),
            notes=(
                "Myopic NetVoI uses proxy kernels and the Lipschitz bound as a "
                "point UCB (not a statistical tail bound)."
            ),
        )


class RecedingHorizonPolicy(MyopicVoIPolicy):
    name = "receding_horizon"

    def __init__(self, horizon: int = 1, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.horizon = horizon

    def recommend(self, **kwargs: object) -> PolicyRecommendation:
        result = super().recommend(**kwargs)
        note = result.notes
        if self.horizon != 1:
            note = "horizon>1 is NOT_IMPLEMENTED; fell back to myopic (horizon=1). " + note
        return replace(result, policy_name=self.name, notes=note)


POLICIES = {
    "legacy": LegacyPolicy(),
    "threshold": ThresholdPolicy(),
    "myopic_voi": MyopicVoIPolicy(),
    "receding_horizon": RecedingHorizonPolicy(horizon=1),
}
