"""Empirical action values. The T2 Lipschitz bound is never Q(s, EXPLORE)."""

from __future__ import annotations

from typing import Mapping

from quasar2.cycle2.observation import finite_entropy
from quasar2.cycle2.recoverability_state import _top_pair
from quasar2.cycle2.types import ActionValueEstimate
from quasar2.math.voi import voi_bound_binary


def answer_value(
    belief: Mapping[str, float],
    *,
    u_correct: float = 1.0,
    rho: float = 1.4,
    unknown_mass: float = 0.0,
) -> float:
    """Asymmetric ANSWER utility. U_wrong = -rho * U_correct."""

    top = max((float(v) for k, v in belief.items() if k != "H_unknown"), default=0.0)
    u_wrong = -abs(rho) * abs(u_correct)
    return top * u_correct + (1.0 - top) * u_wrong - 0.25 * unknown_mass


def posterior_answer_value(
    b: float,
    p1: Mapping[str, float],
    p2: Mapping[str, float],
    *,
    u_correct: float,
    rho: float,
) -> float:
    """E_o[U(ANSWER | b'(o))]. Independent of the T2 bound."""

    now = answer_value({"H1": b, "H2": 1.0 - b}, u_correct=u_correct, rho=rho)
    outcomes = sorted(set(p1) | set(p2))
    expected = 0.0
    for outcome in outcomes:
        p1_o = float(p1.get(outcome, 0.0))
        p2_o = float(p2.get(outcome, 0.0))
        m_o = b * p1_o + (1.0 - b) * p2_o
        if m_o <= 0.0:
            continue
        b_prime = b * p1_o / m_o
        expected += m_o * answer_value({"H1": b_prime, "H2": 1.0 - b_prime}, u_correct=u_correct, rho=rho)
    return expected - now


def ask_response_kernels(kind: str) -> dict[str, dict[str, float]]:
    if kind == "truthful":
        return {"H1": {"h1": 0.95, "h2": 0.03, "none": 0.02}, "H2": {"h1": 0.03, "h2": 0.95, "none": 0.02}}
    if kind == "incomplete":
        return {"H1": {"h1": 0.55, "h2": 0.10, "none": 0.35}, "H2": {"h1": 0.10, "h2": 0.55, "none": 0.35}}
    if kind == "noisy":
        return {"H1": {"h1": 0.65, "h2": 0.30, "none": 0.05}, "H2": {"h1": 0.30, "h2": 0.65, "none": 0.05}}
    if kind == "ambiguous":
        return {"H1": {"h1": 0.40, "h2": 0.40, "none": 0.20}, "H2": {"h1": 0.40, "h2": 0.40, "none": 0.20}}
    if kind == "refusal":
        return {"H1": {"h1": 0.02, "h2": 0.02, "none": 0.96}, "H2": {"h1": 0.02, "h2": 0.02, "none": 0.96}}
    raise KeyError(kind)


def estimate_action_values(
    belief: Mapping[str, float],
    kernels: Mapping[str, Mapping[str, float]] | None,
    *,
    explore_cost: float = 0.10,
    ask_cost: float = 0.28,
    analyze_cost: float = 0.04,
    defer_utility: float = -0.05,
    u_correct: float = 1.0,
    rho: float = 1.4,
    unknown_mass: float = 0.0,
    inference_error: float | None = None,
    evidence_present: bool = True,
    ask_model: str = "noisy",
    risk_lambda: float = 1.0,
    provenance: str = "empirical_proxy",
) -> dict[str, ActionValueEstimate]:
    entropy = finite_entropy(belief)
    q_answer_gross = answer_value(belief, u_correct=u_correct, rho=rho, unknown_mass=unknown_mass)
    risk_answer = risk_lambda * (1.0 - max((float(v) for k, v in belief.items() if k != "H_unknown"), default=0.0))
    pair = _top_pair(belief, kernels or {})
    t2 = None
    voi_emp = 0.0
    if pair is not None and kernels is not None:
        left, right = pair
        b = float(belief.get(left, 0.0))
        voi_emp = posterior_answer_value(
            b, kernels[left], kernels[right], u_correct=u_correct, rho=rho
        )
        t2 = voi_bound_binary(b, kernels[left], kernels[right]).voi_bound_tv
    q_explore_gross = q_answer_gross + voi_emp
    voc = 0.0
    if inference_error is not None and evidence_present:
        voc = max(0.0, min(float(inference_error), 1.0)) * 0.15 * abs(u_correct)
    ask_kernels = ask_response_kernels(ask_model)
    ask_pair = ("H1", "H2") if "H1" in belief and "H2" in belief else None
    ask_gain = 0.0
    if ask_pair is not None:
        b = float(belief.get("H1", 0.0))
        ask_gain = posterior_answer_value(
            b, ask_kernels["H1"], ask_kernels["H2"], u_correct=u_correct, rho=rho
        )
    q_defer_gross = float(defer_utility)
    if unknown_mass >= 0.45 or float(belief.get("H_unknown", 0.0)) >= 0.45:
        q_defer_gross = 0.0
    _ = entropy
    estimates = {
        "ANSWER": ActionValueEstimate(
            action="ANSWER",
            mean=q_answer_gross - risk_answer * 0.0,
            lower_bound=None,
            upper_bound=None,
            uncertainty=None,
            cost=0.0,
            risk=risk_answer,
            provenance=provenance,
            gross_gain=q_answer_gross,
            action_cost=0.0,
            risk_penalty=0.0,
            t2_bound=t2,
        ),
        "EXPLORE": ActionValueEstimate(
            action="EXPLORE",
            mean=q_explore_gross - explore_cost,
            lower_bound=None,
            upper_bound=None,
            uncertainty=None,
            cost=explore_cost,
            risk=unknown_mass,
            provenance=provenance,
            gross_gain=q_explore_gross,
            action_cost=explore_cost,
            risk_penalty=0.0,
            t2_bound=t2,
        ),
        "ASK": ActionValueEstimate(
            action="ASK",
            mean=q_answer_gross + ask_gain - ask_cost,
            lower_bound=None,
            upper_bound=None,
            uncertainty=None,
            cost=ask_cost,
            risk=0.1,
            provenance=f"{provenance}|ask_model={ask_model}",
            gross_gain=q_answer_gross + ask_gain,
            action_cost=ask_cost,
            risk_penalty=0.0,
            t2_bound=t2,
        ),
        "ANALYZE": ActionValueEstimate(
            action="ANALYZE",
            mean=q_answer_gross + voc - analyze_cost,
            lower_bound=None,
            upper_bound=None,
            uncertainty=None,
            cost=analyze_cost,
            risk=0.0,
            provenance=f"{provenance}|heuristic_analyze_not_t1",
            gross_gain=q_answer_gross + voc,
            action_cost=analyze_cost,
            risk_penalty=0.0,
            t2_bound=t2,
        ),
        "DEFER": ActionValueEstimate(
            action="DEFER",
            mean=q_defer_gross,
            lower_bound=None,
            upper_bound=None,
            uncertainty=None,
            cost=0.0,
            risk=unknown_mass,
            provenance=provenance,
            gross_gain=q_defer_gross,
            action_cost=0.0,
            risk_penalty=0.0,
            t2_bound=t2,
        ),
    }
    for name, est in estimates.items():
        if name == "EXPLORE" and t2 is not None:
            if abs(est.mean - t2) < 1e-12:
                raise AssertionError("T2 bound must not equal Q(s,EXPLORE)")
    return estimates


def q_net_map(estimates: Mapping[str, ActionValueEstimate]) -> dict[str, float]:
    return {name: est.net_value for name, est in estimates.items()}


def select_action(
    estimates: Mapping[str, ActionValueEstimate],
    *,
    mode: str = "mean",
    fallback: str = "DEFER",
    near_tie: float = 0.01,
) -> dict[str, object]:
    if not estimates:
        return {
            "selected_action": fallback,
            "second_action": None,
            "action_margin": 0.0,
            "policy_confidence": 0.0,
            "near_tie": True,
            "fallback_reason": "no_candidate_action",
        }
    if mode == "lcb":
        scores = {
            name: (est.lower_bound if est.lower_bound is not None else est.net_value)
            for name, est in estimates.items()
        }
    else:
        scores = {name: est.net_value for name, est in estimates.items()}
    ranked = sorted(scores, key=lambda name: (-scores[name], name))
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    margin = scores[best] - scores[second] if second else abs(scores[best])
    if any(est.mean != est.mean for est in estimates.values()):
        return {
            "selected_action": fallback,
            "second_action": None,
            "action_margin": 0.0,
            "policy_confidence": 0.0,
            "near_tie": True,
            "fallback_reason": "nan_action_value",
        }
    return {
        "selected_action": best,
        "second_action": second,
        "action_margin": margin,
        "policy_confidence": max(0.0, min(1.0, margin / (abs(scores[best]) + 1e-9))),
        "near_tie": margin <= near_tie,
        "fallback_reason": None,
        "estimated_q": scores,
    }


def tau_explore_from_q(q: Mapping[str, float]) -> float:
    return float(q.get("EXPLORE", 0.0)) - float(q.get("ANSWER", 0.0))
