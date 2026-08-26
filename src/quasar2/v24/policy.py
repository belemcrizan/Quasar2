"""One-step legal-action utility policy. Coefficients are frozen, not learned."""

from __future__ import annotations

from dataclasses import dataclass

from quasar2.v24.actions import LEGAL_TRANSITIONS, EpistemicAction
from quasar2.v24.state import PolicyState


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    lambda_cost: float = 0.15
    lambda_risk: float = 0.90
    lambda_waste: float = 0.20
    answer_margin: float = 0.12
    answer_coverage: float = 0.99
    unknown_defer: float = 0.45
    explore_entropy: float = 0.80
    ask_margin: float = 0.08


REASON_CODES = (
    "SUFFICIENT_EVIDENCE",
    "LOW_MARGIN",
    "HIGH_ENTROPY",
    "HIGH_UNKNOWN_MASS",
    "CONTRADICTORY_EVIDENCE",
    "MISSING_RECOVERABLE_SLOT",
    "MISSING_USER_OWNED_SLOT",
    "NO_POSITIVE_VALUE_OF_INFORMATION",
    "SOURCE_OR_DATA_FAILURE",
    "BUDGET_LIMIT",
    "RISK_LIMIT",
    "OPEN_SET",
    "DATA_NOT_AVAILABLE",
)


def legal_actions(state: PolicyState, last: str = "OBSERVE") -> tuple[EpistemicAction, ...]:
    key: str | EpistemicAction = "OBSERVE" if last == "OBSERVE" else EpistemicAction(last)
    allowed = set(LEGAL_TRANSITIONS[key])
    if state.budget.remaining_analyze <= 0:
        allowed.discard(EpistemicAction.ANALYZE)
    if state.budget.remaining_explore <= 0:
        allowed.discard(EpistemicAction.EXPLORE)
    if state.budget.remaining_ask <= 0:
        allowed.discard(EpistemicAction.ASK)
    if state.budget.remaining_steps <= 0 or state.budget.remaining_retrieval_calls <= 0:
        allowed -= {EpistemicAction.ANALYZE, EpistemicAction.EXPLORE, EpistemicAction.ASK}
        if not state.source_available:
            allowed = {EpistemicAction.DEFER}
        else:
            allowed = {EpistemicAction.ANSWER, EpistemicAction.DEFER}
    if not state.source_available:
        allowed = {EpistemicAction.DEFER}
    order = (
        EpistemicAction.ANSWER,
        EpistemicAction.ANALYZE,
        EpistemicAction.EXPLORE,
        EpistemicAction.ASK,
        EpistemicAction.DEFER,
    )
    return tuple(action for action in order if action in allowed)


def _risk(state: PolicyState) -> float:
    return (1.0 - state.margin) * (1.0 - state.coverage) + 0.5 * state.unknown_score + 0.3 * state.contradiction


def utilities(state: PolicyState, cfg: PolicyConfig) -> dict[str, float]:
    risk = _risk(state)
    top = max((h.belief_score for h in state.hypotheses if h.hypothesis_id != "H_unknown"), default=0.0)
    answer_benefit = top * state.coverage * (1.0 if state.margin >= cfg.answer_margin else 0.35)
    analyze_benefit = 0.12 if state.evidence_ids and state.entropy > 0.4 else 0.0
    explore_benefit = 0.22 * state.entropy if state.entropy >= cfg.explore_entropy * 0.5 else 0.02
    ask_benefit = 0.18 if state.margin < cfg.ask_margin and state.unknown_score < cfg.unknown_defer else 0.0
    defer_benefit = 0.25 if state.unknown_score >= cfg.unknown_defer or not state.source_available else 0.0
    costs = {
        EpistemicAction.ANSWER.value: 0.0,
        EpistemicAction.ANALYZE.value: 0.04,
        EpistemicAction.EXPLORE.value: 0.12,
        EpistemicAction.ASK.value: 0.20,
        EpistemicAction.DEFER.value: 0.08,
    }
    benefits = {
        EpistemicAction.ANSWER.value: answer_benefit,
        EpistemicAction.ANALYZE.value: analyze_benefit,
        EpistemicAction.EXPLORE.value: explore_benefit,
        EpistemicAction.ASK.value: ask_benefit,
        EpistemicAction.DEFER.value: defer_benefit,
    }
    waste = {
        EpistemicAction.ANSWER.value: 0.4 if state.coverage < cfg.answer_coverage else 0.0,
        EpistemicAction.ANALYZE.value: 0.3 if not state.evidence_ids else 0.0,
        EpistemicAction.EXPLORE.value: 0.2 if "EXPLORE" in state.history[-1:] else 0.0,
        EpistemicAction.ASK.value: 0.15,
        EpistemicAction.DEFER.value: 0.5 if state.coverage >= cfg.answer_coverage and top >= 0.6 else 0.0,
    }
    return {
        name: benefits[name] - cfg.lambda_cost * costs[name] - cfg.lambda_risk * (risk if name == "ANSWER" else 0.15 * risk) - cfg.lambda_waste * waste[name]
        for name in benefits
    }


def decide(state: PolicyState, *, last: str = "OBSERVE", cfg: PolicyConfig | None = None) -> tuple[EpistemicAction, str, dict[str, float]]:
    cfg = cfg or PolicyConfig()
    allowed = legal_actions(state, last)
    scores = utilities(state, cfg)
    ranked = sorted(allowed, key=lambda action: (-scores[action.value], action.value))
    chosen = ranked[0]
    if not state.source_available:
        return EpistemicAction.DEFER, "SOURCE_OR_DATA_FAILURE", scores
    if state.unknown_score >= cfg.unknown_defer and chosen != EpistemicAction.ASK:
        if EpistemicAction.DEFER in allowed:
            return EpistemicAction.DEFER, "HIGH_UNKNOWN_MASS", scores
    if chosen == EpistemicAction.ANSWER and (state.margin < cfg.answer_margin or state.coverage < cfg.answer_coverage):
        # Prefer a non-terminal repair when commitment is unsafe.
        for fallback, reason in (
            (EpistemicAction.EXPLORE, "LOW_MARGIN"),
            (EpistemicAction.ANALYZE, "HIGH_ENTROPY"),
            (EpistemicAction.ASK, "MISSING_USER_OWNED_SLOT"),
            (EpistemicAction.DEFER, "RISK_LIMIT"),
        ):
            if fallback in allowed:
                return fallback, reason, scores
    reason = {
        EpistemicAction.ANSWER: "SUFFICIENT_EVIDENCE",
        EpistemicAction.ANALYZE: "HIGH_ENTROPY",
        EpistemicAction.EXPLORE: "LOW_MARGIN",
        EpistemicAction.ASK: "MISSING_USER_OWNED_SLOT",
        EpistemicAction.DEFER: "OPEN_SET",
    }[chosen]
    return chosen, reason, scores
