"""Optional v2 shadow telemetry. Never changes the executed legacy action."""

from __future__ import annotations

from typing import Mapping

from quasar2.belief.types import EstimatedBelief, diagnose
from quasar2.decision.conformal import highest_mass_set
from quasar2.decision.kernels import bernoulli_support_kernels
from quasar2.decision.policies import LegacyPolicy, MyopicVoIPolicy, ThresholdPolicy
from quasar2.models.belief import BeliefState
from quasar2.models.decision import Decision
from quasar2.models.telemetry import DecisionTelemetry


def recommended_action_v2_shadow(
    *,
    entropy: float,
    recoverability: float | None,
    inference_error: float | None,
    unknown_mass: float,
) -> str:
    """Quadrant hypothesis, not a hard-coded policy.

    High entropy uses normalized entropy in [0, 1] when provided as such.
    """

    high_uncertainty = entropy >= 0.5
    high_recoverability = recoverability is not None and recoverability >= 0.25
    high_inference_error = inference_error is not None and inference_error >= 0.15
    if unknown_mass >= 0.45:
        return "DEFER"
    if high_inference_error and not high_recoverability:
        return "ANALYZE"
    if high_uncertainty and high_recoverability:
        return "EXPLORE"
    if high_uncertainty and not high_recoverability:
        return "ASK"
    return "ANSWER"


def build_shadow_telemetry(
    belief: BeliefState,
    decision: Decision,
    *,
    unknown_id: str = "H_unknown",
    supports: Mapping[str, float] | None = None,
    shadow_policy: str = "quadrant",
) -> DecisionTelemetry:
    estimated = EstimatedBelief.from_belief_state(belief)
    diagnostics = diagnose(estimated)
    unknown_mass = float(belief.probabilities.get(unknown_id, 0.0))
    kernels = bernoulli_support_kernels(supports) if supports else None
    rec_score = None
    rec_method = None
    recommendation = None
    if shadow_policy == "legacy":
        recommendation = LegacyPolicy().recommend(decision.action.value)
    elif shadow_policy == "threshold":
        recommendation = ThresholdPolicy().recommend(
            top_probability=belief.top_probability,
            margin=belief.margin,
            unknown_mass=unknown_mass,
            entropy=belief.normalized_entropy,
        )
    elif shadow_policy == "myopic_voi":
        recommendation = MyopicVoIPolicy().recommend(
            belief=dict(belief.probabilities),
            kernels=kernels,
            entropy=belief.normalized_entropy,
            unknown_mass=unknown_mass,
            inference_error=diagnostics.inference_error_kl,
            evidence_present=bool(supports),
        )
        rec_score = recommendation.recoverability
        rec_method = recommendation.recoverability_method
    else:
        if kernels:
            from quasar2.recoverability import ESTIMATORS

            result = ESTIMATORS["jsd"].estimate(
                dict(belief.probabilities),
                tuple(belief.probabilities),
                "EXPLORE",
                kernels,
            )
            rec_score = result.score
            rec_method = result.method + "_proxy_kernels"
        recommended = recommended_action_v2_shadow(
            entropy=belief.normalized_entropy,
            recoverability=rec_score,
            inference_error=diagnostics.inference_error_kl,
            unknown_mass=unknown_mass,
        )
    conformal = highest_mass_set(dict(belief.probabilities), alpha=0.1)
    if recommendation is not None:
        recommended = recommendation.selected_action
        rec_score = recommendation.recoverability if rec_score is None else rec_score
        rec_method = recommendation.recoverability_method if rec_method is None else rec_method
        q = recommendation.estimated_q
        return DecisionTelemetry(
            belief_entropy=diagnostics.belief_entropy,
            prior_dispersion=diagnostics.prior_dispersion,
            recoverability=rec_score,
            voi=recommendation.raw_voi,
            voi_true_oracle=None,
            voi_estimate=recommendation.voi_empirical,
            net_voi=recommendation.net_voi,
            ucb=recommendation.best_net_voi_ucb,
            analyze_voc=q.get("ANALYZE"),
            inference_error=diagnostics.inference_error_kl,
            conformal_set_size=len(conformal.members),
            selected_action=decision.action.value,
            recommended_action_v2=recommended,
            executed_action_legacy=decision.action.value,
            action_utility=float(decision.utilities.get(decision.action.value, 0.0)),
            cost=recommendation.retrieval_cost + recommendation.compute_cost,
            risk=recommendation.risk_cost,
            unknown_probability=unknown_mass,
            belief_top1=diagnostics.belief_top1,
            belief_top2=diagnostics.belief_top2,
            belief_margin=diagnostics.belief_margin,
            policy_name=recommendation.policy_name,
            recoverability_method=rec_method,
            voi_bound_binary=recommendation.voi_bound_binary,
            voi_bound_general=recommendation.voi_bound_general,
            voi_empirical=recommendation.voi_empirical,
            voi_bound_gap=recommendation.voi_bound_gap,
            voi_bound_violated=recommendation.voi_bound_violated,
            stop_decision=recommendation.stop_decision,
            stop_reason=recommendation.stop_reason,
            best_info_action=recommendation.best_info_action,
            conformal_alpha=conformal.alpha,
            conformal_coverage=None,
            nonconformity_score=conformal.nonconformity_score,
            estimated_q_answer=q.get("ANSWER"),
            estimated_q_analyze=q.get("ANALYZE"),
            estimated_q_explore=q.get("EXPLORE"),
            estimated_q_ask=q.get("ASK"),
            estimated_q_defer=q.get("DEFER"),
            second_best_action=recommendation.second_best_action,
            action_margin=recommendation.action_margin,
            shadow_policy=shadow_policy,
            kernel_source="bernoulli_support_proxy" if kernels else None,
        )
    return DecisionTelemetry(
        belief_entropy=diagnostics.belief_entropy,
        prior_dispersion=diagnostics.prior_dispersion,
        recoverability=rec_score,
        voi=None,
        net_voi=None,
        ucb=None,
        analyze_voc=None,
        inference_error=diagnostics.inference_error_kl,
        conformal_set_size=len(conformal.members),
        selected_action=decision.action.value,
        recommended_action_v2=recommended,
        executed_action_legacy=decision.action.value,
        action_utility=float(decision.utilities.get(decision.action.value, 0.0)),
        cost=None,
        risk=None,
        unknown_probability=unknown_mass,
        belief_top1=diagnostics.belief_top1,
        belief_top2=diagnostics.belief_top2,
        belief_margin=diagnostics.belief_margin,
        policy_name="legacy_shadow",
        recoverability_method=rec_method,
        conformal_alpha=conformal.alpha,
        conformal_coverage=None,
        nonconformity_score=conformal.nonconformity_score,
        shadow_policy=shadow_policy,
        kernel_source="bernoulli_support_proxy" if kernels else None,
    )
