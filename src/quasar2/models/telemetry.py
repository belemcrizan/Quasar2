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

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)
