"""Optional v2 shadow telemetry. Never changes the executed legacy action."""

from __future__ import annotations

from quasar2.belief.types import EstimatedBelief, diagnose
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
) -> DecisionTelemetry:
    estimated = EstimatedBelief.from_belief_state(belief)
    diagnostics = diagnose(estimated)
    unknown_mass = float(belief.probabilities.get(unknown_id, 0.0))
    recommended = recommended_action_v2_shadow(
        entropy=belief.normalized_entropy,
        recoverability=None,
        inference_error=diagnostics.inference_error_kl,
        unknown_mass=unknown_mass,
    )
    return DecisionTelemetry(
        belief_entropy=diagnostics.belief_entropy,
        prior_dispersion=diagnostics.prior_dispersion,
        recoverability=None,
        voi=None,
        net_voi=None,
        ucb=None,
        analyze_voc=None,
        inference_error=diagnostics.inference_error_kl,
        conformal_set_size=None,
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
    )
