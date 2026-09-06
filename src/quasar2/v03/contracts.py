"""Strict boundary between deployable pre-action state and evaluation outcomes."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class IntegrityError(ValueError):
    """Input cannot support the requested scientific inference."""


class Action(str, Enum):
    ANSWER = "ANSWER"
    EXPLORE = "EXPLORE"
    ANALYZE = "ANALYZE"
    ASK = "ASK"
    VERIFY = "VERIFY"
    DEFER = "DEFER"


FEATURES = (
    "entropy",
    "margin",
    "confidence",
    "recoverability",
    "decision_relevance",
    "coverage",
    "contradiction",
    "novelty",
    "unknown_mass",
    "score_dispersion",
    "query_length",
    "evidence_count",
    "previous_calls",
    "estimated_cost",
)
UNIT_FEATURES = frozenset(FEATURES) - {
    "query_length",
    "evidence_count",
    "previous_calls",
    "estimated_cost",
}
FORBIDDEN = frozenset(
    {
        "gold",
        "label",
        "labels",
        "correct",
        "correct_hypothesis",
        "gold_doc_ids",
        "qrels",
        "oracle",
        "delta_u",
        "post_action",
        "acceptable_intents",
        "expected_observation",
        "realized_utility",
        "target",
        "ground_truth",
    }
)


def reject_hidden(value: Any) -> None:
    pending, seen = [value], set()
    while pending:
        item = pending.pop()
        if not isinstance(item, (Mapping, list, tuple)) or id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, Mapping):
            invalid = FORBIDDEN.intersection(str(k).lower() for k in item)
            if invalid:
                raise IntegrityError(f"Forbidden runtime fields: {sorted(invalid)}")
            pending.extend(item.values())
        else:
            pending.extend(item)


def finite(value: float, name: str, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise IntegrityError(f"{name} must be numeric")
    if not math.isfinite(value) or value < minimum:
        raise IntegrityError(f"{name} must be finite and >= {minimum}")
    return float(value)


@dataclass(frozen=True)
class Costs:
    retrieval_calls: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    documents: int = 0
    reranker_calls: int = 0
    tool_calls: int = 0
    latency_ms: float = 0
    monetary: float = 0

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            finite(value, field.name)
            if field.name not in {"latency_ms", "monetary"} and not isinstance(value, int):
                raise IntegrityError(f"{field.name} must be an integer")

    def __add__(self, other: Costs) -> Costs:
        return Costs(
            **{f.name: getattr(self, f.name) + getattr(other, f.name) for f in fields(self)}
        )


@dataclass(frozen=True)
class RuntimeState:
    features: Mapping[str, float]
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        reject_hidden(self.features)
        if set(self.features) != set(FEATURES):
            raise IntegrityError("Feature schema must match the pre-action allowlist exactly")
        clean = {key: finite(value, key) for key, value in self.features.items()}
        if any(clean[key] > 1 for key in UNIT_FEATURES):
            raise IntegrityError("Normalized feature outside [0,1]")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise IntegrityError("Duplicate evidence")
        object.__setattr__(self, "features", MappingProxyType(clean))
        object.__setattr__(self, "evidence_ids", tuple(self.evidence_ids))

    def to_dict(self):
        return {"features": dict(self.features), "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True)
class Outcome:
    action: Action
    correct: bool
    costs: Costs
    evidence_ids: tuple[str, ...] = ()
    provenance: str = "OBSERVED"

    def __post_init__(self):
        if not isinstance(self.action, Action) or not isinstance(self.correct, bool):
            raise IntegrityError("Invalid outcome action or correctness")
        if self.provenance not in {"OBSERVED", "REPLAYED", "SIMULATED", "ESTIMATED"}:
            raise IntegrityError("Unknown counterfactual provenance")

    def validate_transition(self, before: RuntimeState, baseline: Costs = Costs()):
        if self.action == Action.ANALYZE and (
            set(self.evidence_ids) != set(before.evidence_ids)
            or self.costs.retrieval_calls != baseline.retrieval_calls
            or self.costs.tool_calls != baseline.tool_calls
        ):
            raise IntegrityError("ANALYZE cannot acquire evidence")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise IntegrityError("Duplicate acquired evidence")


@dataclass(frozen=True)
class Case:
    query_id: str
    query: str
    group_id: str
    domain: str
    split: str
    state: RuntimeState
    stop: Outcome
    additional: Outcome
    entity: str = ""
    template: str = ""
    language: str = "en"
    open_set: bool = False
    regime: str = ""

    def __post_init__(self):
        if self.split not in {"train", "development", "calibration", "test"}:
            raise IntegrityError("Unknown split")
        if not self.query_id or not self.group_id or not self.domain or not self.query.strip():
            raise IntegrityError("Case identifiers/query cannot be empty")
        if self.stop.action != Action.ANSWER:
            raise IntegrityError("Primary stop comparator must be ANSWER")
        if self.additional.action in {Action.ANSWER, Action.DEFER}:
            raise IntegrityError("Additional action must acquire or analyze")
        self.additional.validate_transition(self.state, self.stop.costs)

    def to_dict(self):
        return {
            "query_id": self.query_id,
            "query": self.query,
            "group_id": self.group_id,
            "domain": self.domain,
            "split": self.split,
            "runtime": self.state.to_dict(),
            "evaluation": {
                "stop": asdict(self.stop),
                "additional": asdict(self.additional),
                "open_set": self.open_set,
            },
            "entity": self.entity,
            "template": self.template,
            "language": self.language,
            "regime": self.regime,
        }

    @classmethod
    def from_dict(cls, row):
        def outcome(value):
            return Outcome(
                Action(value["action"]),
                value["correct"],
                Costs(**value["costs"]),
                tuple(value.get("evidence_ids", ())),
                value.get("provenance", "OBSERVED"),
            )

        return cls(
            row["query_id"],
            row["query"],
            row["group_id"],
            row["domain"],
            row["split"],
            RuntimeState(row["runtime"]["features"], tuple(row["runtime"]["evidence_ids"])),
            outcome(row["evaluation"]["stop"]),
            outcome(row["evaluation"]["additional"]),
            row.get("entity", ""),
            row.get("template", ""),
            row.get("language", "en"),
            row["evaluation"].get("open_set", False),
            row.get("regime", ""),
        )
