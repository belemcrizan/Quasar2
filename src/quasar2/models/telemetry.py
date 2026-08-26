"""Serializable trace and final result returned by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any

from quasar2.models.belief import BeliefState
from quasar2.models.decision import Decision
from quasar2.models.evidence import EvidenceItem
from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.retrieval.base import SearchHit


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            definition.name: _jsonable(getattr(value, definition.name))
            for definition in fields(value)
        }
    if hasattr(value, "items"):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class DecisionTelemetry:
    """Optional v2 decision diagnostics. Absent on legacy results unless shadow mode is on."""

    belief_entropy: float | None = None
    prior_dispersion: float | None = None
    recoverability: float | None = None
    voi: float | None = None
    voi_true_oracle: float | None = None
    voi_estimate: float | None = None
    voi_ucb: float | None = None
    voi_realized: float | None = None
    net_voi: float | None = None
    net_voi_true_oracle: float | None = None
    net_voi_estimate: float | None = None
    net_voi_ucb: float | None = None
    ucb: float | None = None
    analyze_voc: float | None = None
    inference_error: float | None = None
    conformal_set_size: int | None = None
    selected_action: str | None = None
    recommended_action_v2: str | None = None
    executed_action_legacy: str | None = None
    action_utility: float | None = None
    decision_utility_realized: float | None = None
    cost: float | None = None
    risk: float | None = None
    unknown_probability: float | None = None
    belief_top1: str | None = None
    belief_top2: str | None = None
    belief_margin: float | None = None
    policy_name: str | None = None
    lipschitz_norm: str | None = None
    lipschitz_constant: float | None = None
    divergence_units: str | None = None
    tv_convention: str | None = None
    recoverability_method: str | None = None
    voi_bound_binary: float | None = None
    voi_bound_general: float | None = None
    voi_empirical: float | None = None
    voi_bound_gap: float | None = None
    voi_bound_violated: bool | None = None
    stop_decision: bool | None = None
    stop_reason: str | None = None
    best_info_action: str | None = None
    conformal_alpha: float | None = None
    conformal_coverage: float | None = None
    nonconformity_score: float | None = None
    estimated_q_answer: float | None = None
    estimated_q_analyze: float | None = None
    estimated_q_explore: float | None = None
    estimated_q_ask: float | None = None
    estimated_q_defer: float | None = None
    second_best_action: str | None = None
    action_margin: float | None = None
    shadow_policy: str | None = None
    kernel_source: str | None = None


@dataclass(frozen=True, slots=True)
class TraceEvent:
    sequence: int
    stage: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    observation: Observation
    candidates: tuple[HypothesisCandidate, ...]
    final_belief: BeliefState
    decision: Decision
    predicted_hypothesis_id: str
    answer: str | None
    clarification_question: str | None
    evidence: tuple[EvidenceItem, ...]
    trace: tuple[TraceEvent, ...]
    retrieval_calls: int
    explore_rounds: int
    elapsed_ms: float
    ablation: str = "full"
    retrieval_calls_avoided: int = 0
    pruned_explorations: int = 0
    termination_reason: str = "decision"
    issued_query_hashes: tuple[str, ...] = ()
    mean_document_novelty: float = 0.0
    total_belief_variation: float = 0.0
    total_observed_entropy_reduction: float = 0.0
    retrieval_hits: tuple[SearchHit, ...] = ()
    gate_ms: float = 0.0
    candidate_generation_ms: float = 0.0
    retrieval_ms: float = 0.0
    evidence_scoring_ms: float = 0.0
    belief_update_ms: float = 0.0
    policy_ms: float = 0.0
    v2_telemetry: DecisionTelemetry | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)
