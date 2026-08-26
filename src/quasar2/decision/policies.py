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
from quasar2.math.voi import (
    bound_gap,
    empirical_binary_voi_zero_one,
    empirical_decision_flip_probability,
    voi_bound_binary,
    voi_bound_general,
)
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


class QuadrantPolicy:
    name = "quadrant"

    def recommend(
        self,
        *,
        entropy: float,
        recoverability: float | None,
        inference_error: float | None,
        unknown_mass: float,
        **_: object,
    ) -> PolicyRecommendation:
        from quasar2.decision.shadow import recommended_action_v2_shadow

        action = recommended_action_v2_shadow(
            entropy=entropy,
            recoverability=recoverability,
            inference_error=inference_error,
            unknown_mass=unknown_mass,
        )
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=action,
            second_best_action=None,
            action_margin=0.0,
            estimated_q={action: 0.0},
            recoverability=recoverability,
            recoverability_method="quadrant_threshold",
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
            stop_reason="quadrant_heuristic",
            best_info_action=None,
            best_net_voi_ucb=None,
            notes="Ambiguity x recoverability quadrants. Not a VoI argmax.",
        )


class TabularOraclePolicy:
    """Oracle one-step 0-1 Q-values when kernels are the true observation model.

    Must not be run on WDI with proxy kernels claimed as oracle.
    """

    name = "tabular_oracle"

    def __init__(
        self,
        *,
        explore_cost: float = 0.10,
        ask_cost: float = 0.28,
        analyze_cost: float = 0.04,
    ) -> None:
        self.explore_cost = explore_cost
        self.ask_cost = ask_cost
        self.analyze_cost = analyze_cost

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
        from quasar2.math.voi import binary_zero_one_value

        pair = _top_pair_kernels(belief, kernels or {})
        q_answer = max(belief.values()) if belief else 0.0
        if pair is None or not kernels:
            q_explore = float("-inf")
            voi_emp = 0.0
            drs = 0.0
        else:
            left, right = pair
            b = float(belief.get(left, 0.0))
            voi_emp = empirical_binary_voi_zero_one(b, kernels[left], kernels[right])
            drs = empirical_decision_flip_probability(b, kernels[left], kernels[right])
            q_explore = binary_zero_one_value(b) + voi_emp - self.explore_cost
            q_answer = binary_zero_one_value(b)
        voc = 0.0
        if inference_error is not None and evidence_present:
            voc = max(0.0, min(inference_error, 1.0)) * 0.5
        q_analyze = voc - self.analyze_cost
        q_ask = entropy * (1.0 - drs) + 0.5 * drs - self.ask_cost
        q_defer = unknown_mass - 0.08
        estimated_q = {
            "ANSWER": q_answer,
            "ANALYZE": q_analyze,
            "EXPLORE": q_explore,
            "ASK": q_ask,
            "DEFER": q_defer,
        }
        selected = max(estimated_q, key=lambda name: (estimated_q[name], name))
        ranked = sorted(estimated_q, key=lambda name: (-estimated_q[name], name))
        second = ranked[1] if len(ranked) > 1 else None
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=selected,
            second_best_action=second,
            action_margin=estimated_q[ranked[0]] - estimated_q[second] if second else 0.0,
            estimated_q=estimated_q,
            recoverability=drs,
            recoverability_method="decision_recoverability_oracle_kernels",
            raw_voi=voi_emp if pair is not None else None,
            voi_empirical=voi_emp if pair is not None else None,
            voi_bound_binary=None,
            voi_bound_general=None,
            voi_bound_gap=None,
            voi_bound_violated=None,
            net_voi=estimated_q.get(selected),
            retrieval_cost=self.explore_cost,
            compute_cost=self.analyze_cost,
            risk_cost=unknown_mass,
            stop_decision=selected in {"ANSWER", "DEFER"},
            stop_reason="oracle_argmax",
            best_info_action=max(
                ("ANALYZE", "EXPLORE", "ASK"),
                key=lambda name: (estimated_q[name], name),
            ),
            best_net_voi_ucb=max(estimated_q[name] for name in ("ANALYZE", "EXPLORE", "ASK")),
            notes="Oracle one-step Q under true kernels and 0-1 utility. Not WDI-safe.",
        )


class SPRTInspiredPolicy:
    """Sequential log-likelihood ratio heuristic. Not classical SPRT.

    Classical SPRT assumes i.i.d. observations, two simple hypotheses, and
    known error targets that yield exact thresholds. This policy uses proxy
    kernels, a single look by default, and expected LLR of one observation.
    """

    name = "sprt_inspired"

    def __init__(self, *, alpha: float = 0.05, beta: float = 0.05, explore_cost: float = 0.10) -> None:
        self.alpha = alpha
        self.beta = beta
        self.explore_cost = explore_cost

    def recommend(
        self,
        *,
        belief: Mapping[str, float],
        kernels: Mapping[str, Mapping[str, float]] | None,
        entropy: float,
        unknown_mass: float,
        inference_error: float | None,
        evidence_present: bool,
        llr_accumulated: float = 0.0,
        **_: object,
    ) -> PolicyRecommendation:
        import math

        upper = math.log((1.0 - self.beta) / max(self.alpha, 1e-9))
        lower = math.log(self.beta / max(1.0 - self.alpha, 1e-9))
        pair = _top_pair_kernels(belief, kernels or {})
        expected_llr = 0.0
        if pair is not None and kernels is not None:
            left, right = pair
            p1, p2 = kernels[left], kernels[right]
            outcomes = sorted(set(p1) | set(p2))
            b = float(belief.get(left, 0.0))
            for outcome in outcomes:
                p1_o = max(1e-12, float(p1.get(outcome, 0.0)))
                p2_o = max(1e-12, float(p2.get(outcome, 0.0)))
                m_o = b * p1_o + (1.0 - b) * p2_o
                if m_o <= 0.0:
                    continue
                expected_llr += m_o * math.log(p1_o / p2_o)
        projected = llr_accumulated + expected_llr
        if unknown_mass >= 0.45:
            selected = "DEFER"
        elif llr_accumulated >= upper or llr_accumulated <= lower:
            selected = "ANSWER"
        elif abs(projected) >= abs(upper) * 0.5 and expected_llr != 0.0:
            selected = "EXPLORE"
        elif entropy >= 0.5:
            selected = "ASK"
        else:
            selected = "ANSWER"
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=selected,
            second_best_action=None,
            action_margin=abs(projected),
            estimated_q={selected: projected},
            recoverability=abs(expected_llr),
            recoverability_method="expected_llr",
            raw_voi=abs(expected_llr),
            voi_empirical=None,
            voi_bound_binary=None,
            voi_bound_general=None,
            voi_bound_gap=None,
            voi_bound_violated=None,
            net_voi=abs(expected_llr) - self.explore_cost,
            retrieval_cost=self.explore_cost,
            compute_cost=0.0,
            risk_cost=unknown_mass,
            stop_decision=selected in {"ANSWER", "DEFER"},
            stop_reason="sprt_inspired_threshold",
            best_info_action="EXPLORE" if selected == "EXPLORE" else None,
            best_net_voi_ucb=abs(expected_llr),
            notes=(
                "SPRT-inspired expected LLR on proxy kernels. Not Wald SPRT; "
                "observations are not assumed i.i.d. or exactly Bernoulli."
            ),
        )


class LearnedEpistemicPolicy:
    """Imitation / cost-sensitive linear router. Trained only in synthetic oracle envs."""

    name = "learned_epistemic"

    def __init__(self, weights: dict[str, list[float]] | None = None) -> None:
        self.weights = weights or {}
        self.actions = ("ANSWER", "ANALYZE", "EXPLORE", "ASK", "DEFER")
        self.feature_width = 0

    def fit(self, feature_rows: list[list[float]], oracle_actions: list[str], *, lam: float = 1e-2) -> None:
        from quasar2.math.linear import ridge_fit

        self.feature_width = len(feature_rows[0]) if feature_rows else 0
        for action in self.actions:
            targets = [1.0 if label == action else 0.0 for label in oracle_actions]
            self.weights[action] = ridge_fit(feature_rows, targets, lam=lam)

    def recommend(
        self,
        *,
        belief: Mapping[str, float],
        kernels: Mapping[str, Mapping[str, float]] | None,
        entropy: float,
        unknown_mass: float,
        inference_error: float | None,
        evidence_present: bool,
        explore_cost: float = 0.10,
        ask_cost: float = 0.28,
        **_: object,
    ) -> PolicyRecommendation:
        from quasar2.math.linear import dot
        from quasar2.recoverability import router_features

        kernels = kernels or {}
        features = router_features(
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
        if not self.weights:
            selected = "ANSWER"
            estimated_q = {action: 0.0 for action in self.actions}
        else:
            estimated_q = {}
            width = None
            for action, weights in self.weights.items():
                width = len(weights)
                vec = features[:width]
                if len(vec) < width:
                    vec = vec + [0.0] * (width - len(vec))
                estimated_q[action] = dot(weights, vec)
            selected = max(estimated_q, key=lambda name: (estimated_q[name], name))
        return PolicyRecommendation(
            policy_name=self.name,
            selected_action=selected,
            second_best_action=None,
            action_margin=0.0,
            estimated_q=estimated_q,
            recoverability=None,
            recoverability_method="learned_features",
            raw_voi=None,
            voi_empirical=None,
            voi_bound_binary=None,
            voi_bound_general=None,
            voi_bound_gap=None,
            voi_bound_violated=None,
            net_voi=None,
            retrieval_cost=explore_cost,
            compute_cost=0.0,
            risk_cost=unknown_mass,
            stop_decision=selected in {"ANSWER", "DEFER"},
            stop_reason="learned_argmax",
            best_info_action=None,
            best_net_voi_ucb=None,
            notes="Linear imitation of oracle actions. No gold-intent features.",
        )


POLICIES = {
    "legacy": LegacyPolicy(),
    "threshold": ThresholdPolicy(),
    "quadrant": QuadrantPolicy(),
    "myopic_voi": MyopicVoIPolicy(),
    "receding_horizon": RecedingHorizonPolicy(horizon=1),
    "sprt_inspired": SPRTInspiredPolicy(),
    "tabular_oracle": TabularOraclePolicy(),
    "learned_epistemic": LearnedEpistemicPolicy(),
}
