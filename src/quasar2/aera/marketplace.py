"""Epistemic action marketplace with robust value and execution contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

from quasar2.aera.ask import select_ask
from quasar2.aera.twin import simulate_outcomes
from quasar2.aera.verify import claim_for_hypothesis, verify_claim
from quasar2.rescue.actions import analyze_only, defer_should_fire
from quasar2.rescue.pipeline import RescuePipeline
from quasar2.rescue.policy import ActionCatalog, DISABLED_BY_GATE, ELIGIBLE, SHADOW

LAMBDA_U = 0.25
LAMBDA_M = 0.35


@dataclass(frozen=True, slots=True)
class MarketQuote:
    name: str
    expected_gain: float
    cost: float
    risk: float
    latency: float
    model_uncertainty: float
    robust_net: float | None
    eligible: bool
    maturity: str
    reason: str


def robust_q(*, gain: float, cost: float, risk: float, latency: float, var_q: float, misspec: float) -> float:
    return gain - cost - risk - 0.05 * latency - LAMBDA_U * var_q - LAMBDA_M * misspec


def quote_actions(
    *,
    entropy: float,
    margin: float,
    unknown_mass: float,
    top_generation: float,
    deadline_s: float = 5.0,
    catalog: ActionCatalog | None = None,
    verifier_available: bool = False,
) -> list[MarketQuote]:
    catalog = catalog or ActionCatalog(verifier_available=verifier_available)
    quotes: list[MarketQuote] = []
    specs: tuple[tuple[str, float, float, float, float, str], ...] = (
        ("ANSWER", 1.0 - entropy, 0.0, 0.25 * entropy, 0.01, "commit"),
        ("BM25", 0.16 * entropy, 0.10, 0.05, 0.02, "lexical channel"),
        ("DENSE", 0.18 * entropy, 0.20, 0.08, 0.04, "hashing dense"),
        ("HYBRID", 0.20 * entropy, 0.18, 0.07, 0.03, "hybrid channel"),
        ("RERANK", 0.22 * entropy, 0.22, 0.08, 0.05, "discriminative rerank"),
        ("DISCRIMINATIVE", 0.36 * entropy * (1.0 - margin), 0.25, 0.10, 0.06, "falsification queries"),
        ("ANALYZE", 0.06 * entropy, 0.02, 0.02, 0.01, "internal recompute"),
        ("ASK", 0.42 * entropy, 0.28, 0.05, 2.0, "specific clarification"),
        ("VERIFY", 0.18 * (1.0 - margin) if verifier_available else 0.0, 0.12, 0.04, 0.08, "independent structured source"),
        ("DEFER", 0.0, 0.05, max(0.05, unknown_mass), 0.0, "open-set abstention"),
    )
    for name, gain, cost, risk, latency, reason in specs:
        maturity = catalog.status(name) if name != "VERIFY" else (
            ELIGIBLE if verifier_available else DISABLED_BY_GATE
        )
        eligible = maturity in {ELIGIBLE, "ACTIVE"} or (name == "VERIFY" and verifier_available)
        if name == "ASK":
            eligible = maturity in {ELIGIBLE, "ACTIVE", SHADOW}
        if name == "DEFER":
            eligible = eligible and defer_should_fire(
                entropy=entropy, unknown_mass=unknown_mass, top_generation=top_generation
            )
        if deadline_s < 0.05 and latency > 0.05:
            eligible = False
            reason = "ineligible under autocomplete SLO"
        twin = simulate_outcomes(entropy=entropy, margin=margin, action=name)
        q = robust_q(
            gain=gain,
            cost=cost,
            risk=risk,
            latency=latency,
            var_q=twin.sigma**2,
            misspec=twin.misspecification,
        )
        quotes.append(
            MarketQuote(
                name=name,
                expected_gain=gain,
                cost=cost,
                risk=risk,
                latency=latency,
                model_uncertainty=twin.sigma,
                robust_net=q if eligible else None,
                eligible=eligible,
                maturity=maturity,
                reason=reason,
            )
        )
    return quotes


def select_quote(quotes: Sequence[MarketQuote]) -> MarketQuote:
    eligible = [row for row in quotes if row.eligible and row.robust_net is not None]
    if not eligible:
        return next(row for row in quotes if row.name == "ANSWER")
    return max(eligible, key=lambda row: (row.robust_net, -row.cost, row.name))


def execute_market_action(
    pipeline: RescuePipeline,
    query: str,
    domain: str,
    selected: str,
    *,
    verifier_available: bool = False,
) -> dict[str, Any]:
    if selected == "VERIFY":
        if not verifier_available:
            raise PermissionError("VERIFY disabled: independent source not attached")
        probe = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
        result = verify_claim(claim_for_hypothesis(probe.predicted_id), predicted_id=probe.predicted_id)
        if result.retrieval_calls != 0:
            raise RuntimeError("VERIFY must not retrieve")
        return {
            "selected_action": "VERIFY",
            "executed_action": "VERIFY",
            "arm": "independent_source",
            "retrieval_calls": 0,
            "predicted_id": probe.predicted_id,
            "verify": asdict(result),
            "run": probe,
        }
    if selected == "ASK":
        probe = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
        question = select_ask(query, probe.candidates)
        return {
            "selected_action": "ASK",
            "executed_action": "ASK",
            "arm": "fast",
            "retrieval_calls": probe.retrieval_calls,
            "predicted_id": probe.predicted_id,
            "question": question,
            "run": probe,
        }
    if selected == "ANALYZE":
        analysis = analyze_only(pipeline, query, domain)
        return {
            "selected_action": "ANALYZE",
            "executed_action": "ANALYZE",
            "arm": "fast",
            "retrieval_delta": 0,
            "predicted_id": analysis["predicted_after"],
            "evidence_frozen": analysis["evidence_ids_before"] == analysis["evidence_ids_after"],
            "run": None,
        }
    from quasar2.rescue.policy import execute_selected

    return execute_selected(pipeline, query, domain, selected)


def slo_table() -> dict[str, dict[str, Any]]:
    return {
        "autocomplete": {"deadline_s": 0.05, "likely": "ANSWER"},
        "chat": {"deadline_s": 5.0, "likely": "DISCRIMINATIVE"},
        "backoffice": {"deadline_s": 60.0, "likely": "VERIFY"},
        "high_risk": {"deadline_s": 30.0, "likely": "DEFER_OR_VERIFY"},
    }
