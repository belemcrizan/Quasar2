"""WDI-facing V2.4 pipeline: metadata retrieve, structured fetch, five actions."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Mapping, Sequence

from quasar2.evidence.contracts import FetchRequest
from quasar2.gate.complexity import GateConfig, RetrievalSignals, evaluate_gate
from quasar2.retrieval.base import Retriever, SearchHit
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.v24.actions import EpistemicAction
from quasar2.v24.analyze import analyze
from quasar2.v24.policy import PolicyConfig, decide
from quasar2.v24.state import BudgetState, HypothesisView, PolicyState
from quasar2.wdi.source import WDIEvidenceSource
from quasar2.wdi.taxonomy import DeferReason, ObservationStatus

POLICY_ALIASES = {
    "fast_only": "top1",
    "quasar_always": "v24",
    "gated": "gated_quasar",
}


def canonicalize_policy(policy: str) -> str:
    return POLICY_ALIASES.get(policy, policy)


def compute_proxy(retrieval_calls: int, steps: int, source_calls: int) -> float:
    extra_steps = max(0, steps - 1)
    return retrieval_calls * 1.0 + extra_steps * 0.25 + source_calls * 0.1


@dataclass(frozen=True, slots=True)
class V24Result:
    query: str
    final_action: str
    reason_code: str
    selected_hypothesis_id: str | None
    structured_answer: Mapping[str, Any]
    belief_score: float
    unknown_score: float
    evidence_ids: tuple[str, ...]
    retrieval_calls: int
    source_calls: int
    steps: int
    expected_gains: tuple[float, ...]
    realized_observable_gains: tuple[float, ...]
    trace: tuple[Mapping[str, Any], ...]
    clarification: str | None = None
    defer_reason: str | None = None
    policy_name: str = "v24"
    backend: str = "bm25"
    gate_route: str | None = None
    complexity_score: float = 0.0
    ambiguity_score: float = 0.0
    open_set_score: float = 0.0
    gate_reasons: tuple[str, ...] = ()
    latency_ms: float = 0.0
    gate_ms: float = 0.0
    retrieval_ms: float = 0.0
    candidate_generation_ms: float = 0.0
    evidence_scoring_ms: float = 0.0
    belief_update_ms: float = 0.0
    policy_ms: float = 0.0
    compute_proxy: float = 0.0


def _slots_filled(hyp: HypothesisView) -> float:
    filled = sum(1 for slot in hyp.required_slots if getattr(hyp, slot))
    return filled / max(1, len(hyp.required_slots))


def _top(state: PolicyState) -> HypothesisView | None:
    ranked = sorted(
        (item for item in state.hypotheses if item.hypothesis_id != "H_unknown"),
        key=lambda item: (-item.belief_score, item.hypothesis_id),
    )
    return ranked[0] if ranked else None


class V24Pipeline:
    def __init__(
        self,
        source: WDIEvidenceSource,
        *,
        retriever: Retriever | None = None,
        policy: str = "v24",
        config: PolicyConfig | None = None,
        gate_config: GateConfig | None = None,
        user_reply: Callable[[str, tuple[str, ...]], str | None] | None = None,
    ) -> None:
        self.source = source
        self.retriever = retriever or BM25Retriever(source.documents())
        self.policy = canonicalize_policy(policy)
        self.requested_policy = policy
        self.config = config or PolicyConfig()
        self.gate_config = gate_config or GateConfig()
        self.user_reply = user_reply

    def run(self, query: str, *, language: str = "en", period_hint: str | None = None) -> V24Result:
        wall0 = time.perf_counter()
        trace: list[dict[str, Any]] = []
        retrieval_calls = 0
        source_calls = 0
        expected_gains: list[float] = []
        realized: list[float] = []
        retrieval_ms = 0.0
        gate_ms = 0.0
        candidate_ms = 0.0
        policy_ms = 0.0
        belief_ms = 0.0

        t0 = time.perf_counter()
        hits: Sequence[SearchHit] = self.retriever.search(query, top_k=8, domain="wdi")
        retrieval_ms += (time.perf_counter() - t0) * 1000.0
        retrieval_calls += 1

        t0 = time.perf_counter()
        probe = RetrievalSignals(
            scores=tuple(float(hit.score) for hit in hits),
            top_kinds=tuple(str(hit.document.metadata.get("kind") or "") for hit in hits[:4]),
            open_set_prior=0.6 if any(token in query.lower() for token in ("bitcoin", "weather", "fifa", "stock")) else 0.0,
        )
        gate = evaluate_gate(query, probe, config=self.gate_config)
        gate_ms += (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        evidence_ids = [hit.document.document_id for hit in hits]
        indicators = [hit.document for hit in hits if hit.document.metadata.get("kind") == "INDICATOR_METADATA"]
        entities = [hit.document for hit in hits if hit.document.metadata.get("kind") == "ENTITY_METADATA"]
        if not indicators:
            indicators = [doc for doc in self.source.documents() if doc.metadata.get("kind") == "INDICATOR_METADATA"][:3]
        if not entities:
            entities = [doc for doc in self.source.documents() if doc.metadata.get("kind") == "ENTITY_METADATA"][:2]

        hypotheses = []
        for rank, document in enumerate(indicators[:4]):
            entity = entities[0] if entities else None
            hypotheses.append(
                HypothesisView(
                    hypothesis_id=f"h_{document.metadata['indicator_id']}_{entity.metadata['entity_code'] if entity else 'unk'}",
                    indicator_id=str(document.metadata["indicator_id"]),
                    entity_code=str(entity.metadata["entity_code"]) if entity else None,
                    entity_type=str(entity.metadata["entity_type"]) if entity else None,
                    period=period_hint,
                    unit=str(document.metadata.get("unit") or "") or None,
                    belief_score=max(0.05, 0.45 - 0.07 * rank),
                )
            )
        hypotheses.append(
            HypothesisView(
                hypothesis_id="H_unknown",
                indicator_id=None,
                entity_code=None,
                entity_type=None,
                period=None,
                unit=None,
                belief_score=0.12 if "stock" in query.lower() or "weather" in query.lower() or "bitcoin" in query.lower() else 0.08,
                required_slots=(),
            )
        )
        total = sum(item.belief_score for item in hypotheses) or 1.0
        hypotheses = [
            HypothesisView(
                hypothesis_id=item.hypothesis_id,
                indicator_id=item.indicator_id,
                entity_code=item.entity_code,
                entity_type=item.entity_type,
                period=item.period,
                unit=item.unit,
                belief_score=item.belief_score / total,
                required_slots=item.required_slots,
                status=item.status,
            )
            for item in hypotheses
        ]
        unknown = next(item.belief_score for item in hypotheses if item.hypothesis_id == "H_unknown")
        state = PolicyState(
            query=query,
            language=language,
            hypotheses=tuple(hypotheses),
            evidence_ids=tuple(evidence_ids),
            entropy=1.1,
            margin=max(0.0, hypotheses[0].belief_score - hypotheses[1].belief_score) if len(hypotheses) > 2 else 0.0,
            unknown_score=unknown,
            coverage=_slots_filled(hypotheses[0]),
            contradiction=0.0,
            source_available=True,
            budget=BudgetState(),
        )
        candidate_ms += (time.perf_counter() - t0) * 1000.0

        last = "OBSERVE"
        structured: dict[str, Any] = {}
        clarification = None
        defer_reason = None
        reason = "SUFFICIENT_EVIDENCE"
        action = EpistemicAction.DEFER
        steps = 0
        applied_route = None

        effective = self.policy
        if self.policy == "gated_quasar":
            applied_route = gate.route
            if gate.route == "FAST":
                effective = "top1"
            elif gate.route == "DEFER_EARLY":
                effective = "defer_early"
            else:
                effective = "v24"

        if effective == "defer_early":
            action = EpistemicAction.DEFER
            reason = "OPEN_SET"
            defer_reason = DeferReason.OPEN_SET.value
            steps = 1
        elif effective in {"always_answer", "top1"}:
            action = EpistemicAction.ANSWER
            reason = "SUFFICIENT_EVIDENCE"
            top = _top(state)
            structured = self._commit(top, period_hint)
            source_calls += 1
            steps = 1
        elif effective == "threshold":
            top = _top(state)
            if top and top.belief_score >= 0.35 and _slots_filled(top) >= 0.99:
                action = EpistemicAction.ANSWER
                structured = self._commit(top, period_hint)
                source_calls += 1
            else:
                action = EpistemicAction.DEFER
                defer_reason = DeferReason.BUDGET_EXHAUSTED_UNSAFE.value
                reason = "RISK_LIMIT"
            steps = 1
        else:
            while steps < 8:
                steps += 1
                before_hash = state.state_hash()
                t_dec = time.perf_counter()
                action, reason, scores = decide(state, last=last, cfg=self.config)
                policy_ms += (time.perf_counter() - t_dec) * 1000.0
                expected_gains.append(scores[action.value])
                trace.append(
                    {
                        "step": steps,
                        "action": action.value,
                        "reason_code": reason,
                        "utilities": scores,
                        "state_before": before_hash,
                        "evidence_ids": list(state.evidence_ids),
                    }
                )
                if action == EpistemicAction.ANALYZE:
                    supports = [
                        (hyp.hypothesis_id, 0.4 if hyp.indicator_id and hyp.entity_code else 0.05, 0.0)
                        for hyp in state.hypotheses
                    ]
                    t_b = time.perf_counter()
                    new_state = analyze(state, supports)
                    belief_ms += (time.perf_counter() - t_b) * 1000.0
                    if new_state.evidence_ids != state.evidence_ids:
                        raise RuntimeError("ANALYZE mutated evidence ids")
                    realized.append(abs(new_state.entropy - state.entropy))
                    state = PolicyState(
                        query=new_state.query,
                        language=new_state.language,
                        hypotheses=new_state.hypotheses,
                        evidence_ids=new_state.evidence_ids,
                        entropy=new_state.entropy,
                        margin=new_state.margin,
                        unknown_score=new_state.unknown_score,
                        coverage=new_state.coverage,
                        contradiction=new_state.contradiction,
                        source_available=new_state.source_available,
                        budget=state.budget.charge(steps=1, analyze=1, cost=0.04),
                        analyzed_versions=new_state.analyzed_versions,
                        history=state.history + ("ANALYZE",),
                    )
                    last = action.value
                    continue
                if action == EpistemicAction.EXPLORE:
                    top = _top(state)
                    extra_q = f"{query} {top.indicator_id if top else ''} discriminating metadata"
                    t_r = time.perf_counter()
                    extra = self.retriever.search(extra_q, top_k=4, domain="wdi")
                    retrieval_ms += (time.perf_counter() - t_r) * 1000.0
                    retrieval_calls += 1
                    new_ids = tuple(dict.fromkeys(state.evidence_ids + tuple(hit.document.document_id for hit in extra)))
                    realized.append(float(len(new_ids) - len(state.evidence_ids)))
                    state = PolicyState(
                        query=state.query,
                        language=state.language,
                        hypotheses=state.hypotheses,
                        evidence_ids=new_ids,
                        entropy=max(0.2, state.entropy - 0.15),
                        margin=min(1.0, state.margin + 0.05),
                        unknown_score=state.unknown_score,
                        coverage=state.coverage,
                        contradiction=state.contradiction,
                        source_available=True,
                        budget=state.budget.charge(steps=1, explore=1, retrieval=1, cost=0.12),
                        analyzed_versions=state.analyzed_versions,
                        history=state.history + ("EXPLORE",),
                    )
                    last = action.value
                    continue
                if action == EpistemicAction.ASK:
                    options = tuple(
                        f"{h.indicator_id}" for h in state.hypotheses if h.indicator_id
                    )[:3]
                    question = (
                        "Which indicator family do you mean: "
                        + ", ".join(options)
                        + "?"
                    )
                    clarification = question
                    reply = self.user_reply(question, options) if self.user_reply else None
                    if reply:
                        updated = []
                        for hyp in state.hypotheses:
                            boost = 0.4 if hyp.indicator_id == reply else 0.0
                            updated.append(
                                HypothesisView(
                                    hypothesis_id=hyp.hypothesis_id,
                                    indicator_id=hyp.indicator_id,
                                    entity_code=hyp.entity_code,
                                    entity_type=hyp.entity_type,
                                    period=hyp.period,
                                    unit=hyp.unit,
                                    belief_score=hyp.belief_score + boost,
                                    required_slots=hyp.required_slots,
                                    status=hyp.status,
                                )
                            )
                        total_b = sum(item.belief_score for item in updated) or 1.0
                        updated = [
                            HypothesisView(
                                hypothesis_id=item.hypothesis_id,
                                indicator_id=item.indicator_id,
                                entity_code=item.entity_code,
                                entity_type=item.entity_type,
                                period=item.period,
                                unit=item.unit,
                                belief_score=item.belief_score / total_b,
                                required_slots=item.required_slots,
                                status=item.status,
                            )
                            for item in updated
                        ]
                        state = PolicyState(
                            query=state.query,
                            language=state.language,
                            hypotheses=tuple(updated),
                            evidence_ids=state.evidence_ids,
                            entropy=max(0.2, state.entropy - 0.4),
                            margin=min(1.0, state.margin + 0.2),
                            unknown_score=state.unknown_score * 0.5,
                            coverage=state.coverage,
                            contradiction=state.contradiction,
                            source_available=True,
                            budget=state.budget.charge(steps=1, ask=1, cost=0.2),
                            analyzed_versions=state.analyzed_versions,
                            history=state.history + ("ASK",),
                        )
                        last = action.value
                        continue
                    last = action.value
                    break
                if action == EpistemicAction.ANSWER:
                    top = _top(state)
                    structured = self._commit(top, period_hint)
                    source_calls += 1
                    if structured.get("observation_status") == ObservationStatus.NOT_AVAILABLE.value:
                        action = EpistemicAction.DEFER
                        reason = "DATA_NOT_AVAILABLE"
                        defer_reason = DeferReason.DATA_NOT_AVAILABLE.value
                        structured = {}
                    break
                if action == EpistemicAction.DEFER:
                    defer_reason = (
                        DeferReason.SOURCE_UNAVAILABLE.value
                        if not state.source_available
                        else DeferReason.OPEN_SET.value
                    )
                    break
                break

        top = _top(state)
        latency_ms = (time.perf_counter() - wall0) * 1000.0
        steps_out = max(1, steps)
        proxy = compute_proxy(retrieval_calls, steps_out, source_calls)
        return V24Result(
            query=query,
            final_action=action.value,
            reason_code=reason,
            selected_hypothesis_id=top.hypothesis_id if top else None,
            structured_answer=structured,
            belief_score=top.belief_score if top else 0.0,
            unknown_score=state.unknown_score,
            evidence_ids=state.evidence_ids,
            retrieval_calls=retrieval_calls,
            source_calls=source_calls,
            steps=steps_out,
            expected_gains=tuple(expected_gains),
            realized_observable_gains=tuple(realized),
            trace=tuple(trace),
            clarification=clarification,
            defer_reason=defer_reason,
            policy_name=self.requested_policy,
            backend=getattr(self.retriever, "profile_id", self.retriever.__class__.__name__),
            gate_route=applied_route or gate.route,
            complexity_score=gate.complexity_score,
            ambiguity_score=gate.ambiguity_score,
            open_set_score=gate.open_set_score,
            gate_reasons=gate.reasons,
            latency_ms=latency_ms,
            gate_ms=gate_ms,
            retrieval_ms=retrieval_ms,
            candidate_generation_ms=candidate_ms,
            evidence_scoring_ms=0.0,
            belief_update_ms=belief_ms,
            policy_ms=policy_ms,
            compute_proxy=proxy,
        )

    def _commit(self, top: HypothesisView | None, period_hint: str | None) -> dict[str, Any]:
        if top is None or not top.indicator_id or not top.entity_code:
            return {
                "observation_status": ObservationStatus.UNSUPPORTED_INTENT.value,
            }
        period = top.period or period_hint or "latest"
        fetched = self.source.fetch(
            FetchRequest(indicator_id=top.indicator_id, entity_code=top.entity_code, period=period, unit=top.unit)
        )
        payload = dict(fetched[0].payload)
        payload.update(
            {
                "indicator_id": top.indicator_id,
                "entity_code": top.entity_code,
                "entity_type": top.entity_type,
                "final_action": "ANSWER",
            }
        )
        return payload
